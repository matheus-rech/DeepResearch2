"""
Simple proxy server to forward requests from port 8000 to Streamlit on port 5000
Resolves WebSocket connection issues by proper routing
"""

import asyncio
import aiohttp
from aiohttp import web
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STREAMLIT_URL = "http://localhost:5000"


async def websocket_handler(request):
    """Handle WebSocket connections by proxying to Streamlit"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    # Create connection to Streamlit WebSocket
    session = aiohttp.ClientSession()
    try:
        # Build the target WebSocket URL
        target_url = STREAMLIT_URL.replace('http://', 'ws://') + request.path_qs
        
        async with session.ws_connect(target_url) as upstream_ws:
            # Create tasks for bidirectional message forwarding
            async def forward_to_upstream():
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await upstream_ws.send_str(msg.data)
                    elif msg.type == aiohttp.WSMsgType.BINARY:
                        await upstream_ws.send_bytes(msg.data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f'WebSocket error: {ws.exception()}')
                        break
            
            async def forward_to_client():
                async for msg in upstream_ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await ws.send_str(msg.data)
                    elif msg.type == aiohttp.WSMsgType.BINARY:
                        await ws.send_bytes(msg.data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f'Upstream WebSocket error: {upstream_ws.exception()}')
                        break
            
            # Run both forwarding tasks concurrently
            await asyncio.gather(
                forward_to_upstream(),
                forward_to_client(),
                return_exceptions=True
            )
    
    except Exception as e:
        logger.error(f"WebSocket proxy error: {e}")
    finally:
        await session.close()
        await ws.close()
    
    return ws


async def proxy_handler(request):
    """Handle HTTP requests by proxying to Streamlit"""
    # Check if this is a WebSocket upgrade request
    if request.headers.get('Upgrade') == 'websocket':
        return await websocket_handler(request)
    
    # Build target URL
    target_url = STREAMLIT_URL + request.path_qs
    
    # Create session and make request
    async with aiohttp.ClientSession() as session:
        # Copy headers, removing hop-by-hop headers
        headers = {k: v for k, v in request.headers.items()
                   if k.lower() not in ['host', 'connection', 'upgrade', 'transfer-encoding']}
        
        # Make the request
        try:
            async with session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=await request.read() if request.body_exists else None,
                allow_redirects=False
            ) as resp:
                # Create response
                body = await resp.read()
                
                # Copy response headers, removing hop-by-hop headers
                response_headers = {k: v for k, v in resp.headers.items()
                                    if k.lower() not in ['connection', 'transfer-encoding', 'content-encoding']}
                
                return web.Response(
                    body=body,
                    status=resp.status,
                    headers=response_headers
                )
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            return web.Response(text=f"Proxy error: {str(e)}", status=500)


async def health_check(request):
    """Simple health check endpoint"""
    return web.Response(text="Proxy server is running", status=200)


def create_app():
    """Create the proxy application"""
    app = web.Application()
    
    # Add routes
    app.router.add_get('/health', health_check)
    app.router.add_route('*', '/{path:.*}', proxy_handler)
    
    return app


if __name__ == '__main__':
    app = create_app()
    logger.info("Starting proxy server on port 8000 -> Streamlit on port 5000")
    web.run_app(app, host='0.0.0.0', port=8000)