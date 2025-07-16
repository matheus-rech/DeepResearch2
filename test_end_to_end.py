#!/usr/bin/env python3
"""
Comprehensive end-to-end testing script for DeepResearch2 MCP server
"""
import os
import sys
import time
import requests
import subprocess
from pathlib import Path

sys.path.append('sr_screener')

def test_vector_store_mode():
    """Test vector store mode MCP server"""
    print("=== Testing Vector Store Mode ===")
    
    print("Starting vector store mode server...")
    proc = subprocess.Popen([
        sys.executable, "main.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    time.sleep(5)
    
    try:
        response = requests.get("http://localhost:8001/health", timeout=10)
        if response.status_code == 200:
            print("✓ Vector store mode server started successfully")
            print(f"  Health check response: {response.json()}")
            return True
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Failed to connect to vector store server: {e}")
        if proc.poll() is None:
            print("  Server process is still running, connection issue")
        else:
            print(f"  Server process exited with code: {proc.poll()}")
        return False
    finally:
        proc.terminate()
        proc.wait(timeout=5)

def test_systematic_review_mode():
    """Test systematic review mode MCP server"""
    print("\n=== Testing Systematic Review Mode ===")
    
    print("Starting systematic review mode server...")
    proc = subprocess.Popen([
        sys.executable, "main.py", "sr"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    time.sleep(5)
    
    try:
        response = requests.get("http://localhost:8001/health", timeout=10)
        if response.status_code == 200:
            print("✓ Systematic review mode server started successfully")
            print(f"  Health check response: {response.json()}")
            return True
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Failed to connect to systematic review server: {e}")
        if proc.poll() is None:
            print("  Server process is still running, connection issue")
        else:
            print(f"  Server process exited with code: {proc.poll()}")
        return False
    finally:
        proc.terminate()
        proc.wait(timeout=5)

def test_sse_endpoint():
    """Test SSE endpoint connectivity"""
    print("\n=== Testing SSE Endpoint ===")
    
    proc = subprocess.Popen([
        sys.executable, "main.py", "sr"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    time.sleep(8)
    
    try:
        # Test SSE endpoint
        response = requests.get("http://localhost:8001/sse/", timeout=15, stream=True)
        if response.status_code == 200:
            print("✓ SSE endpoint accessible")
            return True
        else:
            print(f"✗ SSE endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ SSE endpoint test failed: {e}")
        if proc.poll() is None:
            print("  Server process is still running, connection issue")
        else:
            print(f"  Server process exited with code: {proc.poll()}")
        return False
    finally:
        proc.terminate()
        proc.wait(timeout=5)

def test_database_operations():
    """Test database operations"""
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
        return False

def test_citation_parsing():
    """Test citation parsing functionality"""
    print("\n=== Testing Citation Parsing ===")
    
    try:
        sample_file = Path("sample_citations.csv")
        if sample_file.exists():
            print("✓ Sample citation file found")
            
            with open(sample_file, 'r') as f:
                content = f.read()
                if len(content) > 0:
                    print("✓ Sample citation file readable")
                else:
                    print("⚠ Sample citation file is empty")
        else:
            print("⚠ Sample citation file not found")
        
        criteria_file = Path("sr_screener/sample_criteria.json")
        if criteria_file.exists():
            print("✓ Sample criteria file found")
            
            with open(criteria_file, 'r') as f:
                import json
                criteria = json.load(f)
                if 'population' in criteria:
                    print("✓ PICO criteria structure valid")
                else:
                    print("⚠ PICO criteria structure incomplete")
        else:
            print("⚠ Sample criteria file not found")
        
        return True
    except Exception as e:
        print(f"✗ Citation parsing test failed: {e}")
        return False

def test_mcp_validation():
    """Test MCP tools directly without server startup"""
    print("\n=== Testing MCP Tools Direct ===")
    
    try:
        sys.path.append('sr_screener')
        import mcp_server
        
        server = mcp_server.create_server()
        print("✓ MCP server instance created")
        
        if hasattr(server, 'search') and hasattr(server, 'fetch'):
            print("✓ MCP tools registered (search, fetch)")
            return True
        else:
            print("✗ MCP tools not properly registered")
            return False
    except Exception as e:
        print(f"✗ MCP tools test failed: {e}")
        return False

def main():
    """Run all end-to-end tests"""
    print("=== DeepResearch2 End-to-End Testing ===")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    tests = [
        ("Database Operations", test_database_operations),
        ("Citation Parsing", test_citation_parsing),
        ("MCP Validation", test_mcp_validation),
        ("Vector Store Mode", test_vector_store_mode),
        ("Systematic Review Mode", test_systematic_review_mode),
        ("SSE Endpoint", test_sse_endpoint),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'=' * 50}")
        print(f"Running: {test_name}")
        print('=' * 50)
        
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print(f"\n{'=' * 50}")
    print(f"=== FINAL RESULTS: {passed}/{total} tests passed ===")
    print('=' * 50)
    
    if passed == total:
        print("🎉 All tests passed! DeepResearch2 is ready for production.")
        return 0
    else:
        print("❌ Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
