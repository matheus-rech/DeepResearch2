#!/bin/bash
set -e

echo "DeepResearch2 Docker Deployment"
echo "==============================="

if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

if [ ! -f .env.docker ]; then
    if [ -f .env.example ]; then
        echo "Creating .env.docker from .env.example..."
        cp .env.example .env.docker
        echo "Please edit .env.docker to set your environment variables."
        exit 1
    else
        echo "Error: .env.example not found. Please create .env.docker manually."
        exit 1
    fi
fi

export $(grep -v '^#' .env.docker | xargs)

if [ -z "$EXTERNAL_HOST" ]; then
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    echo "Setting EXTERNAL_HOST to local IP: $LOCAL_IP"
    echo "EXTERNAL_HOST=$LOCAL_IP" >> .env.docker
    echo "EXTERNAL_PORT=8001" >> .env.docker
    echo "EXTERNAL_PROTOCOL=http" >> .env.docker
fi

echo "Building and starting Docker containers..."
docker-compose --env-file .env.docker up -d --build

echo "Waiting for services to start..."
sleep 10

echo "Checking MCP server health..."
if curl -s http://localhost:8001/health | grep -q "healthy"; then
    echo "MCP server is running and healthy!"
else
    echo "Warning: MCP server health check failed. Check logs for details."
    docker-compose logs deepresearch2
fi

echo ""
echo "DeepResearch2 is now running!"
echo "=============================="
echo "Streamlit UI: http://localhost:8000"
echo "MCP Server: http://localhost:8001"
echo "MCP Server SSE Endpoint: http://localhost:8001/sse/"
echo ""
echo "To view logs: docker-compose logs -f deepresearch2"
echo "To stop: docker-compose down"
echo ""
echo "For OpenAI Deep Research API integration, use this MCP Server URL:"
echo "http://$EXTERNAL_HOST:${EXTERNAL_PORT:-8001}/sse/"
