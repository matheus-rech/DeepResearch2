# MCP Server Integration Analysis

## Error Analysis: 424 Failed Dependency

When attempting to perform Deep Research screening in the UI, the following error occurs:

```
Error code: 424 - {'error': {'message': "Error retrieving tool list from MCP server: 'DeepResearchServer'. Http status code: 424 (Failed Dependency)", 'type': 'external_connector_error', 'param': 'tools', 'code': 'http_error'}}
```

### Error Interpretation

The 424 HTTP status code (Failed Dependency) indicates that the request failed because it depended on another request that failed. In the context of OpenAI's Deep Research API and MCP servers:

1. **Root Cause**: OpenAI's Deep Research API cannot retrieve the tool list from our MCP server
2. **Dependency Chain**:
   - Deep Research API attempts to connect to our MCP server at the specified URL
   - It tries to retrieve the available tools (search, fetch, etc.)
   - This tool retrieval operation fails with a 424 status code
   - The failure propagates back to the Streamlit UI

### Technical Analysis

Based on examination of the codebase and OpenAI's documentation, the following issues have been identified:

#### 1. MCP Server URL Configuration Issues

The `deep_research.py` file contains inconsistent MCP server URL configurations:

```python
# Default hardcoded URL in function signature
mcp_url: str = "https://repl-nix-workspace-bvibijka.fly.dev/sse/"

# Dynamic URL resolution logic
if os.getenv("HEROKU_APP_NAME"):
    # Running on Heroku - use the public URL
    app_name = os.getenv("HEROKU_APP_NAME")
    mcp_url = f"https://{app_name}.herokuapp.com/sse/"
elif os.getenv("REPL_SLUG") and os.getenv("REPL_OWNER"):
    # Running on Replit - use the public URL with port
    repl_slug = os.getenv("REPL_SLUG")
    repl_owner = os.getenv("REPL_OWNER")
    mcp_url = f"https://{repl_slug}-8001.{repl_owner}.repl.co/sse/"
elif os.getenv("FLY_APP_NAME"):
    # Running on Fly.dev - use the public URL
    app_name = os.getenv("FLY_APP_NAME", "repl-nix-workspace-bvibijka")
    mcp_url = f"https://{app_name}.fly.dev/sse/"
else:
    # Local development fallback
    mcp_url = "http://localhost:8001/sse/"
```

Problems:
- The hardcoded Fly.dev URL may not be accessible or may not exist
- The URL resolution logic doesn't account for potential connectivity issues
- There's no validation that the resolved URL is actually accessible

#### 2. Server Naming Inconsistency

In our implementation:
```python
# sr_screener/mcp_server.py
mcp = FastMCP("DeepResearchServer", instructions=server_instructions)
```

In OpenAI's reference implementation:
```python
# OpenAI cookbook example
mcp = FastMCP(name="Sample Deep Research MCP Server",
              instructions=vector_store_instructions)
```

Problems:
- The server name is inconsistent with OpenAI's reference implementation
- The name "DeepResearchServer" may not provide enough context for the Deep Research API

#### 3. SSE Transport Configuration

Our implementation:
```python
# sr_screener/mcp_server.py
server.run(transport="sse", host="0.0.0.0", port=port)
```

OpenAI's reference:
```python
# OpenAI cookbook example
server.run(transport="sse", host="0.0.0.0", port=8000)
```

While the transport configuration appears correct, there may be issues with:
- Port accessibility from external networks
- Firewall or network configuration blocking the SSE endpoint
- Missing CORS headers for cross-origin requests

#### 4. Tool Registration and Exposure

Our implementation correctly uses the `@mcp.tool()` decorator for registering tools:

```python
@mcp.tool()
async def search(query: str, limit: Optional[int] = None, mode: str = "fulltext") -> Dict[str, Any]:
    # Implementation...
```

However, there may be issues with:
- Tool metadata or schema definition
- Error handling during tool execution
- Response formatting not matching OpenAI's expectations

## Comparison with Reference Implementation

OpenAI's reference implementation in the cookbook provides several key insights:

1. **Server Configuration**:
   - Uses a descriptive server name
   - Explicitly configures SSE transport
   - Sets up proper error handling

2. **Tool Registration**:
   - Uses explicit `@mcp.tool()` decorators
   - Provides comprehensive docstrings for each tool
   - Returns properly formatted responses

