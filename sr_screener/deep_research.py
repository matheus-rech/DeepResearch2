"""
Deep Research integration for systematic review screening
Uses OpenAI's o3-deep-research model for automated screening
"""
import os
import json
import time
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI
import httpx

logger = logging.getLogger(__name__)

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "o3-deep-research-2025-06-26"  # Latest deep research model

# Initialize client
client = OpenAI(api_key=OPENAI_API_KEY, timeout=3600)


def launch_screening_job(
    pico_criteria: Dict[str, str],
    inclusion_criteria: List[str],
    exclusion_criteria: List[str],
    corpus_size: int,
    mcp_url: str = "http://localhost:8001/sse/"
) -> str:
    """
    Launch a deep research screening job for systematic review.
    
    Args:
        pico_criteria: PICO criteria dict with keys: population, intervention, comparator, outcome
        inclusion_criteria: List of inclusion criteria
        exclusion_criteria: List of exclusion criteria  
        corpus_size: Total number of citations in corpus
        mcp_url: URL of the MCP server
        
    Returns:
        Job ID for polling
    """
    # Build the screening task prompt
    task = f"""You are conducting a systematic review screening of {corpus_size} research citations.
The citations are available through the MCP internal_file_lookup tool.

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
5. When uncertain, err on the side of inclusion for full-text review

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
    "reasoning": "Step-by-step reasoning for your decision",
    "decision": "Include" or "Exclude",
    "confidence": "high/medium/low"
  }}
]

Focus on extracting EXACT quotes that support each PICOTT element and criterion match."""

    # System message for research context
    system_message = """You are a professional systematic reviewer with expertise in evidence synthesis.
Your screening decisions should be based solely on the information available in titles and abstracts.
Be consistent in applying the screening criteria across all citations.
Document your reasoning clearly for transparency and potential appeals."""

    try:
        # Launch the deep research job
        response = client.responses.create(
            model=MODEL,
            input=[
                {
                    "role": "developer",
                    "content": [
                        {
                            "type": "input_text",
                            "text": system_message
                        }
                    ]
                },
                {
                    "role": "user", 
                    "content": [
                        {
                            "type": "input_text",
                            "text": task
                        }
                    ]
                }
            ],
            reasoning={
                "summary": "auto"  # Auto-generate reasoning summary
            },
            tools=[
                {
                    "type": "mcp",
                    "server_label": "internal_file_lookup",
                    "server_url": mcp_url,
                    "require_approval": "never"
                }
            ]
        )
        
        logger.info(f"Launched screening job: {response.id}")
        return response.id
        
    except Exception as e:
        logger.error(f"Failed to launch screening job: {e}")
        raise


def poll_job_status(job_id: str, sleep_interval: int = 5) -> Dict[str, Any]:
    """
    Poll the status of a deep research job until completion.
    
    Args:
        job_id: The job ID to poll
        sleep_interval: Seconds between polls
        
    Returns:
        Final response with results
    """
    while True:
        try:
            response = client.responses.retrieve(job_id)
            
            if response.status == "completed":
                # Extract the content
                if response.message and response.message.content:
                    content = response.message.content[0].text
                    return {
                        "status": "completed",
                        "content": content,
                        "reasoning": getattr(response, "reasoning", {})
                    }
                else:
                    raise ValueError("Completed job has no content")
                    
            elif response.status == "failed":
                error_msg = getattr(response, "error", "Unknown error")
                raise RuntimeError(f"Job failed: {error_msg}")
                
            else:
                # Still processing
                logger.info(f"Job {job_id} status: {response.status}")
                time.sleep(sleep_interval)
                
        except Exception as e:
            logger.error(f"Error polling job: {e}")
            raise


