"""
Citation file parsers for various formats
Supports: PubMed XML, RIS, CSV, and more
"""
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
import pandas as pd
import rispy
import io
import csv
import json
from dateutil import parser as date_parser
from bs4 import BeautifulSoup


def normalize_year(date_str: Any) -> Optional[int]:
    """Extract year from various date formats."""
    if pd.isna(date_str) or not date_str:
        return None
    
    try:
        if isinstance(date_str, (int, float)):
            year = int(date_str)
            if 1900 <= year <= 2100:  # Reasonable year range
                return year
        else:
            parsed_date = date_parser.parse(str(date_str))
            return parsed_date.year
    except Exception:
        # Try to extract 4-digit year from string
        import re
        year_match = re.search(r'\b(19|20)\d{2}\b', str(date_str))
        if year_match:
            return int(year_match.group())
    
    return None


def parse_pubmed_xml(file_obj) -> pd.DataFrame:
    """
    Parse PubMed XML export format.
    Returns DataFrame with standardized columns.
    """
    tree = ET.parse(file_obj)
    root = tree.getroot()
    
    citations = []
    
    for article in root.findall('.//PubmedArticle'):
        # Extract PMID
        pmid = article.findtext('.//PMID')
        if not pmid:
            continue
            
        # Extract article details
        article_elem = article.find('.//Article')
        if article_elem is None:
            continue
            
        # Title
        title = article_elem.findtext('.//ArticleTitle', '')
        
        # Abstract
        abstract_parts = []
        abstract_elem = article_elem.find('.//Abstract')
        if abstract_elem is not None:
            for abstract_text in abstract_elem.findall('.//AbstractText'):
                text = abstract_text.text or ''
                label = abstract_text.get('Label', '')
                if label:
                    abstract_parts.append(f"{label}: {text}")
                else:
                    abstract_parts.append(text)
        abstract = ' '.join(abstract_parts)
        
        # Authors
        authors = []
        for author in article_elem.findall('.//Author'):
            last_name = author.findtext('LastName', '')
            fore_name = author.findtext('ForeName', '')
            if last_name:
                authors.append(f"{last_name} {fore_name}".strip())
        
        # Journal
        journal = article_elem.findtext('.//Journal/Title', '')
        
        # Year
        pub_date = article_elem.find('.//Journal/JournalIssue/PubDate')
        year = None
        if pub_date is not None:
            year_text = pub_date.findtext('Year')
            if not year_text:
                medline_date = pub_date.findtext('MedlineDate')
                if medline_date:
                    year_text = medline_date
            year = normalize_year(year_text)
        
        # DOI
        doi = None
        for eloc_id in article_elem.findall('.//ELocationID'):
            if eloc_id.get('EIdType') == 'doi':
                doi = eloc_id.text
                break
        
        # MeSH terms
        mesh_terms = []
        for mesh in article.findall('.//MeshHeading/DescriptorName'):
            mesh_terms.append(mesh.text)
        
        # Keywords
        keywords = []
        for keyword in article.findall('.//Keyword'):
            if keyword.text:
                keywords.append(keyword.text)
        
        citations.append({
            'id': f'PMID:{pmid}',
            'title': title,
            'abstract': abstract,
            'year': year,
            'authors': authors,
            'journal': journal,
            'doi': doi,
            'mesh_terms': mesh_terms,
            'keywords': keywords,
            'raw_data': {
                'source': 'pubmed',
                'pmid': pmid,
                'xml': ET.tostring(article, encoding='unicode')
            }
        })
    
    return pd.DataFrame(citations)


def parse_ris(file_obj) -> pd.DataFrame:
    """
    Parse RIS (Research Information Systems) format.
    Common export format from EndNote, Mendeley, etc.
    """
    entries = rispy.load(file_obj)
    
    citations = []
    for entry in entries:
        # Extract year
        year = entry.get('year')
        if not year:
            year = entry.get('publication_year')
        year = normalize_year(year)
        
        # Extract authors
        authors = []
        if 'authors' in entry:
            authors = entry['authors']
        elif 'first_authors' in entry:
            authors = entry['first_authors']
        
        # Build ID
        cite_id = entry.get('id', '')
        if not cite_id:
            cite_id = entry.get('doi', '')
        if not cite_id:
            cite_id = f"RIS_{len(citations)}"
        
        citations.append({
            'id': cite_id,
            'title': entry.get('title', ''),
            'abstract': entry.get('abstract', ''),
            'year': year,
            'authors': authors,
            'journal': entry.get('journal_name', ''),
            'doi': entry.get('doi', ''),
            'mesh_terms': [],
            'keywords': entry.get('keywords', []),
            'raw_data': {
                'source': 'ris',
                'entry': entry
            }
        })
    
    return pd.DataFrame(citations)


