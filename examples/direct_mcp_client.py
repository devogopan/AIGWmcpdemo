"""
Example: Direct MCP client (no AI Gateway)

Connects directly to the MCP server's stdio transport and calls each
demo tool once to show what the raw MCP protocol looks like.

Usage
-----
  cd mcp_server
  pip install -r requirements.txt
  cd ..
  python examples/direct_mcp_client.py
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SERVER_SCRIPT = Path(__file__).parent.parent / "mcp_server" / "server.py"


async def main() -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_SCRIPT)],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # List available tools
            tools_result = await session.list_tools()
            print("=== Available MCP Tools ===")
            for tool in tools_result.tools:
                print(f"  • {tool.name}: {tool.description}")
            print()

            # --- Calculator ---
            print("--- calculator: 6 × 7 ---")
            result = await session.call_tool(
                "calculator",
                {"operation": "multiply", "a": 6, "b": 7},
            )
            print(result.content[0].text)
            print()

            # --- Current time ---
            print("--- get_current_time ---")
            result = await session.call_tool("get_current_time", {})
            print(result.content[0].text)
            print()

            # --- Unit converter ---
            print("--- unit_converter: 100 km → miles ---")
            result = await session.call_tool(
                "unit_converter",
                {"value": 100, "from_unit": "km", "to_unit": "miles"},
            )
            print(result.content[0].text)
            print()

            # --- Text analyzer ---
            print("--- text_analyzer ---")
            result = await session.call_tool(
                "text_analyzer",
                {"text": "The quick brown fox jumps over the lazy dog. Hello world!"},
            )
            print(result.content[0].text)
            print()

            # --- JSON formatter ---
            print("--- json_formatter ---")
            result = await session.call_tool(
                "json_formatter",
                {"json_string": '{"name":"Alice","age":30,"active":true}'},
            )
            print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
