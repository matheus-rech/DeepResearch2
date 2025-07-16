#!/usr/bin/env python3
"""
MCP Server Validation Script

This script validates the accessibility and configuration of the MCP server
for OpenAI's Deep Research API integration.
"""
import os
import sys
import json
import time
import argparse
import logging
import requests
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def validate_url(url):
    """Validate URL format and accessibility."""
    if not url:
        logger.error("URL is empty")
        return False
    
    if not url.endswith("/sse/"):
        logger.warning(f"URL does not end with /sse/: {url}")
        if url.endswith("/"):
            url = url + "sse/"
        else:
            url = url + "/sse/"
        logger.info(f"Updated URL to: {url}")
    
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        logger.error(f"Invalid URL format: {url}")
        return False
    
    try:
        health_url = url.replace("/sse/", "/health")
        logger.info(f"Testing health endpoint: {health_url}")
        response = requests.get(health_url, timeout=10)
        if response.status_code != 200:
            logger.error(f"Health check failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
        
        logger.info(f"Health check successful: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error accessing URL: {e}")
        return False

def test_cors_headers(url):
    """Test CORS headers for cross-origin requests."""
    try:
        logger.info(f"Testing CORS headers for: {url}")
        headers = {
            "Origin": "https://chat.openai.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
        response = requests.options(url, headers=headers, timeout=10)
        
        cors_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers"
        ]
        
        missing_headers = [h for h in cors_headers if h not in response.headers]
        if missing_headers:
            logger.error(f"Missing CORS headers: {missing_headers}")
            logger.error(f"Response headers: {dict(response.headers)}")
            return False
        
        logger.info("CORS headers are properly configured")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error testing CORS headers: {e}")
        return False

def test_tool_list_retrieval(url):
    """Test tool list retrieval from MCP server."""
    try:
        logger.info(f"Testing tool list retrieval from: {url}")
        headers = {"Content-Type": "application/json"}
        data = {"type": "get_tools"}
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code != 200:
            logger.error(f"Tool list retrieval failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
        
        tools = response.json().get("tools", [])
        if not tools:
            logger.error("No tools returned from MCP server")
            logger.error(f"Response: {response.json()}")
            return False
        
        logger.info(f"Successfully retrieved {len(tools)} tools from MCP server")
        for tool in tools:
            logger.info(f"Tool: {tool.get('name')} - {tool.get('description', '')[:50]}...")
        
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error retrieving tool list: {e}")
        return False

def test_sse_endpoint(url):
    """Test SSE endpoint accessibility."""
    try:
        logger.info(f"Testing SSE endpoint: {url}")
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"SSE endpoint test failed with status code: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False
        
        logger.info("SSE endpoint is accessible")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error testing SSE endpoint: {e}")
        return False

def get_mcp_url():
    """Get MCP server URL from environment or command line."""
    parser = argparse.ArgumentParser(description="Validate MCP server for Deep Research API")
    parser.add_argument("--url", help="MCP server URL")
    args = parser.parse_args()
    
    if args.url:
        return args.url
    
    if os.getenv("MCP_SERVER_URL"):
        return os.getenv("MCP_SERVER_URL")
    
    if os.getenv("FLY_APP_NAME"):
        app_name = os.getenv("FLY_APP_NAME")
        return f"https://{app_name}.fly.dev/sse/"
    
    if os.getenv("HEROKU_APP_NAME"):
        app_name = os.getenv("HEROKU_APP_NAME")
        return f"https://{app_name}.herokuapp.com/sse/"
    
    if os.getenv("REPL_SLUG") and os.getenv("REPL_OWNER"):
        repl_slug = os.getenv("REPL_SLUG")
        repl_owner = os.getenv("REPL_OWNER")
        return f"https://{repl_slug}-8001.{repl_owner}.repl.co/sse/"
    
    return "http://localhost:8001/sse/"

def main():
    """Main validation function."""
    logger.info("Starting MCP server validation")
    
    url = get_mcp_url()
    logger.info(f"Using MCP server URL: {url}")
    
    if not validate_url(url):
        logger.error("URL validation failed")
        sys.exit(1)
    
    if not test_sse_endpoint(url):
        logger.error("SSE endpoint test failed")
        sys.exit(1)
    
    if not test_cors_headers(url):
        logger.warning("CORS headers test failed - this may cause issues with OpenAI's Deep Research API")
    
    if not test_tool_list_retrieval(url):
        logger.error("Tool list retrieval test failed")
        sys.exit(1)
    
    logger.info("MCP server validation completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
