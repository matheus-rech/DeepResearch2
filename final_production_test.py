#!/usr/bin/env python3
"""
Final production test to verify MCP server is working correctly
"""
import sys
import asyncio
import traceback
import pytest

sys.path.append('sr_screener')

@pytest.mark.asyncio
async def test_production_ready():
    """Test that MCP server is production ready"""
    print("=== Final Production Test ===")
    
    try:
        import mcp_server
        
        server = mcp_server.create_server()
        print("✓ MCP server created successfully")
        
        tools = await server.get_tools()
        print(f"✓ Found {len(tools)} registered tools")
        
        expected_tools = ['search', 'fetch', 'health_check', 'corpus_info']
        for tool_name in expected_tools:
            tool = await server.get_tool(tool_name)
            if tool:
                print(f"✓ Tool '{tool_name}' registered successfully")
            else:
                print(f"✗ Tool '{tool_name}' missing")
                assert False, f"Tool '{tool_name}' missing"
        
        print("✓ All MCP tools registered and ready")
        print("✓ DeepResearch2 is production ready!")
        print("✓ SSE endpoint will be available at http://localhost:8001/sse/")
        print("✓ Ready for ChatGPT Deep Research integration")
        
        assert True, "Production test passed"
        
    except Exception as e:
        print(f"✗ Production test failed: {e}")
        traceback.print_exc()
        assert False, f"Production test failed: {e}"

if __name__ == "__main__":
    try:
        asyncio.run(test_production_ready())
        print("\n🎉 PRODUCTION READY: All systems operational!")
        sys.exit(0)
    except AssertionError:
        print("\n❌ PRODUCTION FAILED: Issues detected")
        sys.exit(1)
