#!/usr/bin/env python3
"""
Production readiness test for DeepResearch2
"""
import os
import sys
import subprocess
import time
import requests
from pathlib import Path

def check_environment():
    """Check environment configuration"""
    print("=== Environment Check ===")
    
    required_vars = ['OPENAI_API_KEY', 'VECTOR_STORE_ID']
    optional_vars = ['OPENAI_API_KEY_2', 'DATABASE_URL']
    
    for var in required_vars:
        if var in os.environ:
            print(f"✓ {var} configured")
        else:
            print(f"✗ {var} missing")
            return False
    
    for var in optional_vars:
        if var in os.environ:
            print(f"✓ {var} configured (optional)")
        else:
            print(f"⚠ {var} not configured (optional)")
    
    return True

def test_production_startup():
    """Test production startup sequence"""
    print("\n=== Production Startup Test ===")
    
    print("Testing dual-mode startup...")
    proc = subprocess.Popen([
        sys.executable, "sr_screener/main.py", "both"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    time.sleep(15)
    
    try:
        mcp_response = requests.get("http://localhost:8001/health", timeout=10)
        mcp_ok = mcp_response.status_code == 200
        
        ui_response = requests.get("http://localhost:8000", timeout=10)
        ui_ok = ui_response.status_code == 200
        
        if mcp_ok and ui_ok:
            print("✓ Both services started successfully")
            print(f"  MCP Server: {mcp_response.json().get('status', 'unknown')}")
            print(f"  Streamlit UI: {len(ui_response.text)} characters")
            return True
        else:
            print(f"✗ Service startup failed - MCP: {mcp_ok}, UI: {ui_ok}")
            return False
            
    except Exception as e:
        print(f"✗ Production startup test failed: {e}")
        return False
    finally:
        proc.terminate()
        proc.wait(timeout=10)

def test_file_structure():
    """Test required file structure"""
    print("\n=== File Structure Check ===")
    
    required_files = [
        "main.py",
        "sr_screener/main.py",
        "sr_screener/app.py",
        "sr_screener/database.py",
        "sr_screener/mcp_server.py",
        ".env.example",
        "DEPLOYMENT.md",
        "README.md"
    ]
    
    all_present = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} missing")
            all_present = False
    
    return all_present

def main():
    """Run production readiness tests"""
    print("=== DeepResearch2 Production Readiness Test ===")
    
    tests = [
        ("Environment Configuration", check_environment),
        ("File Structure", test_file_structure),
        ("Production Startup", test_production_startup),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print(f"\n{'='*50}")
    print(f"=== PRODUCTION READINESS: {passed}/{total} tests passed ===")
    print('='*50)
    
    if passed == total:
        print("🚀 DeepResearch2 is production ready!")
        return 0
    else:
        print("⚠️ Some production readiness checks failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
