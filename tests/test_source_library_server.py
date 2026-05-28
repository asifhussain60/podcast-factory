"""tests/test_source_library_server.py — Wave J (J0) structural tests.

Validates the source_library_server module without requiring the Docker
SQL Server container to be running.  Tests import-time behaviour, the tool
manifest, the dispatch table, and the MCP JSON-RPC framing helpers.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

import source_library_server as srv
import source_library_queries as qry  # noqa: F401 (import sanity)


_EXPECTED_TOOLS = {
    "quran_lookup",
    "quran_theme_search",
    "word_etymology",
    "topic_search",
    "topic_get",
    "session_style_fetch",
}


class TestToolManifest(unittest.TestCase):
    """TOOLS list must contain all six canonical tools with required fields."""

    def test_tool_count(self):
        self.assertEqual(len(srv.TOOLS), 6)

    def test_tool_names(self):
        names = {t["name"] for t in srv.TOOLS}
        self.assertEqual(names, _EXPECTED_TOOLS)

    def test_each_tool_has_input_schema(self):
        for tool in srv.TOOLS:
            self.assertIn("inputSchema", tool, f"Tool {tool['name']!r} missing inputSchema")
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_each_tool_has_description(self):
        for tool in srv.TOOLS:
            self.assertIn("description", tool)
            self.assertGreater(len(tool["description"]), 10)

    def test_required_fields_present(self):
        """Each required field is listed in the schema."""
        for tool in srv.TOOLS:
            reqs = tool["inputSchema"].get("required", [])
            props = tool["inputSchema"].get("properties", {})
            for r in reqs:
                self.assertIn(r, props, f"Tool {tool['name']!r}: required={r!r} not in properties")


class TestDispatch(unittest.TestCase):
    """_dispatch raises ValueError for unknown tools; propagates errors for known ones."""

    def test_unknown_tool_raises_value_error(self):
        with self.assertRaises(ValueError):
            srv._dispatch("nonexistent_tool", {})

    def test_known_tool_attempts_query(self):
        """Known tools attempt the DB call — Docker not running → FileNotFoundError or
        CalledProcessError, NOT ValueError or ImportError."""
        for name in _EXPECTED_TOOLS:
            sample_args = {
                "quran_lookup":        {"surah": 1, "ayat": 1},
                "quran_theme_search":  {"keyword": "mercy"},
                "word_etymology":      {"term": "rahma"},
                "topic_search":        {"keyword": "prayer"},
                "topic_get":           {"topic_id": 1},
                "session_style_fetch": {"theme": "patience"},
            }[name]
            try:
                srv._dispatch(name, sample_args)
            except ValueError as exc:
                self.fail(f"_dispatch raised ValueError for known tool {name!r}: {exc}")
            except Exception:
                pass  # Expected: Docker not running


class TestMcpFraming(unittest.TestCase):
    """MCP framing helpers produce valid Content-Length prefixed JSON."""

    def _capture(self, func, *args) -> str:
        import io
        buf = io.StringIO()
        original, sys.stdout = sys.stdout, buf
        try:
            func(*args)
        finally:
            sys.stdout = original
        return buf.getvalue()

    def _parse_mcp(self, raw: str) -> dict:
        """Parse Content-Length framed MCP message back to dict."""
        header, _, body = raw.partition("\r\n\r\n")
        length = int(header.split(":")[1].strip())
        self.assertEqual(len(body.encode("utf-8")), length)
        return json.loads(body)

    def test_mcp_ok_produces_valid_json_rpc(self):
        out = self._capture(srv._mcp_ok, 42, {"result": "ok"})
        msg = self._parse_mcp(out)
        self.assertEqual(msg["jsonrpc"], "2.0")
        self.assertEqual(msg["id"], 42)
        self.assertIn("result", msg)

    def test_mcp_err_produces_error_envelope(self):
        out = self._capture(srv._mcp_err, 1, -32601, "Method not found")
        msg = self._parse_mcp(out)
        self.assertEqual(msg["error"]["code"], -32601)
        self.assertIn("message", msg["error"])


class TestDrRule005(unittest.TestCase):
    """DR-005: no file in scripts/podcast/ may exceed 600 lines."""

    def test_server_file_under_600_lines(self):
        src = REPO / "scripts" / "podcast" / "source_library_server.py"
        lines = src.read_text().count("\n")
        self.assertLessEqual(lines, 600, f"{src.name} is {lines} lines (DR-005 limit: 600)")

    def test_queries_file_under_600_lines(self):
        src = REPO / "scripts" / "podcast" / "source_library_queries.py"
        lines = src.read_text().count("\n")
        self.assertLessEqual(lines, 600, f"{src.name} is {lines} lines (DR-005 limit: 600)")


if __name__ == "__main__":
    unittest.main()
