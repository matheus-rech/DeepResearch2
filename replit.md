# Replit.md

## Overview

This is a dual-mode MCP server designed to integrate with ChatGPT's Deep Research feature:

1. **Vector Store Mode**: Uses OpenAI Vector Store for document search and retrieval
2. **Systematic Review Mode**: A comprehensive citation screening tool for academic research with Streamlit UI

The application provides search and document retrieval capabilities through FastMCP server implementation. It serves as a reference implementation for building custom MCP servers that can extend ChatGPT with specialized research tools.

## System Architecture

The application supports two distinct modes:

### Vector Store Mode (Original)
- **Backend Framework**: FastMCP (Model Context Protocol implementation)
- **Runtime**: Python 3.11 with uvicorn ASGI server
- **Transport**: Server-Sent Events (SSE) for real-time communication
- **Data Storage**: OpenAI Vector Store integration
- **Port**: 8000 (MCP server)

### Systematic Review Mode (New)
- **Backend Framework**: FastMCP for MCP server + Streamlit for UI
- **Database**: PostgreSQL with full-text search (FTS) capabilities
- **File Parsing**: Supports PubMed XML, RIS, CSV, EndNote XML formats
- **Deep Research Integration**: Uses OpenAI o3-deep-research model
- **ICE System**: Internal Consistency Evaluation for quality control
- **Ports**: 8001 (MCP server) + 8000 (Streamlit UI)

## Key Components

### Common Components

#### 1. Main Entry Point (`main.py`)
- **Purpose**: Unified entry point supporting both modes
- **Modes**: 
  - `python main.py vector` - Vector store mode
  - `python main.py sr` - Systematic review MCP server only
  - `python main.py sr-ui` - Systematic review with Streamlit UI
- **Architecture Decision**: Single entry point for flexibility
- **Rationale**: Allows easy switching between modes

### Vector Store Mode Components

#### 1. Vector Store Server (`main.py` - vector mode)
- **Purpose**: MCP server using OpenAI Vector Store
- **Key Functions**:
  - `search()`: Semantic search in vector store
  - `fetch()`: Retrieve complete documents by ID
- **Integration**: Direct OpenAI Vector Store API

### Systematic Review Mode Components

#### 1. SR MCP Server (`sr_screener/mcp_server.py`)
- **Purpose**: MCP server for citation corpus search/fetch
- **Tools**:
  - `search()`: Full-text search in citation database (limit: 10,000 citations)
  - `fetch()`: Retrieve complete citation with metadata
  - `corpus_info()`: Get corpus statistics
- **Database**: PostgreSQL with full-text search
- **Search Strategy**: 
  - Uses PostgreSQL full-text search (NOT vector embeddings)
  - Empty query or "*" returns ALL citations for comprehensive screening
  - No artificial limits on screening - processes entire corpus

#### 2. Citation Parsers (`sr_screener/parsers.py`)
- **Purpose**: Parse various citation formats
- **Supported Formats**:
  - PubMed XML (.xml)
  - RIS format (.ris) - EndNote, Mendeley exports
  - CSV format (.csv)
  - EndNote XML (.xml)
- **Auto-detection**: Automatically detects format

#### 3. Database Layer (`sr_screener/database.py`)
- **Purpose**: PostgreSQL database operations
- **Features**:
  - Full-text search with relevance ranking
  - Bulk citation insertion
  - Search result highlighting
  - Corpus statistics

#### 4. Deep Research Integration (`sr_screener/deep_research.py`)
- **Purpose**: Integration with OpenAI o3-deep-research
- **Functions**:
  - Launch screening jobs with PICO criteria
  - Poll job status
  - Parse screening results
- **Model**: o3-deep-research-2025-06-26

#### 5. Streamlit UI (`sr_screener/app.py`)
- **Purpose**: Web interface for systematic review workflow
- **Features**:
  - Citation file upload
  - PICO criteria configuration
  - Inclusion/exclusion criteria setup
  - Real-time screening progress
  - Results review and export
  - Advanced options for multi-agent mode selection
- **Steps**: Upload → Criteria → Screen → Results

#### 6. Multi-Agent Research (`sr_screener/multi_agent_research.py`)
- **Purpose**: Orchestrates multi-agent pipeline for enhanced screening
- **Agents**:
  - **Triage Agent**: Evaluates criteria completeness and routes requests
  - **Clarifier Agent**: Generates targeted questions for missing elements
  - **Instruction Builder**: Creates detailed screening protocols
  - **Screening Agent**: Performs systematic screening with Deep Research
- **Benefits**:
  - Maximizes context window usage per agent
  - Optimizes each step of the screening process
  - Improves screening quality through specialized agents
- **Integration**: Called when user selects multi-agent mode in UI

#### 7. ICE Critic (`sr_screener/ice_critic.py`)
- **Purpose**: Internal Consistency Evaluation
- **Analyses**:
  - PICO match validation
  - Confidence vs decision consistency
  - Duplicate detection
  - Exclusion reason standardization
  - Sequence pattern detection
