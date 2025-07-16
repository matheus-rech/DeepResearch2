"""
ICE (Internal Consistency Evaluation) Critic Module
Analyzes screening decisions for consistency and potential issues
"""
import re
from typing import List, Dict, Any
from collections import Counter


def analyze_screening_consistency(
    screening_results: List[Dict[str, Any]],
    pico_criteria: Dict[str, str]
) -> Dict[str, Any]:
    """
    Analyze screening results for internal consistency and potential issues.
    
    Args:
        screening_results: List of screening decisions
        pico_criteria: PICOTT criteria used for screening
        
    Returns:
        Dictionary with identified issues and summary statistics
    """
    issues = []
    
    # Analysis 1: Check for missing or incomplete PICOTT evaluations
    for result in screening_results:
        if result.get("include") or result.get("decision") == "Include":
            # Check PICOTT elements completeness
            if "picott" in result:
                picott = result["picott"]
                missing_elements = []
                
                # Check each PICOTT element that was specified in criteria
                for element, criteria_value in pico_criteria.items():
                    if criteria_value and criteria_value != "Not specified":
                        element_key = element if element != "study_type" else "studyType"
                        if element_key in picott and (not picott[element_key] or picott[element_key] == "Not found"):
                            missing_elements.append(element)
                
                if missing_elements:
                    issues.append({
                        "type": "PICOTT_elements_missing",
                        "citation_id": result["id"],
                        "severity": "high",
                        "description": f"Citation included but missing PICOTT elements: {', '.join(missing_elements)}",
                        "suggestion": "Verify if abstract contains required PICOTT elements"
                    })
    
    # Analysis 2: Check confidence vs decision consistency
    low_confidence_included = []
    high_confidence_excluded = []
    
    for result in screening_results:
        if result.get("include") and result.get("confidence") == "low":
            low_confidence_included.append(result)
        elif not result.get("include") and result.get("confidence") == "high":
            high_confidence_excluded.append(result)
    
    # Flag citations with conflicting confidence/decision
    for citation in low_confidence_included:
        issues.append({
            "type": "low_confidence_inclusion",
            "citation_id": citation["id"],
            "severity": "medium",
            "description": "Citation included with low confidence",
            "suggestion": "Consider full-text review to confirm inclusion"
        })
    
    for citation in high_confidence_excluded:
        # This might be okay, but worth flagging for review
        issues.append({
            "type": "high_confidence_exclusion",
            "citation_id": citation["id"],
            "severity": "low",
            "description": "Citation excluded with high confidence - verify exclusion reason",
            "suggestion": "Double-check exclusion criteria are correctly applied"
        })
    
    # Analysis 3: Check for inconsistent exclusion reasons
    exclusion_reasons = [r["reason"] for r in screening_results if not r.get("include")]
    reason_counts = Counter(exclusion_reasons)
    
    # Find similar but differently worded reasons
    similar_reasons = find_similar_reasons(list(reason_counts.keys()))
    for group in similar_reasons:
        if len(group) > 1:
            issues.append({
                "type": "inconsistent_exclusion_wording",
                "citation_id": "Multiple",
                "severity": "low",
                "description": f"Similar exclusion reasons with different wording: {group}",
                "suggestion": "Standardize exclusion reason terminology for consistency"
            })
    
    # Analysis 4: Check for potential missing data patterns
    missing_data_patterns = analyze_missing_data_patterns(screening_results)
    for pattern in missing_data_patterns:
        issues.append(pattern)
    
    # Analysis 5: Statistical outlier detection
    inclusion_rate = sum(1 for r in screening_results if r.get("include")) / len(screening_results)
    
    if inclusion_rate < 0.01:
        issues.append({
            "type": "very_low_inclusion_rate",
            "citation_id": "Overall",
            "severity": "medium",
            "description": "Inclusion rate is very low ({:.1f}%)".format(inclusion_rate * 100),
            "suggestion": "Verify screening criteria are not too restrictive"
        })
    elif inclusion_rate > 0.5:
        issues.append({
            "type": "high_inclusion_rate",
            "citation_id": "Overall",
            "severity": "medium",
            "description": "Inclusion rate is high ({:.1f}%)".format(inclusion_rate * 100),
            "suggestion": "Verify screening criteria are sufficiently specific"
        })
    
    # Analysis 6: Check for potential duplicates
    title_similarity_issues = check_title_similarity(screening_results)
    issues.extend(title_similarity_issues)
    
    # Create summary
    summary = {
        "total_issues": len(issues),
        "high_severity": len([i for i in issues if i["severity"] == "high"]),
        "medium_severity": len([i for i in issues if i["severity"] == "medium"]),
        "low_severity": len([i for i in issues if i["severity"] == "low"]),
        "inclusion_rate": inclusion_rate,
        "confidence_distribution": Counter([r.get("confidence", "unknown") for r in screening_results]),
        "unique_exclusion_reasons": len(reason_counts)
    }
    
    return {
        "issues": issues,
        "summary": summary
    }


