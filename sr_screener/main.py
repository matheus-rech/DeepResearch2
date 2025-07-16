#!/usr/bin/env python3
"""
Main entry point for Systematic Review Screener
Can run either the MCP server or Streamlit UI
"""
import sys
import subprocess
from pathlib import Path

# Add the sr_screener directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


def run_mcp_server():
    """Start the MCP server."""
    print("Starting MCP server on http://0.0.0.0:8001/sse/")
    print("This server provides search/fetch tools for Deep Research integration")
    print("Press Ctrl+C to stop")
    
    import mcp_server
    mcp_server.main(port=8001)


def run_streamlit_app():
    """Start the Streamlit UI."""
    print("Starting Streamlit app on port 8000...")
    app_path = Path(__file__).parent / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path), 
                   "--server.port", "8000", "--server.address", "0.0.0.0"])


def run_both():
    """Run both MCP server and Streamlit app."""
    import threading
    import time
    
    # Start MCP server in a thread (on port 8001 - internal access)
    mcp_thread = threading.Thread(target=run_mcp_server, daemon=True)
    mcp_thread.start()
    
    # Give MCP server time to start
    time.sleep(2)
    
    # Run Streamlit in main thread (on port 8000 - main web port)
    run_streamlit_app()


def main():
    """Main entry point with command line argument handling."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "mcp":
            run_mcp_server()
        elif command == "ui":
            run_streamlit_app()
        elif command == "both":
            run_both()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python main.py [mcp|ui|both]")
            sys.exit(1)
    else:
        # Default: run both
        print("Starting Systematic Review Screener")
        print("Running both MCP server and Streamlit UI...")
        run_both()


if __name__ == "__main__":
    main()