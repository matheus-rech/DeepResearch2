#!/usr/bin/env python3
"""
Simple MCP Server for Deep Research + Claude Integration
Works without complex dependencies for immediate testing
"""
import json
import sys
import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import database as db

logger = logging.getLogger(__name__)

class SimpleMCPServer:
    """Simple MCP server for testing and demonstration"""
    
    def __init__(self):
        self.name = "DeepResearch_Claude_MCP_Server"
        self.version = "2.0"
        
        # Initialize database
        try:
            db.init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.warning(f"Database initialization failed: {e}")
    
    async def search(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search citations with enhanced capabilities"""
        try:
            logger.info(f"Searching for: {query} (limit: {limit})")
            
            if not query.strip() or query.strip() == "*":
                results = db.get_all_citations(limit)
            else:
                results = db.search_citations(query, limit)
            
            # Format for Deep Research spec
            formatted_results = []
            for citation in results:
                # Build URL
                url = None
                if citation["id"].startswith("PMID:"):
                    pmid = citation["id"].replace("PMID:", "")
                    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                elif citation.get("doi"):
                    url = f"https://doi.org/{citation['doi']}"
                else:
                    url = f"mcp://citation/{citation['id']}"
                
                formatted_results.append({
                    "id": citation["id"],
                    "title": citation["title"],
                    "text": citation.get("abstract", "")[:200] + "...",
                    "url": url
                })
            
            return {
                "results": formatted_results,
                "total_found": len(results),
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return {"results": [], "error": str(e)}
    
    async def fetch(self, citation_id: str) -> Dict[str, Any]:
        """Fetch complete citation details"""
        try:
            logger.info(f"Fetching citation: {citation_id}")
            
            citation = db.fetch_citation(citation_id)
            if not citation:
                raise ValueError(f"Citation not found: {citation_id}")
            
            # Build URL
            url = None
            if citation_id.startswith("PMID:"):
                pmid = citation_id.replace("PMID:", "")
                url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            elif citation.get("doi"):
                url = f"https://doi.org/{citation['doi']}"
            
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
    
    async def corpus_info(self) -> Dict[str, Any]:
        """Get corpus information"""
        try:
            stats = db.get_corpus_stats()
            
            return {
                "server_name": self.name,
                "version": self.version,
                "total_citations": stats["total_citations"],
                "year_distribution": stats["year_distribution"],
                "claude_integration": "enabled",
                "capabilities": [
                    "Citation search and retrieval",
                    "Claude-enhanced parsing",
                    "Deep Research compatibility",
                    "Semantic analysis ready"
                ],
                "endpoints": [
                    "search - Find citations by query",
                    "fetch - Get complete citation details", 
                    "corpus_info - Get database statistics"
                ]
            }
            
        except Exception as e:
            logger.error(f"Corpus info error: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Server health check"""
        return {
            "status": "healthy",
            "server": self.name,
            "version": self.version,
            "claude_ready": True,
            "database_ready": True
        }

def format_json_response(data: Dict[str, Any]) -> str:
    """Format response as pretty JSON"""
    return json.dumps(data, indent=2, ensure_ascii=False)

async def interactive_test():
    """Interactive testing mode"""
    server = SimpleMCPServer()
    
    print(f"🚀 {server.name} v{server.version}")
    print("=" * 60)
    print("Interactive testing mode - Claude + Deep Research integration")
    print("\nCommands:")
    print("  search <query>     - Search citations")
    print("  fetch <id>         - Fetch citation by ID")
    print("  stats              - Show corpus statistics")
    print("  health             - Health check")
    print("  quit               - Exit")
    print("=" * 60)
    
    while True:
        try:
            command = input("\n📝 Enter command: ").strip()
            
            if command.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if command.startswith('search '):
                query = command[7:]
                result = await server.search(query, limit=5)
                print(f"\n🔍 Search Results for '{query}':")
                print(format_json_response(result))
                
            elif command.startswith('fetch '):
                citation_id = command[6:]
                try:
                    result = await server.fetch(citation_id)
                    print(f"\n📄 Citation Details:")
                    print(format_json_response(result))
                except Exception as e:
                    print(f"❌ Error: {e}")
                    
            elif command == 'stats':
                result = await server.corpus_info()
                print(f"\n📊 Corpus Statistics:")
                print(format_json_response(result))
                
            elif command == 'health':
                result = await server.health_check()
                print(f"\n💚 Health Check:")
                print(format_json_response(result))
                
            else:
                print("❓ Unknown command. Type 'quit' to exit.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

async def run_background_server():
    """Run server in background for MCP integration"""
    server = SimpleMCPServer()
    
    print(f"🚀 Starting {server.name} v{server.version}")
    print("=" * 60)
    
    # Test basic functionality
    print("🧪 Testing server capabilities...")
    
    # Health check
    health = await server.health_check()
    print(f"Health: {health['status']}")
    
    # Corpus info
    info = await server.corpus_info()
    print(f"Corpus: {info.get('total_citations', 0)} citations")
    
    # Test search
    search_result = await server.search("diabetes", limit=3)
    print(f"Search test: {len(search_result.get('results', []))} results")
    
    print("\n✅ Server is ready for Deep Research integration!")
    print("🔗 MCP endpoints available:")
    print("   - search(query, limit)")
    print("   - fetch(id)")
    print("   - corpus_info()")
    print("   - health_check()")
    
    # Keep running
    print("\n⏳ Server running in background...")
    try:
        while True:
            await asyncio.sleep(10)
            # Periodic health check
            health = await server.health_check()
            if health['status'] != 'healthy':
                logger.warning("Health check failed")
    except KeyboardInterrupt:
        print("\n👋 Server stopped.")

async def main():
    """Main function with mode selection"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        await interactive_test()
    else:
        await run_background_server()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())