- **Output**: Severity-ranked issues with suggestions

### Configuration Files
- **`.replit`**: Python 3.11 environment
- **`pyproject.toml`**: Core dependencies
- **`sr_screener/requirements.txt`**: SR-specific dependencies
- **`sr_screener/.env.example`**: Environment variables template

## Data Flow

### Vector Store Mode
1. **Server Startup**: 
   - Connect to OpenAI Vector Store using API key
   - Initialize FastMCP server with search and fetch tools

2. **Search Operations**:
   - Accept natural language queries
   - Perform semantic search in vector store
   - Return matching documents with snippets

3. **Fetch Operations**:
   - Retrieve complete documents by file ID
   - Return full content with metadata

### Systematic Review Mode
1. **Citation Upload (UI)**:
   - User uploads citation file (PubMed, RIS, CSV, etc.)
   - Parser auto-detects format and extracts citations
   - Bulk insert into PostgreSQL database

2. **Criteria Configuration (UI)**:
   - User defines PICO criteria
   - Sets inclusion/exclusion criteria
   - Saves configuration for screening

3. **Screening Process**:
   - Deep Research agent queries MCP server for citations
   - Evaluates each citation against criteria
   - Returns screening decisions with confidence levels

4. **MCP Communication**:
   - Search tool: Full-text search in citation corpus
   - Fetch tool: Retrieve complete citation details
   - Corpus info: Get statistics about loaded citations
   - MCP server runs on port 8001 (separate from UI)

5. **Results Review (UI)**:
   - Display included/excluded citations
   - Run ICE analysis for quality control
   - Export results in multiple formats

## External Dependencies

### Core Dependencies
- **fastmcp (>=2.9.0)**: MCP protocol implementation
- **uvicorn (>=0.34.3)**: ASGI server for hosting
- **pydantic**: Data validation (indirect dependency)

### Development Environment
- **Python 3.11**: Runtime environment
- **Nix**: Package management and environment reproducibility

## Deployment Strategy

### Development Deployment
- **Platform**: Replit environment with Nix package management
- **Process**: Single uvicorn server process
- **Port**: 8000 (configured in workflow)
- **Auto-restart**: Enabled through Replit workflow configuration

### Production Considerations
- **Scaling**: Currently single-process, would need load balancing for production
- **Data Persistence**: JSON file storage suitable for read-only scenarios
- **Security**: No authentication implemented (would need to add for production)

### Architecture Decision: In-Memory Storage
- **Problem**: Need fast document retrieval for MCP operations
- **Solution**: Load all documents into memory at startup
- **Pros**: Fast lookup times, simple implementation
- **Cons**: Limited by available memory, data lost on restart
- **Alternative Considered**: Database storage (would add complexity for sample)

## Usage Instructions

### Running Vector Store Mode
```bash
# Default mode - runs MCP server with OpenAI Vector Store
python main.py vector

# Or simply:
python main.py
```

### Running Systematic Review Mode

#### Option 1: MCP Server Only
```bash
# Run just the MCP server for systematic review (port 8000)
python main.py sr
```

#### Option 2: Full UI Experience (Recommended)
```bash
# Run both MCP server and Streamlit UI
python main.py sr-ui

# Access the UI at: http://localhost:8501
```

### Systematic Review Workflow

1. **Upload Citations**: 
   - Access Streamlit UI at http://localhost:8501
   - Upload your citation export (PubMed XML, RIS, CSV, EndNote XML)
   - System auto-detects format and loads citations

2. **Configure Criteria**:
   - Define PICO criteria (Population, Intervention, Comparator, Outcome)
   - Set inclusion criteria (e.g., RCTs, English language, year range)
   - Set exclusion criteria (e.g., case reports, animal studies)

3. **Run Screening**:
   - Click "Start Screening" to launch Deep Research agent
   - Agent systematically evaluates each citation against criteria
   - Progress updates shown in real-time

4. **Review Results**:
   - View included/excluded citations with reasons
   - Run ICE analysis to check consistency
   - Export results as JSON, CSV, or PRISMA flow data

## Recent Changes

- **July 13, 2025**: Removed Citation Limits for Comprehensive Screening
  - **Issue Fixed**: Previous implementation had hard limits on citation retrieval that could prevent comprehensive screening
  - **Changes Made**:
    - MCP Server `search()` tool: Changed default limit from 10,000 to None (unlimited)
    - Database `get_all_citations()`: Changed default limit from 10,000 to None
    - Database `search_citations()`: Changed default limit from 10,000 to None  
    - Database `semantic_search_citations()`: Changed default limit from 100 to None (was particularly restrictive)
    - UI citation browser: Now shows up to 1,000 citations for browsing but clarifies all will be screened
  - **Impact**: Systematic reviews can now process unlimited citations without artificial constraints
  - **Note**: For UI performance, browsing is limited to 1,000 citations, but screening always processes the full corpus

