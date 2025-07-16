#!/usr/bin/env python3
"""
Production Readiness Assessment Script for DeepResearch2
Tests core functionality, environment setup, and integration capabilities
"""

import os
import sys
import asyncio
import platform
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "sr_screener"))

def test_environment_setup():
    """Test environment configuration and dependencies"""
    print("🔧 Testing Environment Setup...")
    
    required_vars = ["OPENAI_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {missing_vars}")
        return False
    
    try:
        import fastmcp
        import openai
        import streamlit
        import sqlalchemy
        print("✅ Core dependencies imported successfully")
        print(f"   - FastMCP: {fastmcp.__version__}")
        print(f"   - OpenAI: {openai.__version__}")
        print(f"   - Streamlit: {streamlit.__version__}")
        print(f"   - SQLAlchemy: {sqlalchemy.__version__}")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_database_connectivity():
    """Test database initialization and basic operations"""
    print("\n💾 Testing Database Connectivity...")
    
    try:
        import database as db
        
        # Initialize database
        db.init_db()
        print("✅ Database initialized successfully")
        
        stats = db.get_corpus_stats()
        print(f"✅ Database stats retrieved: {stats.get('total_citations', 0)} citations")
        
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_mcp_server_creation():
    """Test MCP server creation and tool registration"""
    print("\n🔧 Testing MCP Server Creation...")
    
    try:
        import mcp_server
        
        server = mcp_server.create_server()
        print("✅ MCP server created successfully")
        
        tools = asyncio.run(server.get_tools())
        expected_tools = ["search", "fetch", "health_check", "corpus_info"]
        
        tool_names = []
        for tool in tools:
            if hasattr(tool, 'name'):
                tool_names.append(tool.name)
            elif hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))
        missing_tools = [tool for tool in expected_tools if tool not in tool_names]
        
        if missing_tools:
            print(f"❌ Missing tools: {missing_tools}")
            return False
        
        print(f"✅ All required tools registered: {tool_names}")
        return True
    except Exception as e:
        print(f"❌ MCP server error: {e}")
        return False

def test_citation_parsing():
    """Test citation parsing with sample data"""
    print("\n📄 Testing Citation Parsing...")
    
    try:
        import parsers
        
        sample_file = "sample_pubmed_citations.txt"
        if not os.path.exists(sample_file):
            print(f"❌ Sample file not found: {sample_file}")
            return False
        
        with open(sample_file, 'rb') as f:
            citations = parsers.parse_pubmed_text(f)
        
        if len(citations) == 0:
            print("❌ No citations parsed from sample file")
            return False
        
        print(f"✅ Parsed {len(citations)} citations from sample file")
        
        required_fields = ["title", "abstract", "authors"]
        for i, citation in enumerate(citations.head(3).to_dict('records')):  # Check first 3
            missing_fields = [field for field in required_fields if not citation.get(field)]
            if missing_fields:
                print(f"❌ Citation {i + 1} missing fields: {missing_fields}")
                return False
        
        print("✅ Citation structure validation passed")
        return True
    except Exception as e:
        print(f"❌ Citation parsing error: {e}")
        return False

def test_vector_store_mode():
    """Test vector store mode functionality"""
    print("\n🔍 Testing Vector Store Mode...")
    
    try:
        import main
        
        server = main.create_server()
        print("✅ Vector store server created successfully")
        
        tools = asyncio.run(server.get_tools())
        tool_names = []
        for tool in tools:
            if hasattr(tool, 'name'):
                tool_names.append(tool.name)
            elif hasattr(tool, '__name__'):
                tool_names.append(tool.__name__)
            else:
                tool_names.append(str(tool))
        
        expected_tools = ["search", "fetch", "health_check"]
        missing_tools = [tool for tool in expected_tools if tool not in tool_names]
        
        if missing_tools:
            print(f"❌ Missing vector store tools: {missing_tools}")
            return False
        
        print(f"✅ Vector store tools available: {tool_names}")
        return True
    except Exception as e:
        print(f"❌ Vector store mode error: {e}")
        return False

def test_file_structure():
    """Test required file structure and permissions"""
    print("\n📁 Testing File Structure...")
    
    required_files = [
        "main.py",
        "requirements.txt",
        ".env.example",
        "README.md",
        "sr_screener/mcp_server.py",
        "sr_screener/database.py",
        "sr_screener/parsers.py",
        "sr_screener/app.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    
    print("✅ All required files present")
    
    executable_files = ["main.py"]
    for file_path in executable_files:
        if platform.system() == "Windows":
            if not (os.path.exists(file_path) and file_path.endswith(".py")):
                print(f"❌ File not executable or missing on Windows: {file_path}")
                return False
        else:
            if not os.access(file_path, os.X_OK):
                print(f"❌ File not executable on Unix-like system: {file_path}")
                return False
    
    print("✅ File permissions correct")
    return True

def main():
    """Run comprehensive production readiness assessment"""
    print("🚀 DeepResearch2 Production Readiness Assessment")
    print("=" * 50)
    
    tests = [
        ("Environment Setup", test_environment_setup),
        ("File Structure", test_file_structure),
        ("Database Connectivity", test_database_connectivity),
        ("Citation Parsing", test_citation_parsing),
        ("MCP Server Creation", test_mcp_server_creation),
        ("Vector Store Mode", test_vector_store_mode)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    print("\n" + "=" * 50)
    print("📊 ASSESSMENT SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 PRODUCTION READY - All tests passed!")
        return True
    else:
        print("⚠️  NEEDS ATTENTION - Some tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
