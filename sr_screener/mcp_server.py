#!/usr/bin/env python3
"""
MCP server for systematic review screening.

This file creates and configures an MCP server using the ``FastMCP``
library.  The implementation is based on the upstream DeepResearch2
``mcp_server.py`` but includes several improvements:

* A ``SyncMCPServer`` wrapper class that provides both synchronous
  and asynchronous access to MCP server tools. The wrapper exposes
  ``get_tools()`` for synchronous access and ``aget_tools()`` for 
  asynchronous access, allowing consumers (such as test scripts) to 
  call them from both synchronous and asynchronous contexts.
* Minor code clean‑ups and type hints for clarity.

The server exposes four tools: ``search``, ``fetch``, ``health_check``
and ``corpus_info``.  Each tool is registered via the ``@mcp.tool()``
decorator so that it becomes discoverable by Deep Research.
"""

from __future__ import annotations

import os
import logging
import time
import asyncio
from typing import Dict, Any, Optional, List

from fastmcp import FastMCP  # type: ignore
import database as db  # type: ignore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyncMCPServer:
    """Wrapper class that provides both synchronous and asynchronous access to FastMCP server tools."""
    
    def __init__(self, mcp: FastMCP):
        self._mcp = mcp

    async def aget_tools(self):
        """Asynchronous access to tools."""
        return await self._mcp.get_tools()

    def get_tools(self):
        """Provide synchronous access for scripts/tests."""
        return asyncio.run(self._mcp.get_tools())

    def __getattr__(self, name):
        """Delegate all other attribute access to the underlying FastMCP instance."""
        return getattr(self._mcp, name)


# Server instructions shown to the language model
server_instructions: str = """
This MCP server provides search and document retrieval capabilities for systematic review screening.
The server contains a corpus of research citations (titles, abstracts, metadata) that can be searched
and retrieved for systematic review screening tasks.

Use the search tool to find relevant citations based on keywords or concepts, then use the fetch tool
to retrieve complete citation details including abstract, authors, and metadata.

The corpus consists of academic citations from medical and scientific literature.
"""


def create_server() -> SyncMCPServer:
    """Create and configure the MCP server with search and fetch tools."""
    # Initialise the database
    db.init_db()
    # Create FastMCP server
    mcp: FastMCP = FastMCP("DeepResearchServer", instructions=server_instructions)

    @mcp.tool()
    async def search(query: str, limit: Optional[int] = None, mode: str = 'fulltext') -> Dict[str, Any]:
        """
        Search for citations in the systematic review corpus.
        This tool searches through titles, abstracts and metadata to find
        semantically relevant citations.  Returns a list of matching
        citations with basic information.  Use the ``fetch`` tool to get
        complete details.
        """
        try:
            # empty query or "*" returns all citations
            if not query.strip() or query.strip() == '*':
                results = db.get_all_citations(limit)
            else:
                if mode == 'semantic':
                    results = db.semantic_search_citations(query, limit)
                else:
                    results = db.search_citations(query, limit)
            formatted_results: List[Dict[str, Any]] = []
            for citation in results:
                url: Optional[str] = None
                if citation['id'].startswith('PMID:'):
                    pmid = citation['id'].replace('PMID:', '')
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                elif citation.get('doi'):
                    url = f"https://doi.org/{citation['doi']}"
                else:
                    url = f"mcp://citation/{citation['id']}"
                snippet = citation.get('abstract_snippet') or citation.get('abstract', '')
                if snippet:
                    snippet = (snippet[:200] + '...') if len(snippet) > 200 else snippet
                formatted_results.append({
                    'id': citation['id'],
                    'title': citation['title'],
                    'text': snippet,
                    'url': url,
                })
            return {'results': formatted_results}
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {'results': [], 'error': str(e)}

    @mcp.tool()
    async def fetch(id: str) -> Dict[str, Any]:
        """
        Retrieve complete citation details by ID.
        This tool fetches the full citation content including abstract,
        authors, metadata and bibliographic information.
        """
        try:
            citation = db.fetch_citation(id)
            if not citation:
                raise ValueError(f"Citation not found: {id}")
            url: Optional[str] = None
            if id.startswith('PMID:'):
                pmid = id.replace('PMID:', '')
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            elif citation.get('doi'):
                url = f"https://doi.org/{citation['doi']}"
            return {
                'id': citation['id'],
                'title': citation['title'],
                'text': citation['abstract'],
                'url': url,
                'metadata': {
                    'authors': citation.get('authors', []),
                    'year': citation.get('year'),
                    'journal': citation.get('journal', ''),
                    'doi': citation.get('doi', ''),
                    'mesh_terms': citation.get('mesh_terms', []),
                    'keywords': citation.get('keywords', []),
                    'created_at': citation.get('created_at'),
                    'source': citation.get('raw_data', {}).get('source', 'unknown'),
                },
            }
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            raise ValueError(f"Error fetching citation: {e}")

    @mcp.tool()
    async def health_check() -> Dict[str, str]:
        """Health check endpoint to verify server is running."""
        return {
            'status': 'healthy',
            'server': 'DeepResearchServer',
            'timestamp': str(time.time()),
        }

    @mcp.tool()
    async def corpus_info() -> Dict[str, Any]:
        """Return statistics and metadata about the loaded citation corpus."""
        try:
            stats = db.get_corpus_stats()
            return {
                'total_citations': stats['total_citations'],
                'year_distribution': stats['year_distribution'],
                'description': 'Systematic review citation corpus for medical/scientific literature',
                'search_capabilities': [
                    'Full‑text search in titles and abstracts',
                    'Relevance ranking',
                    'Semantic search capabilities',
                ],
            }
        except Exception as e:
            logger.error(f"Corpus info error: {e}")
            return {'error': str(e), 'total_citations': 0}

    return SyncMCPServer(mcp)


def main(port: int = 8001) -> None:
    """Entry point to start the MCP server."""
    server = create_server()
    @server._mcp.custom_route('/health', methods=['GET'])  # type: ignore
    async def health_endpoint(request):  # type: ignore
        from starlette.responses import JSONResponse  # type: ignore
        try:
            tools = await server._mcp.get_tools()
            return JSONResponse({
                'status': 'healthy',
                'server': 'DeepResearchServer',
                'timestamp': str(time.time()),
                'tools_count': len(tools),
            })
        except Exception as e:
            return JSONResponse({
                'status': 'unhealthy',
                'server': 'DeepResearchServer',
                'timestamp': str(time.time()),
                'error': str(e),
            }, status_code=500)
    # Log server info
    logger.info(f"Starting Systematic Review MCP server on 0.0.0.0:{port}")
    logger.info('Server will be accessible via SSE transport')
    logger.info(f"Health endpoint: http://0.0.0.0:{port}/health")
    logger.info(
        f"External URL: https://{os.getenv('REPL_SLUG', 'unknown')}-{port}.{os.getenv('REPL_OWNER', 'unknown')}.repl.co/sse/"
    )
    # Start server with SSE transport
    server._mcp.run(transport='sse', host='0.0.0.0', port=port)


if __name__ == '__main__':
    main()
