#!/bin/bash
set -e

# DeepResearch2 Docker Deployment Script
echo "DeepResearch2 Docker Deployment"
echo "==============================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    echo "Visit https://docs.docker.com/get-docker/ for installation instructions."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Error: Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit https://docs.docker.com/compose/install/ for installation instructions."
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "Error: Docker daemon is not running. Please start Docker first."
    echo "On Linux: sudo systemctl start docker"
    echo "On macOS/Windows: Start Docker Desktop"
    exit 1
fi

# Check if .env.docker exists, if not create it from example
if [ ! -f .env.docker ]; then
    if [ -f .env.docker.example ]; then
        echo "Creating .env.docker from .env.docker.example..."
        cp .env.docker.example .env.docker
        echo "Please edit .env.docker to set your environment variables."
        
        # Check if OPENAI_API_KEY is set in environment
        if [ ! -z "$OPENAI_API_KEY" ]; then
            echo "Found OPENAI_API_KEY in environment, adding to .env.docker..."
            sed -i "s/OPENAI_API_KEY=your_openai_api_key_here/OPENAI_API_KEY=$OPENAI_API_KEY/g" .env.docker
        else
            echo "WARNING: OPENAI_API_KEY is not set. You must edit .env.docker to add your API key."
            echo "Press Enter to continue or Ctrl+C to abort and edit the file manually."
            read
        fi
        
        # Check if VECTOR_STORE_ID is set in environment
        if [ ! -z "$VECTOR_STORE_ID" ]; then
            echo "Found VECTOR_STORE_ID in environment, adding to .env.docker..."
            sed -i "s/VECTOR_STORE_ID=your_vector_store_id_here/VECTOR_STORE_ID=$VECTOR_STORE_ID/g" .env.docker
        fi
    else
        echo "Error: .env.docker.example not found. Please create .env.docker manually."
        exit 1
    fi
fi

# Load environment variables
export $(grep -v '^#' .env.docker | xargs -0 2>/dev/null)

# Set external host for MCP server
if [ -z "$EXTERNAL_HOST" ] || [ "$EXTERNAL_HOST" = "your_public_hostname_here" ] || [ "$EXTERNAL_HOST" = "localhost" ]; then
    # Get local IP address
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    if [ -z "$LOCAL_IP" ]; then
        # Fallback for macOS
        LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || echo "localhost")
    fi
    echo "Setting EXTERNAL_HOST to local IP: $LOCAL_IP"
    sed -i "s/EXTERNAL_HOST=.*/EXTERNAL_HOST=$LOCAL_IP/g" .env.docker
    sed -i "s/EXTERNAL_PORT=.*/EXTERNAL_PORT=8001/g" .env.docker
    sed -i "s/EXTERNAL_PROTOCOL=.*/EXTERNAL_PROTOCOL=http/g" .env.docker
    
    # Reload environment variables
    export $(grep -v '^#' .env.docker | xargs -0 2>/dev/null)
fi

# Check for port conflicts
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Warning: Port 8000 is already in use. Streamlit UI may not start correctly."
fi

if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null ; then
    echo "Warning: Port 8001 is already in use. MCP server may not start correctly."
fi

# Build and start containers
echo "Building and starting Docker containers..."
docker-compose --env-file .env.docker up -d --build

# Wait for services to start
echo "Waiting for services to start..."
for i in {1..30}; do
    echo -n "."
    if curl -s http://localhost:8001/health &> /dev/null; then
        echo " Done!"
        break
    fi
    sleep 1
    if [ $i -eq 30 ]; then
        echo " Timeout!"
    fi
done

# Check if MCP server is running
echo "Checking MCP server health..."
if curl -s http://localhost:8001/health | grep -q "healthy"; then
    echo "✅ MCP server is running and healthy!"
else
    echo "⚠️ Warning: MCP server health check failed. Check logs for details."
    docker-compose logs deepresearch2
fi

# Test tool list retrieval
echo "Testing tool list retrieval..."
if curl -s -X POST -H "Content-Type: application/json" -d '{"type":"get_tools"}' http://localhost:8001/sse/ | grep -q "tools"; then
    echo "✅ Tool list retrieval successful!"
else
    echo "⚠️ Warning: Tool list retrieval failed. This may cause issues with OpenAI's Deep Research API."
    echo "Check logs for details:"
    docker-compose logs deepresearch2
fi

# Print access information
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
echo ""
echo "For more information, see DOCKER_DEPLOYMENT.md"
