#!/usr/bin/env python3
"""
Basic flow test to verify components work without full server setup
"""
import sys
import os
from pathlib import Path

# Add sr_screener to path
sys.path.insert(0, 'sr_screener')

def test_imports():
    """Test that all modules can be imported"""
    print("Testing imports...")
    try:
        import sr_screener.app
        import sr_screener.database as db
        import sr_screener.parsers
        import sr_screener.deep_research
        import sr_screener.ice_critic
        import sr_screener.data_validator
        import sr_screener.multi_agent_research
        print("✓ All modules imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_database():
    """Test database initialization"""
    print("\nTesting database...")
    try:
        import sr_screener.database as db
        db.init_db()
        
        # Test basic operations
        stats = db.get_corpus_stats()
        print(f"✓ Database initialized. Current citations: {stats['total_citations']}")
        return True
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

def test_parsers():
    """Test citation parsers"""
    print("\nTesting parsers...")
    try:
        import sr_screener.parsers as parsers
        
        # Create test RIS content
        test_ris = """TY  - JOUR
T1  - Test Article
AU  - Test Author
PY  - 2023
JO  - Test Journal
AB  - This is a test abstract.
ER  - 
"""
        test_file = Path("test.ris")
        test_file.write_text(test_ris)
        
        # Parse the file - parsers expect file-like object with read() method
        from io import BytesIO
        df = parsers.parse_citations(BytesIO(test_ris.encode()), "test.ris")
        
        if len(df) == 1 and df.iloc[0]['title'] == "Test Article":
            print("✓ RIS parser working correctly")
            test_file.unlink()
            return True
        else:
            print("✗ Parser returned unexpected results")
            test_file.unlink()
            return False
    except Exception as e:
        print(f"✗ Parser error: {e}")
        if test_file.exists():
            test_file.unlink()
        return False

def test_data_validator():
    """Test citation validator"""
    print("\nTesting data validator...")
    try:
        from sr_screener.data_validator import CitationValidator
        import pandas as pd
        
        # Create test data with complete fields
        test_data = pd.DataFrame([{
            'id': 'test123',
            'title': 'Effects of continuous glucose monitoring on glycemic control in type 2 diabetes',
            'abstract': 'This randomized controlled trial examined the effects of continuous glucose monitoring (CGM) on glycemic control in adults with type 2 diabetes. Participants (n=200) were randomly assigned to CGM or standard blood glucose monitoring for 6 months.',
            'year': 2023,
            'journal': 'Diabetes Care',
            'authors': '[{"name": "Smith, J."}, {"name": "Doe, J."}]',
            'doi': '10.1234/test.2023.001'
        }])
        
        validator = CitationValidator()
        validated_df, report = validator.validate_citations(test_data)
        
        # Check both quality score and valid count
        if report['quality_score'] > 0 or report['summary']['valid'] > 0:
            print(f"✓ Validator working. Quality score: {report['quality_score']:.1f}%, Valid citations: {report['summary']['valid']}")
            return True
        else:
            print(f"✗ Validator issues: {report}")
            return False
    except Exception as e:
        print(f"✗ Validator error: {e}")
        return False

def main():
    """Run all basic tests"""
    print("=== DeepResearch2 Basic Component Tests ===\n")
    
    tests = [
        test_imports,
        test_database,
        test_parsers,
        test_data_validator
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with error: {e}")
            results.append(False)
    
    # Summary
    print("\n=== Test Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All basic tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())