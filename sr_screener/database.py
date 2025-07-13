"""
Database module for systematic review screener
Uses PostgreSQL with full-text search capabilities
"""
import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from typing import List, Dict, Optional, Any

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text, Column, String, Text, Integer, DateTime, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import ARRAY
from openai import OpenAI

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
Base = declarative_base()

# OpenAI client for embeddings
openai_client = None
if os.environ.get("OPENAI_API_KEY"):
    openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class Citation(Base):
    __tablename__ = 'citations'
    
    id = Column(String, primary_key=True)
    title = Column(Text, nullable=False)
    abstract = Column(Text)
    year = Column(Integer)
    authors = Column(Text)  # JSON string
    journal = Column(String)
    doi = Column(String)
    mesh_terms = Column(Text)  # JSON string
    keywords = Column(Text)  # JSON string
    raw_data = Column(JSON)  # Original data
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Full-text search column
    search_vector = Column(Text)  # Will store tsvector
    
    # Vector embedding for semantic search
    embedding = Column(ARRAY(Float))  # Store OpenAI embeddings


# Create engine and session
if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # Fallback for testing
    engine = create_engine('sqlite:///citations.db', 
                         connect_args={'check_same_thread': False},
                         poolclass=StaticPool)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db():
    """Provide a transactional scope for database operations."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database with tables and full-text search."""
    Base.metadata.create_all(bind=engine)
    
    # Create full-text search index if using PostgreSQL
    if 'postgresql' in str(engine.url):
        with engine.connect() as conn:
            # Enable extensions
            conn.execute(text("""
                CREATE EXTENSION IF NOT EXISTS pg_trgm;
                CREATE EXTENSION IF NOT EXISTS vector;
            """))
            conn.commit()
            
            # Add embedding column if it doesn't exist
            try:
                conn.execute(text("""
                    ALTER TABLE citations 
                    ADD COLUMN IF NOT EXISTS embedding float[]
                """))
                conn.commit()
                logger.info("Added embedding column to citations table")
            except Exception as e:
                logger.info(f"Embedding column might already exist: {e}")
            
            # Create indexes
            conn.execute(text("""
                -- Create GIN index for full-text search
                CREATE INDEX IF NOT EXISTS idx_citations_search 
                ON citations USING gin(to_tsvector('english', 
                    coalesce(title, '') || ' ' || 
                    coalesce(abstract, '') || ' ' || 
                    coalesce(authors, '') || ' ' ||
                    coalesce(keywords, '')
                ));
                
                -- Create index for vector similarity search (if embeddings exist)
                -- This will be created after embeddings are generated
            """))
            conn.commit()


