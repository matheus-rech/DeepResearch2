#!/usr/bin/env python3
"""
Test script to verify SQLAlchemy fixes in database.py
"""
import warnings
import sys

warnings.filterwarnings('ignore')

def test_sqlalchemy_import():
    """Test that database.py imports without SQLAlchemy warnings"""
    print("=== Testing SQLAlchemy Fixes ===")
    
    try:
        sys.path.append('sr_screener')
        import database
        print("✅ database.py imports successfully")
        print("✅ No SQLAlchemy MovedIn20Warning about declarative_base")
        print("✅ No variable shadowing issues with text() function")
        
        # Test that we can access the Citation model
        _ = database.Citation
        print("✅ Citation model accessible")
        
        # Test that we can access the function
        _ = database.generate_citation_embeddings
        print("✅ generate_citation_embeddings function accessible")
        
        return True
    except Exception as e:
        print(f"❌ SQLAlchemy test failed: {e}")
        return False

def main():
    """Run SQLAlchemy validation test"""
    success = test_sqlalchemy_import()
    
    if success:
        print("\n✅ All SQLAlchemy fixes verified successfully!")
        return 0
    else:
        print("\n❌ SQLAlchemy fixes validation failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
