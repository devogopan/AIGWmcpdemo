FROM python:3.12-slim

WORKDIR /app

# Install mcp-proxy to wrap the stdio server with an SSE transport
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt mcp-proxy

COPY server.py .

# Health check endpoint is provided by mcp-proxy
EXPOSE 8000

# mcp-proxy wraps the stdio server and exposes SSE on $MCP_PORT
CMD ["sh", "-c", "mcp-proxy --port ${MCP_PORT:-8000} -- python server.py"]