def parse_screening_results(results_json: str) -> List[Dict[str, Any]]:
    """
    Parse the JSON screening results from deep research.
    
    Args:
        results_json: JSON string with screening results
        
    Returns:
        List of parsed screening decisions with PICOTT elements
    """
    try:
        # Extract JSON from the response
        # Deep research might include explanation text around the JSON
        import re
        json_match = re.search(r'\[\s*\{.*\}\s*\]', results_json, re.DOTALL)
        
        if json_match:
            results = json.loads(json_match.group())
        else:
            # Try parsing the whole content
            results = json.loads(results_json)
            
        # Validate and normalize results
        normalized_results = []
        for result in results:
            # Handle both old and new format
            if "decision" in result:
                # New PICOTT format
                normalized_results.append({
                    "id": result.get("id", ""),
                    "title": result.get("title", ""),
                    "include": result.get("decision", "Exclude") == "Include",
                    "reason": result.get("reasoning", "No reason provided"),
                    "confidence": result.get("confidence", "medium"),
                    "picott": result.get("picott", {}),
                    "inclusionCriteria": result.get("inclusionCriteria", []),
                    "exclusionCriteria": result.get("exclusionCriteria", []),
                    "decision": result.get("decision", "Exclude")
                })
            else:
                # Old format compatibility
                normalized_results.append({
                    "id": result.get("id", ""),
                    "title": result.get("title", ""),
                    "include": bool(result.get("include", False)),
                    "reason": result.get("reason", "No reason provided"),
                    "confidence": result.get("confidence", "medium"),
                    "picott": {},
                    "inclusionCriteria": [],
                    "exclusionCriteria": [],
                    "decision": "Include" if result.get("include", False) else "Exclude"
                })
            
        return normalized_results
        
    except Exception as e:
        logger.error(f"Failed to parse screening results: {e}")
        # Return empty results rather than failing completely
        return []


def run_systematic_screening(
    pico_criteria: Dict[str, str],
    inclusion_criteria: List[str],
    exclusion_criteria: List[str],
    corpus_size: int,
    mcp_url: str = "http://localhost:8001/sse/",
    callback=None,
    use_multi_agent: bool = False
) -> Dict[str, Any]:
    """
    Run a complete systematic review screening process.
    
    Args:
        pico_criteria: PICO criteria
        inclusion_criteria: Inclusion criteria list
        exclusion_criteria: Exclusion criteria list
        corpus_size: Number of citations
        mcp_url: MCP server URL
        callback: Optional callback function for progress updates
        use_multi_agent: Whether to use multi-agent architecture
        
    Returns:
        Dictionary with screening results and statistics
    """
    # Use multi-agent mode if requested
    if use_multi_agent:
        import asyncio
        from .multi_agent_research import run_multi_agent_screening
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                run_multi_agent_screening(
                    pico_criteria,
                    inclusion_criteria,
                    exclusion_criteria,
                    corpus_size,
                    mcp_url,
                    callback
                )
            )
            return result
        finally:
            loop.close()
    try:
        # Launch the job
        if callback:
            callback("Launching deep research screening job...")
        job_id = launch_screening_job(
            pico_criteria,
            inclusion_criteria,
            exclusion_criteria,
            corpus_size,
            mcp_url
        )
        
        # Poll for results
        if callback:
            callback(f"Screening in progress (Job ID: {job_id})...")
        response = poll_job_status(job_id)
        
        # Parse results
        if callback:
            callback("Parsing screening results...")
        results = parse_screening_results(response["content"])
        
        # Calculate statistics
        total_screened = len(results)
        included = [r for r in results if r["include"]]
        excluded = [r for r in results if not r["include"]]
        
        # Confidence breakdown
        confidence_counts = {
            "high": len([r for r in results if r["confidence"] == "high"]),
            "medium": len([r for r in results if r["confidence"] == "medium"]),
            "low": len([r for r in results if r["confidence"] == "low"])
        }
        
        return {
            "job_id": job_id,
            "results": results,
            "statistics": {
                "total_screened": total_screened,
                "included": len(included),
                "excluded": len(excluded),
                "inclusion_rate": len(included) / total_screened if total_screened > 0 else 0,
                "confidence_breakdown": confidence_counts
            },
            "included_citations": included,
            "excluded_citations": excluded,
            "reasoning": response.get("reasoning", {})
        }
        
    except Exception as e:
        logger.error(f"Screening failed: {e}")
        raise