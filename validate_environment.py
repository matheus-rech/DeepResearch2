#!/usr/bin/env python3
"""
Environment validation script for DeepResearch2
Validates required environment variables, connections, and provides helpful error messages
"""

import os
import sys
import logging
from typing import List, Tuple, Dict, Any

# Set up logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)s: %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Define required ports
REQUIRED_PORTS = [8000, 8001]  # Default ports for Streamlit and MCP

def validate_database_connection() -> Tuple[bool, str]:
    """Check if database connection is available by attempting to connect."""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        return False, "DATABASE_URL not set - using SQLite database"
    
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.exc import SQLAlchemyError
        engine = create_engine(database_url)
        with engine.connect():
            # Connection is implicitly checked by entering the 'with' block
            pass
        return True, "Database connection successful"
    except ImportError:
        return False, "SQLAlchemy is not installed. Cannot validate database connection."
    except SQLAlchemyError as e:
        return False, f"Database validation failed: {e}"

def validate_openai_key() -> Tuple[bool, List[str], List[str]]:
    """Check if OpenAI API keys are available and valid"""
    errors = []
    warnings = []
    
    # Primary OpenAI key
    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        errors.append("OPENAI_API_KEY is required for all modes")
    elif openai_key == "your_openai_api_key_here":
        errors.append("OPENAI_API_KEY contains placeholder value - please set your actual API key")
    
    # Secondary OpenAI key (optional)
    openai_key_2 = os.environ.get("OPENAI_API_KEY_2")
    if openai_key_2 and openai_key_2 == "your_secondary_openai_api_key_here":
        warnings.append("OPENAI_API_KEY_2 contains placeholder value")
    
    is_valid = len(errors) == 0
    return is_valid, errors, warnings

def check_vector_store() -> List[str]:
    """Check vector store configuration"""
    warnings = []
    
    vector_store_id = os.environ.get("VECTOR_STORE_ID")
    if not vector_store_id:
        warnings.append("VECTOR_STORE_ID not set - vector store mode will use fallback ID")
    elif vector_store_id == "your_vector_store_id_here":
        warnings.append("VECTOR_STORE_ID contains placeholder value - vector store mode may not work correctly")
    
    return warnings

def check_required_ports() -> Tuple[List[int], List[str], List[str]]:
    """Check if required ports are available and properly configured."""
    import socket
    
    errors = []
    warnings = []
    available_ports = []
    
    # Check port configuration
    mcp_port = os.environ.get("MCP_PORT", "8001")
    streamlit_port = os.environ.get("STREAMLIT_PORT", "8000")
    
    try:
        mcp_port_int = int(mcp_port)
        streamlit_port_int = int(streamlit_port)
        if mcp_port_int == streamlit_port_int:
            errors.append(f"MCP_PORT ({mcp_port}) and STREAMLIT_PORT ({streamlit_port}) cannot be the same")
    except ValueError:
        errors.append(f"Invalid port value: MCP_PORT ({mcp_port}) or STREAMLIT_PORT ({streamlit_port}) is not a valid integer")
        return [], errors, warnings
    
    # Check port availability
    required_ports = [mcp_port_int, streamlit_port_int]
    
    for port in required_ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                # If a port is in use, bind() will raise an OSError
                s.bind(("127.0.0.1", port))
                available_ports.append(port)
            except OSError:
                warnings.append(f"Port {port} is already in use and not available")
    
    return available_ports, errors, warnings

def check_environment() -> Tuple[bool, List[str], List[str]]:
    """
    Check environment configuration for DeepResearch2
    
    Returns:
        Tuple of (is_valid, errors, warnings)
    """
    all_errors = []
    all_warnings = []
    
    # Check OpenAI API keys
    openai_valid, openai_errors, openai_warnings = validate_openai_key()
    all_errors.extend(openai_errors)
    all_warnings.extend(openai_warnings)
    
    # Check vector store configuration
    vector_warnings = check_vector_store()
    all_warnings.extend(vector_warnings)
    
    # Check ports
    available_ports, port_errors, port_warnings = check_required_ports()
    all_errors.extend(port_errors)
    all_warnings.extend(port_warnings)
    
    # Check database connection
    db_ok, db_message = validate_database_connection()
    if not db_ok:
        all_warnings.append(db_message)
    
    is_valid = len(all_errors) == 0
    return is_valid, all_errors, all_warnings

def generate_environment_report() -> Dict[str, Any]:
    """Generate comprehensive environment validation report"""
    is_valid, errors, warnings = check_environment()
    
    # Database check
    db_ok, db_message = validate_database_connection()
    
    # OpenAI key check
    openai_valid, _, _ = validate_openai_key()
    
    # Port availability
    available_ports, _, _ = check_required_ports()
    
    report = {
        "valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "details": {
            "database_ok": db_ok,
            "openai_ok": openai_valid,
            "available_ports": available_ports,
        }
    }
    
    return report

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
    
    # Print detailed status
    report = generate_environment_report()
    details = report["details"]
    
    print("\n=== Detailed Status ===")
    print(f"Database: {'✅' if details['database_ok'] else '⚠️'}")
    print(f"OpenAI API: {'✅' if details['openai_ok'] else '❌'}")
    print(f"Available ports: {len(details['available_ports'])}/{len(REQUIRED_PORTS)}")
    
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
        is_valid, _, _ = check_environment()
        sys.exit(0 if is_valid else 1)
    elif len(sys.argv) > 1 and sys.argv[1] == "--report":
        report = generate_environment_report()
        print(report)
        sys.exit(0 if report["valid"] else 1)
    else:
        is_valid = print_environment_status()
        sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()
