"""
Data validation module for citation quality assurance
Ensures citations have required fields, especially abstracts
"""
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
import re

logger = logging.getLogger(__name__)


class CitationValidator:
    """Validates citation data quality before database insertion"""
    
    def __init__(self):
        self.validation_results = []
        self.stats = {
            "total": 0,
            "valid": 0,
            "missing_abstract": 0,
            "missing_title": 0,
            "invalid_year": 0,
            "invalid_id": 0,
            "enhanced": 0
        }
    
    def validate_citations(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, any]]:
        """
        Validate and enhance citation data.
        
        Returns:
            Tuple of (validated_df, validation_stats)
        """
        self.stats["total"] = len(df)
        validated_rows = []
        
        for idx, row in df.iterrows():
            validated_row, issues = self.validate_single_citation(row.to_dict())
            
            if issues:
                self.validation_results.append({
                    'citation_id': validated_row.get('id', f'row_{idx}'),
                    'title': validated_row.get('title', 'Unknown')[:50],
                    'issues': issues
                })
            
            validated_rows.append(validated_row)
        
        # Create validated DataFrame
        validated_df = pd.DataFrame(validated_rows)
        
        # Generate summary report
        report = self.generate_validation_report()
        
        return validated_df, report
    
    def validate_single_citation(self, citation: Dict) -> Tuple[Dict, List[str]]:
        """Validate and enhance a single citation"""
        issues = []
        
        # Validate ID
        citation_id = str(citation.get('id', '')).strip()
        if not citation_id or citation_id.lower() == 'nan':
            issues.append("Missing or invalid ID")
            self.stats["invalid_id"] += 1
            # Generate ID from DOI or title if possible
            if citation.get('doi') and str(citation['doi']).lower() != 'nan':
                citation['id'] = citation['doi']
            else:
                # Create hash from title
                title = citation.get('title', '')
                if title:
                    import hashlib
                    citation['id'] = f"hash_{hashlib.md5(title.encode()).hexdigest()[:12]}"
                else:
                    citation['id'] = f"unknown_{self.stats['total']}"
        
        # Validate title
        title = str(citation.get('title', '')).strip()
        if not title or len(title) < 10:
            issues.append("Missing or too short title")
            self.stats["missing_title"] += 1
        
        # Validate abstract - CRITICAL for screening
        abstract = str(citation.get('abstract', '')).strip()
        if not abstract or len(abstract) < 50:
            issues.append("Missing or insufficient abstract")
            self.stats["missing_abstract"] += 1
            
            # Try to enhance abstract from other fields
            if not abstract and citation.get('keywords'):
                keywords = citation['keywords']
                if isinstance(keywords, list) and keywords:
                    citation['abstract'] = f"Keywords: {', '.join(keywords)}"
                    self.stats["enhanced"] += 1
        
        # Validate year
        year = citation.get('year')
        if year:
            try:
                year_int = int(year)
                if year_int < 1900 or year_int > 2100:
                    issues.append(f"Invalid year: {year}")
                    self.stats["invalid_year"] += 1
                    citation['year'] = None
            except (ValueError, TypeError):
                issues.append(f"Invalid year format: {year}")
                self.stats["invalid_year"] += 1
                citation['year'] = None
        
        # Count as valid only if has both title and abstract
        if title and len(title) >= 10 and abstract and len(abstract) >= 50:
            self.stats["valid"] += 1
        
        return citation, issues
    
    def generate_validation_report(self) -> Dict[str, any]:
        """Generate comprehensive validation report"""
        report = {
            "summary": self.stats,
            "quality_score": (self.stats["valid"] / self.stats["total"] * 100) if self.stats["total"] > 0 else 0,
            "critical_issues": {
                "missing_abstracts": self.stats["missing_abstract"],
                "missing_abstracts_pct": (self.stats["missing_abstract"] / self.stats["total"] * 100) if self.stats["total"] > 0 else 0
            },
            "recommendations": []
        }
        
        # Add recommendations based on findings
        if report["critical_issues"]["missing_abstracts_pct"] > 20:
            report["recommendations"].append(
                "⚠️ High percentage of citations missing abstracts. Consider using a different export format "
                "or source that includes full abstracts for better screening accuracy."
            )
        
        if self.stats["invalid_id"] > 0:
            report["recommendations"].append(
                f"Generated IDs for {self.stats['invalid_id']} citations with missing/invalid identifiers."
            )
        
        if self.stats["enhanced"] > 0:
            report["recommendations"].append(
                f"Enhanced {self.stats['enhanced']} citations by using keywords as minimal abstracts."
            )
        
        # Add detailed issues for problematic citations
        report["problematic_citations"] = self.validation_results[:10]  # First 10 issues
        if len(self.validation_results) > 10:
            report["problematic_citations"].append({
                "note": f"... and {len(self.validation_results) - 10} more citations with issues"
            })
        
        return report


def check_abstract_coverage(citations: List[Dict]) -> Dict[str, any]:
    """Quick check of abstract coverage in citation list"""
    total = len(citations)
    with_abstract = sum(1 for c in citations if c.get('abstract') and len(str(c['abstract'])) > 50)
    
    return {
        "total_citations": total,
        "citations_with_abstract": with_abstract,
        "abstract_coverage": (with_abstract / total * 100) if total > 0 else 0,
        "suitable_for_screening": with_abstract >= total * 0.8  # 80% threshold
    }