def find_similar_reasons(reasons: List[str]) -> List[List[str]]:
    """
    Find groups of similar exclusion reasons that might be the same concept.
    """
    groups = []
    used = set()
    
    for i, reason1 in enumerate(reasons):
        if reason1 in used:
            continue
            
        group = [reason1]
        used.add(reason1)
        
        for j, reason2 in enumerate(reasons[i + 1:], i + 1):
            if reason2 in used:
                continue
                
            # Simple similarity check
            if calculate_reason_similarity(reason1, reason2) > 0.7:
                group.append(reason2)
                used.add(reason2)
        
        if len(group) > 1:
            groups.append(group)
    
    return groups


def calculate_reason_similarity(reason1: str, reason2: str) -> float:
    """
    Calculate similarity between two exclusion reasons.
    Simple word overlap approach.
    """
    # Normalize and tokenize
    words1 = set(re.findall(r'\w+', reason1.lower()))
    words2 = set(re.findall(r'\w+', reason2.lower()))
    
    # Remove common words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                  'of', 'with', 'by', 'from', 'not', 'no', 'does', 'did', 'is', 'was'}
    words1 -= stop_words
    words2 -= stop_words
    
    if not words1 or not words2:
        return 0.0
    
    # Jaccard similarity
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


def analyze_missing_data_patterns(screening_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze patterns in missing data that might indicate issues.
    """
    patterns = []
    
    # Check for citations with missing key information
    missing_title = [r for r in screening_results if not r.get("title") or len(r["title"]) < 10]
    if missing_title:
        patterns.append({
            "type": "missing_title_data",
            "citation_id": "{} citations".format(len(missing_title)),
            "severity": "high",
            "description": "{} citations have missing or very short titles".format(len(missing_title)),
            "suggestion": "Verify data import was successful for these citations"
        })
    
    # Check for suspiciously uniform decisions in sequence
    sequence_patterns = check_sequence_patterns(screening_results)
    patterns.extend(sequence_patterns)
    
    return patterns


def check_sequence_patterns(screening_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Check for suspicious patterns in sequential screening decisions.
    """
    issues = []
    
    # Look for long sequences of the same decision
    max_sequence = 10  # Flag if more than 10 consecutive same decisions
    current_decision = None
    sequence_start = 0
    sequence_length = 0
    
    for i, result in enumerate(screening_results):
        decision = result.get("include")
        
        if decision == current_decision:
            sequence_length += 1
        else:
            if sequence_length > max_sequence:
                issues.append({
                    "type": "suspicious_sequence_pattern",
                    "citation_id": "Citations {} to {}".format(sequence_start, i - 1),
                    "severity": "medium",
                    "description": "{} consecutive {}".format(sequence_length, 'inclusions' if current_decision else 'exclusions'),
                    "suggestion": "Review for potential automation bias or fatigue"
                })
            
            current_decision = decision
            sequence_start = i
            sequence_length = 1
    
    return issues


def check_title_similarity(screening_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Check for potential duplicate citations based on title similarity.
    """
    issues = []
    
    # Check for very similar titles with different decisions
    for i, result1 in enumerate(screening_results):
        for j, result2 in enumerate(screening_results[i + 1:], i + 1):
            if result1.get("title") and result2.get("title"):
                similarity = calculate_title_similarity(result1["title"], result2["title"])
                
                if similarity > 0.85:  # Very similar titles
                    if result1.get("include") != result2.get("include"):
                        issues.append({
                            "type": "similar_titles_different_decisions",
                            "citation_id": "{} vs {}".format(result1['id'], result2['id']),
                            "severity": "high",
                            "description": "Very similar titles with different screening decisions",
                            "suggestion": "Check if these are duplicate citations or require consistent decisions"
                        })
                    elif similarity > 0.95:  # Likely duplicates
                        issues.append({
                            "type": "potential_duplicate",
                            "citation_id": "{} and {}".format(result1['id'], result2['id']),
                            "severity": "medium",
                            "description": "Potential duplicate citations detected",
                            "suggestion": "Verify if these are true duplicates and handle accordingly"
                        })
    
    return issues


def calculate_title_similarity(title1: str, title2: str) -> float:
    """
    Calculate similarity between two titles.
    """
    # Normalize
    title1_norm = re.sub(r'[^\w\s]', '', title1.lower()).split()
    title2_norm = re.sub(r'[^\w\s]', '', title2.lower()).split()
    
    if not title1_norm or not title2_norm:
        return 0.0
    
    # Use Jaccard similarity
    set1 = set(title1_norm)
    set2 = set(title2_norm)
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return intersection / union if union > 0 else 0.0


def generate_ice_report(
    screening_results: List[Dict[str, Any]],
    pico_criteria: Dict[str, str],
    issues: List[Dict[str, Any]]
) -> str:
    """
    Generate a formatted ICE report.
    """
    report = f"""
# Internal Consistency Evaluation Report

## Screening Overview
- Total Citations Screened: {len(screening_results)}
- Included: {sum(1 for r in screening_results if r.get('include'))}
- Excluded: {sum(1 for r in screening_results if not r.get('include'))}

## PICO Criteria Applied
- Population: {pico_criteria.get('population', 'Not specified')}
- Intervention: {pico_criteria.get('intervention', 'Not specified')}
- Comparator: {pico_criteria.get('comparator', 'Not specified')}
- Outcome: {pico_criteria.get('outcome', 'Not specified')}

## Issues Identified
Total Issues: {len(issues)}
- High Severity: {len([i for i in issues if i['severity'] == 'high'])}
- Medium Severity: {len([i for i in issues if i['severity'] == 'medium'])}
- Low Severity: {len([i for i in issues if i['severity'] == 'low'])}

### High Severity Issues
"""
    
    for issue in [i for i in issues if i['severity'] == 'high']:
        report += f"\n- **{issue['type']}** ({issue['citation_id']}): {issue['description']}\n"
        report += f"  - Suggestion: {issue['suggestion']}\n"
    
    report += "\n### Medium Severity Issues\n"
    for issue in [i for i in issues if i['severity'] == 'medium'][:5]:  # Limit to 5
        report += f"\n- **{issue['type']}** ({issue['citation_id']}): {issue['description']}\n"
    
    if len([i for i in issues if i['severity'] == 'medium']) > 5:
        report += f"\n... and {len([i for i in issues if i['severity'] == 'medium']) - 5} more medium severity issues\n"
    
    report += "\n## Recommendations\n"
    report += "1. Review all high severity issues before finalizing screening decisions\n"
    report += "2. Consider standardizing exclusion reason terminology\n"
    report += "3. Verify PICO criteria are consistently applied\n"
    report += "4. Check for and resolve any duplicate citations\n"
    
    return report