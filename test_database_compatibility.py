#!/usr/bin/env python3
"""
Test script to verify database compatibility fixes
"""
import os
import sys
sys.path.append('sr_screener')

import database as db
import pandas as pd

def test_database_init():
    """Test database initialization with SQLite"""
    print("Testing database initialization...")
    try:
        db.init_db()
        print("✓ Database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return False

def test_citation_insertion():
    """Test citation insertion with sample data"""
    print("Testing citation insertion...")
    try:
        sample_data = pd.DataFrame([
            {
                'id': 'TEST001',
                'title': 'Test Citation Title',
                'abstract': 'This is a test abstract for database compatibility testing.',
                'year': 2024,
                'authors': ['Test Author'],
                'journal': 'Test Journal',
                'doi': '10.1234/test',
                'mesh_terms': ['test', 'database'],
                'keywords': ['testing', 'compatibility'],
                'raw_data': {'source': 'test'}
            }
        ])
        
        stats = db.bulk_insert_citations(sample_data)
        print(f"✓ Citation insertion successful: {stats}")
        return True
    except Exception as e:
        print(f"✗ Citation insertion failed: {e}")
        return False

def test_search_functionality():
    """Test search functionality"""
    print("Testing search functionality...")
    try:
        results = db.search_citations("test", limit=5)
        print(f"✓ Search successful, found {len(results)} results")
        return True
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return False

def test_embedding_generation():
    """Test embedding generation if OpenAI client is available"""
    print("Testing embedding generation...")
    try:
        if db.openai_client:
            embedding = db.generate_embedding("test text")
            if embedding:
                print("✓ Embedding generation successful")
                return True
            else:
                print("⚠ Embedding generation returned None (API issue?)")
                return False
        else:
            print("⚠ OpenAI client not available, skipping embedding test")
            return True
    except Exception as e:
        print(f"✗ Embedding generation failed: {e}")
        return False

def main():
    """Run all database compatibility tests"""
    print("=== Database Compatibility Test ===")
    
    tests = [
        test_database_init,
        test_citation_insertion,
        test_search_functionality,
        test_embedding_generation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"=== Results: {passed}/{total} tests passed ===")
    
    if passed == total:
        print("✓ All database compatibility tests passed!")
        return 0
    else:
        print("✗ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
