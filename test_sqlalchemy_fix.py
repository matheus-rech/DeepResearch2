"""
Test file for SQLAlchemy fix
"""
import os
import sys

# Add the sr_screener directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'sr_screener'))

from database import generate_citation_embeddings

def test_embedding_generation():
    """Test that citation embeddings can be generated"""
    try:
        stats = database.generate_citation_embeddings()
        print(f"Embedding generation stats: {stats}")
        assert isinstance(stats, dict)
        return True
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return False

if __name__ == "__main__":
    success = test_embedding_generation()
    print(f"Test result: {'PASS' if success else 'FAIL'}")