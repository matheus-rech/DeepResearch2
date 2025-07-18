"""
Citation file parsers for various formats.

This module provides a collection of parsing functions to ingest citation
exports from a number of common reference managers and online databases.
Supported formats include PubMed XML and text exports, RIS, EndNote XML
and generic CSV files.  It also exposes helpers to call the Llama‑Index
readers for ArXiv and PubMed when those optional dependencies are
installed.

The primary entry point is ``parse_citations()``, which will attempt to
auto‑detect the file type and dispatch to the appropriate parser.

Compared to the upstream version of this file, the ``detect_format``
function has been rewritten to be more robust.  The original logic
simply checked for the presence of arbitrary spaces in the XML content
and returned ``pubmed_xml`` for all cases; this prevented EndNote XML
exports from being detected correctly and could cause confusing
``Unsupported file format`` errors.  The new implementation instead
looks for characteristic XML tags (e.g. ``<PubmedArticle>`` vs
``<record>``) or MEDLINE style prefixes to determine the format.

Additionally, this module now defensively handles missing optional
dependencies (like llama‑index) by raising clear ``ImportError``
exceptions when the ArXiv or PubMed search helpers are invoked without
the readers installed.

"""

from __future__ import annotations

import io
import logging
import xml.etree.ElementTree as ET
from typing import Any, Optional, Dict, List

import pandas as pd  # type: ignore
import rispy  # type: ignore
from dateutil import parser as date_parser  # type: ignore
from bs4 import BeautifulSoup  # type: ignore

# Optional imports for academic paper readers
try:
    from llama_index.readers.papers import ArxivReader, PubmedReader  # type: ignore
    LLAMA_READERS_AVAILABLE = True
except Exception:
    LLAMA_READERS_AVAILABLE = False

logger = logging.getLogger(__name__)


def normalize_year(date_str: Any) -> Optional[int]:
    """Extract a four‑digit year from a variety of date representations.

    Given a value that could be an integer, float, string or a Pandas
    ``NaN``, attempt to coerce it into a reasonable publication year.  If
    the year cannot be determined or falls outside of the 1900‑2100
    range, ``None`` is returned.
    """
    if pd.isna(date_str) or not date_str:
        return None

    try:
        if isinstance(date_str, (int, float)):
            year = int(date_str)
            if 1900 <= year <= 2100:
                return year
        else:
            parsed_date = date_parser.parse(str(date_str))
            return parsed_date.year
    except Exception:
        import re
        year_match = re.search(r"\b(19|20)\d{2}\b", str(date_str))
        if year_match:
            return int(year_match.group())
    return None


def parse_pubmed_xml(file_obj: io.BufferedIOBase) -> pd.DataFrame:
    """Parse PubMed XML export format into a DataFrame.

    The PubMed XML format is returned from the NCBI export tool when
    downloading citations in MEDLINE or PubMed XML formats.  Each
    ``<PubmedArticle>`` element represents a single citation.
    """
    tree = ET.parse(file_obj)
    root = tree.getroot()
    citations: List[Dict[str, Any]] = []
    for article in root.findall('.//PubmedArticle'):
        pmid = article.findtext('.//PMID')
        if not pmid:
            continue
        article_elem = article.find('.//Article')
        if article_elem is None:
            continue
        title = article_elem.findtext('.//ArticleTitle', default='')
        abstract_parts: List[str] = []
        abstract_elem = article_elem.find('.//Abstract')
        if abstract_elem is not None:
            for abstract_text in abstract_elem.findall('.//AbstractText'):
                text = abstract_text.text or ''
                label = abstract_text.get('Label', '') or ''
                abstract_parts.append(f"{label}: {text}".strip() if label else text)
        abstract = ' '.join(abstract_parts)
        authors: List[str] = []
        for author in article_elem.findall('.//Author'):
            last_name = author.findtext('LastName', default='')
            fore_name = author.findtext('ForeName', default='')
            if last_name:
                authors.append(f"{last_name} {fore_name}".strip())
        journal = article_elem.findtext('.//Journal/Title', default='')
        pub_date = article_elem.find('.//Journal/JournalIssue/PubDate')
        year: Optional[int] = None
        if pub_date is not None:
            year_text = pub_date.findtext('Year')
            if not year_text:
                medline_date = pub_date.findtext('MedlineDate')
                if medline_date:
                    year_text = medline_date
            year = normalize_year(year_text)
        doi: Optional[str] = None
        for eloc_id in article_elem.findall('.//ELocationID'):
            if eloc_id.get('EIdType') == 'doi':
                doi = eloc_id.text
                break
        mesh_terms: List[str] = [mesh.text for mesh in article.findall('.//MeshHeading/DescriptorName') if mesh.text]
        keywords: List[str] = [kw.text for kw in article.findall('.//Keyword') if kw.text]
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


