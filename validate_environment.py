#!/usr/bin/env python3
"""
Environment validation script for DeepResearch2
Validates required environment variables and provides helpful error messages
"""

import os
import sys
from typing import Dict, List, Tuple

def check_environment() -> Tuple[bool, List[str], List[str]]:
    """
    Check environment configuration for DeepResearch2
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    errors = []
    warnings = []
    
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        errors.append("OPENAI_API_KEY is required for all modes")
    elif openai_key == "your_openai_api_key_here":
        errors.append("OPENAI_API_KEY contains placeholder value - please set your actual API key")
    
    vector_store_id = os.environ.get("VECTOR_STORE_ID")
    if not vector_store_id:
        warnings.append("VECTOR_STORE_ID not set - vector store mode will use fallback ID")
    elif vector_store_id == "your_vector_store_id_here":
        warnings.append("VECTOR_STORE_ID contains placeholder value - vector store mode may not work correctly")
    
    openai_key_2 = os.environ.get("OPENAI_API_KEY_2")
    if openai_key_2 and openai_key_2 == "your_secondary_openai_api_key_here":
        warnings.append("OPENAI_API_KEY_2 contains placeholder value")
    
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        warnings.append("DATABASE_URL not set - using SQLite database")
    
    mcp_host = os.environ.get("MCP_HOST", "0.0.0.0")
    mcp_port = os.environ.get("MCP_PORT", "8001")
    streamlit_host = os.environ.get("STREAMLIT_HOST", "0.0.0.0")
    streamlit_port = os.environ.get("STREAMLIT_PORT", "8000")
    
    try:
        mcp_port_int = int(mcp_port)
        streamlit_port_int = int(streamlit_port)
        if mcp_port_int == streamlit_port_int:
            errors.append(f"MCP_PORT ({mcp_port}) and STREAMLIT_PORT ({streamlit_port}) cannot be the same")
    except ValueError:
        errors.append(f"Invalid port value: MCP_PORT ({mcp_port}) or STREAMLIT_PORT ({streamlit_port}) is not a valid integer")
    
    is_valid = len(errors) == 0
    return is_valid, errors, warnings

def print_environment_status():
    """Print environment validation results"""
    print("=== DeepResearch2 Environment Validation ===")
    
    is_valid, errors, warnings = check_environment()
    
    if errors:
        print("\n❌ ERRORS (must be fixed):")
        for error in errors:
            print(f"  • {error}")
    
    if warnings:
        print("\n⚠️  WARNINGS (recommended to fix):")
        for warning in warnings:
            print(f"  • {warning}")
    
    if is_valid:
        print("\n✅ Environment validation passed!")
        print("\nAvailable modes:")
        print("  • python main.py vector    # Vector store mode")
        print("  • python main.py sr        # Systematic review mode")
        print("  • python main.py sr-ui     # Systematic review with UI")
    else:
        print(f"\n❌ Environment validation failed with {len(errors)} error(s)")
        print("\nTo fix:")
        print("  1. Copy .env.example to .env")
        print("  2. Fill in your actual API keys and configuration")
        print("  3. Run this script again to validate")
    
    return is_valid

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--check-only":
        is_valid, errors, warnings = check_environment()
        sys.exit(0 if is_valid else 1)
    else:
        is_valid = print_environment_status()
        sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()
