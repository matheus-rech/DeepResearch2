#!/usr/bin/env python3
"""
Script to run end-to-end tests with proper setup
"""
import sys
import subprocess
from pathlib import Path

# Add sr_screener to path
sys.path.insert(0, 'sr_screener')

def setup_environment():
    """Setup test environment"""
    print("Setting up test environment...")
    
    # Create necessary directories
    Path("e2e_screenshots").mkdir(exist_ok=True)
    
    # Initialize database
    print("Initializing database...")
    try:
        import sr_screener.database as db
        db.init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
        print("Tests will continue with SQLite fallback")
    
    # Check if servers are already running
    import requests
    try:
        resp = requests.get("http://localhost:8000", timeout=2)
        if resp.status_code == 200:
            print("Warning: Streamlit server already running on port 8000")
            return False
    except Exception:
        pass
    
    return True

def main():
    """Run the E2E tests"""
    print("=== DeepResearch2 End-to-End Tests ===")
    
    # Setup environment
    setup_environment()
    
    # Run the tests
    print("\nRunning Playwright E2E tests...")
    result = subprocess.run(
        [sys.executable, "test_e2e_playwright.py"],
        capture_output=False
    )
    
    print(f"\nTests completed with exit code: {result.returncode}")
    
    # Show results location
    print("\n=== Test Results ===")
    print("Screenshots: ./e2e_screenshots/")
    print("Test report: ./e2e_test_report.html")
    print("Test logs: ./e2e_test_log.txt")
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())