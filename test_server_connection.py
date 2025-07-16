#!/usr/bin/env python3
# Test script to verify MCP server connectivity
"""
Test script to verify MCP server connectivity
"""
import requests
import os

def test_mcp_server():
    """Test if the MCP server is accessible"""
    
    # Construct the server URL
    if os.getenv("REPL_SLUG") and os.getenv("REPL_OWNER"):
        repl_slug = os.getenv("REPL_SLUG")
        repl_owner = os.getenv("REPL_OWNER")
        base_url = f"https://{repl_slug}-8001.{repl_owner}.repl.co"
    else:
        base_url = "http://localhost:8001"
    
    sse_url = f"{base_url}/sse/"
    
    print(f"Testing MCP server at: {sse_url}")
    
    try:
        # Test basic connectivity
        response = requests.get(base_url, timeout=10)
        print(f"Base URL status: {response.status_code}")
        
        # Test SSE endpoint
        response = requests.get(sse_url, timeout=10)
        print(f"SSE endpoint status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ MCP server is accessible!")
            assert True, "Test completed successfully"
        else:
            print(f"❌ MCP server returned status {response.status_code}")
            print(f"Response: {response.text[:200]}")
            assert False, "Test failed"
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {e}")
        assert False, "Test failed"

if __name__ == "__main__":
    test_mcp_server()
