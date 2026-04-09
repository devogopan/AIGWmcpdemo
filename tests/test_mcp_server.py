"""
Unit tests for the MCP server tool implementations.

Run with:
  pip install pytest
  pytest tests/
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make the mcp_server package importable
sys.path.insert(0, str(Path(__file__).parent.parent / "mcp_server"))

import pytest

# Import private helpers directly so we can unit-test them without spinning up
# the full MCP server runtime.
from server import (
    _calculator,
    _get_current_time,
    _json_formatter,
    _text_analyzer,
    _unit_converter,
)


# ---------------------------------------------------------------------------
# calculator
# ---------------------------------------------------------------------------


class TestCalculator:
    def test_add(self):
        r = _calculator("add", 3, 4)
        assert r["result"] == 7

    def test_subtract(self):
        r = _calculator("subtract", 10, 3)
        assert r["result"] == 7

    def test_multiply(self):
        r = _calculator("multiply", 6, 7)
        assert r["result"] == 42

    def test_divide(self):
        r = _calculator("divide", 10, 4)
        assert r["result"] == pytest.approx(2.5)

    def test_divide_by_zero(self):
        r = _calculator("divide", 5, 0)
        assert "error" in r
        assert "zero" in r["error"].lower()

    def test_unknown_operation(self):
        r = _calculator("modulo", 10, 3)
        assert "error" in r

    def test_expression_field(self):
        r = _calculator("add", 1, 2)
        assert "expression" in r


# ---------------------------------------------------------------------------
# get_current_time
# ---------------------------------------------------------------------------


class TestGetCurrentTime:
    def test_returns_utc_key(self):
        r = _get_current_time()
        assert "utc" in r

    def test_returns_readable_key(self):
        r = _get_current_time()
        assert "readable" in r

    def test_utc_is_iso_format(self):
        r = _get_current_time()
        from datetime import datetime, timezone

        # Should parse without error
        dt = datetime.fromisoformat(r["utc"])
        assert dt.tzinfo is not None


# ---------------------------------------------------------------------------
# unit_converter
# ---------------------------------------------------------------------------


class TestUnitConverter:
    def test_km_to_miles(self):
        r = _unit_converter(100, "km", "miles")
        assert r["result"] == pytest.approx(62.1371, rel=1e-3)

    def test_miles_to_km(self):
        r = _unit_converter(1, "miles", "km")
        assert r["result"] == pytest.approx(1.60934, rel=1e-3)

    def test_kg_to_lbs(self):
        r = _unit_converter(1, "kg", "lbs")
        assert r["result"] == pytest.approx(2.20462, rel=1e-3)

    def test_celsius_to_fahrenheit(self):
        r = _unit_converter(0, "celsius", "fahrenheit")
        assert r["result"] == pytest.approx(32.0)

    def test_fahrenheit_to_celsius(self):
        r = _unit_converter(212, "fahrenheit", "celsius")
        assert r["result"] == pytest.approx(100.0)

    def test_liters_to_gallons(self):
        r = _unit_converter(1, "liters", "gallons")
        assert r["result"] == pytest.approx(0.264172, rel=1e-3)

    def test_unsupported_conversion(self):
        r = _unit_converter(1, "meters", "feet")
        assert "error" in r

    def test_case_insensitive(self):
        r = _unit_converter(100, "KM", "MILES")
        assert r["result"] == pytest.approx(62.1371, rel=1e-3)


# ---------------------------------------------------------------------------
# text_analyzer
# ---------------------------------------------------------------------------


class TestTextAnalyzer:
    def test_word_count(self):
        r = _text_analyzer("hello world foo")
        assert r["words"] == 3

    def test_character_count(self):
        r = _text_analyzer("abc")
        assert r["characters"] == 3

    def test_characters_no_spaces(self):
        r = _text_analyzer("a b c")
        assert r["characters_no_spaces"] == 3

    def test_sentence_count(self):
        r = _text_analyzer("Hello. World. Foo.")
        assert r["sentences"] == 3

    def test_empty_text(self):
        r = _text_analyzer("")
        assert r["words"] == 0
        assert r["average_word_length"] == 0

    def test_average_word_length(self):
        # "ab cd" → avg = (2+2)/2 = 2.0
        r = _text_analyzer("ab cd")
        assert r["average_word_length"] == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# json_formatter
# ---------------------------------------------------------------------------


class TestJsonFormatter:
    def test_valid_json(self):
        r = _json_formatter('{"a": 1}')
        assert r["valid"] is True
        assert "formatted" in r

    def test_pretty_printed(self):
        r = _json_formatter('{"a":1}', indent=4)
        parsed = json.loads(r["formatted"])
        assert parsed == {"a": 1}
        assert "    " in r["formatted"]  # 4-space indentation

    def test_invalid_json(self):
        r = _json_formatter("{not valid json}")
        assert r["valid"] is False
        assert "error" in r

    def test_array_input(self):
        r = _json_formatter("[1, 2, 3]")
        assert r["valid"] is True
        assert json.loads(r["formatted"]) == [1, 2, 3]

    def test_unicode_preserved(self):
        r = _json_formatter('{"emoji": "🎉"}')
        assert r["valid"] is True
        assert "🎉" in r["formatted"]
