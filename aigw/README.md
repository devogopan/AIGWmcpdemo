# AIGW MCP Demo – AI Gateway Configuration

This directory contains the **AI Gateway (AIGW)** configuration that
sits between your application clients and the upstream LLM providers.
The gateway proxies calls to the [MCP server](../mcp_server/) and enforces
cross-cutting policies (authentication, rate-limiting, prompt-injection
blocking) in a single place.

## Architecture

```
Client App
    │
    │  HTTP (POST /v1/chat/completions)
    ▼
┌──────────────────────────────────┐
│         AI Gateway (AIGW)        │
│   ┌─────────────────────────┐    │
│   │  Policies               │    │
│   │  • JWT Authentication   │    │
│   │  • Rate Limiting        │    │
│   │  • Input Guard (PII /   │    │
│   │    Prompt-Injection)    │    │
│   └─────────────────────────┘    │
│   ┌─────────────────────────┐    │
│   │  MCP Tool Injection     │    │
│   │  (demo-tools server)    │    │
│   └─────────────────────────┘    │
└──────────────────────────────────┘
    │                      │
    │  LLM API             │  MCP (SSE)
    ▼                      ▼
OpenAI / Anthropic     MCP Server
```

## Configuration File

[`aigw.yaml`](./aigw.yaml) is read by the AIGW process at startup.

Key sections:

| Section | Purpose |
|---------|---------|
| `services` | Upstream LLM providers (OpenAI, Anthropic, …) |
| `mcpServers` | MCP tool servers to inject into every request |
| `listeners` | Ports / routes exposed by the gateway |
| `policies` | Authentication, rate-limiting, and guard rules |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | When using the OpenAI service | OpenAI API key |
| `ANTHROPIC_API_KEY` | When using the Anthropic service | Anthropic API key |
| `AIGW_JWT_SECRET` | Yes | HS256 secret for JWT verification |

## Running the Gateway (Docker)

```bash
# from the repository root
docker compose up aigw
```

See [`docker-compose.yml`](../docker-compose.yml) for the full setup.
