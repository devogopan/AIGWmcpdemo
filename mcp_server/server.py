"""
AIGW MCP Demo - MCP Server

This MCP server exposes a set of tools that an AI model can call
through the AI Gateway (AIGW). The tools demonstrate common patterns
used in enterprise AI integrations.
"""

import json
from datetime import datetime, timezone
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)

app = Server("aigw-mcp-demo-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
            Tool(
                name="calculator",
                description=(
                    "Perform basic arithmetic operations: add, subtract, multiply, divide."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["add", "subtract", "multiply", "divide"],
                            "description": "The arithmetic operation to perform.",
                        },
                        "a": {
                            "type": "number",
                            "description": "First operand.",
                        },
                        "b": {
                            "type": "number",
                            "description": "Second operand.",
                        },
                    },
                    "required": ["operation", "a", "b"],
                },
            ),
            Tool(
                name="get_current_time",
                description="Return the current UTC date and time.",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="unit_converter",
                description="Convert between common units of measurement.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "value": {
                            "type": "number",
                            "description": "The value to convert.",
                        },
                        "from_unit": {
                            "type": "string",
                            "description": (
                                "Source unit. Supported: km, miles, kg, lbs, "
                                "celsius, fahrenheit, liters, gallons."
                            ),
                        },
                        "to_unit": {
                            "type": "string",
                            "description": "Target unit (same set as from_unit).",
                        },
                    },
                    "required": ["value", "from_unit", "to_unit"],
                },
            ),
            Tool(
                name="text_analyzer",
                description=(
                    "Analyze a piece of text and return statistics such as "
                    "word count, character count, and sentence count."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The text to analyze.",
                        },
                    },
                    "required": ["text"],
                },
            ),
            Tool(
                name="json_formatter",
                description="Validate and pretty-print a JSON string.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "json_string": {
                            "type": "string",
                            "description": "The raw JSON string to format.",
                        },
                        "indent": {
                            "type": "integer",
                            "description": "Number of spaces for indentation (default: 2).",
                            "default": 2,
                        },
                    },
                    "required": ["json_string"],
                },
            ),
        ]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _calculator(operation: str, a: float, b: float) -> dict[str, Any]:
    ops = {
        "add": a + b,
        "subtract": a - b,
        "multiply": a * b,
    }
    if operation in ops:
        return {"result": ops[operation], "expression": f"{a} {operation} {b}"}
    if operation == "divide":
        if b == 0:
            return {"error": "Division by zero is not allowed."}
        return {"result": a / b, "expression": f"{a} / {b}"}
    return {"error": f"Unknown operation: {operation}"}


def _get_current_time() -> dict[str, str]:
    now = datetime.now(timezone.utc)
    return {
        "utc": now.isoformat(),
        "readable": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }


_CONVERSIONS: dict[tuple[str, str], float] = {
    # distance
    ("km", "miles"): 0.621371,
    ("miles", "km"): 1.60934,
    # weight
    ("kg", "lbs"): 2.20462,
    ("lbs", "kg"): 0.453592,
    # volume
    ("liters", "gallons"): 0.264172,
    ("gallons", "liters"): 3.78541,
}


def _unit_converter(value: float, from_unit: str, to_unit: str) -> dict[str, Any]:
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()

    # Temperature requires special handling
    if from_unit == "celsius" and to_unit == "fahrenheit":
        result = value * 9 / 5 + 32
        return {"result": result, "from": f"{value} °C", "to": f"{result:.4f} °F"}
    if from_unit == "fahrenheit" and to_unit == "celsius":
        result = (value - 32) * 5 / 9
        return {"result": result, "from": f"{value} °F", "to": f"{result:.4f} °C"}

    key = (from_unit, to_unit)
    if key not in _CONVERSIONS:
        return {
            "error": (
                f"Unsupported conversion: {from_unit} → {to_unit}. "
                "Supported pairs: km↔miles, kg↔lbs, celsius↔fahrenheit, liters↔gallons."
            )
        }
    factor = _CONVERSIONS[key]
    result = value * factor
    return {"result": result, "from": f"{value} {from_unit}", "to": f"{result:.4f} {to_unit}"}


def _text_analyzer(text: str) -> dict[str, Any]:
    words = text.split()
    sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    return {
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "")),
        "words": len(words),
        "sentences": len(sentences),
        "paragraphs": len([p for p in text.split("\n\n") if p.strip()]),
        "average_word_length": round(
            sum(len(w) for w in words) / len(words), 2
        ) if words else 0,
    }


def _json_formatter(json_string: str, indent: int = 2) -> dict[str, Any]:
    try:
        parsed = json.loads(json_string)
        formatted = json.dumps(parsed, indent=indent, ensure_ascii=False)
        return {"valid": True, "formatted": formatted}
    except json.JSONDecodeError as exc:
        return {"valid": False, "error": str(exc)}


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    args = arguments or {}

    if name == "calculator":
        result = _calculator(
            operation=args["operation"],
            a=args["a"],
            b=args["b"],
        )
    elif name == "get_current_time":
        result = _get_current_time()
    elif name == "unit_converter":
        result = _unit_converter(
            value=args["value"],
            from_unit=args["from_unit"],
            to_unit=args["to_unit"],
        )
    elif name == "text_analyzer":
        result = _text_analyzer(text=args["text"])
    elif name == "json_formatter":
        result = _json_formatter(
            json_string=args["json_string"],
            indent=args.get("indent", 2),
        )
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [
        TextContent(
            type="text",
            text=json.dumps(result, indent=2, ensure_ascii=False),
        )
    ]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