def parse_csv(file_obj) -> pd.DataFrame:
    """
    Parse generic CSV format.
    Expects standard column names but will map common variations.
    """
    df = pd.read_csv(file_obj)
    
    # Column mapping for common variations
    column_map = {
        'pmid': 'id',
        'PMID': 'id',
        'Title': 'title',
        'Abstract': 'abstract',
        'Year': 'year',
        'Publication Year': 'year',
        'Authors': 'authors',
        'Journal': 'journal',
        'Journal/Book': 'journal',
        'DOI': 'doi',
        'MeSH Terms': 'mesh_terms',
        'Keywords': 'keywords'
    }
    
    # Rename columns
    df = df.rename(columns=column_map)
    
    # Ensure required columns exist
    required = ['id', 'title']
    for col in required:
        if col not in df.columns:
            # Try to generate ID from other columns
            if col == 'id' and 'doi' in df.columns:
                df['id'] = df['doi']
            elif col == 'id':
                df['id'] = [f'CSV_{i}' for i in range(len(df))]
            else:
                df[col] = ''
    
    # Normalize data
    if 'year' in df.columns:
        df['year'] = df['year'].apply(normalize_year)
    
    # Parse list fields
    list_fields = ['authors', 'mesh_terms', 'keywords']
    for field in list_fields:
        if field in df.columns:
            df[field] = df[field].apply(lambda x: 
                x.split(';') if isinstance(x, str) else []
            )
        else:
            df[field] = [[] for _ in range(len(df))]
    
    # Add raw data
    df['raw_data'] = df.apply(lambda row: {
        'source': 'csv',
        'row': row.to_dict()
    }, axis=1)
    
    # Ensure all columns exist
    for col in ['abstract', 'journal', 'doi']:
        if col not in df.columns:
            df[col] = ''
    
    return df[['id', 'title', 'abstract', 'year', 'authors', 
               'journal', 'doi', 'mesh_terms', 'keywords', 'raw_data']]


def parse_endnote_xml(file_obj) -> pd.DataFrame:
    """
    Parse EndNote XML export format.
    """
    soup = BeautifulSoup(file_obj.read(), 'xml')
    
    citations = []
    for record in soup.find_all('record'):
        # Extract fields
        rec_number = record.find('rec-number')
        rec_id = f"EndNote_{rec_number.text}" if rec_number else f"EndNote_{len(citations)}"
        
        # Title
        title_elem = record.find('title')
        title = title_elem.text if title_elem else ''
        
        # Abstract
        abstract_elem = record.find('abstract')
        abstract = abstract_elem.text if abstract_elem else ''
        
        # Authors
        authors = []
        contributors = record.find('contributors')
        if contributors:
            for author in contributors.find_all('author'):
                authors.append(author.text)
        
        # Year
        year_elem = record.find('year')
        year = normalize_year(year_elem.text if year_elem else None)
        
        # Journal
        journal_elem = record.find('secondary-title')
        journal = journal_elem.text if journal_elem else ''
        
        # DOI
        doi_elem = record.find('electronic-resource-num')
        doi = doi_elem.text if doi_elem else ''
        
        # Keywords
        keywords = []
        keywords_elem = record.find('keywords')
        if keywords_elem:
            for keyword in keywords_elem.find_all('keyword'):
                keywords.append(keyword.text)
        
        citations.append({
            'id': rec_id,
            'title': title,
            'abstract': abstract,
            'year': year,
            'authors': authors,
            'journal': journal,
            'doi': doi,
            'mesh_terms': [],
            'keywords': keywords,
            'raw_data': {
                'source': 'endnote_xml',
                'xml': str(record)
            }
        })
    
    return pd.DataFrame(citations)


def detect_format(filename: str, content: bytes) -> str:
    """
    Detect citation file format from filename and content.
    """
    filename_lower = filename.lower()
    
    # Check by extension
    if filename_lower.endswith('.xml'):
        # Check if it's PubMed or EndNote XML
        content_str = content.decode('utf-8', errors='ignore')
        if '<PubmedArticle>' in content_str:
            return 'pubmed_xml'
        elif '<records>' in content_str and '<record>' in content_str:
            return 'endnote_xml'
        else:
            return 'unknown_xml'
    elif filename_lower.endswith('.ris'):
        return 'ris'
    elif filename_lower.endswith('.csv'):
        return 'csv'
    elif filename_lower.endswith('.nbib'):
        return 'pubmed_nbib'
    
    # Check by content if no clear extension
    try:
        content_str = content.decode('utf-8', errors='ignore')[:1000]
        if 'TY  -' in content_str:
            return 'ris'
        elif '<PubmedArticle>' in content_str:
            return 'pubmed_xml'
        elif content_str.strip().startswith('PMID-'):
            return 'pubmed_nbib'
    except:
        pass
    
    return 'unknown'


def parse_citations(file_obj, filename: str) -> pd.DataFrame:
    """
    Main entry point for parsing citation files.
    Automatically detects format and parses accordingly.
    """
    # Read content for format detection
    content = file_obj.read()
    file_format = detect_format(filename, content)
    
    # Reset file pointer
    file_obj = io.BytesIO(content)
    
    # Parse based on detected format
    if file_format == 'pubmed_xml':
        return parse_pubmed_xml(file_obj)
    elif file_format == 'ris':
        file_obj = io.StringIO(content.decode('utf-8', errors='ignore'))
        return parse_ris(file_obj)
    elif file_format == 'csv':
        file_obj = io.StringIO(content.decode('utf-8', errors='ignore'))
        return parse_csv(file_obj)
    elif file_format == 'endnote_xml':
        return parse_endnote_xml(file_obj)
    else:
        raise ValueError(f"Unsupported file format: {file_format}")