#!/usr/bin/env python3
"""
Test MCP tools functionality directly
"""
import sys
import asyncio
sys.path.append('sr_screener')

async def test_mcp_tools():
    """Test MCP tools directly"""
    print("=== Testing MCP Tools ===")
    
    try:
        from mcp_server import create_server
        
        server = create_server()
        print("✓ MCP server created successfully")
        
        search_result = await server.search("test query", limit=5)
        print(f"✓ Search tool executed: {len(search_result.get('results', []))} results")
        
        health_result = await server.health_check()
        print(f"✓ Health check executed: {health_result.get('status', 'unknown')}")
        
        corpus_result = await server.corpus_info()
        print(f"✓ Corpus info executed: {corpus_result.get('total_citations', 0)} citations")
        
        return True
    except Exception as e:
        print(f"✗ MCP tools test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())
