#!/usr/bin/env python3
"""
Test script to validate PubMed text parser functionality
"""
import sys
import io
import pandas as pd
from pathlib import Path

def test_pubmed_text_parser():
    """Test the PubMed text parser with sample data"""
    print("=== Testing PubMed Text Parser ===")
    
    try:
        sys.path.append('sr_screener')
        from parsers import parse_pubmed_text, detect_format, parse_citations
        
        sample_file = Path('test_pubmed_sample.txt')
        if not sample_file.exists():
            print("❌ Sample file not found")
            return False
        
        with open(sample_file, 'rb') as f:
            content = f.read()
            detected_format = detect_format('test_pubmed_sample.txt', content)
            print(f"✓ Format detection: {detected_format}")
            
            if detected_format != 'pubmed_text':
                print(f"❌ Expected 'pubmed_text', got '{detected_format}'")
                return False
        
        with open(sample_file, 'rb') as f:
            df = parse_pubmed_text(f)
            print(f"✓ Parsed {len(df)} citations")
            
            if len(df) == 0:
                print("❌ No citations parsed")
                return False
            
            required_columns = ['id', 'title', 'abstract', 'year', 'authors', 'journal', 'doi']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                print(f"❌ Missing columns: {missing_columns}")
                return False
            
            print("✓ All required columns present")
            
            for idx, row in df.iterrows():
                print(f"\n--- Citation {idx + 1} ---")
                print(f"ID: {row['id']}")
                print(f"Title: {row['title'][:100]}...")
                print(f"Journal: {row['journal']}")
                print(f"Year: {row['year']}")
                print(f"DOI: {row['doi']}")
                print(f"Abstract length: {len(str(row['abstract']))}")
                
                if not row['title'] or len(str(row['title']).strip()) < 10:
                    print(f"⚠️  Warning: Title seems too short")
                
                if not row['abstract'] or len(str(row['abstract']).strip()) < 50:
                    print(f"⚠️  Warning: Abstract seems too short")
                
                if not row['id'] or 'PMID:' not in str(row['id']):
                    print(f"⚠️  Warning: PMID not properly extracted")
        
        print("\n=== Testing Main Parser Function ===")
        with open(sample_file, 'rb') as f:
            df_main = parse_citations(f, 'test_pubmed_sample.txt')
            print(f"✓ Main parser processed {len(df_main)} citations")
            
            if len(df_main) != len(df):
                print(f"⚠️  Warning: Different citation counts between parsers")
        
        return True
        
    except Exception as e:
        print(f"❌ Parser test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run PubMed parser validation"""
    success = test_pubmed_text_parser()
    
    if success:
        print("\n✅ PubMed text parser validation successful!")
        return 0
    else:
        print("\n❌ PubMed text parser validation failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
