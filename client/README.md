# AIGW MCP Demo – Client

A Python CLI client that sends prompts to an LLM **through the AI Gateway**
so that MCP tools are automatically available to the model.

## Quick Start

```bash
pip install -r requirements.txt

# Via the AI Gateway (recommended)
export AIGW_BASE_URL=http://localhost:4141
export AIGW_JWT=<your-jwt-token>   # issued by your identity provider
python client.py

# Direct (no gateway – useful for local development)
export OPENAI_API_KEY=sk-...
python client.py --base-url https://api.openai.com
```

## Options

```
usage: client.py [-h] [--prompt PROMPT] [--provider {openai,anthropic}] [--base-url BASE_URL]

optional arguments:
  --prompt PROMPT              Single prompt to send. If omitted, runs the full demo.
  --provider {openai,anthropic}
                               LLM provider to use (default: openai).
  --base-url BASE_URL          Override gateway base URL.
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AIGW_BASE_URL` | Base URL of the AI Gateway (default: `http://localhost:4141`) |
| `AIGW_JWT` | Pre-signed JWT token for gateway authentication |
| `OPENAI_API_KEY` | OpenAI API key (used when calling OpenAI directly) |
| `ANTHROPIC_API_KEY` | Anthropic API key (used when calling Anthropic directly) |
