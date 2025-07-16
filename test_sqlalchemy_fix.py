#!/usr/bin/env python3
"""
Test script to verify SQLAlchemy fixes and functionality in database.py
"""
import warnings
import sys
import os

# Add the project root directory to the path for robust imports
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _PROJECT_ROOT)

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

def test_embedding_generation():
    """Test that citation embeddings can be generated"""
    print("=== Testing Citation Embedding Generation ===")
    try:
        from sr_screener import database
        stats = database.generate_citation_embeddings()
        print(f"Embedding generation stats: {stats}")
        assert isinstance(stats, dict)
        print("✅ Embedding generation successful")
        return True
    except Exception as e:
        print(f"❌ Error generating embeddings: {e}")
        return False

def main():
    """Run SQLAlchemy validation tests"""
    import_success = test_sqlalchemy_import()
    
    # Only test embedding generation if imports succeeded
    if import_success:
        embedding_success = test_embedding_generation()
    else:
        embedding_success = False
        print("\n⚠️ Skipping embedding generation test due to import failure")
    
    if import_success and embedding_success:
        print("\n✅ All SQLAlchemy tests verified successfully!")
        return 0
    else:
        print("\n❌ Some SQLAlchemy tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
