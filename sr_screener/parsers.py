"""
Citation file parsers for various formats
Supports: PubMed XML, RIS, CSV, ArXiv, and more
"""
import xml.etree.ElementTree as ET
from typing import Any, Optional
import pandas as pd
import rispy
import io
from dateutil import parser as date_parser
from bs4 import BeautifulSoup
import logging
import requests

# Optional imports for academic paper readers
try:
    from llama_index.readers.papers import ArxivReader, PubmedReader
    LLAMA_READERS_AVAILABLE = True
except ImportError:
    LLAMA_READERS_AVAILABLE = False
    
logger = logging.getLogger(__name__)


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
            df[field] = df[field].apply(
                lambda x: x.split(';') if isinstance(x, str) else []
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


def parse_pubmed_text(file_obj) -> pd.DataFrame:
    """
    Parse PubMed text export format with abstracts.
    """
    import re
    
    content = file_obj.read().decode('utf-8', errors='ignore')
    citations = []
    
    entries = re.split(r'\n(?=PMID-)', content)
    
    for entry in entries:
        if not entry.strip():
            continue
            
        lines = entry.strip().split('\n')
        if not lines:
            continue
            
        # Extract PMID, DOI, title, abstract, etc.
        citation = {
            'id': '',
            'title': '',
            'abstract': '',
            'year': None,
            'authors': [],
            'journal': '',
            'doi': '',
            'mesh_terms': [],
            'keywords': [],
            'raw_data': {'source': 'pubmed_text'}
        }
        
        full_text = '\n'.join(lines)
        
        # Extract PMID
        pmid_match = re.search(r'PMID-\s*(\d+)', full_text)
        if pmid_match:
            citation['id'] = f"PMID:{pmid_match.group(1)}"
        
        # Extract DOI
        doi_match = re.search(r'LID\s*-\s*(10\.\S+)\s*\[doi\]', full_text, re.IGNORECASE)
        if doi_match:
            citation['doi'] = doi_match.group(1)
        
        # Extract title
        title_match = re.search(r'TI\s*-\s*(.+?)(?=\nPG|\nLID|\nAB|\nAD|\nFAU|\nAU|\nLA|\n\w{2,4}\s*-)', full_text, re.DOTALL)
        if title_match:
            citation['title'] = title_match.group(1).strip().replace('\n', ' ')
        
        # Extract abstract
        abstract_match = re.search(r'AB\s*-\s*(.+?)(?=\nAD|\nFAU|\nAU|\nLA|\n\w{2,4}\s*-)', full_text, re.DOTALL)
        if abstract_match:
            citation['abstract'] = abstract_match.group(1).strip().replace('\n', ' ')
        
        # Extract authors
        authors = []
        author_matches = re.findall(r'FAU\s*-\s*(.+)', full_text)
        for author in author_matches:
            authors.append(author.strip())
        citation['authors'] = authors
        
        # Extract journal
        journal_match = re.search(r'TA\s*-\s*(.+)', full_text)
        if journal_match:
            citation['journal'] = journal_match.group(1).strip()
        
        # Extract year from date
        date_match = re.search(r'DP\s*-\s*(\d{4})', full_text)
        if date_match:
            citation['year'] = int(date_match.group(1))
        
        # Extract MeSH terms
        mesh_terms = []
        mesh_matches = re.findall(r'MH\s*-\s*(.+?)(?:/\*[\w\-]+|\*[\w\-]+|$)', full_text)
        for mesh in mesh_matches:
            mesh_terms.append(mesh.strip())
        citation['mesh_terms'] = mesh_terms
        
        if citation['id'] or citation['title']:
            citations.append(citation)
    
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
    elif filename_lower.endswith('.txt'):
        # Check if it's PubMed abstract format
        content_str = content.decode('utf-8', errors='ignore')[:2000]
        if any(pattern in content_str for pattern in ['PMID:', 'DOI:', 'J Affect Disord', 'Brain Stimul', 'Front Psychiatry']):
            return 'pubmed_text'
    
    # Check by content if no clear extension
    try:
        content_str = content.decode('utf-8', errors='ignore')[:1000]
        if 'TY  -' in content_str:
            return 'ris'
        elif '<PubmedArticle>' in content_str:
            return 'pubmed_xml'
        elif content_str.strip().startswith('PMID-') and any(pattern in content_str for pattern in ['TI  -', 'AB  -', 'FAU -']):
            return 'pubmed_text'  # MEDLINE format with PMID- prefix
        elif content_str.strip().startswith('PMID-'):
            return 'pubmed_nbib'  # NBIB format
        elif any(pattern in content_str for pattern in ['PMID:', 'DOI:', '. 20']):
            return 'pubmed_text'
    except Exception:
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
    elif file_format == 'pubmed_text':
        file_obj = io.BytesIO(content)
        return parse_pubmed_text(file_obj)
    else:
        raise ValueError(f"Unsupported file format: {file_format}")


def parse_arxiv_search(search_query: str, max_results: int = 10) -> pd.DataFrame:
    """
    Fetch papers from ArXiv using search query.
    
    Args:
        search_query: ArXiv search query (e.g., "quantum computing", "au:Karpathy")
        max_results: Maximum number of papers to fetch
        
    Returns:
        DataFrame with standardized citation columns
    """
    if not LLAMA_READERS_AVAILABLE:
        raise ImportError("Please install llama-index-readers-papers to use ArXiv search")
    
    try:
        loader = ArxivReader()
        documents, abstracts = loader.load_papers_and_abstracts(
            search_query=search_query,
            max_results=max_results
        )
        
        citations = []
        for doc, abstract in zip(documents, abstracts):
            # Extract metadata from document
            metadata = doc.metadata
            
            # Extract authors from metadata
            authors = metadata.get('authors', [])
            if isinstance(authors, str):
                authors = [authors]
            
            # Extract year from published date
            published = metadata.get('published', '')
            year = None
            if published:
                year = normalize_year(published)
            
            citation = {
                'id': f"arxiv:{metadata.get('article_id', '')}",
                'title': metadata.get('title', ''),
                'abstract': abstract.text if abstract else metadata.get('summary', ''),
                'year': year,
                'authors': authors,
                'journal': 'arXiv',
                'doi': metadata.get('doi', ''),
                'mesh_terms': [],
                'keywords': metadata.get('categories', '').split() if metadata.get('categories') else [],
                'raw_data': metadata
            }
            citations.append(citation)
        
        return pd.DataFrame(citations)
        
    except Exception as e:
        logger.error(f"Error fetching from ArXiv: {e}")
        raise


def parse_pubmed_search(search_query: str, max_results: int = 10) -> pd.DataFrame:
    """
    Fetch papers from PubMed using search query.
    
    Args:
        search_query: PubMed search query (e.g., "diabetes", "cancer immunotherapy")
        max_results: Maximum number of papers to fetch
        
    Returns:
        DataFrame with standardized citation columns
    """
    if not LLAMA_READERS_AVAILABLE:
        raise ImportError("Please install llama-index-readers-papers to use PubMed search")
    
    try:
        loader = PubmedReader()
        documents = loader.load_data(
            search_query=search_query,
            max_results=max_results
        )
        
        citations = []
        for doc in documents:
            # Extract metadata from document
            metadata = doc.metadata
            
            # Parse authors from metadata
            authors_str = metadata.get('Authors', '')
            authors = [a.strip() for a in authors_str.split(';')] if authors_str else []
            
            # Extract year from publication date
            pub_date = metadata.get('PubDate', '')
            year = normalize_year(pub_date)
            
            citation = {
                'id': f"PMID:{metadata.get('PubmedId', '')}",
                'title': metadata.get('Title', ''),
                'abstract': doc.text,  # The document text contains the abstract
                'year': year,
                'authors': authors,
                'journal': metadata.get('Journal', ''),
                'doi': metadata.get('DOI', ''),
                'mesh_terms': metadata.get('MeshHeadings', '').split(';') if metadata.get('MeshHeadings') else [],
                'keywords': metadata.get('Keywords', '').split(';') if metadata.get('Keywords') else [],
                'raw_data': metadata
            }
            citations.append(citation)
        
        return pd.DataFrame(citations)
        
    except Exception as e:
        logger.error(f"Error fetching from PubMed: {e}")
        raise


def fetch_crossref_abstract(doi: str) -> Optional[str]:
    """
    Fetch abstract from CrossRef API using DOI.
    
    Args:
        doi: DOI identifier (e.g., "10.1234/example")
        
    Returns:
        Abstract text if found, None otherwise
    """
    if not doi or pd.isna(doi) or doi == '':
        return None
    
    # Clean DOI - remove any URL prefix
    if 'doi.org/' in doi:
        doi = doi.split('doi.org/')[-1]
    
    try:
        # CrossRef API endpoint
        url = f"https://api.crossref.org/works/{doi}"
        headers = {
            'User-Agent': 'SystematicReviewScreener/1.0 (mailto:support@example.com)'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            work = data.get('message', {})
            
            # Try to get abstract
            abstract = work.get('abstract')
            if abstract:
                # Clean HTML tags if present
                soup = BeautifulSoup(abstract, 'html.parser')
                return soup.get_text().strip()
        
        return None
        
    except Exception as e:
        logger.debug(f"Could not fetch abstract from CrossRef for DOI {doi}: {e}")
        return None


def enrich_citations_with_crossref(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich citations with missing abstracts from CrossRef.
    
    Args:
        df: DataFrame with citation data
        
    Returns:
        DataFrame with enriched abstracts
    """
    enriched_count = 0
    
    for idx, row in df.iterrows():
        # Only fetch if abstract is missing or too short
        current_abstract = row.get('abstract', '')
        if pd.isna(current_abstract) or len(str(current_abstract).strip()) < 50:
            doi = row.get('doi')
            if doi and not pd.isna(doi):
                logger.info(f"Fetching abstract from CrossRef for DOI: {doi}")
                abstract = fetch_crossref_abstract(doi)
                
                if abstract and len(abstract) >= 50:
                    df.at[idx, 'abstract'] = abstract
                    enriched_count += 1
                    logger.info(f"Successfully enriched abstract for {doi}")
    
    if enriched_count > 0:
        logger.info(f"Enriched {enriched_count} citations with abstracts from CrossRef")
    
    return df
