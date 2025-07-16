"""
Test script for multi-agent systematic review screening
Demonstrates the multi-agent pipeline without requiring full UI
"""
import asyncio
import pytest
from sr_screener.multi_agent_research import MultiAgentScreener

@pytest.mark.asyncio
async def test_multi_agent():
    """Test the multi-agent screening pipeline"""
    
    # Create test criteria
    criteria = {
        "pico_criteria": {
            "population": "Adults with type 2 diabetes",
            "intervention": "Continuous glucose monitoring",
            "comparator": "Standard blood glucose monitoring",
            "outcome": "Glycemic control (HbA1c)",
            "timeframe": "6 months",
            "studyType": "Randomized controlled trials"
        },
        "inclusion_criteria": [
            "Adults (18+ years)",
            "Type 2 diabetes diagnosis",
            "RCT study design",
            "Published in English",
            "Full text available"
        ],
        "exclusion_criteria": [
            "Type 1 diabetes",
            "Gestational diabetes",
            "Case reports",
            "Animal studies",
            "Systematic reviews"
        ],
        "corpus_size": 5
    }
    
    # Initialize the multi-agent screener
    screener = MultiAgentScreener()
    
    print("🚀 Starting Multi-Agent Screening Pipeline\n")
    
    # Run the triage agent
    print("1️⃣ TRIAGE AGENT")
    print("-" * 50)
    triage_result = await screener.triage_request(criteria)
    print(f"Needs clarification: {triage_result.get('needs_clarification')}")
    print(f"Missing elements: {triage_result.get('missing_elements', [])}")
    print(f"Route to: {triage_result.get('route_to')}\n")
    
    # Run the clarifier agent (if needed)
    if triage_result.get('needs_clarification'):
        print("2️⃣ CLARIFIER AGENT")
        print("-" * 50)
        questions = await screener.clarify_criteria(
            criteria, 
            triage_result.get('missing_elements', [])
        )
        print("Generated questions:")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q}")
        print()
    
    # Run the instruction builder
    print("3️⃣ INSTRUCTION BUILDER AGENT")
    print("-" * 50)
    instructions = await screener.build_instructions(criteria)
    print("Generated instructions (preview):")
    print(instructions[:500] + "...\n")
    
    # Show the complete pipeline log
    print("4️⃣ SCREENING AGENT")
    print("-" * 50)
    print("Would perform actual screening with Deep Research here")
    print("Using MCP server tools: search, fetch, corpus_info")
    print()
    
    print("✅ Multi-Agent Pipeline Test Complete!")
    print("\nThis demonstrates how the multi-agent architecture:")
    print("- Evaluates criteria completeness")
    print("- Generates clarification questions if needed")
    print("- Builds detailed screening instructions")
    print("- Would perform systematic screening with specialized agents")

if __name__ == "__main__":
    asyncio.run(test_multi_agent())