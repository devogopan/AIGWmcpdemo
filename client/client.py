"""
AIGW MCP Demo – Client

Demonstrates how an application talks to an AI model through the
AI Gateway, which automatically injects MCP tools from the demo
MCP server.

Usage
-----
  # Set your credentials
  export OPENAI_API_KEY=sk-...
  export AIGW_JWT_SECRET=my-demo-secret

  # Optional: override the AIGW base URL (defaults to localhost)
  export AIGW_BASE_URL=http://localhost:4141

  # Run the interactive demo
  python client.py

  # Or run with a single prompt
  python client.py --prompt "What is 42 multiplied by 7?"
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Configuration (from environment variables)
# ---------------------------------------------------------------------------
AIGW_BASE_URL = os.environ.get("AIGW_BASE_URL", "http://localhost:4141")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
AIGW_JWT = os.environ.get("AIGW_JWT", "")  # pre-signed JWT for the gateway

# When running without a gateway (direct OpenAI / Anthropic access)
DIRECT_OPENAI_URL = "https://api.openai.com/v1"
DIRECT_ANTHROPIC_URL = "https://api.anthropic.com/v1"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_headers(provider: str = "openai") -> dict[str, str]:
    """Return HTTP headers for the chosen provider/gateway."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if AIGW_JWT:
        headers["Authorization"] = f"Bearer {AIGW_JWT}"
    elif provider == "openai" and OPENAI_API_KEY:
        headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"
    elif provider == "anthropic" and ANTHROPIC_API_KEY:
        headers["x-api-key"] = ANTHROPIC_API_KEY
        headers["anthropic-version"] = "2023-06-01"
    return headers


def _chat_openai(
    messages: list[dict[str, Any]],
    *,
    model: str = "gpt-4o",
    base_url: str | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Send a chat-completion request (OpenAI-compatible API)."""
    url = f"{base_url or AIGW_BASE_URL}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=_build_headers("openai"), json=payload)
        response.raise_for_status()
        return response.json()


def _chat_anthropic(
    messages: list[dict[str, Any]],
    *,
    model: str = "claude-3-5-sonnet-20241022",
    base_url: str | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Send a messages request (Anthropic API)."""
    url = f"{base_url or AIGW_BASE_URL}/anthropic/v1/messages"
    payload = {
        "model": model,
        "max_tokens": 1024,
        "messages": messages,
    }
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=_build_headers("anthropic"), json=payload)
        response.raise_for_status()
        return response.json()


def list_mcp_tools(base_url: str | None = None, timeout: float = 10.0) -> list[dict[str, Any]]:
    """Retrieve the list of MCP tools exposed by the gateway."""
    url = f"{base_url or AIGW_BASE_URL}/mcp/tools"
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("tools", data) if isinstance(data, dict) else data


# ---------------------------------------------------------------------------
# Interactive demo
# ---------------------------------------------------------------------------

DEMO_PROMPTS = [
    "What is 1234 multiplied by 5678?",
    "Convert 100 kilometers to miles.",
    "What is the current UTC time?",
    "Analyze the following text: 'The quick brown fox jumps over the lazy dog. "
    "It was a bright, sunny day in the forest.'",
    'Format this JSON: {"name":"Alice","age":30,"hobbies":["reading","coding"]}',
]


def print_separator(char: str = "─", width: int = 60) -> None:
    print(char * width)


def run_demo(provider: str = "openai") -> None:
    """Run through the demo prompts and print results."""
    print_separator("═")
    print("  AIGW MCP Demo Client")
    print(f"  Gateway URL : {AIGW_BASE_URL}")
    print(f"  Provider    : {provider}")
    print_separator("═")

    # Try to list available tools via the gateway
    print("\n🔧  Fetching available MCP tools …")
    try:
        tools = list_mcp_tools()
        for tool in tools:
            name = tool.get("name", "?")
            desc = tool.get("description", "")
            print(f"  • {name}: {desc}")
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠  Could not reach gateway tool endpoint: {exc}")
        print("  (Continuing with demo prompts anyway)")

    print()
    print_separator()

    for i, prompt in enumerate(DEMO_PROMPTS, 1):
        print(f"\n[{i}/{len(DEMO_PROMPTS)}] User: {prompt}")
        messages = [{"role": "user", "content": prompt}]

        try:
            if provider == "openai":
                response = _chat_openai(messages)
                reply = response["choices"][0]["message"]["content"]
            else:
                response = _chat_anthropic(messages)
                reply = response["content"][0]["text"]

            print(f"Assistant: {reply}")
        except httpx.HTTPStatusError as exc:
            print(f"  ✗ HTTP {exc.response.status_code}: {exc.response.text[:200]}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ Error: {exc}")

        print_separator()

    print("\n✓ Demo complete.")


def run_single_prompt(prompt: str, provider: str = "openai") -> None:
    """Send a single prompt to the gateway and print the response."""
    messages = [{"role": "user", "content": prompt}]
    print(f"User: {prompt}\n")

    if provider == "openai":
        response = _chat_openai(messages)
        reply = response["choices"][0]["message"]["content"]
    else:
        response = _chat_anthropic(messages)
        reply = response["content"][0]["text"]

    print(f"Assistant: {reply}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIGW MCP Demo Client")
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Single prompt to send. If omitted, runs the full demo.",
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["openai", "anthropic"],
        default="openai",
        help="LLM provider to use (default: openai).",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help=f"Override gateway base URL (default: {AIGW_BASE_URL}).",
    )
    args = parser.parse_args()

    if args.base_url:
        AIGW_BASE_URL = args.base_url  # type: ignore[assignment]

    if args.prompt:
        run_single_prompt(args.prompt, provider=args.provider)
    else:
        run_demo(provider=args.provider)
