#!/usr/bin/env python3
"""
Claude Unix-Style Utility Integration for Deep Research
Implements piping, linting, and structured output capabilities
"""
import subprocess
import json
import sys
import os
from typing import Optional, Dict, Any, List
import asyncio

class ClaudeUnixUtility:
    """Use Claude as a Unix-style utility for Deep Research"""
    
    @staticmethod
    def claude_lint_citations(file_path: str) -> str:
        """Use Claude as a citation format linter"""
        prompt = """You are a citation format linter. Check this file for:
        1. Missing required fields (title, authors, year)
        2. Formatting inconsistencies
        3. Invalid DOIs or dates
        4. Duplicate entries
        
        Report: filename:line_number - issue description
        Only report actual issues, no other text."""
        
        cmd = f"cat {file_path} | claude-code -p '{prompt}' --output-format text"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout
    
    @staticmethod
    def claude_parse_citations(input_file: str, output_file: str) -> None:
        """Parse citations through Claude with structured JSON output"""
        prompt = """Parse these citations and extract structured data.
        For each citation return: {
            "title": "",
            "authors": [],
            "year": 0,
            "journal": "",
            "doi": "",
            "abstract": ""
        }
        Return as JSON array."""
        
        cmd = f"cat {input_file} | claude-code -p '{prompt}' --output-format json > {output_file}"
        subprocess.run(cmd, shell=True, check=True)
    
    @staticmethod
    async def claude_screen_pipeline(citations_file: str, criteria_file: str) -> Dict[str, Any]:
        """Complete screening pipeline using Claude unix-style"""
        
        # Step 1: Validate criteria
        validate_cmd = f"""cat {criteria_file} | claude-code -p 'Validate these PICOTT criteria. \
Return JSON with {{"valid": bool, "issues": [], "suggestions": []}}' --output-format json"""
        
        validation = subprocess.run(validate_cmd, shell=True, capture_output=True, text=True)
        validation_result = json.loads(validation.stdout)
        
        # Step 2: Screen citations
        screen_prompt = f"""You are screening citations for systematic review.
        Criteria: $(cat {criteria_file})
        
        For each citation, return JSON:
        {{
            "title": "",
            "decision": "include|exclude",
            "score": 0.0-1.0,
            "reasoning": "",
            "matches": {{criterion: bool}}
        }}"""
        
        screen_cmd = f"cat {citations_file} | claude-code -p '{screen_prompt}' --output-format stream-json"
        
        # Process streaming results
        process = await asyncio.create_subprocess_shell(
            screen_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        results = []
        async for line in process.stdout:
            if line:
                try:
                    result = json.loads(line.decode())
                    results.append(result)
                    # Real-time progress
                    print(f"✓ Screened: {result['title'][:50]}... - {result['decision'].upper()}")
                except json.JSONDecodeError:
                    continue
        
        # Step 3: Generate report
        report_cmd = f"""echo '{json.dumps(results)}' | claude-code -p 'Generate a comprehensive \
systematic review screening report from these results. Use markdown format.' --output-format text"""
        
        report = subprocess.run(report_cmd, shell=True, capture_output=True, text=True)
        
        return {
            'validation': validation_result,
            'screening_results': results,
            'report': report.stdout
        }

class ClaudeReviewIntegration:
    """Integrate Claude as automated reviewer"""
    
    @staticmethod
    def add_to_package_json():
        """Add Claude linting scripts to package.json"""
        scripts = {
            "lint:citations": "find . -name '*.csv' -o -name '*.ris' | xargs -I {} sh -c 'echo \"Checking {}...\" && cat {} | claude-code -p \"Check citation format issues\" --output-format text'",
            
            "lint:criteria": "cat sr_screener/sample_criteria.json | claude-code -p 'Validate PICOTT criteria completeness and clarity' --output-format json",
            
            "review:screening": "git diff main | claude-code -p 'Review screening logic changes for accuracy' --output-format text",
            
            "generate:report": "cat screening_results.json | claude-code -p 'Generate executive summary of screening results' --output-format text > summary.md"
        }
        
        return {
            "scripts": scripts,
            "claude-config": {
                "output_formats": ["text", "json", "stream-json"],
                "max_tokens": 4096,
                "temperature": 0.1
            }
        }

# Bash script generator for common workflows
def generate_screening_script():
    """Generate bash script for complete screening workflow"""
    script = """#!/bin/bash
# Deep Research Screening with Claude Unix Integration

set -e

# Colors for output
GREEN='\\033[0;32m'
BLUE='\\033[0;34m'
RED='\\033[0;31m'
NC='\\033[0m'

echo -e "${BLUE}🔬 Deep Research Systematic Review Screening${NC}"
echo "================================================"

# Check if Claude is available
if ! command -v claude-code &> /dev/null; then
    echo -e "${RED}❌ Claude Code CLI not found. Please install it first.${NC}"
    exit 1
fi

# Input files
CITATIONS_FILE="${1:-sample_citations.csv}"
CRITERIA_FILE="${2:-criteria.json}"
OUTPUT_DIR="${3:-screening_results}"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}📋 Step 1: Validating citation format...${NC}"
cat "$CITATIONS_FILE" | claude-code -p 'Check for citation format issues. Report line:issue only.' \\
    --output-format text > "$OUTPUT_DIR/lint_report.txt"

echo -e "${BLUE}📝 Step 2: Parsing citations...${NC}"
cat "$CITATIONS_FILE" | claude-code -p 'Parse citations to JSON array with title,authors,year,journal,doi,abstract' \\
    --output-format json > "$OUTPUT_DIR/parsed_citations.json"

echo -e "${BLUE}✅ Step 3: Validating criteria...${NC}"
cat "$CRITERIA_FILE" | claude-code -p 'Validate PICOTT criteria. Return JSON: {valid:bool,issues:[],suggestions:[]}' \\
    --output-format json > "$OUTPUT_DIR/criteria_validation.json"

echo -e "${BLUE}🤖 Step 4: Running screening...${NC}"
# Combine citations and criteria for screening
jq -s '.[0] as $criteria | .[1] as $citations | {criteria: $criteria, citations: $citations}' \\
    "$CRITERIA_FILE" "$OUTPUT_DIR/parsed_citations.json" | \\
    claude-code -p 'Screen each citation against criteria. Return array of {title,decision,score,reasoning}' \\
    --output-format stream-json > "$OUTPUT_DIR/screening_results.jsonl"

echo -e "${BLUE}📊 Step 5: Generating report...${NC}"
cat "$OUTPUT_DIR/screening_results.jsonl" | \\
    jq -s '.' | \\
    claude-code -p 'Generate comprehensive systematic review report with statistics, included/excluded lists, and recommendations' \\
    --output-format text > "$OUTPUT_DIR/screening_report.md"

# Summary statistics
TOTAL=$(jq -s 'length' "$OUTPUT_DIR/screening_results.jsonl")
INCLUDED=$(jq -s 'map(select(.decision == "include")) | length' "$OUTPUT_DIR/screening_results.jsonl")
EXCLUDED=$(jq -s 'map(select(.decision == "exclude")) | length' "$OUTPUT_DIR/screening_results.jsonl")

echo
echo -e "${GREEN}✅ Screening Complete!${NC}"
echo "===================="
echo "Total citations: $TOTAL"
echo "Included: $INCLUDED"
echo "Excluded: $EXCLUDED"
echo
echo "Results saved to: $OUTPUT_DIR/"
echo "  - Lint report: lint_report.txt"
echo "  - Parsed citations: parsed_citations.json"
echo "  - Screening results: screening_results.jsonl"
echo "  - Final report: screening_report.md"
"""
    
    with open('claude_screening.sh', 'w') as f:
        f.write(script)
    os.chmod('claude_screening.sh', 0o755)
    
    return script

# Python wrapper for easy integration
class ClaudeScreeningPipeline:
    """Python wrapper for Claude unix-style screening"""
    
    def __init__(self):
        self.check_claude_available()
    
    def check_claude_available(self):
        """Check if Claude CLI is available"""
        try:
            subprocess.run(['claude-code', '--version'], 
                         capture_output=True, check=True)
            self.claude_available = True
        except:
            self.claude_available = False
            print("⚠️  Claude Code CLI not available. Install with: npm install -g @claude-code/cli")
    
    def screen_citations(self, citations_file: str, criteria: Dict[str, str], 
                        output_format: str = 'json') -> Dict[str, Any]:
        """Screen citations using Claude unix-style"""
        
        if not self.claude_available:
            raise Exception("Claude Code CLI not available")
        
        # Create criteria prompt
        criteria_text = "\n".join([f"{k}: {v}" for k, v in criteria.items()])
        
        prompt = f"""Screen these citations against the following criteria:
{criteria_text}

For each citation, decide include/exclude with reasoning.
Return structured JSON array."""
        
        # Run screening
        cmd = [
            'cat', citations_file, '|',
            'claude-code', '-p', f'"{prompt}"',
            '--output-format', output_format
        ]
        
        result = subprocess.run(' '.join(cmd), shell=True, 
                              capture_output=True, text=True)
        
        if output_format == 'json':
            return json.loads(result.stdout)
        else:
            return {'raw_output': result.stdout}
    
    def generate_report(self, results_file: str) -> str:
        """Generate report using Claude"""
        
        cmd = f"""cat {results_file} | claude-code -p 'Generate a publication-ready \
systematic review screening report with PRISMA flow diagram description' --output-format text"""
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout

# Example usage
if __name__ == "__main__":
    # Generate the screening script
    generate_screening_script()
    print("✅ Generated claude_screening.sh")
    
    # Example of using the pipeline
    pipeline = ClaudeScreeningPipeline()
    
    if pipeline.claude_available:
        print("🚀 Claude Code CLI is available!")
        print("\nRun screening with:")
        print("  ./claude_screening.sh sample_citations.csv criteria.json")
        print("\nOr use Python:")
        print("  results = pipeline.screen_citations('citations.csv', criteria)")
    else:
        print("❌ Please install Claude Code CLI first")