#!/bin/bash
# Claude-Powered Citation Processing Pipeline

set -e

INPUT_FILE="${1:-citations.csv}"
OUTPUT_DIR="${2:-processed_citations}"

echo "🔬 Claude Citation Processing Pipeline"
echo "======================================"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "📁 Processing: $INPUT_FILE"
echo "📤 Output directory: $OUTPUT_DIR"

# Step 1: Parse with Claude
echo "🤖 Step 1: Parsing citations with Claude..."
python -c "
from claude_citation_parser import ClaudeCitationParser
parser = ClaudeCitationParser()
citations = parser.parse_citations_with_claude('$INPUT_FILE')
parser.save_for_deep_research(citations, '$OUTPUT_DIR/citations_for_screening.json')
parser.save_for_ui_browser(citations, '$OUTPUT_DIR/citations_for_ui.csv')
print(f'✅ Processed {len(citations)} citations')
"

# Step 2: Validate with Claude
echo "✅ Step 2: Validating citation quality..."
cat "$OUTPUT_DIR/citations_for_screening.json" | claude-code -p 'Analyze these citations for quality issues: missing data, formatting problems, duplicates. Return JSON with validation results.' --output-format json > "$OUTPUT_DIR/validation_report.json"

# Step 3: Generate summary
echo "📊 Step 3: Generating summary..."
cat "$OUTPUT_DIR/citations_for_screening.json" | claude-code -p 'Create a summary report of these citations: total count, year distribution, journal distribution, study types, quality assessment.' --output-format text > "$OUTPUT_DIR/citation_summary.md"

echo "✅ Citation processing complete!"
echo "Files created:"
echo "  - $OUTPUT_DIR/citations_for_screening.json (for Deep Research)"
echo "  - $OUTPUT_DIR/citations_for_ui.csv (for UI browser)"
echo "  - $OUTPUT_DIR/validation_report.json (quality check)"
echo "  - $OUTPUT_DIR/citation_summary.md (summary report)"
