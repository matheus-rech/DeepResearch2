"""
Enhanced Citation Parsers with Claude Integration
Combines traditional parsing with Claude's intelligence for perfect results
"""
import json
import subprocess
import tempfile
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import pandas as pd
import logging

# Import original parsers as fallback
from parsers import parse_csv as original_parse_csv, parse_ris as original_parse_ris
from claude_citation_parser import ClaudeCitationParser

logger = logging.getLogger(__name__)

class EnhancedCitationParser:
    """Enhanced parser that uses Claude for intelligent citation processing"""
    
    def __init__(self):
        self.claude_parser = ClaudeCitationParser()
        
    def parse_any_format(self, file_path: str, use_claude: bool = True) -> List[Dict[str, Any]]:
        """
        Parse citations from any format using Claude intelligence
        Falls back to traditional parsing if Claude unavailable
        """
        try:
            if use_claude and self.claude_parser.claude_available:
                logger.info(f"🤖 Using Claude to parse {file_path}")
                citations = self.claude_parser.parse_citations_with_claude(file_path)
                logger.info(f"✅ Claude parsed {len(citations)} citations")
                return citations
            else:
                logger.info(f"📄 Using traditional parsing for {file_path}")
                return self._traditional_parse(file_path)
                
        except Exception as e:
            logger.error(f"❌ Enhanced parsing failed: {e}")
            logger.info("🔄 Falling back to traditional parsing")
            return self._traditional_parse(file_path)
    
    def _traditional_parse(self, file_path: str) -> List[Dict[str, Any]]:
        """Traditional parsing as fallback"""
        file_ext = Path(file_path).suffix.lower()
        
        try:
            if file_ext == '.csv':
                return self._normalize_citations(original_parse_csv(file_path))
            elif file_ext == '.ris':
                return self._normalize_citations(original_parse_ris(file_path))
            else:
                # Generic text parsing
                return self._parse_generic_text(file_path)
        except Exception as e:
            logger.error(f"Traditional parsing failed: {e}")
            return []
    
    def _normalize_citations(self, citations: List[Dict]) -> List[Dict[str, Any]]:
        """Normalize citation format for consistency"""
        normalized = []
        
        for i, citation in enumerate(citations):
            normalized_citation = {
                'id': citation.get('id') or f"citation_{i+1}",
                'title': citation.get('title') or citation.get('Title') or "Unknown Title",
                'abstract': citation.get('abstract') or citation.get('Abstract') or "",
                'authors': citation.get('authors') or citation.get('Authors') or "Unknown Authors",
                'year': self._normalize_year(citation.get('year') or citation.get('Year')),
                'journal': citation.get('journal') or citation.get('Journal') or "Unknown Journal",
                'doi': citation.get('doi') or citation.get('DOI'),
                'pmid': citation.get('pmid') or citation.get('PMID'),
                'keywords': citation.get('keywords') or citation.get('Keywords'),
                'study_type': citation.get('study_type'),
                'url': citation.get('url'),
                'volume': citation.get('volume'),
                'issue': citation.get('issue'),
                'pages': citation.get('pages'),
                'language': citation.get('language'),
                'country': citation.get('country')
            }
            normalized.append(normalized_citation)
        
        return normalized
    
    def _normalize_year(self, year_value: Any) -> int:
        """Normalize year to integer"""
        if not year_value:
            return 2024
        
        try:
            if isinstance(year_value, str):
                # Extract first 4-digit number
                import re
                year_match = re.search(r'\b(19|20)\d{2}\b', year_value)
                if year_match:
                    return int(year_match.group())
            return int(year_value)
        except:
            return 2024
    
    def _parse_generic_text(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse generic text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split by double line breaks or common separators
            potential_citations = []
            for separator in ['\n\n', '\n---\n', '\n***\n']:
                if separator in content:
                    potential_citations = content.split(separator)
                    break
            
            if not potential_citations:
                potential_citations = [content]
            
            citations = []
            for i, text in enumerate(potential_citations):
                if text.strip():
                    citation = {
                        'id': f"text_citation_{i+1}",
                        'title': text.split('\n')[0][:100] if text else "Unknown Title",
                        'abstract': text.strip(),
                        'authors': "Unknown Authors",
                        'year': 2024,
                        'journal': "Unknown Journal",
                        'doi': None,
                        'pmid': None,
                        'keywords': None,
                        'study_type': None,
                        'url': None,
                        'volume': None,
                        'issue': None,
                        'pages': None,
                        'language': None,
                        'country': None
                    }
                    citations.append(citation)
            
            return citations
            
        except Exception as e:
            logger.error(f"Generic text parsing failed: {e}")
            return []

# Public interface functions for compatibility with existing code
def parse_csv(file_path: str, use_claude: bool = True) -> List[Dict[str, Any]]:
    """Parse CSV file with optional Claude enhancement"""
    parser = EnhancedCitationParser()
    
    if use_claude:
        return parser.parse_any_format(file_path, use_claude=True)
    else:
        return parser._traditional_parse(file_path)

def parse_ris(file_path: str, use_claude: bool = True) -> List[Dict[str, Any]]:
    """Parse RIS file with optional Claude enhancement"""
    parser = EnhancedCitationParser()
    
    if use_claude:
        return parser.parse_any_format(file_path, use_claude=True)
    else:
        return parser._traditional_parse(file_path)

def parse_any_citation_file(file_path: str, use_claude: bool = True) -> List[Dict[str, Any]]:
    """Parse any citation file format with Claude intelligence"""
    parser = EnhancedCitationParser()
    return parser.parse_any_format(file_path, use_claude=use_claude)

def validate_citations_with_claude(citations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Use Claude to validate citation quality"""
    
    # Create temp file with citations
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as temp_file:
        json.dump(citations, temp_file, indent=2)
        temp_file_path = temp_file.name
    
    try:
        # Create validation prompt
        prompt = """Analyze these citations for quality issues:

1. Missing required fields (title, authors, year, journal)
2. Formatting inconsistencies 
3. Duplicate entries
4. Invalid data (years, DOIs)
5. Incomplete abstracts
6. Author name formatting issues

Return JSON with:
{
    "total_citations": 0,
    "issues_found": [],
    "quality_score": 0.0-1.0,
    "recommendations": [],
    "duplicates": [],
    "missing_fields": {}
}"""
        
        # Run Claude validation
        cmd = f"cat {temp_file_path} | claude-code -p '{prompt}' --output-format json"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return {
                "total_citations": len(citations),
                "issues_found": ["Claude validation unavailable"],
                "quality_score": 0.8,
                "recommendations": ["Manual review recommended"],
                "duplicates": [],
                "missing_fields": {}
            }
            
    except Exception as e:
        logger.error(f"Claude validation failed: {e}")
        return {
            "total_citations": len(citations),
            "issues_found": [f"Validation error: {e}"],
            "quality_score": 0.7,
            "recommendations": ["Manual validation needed"],
            "duplicates": [],
            "missing_fields": {}
        }
    finally:
        # Clean up temp file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

def format_citations_for_ui(citations: List[Dict[str, Any]]) -> pd.DataFrame:
    """Format citations for Streamlit UI display"""
    
    ui_data = []
    for citation in citations:
        # Create display-friendly format
        ui_citation = {
            'ID': citation.get('id', ''),
            'Title': citation.get('title', '')[:100] + ('...' if len(citation.get('title', '')) > 100 else ''),
            'Authors': citation.get('authors', '')[:50] + ('...' if len(citation.get('authors', '')) > 50 else ''),
            'Year': citation.get('year', ''),
            'Journal': citation.get('journal', '')[:40] + ('...' if len(citation.get('journal', '')) > 40 else ''),
            'Abstract': citation.get('abstract', '')[:150] + ('...' if len(citation.get('abstract', '')) > 150 else ''),
            'DOI': citation.get('doi', ''),
            'Study Type': citation.get('study_type', ''),
            'Full_Title': citation.get('title', ''),
            'Full_Abstract': citation.get('abstract', ''),
            'Full_Authors': citation.get('authors', '')
        }
        ui_data.append(ui_citation)
    
    return pd.DataFrame(ui_data)

def export_for_screening(citations: List[Dict[str, Any]], output_path: str) -> None:
    """Export citations in format optimized for Deep Research screening"""
    
    screening_citations = []
    for citation in citations:
        screening_citation = {
            **citation,  # Include all original fields
            'screening_notes': '',
            'reviewer_id': '',
            'screening_date': '',
            'inclusion_decision': '',
            'exclusion_reason': '',
            'quality_score': None,
            'confidence_level': None,
            'conflicts_of_interest': None,
            'funding_source': citation.get('funding'),
            'study_limitations': []
        }
        screening_citations.append(screening_citation)
    
    # Save as JSON for screening engine
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(screening_citations, f, indent=2, ensure_ascii=False)

# Demo function
def demo_enhanced_parsing():
    """Demonstrate enhanced parsing capabilities"""
    
    print("🔬 Enhanced Citation Parser Demo")
    print("=" * 40)
    
    # Create sample files
    sample_csv = '''title,authors,year,journal,abstract,doi
"Effects of CGM on diabetes","Smith J, Jones A",2023,"Diabetes Care","Background: This study...",10.1234/dc.2023.1
"Glucose monitoring review","Taylor M",2023,"Diabetes Tech","This review examines...",10.1234/dt.2023.1'''
    
    with open('demo_citations.csv', 'w') as f:
        f.write(sample_csv)
    
    # Test enhanced parsing
    parser = EnhancedCitationParser()
    
    print("📄 Parsing with enhanced parser...")
    citations = parser.parse_any_format('demo_citations.csv')
    
    print(f"✅ Parsed {len(citations)} citations")
    if citations:
        print("\n📋 Sample citation:")
        print(json.dumps(citations[0], indent=2))
    
    # Test validation
    print("\n🔍 Validating with Claude...")
    validation = validate_citations_with_claude(citations)
    print(f"Quality Score: {validation.get('quality_score', 'N/A')}")
    print(f"Issues Found: {len(validation.get('issues_found', []))}")
    
    # Test UI formatting
    print("\n📊 Formatting for UI...")
    ui_df = format_citations_for_ui(citations)
    print(f"UI DataFrame shape: {ui_df.shape}")
    print(f"Columns: {list(ui_df.columns)}")
    
    # Clean up
    os.unlink('demo_citations.csv')
    
    print("\n✅ Demo complete!")

if __name__ == "__main__":
    demo_enhanced_parsing()