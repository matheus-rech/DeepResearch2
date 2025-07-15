#!/usr/bin/env python3
"""
Debug script to test MCP server tool registration
"""
import sys
import traceback

sys.path.append('sr_screener')

def test_mcp_server_creation():
    """Test MCP server creation and tool registration"""
    print("=== Testing MCP Server Creation ===")
    
    try:
        import mcp_server
        print("✓ Successfully imported mcp_server module")
        
        server = mcp_server.create_server()
        print("✓ MCP server instance created successfully")
        
        print(f"Server type: {type(server)}")
        print(f"Available attributes: {[attr for attr in dir(server) if not attr.startswith('_')]}")
        
        if hasattr(server, '_tools'):
            print(f"✓ Server has _tools attribute: {len(server._tools)} tools registered")
            for tool_name in server._tools.keys():
                print(f"  - Tool: {tool_name}")
        else:
            print("✗ Server missing _tools attribute")
            
        if hasattr(server, 'search') and hasattr(server, 'fetch'):
            print("✓ MCP tools registered (search, fetch)")
            return True
        else:
            print("✗ MCP tools not properly registered")
            return False
            
    except Exception as e:
        print(f"✗ MCP server creation failed: {e}")
        traceback.print_exc()
        return False

def test_database_operations():
    """Test basic database operations"""
    print("\n=== Testing Database Operations ===")
    
    try:
        import database as db
        
        db.init_db()
        print("✓ Database initialization successful")
        
        results = db.search_citations("test", limit=5)
        print(f"✓ Citation search successful, found {len(results)} results")
        
        stats = db.get_corpus_stats()
        print(f"✓ Corpus stats retrieved: {stats}")
        
        return True
    except Exception as e:
        print(f"✗ Database operations failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("DeepResearch2 MCP Tools Debug Script")
    print("=" * 50)
    
    success_count = 0
    total_tests = 2
    
    if test_database_operations():
        success_count += 1
        
    if test_mcp_server_creation():
        success_count += 1
    
    print(f"\n=== RESULTS: {success_count}/{total_tests} tests passed ===")
    
    if success_count == total_tests:
        print("🎉 All debug tests passed!")
        sys.exit(0)
    else:
        print("❌ Some debug tests failed.")
        sys.exit(1)