- **July 13, 2025**: Added Vector Embeddings for Semantic Search
  - **Database Enhancement**: Integrated PostgreSQL pgvector extension for semantic search
    - Added embedding column to citations table for storing OpenAI embeddings
    - Automatic migration adds column to existing databases
    - Uses text-embedding-3-small model for efficient embedding generation
  - **Dual Search Modes**: Users can now choose between:
    - **Full-text Search**: Traditional keyword-based PostgreSQL search (default)
    - **Semantic Search**: AI-powered conceptual similarity using vector embeddings
  - **UI Integration**: 
    - Added search mode selector in Advanced Options during screening
    - Shows embedding generation progress and status
    - One-click embedding generation for existing citations
  - **Clean Integration**: 
    - Preserves all existing functionality - full-text search remains default
    - Embeddings generated automatically on citation upload (if API key present)
    - Graceful fallback to full-text search if embeddings unavailable
  - **MCP Server Updates**:
    - Search tool now accepts `mode` parameter ("fulltext" or "semantic")
    - Deep Research prompts updated to specify search mode
    - Multi-agent pipeline passes search mode through all agents

- **July 13, 2025**: Enhanced Deep Research Integration Following OpenAI Documentation
  - **MCP Server Compliance**: Updated to match exact Deep Research specification
    - Search tool now returns only: id, title, text, url (removed extra fields)
    - Fetch tool returns "text" field instead of "abstract" for full content
    - Added proper URL generation for citations (PubMed, DOI, or internal)
  - **Deep Research API Updates**:
    - Switched to Responses API with background mode (as strongly recommended)
    - Proper tool configuration: `{"type": "mcp", "server": {"url": mcp_url}}`
    - Added max_tool_calls parameter (200) for cost control
    - Implemented proper polling mechanism for background jobs
  - **Multi-Agent Optimization**:
    - Uses gpt-4.1 for triage/clarification/instruction building (faster, cheaper)
    - Only uses o3-deep-research for actual screening (expensive operations)
    - All agents now use appropriate models per documentation best practices
  - **Methodological Improvements**:
    - Background mode prevents timeouts for long screening tasks
    - Proper error handling for API failures
    - Follows OpenAI's 3-step pattern: Clarification → Prompt enrichment → Deep research

- **July 13, 2025**: Implemented Multi-Agent Architecture for Systematic Review
  - Added multi-agent pipeline inspired by OpenAI cookbook with specialized agents:
    - **Triage Agent**: Evaluates criteria completeness and routes requests
    - **Clarifier Agent**: Generates targeted questions for missing PICOTT elements
    - **Instruction Builder**: Creates detailed screening protocols
    - **Screening Agent**: Performs systematic screening with Deep Research
  - Benefits: Maximizes context window usage, optimizes each step, improves screening quality
  - User can now choose between single-agent (faster) or multi-agent (more thorough) modes
  - Updated UI with Advanced Options toggle for screening mode selection
  - Architecture designed to match OpenAI's Deep Research multi-agent pattern

- **July 13, 2025**: Added Systematic Review Screener and Fixed WebSocket Issues
  - Created comprehensive citation screening tool with Streamlit UI
  - Integrated PostgreSQL database with full-text search
  - Added support for multiple citation formats (PubMed, RIS, CSV, EndNote)
  - Implemented Deep Research integration for automated screening
  - Added ICE (Internal Consistency Evaluation) system
  - Created dual-mode main.py supporting both vector store and SR modes
  - Added comprehensive documentation and workflow configurations
  - **Fixed WebSocket errors**: Swapped port configuration - Streamlit UI now on port 8000 (main web port), MCP server on port 8001
  - Resolved browser connectivity issues by proper port assignment

- **July 1, 2025**: Fixed vector store ID configuration issue
  - Resolved empty VECTOR_STORE_ID causing server initialization problems
  - Added fallback logic to use default vector store when environment variable is empty
  - Server now properly initializes with vs_682552f3ab90819185d4b99adcae7a07
  - MCP server running successfully on port 8000 with proper vector store connection

- **June 24, 2025**: Fixed deployment port configuration and URL formatting
  - Updated server port from 5000 back to 8000 to match deployment requirements
  - Reconfigured workflow to expect port 8000 instead of 5000
  - Resolved deployment failure caused by port forwarding mismatch
  - Fixed search function URL formatting to match fetch function format
  - Both search and fetch now return proper OpenAI platform URLs for citations
  - Server now properly configured for Autoscale deployments on port 8000

## Changelog

```
Changelog:
- June 24, 2025: Complete MCP server with vector store integration
  - FastMCP server with search/fetch tools
  - OpenAI Vector Store semantic search integration
  - OpenAI Vector Store file content retrieval
  - Pure OpenAI API implementation (no fallbacks)
  - SSE transport enabled for ChatGPT integration
  - Comprehensive documentation and setup guide
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```