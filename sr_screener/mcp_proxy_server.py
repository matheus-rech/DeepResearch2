"""
Simple HTTP proxy server that forwards MCP requests to the internal server
and serves Streamlit on other paths
"""
import asyncio
import aiohttp
from aiohttp import web
import subprocess
import sys
import os
import logging
from pathlib import Path
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MCPProxyServer:
    def __init__(self):
        self.streamlit_process = None
        self.mcp_server_ready = False
        
    async def start_mcp_server(self):
        """Start the MCP server on port 8001"""
        def run_mcp():
            sys.path.insert(0, str(Path(__file__).parent))
            import mcp_server
            mcp_server.main(port=8001)
        
        # Start MCP server in thread
        mcp_thread = threading.Thread(target=run_mcp, daemon=True)
        mcp_thread.start()
        
        # Wait for MCP server to be ready
        await asyncio.sleep(3)
        self.mcp_server_ready = True
        logger.info("MCP server started and ready")
        
    def start_streamlit(self):
        """Start Streamlit app on port 8002"""
        logger.info("Starting Streamlit app on port 8002...")
        app_path = Path(__file__).parent / "app.py"
        
        env = os.environ.copy()
        env['MCP_URL'] = 'http://localhost:8001/sse/'
        
        self.streamlit_process = subprocess.Popen([
            sys.executable, "-m", "streamlit", "run", str(app_path),
            "--server.port", "8002",
            "--server.address", "0.0.0.0"
        ], env=env)
        
    async def proxy_to_streamlit(self, request):
        """Proxy request to Streamlit app"""
        target_url = f"http://localhost:8002{request.path_qs}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=request.headers,
                    data=await request.read()
                ) as response:
                    body = await response.read()
                    return web.Response(
                        body=body,
                        status=response.status,
                        headers=response.headers
                    )
            except Exception as e:
                logger.error(f"Streamlit proxy error: {e}")
                return web.Response(text=f"Streamlit connection error: {e}", status=502)
    
    async def proxy_to_mcp(self, request):
        """Proxy request to MCP server"""
        if not self.mcp_server_ready:
            return web.Response(text="MCP server not ready", status=503)
            
        # Forward to MCP server on port 8001
        target_url = f"http://localhost:8001{request.path_qs}"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=request.headers,
                    data=await request.read()
                ) as response:
                    body = await response.read()
                    
                    # Preserve SSE headers
                    headers = dict(response.headers)
                    if 'content-type' in headers and 'text/event-stream' in headers['content-type']:
                        headers['Cache-Control'] = 'no-cache'
                        headers['Connection'] = 'keep-alive'
                    
                    return web.Response(
                        body=body,
                        status=response.status,
                        headers=headers
                    )
            except Exception as e:
                logger.error(f"MCP proxy error: {e}")
                return web.Response(text=f"MCP server connection error: {e}", status=502)
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.Response(text="OK", status=200)
    
    def create_app(self):
        """Create the proxy application"""
        app = web.Application()
        
        # Add CORS middleware
        async def cors_middleware(request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return response
        
        app.middlewares.append(cors_middleware)
        
        # MCP routes
        app.router.add_route('*', '/sse/{path:.*}', self.proxy_to_mcp)
        app.router.add_route('*', '/mcp/{path:.*}', self.proxy_to_mcp)
        
        # Health check
        app.router.add_get('/health', self.health_check)
        
        # Default route - proxy to Streamlit
        app.router.add_route('*', '/{path:.*}', self.proxy_to_streamlit)
        
        return app
    
    async def run(self):
        """Run the proxy server"""
        logger.info("Starting MCP proxy server...")
        
        # Start MCP server
        await self.start_mcp_server()
        
        # Start Streamlit
        self.start_streamlit()
        
        # Wait for Streamlit to start
        await asyncio.sleep(3)
        
        # Create and run proxy app
        app = self.create_app()
        
        logger.info("Proxy server ready on port 8000")
        logger.info("MCP endpoints: /sse/ and /mcp/")
        logger.info("Streamlit UI: / (all other paths)")
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8000)
        await site.start()
        
        # Keep running
        try:
            await asyncio.Future()  # Run forever
        except KeyboardInterrupt:
            logger.info("Shutting down proxy server...")
            if self.streamlit_process:
                self.streamlit_process.terminate()

def main():
    """Main function"""
    proxy = MCPProxyServer()
    asyncio.run(proxy.run())

if __name__ == "__main__":
    main()