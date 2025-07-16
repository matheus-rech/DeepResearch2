"""
Test file for SQLAlchemy fix
"""
import os
import sys

# Add the project root directory to the path for robust imports
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _PROJECT_ROOT)

from sr_screener import database

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