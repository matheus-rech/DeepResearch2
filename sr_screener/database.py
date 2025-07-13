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
from sqlalchemy import create_engine, text, Column, String, Text, Integer, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.environ.get("DATABASE_URL")
Base = declarative_base()

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
            conn.execute(text("""
                CREATE EXTENSION IF NOT EXISTS pg_trgm;
                
                -- Create GIN index for full-text search
                CREATE INDEX IF NOT EXISTS idx_citations_search 
                ON citations USING gin(to_tsvector('english', 
                    coalesce(title, '') || ' ' || 
                    coalesce(abstract, '') || ' ' || 
                    coalesce(authors, '') || ' ' ||
                    coalesce(keywords, '')
                ));
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
        for _, row in df.iterrows():
            try:
                citation_id = str(row.get('id', ''))
                
                # Check if citation already exists
                existing = db.query(Citation).filter(Citation.id == citation_id).first()
                
                if existing:
                    # Update existing citation
                    existing.title = str(row.get('title', ''))
                    existing.abstract = str(row.get('abstract', ''))
                    existing.year = int(row.get('year')) if pd.notna(row.get('year')) else None
                    existing.authors = json.dumps(row.get('authors', [])) if isinstance(row.get('authors'), list) else str(row.get('authors', ''))
                    existing.journal = str(row.get('journal', ''))
                    existing.doi = str(row.get('doi', ''))
                    existing.mesh_terms = json.dumps(row.get('mesh_terms', [])) if isinstance(row.get('mesh_terms'), list) else str(row.get('mesh_terms', ''))
                    existing.keywords = json.dumps(row.get('keywords', [])) if isinstance(row.get('keywords'), list) else str(row.get('keywords', ''))
                    existing.raw_data = row.get('raw_data', {}) if isinstance(row.get('raw_data'), dict) else {}
                    stats["updated"] += 1
                else:
                    # Insert new citation
                    citation = Citation(
                        id=citation_id,
                        title=str(row.get('title', '')),
                        abstract=str(row.get('abstract', '')),
                        year=int(row.get('year')) if pd.notna(row.get('year')) else None,
                        authors=json.dumps(row.get('authors', [])) if isinstance(row.get('authors'), list) else str(row.get('authors', '')),
                        journal=str(row.get('journal', '')),
                        doi=str(row.get('doi', '')),
                        mesh_terms=json.dumps(row.get('mesh_terms', [])) if isinstance(row.get('mesh_terms'), list) else str(row.get('mesh_terms', '')),
                        keywords=json.dumps(row.get('keywords', [])) if isinstance(row.get('keywords'), list) else str(row.get('keywords', '')),
                        raw_data=row.get('raw_data', {}) if isinstance(row.get('raw_data'), dict) else {}
                    )
                    db.add(citation)
                    stats["inserted"] += 1
                    
            except Exception as e:
                logger.error(f"Error processing citation {row.get('id', 'unknown')}: {str(e)}")
                stats["skipped"] += 1
                continue
        
        db.commit()
        
        return stats


def search_citations(query: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Search citations using full-text search.
    Returns list of matching citations with snippets.
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