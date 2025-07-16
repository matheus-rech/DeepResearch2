#!/bin/bash
# Deep Research Screening with Claude Unix Integration

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

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
cat "$CITATIONS_FILE" | claude-code -p 'Check for citation format issues. Report line:issue only.' \
    --output-format text > "$OUTPUT_DIR/lint_report.txt"

echo -e "${BLUE}📝 Step 2: Parsing citations...${NC}"
cat "$CITATIONS_FILE" | claude-code -p 'Parse citations to JSON array with title,authors,year,journal,doi,abstract' \
    --output-format json > "$OUTPUT_DIR/parsed_citations.json"

echo -e "${BLUE}✅ Step 3: Validating criteria...${NC}"
cat "$CRITERIA_FILE" | claude-code -p 'Validate PICOTT criteria. Return JSON: {valid:bool,issues:[],suggestions:[]}' \
    --output-format json > "$OUTPUT_DIR/criteria_validation.json"

echo -e "${BLUE}🤖 Step 4: Running screening...${NC}"
# Combine citations and criteria for screening
jq -s '.[0] as $criteria | .[1] as $citations | {criteria: $criteria, citations: $citations}' \
    "$CRITERIA_FILE" "$OUTPUT_DIR/parsed_citations.json" | \
    claude-code -p 'Screen each citation against criteria. Return array of {title,decision,score,reasoning}' \
    --output-format stream-json > "$OUTPUT_DIR/screening_results.jsonl"

echo -e "${BLUE}📊 Step 5: Generating report...${NC}"
cat "$OUTPUT_DIR/screening_results.jsonl" | \
    jq -s '.' | \
    claude-code -p 'Generate comprehensive systematic review report with statistics, included/excluded lists, and recommendations' \
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
