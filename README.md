# DeepResearch2: MCP Server for Systematic Review & Deep Research

This is a dual-mode Model Context Protocol (MCP) server designed to work with ChatGPT's Deep Research feature. It provides both vector store search capabilities and a comprehensive systematic review screening pipeline for academic research.

> **Note**: This repository has been verified for development workflow compatibility and production readiness.

## Features

### Vector Store Mode (Default)
- **Vector Store Integration**: Seamlessly connects to OpenAI's Vector Store API for semantic document search
- **MCP Protocol Compliance**: Implements the Model Context Protocol for ChatGPT integration
- **Server-Sent Events (SSE)**: Provides real-time communication with ChatGPT
- **Document Retrieval**: Fetches and returns relevant documents based on search queries

### Systematic Review Mode
- **Citation Management**: Upload and parse citations from multiple formats (RIS, CSV, PubMed XML, EndNote)
- **PICO Criteria Configuration**: Define Population, Intervention, Comparator, Outcome criteria
- **Dual Database Support**: PostgreSQL with vector embeddings or SQLite fallback
- **Semantic Search**: OpenAI embeddings for intelligent citation screening
- **Streamlit UI**: Web interface for systematic review workflow
- **Export Capabilities**: Multiple output formats for research results

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Run Vector Store Mode** (Default):
   ```bash
   python main.py
   ```

4. **Run Systematic Review Mode**:
   ```bash
   python main.py sr
   ```

5. **Run Both Modes**:
   ```bash
   python sr_screener/main.py both
   ```

The MCP server starts on `http://localhost:8001` with SSE endpoint at `/sse/` for ChatGPT integration.
The Streamlit UI (systematic review mode) runs on `http://localhost:8000`.

## Configuration

### Environment Variables

Required:
- `OPENAI_API_KEY`: Your OpenAI API key for embeddings and vector store
- `VECTOR_STORE_ID`: OpenAI Vector Store ID (for vector store mode)

Optional:
- `OPENAI_API_KEY_2`: Secondary API key for load balancing
- `DATABASE_URL`: PostgreSQL connection string (defaults to SQLite)
- `MCP_HOST`: MCP server host (default: 0.0.0.0)
- `MCP_PORT`: MCP server port (default: 8001)
- `STREAMLIT_HOST`: Streamlit UI host (default: 0.0.0.0)
- `STREAMLIT_PORT`: Streamlit UI port (default: 8000)

### Database Support

- **PostgreSQL**: Full vector similarity search with pgvector extension
- **SQLite**: Fallback mode with JSON-stored embeddings and Python-computed similarity

## API Endpoints

### MCP Tools

#### Search Tool
- **Purpose**: Search through vector store or citation database
- **Parameters**: 
  - `query` (string): The search query
  - `limit` (integer, optional): Maximum number of results
- **Returns**: List of relevant documents/citations with metadata

#### Fetch Tool  
- **Purpose**: Retrieve specific document or citation by ID
- **Parameters**:
  - `id` (string): The document/citation ID to fetch
- **Returns**: Full content and metadata

#### Health Check Tool
- **Purpose**: Check server status and database connectivity
- **Returns**: Server health and configuration information

#### Corpus Info Tool
- **Purpose**: Get statistics about the citation database
- **Returns**: Citation count, embedding status, database info

### HTTP Endpoints

- **SSE Endpoint**: `/sse/` - Server-Sent Events for ChatGPT MCP communication
- **Health Check**: `/health` - Server status endpoint
- **Streamlit UI**: `http://localhost:8000` - Web interface for systematic reviews

## Development

### Testing the Server

Test MCP protocol compliance:
```bash
python validate_mcp.py
```

Test SSE endpoint connectivity:
```bash
python test_server_connection.py
```

Test database compatibility:
```bash
python test_database_compatibility.py
```

### Running Tests

Test vector store mode:
```bash
python main.py &
curl http://localhost:8001/health
```

Test systematic review mode:
```bash
python main.py sr &
python sr_screener/main.py ui
```

### Linting

```bash
flake8 --exclude=.venv .
```

## Integration with ChatGPT Deep Research

### Vector Store Mode
1. Start the server: `python main.py`
2. Configure ChatGPT to connect to `http://localhost:8001/sse/`
3. ChatGPT can search and retrieve documents from your OpenAI Vector Store

### Systematic Review Mode
1. Start both services: `python sr_screener/main.py both`
2. Upload citations via Streamlit UI at `http://localhost:8000`
3. Configure PICO criteria and screening parameters
4. ChatGPT can search through uploaded citations via MCP at `http://localhost:8001/sse/`

## Citation Formats Supported

- **RIS Format**: Reference Manager, EndNote, Zotero exports
- **CSV Format**: Custom citation spreadsheets
- **PubMed XML**: Direct PubMed exports
- **EndNote Format**: EndNote library exports
- **PMID Lists**: PubMed ID lists for bulk retrieval

## Production Deployment

1. Set up PostgreSQL database with pgvector extension
2. Configure environment variables in `.env`
3. Run database migrations: `python -c "from sr_screener.database import init_db; init_db()"`
4. Start services with process manager (PM2, systemd, etc.)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
