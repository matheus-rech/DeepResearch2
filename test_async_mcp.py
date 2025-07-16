#!/usr/bin/env python3
"""
Async test script for FastMCP tool registration
"""
import sys
import asyncio
import traceback
import pytest

sys.path.append('sr_screener')

@pytest.mark.asyncio
async def test_mcp_server_async():
    """Test MCP server tool registration with proper async handling"""
    print("=== Testing MCP Server Tools (Async) ===")
    
    try:
        import mcp_server
        
        server = mcp_server.create_server()
        print("✓ MCP server created")
        
        tools = await server.get_tools()
        print(f"Registered tools: {len(tools)} tools found")
        
        if tools and len(tools) > 0:
            print(f"✓ Found {len(tools)} registered tools")
            for tool in tools:
                tool_name = tool.get('name', 'unknown')
                tool_desc = tool.get('description', 'No description')[:100]
                print(f"  - Tool: {tool_name}")
                print(f"    Description: {tool_desc}...")
            return True
        else:
            print("✗ No tools registered")
            return False
            
    except Exception as e:
        print(f"✗ MCP server test failed: {e}")
        traceback.print_exc()
        return False

@pytest.mark.asyncio
async def test_tool_functionality():
    """Test actual tool functionality"""
    print("\n=== Testing Tool Functionality ===")
    
    try:
        import mcp_server
        
        server = mcp_server.create_server()
        
        health_result = await server.get_tool('health_check')
        if health_result:
            print("✓ Health check tool found")
        else:
            print("✗ Health check tool not found")
            
        search_result = await server.get_tool('search')
        if search_result:
            print("✓ Search tool found")
        else:
            print("✗ Search tool not found")
            
        fetch_result = await server.get_tool('fetch')
        if fetch_result:
            print("✓ Fetch tool found")
        else:
            print("✗ Fetch tool not found")
            
        return True
        
    except Exception as e:
        print(f"✗ Tool functionality test failed: {e}")
        traceback.print_exc()
        return False

async def main():
    """Run all async tests"""
    print("FastMCP Async Tool Test")
    print("=" * 50)
    
    success_count = 0
    total_tests = 2
    
    if await test_mcp_server_async():
        success_count += 1
        
    if await test_tool_functionality():
        success_count += 1
    
    print(f"\n=== RESULTS: {success_count}/{total_tests} tests passed ===")
    
    if success_count == total_tests:
        print("🎉 All async MCP tests passed!")
        return 0
    else:
        print("❌ Some async MCP tests failed.")
        return 1

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(result)
