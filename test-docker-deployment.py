#!/usr/bin/env python3
"""
Test Docker Deployment for DeepResearch2

This script tests the Docker deployment of DeepResearch2 by:
1. Validating the MCP server accessibility
2. Testing standard search functionality
3. Testing multi-agent search functionality
"""
import os
import sys
import json
import time
import logging
import requests
import argparse
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def validate_mcp_server(url):
    """Validate MCP server accessibility."""
    if not url.endswith("/sse/"):
        if url.endswith("/"):
            url = url + "sse/"
        else:
            url = url + "/sse/"
    
    try:
        health_url = url.replace("/sse/", "/health")
        logger.info(f"Testing health endpoint: {health_url}")
        response = requests.get(health_url, timeout=10)
        if response.status_code != 200:
            logger.error(f"Health check failed with status code: {response.status_code}")
            return False
        
        logger.info(f"Health check successful: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error accessing URL: {e}")
        return False

def test_standard_search(url, query="systematic review"):
    """Test standard search functionality."""
    try:
        logger.info(f"Testing standard search with query: '{query}'")
        headers = {"Content-Type": "application/json"}
        data = {
            "type": "run_tool",
            "tool": "search",
            "parameters": {
                "query": query,
                "limit": 5,
                "mode": "fulltext"
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code != 200:
            logger.error(f"Standard search failed with status code: {response.status_code}")
            return False
        
        result = response.json()
        if "result" not in result:
            logger.error("No result in response")
            return False
        
        logger.info(f"Standard search successful: {len(result['result'])} results")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error testing standard search: {e}")
        return False

def test_multi_agent_search(url, query="Chiari malformation treatment"):
    """Test multi-agent search functionality."""
    try:
        logger.info(f"Testing multi-agent search with query: '{query}'")
        headers = {"Content-Type": "application/json"}
        data = {
            "type": "run_tool",
            "tool": "multi_agent_search",
            "parameters": {
                "query": query,
                "max_agents": 3,
                "max_iterations": 2
            }
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code != 200:
            logger.error(f"Multi-agent search failed with status code: {response.status_code}")
            return False
        
        result = response.json()
        if "result" not in result:
            logger.error("No result in response")
            return False
        
        logger.info(f"Multi-agent search successful")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Error testing multi-agent search: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test DeepResearch2 Docker deployment")
    parser.add_argument("--url", default="http://localhost:8001/sse/", help="MCP server URL")
    parser.add_argument("--query", default="Chiari malformation", help="Search query")
    args = parser.parse_args()
    
    logger.info("Starting DeepResearch2 Docker deployment test")
    
    if not validate_mcp_server(args.url):
        logger.error("MCP server validation failed")
        return 1
    
    if not test_standard_search(args.url, args.query):
        logger.error("Standard search test failed")
        return 1
    
    if not test_multi_agent_search(args.url, args.query):
        logger.error("Multi-agent search test failed")
        return 1
    
    logger.info("All tests passed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
