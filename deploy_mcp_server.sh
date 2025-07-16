#!/bin/bash

set -e

if ! command -v flyctl &> /dev/null; then
    echo "Fly.io CLI not found. Installing..."
    curl -L https://fly.io/install.sh | sh
    export FLYCTL_INSTALL="/home/ubuntu/.fly"
    export PATH="$FLYCTL_INSTALL/bin:$PATH"
fi

if ! flyctl auth whoami &> /dev/null; then
    echo "Please authenticate with Fly.io:"
    flyctl auth login
fi

APP_NAME="deepresearch2-mcp"
if ! flyctl apps list | grep -q "$APP_NAME"; then
    echo "Creating new Fly.io app: $APP_NAME"
    flyctl apps create "$APP_NAME" --org personal
else
    echo "App $APP_NAME already exists"
fi

echo "Setting environment variables..."
flyctl secrets set \
    OPENAI_API_KEY="$OPENAI_API_KEY" \
    VECTOR_STORE_ID="$VECTOR_STORE_ID" \
    MCP_HOST="0.0.0.0" \
    MCP_PORT="8001" \
    STREAMLIT_HOST="0.0.0.0" \
    STREAMLIT_PORT="8000" \
    EXTERNAL_HOST="$APP_NAME.fly.dev" \
    EXTERNAL_PORT="443" \
    EXTERNAL_PROTOCOL="https" \
    LOG_LEVEL="INFO" \
    DOCKER_CONTAINER="true"

echo "Deploying application..."
flyctl deploy

echo "Verifying deployment..."
flyctl status

echo "Testing MCP server..."
curl -s "https://$APP_NAME.fly.dev/health" | python -m json.tool

echo "Deployment complete! MCP server is available at: https://$APP_NAME.fly.dev/sse/"
echo "To validate the server, run: python validate_mcp_server.py --url https://$APP_NAME.fly.dev/sse/"
