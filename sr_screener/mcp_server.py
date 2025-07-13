#!/usr/bin/env python3
"""
MCP Server for Systematic Review Screening
Implements search and fetch tools for Deep Research integration
"""
import os
import logging
from typing import Dict, List, Any

from fastmcp import FastMCP
import database as db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Server configuration
server_instructions = """
This MCP server provides search and document retrieval capabilities for systematic review screening.
The server contains a corpus of research citations (titles, abstracts, metadata) that can be searched
and retrieved for systematic review screening tasks.

Use the search tool to find relevant citations based on keywords or concepts, then use the fetch tool 
to retrieve complete citation details including abstract, authors, and metadata.

The corpus consists of academic citations from medical and scientific literature.
"""


def create_server():
    """Create and configure the MCP server with search and fetch tools."""
    # Initialize database
    db.init_db()
    
    # Create FastMCP server
    mcp = FastMCP("Systematic Review MCP Server", instructions=server_instructions)
    
    @mcp.tool()
    async def search(query: str, limit: int = 10000, mode: str = "fulltext") -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for citations in the systematic review corpus.
        
        This tool searches through titles, abstracts, and metadata to find 
        semantically relevant citations. Returns a list of matching citations 
        with basic information. Use the fetch tool to get complete details.
        
        Args:
            query: Search query string. Natural language queries work best.
                   Examples: "randomized controlled trials diabetes", 
                            "spinal cord injury rehabilitation"
            limit: Maximum number of results to return (default: 10000 to ensure all citations available)
            mode: Search mode - "fulltext" for keyword search or "semantic" for embedding-based search
        
        Returns:
            Dictionary with 'results' key containing list of matching citations.
            Each result includes id, title, text snippet, and url per Deep Research spec.
        """
        try:
            # Get search results based on mode
            # Special case: empty query or "*" returns all citations
            if not query.strip() or query.strip() == "*":
                # Return all citations for comprehensive screening
                results = db.get_all_citations(limit)
            else:
                # Use semantic or fulltext search based on mode
                if mode == "semantic":
                    results = db.semantic_search_citations(query, limit)
                else:
                    results = db.search_citations(query, limit)
            
            # Format results for MCP - must comply with Deep Research spec
            formatted_results = []
            for citation in results:
                # Build URL based on citation ID
                url = None
                if citation["id"].startswith("PMID:"):
                    pmid = citation["id"].replace("PMID:", "")
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                elif citation.get("doi"):
                    url = f"https://doi.org/{citation['doi']}"
                else:
                    # Fallback URL for internal references
                    url = f"mcp://citation/{citation['id']}"
                
                # Format exactly as required by Deep Research spec
                formatted_results.append({
                    "id": citation["id"],
                    "title": citation["title"],
                    "text": citation["abstract_snippet"] or citation.get("abstract", "")[:200] + "...",
                    "url": url
                })
            
            # Return only the results array as specified
            return {"results": formatted_results}
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {
                "results": [],
                "query": query,
                "error": str(e)
            }
    
    @mcp.tool()
    async def fetch(id: str) -> Dict[str, Any]:
        """
        Retrieve complete citation details by ID.
        
        This tool fetches the full citation content including abstract, authors,
        metadata, and bibliographic information. Use this after finding relevant 
        citations with the search tool to get complete information for analysis.
        
        Args:
            id: Citation ID (e.g., "PMID:12345678" or other identifier)
            
        Returns:
            Complete citation with all available metadata including:
            - id: Unique identifier
            - title: Full title
            - abstract: Complete abstract text
            - authors: List of authors
            - year: Publication year
            - journal: Journal name
            - doi: DOI if available
            - mesh_terms: MeSH terms if available
            - keywords: Keywords
            - url: Link to original source (when available)
            
        Raises:
            ValueError: If the specified ID is not found
        """
        try:
            # Fetch citation from database
            citation = db.fetch_citation(id)
            
            if not citation:
                raise ValueError(f"Citation not found: {id}")
            
            # Build URL if possible
            url = None
            if id.startswith("PMID:"):
                pmid = id.replace("PMID:", "")
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            elif citation.get("doi"):
                url = f"https://doi.org/{citation['doi']}"
            
            # Format response according to Deep Research spec
            return {
                "id": citation["id"],
                "title": citation["title"],
                "text": citation["abstract"],  # Required field name per spec
                "url": url,
                "metadata": {
                    "authors": citation.get("authors", []),
                    "year": citation.get("year"),
                    "journal": citation.get("journal", ""),
                    "doi": citation.get("doi", ""),
                    "mesh_terms": citation.get("mesh_terms", []),
                    "keywords": citation.get("keywords", []),
                    "created_at": citation.get("created_at"),
                    "source": citation.get("raw_data", {}).get("source", "unknown")
                }
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            raise ValueError(f"Error fetching citation: {str(e)}")
    
    @mcp.tool()
    async def corpus_info() -> Dict[str, Any]:
        """
        Get information about the citation corpus.
        
        Returns statistics and metadata about the loaded citation corpus,
        including total count, year distribution, and data sources.
        
        Returns:
            Dictionary with corpus statistics and metadata
        """
        try:
            stats = db.get_corpus_stats()
            
            return {
                "total_citations": stats["total_citations"],
                "year_distribution": stats["year_distribution"],
                "description": "Systematic review citation corpus for medical/scientific literature",
                "search_capabilities": [
                    "Full-text search in titles and abstracts",
                    "Relevance ranking",
                    "Semantic search capabilities"
                ]
            }
            
        except Exception as e:
            logger.error(f"Corpus info error: {e}")
            return {
                "error": str(e),
                "total_citations": 0
            }
    
    return mcp


def main(port=8000):
    """Main function to start the MCP server."""
    server = create_server()
    
    # Log server info
    logger.info(f"Starting Systematic Review MCP server on 0.0.0.0:{port}")
    logger.info("Server will be accessible via SSE transport")
    
    # Start server with SSE transport
    server.run(transport="sse", port=port)


if __name__ == "__main__":
    main()