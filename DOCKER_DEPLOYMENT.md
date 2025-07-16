# Docker Deployment Guide for DeepResearch2

This guide provides instructions for deploying the DeepResearch2 application using Docker. The deployment includes both the Streamlit UI and the MCP server required for OpenAI's Deep Research API integration.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (version 20.10.0 or higher)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0.0 or higher)
- OpenAI API Key with access to the Deep Research API
- Vector Store ID (optional, for using OpenAI's Vector Store)

## Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/matheus-rech/DeepResearch2.git
   cd DeepResearch2
   ```

2. Create a `.env.docker` file with your environment variables:
   ```bash
   cp .env.docker.example .env.docker
   # Edit .env.docker with your API keys and configuration
   ```

3. Run the deployment script:
   ```bash
   chmod +x docker-deploy.sh
   ./docker-deploy.sh
   ```

4. Access the application:
   - Streamlit UI: http://localhost:8000
   - MCP Server: http://localhost:8001
   - MCP Server SSE Endpoint: http://localhost:8001/sse/

## Manual Deployment

If you prefer to deploy manually or need more control over the deployment process:

1. Build and start the containers:
   ```bash
   docker-compose --env-file .env.docker up -d --build
   ```

2. Check the container status:
   ```bash
   docker-compose ps
   ```

3. View logs:
   ```bash
   docker-compose logs -f deepresearch2
   ```

4. Stop the containers:
   ```bash
   docker-compose down
   ```

## Environment Variables

The following environment variables can be configured in your `.env.docker` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key (required) | - |
| `OPENAI_API_KEY_2` | Secondary OpenAI API key (optional) | - |
| `VECTOR_STORE_ID` | Vector Store ID for Deep Research API (optional) | - |
| `DATABASE_URL` | Database connection string | `sqlite:///citations.db` |
| `MCP_HOST` | MCP server host | `0.0.0.0` |
| `MCP_PORT` | MCP server port | `8001` |
| `STREAMLIT_HOST` | Streamlit UI host | `0.0.0.0` |
| `STREAMLIT_PORT` | Streamlit UI port | `8000` |
| `EXTERNAL_HOST` | External hostname for MCP server | `localhost` |
| `EXTERNAL_PORT` | External port for MCP server | `8001` |
| `EXTERNAL_PROTOCOL` | Protocol for external access | `http` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Testing the Deployment

To verify that your deployment is working correctly, you can use the included test script:

```bash
python test-docker-deployment.py
```

This script will:
1. Validate the MCP server accessibility
2. Test standard search functionality
3. Test multi-agent search functionality

## Troubleshooting

### MCP Server Not Accessible

If the MCP server is not accessible, check the following:

1. Verify that the container is running:
   ```bash
   docker-compose ps
   ```

2. Check the logs for any errors:
   ```bash
   docker-compose logs deepresearch2
   ```

3. Ensure that the MCP server port (8001) is not being used by another application.

4. Verify that the environment variables are correctly set in your `.env.docker` file.

### OpenAI Deep Research API Integration Issues

If you encounter a 424 "Failed Dependency" error when using the Deep Research API:

1. Ensure that your OpenAI API key has access to the Deep Research API.

2. Verify that the MCP server is accessible from the internet if you're using the OpenAI web interface.

3. Check that the MCP server URL is correctly configured in the Streamlit UI.

4. Verify that the MCP server is properly configured with CORS headers.

5. Test the MCP server directly using curl:
   ```bash
   curl -s http://localhost:8001/health | python -m json.tool
   curl -s -X POST -H "Content-Type: application/json" -d '{"type":"get_tools"}' http://localhost:8001/sse/ | python -m json.tool
   ```

## Production Deployment

For production deployment, consider the following:

1. Use a reverse proxy like Traefik or Nginx to handle SSL/TLS termination.

2. Set up proper authentication for the MCP server.

3. Configure the `EXTERNAL_HOST`, `EXTERNAL_PORT`, and `EXTERNAL_PROTOCOL` variables to match your production environment.

4. Consider using a PostgreSQL database instead of SQLite for better performance and reliability.

5. Set up monitoring and alerting for the containers.

The repository includes a Traefik configuration in the `docker-compose.yml` file that can be enabled by using the `production` profile:

```bash
docker-compose --profile production --env-file .env.docker up -d
```

## Using with OpenAI's Deep Research API

To use the deployed MCP server with OpenAI's Deep Research API:

1. Go to ChatGPT settings.
2. Navigate to the "Connectors" tab.
3. Add your MCP server URL: `http://<EXTERNAL_HOST>:<EXTERNAL_PORT>/sse/`
4. Test the connection to ensure it's working.

Once connected, you can use the Deep Research feature in ChatGPT to search and retrieve documents from your MCP server.
