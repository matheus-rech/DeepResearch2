"""
OpenAI Deep Research integration for systematic review screening.

This module defines helper functions for launching and polling Deep
Research screening jobs using OpenAI's ``o3-deep-research`` model.  It
mirrors the functionality of the upstream implementation but adds
robust environment validation.  The original code silently created
an ``OpenAI`` client even when no API key was configured, which led
to confusing runtime exceptions.  This version explicitly checks for
``OPENAI_API_KEY`` or ``OPENAI_API_KEYS`` in the environment and raises
a descriptive error if none are provided.  When ``OPENAI_API_KEYS`` is
present it is treated as a comma‑separated list and the first key is
used by default.

The public functions are:

* ``launch_screening_job`` – submit a new screening job to the Deep
  Research API.
* ``poll_job_status`` – extract results from a completed response.

"""

from __future__ import annotations

import os
import logging
from typing import Dict, List, Any, Optional

from openai import OpenAI  # type: ignore

logger = logging.getLogger(__name__)

# Resolve API key from environment variables
def _resolve_api_key() -> str:
    """Return a valid OpenAI API key from the environment.

    The function first checks the ``OPENAI_API_KEY`` environment
    variable.  If absent, it will look for ``OPENAI_API_KEYS`` and
    return the first key from the comma‑separated list.  If no key is
    found, an ``EnvironmentError`` is raised.
    """
    single = os.getenv('OPENAI_API_KEY')
    if single:
        return single
    multiple = os.getenv('OPENAI_API_KEYS')
    if multiple:
        # take the first non‑empty trimmed key
        for key in (k.strip() for k in multiple.split(',')):
            if key:
                return key
    raise EnvironmentError(
        'Missing OpenAI API key. Set OPENAI_API_KEY or OPENAI_API_KEYS in your environment.'
    )


# Initialise client lazily so that API key resolution happens at import
API_KEY: str = _resolve_api_key()
# Define the default model version; this should be kept in sync with
# OpenAI documentation for the Deep Research API.
MODEL: str = 'o3-deep-research-2025-06-26'
client: OpenAI = OpenAI(api_key=API_KEY, timeout=3600)


def launch_screening_job(
    pico_criteria: Dict[str, str],
    inclusion_criteria: List[str],
    exclusion_criteria: List[str],
    corpus_size: int,
    mcp_url: str = 'http://localhost:8001/sse/',
    search_mode: str = 'fulltext'
) -> Any:
    """Launch a deep research screening job for systematic review.

    Given a set of PICOTT criteria and inclusion/exclusion filters,
    construct the prompt expected by the Deep Research API and submit
    it via the OpenAI client.  The returned object is an OpenAI
    response which can be passed to ``poll_job_status`` to extract
    results.
    """
    # Build the screening task prompt
    task = f"""You are conducting a systematic review screening of {corpus_size} research citations.
The citations are available through the MCP internal_file_lookup tool.

IMPORTANT: Use search mode="{search_mode}" for all search operations.

Your task is to screen each citation based on the following criteria:

## PICOTT Criteria (ALL must match for inclusion):
- Population: {pico_criteria.get('population', 'Not specified')}
- Intervention: {pico_criteria.get('intervention', 'Not specified')}
- Comparator: {pico_criteria.get('comparator', 'Not specified')}
- Outcome: {pico_criteria.get('outcome', 'Not specified')}
- Timeframe: {pico_criteria.get('timeframe', 'Not specified')}
- Study Type: {pico_criteria.get('study_type', 'Not specified')}

## Additional Inclusion Criteria:
{chr(10).join(f'- {criterion}' for criterion in inclusion_criteria)}

## Exclusion Criteria:
{chr(10).join(f'- {criterion}' for criterion in exclusion_criteria)}

## Instructions:
1. Search the corpus systematically to identify all potentially relevant citations
2. Extract PICOTT elements with EXACT QUOTES from the title/abstract
3. A citation must meet ALL PICOTT criteria AND inclusion criteria to be included
4. If ANY exclusion criterion is met, the citation should be excluded
5. When uncertain, err on the side of inclusion for full‑text review

Return your results as a JSON array where each citation has this structure:
[
  {{
    "id": "citation_id",
    "title": "citation title",
    "picott": {{
      "population": "exact quote from abstract identifying population or 'Not found'",
      "intervention": "exact quote from abstract identifying intervention or 'Not found'",
      "comparison": "exact quote from abstract identifying comparison or 'Not found'",
      "outcome": "exact quote from abstract identifying outcome or 'Not found'",
      "timeframe": "exact quote from abstract identifying timeframe or 'Not found'",
      "studyType": "exact quote from abstract identifying study type or 'Not found'"
    }},
    "inclusionCriteria": ["list of matched inclusion criteria with supporting quotes"],
    "exclusionCriteria": ["list of matched exclusion criteria with supporting quotes"],
    "reasoning": "Step‑by‑step reasoning for your decision",
    "decision": "Include" or "Exclude",
    "confidence": "high/medium/low"
  }}
]

Focus on extracting EXACT quotes that support each PICOTT element and criterion match."""

    # Override MCP URL if running on hosted environments
    if os.getenv('HEROKU_APP_NAME'):
        app_name = os.getenv('HEROKU_APP_NAME')
        mcp_url = f"https://{app_name}.herokuapp.com/sse/"
    elif os.getenv('REPL_SLUG') and os.getenv('REPL_OWNER'):
        repl_slug = os.getenv('REPL_SLUG')
        repl_owner = os.getenv('REPL_OWNER')
        mcp_url = f"https://{repl_slug}-8001.{repl_owner}.repl.co/sse/"
    else:
        mcp_url = mcp_url or 'http://localhost:8001/sse/'
    try:
        response = client.responses.create(
            model=MODEL,
            input=task,
            tools=[
                {"type": "web_search_preview"},
                {
                    "type": "mcp",
                    "server_label": "DeepResearchServer",
                    "server_url": mcp_url,
                    "require_approval": "never",
                },
            ],
        )
        logger.info(f"Launched screening job: {getattr(response, 'id', 'unknown')}")
        return response
    except Exception as e:
        logger.error(f"Failed to launch screening job: {e}")
        raise


def poll_job_status(response: Any, sleep_interval: int = 5) -> Dict[str, Any]:
    """Extract results from a Deep Research API response.

    The Deep Research API does not support long‑running background
    operations with MCP tools.  Instead, the full answer is returned in
    the initial response.  This helper pulls the final output from the
    response object and normalises it into a dictionary with keys
    ``status``, ``content`` and optionally ``reasoning`` and
    ``full_output``.
    """
    try:
        # Newer API versions return responses in ``output``
        if hasattr(response, 'output') and response.output:
            final_output = response.output[-1]
            if hasattr(final_output, 'content') and final_output.content:
                content = final_output.content[0].text
                return {
                    'status': 'completed',
                    'content': content,
                    'reasoning': getattr(response, 'reasoning', {}),
                    'full_output': response.output,
                }
            raise ValueError('Completed job has no content in final output')
        # Fallback for message based responses
        if hasattr(response, 'message') and response.message and hasattr(response.message, 'content'):
            if isinstance(response.message.content, list) and response.message.content:
                content = response.message.content[0].text
            else:
                content = response.message.content
            return {
                'status': 'completed',
                'content': content,
                'reasoning': getattr(response, 'reasoning', {}),
            }
        raise ValueError('Unrecognised response format; cannot extract results')
    except Exception as e:
        logger.error(f"Failed to extract job results: {e}")
        raise
