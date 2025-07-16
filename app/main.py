#!/usr/bin/env python3
"""
FastAPI wrapper for MCP Server deployment on Heroku
"""
import os
import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "sr_screener"))

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DeepResearch2 MCP Server",
    description="MCP Server for OpenAI Deep Research API integration",
    version="1.0.0"
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "DeepResearch2 MCP Server", "status": "running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        return JSONResponse({
            "status": "healthy",
            "server": "DeepResearch2-MCP-Server",
            "message": "Server is running"
        })
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e)
        }, status_code=500)

@app.on_event("startup")
async def startup_event():
    """Initialize MCP server on startup"""
    logger.info("Starting DeepResearch2 MCP Server")
    
    try:
        import sr_screener.mcp_server as mcp_server
        
        mcp = mcp_server.create_server()
        
        @app.get("/sse/")
        async def mcp_sse_endpoint():
            """MCP SSE endpoint for OpenAI Deep Research"""
            return {"message": "MCP SSE endpoint - use SSE client to connect"}
        
        logger.info("MCP server initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize MCP server: {e}")
        raise

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
