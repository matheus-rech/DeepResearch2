# DeepResearch2 Testing Guide

## Test Suite Overview

This repository includes comprehensive testing to ensure production readiness:

### Core Tests

1. **Quick Validation** (`test_quick_validation.py`)
   - Module imports
   - Environment configuration
   - File structure validation

2. **Database Compatibility** (`test_database_compatibility.py`)
   - SQLite/PostgreSQL compatibility
   - Citation insertion and search
   - Embedding generation

3. **End-to-End Testing** (`test_end_to_end.py`)
   - Database operations
   - Citation parsing
   - MCP tools functionality
   - Server startup tests
   - SSE endpoint connectivity

4. **Production Readiness** (`production_test.py`)
   - Environment configuration
   - Dual-mode startup
   - Service health checks

### Running Tests

#### Quick Validation
```bash
python test_quick_validation.py
```

#### Database Tests
```bash
python test_database_compatibility.py
```

#### Full End-to-End
```bash
python test_end_to_end.py
```

#### Production Readiness
```bash
python production_test.py
```

### Individual Component Tests

#### MCP Tools
```bash
python test_mcp_tools.py
```

#### Streamlit UI
```bash
python test_streamlit_ui.py
```

#### MCP Protocol Validation
```bash
python validate_mcp.py
```

#### SSE Connection
```bash
python test_server_connection.py
```

### Test Environment Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Activate Virtual Environment**
   ```bash
   source .venv/bin/activate
   ```

### Expected Test Results

#### Passing Tests
- ✅ Database initialization and operations
- ✅ Citation parsing and sample data validation
- ✅ MCP tools registration and functionality
- ✅ Environment configuration validation
- ✅ File structure completeness

#### Server Startup Tests
These tests require network connectivity and may take longer:
- Vector Store Mode server startup
- Systematic Review Mode server startup
- SSE endpoint accessibility

#### Common Issues

1. **Connection Refused Errors**
   - Servers may take time to start (8-15 seconds)
   - Check if ports 8000/8001 are available
   - Verify environment variables are set

2. **Import Errors**
   - Ensure virtual environment is activated
   - Check all dependencies are installed
   - Verify Python path includes sr_screener

3. **Database Errors**
   - SQLite fallback should work automatically
   - Check write permissions in project directory
   - Verify OpenAI API key for embeddings

### Continuous Integration

The test suite is designed to work in CI environments:

```bash
# Run all tests in sequence
python test_quick_validation.py && \
python test_database_compatibility.py && \
python test_end_to_end.py
```

### Test Coverage

- ✅ Database operations (SQLite/PostgreSQL)
- ✅ Citation parsing (RIS, CSV, XML, EndNote)
- ✅ MCP protocol compliance
- ✅ OpenAI API integration
- ✅ Streamlit UI functionality
- ✅ Server startup and health checks
- ✅ Environment configuration
- ✅ File structure validation

### Performance Benchmarks

- Database initialization: < 2 seconds
- Citation insertion (100 records): < 5 seconds
- Embedding generation: Depends on OpenAI API
- Server startup: 8-15 seconds
- Health check response: < 1 second

### Debugging Failed Tests

1. **Check Logs**
   ```bash
   # Server logs during testing
   tail -f server.log
   ```

2. **Manual Server Testing**
   ```bash
   # Start server manually
   python main.py sr
   
   # Test health endpoint
   curl http://localhost:8001/health
   ```

3. **Database Debugging**
   ```bash
   # Check database file
   ls -la citations.db
   
   # Test database connection
   python -c "from sr_screener.database import init_db; init_db()"
   ```

4. **Environment Debugging**
   ```bash
   # Check environment variables
   env | grep OPENAI
   env | grep VECTOR_STORE
   ```

### Test Data

- `sample_citations.csv`: Sample citation data for testing
- `sr_screener/sample_criteria.json`: PICO criteria configuration
- `sample_data.json`: Additional test documents

### Integration Testing

For ChatGPT Deep Research integration:

1. Start the MCP server
2. Configure ChatGPT to connect to `http://localhost:8001/sse/`
3. Test search and fetch operations through ChatGPT interface
4. Verify systematic review workflow through Streamlit UI

### Security Testing

- API keys are properly handled as environment variables
- No secrets are logged or exposed in responses
- Database connections use appropriate security measures
- HTTPS support for production deployment
