#!/usr/bin/env python3
"""
Claude Code SDK Integration for Deep Research
Leverages Claude's capabilities for better parsing, structured output, and workflow
"""
import os
import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import subprocess

@dataclass
class CitationAnalysis:
    """Structured citation analysis result"""
    title: str
    relevance_score: float
    inclusion_decision: str
    reasoning: str
    key_findings: List[str]
    limitations: List[str]
    matches_criteria: Dict[str, bool]

class ClaudeResearchIntegration:
    """Integrate Claude Code SDK for systematic review screening"""
    
    def __init__(self):
        self.claude_available = self._check_claude_sdk()
    
    def _check_claude_sdk(self) -> bool:
        """Check if Claude Code SDK is available"""
        try:
            result = subprocess.run(['claude-code', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    async def parse_citation_with_claude(self, citation_text: str) -> Dict[str, Any]:
        """Use Claude to parse citations with perfect structure"""
        prompt = f"""
        Parse this citation and extract structured data.
        Return JSON with: title, authors, year, journal, abstract, doi
        
        Citation: {citation_text}
        
        Respond ONLY with valid JSON, no explanations.
        """
        
        if self.claude_available:
            # Use Claude Code SDK
            result = await self._run_claude_sdk(prompt, output_format='json')
            return json.loads(result)
        else:
            # Fallback to API or manual parsing
            return self._fallback_parse(citation_text)
    
    async def screen_with_claude(self, 
                                citation: Dict[str, Any], 
                                criteria: Dict[str, str]) -> CitationAnalysis:
        """Use Claude for intelligent screening decisions"""
        prompt = f"""
        Analyze this citation against the PICOTT criteria.
        
        Citation:
        Title: {citation.get('title')}
        Abstract: {citation.get('abstract')}
        Year: {citation.get('year')}
        
        PICOTT Criteria:
        Population: {criteria.get('population')}
        Intervention: {criteria.get('intervention')}
        Comparison: {criteria.get('comparison')}
        Outcomes: {criteria.get('outcomes')}
        Timeframe: {criteria.get('timeframe')}
        Study Types: {criteria.get('study_types')}
        
        Provide a structured analysis with:
        1. Relevance score (0-1)
        2. Include/Exclude decision
        3. Detailed reasoning
        4. Key findings
        5. Limitations
        6. Which criteria are met
        
        Return as JSON matching CitationAnalysis structure.
        """
        
        if self.claude_available:
            result = await self._run_claude_sdk(prompt, output_format='json')
            data = json.loads(result)
            return CitationAnalysis(**data)
        else:
            return self._fallback_screening(citation, criteria)
    
    async def generate_screening_report(self, 
                                      results: List[CitationAnalysis]) -> str:
        """Use Claude to generate comprehensive screening report"""
        prompt = f"""
        Generate a systematic review screening report.
        
        Screening Results:
        - Total citations: {len(results)}
        - Included: {sum(1 for r in results if r.inclusion_decision == 'include')}
        - Excluded: {sum(1 for r in results if r.inclusion_decision == 'exclude')}
        
        Create a well-structured markdown report with:
        1. Executive Summary
        2. Methodology
        3. Results by criterion
        4. Quality assessment
        5. Recommendations
        
        Make it publication-ready.
        """
        
        if self.claude_available:
            return await self._run_claude_sdk(prompt, output_format='markdown')
        else:
            return self._generate_basic_report(results)
    
    async def validate_criteria_with_claude(self, criteria: Dict[str, str]) -> Dict[str, Any]:
        """Use Claude to validate and improve PICOTT criteria"""
        prompt = f"""
        Review these PICOTT criteria for systematic review:
        {json.dumps(criteria, indent=2)}
        
        Check for:
        1. Clarity and specificity
        2. Potential ambiguities
        3. Missing elements
        4. Suggestions for improvement
        
        Return structured feedback as JSON.
        """
        
        if self.claude_available:
            result = await self._run_claude_sdk(prompt, output_format='json')
            return json.loads(result)
        else:
            return {"valid": True, "suggestions": []}
    
    async def _run_claude_sdk(self, prompt: str, output_format: str = 'text') -> str:
        """Execute Claude Code SDK command"""
        cmd = ['claude-code', '--json' if output_format == 'json' else '--text']
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate(prompt.encode())
        
        if process.returncode != 0:
            raise Exception(f"Claude SDK error: {stderr.decode()}")
        
        return stdout.decode().strip()
    
    def _fallback_parse(self, citation_text: str) -> Dict[str, Any]:
        """Fallback parsing without Claude SDK"""
        # Basic parsing logic
        return {
            "title": citation_text.split('\n')[0] if citation_text else "",
            "authors": "Unknown",
            "year": 2024,
            "journal": "Unknown",
            "abstract": citation_text,
            "doi": ""
        }
    
    def _fallback_screening(self, citation: Dict[str, Any], 
                           criteria: Dict[str, str]) -> CitationAnalysis:
        """Fallback screening without Claude SDK"""
        # Basic keyword matching
        abstract = citation.get('abstract', '').lower()
        title = citation.get('title', '').lower()
        
        matches = {}
        score = 0.0
        
        for key, value in criteria.items():
            if value and value.lower() in abstract + title:
                matches[key] = True
                score += 1/len(criteria)
            else:
                matches[key] = False
        
        return CitationAnalysis(
            title=citation.get('title', ''),
            relevance_score=score,
            inclusion_decision='include' if score > 0.5 else 'exclude',
            reasoning=f"Matched {sum(matches.values())}/{len(criteria)} criteria",
            key_findings=[],
            limitations=[],
            matches_criteria=matches
        )
    
    def _generate_basic_report(self, results: List[CitationAnalysis]) -> str:
        """Generate basic report without Claude SDK"""
        included = [r for r in results if r.inclusion_decision == 'include']
        excluded = [r for r in results if r.inclusion_decision == 'exclude']
        
        report = f"""# Systematic Review Screening Report

## Summary
- Total citations screened: {len(results)}
- Citations included: {len(included)}
- Citations excluded: {len(excluded)}
- Inclusion rate: {len(included)/len(results)*100:.1f}%

## Included Citations
"""
        for i, citation in enumerate(included, 1):
            report += f"\n{i}. {citation.title}\n"
            report += f"   - Score: {citation.relevance_score:.2f}\n"
            report += f"   - Reason: {citation.reasoning}\n"
        
        return report

# Enhanced Deep Research integration
class EnhancedDeepResearch:
    """Enhanced Deep Research with Claude Code SDK"""
    
    def __init__(self):
        self.claude = ClaudeResearchIntegration()
    
    async def intelligent_screening(self, 
                                  citations: List[Dict[str, Any]], 
                                  criteria: Dict[str, str]) -> Dict[str, Any]:
        """Run intelligent screening with Claude integration"""
        
        # First, validate criteria with Claude
        validation = await self.claude.validate_criteria_with_claude(criteria)
        
        if validation.get('suggestions'):
            print("📝 Claude suggests improving criteria:")
            for suggestion in validation['suggestions']:
                print(f"   - {suggestion}")
        
        # Screen each citation
        results = []
        for citation in citations:
            analysis = await self.claude.screen_with_claude(citation, criteria)
            results.append(analysis)
            
            # Real-time progress with structured output
            print(f"📄 {analysis.title[:50]}...")
            print(f"   Score: {analysis.relevance_score:.2f}")
            print(f"   Decision: {analysis.inclusion_decision.upper()}")
        
        # Generate comprehensive report
        report = await self.claude.generate_screening_report(results)
        
        return {
            'results': [asdict(r) for r in results],
            'report': report,
            'statistics': {
                'total': len(results),
                'included': sum(1 for r in results if r.inclusion_decision == 'include'),
                'excluded': sum(1 for r in results if r.inclusion_decision == 'exclude'),
                'average_score': sum(r.relevance_score for r in results) / len(results)
            }
        }

# CLI Integration
async def main():
    """Example usage of Claude-enhanced Deep Research"""
    
    # Sample data
    citations = [
        {
            'title': 'Effects of continuous glucose monitoring on glycemic control',
            'abstract': 'A randomized controlled trial of CGM in adults with type 2 diabetes...',
            'year': 2023
        }
    ]
    
    criteria = {
        'population': 'Adults with type 2 diabetes',
        'intervention': 'Continuous glucose monitoring',
        'comparison': 'Standard care',
        'outcomes': 'HbA1c levels',
        'timeframe': '6 months',
        'study_types': 'RCTs'
    }
    
    # Run enhanced screening
    enhanced = EnhancedDeepResearch()
    results = await enhanced.intelligent_screening(citations, criteria)
    
    print("\n📊 SCREENING COMPLETE!")
    print(f"Included: {results['statistics']['included']}")
    print(f"Excluded: {results['statistics']['excluded']}")
    print(f"\n📄 Full report saved to: screening_report.md")
    
    with open('screening_report.md', 'w') as f:
        f.write(results['report'])

if __name__ == "__main__":
    asyncio.run(main())