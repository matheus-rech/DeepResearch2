# DeepResearch2 Agent Architecture

## Overview

DeepResearch2 implements a sophisticated multi-agent architecture designed for systematic literature review and research screening. The system leverages specialized AI agents to handle different aspects of the research workflow, from initial triage to final screening decisions.

## Current Agent Implementation

### 1. Triage Agent
**Model**: `gpt-4.1`  
**Purpose**: Initial assessment and routing of research requests  
**Responsibilities**:
- Evaluates completeness of PICOTT criteria (Population, Intervention, Comparison, Outcomes, Time frame, Study Types)
- Determines if sufficient information is available to proceed with screening
- Routes requests to appropriate downstream agents
- Provides initial quality assessment of research queries

**Current Tools**:
- Text analysis and criteria evaluation
- Decision routing logic
- Quality assessment scoring

### 2. Clarifier Agent  
**Model**: `gpt-4.1`  
**Purpose**: Generates targeted questions for incomplete research criteria  
**Responsibilities**:
- Identifies missing or unclear PICOTT elements
- Formulates specific, actionable questions for researchers
- Provides guidance on improving research criteria definition
- Ensures comprehensive coverage of systematic review requirements

**Current Tools**:
- PICOTT gap analysis
- Question generation templates
- Research methodology guidance

### 3. Instruction Builder Agent
**Model**: `gpt-4.1`  
**Purpose**: Creates detailed screening protocols and instructions  
**Responsibilities**:
- Translates PICOTT criteria into actionable screening instructions
- Develops inclusion/exclusion decision trees
- Creates standardized evaluation frameworks
- Ensures consistency across screening decisions

**Current Tools**:
- Protocol generation templates
- Decision tree construction
- Instruction standardization frameworks

### 4. Screening Agent
**Model**: `o3-deep-research-2025-06-26`  
**Purpose**: Performs systematic citation screening and evaluation  
**Responsibilities**:
- Applies screening criteria to individual citations
- Provides detailed inclusion/exclusion decisions with reasoning
- Generates confidence scores for screening decisions
- Maintains consistency with established protocols

**Current Tools**:
- MCP search tool for citation corpus access
- MCP fetch tool for detailed citation retrieval
- Web search preview tool (required for Deep Research integration)
- Citation analysis and evaluation frameworks

## MCP Integration

### Available MCP Tools

1. **search(query, limit, mode)**
   - Searches citation corpus using full-text or semantic search
   - Returns formatted results compatible with Deep Research specification
   - Supports both keyword and embedding-based retrieval

2. **fetch(id)**
   - Retrieves complete citation details by ID
   - Returns full metadata including abstracts, authors, and bibliographic information
   - Provides structured data for agent analysis

3. **health_check()**
   - Verifies server status and connectivity
   - Ensures system reliability for agent operations

4. **corpus_info()**
   - Provides statistics about the citation database
   - Enables agents to understand corpus scope and coverage

## Recommended Tool Enhancements

