#!/usr/bin/env python3
"""
MCP Server for Systematic Review Screening
Implements search and fetch tools for Deep Research integration
"""
import os
import logging
import time
from typing import Dict, Any, Optional

from fastmcp import FastMCP
from starlette.middleware.cors import CORSMiddleware
import database as db

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
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
    
    # Create FastMCP server with descriptive name for OpenAI Deep Research API
    mcp = FastMCP(
        name="DeepResearch Systematic Review MCP Server",
        instructions=server_instructions
    )
    
    @mcp.tool()
    async def search(query: str, limit: Optional[int] = None, mode: str = "fulltext") -> Dict[str, Any]:
        """
        Search for citations in the systematic review corpus.
        
        This tool searches through titles, abstracts, and metadata to find 
        semantically relevant citations. Returns a list of matching citations 
        with basic information. Use the fetch tool to get complete details.
        
        Args:
            query: Search query string. Natural language queries work best.
                   Examples: "randomized controlled trials diabetes", 
                            "spinal cord injury rehabilitation"
            limit: Maximum number of results to return (default: None - returns all matching citations)
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
    async def health_check() -> Dict[str, str]:
        """
        Health check endpoint to verify server is running.
        
        Returns:
            Simple health status
        """
        return {
            "status": "healthy",
            "server": "DeepResearchServer",
            "timestamp": str(time.time())
        }
    
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


def main(port=8001):
    """Main function to start the MCP server."""
    server = create_server()
    
    server.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins in development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"]
    )
    
    @server.custom_route("/health", methods=["GET"])
    async def health_endpoint(request):
        """HTTP health check endpoint for production monitoring"""
        from starlette.responses import JSONResponse
        try:
            tools = await server.get_tools()
            return JSONResponse({
                "status": "healthy",
                "server": "DeepResearch Systematic Review MCP Server",
                "timestamp": str(time.time()),
                "tools_count": len(tools),
                "version": "1.0.0"
            })
        except Exception as e:
            return JSONResponse({
                "status": "unhealthy",
                "server": "DeepResearch Systematic Review MCP Server",
                "timestamp": str(time.time()),
                "error": str(e)
            }, status_code=500)
    
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", port))
    
    # Log server info
    logger.info(f"Starting Systematic Review MCP server on {host}:{port}")
    logger.info("Server will be accessible via SSE transport")
    logger.info(f"Health endpoint: http://{host}:{port}/health")
    
    if os.getenv("EXTERNAL_HOST"):
        protocol = os.getenv("EXTERNAL_PROTOCOL", "https")
        ext_host = os.getenv("EXTERNAL_HOST")
        ext_port = os.getenv("EXTERNAL_PORT", "443")
        
        if (protocol == "https" and ext_port == "443") or (protocol == "http" and ext_port == "80"):
            ext_url = f"{protocol}://{ext_host}/sse/"
        else:
            ext_url = f"{protocol}://{ext_host}:{ext_port}/sse/"
            
        logger.info(f"External URL: {ext_url}")
    elif os.getenv("FLY_APP_NAME"):
        app_name = os.getenv("FLY_APP_NAME")
        logger.info(f"External URL: https://{app_name}.fly.dev/sse/")
    elif os.getenv("HEROKU_APP_NAME"):
        app_name = os.getenv("HEROKU_APP_NAME")
        logger.info(f"External URL: https://{app_name}.herokuapp.com/sse/")
    elif os.getenv("REPL_SLUG") and os.getenv("REPL_OWNER"):
        repl_slug = os.getenv("REPL_SLUG")
        repl_owner = os.getenv("REPL_OWNER")
        logger.info(f"External URL: https://{repl_slug}-{port}.{repl_owner}.repl.co/sse/")
    else:
        logger.info(f"Local URL: http://localhost:{port}/sse/")
    
    # Start server with SSE transport
    server.run(transport="sse", host=host, port=port)


if __name__ == "__main__":
    main()
