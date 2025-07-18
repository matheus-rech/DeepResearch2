"""
Multi‑Agent Deep Research pipeline for systematic review screening.

This module orchestrates a series of specialised agents (triage,
clarification, instruction building and screening) to automate the
process of screening research citations.  It is an adaptation of the
original ``multi_agent_research.py`` in DeepResearch2 but with added
environment validation for OpenAI API keys.  The upstream version
constructed an ``OpenAI`` client directly from ``os.getenv('OPENAI_API_KEY')``;
here we look for either ``OPENAI_API_KEY`` or the first entry in
``OPENAI_API_KEYS`` and raise a clear error if no key is configured.

"""

from __future__ import annotations

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from openai import OpenAI  # type: ignore

logger = logging.getLogger(__name__)


def _resolve_api_key() -> str:
    """Resolve an OpenAI API key from the environment.

    Checks ``OPENAI_API_KEY`` first; if absent, splits
    ``OPENAI_API_KEYS`` by comma and returns the first non‑empty key.
    Raises ``EnvironmentError`` if no key is found.
    """
    single = os.getenv('OPENAI_API_KEY')
    if single:
        return single
    multiple = os.getenv('OPENAI_API_KEYS')
    if multiple:
        for key in (k.strip() for k in multiple.split(',')):
            if key:
                return key
    raise EnvironmentError(
        'Missing OpenAI API key. Please set OPENAI_API_KEY or OPENAI_API_KEYS in your environment.'
    )


# Create a shared OpenAI client for all agents
API_KEY: str = _resolve_api_key()
client: OpenAI = OpenAI(api_key=API_KEY, timeout=3600.0)

# Model selection per Deep Research best practices
FAST_MODEL: str = 'gpt-4.1'  # For clarification and triage steps
DEEP_RESEARCH_MODEL: str = 'o3-deep-research-2025-06-26'  # For screening

# Agent prompts for systematic review screening
TRIAGE_AGENT_PROMPT = """
You are a triage agent for systematic review screening. Analyse the screening request and determine:
1. If PICOTT criteria are complete and specific enough
2. If inclusion/exclusion criteria need clarification
3. Whether to route to clarifier agent or directly to instruction builder

Evaluate these aspects:
- Are all PICOTT elements clearly defined?
- Are inclusion/exclusion criteria specific and measurable?
- Is the corpus size reasonable for the criteria?

Output: {"needs_clarification": true/false, "missing_elements": [...], "route_to": "clarifier" or "instruction_builder"}
"""

CLARIFIER_AGENT_PROMPT = """
You are a clarification agent for systematic review screening. Based on the missing elements, ask targeted questions to improve screening precision:

For PICOTT elements:
- Population: Ask for specific demographics, conditions, or characteristics
- Intervention: Request details on dosage, duration, or specific procedures
- Comparator: Clarify control groups or alternative interventions
- Outcome: Specify primary vs secondary outcomes, measurement methods
- Timeframe: Define follow‑up periods or study duration requirements
- Study Type: Clarify acceptable study designs

For criteria:
- Make inclusion/exclusion criteria more specific and measurable
- Resolve any ambiguities or conflicts

Be concise and ask 2–3 focused questions maximum.
"""

INSTRUCTION_BUILDER_PROMPT = """
You are an instruction builder for systematic review screening. Convert the enriched screening criteria into detailed research instructions for the screening agent.

Create a comprehensive screening protocol that includes:

1. **Screening Objective**: Clear statement of what citations to identify

2. **PICOTT Matching Instructions**:
   - For each PICOTT element, specify exact terms or phrases to look for
   - Include synonyms and related terms
   - Specify how to identify each element in abstracts

3. **Decision Rules**:
   - Clear hierarchy of criteria (e.g. exclude first, then apply PICOTT)
   - How to handle missing information
   - Confidence thresholds for decisions

4. **Output Requirements**:
   - Extract exact quotes for each PICOTT element
   - Document which criteria were matched/not matched
   - Provide step‑by‑step reasoning

5. **Quality Checks**:
   - Flag potential duplicates
   - Identify citations needing second review
   - Note any ambiguous cases

OUTPUT ONLY THE SCREENING INSTRUCTIONS IN STRUCTURED FORMAT.
"""

