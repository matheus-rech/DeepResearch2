#!/usr/bin/env python3
"""
Claude-Powered Citation Parser/Loader for Deep Research
Ensures perfect formatting for both screening engine and UI browser
"""
import json
import subprocess
import pandas as pd
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
import tempfile
import os

class ClaudeCitationParser:
    """Use Claude to parse and format citations perfectly"""
    
    def __init__(self):
        self.claude_available = self._check_claude_availability()
        
    def _check_claude_availability(self) -> bool:
        """Check if Claude CLI is available"""
        try:
            result = subprocess.run(['claude-code', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    def parse_citations_with_claude(self, input_file: str, 
                                   input_format: str = 'auto') -> List[Dict[str, Any]]:
        """Parse citations using Claude for perfect structure"""
        
        # Read input file
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            raw_content = f.read()
        
        # Detect format if auto
        if input_format == 'auto':
            input_format = self._detect_format(raw_content, input_file)
        
        # Create Claude prompt based on format
        prompt = self._create_parsing_prompt(input_format)
        
        if self.claude_available:
            # Use Claude for intelligent parsing
            parsed_data = self._parse_with_claude_cli(raw_content, prompt)
        else:
            # Fallback to basic parsing
            parsed_data = self._fallback_parse(raw_content, input_format)
        
        # Validate and clean the parsed data
        cleaned_citations = self._validate_and_clean(parsed_data)
        
        return cleaned_citations
    
    def _detect_format(self, content: str, filename: str) -> str:
        """Detect citation format"""
        filename_lower = filename.lower()
        
        if filename_lower.endswith('.csv'):
            return 'csv'
        elif filename_lower.endswith('.ris'):
            return 'ris'
        elif filename_lower.endswith('.xml'):
            if 'PubmedArticle' in content or 'pubmed' in content.lower():
                return 'pubmed_xml'
            else:
                return 'endnote_xml'
        elif filename_lower.endswith('.nbib'):
            return 'nbib'
        elif 'TY  -' in content:
            return 'ris'
        elif '<?xml' in content:
            return 'xml'
        else:
            return 'text'
    
    def _create_parsing_prompt(self, format_type: str) -> str:
        """Create format-specific parsing prompt"""
        
        base_prompt = """Parse this citation data and return a JSON array where each citation has this EXACT structure:

{
    "id": "unique_identifier",
    "title": "complete_title",
    "abstract": "full_abstract_text",
    "authors": "comma_separated_author_list",
    "year": 2024,
    "journal": "journal_name",
    "doi": "doi_if_available",
    "pmid": "pubmed_id_if_available",
    "keywords": "comma_separated_keywords",
    "study_type": "detected_study_type",
    "url": "url_if_available",
    "volume": "volume_number",
    "issue": "issue_number", 
    "pages": "page_range",
    "language": "language_code",
    "country": "country_of_study"
}

CRITICAL REQUIREMENTS:
1. Every citation MUST have at least: id, title, authors, year, journal
2. Use "Unknown" for missing required fields, null for optional fields
3. Clean up formatting (remove extra spaces, line breaks in wrong places)
4. Generate unique IDs if not provided (author_year_keyword format)
5. Standardize years as integers
6. Return ONLY valid JSON array, no explanations"""

        format_specific = {
            'csv': "\n\nThis is CSV format. Parse each row as a citation.",
            'ris': "\n\nThis is RIS format. Each citation starts with 'TY  -' and ends with 'ER  -'.",
            'pubmed_xml': "\n\nThis is PubMed XML. Extract from <PubmedArticle> elements.",
            'endnote_xml': "\n\nThis is EndNote XML format. Parse <record> elements.",
            'nbib': "\n\nThis is NBIB format from PubMed. Parse each citation block.",
            'text': "\n\nThis is plain text. Use your best judgment to identify citation boundaries."
        }
        
        return base_prompt + format_specific.get(format_type, "")
    
    def _parse_with_claude_cli(self, content: str, prompt: str) -> List[Dict[str, Any]]:
        """Use Claude CLI to parse citations"""
        
        # Create temporary file with content
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Run Claude CLI
            cmd = f"cat {temp_file_path} | claude-code -p '{prompt}' --output-format json"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse Claude's JSON response
                claude_output = json.loads(result.stdout)
                
                # Extract citations from Claude's response structure
                if isinstance(claude_output, list):
                    return claude_output
                elif isinstance(claude_output, dict):
                    # Handle different response formats
                    if 'content' in claude_output:
                        content_text = claude_output['content']
                        # Try to extract JSON from content
                        try:
                            return json.loads(content_text)
                        except:
                            # Parse as text and retry
                            return self._extract_json_from_text(content_text)
                    elif 'citations' in claude_output:
                        return claude_output['citations']
                    elif 'data' in claude_output:
                        return claude_output['data']
                
                return []
            else:
                print(f"Claude CLI error: {result.stderr}")
                return []
                
        finally:
            # Clean up temp file
            os.unlink(temp_file_path)
    
    def _extract_json_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract JSON array from text response"""
        # Look for JSON array in the text
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Look for individual JSON objects
        json_objects = re.findall(r'\{[^}]*\}', text)
        citations = []
        for obj_str in json_objects:
            try:
                citations.append(json.loads(obj_str))
            except:
                pass
        
        return citations
    
    def _fallback_parse(self, content: str, format_type: str) -> List[Dict[str, Any]]:
        """Fallback parsing without Claude"""
        citations = []
        
        if format_type == 'csv':
            # Basic CSV parsing
            lines = content.strip().split('\n')
            if len(lines) > 1:
                headers = [h.strip().lower() for h in lines[0].split(',')]
                for line in lines[1:]:
                    fields = line.split(',')
                    citation = self._create_empty_citation()
                    
                    for i, field in enumerate(fields):
                        if i < len(headers):
                            header = headers[i]
                            if 'title' in header:
                                citation['title'] = field.strip('"')
                            elif 'author' in header:
                                citation['authors'] = field.strip('"')
                            elif 'year' in header:
                                try:
                                    citation['year'] = int(field.strip('"'))
                                except:
                                    citation['year'] = 2024
                    
                    if citation['title']:
                        citations.append(citation)
        
        elif format_type == 'ris':
            # Basic RIS parsing
            citation_blocks = content.split('TY  -')
            for block in citation_blocks[1:]:  # Skip first empty block
                citation = self._create_empty_citation()
                lines = block.split('\n')
                
                for line in lines:
                    if line.startswith('TI  -'):
                        citation['title'] = line[6:].strip()
                    elif line.startswith('AU  -'):
                        if citation['authors']:
                            citation['authors'] += ', ' + line[6:].strip()
                        else:
                            citation['authors'] = line[6:].strip()
                    elif line.startswith('PY  -'):
                        try:
                            citation['year'] = int(line[6:].strip()[:4])
                        except:
                            citation['year'] = 2024
                    elif line.startswith('JO  -'):
                        citation['journal'] = line[6:].strip()
                    elif line.startswith('AB  -'):
                        citation['abstract'] = line[6:].strip()
                
                if citation['title']:
                    citations.append(citation)
        
        return citations
    
    def _create_empty_citation(self) -> Dict[str, Any]:
        """Create empty citation with required structure"""
        return {
            "id": "",
            "title": "",
            "abstract": "",
            "authors": "",
            "year": 2024,
            "journal": "",
            "doi": None,
            "pmid": None,
            "keywords": None,
            "study_type": None,
            "url": None,
            "volume": None,
            "issue": None,
            "pages": None,
            "language": None,
            "country": None
        }
    
    def _validate_and_clean(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean parsed citations"""
        cleaned = []
        
        for i, citation in enumerate(citations):
            # Ensure required fields
            if not citation.get('id'):
                # Generate ID from author, year, and first word of title
                author_part = citation.get('authors', 'unknown').split(',')[0].split()[-1] if citation.get('authors') else 'unknown'
                year_part = str(citation.get('year', 2024))
                title_part = citation.get('title', 'untitled').split()[0] if citation.get('title') else 'untitled'
                citation['id'] = f"{author_part.lower()}_{year_part}_{title_part.lower()}_{i}"
            
            # Clean title
            if citation.get('title'):
                citation['title'] = re.sub(r'\s+', ' ', citation['title']).strip()
            else:
                citation['title'] = "Untitled"
            
            # Clean abstract
            if citation.get('abstract'):
                citation['abstract'] = re.sub(r'\s+', ' ', citation['abstract']).strip()
            
            # Ensure year is integer
            try:
                citation['year'] = int(citation.get('year', 2024))
            except:
                citation['year'] = 2024
            
            # Clean authors
            if citation.get('authors'):
                citation['authors'] = re.sub(r'\s+', ' ', citation['authors']).strip()
            else:
                citation['authors'] = "Unknown"
            
            # Ensure journal
            if not citation.get('journal'):
                citation['journal'] = "Unknown"
            
            cleaned.append(citation)
        
        return cleaned
    
    def save_for_deep_research(self, citations: List[Dict[str, Any]], 
                              output_file: str) -> None:
        """Save in format optimized for Deep Research screening"""
        
        # Create format optimized for screening
        screening_format = []
        for citation in citations:
            screening_citation = {
                'id': citation['id'],
                'title': citation['title'],
                'abstract': citation.get('abstract', ''),
                'authors': citation['authors'],
                'year': citation['year'],
                'journal': citation['journal'],
                'doi': citation.get('doi'),
                'study_type': citation.get('study_type'),
                'keywords': citation.get('keywords'),
                # Additional metadata for screening
                'screening_notes': '',
                'reviewer_id': '',
                'screening_date': '',
                'inclusion_decision': '',
                'exclusion_reason': '',
                'quality_score': None
            }
            screening_format.append(screening_citation)
        
        # Save as JSON for Deep Research
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(screening_format, f, indent=2, ensure_ascii=False)
    
    def save_for_ui_browser(self, citations: List[Dict[str, Any]], 
                           output_file: str) -> None:
        """Save in format optimized for Streamlit UI browser"""
        
        # Create DataFrame for UI
        ui_data = []
        for citation in citations:
            ui_citation = {
                'ID': citation['id'],
                'Title': citation['title'],
                'Authors': citation['authors'],
                'Year': citation['year'],
                'Journal': citation['journal'],
                'Abstract': (citation.get('abstract', '')[:200] + '...' 
                           if citation.get('abstract') and len(citation.get('abstract', '')) > 200 
                           else citation.get('abstract', '')),
                'DOI': citation.get('doi', ''),
                'Study Type': citation.get('study_type', ''),
                'Keywords': citation.get('keywords', ''),
                'Full Abstract': citation.get('abstract', '')
            }
            ui_data.append(ui_citation)
        
        # Save as CSV for UI
        df = pd.DataFrame(ui_data)
        df.to_csv(output_file, index=False, encoding='utf-8')

def create_citation_processing_script():
    """Create bash script for complete citation processing"""
    script = '''#!/bin/bash
# Claude-Powered Citation Processing Pipeline

set -e

INPUT_FILE="${1:-citations.csv}"
OUTPUT_DIR="${2:-processed_citations}"

echo "🔬 Claude Citation Processing Pipeline"
echo "======================================"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "📁 Processing: $INPUT_FILE"
echo "📤 Output directory: $OUTPUT_DIR"

# Step 1: Parse with Claude
echo "🤖 Step 1: Parsing citations with Claude..."
python -c "
from claude_citation_parser import ClaudeCitationParser
parser = ClaudeCitationParser()
citations = parser.parse_citations_with_claude('$INPUT_FILE')
parser.save_for_deep_research(citations, '$OUTPUT_DIR/citations_for_screening.json')
parser.save_for_ui_browser(citations, '$OUTPUT_DIR/citations_for_ui.csv')
print(f'✅ Processed {len(citations)} citations')
"

# Step 2: Validate with Claude
echo "✅ Step 2: Validating citation quality..."
cat "$OUTPUT_DIR/citations_for_screening.json" | claude-code -p 'Analyze these citations for quality issues: missing data, formatting problems, duplicates. Return JSON with validation results.' --output-format json > "$OUTPUT_DIR/validation_report.json"

# Step 3: Generate summary
echo "📊 Step 3: Generating summary..."
cat "$OUTPUT_DIR/citations_for_screening.json" | claude-code -p 'Create a summary report of these citations: total count, year distribution, journal distribution, study types, quality assessment.' --output-format text > "$OUTPUT_DIR/citation_summary.md"

echo "✅ Citation processing complete!"
echo "Files created:"
echo "  - $OUTPUT_DIR/citations_for_screening.json (for Deep Research)"
echo "  - $OUTPUT_DIR/citations_for_ui.csv (for UI browser)"
echo "  - $OUTPUT_DIR/validation_report.json (quality check)"
echo "  - $OUTPUT_DIR/citation_summary.md (summary report)"
'''
    
    with open('process_citations.sh', 'w') as f:
        f.write(script)
    os.chmod('process_citations.sh', 0o755)

# Example usage and testing
def demo_citation_processing():
    """Demonstrate citation processing capabilities"""
    
    # Create sample citation file
    sample_citations = '''id,title,abstract,year,authors,journal,doi
1,"Effects of continuous glucose monitoring on glycemic control","Background: Type 2 diabetes management requires regular monitoring...",2023,"Smith J, Johnson K","Diabetes Care","10.1234/dc.2023.1"
2,"Glucose monitoring technologies review","This systematic review examines various glucose monitoring technologies...",2023,"Taylor M, Anderson P","Journal of Diabetes Technology","10.1234/jdt.2023.1"
'''
    
    with open('sample_citations.csv', 'w') as f:
        f.write(sample_citations)
    
    # Process citations
    parser = ClaudeCitationParser()
    
    print("🔬 Testing Citation Processing")
    print("=" * 40)
    
    citations = parser.parse_citations_with_claude('sample_citations.csv')
    
    print(f"📄 Parsed {len(citations)} citations")
    print(f"📊 Sample citation structure:")
    if citations:
        print(json.dumps(citations[0], indent=2))
    
    # Save in both formats
    parser.save_for_deep_research(citations, 'citations_for_deep_research.json')
    parser.save_for_ui_browser(citations, 'citations_for_ui.csv')
    
    print("\n✅ Files created:")
    print("  - citations_for_deep_research.json")
    print("  - citations_for_ui.csv")

if __name__ == "__main__":
    # Create the processing script
    create_citation_processing_script()
    
    # Run demo
    demo_citation_processing()
    
    print("\n🚀 Ready to use!")
    print("Run: ./process_citations.sh your_citations.csv")