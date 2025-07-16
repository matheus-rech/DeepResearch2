#!/usr/bin/env python3
"""
Enhanced MCP Server for Systematic Review with Claude Integration
Provides search and fetch tools for Deep Research + Claude intelligent analysis
"""
import os
import sys
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the current directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool, 
        TextContent,
        CallToolResult,
        ListToolsResult
    )
except ImportError:
    # Fallback for basic MCP functionality
    print("Warning: MCP library not found. Running in compatibility mode.")
    
import database as db
from claude_integration import ClaudeScreener
from enhanced_parsers import EnhancedCitationParser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClaudeMCPServer:
    """Enhanced MCP Server with Claude intelligence"""
    
    def __init__(self):
        self.server_name = "Claude_Enhanced_Systematic_Review_MCP"
        self.version = "2.0.0"
        self.claude_screener = ClaudeScreener()
        self.citation_parser = EnhancedCitationParser()
        
        # Initialize database
        db.init_db()
        
        # Server instructions
        self.instructions = """
        Enhanced MCP server for systematic review screening with Claude AI integration.
        
        This server provides:
        1. Intelligent citation search with semantic understanding
        2. Claude-powered citation analysis and screening
        3. PICOTT criteria validation
        4. Detailed reasoning for inclusion/exclusion decisions
        5. Quality assessment and validation
        
        Use 'search' to find relevant citations, 'claude_screen' for AI-powered analysis,
        and 'validate_criteria' to check PICOTT criteria completeness.
        """
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return available tools"""
        return [
            {
                "name": "search",
                "description": "Search citations in the corpus with optional semantic analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (natural language supported)"
                        },
                        "limit": {
                            "type": "integer", 
                            "description": "Maximum results to return",
                            "default": 10
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["fulltext", "semantic", "claude"],
                            "description": "Search mode: fulltext, semantic, or claude-enhanced",
                            "default": "claude"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "fetch",
                "description": "Retrieve complete citation details by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Citation ID to fetch"
                        }
                    },
                    "required": ["id"]
                }
            },
            {
                "name": "claude_screen",
                "description": "Use Claude AI to screen citations against PICOTT criteria",
                "inputSchema": {
                    "type": "object", 
                    "properties": {
                        "citations": {
                            "type": "array",
                            "description": "List of citation IDs or objects to screen"
                        },
                        "criteria": {
                            "type": "object",
                            "description": "PICOTT criteria for screening",
                            "properties": {
                                "population": {"type": "string"},
                                "intervention": {"type": "string"},
                                "comparison": {"type": "string"},
                                "outcomes": {"type": "string"},
                                "timeframe": {"type": "string"},
                                "study_types": {"type": "string"}
                            }
                        }
                    },
                    "required": ["citations", "criteria"]
                }
            },
            {
                "name": "validate_criteria",
                "description": "Validate PICOTT criteria with Claude",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "criteria": {
                            "type": "object",
                            "description": "PICOTT criteria to validate"
                        }
                    },
                    "required": ["criteria"]
                }
            },
            {
                "name": "corpus_stats",
                "description": "Get corpus statistics and information",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    
    async def handle_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle search requests with Claude enhancement"""
        try:
            query = arguments.get("query", "")
            limit = arguments.get("limit", 10)
            mode = arguments.get("mode", "claude")
            
            if not query.strip() or query.strip() == "*":
                # Return all citations
                results = db.get_all_citations(limit)
            else:
                if mode == "claude":
                    # Use Claude-enhanced search
                    results = await self._claude_enhanced_search(query, limit)
                elif mode == "semantic":
                    results = db.semantic_search_citations(query, limit)
                else:
                    results = db.search_citations(query, limit)
            
            # Format results for Deep Research
            formatted_results = []
            for citation in results:
                url = self._build_citation_url(citation)
                formatted_results.append({
                    "id": citation["id"],
                    "title": citation["title"],
                    "text": citation.get("abstract", "")[:300] + "...",
                    "url": url,
                    "relevance_score": citation.get("relevance_score", 0.0)
                })
            
            return {"results": formatted_results}
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"results": [], "error": str(e)}
    
    async def handle_fetch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle fetch requests"""
        try:
            citation_id = arguments.get("id")
            citation = db.fetch_citation(citation_id)
            
            if not citation:
                raise ValueError(f"Citation not found: {citation_id}")
            
            url = self._build_citation_url(citation)
            
            return {
                "id": citation["id"],
                "title": citation["title"],
                "text": citation.get("abstract", ""),
                "url": url,
                "metadata": {
                    "authors": citation.get("authors", []),
                    "year": citation.get("year"),
                    "journal": citation.get("journal", ""),
                    "doi": citation.get("doi", ""),
                    "mesh_terms": citation.get("mesh_terms", []),
                    "keywords": citation.get("keywords", [])
                }
            }
            
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            raise ValueError(f"Error fetching citation: {str(e)}")
    
    async def handle_claude_screen(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Claude screening requests"""
        try:
            citation_ids = arguments.get("citations", [])
            criteria = arguments.get("criteria", {})
            
            # Fetch full citations
            citations = []
            for cid in citation_ids:
                if isinstance(cid, str):
                    citation = db.fetch_citation(cid)
                    if citation:
                        citations.append(citation)
                else:
                    citations.append(cid)
            
            # Screen with Claude
            screening_results = await self.claude_screener.screen_citations_batch(citations, criteria)
            
            return {
                "screening_results": screening_results,
                "total_screened": len(citations),
                "included": sum(1 for r in screening_results if r.get("decision") == "include"),
                "excluded": sum(1 for r in screening_results if r.get("decision") == "exclude")
            }
            
        except Exception as e:
            logger.error(f"Claude screening error: {e}")
            return {"error": str(e)}
    
    async def handle_validate_criteria(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle criteria validation requests"""
        try:
            criteria = arguments.get("criteria", {})
            
            # Use Claude to validate criteria
            validation = await self.claude_screener.validate_screening_criteria(criteria)
            
            return validation
            
        except Exception as e:
            logger.error(f"Criteria validation error: {e}")
            return {"error": str(e)}
    
    async def handle_corpus_stats(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle corpus statistics requests"""
        try:
            stats = db.get_corpus_stats()
            
            return {
                "total_citations": stats["total_citations"],
                "year_distribution": stats["year_distribution"],
                "server_version": self.version,
                "claude_integration": "enabled",
                "capabilities": [
                    "Claude-enhanced search",
                    "Intelligent screening",
                    "PICOTT criteria validation",
                    "Semantic analysis",
                    "Quality assessment"
                ]
            }
            
        except Exception as e:
            logger.error(f"Corpus stats error: {e}")
            return {"error": str(e)}
    
    def _build_citation_url(self, citation: Dict[str, Any]) -> Optional[str]:
        """Build URL for citation"""
        if citation["id"].startswith("PMID:"):
            pmid = citation["id"].replace("PMID:", "")
            return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        elif citation.get("doi"):
            return f"https://doi.org/{citation['doi']}"
        else:
            return f"mcp://citation/{citation['id']}"
    
    async def _claude_enhanced_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Enhanced search using Claude intelligence"""
        try:
            # Get initial results
            initial_results = db.search_citations(query, limit * 2)  # Get more for filtering
            
            # Use Claude to enhance relevance scoring
            enhanced_results = []
            for citation in initial_results[:limit]:
                # Add Claude relevance analysis
                relevance = await self.claude_screener.analyze_relevance(citation, query)
                citation["relevance_score"] = relevance.get("score", 0.0)
                citation["relevance_reasoning"] = relevance.get("reasoning", "")
                enhanced_results.append(citation)
            
            # Sort by Claude relevance scores
            enhanced_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Claude-enhanced search error: {e}")
            # Fallback to regular search
            return db.search_citations(query, limit)

# Standalone server function for testing
async def run_test_server():
    """Run server for testing without MCP protocol"""
    server = ClaudeMCPServer()
    
    print(f"🚀 {server.server_name} v{server.version}")
    print("=" * 60)
    print(server.instructions)
    print("\n📋 Available Tools:")
    
    tools = server.get_tools()
    for tool in tools:
        print(f"  • {tool['name']}: {tool['description']}")
    
    print("\n✅ Server ready for testing!")
    
    # Test search functionality
    print("\n🔍 Testing search...")
    search_result = await server.handle_search({
        "query": "diabetes glucose monitoring",
        "limit": 3,
        "mode": "claude"
    })
    
    print(f"Found {len(search_result.get('results', []))} citations")
    if search_result.get('results'):
        for result in search_result['results'][:2]:
            print(f"  • {result['title'][:60]}...")
    
    # Test corpus stats
    print("\n📊 Testing corpus stats...")
    stats = await server.handle_corpus_stats({})
    print(f"Corpus: {stats.get('total_citations', 0)} citations")
    print(f"Claude integration: {stats.get('claude_integration', 'unknown')}")
    
    return server

# MCP protocol server (if mcp library available)
def create_mcp_server():
    """Create MCP protocol server"""
    try:
        from mcp.server import Server
        from mcp.types import Tool
        
        server = Server(name="claude-enhanced-systematic-review")
        claude_server = ClaudeMCPServer()
        
        @server.list_tools()
        async def list_tools() -> ListToolsResult:
            tools = claude_server.get_tools()
            mcp_tools = []
            
            for tool in tools:
                mcp_tools.append(Tool(
                    name=tool["name"],
                    description=tool["description"],
                    inputSchema=tool["inputSchema"]
                ))
            
            return ListToolsResult(tools=mcp_tools)
        
        @server.call_tool()
        async def call_tool(name: str, arguments: dict) -> CallToolResult:
            try:
                if name == "search":
                    result = await claude_server.handle_search(arguments)
                elif name == "fetch":
                    result = await claude_server.handle_fetch(arguments)
                elif name == "claude_screen":
                    result = await claude_server.handle_claude_screen(arguments)
                elif name == "validate_criteria":
                    result = await claude_server.handle_validate_criteria(arguments)
                elif name == "corpus_stats":
                    result = await claude_server.handle_corpus_stats(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return CallToolResult(
                    content=[TextContent(type="text", text=json.dumps(result, indent=2))]
                )
                
            except Exception as e:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")]
                )
        
        return server
        
    except ImportError:
        logger.warning("MCP library not available. Use test server mode.")
        return None

async def main():
    """Main function"""
    try:
        # Try to create MCP server
        mcp_server = create_mcp_server()
        
        if mcp_server:
            print("🚀 Starting Claude-Enhanced MCP Server...")
            await stdio_server(mcp_server)
        else:
            print("🧪 Running in test mode...")
            await run_test_server()
            
            # Keep server running
            print("\n⏳ Server running. Press Ctrl+C to stop.")
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n👋 Server stopped.")
                
    except Exception as e:
        logger.error(f"Server error: {e}")
        print(f"❌ Server failed to start: {e}")

if __name__ == "__main__":
    asyncio.run(main())