def parse_ris(file_obj: io.TextIOBase) -> pd.DataFrame:
    """Parse RIS (Research Information Systems) formatted files.

    RIS is a tagged text format used by reference managers like EndNote
    and Mendeley.  ``rispy`` is used to parse the entries into Python
    dictionaries.
    """
    entries = rispy.load(file_obj)
    citations: List[Dict[str, Any]] = []
    for entry in entries:
        year = entry.get('year') or entry.get('publication_year')
        year = normalize_year(year)
        authors: List[str] = []
        if 'authors' in entry:
            authors = entry['authors']
        elif 'first_authors' in entry:
            authors = entry['first_authors']
        cite_id = entry.get('id') or entry.get('doi') or f"RIS_{len(citations)}"
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


def parse_csv(file_obj: io.TextIOBase) -> pd.DataFrame:
    """Parse a generic CSV file containing citation information.

    The parser looks for a variety of common column names and
    normalises them to the canonical keys used throughout the system.
    """
    df = pd.read_csv(file_obj)
    column_map = {
        'pmid': 'id', 'PMID': 'id',
        'Title': 'title', 'Abstract': 'abstract',
        'Year': 'year', 'Publication Year': 'year',
        'Authors': 'authors',
        'Journal': 'journal', 'Journal/Book': 'journal',
        'DOI': 'doi',
        'MeSH Terms': 'mesh_terms', 'Keywords': 'keywords'
    }
    df = df.rename(columns=column_map)
    # Ensure required columns exist
    for col in ['id', 'title', 'abstract', 'authors', 'journal', 'doi', 'mesh_terms', 'keywords']:
        if col not in df.columns:
            df[col] = '' if col != 'authors' else []
    # Normalise years
    df['year'] = df['year'].apply(normalize_year)
    return df[['id', 'title', 'abstract', 'year', 'authors', 'journal', 'doi', 'mesh_terms', 'keywords']]


def parse_endnote_xml(file_obj: io.BufferedIOBase) -> pd.DataFrame:
    """Parse EndNote XML export files.

    EndNote exports use a simple XML structure with ``<record>`` elements
    containing child tags such as ``<title>``, ``<abstract>``,
    ``<contributors>``, etc.
    """
    soup = BeautifulSoup(file_obj.read(), 'xml')
    citations: List[Dict[str, Any]] = []
    for record in soup.find_all('record'):
        rec_number = record.find('rec-number')
        rec_id = f"EndNote_{rec_number.text}" if rec_number else f"EndNote_{len(citations)}"
        title_elem = record.find('title')
        title = title_elem.text if title_elem else ''
        abstract_elem = record.find('abstract')
        abstract = abstract_elem.text if abstract_elem else ''
        authors: List[str] = []
        contributors = record.find('contributors')
        if contributors:
            for author in contributors.find_all('author'):
                if author.text:
                    authors.append(author.text)
        year_elem = record.find('year')
        year = normalize_year(year_elem.text if year_elem else None)
        journal_elem = record.find('secondary-title')
        journal = journal_elem.text if journal_elem else ''
        doi_elem = record.find('electronic-resource-num')
        doi = doi_elem.text if doi_elem else ''
        keywords: List[str] = []
        keywords_elem = record.find('keywords')
        if keywords_elem:
            for keyword in keywords_elem.find_all('keyword'):
                if keyword.text:
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