3. **Deployment Considerations**:
   - Emphasizes the need for public accessibility
   - Suggests using tunneling tools for local testing
   - Recommends HTTPS for production use

## Recommendations

Based on the analysis, the following fixes are recommended:

### 1. MCP Server URL Configuration

- Remove hardcoded URLs from function signatures
- Implement robust URL resolution logic
- Add validation to ensure the MCP server is accessible
- Use environment variables for configuration

```python
# Recommended implementation
def get_mcp_url():
    """Get the appropriate MCP server URL based on environment."""
    # Priority order: explicit env var, platform-specific logic, localhost fallback
    if os.getenv("MCP_SERVER_URL"):
        return os.getenv("MCP_SERVER_URL")
    elif os.getenv("HEROKU_APP_NAME"):
        return f"https://{os.getenv('HEROKU_APP_NAME')}.herokuapp.com/sse/"
    elif os.getenv("FLY_APP_NAME"):
        return f"https://{os.getenv('FLY_APP_NAME')}.fly.dev/sse/"
    elif os.getenv("REPL_SLUG") and os.getenv("REPL_OWNER"):
        return f"https://{os.getenv('REPL_SLUG')}-8001.{os.getenv('REPL_OWNER')}.repl.co/sse/"
    else:
        return "http://localhost:8001/sse/"
```

### 2. Server Naming and Instructions

- Use a more descriptive server name
- Provide comprehensive instructions
- Ensure consistency with OpenAI's reference implementation

```python
# Recommended implementation
mcp = FastMCP(
    name="DeepResearch Systematic Review MCP Server",
    instructions="""
    This MCP server provides search and document retrieval capabilities for systematic review screening.
    Use the search tool to find relevant citations based on keywords or concepts, then use the fetch tool 
    to retrieve complete citation details including abstract, authors, and metadata.
    """
)
```

### 3. SSE Transport and Accessibility

- Ensure the server is accessible from external networks
- Add proper CORS headers for cross-origin requests
- Consider using a reverse proxy or API gateway for production

```python
# Recommended implementation
from starlette.middleware.cors import CORSMiddleware

# Add CORS middleware
server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Run with SSE transport
server.run(transport="sse", host="0.0.0.0", port=port)
```

### 4. Tool Registration and Response Formatting

- Ensure tool responses match OpenAI's expected format
- Add comprehensive error handling
- Provide detailed docstrings for each tool

```python
# Recommended implementation
@mcp.tool()
async def search(query: str, limit: Optional[int] = None, mode: str = "fulltext") -> Dict[str, Any]:
    """
    Search for citations in the systematic review corpus.
    
    This tool searches through titles, abstracts, and metadata to find 
    semantically relevant citations. Returns a list of matching citations 
    with basic information. Use the fetch tool to get complete details.
    
    Args:
        query: Search query string. Natural language queries work best.
        limit: Maximum number of results to return (default: None - returns all matching citations)
        mode: Search mode - "fulltext" for keyword search or "semantic" for embedding-based search
    
    Returns:
        Dictionary with 'results' key containing list of matching citations.
        Each result includes id, title, text snippet, and url per Deep Research spec.
    """
    try:
        # Implementation...
        return {"results": formatted_results}
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {"results": [], "error": str(e)}
```

## Deployment Recommendations

For production deployment, consider the following:

1. **Use HTTPS**: Ensure the MCP server is accessible via HTTPS
2. **Public Accessibility**: The server must be accessible from OpenAI's servers
3. **Environment Variables**: Use environment variables for configuration
4. **Monitoring**: Add comprehensive logging and monitoring
5. **Error Handling**: Implement robust error handling and fallback mechanisms

## Similar Issues in the Community

Research into similar 424 errors with MCP servers reveals:

1. **Accessibility Issues**: The most common cause is the MCP server not being publicly accessible
2. **Tool Registration Problems**: Incorrect tool registration or response formatting
3. **Authentication Failures**: Missing or invalid API keys
4. **Transport Configuration**: Incorrect SSE transport configuration

## Conclusion

The 424 "Failed Dependency" error is primarily caused by OpenAI's Deep Research API being unable to retrieve the tool list from our MCP server. This is likely due to a combination of:

1. Incorrect or inaccessible MCP server URL
2. Server naming and configuration inconsistencies
3. SSE transport accessibility issues
4. Tool registration or response formatting problems

Implementing the recommended fixes should resolve the issue and enable successful integration with OpenAI's Deep Research API.