def bulk_insert_citations(df: pd.DataFrame):
    """
    Bulk insert citations from DataFrame, handling duplicates gracefully.
    Expected columns: id, title, abstract, year, authors, journal, doi, 
                     mesh_terms, keywords, raw_data
    
    Returns:
        Dict with counts of inserted, updated, and skipped citations
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "total": len(df)}
    
    with get_db() as db:
        # Get all existing citation IDs to avoid duplicate queries
        existing_ids = set()
        try:
            existing_citations = db.query(Citation.id).all()
            existing_ids = {citation.id for citation in existing_citations}
        except Exception as e:
            logger.warning(f"Could not fetch existing citation IDs: {e}")
        
        for _, row in df.iterrows():
            try:
                citation_id = str(row.get('id', ''))
                if not citation_id:
                    logger.warning("Skipping row with empty ID")
                    stats["skipped"] += 1
                    continue
                
                # Prepare citation data
                citation_data = {
                    'title': str(row.get('title', '')),
                    'abstract': str(row.get('abstract', '')),
                    'year': int(row.get('year')) if pd.notna(row.get('year')) else None,
                    'authors': json.dumps(row.get('authors', [])) if isinstance(row.get('authors'), list) else str(row.get('authors', '')),
                    'journal': str(row.get('journal', '')),
                    'doi': str(row.get('doi', '')),
                    'mesh_terms': json.dumps(row.get('mesh_terms', [])) if isinstance(row.get('mesh_terms'), list) else str(row.get('mesh_terms', '')),
                    'keywords': json.dumps(row.get('keywords', [])) if isinstance(row.get('keywords'), list) else str(row.get('keywords', '')),
                    'raw_data': row.get('raw_data', {}) if isinstance(row.get('raw_data'), dict) else {}
                }
                
                if citation_id in existing_ids:
                    # Update existing citation
                    try:
                        db.query(Citation).filter(Citation.id == citation_id).update(citation_data)
                        stats["updated"] += 1
                    except Exception as e:
                        logger.error(f"Error updating citation {citation_id}: {str(e)}")
                        stats["skipped"] += 1
                else:
                    # Insert new citation
                    try:
                        citation = Citation(id=citation_id, **citation_data)
                        db.add(citation)
                        existing_ids.add(citation_id)  # Add to our local set
                        stats["inserted"] += 1
                    except Exception as e:
                        logger.error(f"Error inserting citation {citation_id}: {str(e)}")
                        stats["skipped"] += 1
                        
            except Exception as e:
                logger.error(f"Error processing citation {row.get('id', 'unknown')}: {str(e)}")
                stats["skipped"] += 1
                continue
        
        try:
            db.commit()
            
            # Generate embeddings for new citations in background
            if openai_client and (stats['inserted'] > 0 or stats['updated'] > 0):
                logger.info("Generating embeddings for new citations...")
                embedding_stats = generate_citation_embeddings()
                logger.info(f"Embedding results: {embedding_stats}")
                stats['embeddings'] = embedding_stats
                
        except Exception as e:
            logger.error(f"Error committing changes: {str(e)}")
            db.rollback()
            raise
        
        return stats


def search_citations(query: str, limit: int = 10000) -> List[Dict[str, Any]]:
    """
    Search citations using full-text search.
    Returns list of matching citations with snippets.
    
    Note: Default limit increased to 10000 to ensure all citations can be screened.
    """
    with get_db() as db:
        if 'postgresql' in str(engine.url):
            # PostgreSQL full-text search
            results = db.execute(text("""
                SELECT 
                    id, 
                    title,
                    abstract,
                    year,
                    journal,
                    ts_headline('english', title, plainto_tsquery('english', :query), 
                               'MaxWords=30, MinWords=15, ShortWord=3, HighlightAll=FALSE') as title_snippet,
                    ts_headline('english', abstract, plainto_tsquery('english', :query), 
                               'MaxWords=50, MinWords=30, ShortWord=3, HighlightAll=FALSE') as abstract_snippet,
                    ts_rank(to_tsvector('english', coalesce(title, '') || ' ' || coalesce(abstract, '')), 
                           plainto_tsquery('english', :query)) as relevance
                FROM citations
                WHERE to_tsvector('english', coalesce(title, '') || ' ' || coalesce(abstract, '')) 
                      @@ plainto_tsquery('english', :query)
                ORDER BY relevance DESC
                LIMIT :limit
            """), {"query": query, "limit": limit})
        else:
            # SQLite fallback - simple LIKE search
            search_pattern = f"%{query}%"
            results = db.execute(text("""
                SELECT 
                    id, 
                    title,
                    abstract,
                    year,
                    journal,
                    title as title_snippet,
                    substr(abstract, 1, 200) as abstract_snippet,
                    1.0 as relevance
                FROM citations
                WHERE title LIKE :pattern OR abstract LIKE :pattern
                LIMIT :limit
            """), {"pattern": search_pattern, "limit": limit})
        
        citations = []
        for row in results:
            citations.append({
                "id": row.id,
                "title": row.title,
                "abstract": row.abstract,
                "year": row.year,
                "journal": row.journal,
                "title_snippet": row.title_snippet,
                "abstract_snippet": row.abstract_snippet,
                "relevance": float(row.relevance)
            })
        
        return citations


def fetch_citation(citation_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single citation by ID with all metadata.
    """
    with get_db() as db:
        citation = db.query(Citation).filter(Citation.id == citation_id).first()
        
        if not citation:
            return None
        
        return {
            "id": citation.id,
            "title": citation.title,
            "abstract": citation.abstract,
            "year": citation.year,
            "authors": json.loads(citation.authors) if citation.authors else [],
            "journal": citation.journal,
            "doi": citation.doi,
            "mesh_terms": json.loads(citation.mesh_terms) if citation.mesh_terms else [],
            "keywords": json.loads(citation.keywords) if citation.keywords else [],
            "raw_data": citation.raw_data,
            "created_at": citation.created_at.isoformat() if citation.created_at else None
        }


