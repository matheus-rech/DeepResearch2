"""
PubMed-compatible export formats for citations
Implements native PubMed export formats as used on pubmed.ncbi.nlm.nih.gov
"""
import json
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def export_summary_text(citations: List[Dict[str, Any]]) -> str:
    """
    Export citations in PubMed Summary (text) format - NLM citation style.
    
    Example output:
    1. Smith J, Jones M. Title of article. J Med Sci. 2023;45(3):123-134. doi: 10.1234/example. PMID: 12345678.
    """
    output_lines = []
    
    for i, citation in enumerate(citations, 1):
        # Authors
        authors = citation.get('authors', [])
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except Exception:
                authors = [authors] if authors else []
        
        if authors:
            # Format authors as "Smith J, Jones M"
            formatted_authors = []
            for author in authors[:3]:  # Show first 3 authors
                if isinstance(author, dict):
                    last = author.get('family', author.get('given', ''))
                    first = author.get('given', '')
                    if first:
                        formatted_authors.append(f"{last} {first[0]}")
                    else:
                        formatted_authors.append(last)
                else:
                    # Handle string format "Last, First" or "Last First"
                    parts = str(author).replace(',', ' ').split()
                    if len(parts) >= 2:
                        formatted_authors.append(f"{parts[0]} {parts[1][0]}")
                    else:
                        formatted_authors.append(parts[0] if parts else author)
            
            if len(authors) > 3:
                formatted_authors.append("et al")
            
            author_str = ", ".join(formatted_authors) + ". "
        else:
            author_str = ""
        
        # Title
        title = citation.get('title', 'No title')
        if not title.endswith('.'):
            title += '.'
        
        # Journal, year, volume, pages
        journal = citation.get('journal', '')
        year = citation.get('year', '')
        volume = citation.get('volume', '')
        issue = citation.get('issue', '')
        pages = citation.get('pages', '')
        
        # Build journal citation
        journal_parts = []
        if journal:
            journal_parts.append(journal)
        if year:
            journal_parts.append(f"{year}")
        if volume:
            if issue:
                journal_parts.append(f"{volume}({issue})")
            else:
                journal_parts.append(volume)
        if pages:
            journal_parts.append(pages)
        
        journal_str = ". " + ";".join(journal_parts) + "." if journal_parts else ""
        
        # DOI and PMID
        doi = citation.get('doi', '')
        pmid = citation.get('id', '').replace('PMID:', '')
        
        identifiers = []
        if doi:
            identifiers.append(f"doi: {doi}")
        if pmid and pmid.isdigit():
            identifiers.append(f"PMID: {pmid}")
        
        id_str = " " + ". ".join(identifiers) + "." if identifiers else ""
        
        # Combine all parts
        line = f"{i}. {author_str}{title}{journal_str}{id_str}"
        output_lines.append(line)
    
    return "\n\n".join(output_lines)


def export_pubmed_format(citations: List[Dict[str, Any]]) -> str:
    """
    Export citations in PubMed format (MEDLINE format).
    
    Example output:
    PMID- 12345678
    OWN - NLM
    STAT- MEDLINE
    DA  - 20230615
    TI  - Title of the article
    AB  - Abstract text...
    AU  - Smith J
    AU  - Jones M
    ...
    """
    output_records = []
    
    for citation in citations:
        lines = []
        
        # PMID
        pmid = citation.get('id', '').replace('PMID:', '')
        if pmid:
            lines.append(f"PMID- {pmid}")
        
        # Owner
        lines.append("OWN - NLM")
        lines.append("STAT- MEDLINE")
        
        # Date
        current_date = datetime.now().strftime("%Y%m%d")
        lines.append(f"DCOM- {current_date}")
        
        # Title
        title = citation.get('title', '')
        if title:
            lines.append(f"TI  - {title}")
        
        # Abstract
        abstract = citation.get('abstract', '')
        if abstract:
            # Split long abstracts into multiple lines
            words = abstract.split()
            current_line = "AB  - "
            line_length = 0
            
            for word in words:
                if line_length + len(word) + 1 > 80:
                    lines.append(current_line.rstrip())
                    current_line = "      " + word + " "
                    line_length = len(word) + 1
                else:
                    current_line += word + " "
                    line_length += len(word) + 1
            
            if current_line.strip():
                lines.append(current_line.rstrip())
        
        # Authors
        authors = citation.get('authors', [])
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except Exception:
                authors = [authors] if authors else []
        
        for author in authors:
            if isinstance(author, dict):
                name = f"{author.get('family', '')} {author.get('given', '')}"
            else:
                name = str(author)
            lines.append(f"AU  - {name}")
        
        # Journal
        journal = citation.get('journal', '')
        if journal:
            lines.append(f"TA  - {journal}")
        
        # Year
        year = citation.get('year', '')
        if year:
            lines.append(f"DP  - {year}")
        
        # DOI
        doi = citation.get('doi', '')
        if doi:
            lines.append(f"LID - {doi} [doi]")
        
        # MeSH terms
        mesh_terms = citation.get('mesh_terms', [])
        if isinstance(mesh_terms, str):
            try:
                mesh_terms = json.loads(mesh_terms)
            except Exception:
                mesh_terms = []
        
        for term in mesh_terms:
            lines.append(f"MH  - {term}")
        
        lines.append("")  # Empty line between records
        output_records.append("\n".join(lines))
    
    return "\n".join(output_records)


def export_pmid_list(citations: List[Dict[str, Any]]) -> str:
    """
    Export just the PMIDs, one per line.
    """
    pmids = []
    for citation in citations:
        pmid = citation.get('id', '').replace('PMID:', '')
        if pmid:
            pmids.append(pmid)
    
    return "\n".join(pmids)


