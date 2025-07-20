#!/usr/bin/env python3
"""
Robust server readiness checker with exponential backoff.
Replaces unreliable time.sleep() patterns with proper health checks.
"""

import time
import requests
import logging

logger = logging.getLogger(__name__)

def wait_for_server(
    url: str, 
    timeout: int = 30,
    max_retries: int = 10,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0
) -> bool:
    """
    Wait for a server to be ready with exponential backoff.

    Args:
        url: URL to check for server readiness
        timeout: Total timeout in seconds
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor to multiply delay by each retry

    Returns:
        True if server is ready, False if timeout reached
    """
    start_time = time.time()
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            logger.info(f"Checking server readiness: {url} (attempt {attempt + 1}/{max_retries})")

            # Check if we've exceeded total timeout
            if time.time() - start_time > timeout:
                logger.error(f"Server readiness check timed out after {timeout} seconds")
                return False

            # Attempt to connect to server
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                logger.info(f"Server is ready at {url}")
                return True
            else:
                logger.warning(f"Server responded with status {response.status_code}")

        except requests.exceptions.RequestException as e:
            logger.warning(f"Server not ready: {e}")

        # Calculate next delay with exponential backoff
        if attempt < max_retries - 1:  # Don't sleep on the last attempt
            actual_delay = min(delay, max_delay)
            logger.info(f"Retrying in {actual_delay:.1f} seconds...")
            time.sleep(actual_delay)
            delay *= backoff_factor

    logger.error(f"Server failed to become ready after {max_retries} attempts")
    return False

def wait_for_streamlit(host: str = "localhost", port: int = 8000, timeout: int = 30) -> bool:
    """Wait for Streamlit server to be ready."""
    url = f"http://{host}:{port}"
    return wait_for_server(url, timeout=timeout)

def wait_for_mcp_server(host: str = "localhost", port: int = 8001, timeout: int = 30) -> bool:
    """Wait for MCP server to be ready."""
    url = f"http://{host}:{port}/health"
    return wait_for_server(url, timeout=timeout)

def wait_for_multiple_servers(servers: list, timeout: int = 60) -> bool:
    """
    Wait for multiple servers to be ready.

    Args:
        servers: List of (url, description) tuples
        timeout: Total timeout for all servers

    Returns:
        True if all servers are ready, False otherwise
    """
    start_time = time.time()

    for url, description in servers:
        remaining_time = timeout - (time.time() - start_time)
        if remaining_time <= 0:
            logger.error(f"Timeout reached before checking {description}")
            return False

        logger.info(f"Waiting for {description}...")
        if not wait_for_server(url, timeout=int(remaining_time)):
            logger.error(f"Failed to wait for {description}")
            return False

    logger.info("All servers are ready!")
    return True

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Test single server
    if wait_for_streamlit():
        print("✅ Streamlit server is ready")
    else:
        print("❌ Streamlit server failed to start")
    # Test multiple servers
    servers = [
        ("http://localhost:8000", "Streamlit UI"),
        ("http://localhost:8001/health", "MCP Server")
    ]
    if wait_for_multiple_servers(servers):
        print("✅ All servers are ready")
    else:
        print("❌ Some servers failed to start")