def parse_pubmed_text(file_obj: io.BufferedIOBase) -> pd.DataFrame:
    """Parse PubMed's MEDLINE text (NBIB) export format.

    The MEDLINE/NBIB format contains lines prefixed with field codes such
    as ``PMID-``, ``TI  -`` (title), ``AB  -`` (abstract) and ``FAU -``
    (author).  This parser extracts those fields and returns a
    DataFrame.
    """
    import re
    content = file_obj.read().decode('utf-8', errors='ignore')
    citations: List[Dict[str, Any]] = []
    entries = re.split(r'\n(?=PMID-)', content)
    for entry in entries:
        if not entry.strip():
            continue
        lines = entry.strip().split('\n')
        if not lines:
            continue
        citation: Dict[str, Any] = {
            'id': '', 'title': '', 'abstract': '', 'year': None,
            'authors': [], 'journal': '', 'doi': '',
            'mesh_terms': [], 'keywords': [],
            'raw_data': {'source': 'pubmed_text'}
        }
        full_text = '\n'.join(lines)
        pmid_match = re.search(r'PMID-\s*(\d+)', full_text)
        if pmid_match:
            citation['id'] = f"PMID:{pmid_match.group(1)}"
        doi_match = re.search(r'LID\s*-\s*(10\.\S+)\s*\[doi\]', full_text, re.IGNORECASE)
        if doi_match:
            citation['doi'] = doi_match.group(1)
        # Title: capture text between TI - and next field prefix
        title_match = re.search(r'TI\s*-\s*(.+?)(?=\n[A-Z]{2}\s*-)', full_text, re.DOTALL)
        if title_match:
            citation['title'] = title_match.group(1).strip().replace('\n', ' ')
        abstract_match = re.search(r'AB\s*-\s*(.+?)(?=\n[A-Z]{2}\s*-)', full_text, re.DOTALL)
        if abstract_match:
            citation['abstract'] = abstract_match.group(1).strip().replace('\n', ' ')
        authors = re.findall(r'FAU\s*-\s*(.+)', full_text)
        citation['authors'] = [a.strip() for a in authors]
        journal_match = re.search(r'TA\s*-\s*(.+)', full_text)
        if journal_match:
            citation['journal'] = journal_match.group(1).strip()
        date_match = re.search(r'DP\s*-\s*(\d{4})', full_text)
        if date_match:
            citation['year'] = int(date_match.group(1))
        mesh_terms: List[str] = []
        for mesh in re.findall(r'MH\s*-\s*([^\n]+)', full_text):
            mesh_terms.append(mesh.strip())
        citation['mesh_terms'] = mesh_terms
        if citation['id'] or citation['title']:
            citations.append(citation)
    return pd.DataFrame(citations)


def detect_format(filename: str, content: bytes) -> str:
    """Detect the citation file format based on filename and file content.

    The detection routine follows a hierarchy of checks:
    1. File extension – obvious extensions like ``.ris`` and ``.csv`` are
       returned immediately.
    2. XML files are disambiguated by scanning for characteristic tags.
       A PubMed XML export contains ``<PubmedArticle>`` elements while
       EndNote exports contain ``<record>`` elements.
    3. Plain text files are scanned for MEDLINE field codes (``PMID:``,
       ``TI  -``, etc.) to detect PubMed text exports.
    4. As a last resort the beginning of the file is searched for tags
       like ``TY  -`` which indicate an RIS file.
    If no format can be confidently determined ``'unknown'`` is
    returned.
    """
    filename_lower = filename.lower()
    # Extension based checks
    if filename_lower.endswith('.ris'):
        return 'ris'
    if filename_lower.endswith('.csv'):
        return 'csv'
    if filename_lower.endswith('.nbib'):
        return 'pubmed_nbib'
    if filename_lower.endswith('.xml'):
        content_str = content.decode('utf-8', errors='ignore')
        lower = content_str.lower()
        # Distinguish between PubMed and EndNote XML by tag
        if '<pubmedarticle' in lower:
            return 'pubmed_xml'
        if '<record' in lower or '<records' in lower:
            return 'endnote_xml'
        return 'unknown_xml'
    if filename_lower.endswith('.txt'):
        # Look for MEDLINE style field codes near the start of the file
        content_str = content.decode('utf-8', errors='ignore')[:2000]
        if any(prefix in content_str for prefix in ['PMID:', 'PMID-', 'TI  -', 'AB  -', 'FAU  -', 'AU  -', 'LID  -', 'DP  -']):
            return 'pubmed_text'
    # Fallback based on content regardless of extension
    try:
        snippet = content.decode('utf-8', errors='ignore')[:2000].lower()
        if 'ty  -' in snippet:
            return 'ris'
        if '<pubmedarticle' in snippet:
            return 'pubmed_xml'
        if '<record' in snippet or '<records' in snippet:
            return 'endnote_xml'
        if snippet.startswith('pmid-') or 'pmid:' in snippet:
            return 'pubmed_text'
        if 'doi:' in snippet:
            return 'pubmed_text'
    except Exception:
        pass
    return 'unknown'