Based on the [OpenAI Agents Python SDK](https://openai.github.io/openai-agents-python/ref/tool/), the following tools could significantly enhance agent performance:

### High Priority Recommendations

#### 1. File Management Tools
```python
from openai.agents.tools import FileSearchTool, FileUploadTool
```
**Benefits**:
- Enable agents to process uploaded RIS files, CSV exports, and EndNote libraries
- Allow direct file analysis without manual parsing
- Support batch processing of citation imports

**Implementation Priority**: High - Essential for streamlined citation upload workflow

#### 2. Code Interpreter Tool
```python
from openai.agents.tools import CodeInterpreterTool
```
**Benefits**:
- Enable statistical analysis of screening results
- Generate PRISMA flowcharts and screening statistics
- Perform data validation and quality checks
- Create custom visualizations for research outcomes

**Implementation Priority**: High - Critical for research analytics and reporting

#### 3. Vector Store Tools
```python
from openai.agents.tools import VectorStoreTool
```
**Benefits**:
- Enhanced semantic search capabilities
- Improved citation similarity detection
- Better duplicate identification across databases
- More sophisticated relevance ranking

**Implementation Priority**: Medium - Would improve search quality but current implementation is functional

### Medium Priority Recommendations

#### 4. Function Calling Tools
```python
from openai.agents.tools import FunctionTool
```
**Benefits**:
- Custom database query functions
- Specialized citation parsing routines
- Integration with external research databases (PubMed, Scopus, Web of Science)
- Custom PICOTT validation functions

**Implementation Priority**: Medium - Would enable more sophisticated integrations

#### 5. Web Search Tools
```python
from openai.agents.tools import WebSearchTool
```
**Benefits**:
- Real-time access to latest research publications
- Verification of citation metadata
- Access to full-text articles when available
- Cross-referencing with multiple databases

**Implementation Priority**: Medium - Current web_search_preview tool provides basic functionality

### Low Priority Recommendations

#### 6. Image Analysis Tools
```python
from openai.agents.tools import ImageAnalysisTool
```
**Benefits**:
- Analysis of figures and charts in research papers
- Extraction of data from graphical abstracts
- Processing of scanned documents

**Implementation Priority**: Low - Not essential for text-based systematic reviews

## Agent Workflow Integration

### Current Workflow
1. **Triage Agent** → Evaluates request completeness
2. **Clarifier Agent** → Generates questions for missing criteria (if needed)
3. **Instruction Builder** → Creates screening protocol
4. **Screening Agent** → Performs systematic screening using MCP tools

### Enhanced Workflow with Recommended Tools
1. **File Upload** → Process citations using FileUploadTool
2. **Triage Agent** → Enhanced evaluation with CodeInterpreterTool for statistics
3. **Clarifier Agent** → Web search integration for context
4. **Instruction Builder** → Function tools for custom protocol generation
5. **Screening Agent** → Enhanced search with VectorStoreTool + MCP integration
6. **Analytics** → CodeInterpreterTool for PRISMA flowcharts and reporting

## Implementation Recommendations

### Phase 1: Core Enhancements (Immediate)
- Integrate FileSearchTool and FileUploadTool for citation processing
- Add CodeInterpreterTool for statistical analysis and PRISMA generation
- Enhance error handling and tool fallback mechanisms

### Phase 2: Search Improvements (Short-term)
- Implement VectorStoreTool for enhanced semantic search
- Add FunctionTool for custom database integrations
- Improve duplicate detection and citation deduplication

### Phase 3: Advanced Features (Long-term)
- WebSearchTool integration for real-time research access
- Custom tool development for specialized research databases
- Advanced analytics and machine learning integration

## Configuration Requirements

### Environment Variables
```bash
# Required for enhanced tools
OPENAI_API_KEY=your_api_key_here
VECTOR_STORE_ID=your_vector_store_id
FILE_UPLOAD_ENDPOINT=your_upload_endpoint

# Optional for advanced features
PUBMED_API_KEY=your_pubmed_key
SCOPUS_API_KEY=your_scopus_key
WOS_API_KEY=your_web_of_science_key
```

### Agent Model Recommendations
- **Triage/Clarifier/Instruction Builder**: Continue with `gpt-4.1` for consistency
- **Screening Agent**: `o3-deep-research-2025-06-26` is optimal for research tasks
- **Analytics Agent** (new): `gpt-4.1` with CodeInterpreterTool for statistical analysis

## Performance Optimization

### Current Strengths
- Specialized agents for different workflow stages
- MCP integration for efficient citation access
- Deep Research compatibility for ChatGPT integration
- Robust error handling and fallback mechanisms

### Areas for Improvement
1. **Tool Integration**: Add recommended OpenAI Agent tools for enhanced capabilities
2. **Parallel Processing**: Enable concurrent agent operations for large datasets
3. **Caching**: Implement intelligent caching for repeated searches and analyses
4. **Monitoring**: Add comprehensive logging and performance metrics

## Conclusion

The current agent architecture provides a solid foundation for systematic literature review. The recommended tool enhancements would significantly improve functionality, particularly in file processing, statistical analysis, and search capabilities. Priority should be given to FileUploadTool and CodeInterpreterTool integration, as these would provide immediate value for the research workflow.

The multi-agent approach ensures specialized handling of different review stages while maintaining consistency and quality throughout the screening process. With the recommended enhancements, DeepResearch2 would become a comprehensive platform for AI-assisted systematic reviews.