def export_abstract_text(citations: List[Dict[str, Any]]) -> str:
    """
    Export citations with full abstracts in text format.
    """
    output_records = []
    
    for i, citation in enumerate(citations, 1):
        lines = []
        
        # Number and title
        title = citation.get('title', 'No title')
        lines.append(f"{i}. {title}")
        lines.append("")
        
        # Authors
        authors = citation.get('authors', [])
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except Exception:
                authors = [authors] if authors else []
        
        if authors:
            author_names = []
            for author in authors:
                if isinstance(author, dict):
                    name = f"{author.get('given', '')} {author.get('family', '')}"
                else:
                    name = str(author)
                author_names.append(name.strip())
            
            lines.append("Authors: " + "; ".join(author_names))
        
        # Journal info
        journal_parts = []
        if citation.get('journal'):
            journal_parts.append(citation['journal'])
        if citation.get('year'):
            journal_parts.append(str(citation['year']))
        if citation.get('volume'):
            vol = f"Vol. {citation['volume']}"
            if citation.get('issue'):
                vol += f"({citation['issue']})"
            journal_parts.append(vol)
        if citation.get('pages'):
            journal_parts.append(f"pp. {citation['pages']}")
        
        if journal_parts:
            lines.append("Journal: " + ", ".join(journal_parts))
        
        # Identifiers
        identifiers = []
        if citation.get('doi'):
            identifiers.append(f"DOI: {citation['doi']}")
        pmid = citation.get('id', '').replace('PMID:', '')
        if pmid:
            identifiers.append(f"PMID: {pmid}")
        
        if identifiers:
            lines.append(" | ".join(identifiers))
        
        lines.append("")
        
        # Abstract
        abstract = citation.get('abstract', 'No abstract available.')
        lines.append("Abstract:")
        lines.append(abstract)
        lines.append("")
        lines.append("-" * 80)
        lines.append("")
        
        output_records.append("\n".join(lines))
    
    return "\n".join(output_records)


def export_csv(citations: List[Dict[str, Any]]) -> str:
    """
    Export citations as CSV format compatible with PubMed's CSV export.
    """
    # Prepare data for DataFrame
    rows = []
    
    for citation in citations:
        # Parse authors
        authors = citation.get('authors', [])
        if isinstance(authors, str):
            try:
                authors = json.loads(authors)
            except Exception:
                authors = [authors] if authors else []
        
        # Format authors
        author_names = []
        for author in authors:
            if isinstance(author, dict):
                name = f"{author.get('given', '')} {author.get('family', '')}"
            else:
                name = str(author)
            author_names.append(name.strip())
        
        # Parse other JSON fields
        mesh_terms = citation.get('mesh_terms', [])
        if isinstance(mesh_terms, str):
            try:
                mesh_terms = json.loads(mesh_terms)
            except Exception:
                mesh_terms = []
        
        keywords = citation.get('keywords', [])
        if isinstance(keywords, str):
            try:
                keywords = json.loads(keywords)
            except Exception:
                keywords = []
        
        row = {
            'Title': citation.get('title', ''),
            'Authors': '; '.join(author_names),
            'Journal': citation.get('journal', ''),
            'Year': citation.get('year', ''),
            'Volume': citation.get('volume', ''),
            'Issue': citation.get('issue', ''),
            'Pages': citation.get('pages', ''),
            'DOI': citation.get('doi', ''),
            'PMID': citation.get('id', '').replace('PMID:', ''),
            'Abstract': citation.get('abstract', ''),
            'MeSH Terms': '; '.join(mesh_terms),
            'Keywords': '; '.join(keywords)
        }
        rows.append(row)
    
    # Create DataFrame and export to CSV
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def export_nbib(citations: List[Dict[str, Any]]) -> str:
    """
    Export citations in NBIB format (MEDLINE/PubMed format) for citation managers.
    This is similar to PubMed format but uses specific fields for citation managers.
    """
    # NBIB is essentially the same as PubMed format
    # but may include additional fields for citation managers
    return export_pubmed_format(citations)


def export_citations(citations: List[Dict[str, Any]], format_type: str) -> tuple[str, str, str]:
    """
    Export citations in the specified PubMed-compatible format.
    
    Args:
        citations: List of citation dictionaries
        format_type: One of 'summary', 'pubmed', 'pmid', 'abstract', 'csv', 'nbib'
        
    Returns:
        Tuple of (content, filename, content_type)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if format_type == 'summary':
        content = export_summary_text(citations)
        filename = f"pubmed_summary_{timestamp}.txt"
        content_type = "text/plain"
    
    elif format_type == 'pubmed':
        content = export_pubmed_format(citations)
        filename = f"pubmed_format_{timestamp}.txt"
        content_type = "text/plain"
    
    elif format_type == 'pmid':
        content = export_pmid_list(citations)
        filename = f"pmid_list_{timestamp}.txt"
        content_type = "text/plain"
    
    elif format_type == 'abstract':
        content = export_abstract_text(citations)
        filename = f"abstracts_{timestamp}.txt"
        content_type = "text/plain"
    
    elif format_type == 'csv':
        content = export_csv(citations)
        filename = f"citations_{timestamp}.csv"
        content_type = "text/csv"
    
    elif format_type == 'nbib':
        content = export_nbib(citations)
        filename = f"citations_{timestamp}.nbib"
        content_type = "application/x-nbib"
    
    else:
        raise ValueError(f"Unknown format type: {format_type}")
    
    return content, filename, content_type