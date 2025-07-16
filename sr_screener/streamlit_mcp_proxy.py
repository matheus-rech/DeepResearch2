"""
Streamlit-integrated MCP proxy for external access
"""
import streamlit as st
import requests
import json

def create_mcp_proxy_route():
    """Create MCP proxy route that forwards requests to local MCP server"""
    
    # This runs inside Streamlit context
    if 'mcp_proxy_path' in st.query_params:
        mcp_path = st.query_params['mcp_proxy_path']
        
        # Forward to local MCP server
        local_mcp_url = f"http://localhost:8001{mcp_path}"
        
        try:
            # Get request method and data from session state
            method = st.session_state.get('mcp_method', 'GET')
            data = st.session_state.get('mcp_data', None)
            
            # Forward the request
            if method == 'GET':
                response = requests.get(local_mcp_url, timeout=30)
            elif method == 'POST':
                response = requests.post(local_mcp_url, json=data, timeout=30)
            else:
                response = requests.request(method, local_mcp_url, json=data, timeout=30)
            
            # Return response
            st.session_state.mcp_response = {
                'status': response.status_code,
                'headers': dict(response.headers),
                'content': response.text
            }
            
        except Exception as e:
            st.session_state.mcp_response = {
                'status': 502,
                'headers': {'Content-Type': 'application/json'},
                'content': json.dumps({'error': str(e)})
            }
    
    return st.session_state.get('mcp_response', None)

def setup_mcp_proxy():
    """Setup MCP proxy in Streamlit app"""
    
    # Add custom CSS to hide proxy functionality from users
    st.markdown("""
    <style>
    .mcp-proxy-hidden {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Check if this is a proxy request
    response = create_mcp_proxy_route()
    if response:
        # This is a proxy request - handle it
        st.markdown(f'<div class="mcp-proxy-hidden">{response}</div>', unsafe_allow_html=True)
        return True
    
    return False