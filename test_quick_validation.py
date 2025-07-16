#!/usr/bin/env python3
"""
Quick validation test for core functionality
"""
import sys
import os
import warnings
import logging
from pathlib import Path

os.environ["STREAMLIT_LOGGER_LEVEL"] = "ERROR"
warnings.filterwarnings("ignore", message=".*ScriptRunContext.*")
warnings.filterwarnings("ignore", message=".*Session state does not function.*")
warnings.filterwarnings("ignore", message=".*to view this Streamlit app.*")
warnings.filterwarnings("ignore", category=UserWarning, module="streamlit")

logging.getLogger("streamlit").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)

def test_imports():
    """Test that all modules can be imported"""
    print("=== Testing Module Imports ===")
    
    try:
        import main  # noqa: F401
        print("✓ main.py imports successfully")
        
        sys.path.append('sr_screener')
        
        import database  # noqa: F401
        import mcp_server  # noqa: F401
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import app  # noqa: F401
            
        print("✓ sr_screener modules import successfully")
        
        return True
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False

def test_environment():
    """Test environment configuration"""
    print("\n=== Testing Environment ===")
    
    required_vars = ['OPENAI_API_KEY', 'VECTOR_STORE_ID']
    missing = []
    
    for var in required_vars:
        if var in os.environ:
            print(f"✓ {var} configured")
        else:
            print(f"✗ {var} missing")
            missing.append(var)
    
    return len(missing) == 0

def test_files():
    """Test required files exist"""
    print("\n=== Testing File Structure ===")
    
    required_files = [
        "main.py",
        "sr_screener/main.py",
        "sr_screener/app.py",
        "sr_screener/database.py",
        "sr_screener/mcp_server.py",
        "sample_citations.csv",
        "sr_screener/sample_criteria.json"
    ]
    
    missing = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} missing")
            missing.append(file_path)
    
    return len(missing) == 0

def main():
    """Run quick validation tests"""
    print("=== DeepResearch2 Quick Validation ===")
    
    tests = [
        ("Module Imports", test_imports),
        ("Environment", test_environment),
        ("File Structure", test_files),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED\n")
            else:
                print(f"✗ {test_name} FAILED\n")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}\n")
    
    print(f"=== QUICK VALIDATION: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("✅ Core functionality validated!")
        return 0
    else:
        print("❌ Some validation checks failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