def parse_citations(file_obj: io.BufferedIOBase, filename: str) -> pd.DataFrame:
    """Main entry point to parse uploaded citation files.

    ``parse_citations`` will read the entire file into memory, detect the
    format using ``detect_format`` and then delegate to the appropriate
    parser.  The caller should provide the original filename so that
    extension based heuristics can be applied.
    """
    content = file_obj.read()
    file_format = detect_format(filename, content)
    # reset pointer
    file_obj = io.BytesIO(content)
    if file_format == 'pubmed_xml':
        return parse_pubmed_xml(file_obj)
    if file_format == 'ris':
        return parse_ris(io.StringIO(content.decode('utf-8', errors='ignore')))
    if file_format == 'csv':
        return parse_csv(io.StringIO(content.decode('utf-8', errors='ignore')))
    if file_format == 'endnote_xml':
        return parse_endnote_xml(file_obj)
    if file_format in ('pubmed_text', 'pubmed_nbib'):
        return parse_pubmed_text(file_obj)
    raise ValueError(f"Unsupported file format: {file_format}")


def parse_arxiv_search(search_query: str, max_results: int = 10) -> pd.DataFrame:
    """Fetch papers from ArXiv using the llama‑index ``ArxivReader``.

    Requires the optional ``llama_index.readers.papers`` package.  If
    missing, an ``ImportError`` is raised.  The returned DataFrame
    contains standardised citation fields.
    """
    if not LLAMA_READERS_AVAILABLE:
        raise ImportError("Please install llama-index-readers-papers to use ArXiv search")
    loader = ArxivReader()
    documents, abstracts = loader.load_papers_and_abstracts(search_query=search_query, max_results=max_results)
    citations: List[Dict[str, Any]] = []
    for doc, abstract in zip(documents, abstracts):
        metadata = doc.metadata
        authors: Any = metadata.get('authors', [])
        if isinstance(authors, str):
            authors = [authors]
        published = metadata.get('published', '')
        year = normalize_year(published) if published else None
        citations.append({
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
        })
    return pd.DataFrame(citations)


def parse_pubmed_search(search_query: str, max_results: int = 10) -> pd.DataFrame:
    """Fetch papers from PubMed via the llama‑index ``PubmedReader``.

    This helper requires the optional llama‑index readers package.  It
    performs a PubMed search and returns a DataFrame in the canonical
    citation format.
    """
    if not LLAMA_READERS_AVAILABLE:
        raise ImportError("Please install llama-index-readers-papers to use PubMed search")
    loader = PubmedReader()
    documents = loader.load_data(search_query=search_query, max_results=max_results)
    citations: List[Dict[str, Any]] = []
    for doc in documents:
        metadata = doc.metadata
        authors_str = metadata.get('Authors', '') or ''
        authors = [a.strip() for a in authors_str.split(';')] if authors_str else []
        pub_date = metadata.get('PubDate', '')
        year = normalize_year(pub_date)
        citations.append({
            'id': f"PMID:{metadata.get('PubmedId', '')}",
            'title': metadata.get('Title', ''),
            'abstract': doc.text,
            'year': year,
            'authors': authors,
            'journal': metadata.get('Journal', ''),
            'doi': metadata.get('DOI', ''),
            'mesh_terms': metadata.get('MeshHeadings', '').split(';') if metadata.get('MeshHeadings') else [],
            'keywords': metadata.get('Keywords', '').split(';') if metadata.get('Keywords') else [],
            'raw_data': metadata
        })
    return pd.DataFrame(citations)