SCREENING_AGENT_PROMPT = """
You are an expert systematic reviewer conducting citation screening. Follow the provided instructions precisely.

For each citation:
1. Extract PICOTT elements with exact quotes
2. Check against all inclusion/exclusion criteria
3. Make screening decision with reasoning
4. Assign confidence level

Output format for each citation:
{
    "id": "citation_id",
    "title": "title",
    "picott": {
        "population": "exact quote or 'Not found'",
        "intervention": "exact quote or 'Not found'",
        "comparison": "exact quote or 'Not found'",
        "outcome": "exact quote or 'Not found'",
        "timeframe": "exact quote or 'Not found'",
        "studyType": "exact quote or 'Not found'"
    },
    "inclusionCriteria": ["matched criteria with supporting quotes"],
    "exclusionCriteria": ["matched criteria with supporting quotes"],
    "reasoning": "Step‑by‑step decision process",
    "decision": "Include" or "Exclude",
    "confidence": "high/medium/low",
    "flags": ["any special considerations"]
}
"""


class MultiAgentScreener:
    """Orchestrates multi‑agent systematic review screening."""

    def __init__(self, mcp_url: str = 'http://localhost:8001/sse/') -> None:
        self.mcp_url = mcp_url
        self.screening_log: List[Dict[str, Any]] = []

    def triage_request(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Triage agent evaluates if criteria need clarification."""
        prompt = f"""
        Evaluate these systematic review screening criteria and respond with valid JSON:

        PICOTT: {json.dumps(criteria.get('pico_criteria', {}), indent=2)}
        Inclusion: {criteria.get('inclusion_criteria', [])}
        Exclusion: {criteria.get('exclusion_criteria', [])}
        Corpus size: {criteria.get('corpus_size', 0)}
        
        Please respond with JSON format containing your evaluation.
        """
        response = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {"role": "system", "content": TRIAGE_AGENT_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    def clarify_criteria(self, criteria: Dict[str, Any], missing_elements: List[str]) -> List[str]:
        """Clarifier agent generates questions for missing elements."""
        prompt = f"""
        Current criteria:
        {json.dumps(criteria, indent=2)}
        
        Missing or unclear elements: {missing_elements}
        
        Generate 2–3 focused clarification questions.
        """
        response = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {"role": "system", "content": CLARIFIER_AGENT_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        questions = response.choices[0].message.content.strip().split('\n')
        return [q.strip() for q in questions if q.strip()]

    def build_instructions(self, criteria: Dict[str, Any], clarifications: Optional[Dict[str, str]] = None) -> str:
        """Instruction builder creates detailed screening protocol."""
        prompt = f"""
        Create screening instructions for:
        
        PICOTT Criteria:
        {json.dumps(criteria.get('pico_criteria', {}), indent=2)}
        
        Inclusion Criteria:
        {json.dumps(criteria.get('inclusion_criteria', []), indent=2)}
        
        Exclusion Criteria:
        {json.dumps(criteria.get('exclusion_criteria', []), indent=2)}
        
        Corpus Size: {criteria.get('corpus_size', 0)} citations
        
        Search Mode: {criteria.get('search_mode', 'fulltext')}
        """
        if clarifications:
            prompt += f"\n\nClarifications provided:\n{json.dumps(clarifications, indent=2)}"
        response = client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {"role": "system", "content": INSTRUCTION_BUILDER_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content

    def screen_citations(self, instructions: str, batch_size: int = 20) -> List[Dict[str, Any]]:
        """Screening agent performs the actual citation screening."""
        screening_prompt = f"""
        {SCREENING_AGENT_PROMPT}
        
        {instructions}
        
        You have access to an MCP server with search and fetch tools to access the citation corpus.
        Screen all citations systematically using these tools.
        
        Process efficiently by:
        1. Search for citations in batches
        2. Fetch complete details for each citation
        3. Apply screening criteria and extract PICOTT elements
        4. Document your decisions with exact quotes
        
        IMPORTANT: For each citation, you MUST extract exact quotes for PICOTT elements.
        Return results as a JSON array with the structure shown in the prompt.
        """
        response = client.responses.create(
            model=DEEP_RESEARCH_MODEL,
            input=screening_prompt,
            tools=[
                {"type": "web_search_preview"},
                {
                    "type": "mcp",
                    "server_label": "DeepResearchServer",
                    "server_url": self.mcp_url,
                    "require_approval": "never",
                },
            ],
        )
        logger.info(f"Screening job completed: {getattr(response, 'id', 'unknown')}")
        content: Optional[str] = None
        if hasattr(response, 'output') and response.output:
            final_output = response.output[-1]
            if hasattr(final_output, 'content') and final_output.content:
                content = final_output.content[0].text
        elif hasattr(response, 'message') and hasattr(response.message, 'content'):
            if isinstance(response.message.content, list) and response.message.content:
                content = response.message.content[0].text
            else:
                content = response.message.content  # type: ignore
        elif hasattr(response, 'output_text') and response.output_text:
            content = response.output_text  # type: ignore
        if content:
            try:
                import re
                json_match = re.search(r'\[[\s\S]*\]', content)
                if json_match:
                    return json.loads(json_match.group())
                logger.error("No JSON array found in response")
                return []
            except Exception as e:
                logger.error(f"Error parsing screening results: {e}")
                return []
        logger.error("No content in response")
        return []

    def run_screening_pipeline(
        self,
        criteria: Dict[str, Any],
        interactive: bool = False,
        callback: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Run the complete multi‑agent screening pipeline."""
        if callback:
            callback("Starting multi‑agent screening pipeline...")
        if callback:
            callback("Triaging screening criteria...")
        triage_result = self.triage_request(criteria)
        self.screening_log.append({"agent": "triage", "result": triage_result})
        clarifications: Dict[str, str] = {}
        if triage_result.get('needs_clarification') and interactive:
            if callback:
                callback("Generating clarification questions...")
            questions = self.clarify_criteria(criteria, triage_result.get('missing_elements', []))
            self.screening_log.append({"agent": "clarifier", "questions": questions})
            # In a real UI, user responses would populate ``clarifications``
        if callback:
            callback("Building detailed screening instructions...")
        instructions = self.build_instructions(criteria, clarifications)
        self.screening_log.append({"agent": "instruction_builder", "instructions": instructions})
        if callback:
            callback("Performing systematic screening...")
        screening_results = self.screen_citations(instructions)
        return {
            'screening_log': self.screening_log,
            'instructions': instructions,
            'results': screening_results,
            'timestamp': datetime.now().isoformat(),
        }


# Convenience function for integration
def run_multi_agent_screening(
    pico_criteria: Dict[str, str],
    inclusion_criteria: List[str],
    exclusion_criteria: List[str],
    corpus_size: int,
    mcp_url: str = 'http://localhost:8001/sse/',
    callback: Optional[Any] = None,
    search_mode: str = 'fulltext',
) -> Dict[str, Any]:
    """Run multi‑agent screening with the provided criteria."""
    screener = MultiAgentScreener(mcp_url)
    criteria = {
        'pico_criteria': pico_criteria,
        'inclusion_criteria': inclusion_criteria,
        'exclusion_criteria': exclusion_criteria,
        'corpus_size': corpus_size,
        'search_mode': search_mode,
    }
    return screener.run_screening_pipeline(criteria, interactive=False, callback=callback)
