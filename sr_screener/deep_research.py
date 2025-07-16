"""
Deep Research integration for systematic review screening
Uses OpenAI's o3-deep-research model for automated screening
"""
import os
import json
import logging
import urllib.parse
from typing import Dict, List, Any, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


def get_mcp_url() -> str:
    """
    Get the appropriate MCP server URL based on environment.
    
    Returns:
        str: The MCP server URL with /sse/ endpoint
    """
    # Priority order: explicit env var, platform-specific logic, localhost fallback
    if os.getenv("MCP_SERVER_URL"):
        url = os.getenv("MCP_SERVER_URL")
        if not url.endswith("/sse/"):
            url = url.rstrip("/") + "/sse/"
        return url
        
    if os.getenv("EXTERNAL_HOST"):
        host = os.getenv("EXTERNAL_HOST")
        port = os.getenv("EXTERNAL_PORT", "443")
        protocol = os.getenv("EXTERNAL_PROTOCOL", "https")
        
        if (protocol == "https" and port == "443") or (protocol == "http" and port == "80"):
            url = f"{protocol}://{host}/sse/"
        else:
            url = f"{protocol}://{host}:{port}/sse/"
        
        return url
    
    if os.getenv("HEROKU_APP_NAME"):
        # Running on Heroku
        app_name = os.getenv("HEROKU_APP_NAME")
        return f"https://{app_name}.herokuapp.com/sse/"
    
    if os.getenv("FLY_APP_NAME"):
        # Running on Fly.io
        app_name = os.getenv("FLY_APP_NAME")
        return f"https://{app_name}.fly.dev/sse/"
        
    if os.getenv("REPL_SLUG") and os.getenv("REPL_OWNER"):
        # Running on Replit
        repl_slug = os.getenv("REPL_SLUG")
        repl_owner = os.getenv("REPL_OWNER")
        return f"https://{repl_slug}-8001.{repl_owner}.repl.co/sse/"
    
    # Docker container configuration
    if os.getenv("DOCKER_CONTAINER"):
        # Running in Docker with external access
        if os.getenv("EXTERNAL_HOST"):
            host = os.getenv("EXTERNAL_HOST")
            port = os.getenv("EXTERNAL_PORT", "8001")
            protocol = os.getenv("EXTERNAL_PROTOCOL", "http")
            return f"{protocol}://{host}:{port}/sse/"
        return "http://localhost:8001/sse/"
    
    # Local development fallback
    mcp_host = os.getenv("MCP_HOST", "localhost")
    mcp_port = os.getenv("MCP_PORT", "8001")
    return f"http://{mcp_host}:{mcp_port}/sse/"

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
    mcp_url: Optional[str] = None,
    search_mode: str = "fulltext"
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

    # Get the appropriate MCP server URL based on environment
    mcp_url = get_mcp_url()

    try:
        # Launch the deep research job with proper configuration per docs
        response = client.responses.create(
            model=MODEL,
            input=task,  # Deep Research expects a simple string input
            tools=[
                {
                    "type": "web_search_preview"  # Required for Deep Research
                },
                {
                    "type": "mcp",
                    "server_label": "DeepResearchServer",
                    "server_url": mcp_url,
                    "require_approval": "never"
                }
            ],
            # Note: background mode not supported with MCP tools
        )

        logger.info(f"Launched screening job: {response.id}")
        return response

    except Exception as e:
        logger.error(f"Failed to launch screening job: {e}")
        raise


def poll_job_status(response: Any, sleep_interval: int = 5) -> Dict[str, Any]:
    """
    Extract results from a deep research response (no polling needed without background mode).

    Args:
        response: The response object from create call
        sleep_interval: Not used (kept for compatibility)

    Returns:
        Final response with results
    """
    try:
        # Extract the content according to documentation
        # The final answer is in response.output[-1].content[0].text
        if hasattr(response, 'output') and response.output:
            # Get the last output item (the final answer)
            final_output = response.output[-1]
            if hasattr(final_output, 'content') and final_output.content:
                content = final_output.content[0].text
                return {
                    "status": "completed",
                    "content": content,
                    "reasoning": getattr(response, "reasoning", {}),
                    "full_output": response.output  # Keep full output for debugging
                }
            else:
                raise ValueError("Completed job has no content in final output")
        # Fallback to message format if available
        elif hasattr(response, 'message') and response.message and hasattr(response.message, 'content'):
            if isinstance(response.message.content, list) and response.message.content:
                content = response.message.content[0].text
            else:
                content = response.message.content
            return {
                "status": "completed",
                "content": content,
                "reasoning": getattr(response, "reasoning", {})
            }
        else:
            # Try output_text as shown in platform docs
            if hasattr(response, 'output_text') and response.output_text:
                return {
                    "status": "completed",
                    "content": response.output_text,
                    "reasoning": getattr(response, "reasoning", {})
                }
            raise ValueError("Response has no content")

    except Exception as e:
        logger.error(f"Error extracting results: {e}")
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
    mcp_url: Optional[str] = None,
    callback=None,
    use_multi_agent: bool = False,
    search_mode: str = "fulltext"
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
        from multi_agent_research import run_multi_agent_screening

        # Run sync function directly
        result = run_multi_agent_screening(
            pico_criteria,
            inclusion_criteria,
            exclusion_criteria,
            corpus_size,
            mcp_url,
            callback,
            search_mode
        )
        return result
    try:
        # Launch the job
        if callback:
            callback("Launching deep research screening job...")
        response = launch_screening_job(
            pico_criteria,
            inclusion_criteria,
            exclusion_criteria,
            corpus_size,
            mcp_url,
            search_mode
        )

        # Extract results
        if callback:
            callback("Processing screening results...")
        results_data = poll_job_status(response)

        # Parse results
        if callback:
            callback("Parsing screening results...")
        results = parse_screening_results(results_data["content"])

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
            "job_id": response.id,
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
            "reasoning": results_data.get("reasoning", {})
        }

    except Exception as e:
        logger.error(f"Screening failed: {e}")
        raise