def get_all_citations(limit: int = 10000) -> List[Dict[str, Any]]:
    """
    Get all citations from the database (no search filtering).
    Used for comprehensive systematic review screening.
    
    Args:
        limit: Maximum number of citations to return (default: 10000)
        
    Returns:
        List of all citations with basic metadata
    """
    with get_db() as db:
        results = db.query(Citation).limit(limit).all()
        
        citations = []
        for citation in results:
            citations.append({
                "id": citation.id,
                "title": citation.title,
                "abstract": citation.abstract,
                "abstract_snippet": citation.abstract[:200] + "..." if citation.abstract and len(citation.abstract) > 200 else citation.abstract,
                "year": citation.year,
                "journal": citation.journal,
                "doi": citation.doi,
                "authors": json.loads(citation.authors) if citation.authors else [],
                "mesh_terms": json.loads(citation.mesh_terms) if citation.mesh_terms else [],
                "keywords": json.loads(citation.keywords) if citation.keywords else []
            })
        
        return citations


def get_corpus_stats() -> Dict[str, Any]:
    """Get statistics about the citation corpus."""
    with get_db() as db:
        total = db.query(Citation).count()
        
        year_stats = db.execute(text("""
            SELECT year, COUNT(*) as count
            FROM citations
            WHERE year IS NOT NULL
            GROUP BY year
            ORDER BY year DESC
            LIMIT 20
        """))
        
        return {
            "total_citations": total,
            "year_distribution": [{"year": row.year, "count": row.count} for row in year_stats]
        }


def clear_all_citations():
    """Clear all citations from the database."""
    with get_db() as db:
        count = db.query(Citation).count()
        db.query(Citation).delete()
        db.commit()
        return count


def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate OpenAI embedding for text.
    
    Args:
        text: Text to generate embedding for
        
    Returns:
        List of floats representing the embedding, or None if failed
    """
    if not openai_client:
        logger.warning("OpenAI client not initialized, skipping embedding generation")
        return None
        
    try:
        # Combine title and abstract for embedding
        response = openai_client.embeddings.create(
            model="text-embedding-3-small",  # Efficient model for embeddings
            input=text[:8000]  # Limit text length
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        return None


def generate_citation_embeddings():
    """Generate embeddings for all citations without embeddings."""
    if not openai_client:
        logger.warning("OpenAI client not initialized, cannot generate embeddings")
        return {"generated": 0, "skipped": 0, "errors": 0}
        
    stats = {"generated": 0, "skipped": 0, "errors": 0}
    
    with get_db() as db:
        # Get citations without embeddings
        citations = db.query(Citation).filter(Citation.embedding == None).all()
        
        for citation in citations:
            try:
                # Create text for embedding from title and abstract
                text = f"{citation.title}\n\n{citation.abstract or ''}"
                embedding = generate_embedding(text)
                
                if embedding:
                    citation.embedding = embedding
                    stats["generated"] += 1
                else:
                    stats["skipped"] += 1
                    
            except Exception as e:
                logger.error(f"Error generating embedding for {citation.id}: {e}")
                stats["errors"] += 1
        
        db.commit()
        
        # Create vector index if we have embeddings
        if stats["generated"] > 0:
            try:
                db.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_citations_embedding 
                    ON citations USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = 100);
                """))
                db.commit()
            except Exception as e:
                logger.warning(f"Could not create vector index: {e}")
    
    return stats


def semantic_search_citations(query: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Search citations using semantic similarity with embeddings.
    
    Args:
        query: Search query text
        limit: Maximum number of results
        
    Returns:
        List of citations sorted by semantic similarity
    """
    if not openai_client:
        logger.warning("OpenAI client not initialized, falling back to full-text search")
        return search_citations(query, limit)
    
    # Generate embedding for query
    query_embedding = generate_embedding(query)
    if not query_embedding:
        logger.warning("Could not generate query embedding, falling back to full-text search")
        return search_citations(query, limit)
    
    with get_db() as db:
        # Convert embedding to PostgreSQL array format
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # Semantic similarity search using cosine distance
        results = db.execute(text("""
            SELECT 
                id, title, abstract, year, journal, doi, authors, mesh_terms, keywords,
                1 - (embedding <=> :query_embedding::vector) as similarity
            FROM citations
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> :query_embedding::vector
            LIMIT :limit
        """), {"query_embedding": embedding_str, "limit": limit})
        
        citations = []
        for row in results:
            # Create snippet from abstract
            abstract = row.abstract or ""
            snippet = abstract[:200] + "..." if len(abstract) > 200 else abstract
            
            citations.append({
                "id": row.id,
                "title": row.title,
                "abstract": row.abstract,
                "abstract_snippet": snippet,
                "year": row.year,
                "journal": row.journal,
                "doi": row.doi,
                "authors": json.loads(row.authors) if row.authors else [],
                "mesh_terms": json.loads(row.mesh_terms) if row.mesh_terms else [],
                "keywords": json.loads(row.keywords) if row.keywords else [],
                "relevance": row.similarity
            })
        
        return citations