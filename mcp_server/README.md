# AIGW MCP Demo – Server

A lightweight [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that
exposes demo tools. The server is designed to be consumed through an
**AI Gateway (AIGW)** so that rate-limiting, authentication, and policy
enforcement happen centrally rather than inside each tool.

## Provided Tools

| Tool | Description |
|------|-------------|
| `calculator` | Basic arithmetic (add / subtract / multiply / divide) |
| `get_current_time` | Return the current UTC date and time |
| `unit_converter` | Convert between km↔miles, kg↔lbs, °C↔°F, liters↔gallons |
| `text_analyzer` | Word / character / sentence / paragraph counts |
| `json_formatter` | Validate and pretty-print a JSON string |

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server (stdio transport – suitable for direct MCP client connections)
python server.py
```

The server speaks the MCP **stdio transport** protocol and can be
proxied by any MCP-compatible AI gateway.

## Running with SSE Transport (HTTP)

To expose the server over HTTP (required for remote AIGW connections) use a
transport adapter such as [`mcp-proxy`](https://github.com/sparfenyuk/mcp-proxy):

```bash
pip install mcp-proxy
mcp-proxy --port 8000 -- python server.py
```

The MCP endpoint will be available at `http://localhost:8000/sse`.
