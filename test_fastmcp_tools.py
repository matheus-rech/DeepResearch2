#!/usr/bin/env python3
"""
Test script to understand FastMCP tool registration
"""
import sys
import traceback

sys.path.append('sr_screener')

def test_fastmcp_registration():
    """Test FastMCP tool registration methods"""
    print("=== Testing FastMCP Tool Registration ===")
    
    try:
        from fastmcp import FastMCP
        import asyncio
        
        async def test_async_registration():
            test_server = FastMCP("Test Server")
            print("✓ FastMCP server created")
            
            tool_methods = [m for m in dir(test_server) if 'tool' in m.lower()]
            print(f"Available tool methods: {tool_methods}")
            
            tools = await test_server.get_tools()
            print(f"Initial tools: {len(tools)} tools")
            
            @test_server.tool()
            def test_tool(message: str) -> str:
                """A test tool"""
                return f"Test: {message}"
            
            tools_after = await test_server.get_tools()
            print(f"Tools after registration: {len(tools_after)} tools")
            
            if len(tools_after) > len(tools):
                print("✓ Tool registration working")
                return True
            else:
                print("✗ Tool registration failed")
                return False
        
        return asyncio.run(test_async_registration())
            
    except Exception as e:
        print(f"✗ FastMCP test failed: {e}")
        traceback.print_exc()
        return False

def test_mcp_server_tools():
    """Test the actual MCP server tool registration"""
    print("\n=== Testing Actual MCP Server Tools ===")
    
    try:
        import mcp_server
        import asyncio
        
        async def test_async_tools():
            server = mcp_server.create_server()
            print("✓ MCP server created")
            
            tools = await server.get_tools()
            print(f"Registered tools: {len(tools)} tools found")
            
            if tools and len(tools) > 0:
                print(f"✓ Found {len(tools)} registered tools")
                for tool in tools:
                    if isinstance(tool, dict):
                        print(f"  - Tool: {tool.get('name', 'unknown')}")
                    else:
                        print(f"  - Tool: {tool}")
                return True
            else:
                print("✗ No tools registered")
                return False
        
        return asyncio.run(test_async_tools())
            
    except Exception as e:
        print(f"✗ MCP server test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("FastMCP Tool Registration Test")
    print("=" * 50)
    
    success_count = 0
    total_tests = 2
    
    if test_fastmcp_registration():
        success_count += 1
        
    if test_mcp_server_tools():
        success_count += 1
    
    print(f"\n=== RESULTS: {success_count}/{total_tests} tests passed ===")
    
    if success_count == total_tests:
        print("🎉 All FastMCP tests passed!")
        sys.exit(0)
    else:
        print("❌ Some FastMCP tests failed.")
        sys.exit(1)
