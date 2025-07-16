#!/usr/bin/env python3
"""
Test Streamlit UI functionality for systematic review mode
"""
import subprocess
import time
import requests
import sys

def test_streamlit_ui():
    """Test Streamlit UI startup and basic functionality"""
    print("=== Testing Streamlit UI ===")
    
    print("Starting Streamlit UI...")
    proc = subprocess.Popen([
        sys.executable, "sr_screener/main.py", "ui"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    time.sleep(10)
    
    try:
        response = requests.get("http://localhost:8000", timeout=15)
        if response.status_code == 200:
            print("✓ Streamlit UI accessible")
            print(f"  Response length: {len(response.text)} characters")
            assert True, "Test completed successfully"
        else:
            print(f"✗ UI not accessible: {response.status_code}")
            assert False, "Test failed"
    except Exception as e:
        print(f"✗ Failed to connect to UI: {e}")
        assert False, "Test failed"
    finally:
        proc.terminate()
        proc.wait(timeout=5)

if __name__ == "__main__":
    test_streamlit_ui()
