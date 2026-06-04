"""source_library_server.py — Wave J (J0): dual-interface source library server.

Two transports, one codebase:

    --stdio     MCP stdio mode (JSON-RPC 2.0, Content-Length framing).
                Registered in .mcp.json for Claude Code, Copilot, and
                Claude Desktop to use as a tool server.

    (default)   HTTP mode (FastAPI on port 4390).
                Used by the Astro editor's QuranPopover and TermPopover
                components.  Browser cannot call stdio; HTTP is required.

Both transports delegate to the six query functions in
source_library_queries.py — zero duplication.

Usage:
    python3 scripts/podcast/source_library_server.py            # HTTP :4390
    python3 scripts/podcast/source_library_server.py --stdio    # MCP stdio

To register in .mcp.json (one-time):
    python3 scripts/podcast/source_library_server.py --register
"""
from __future__ import annotations

import argparse
import json
import sys
import io
from pathlib import Path
from typing import Any

# ── path bootstrap ────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.podcast.source_library_queries import (
    quran_lookup,
    quran_theme_search,
    word_etymology,
    topic_search,
    topic_get,
    session_style_fetch,
)

# ── tool manifest (shared by both transports) ─────────────────────────────────

TOOLS: list[dict[str, Any]] = [
    {
        "name": "quran_lookup",
        "description": "Return a single Quran verse by surah and ayat numbers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "surah": {"type": "integer", "description": "Surah (chapter) number 1–114"},
                "ayat":  {"type": "integer", "description": "Ayat (verse) number"},
            },
            "required": ["surah", "ayat"],
        },
    },
    {
        "name": "quran_theme_search",
        "description": "Search Quran verses by keyword across Pickthall and Asad translations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "limit":   {"type": "integer", "default": 10},
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "word_etymology",
        "description": "Return the Arabic root and all derivatives for a term.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "term": {"type": "string", "description": "Arabic term or transliteration"},
            },
            "required": ["term"],
        },
    },
    {
        "name": "topic_search",
        "description": "Search KASHKOLE topics by keyword (name search).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "limit":   {"type": "integer", "default": 10},
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "topic_get",
        "description": "Return a full topic record with linked Quran ayats and glossary terms.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic_id": {"type": "integer"},
            },
            "required": ["topic_id"],
        },
    },
    {
        "name": "session_style_fetch",
        "description": "Return style-reference passages from the teaching sessions corpus.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "theme":    {"type": "string", "description": "Theme or keyword to search"},
                "group_id": {"type": ["integer", "null"], "default": None},
                "limit":    {"type": "integer", "default": 4},
            },
            "required": ["theme"],
        },
    },
]


def _dispatch(name: str, args: dict[str, Any]) -> Any:
    """Call the named query function with validated args."""
    if name == "quran_lookup":
        return quran_lookup(int(args["surah"]), int(args["ayat"]))
    if name == "quran_theme_search":
        return quran_theme_search(args["keyword"], int(args.get("limit", 10)))
    if name == "word_etymology":
        return word_etymology(args["term"])
    if name == "topic_search":
        return topic_search(args["keyword"], int(args.get("limit", 10)))
    if name == "topic_get":
        return topic_get(int(args["topic_id"]))
    if name == "session_style_fetch":
        gid = args.get("group_id")
        return session_style_fetch(
            args["theme"],
            int(gid) if gid is not None else None,
            int(args.get("limit", 4)),
        )
    raise ValueError(f"Unknown tool: {name!r}")


# ── MCP stdio server ──────────────────────────────────────────────────────────

def _mcp_send(msg: dict[str, Any]) -> None:
    body = json.dumps(msg, ensure_ascii=False)
    header = f"Content-Length: {len(body.encode('utf-8'))}\r\n\r\n"
    sys.stdout.write(header + body)
    sys.stdout.flush()


def _mcp_ok(req_id: Any, result: Any) -> None:
    _mcp_send({"jsonrpc": "2.0", "id": req_id, "result": result})


def _mcp_err(req_id: Any, code: int, message: str) -> None:
    _mcp_send({"jsonrpc": "2.0", "id": req_id,
               "error": {"code": code, "message": message}})


def run_stdio() -> None:
    """Serve MCP JSON-RPC 2.0 over stdin/stdout (LSP Content-Length framing)."""
    raw_stdin = sys.stdin.buffer
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    while True:
        # Read headers until blank line
        headers: dict[str, str] = {}
        while True:
            line = raw_stdin.readline()
            if not line:
                return  # EOF
            decoded = line.decode("utf-8").rstrip("\r\n")
            if decoded == "":
                break
            if ":" in decoded:
                k, _, v = decoded.partition(":")
                headers[k.strip().lower()] = v.strip()

        length = int(headers.get("content-length", 0))
        if length == 0:
            continue

        body = raw_stdin.read(length).decode("utf-8")
        try:
            msg = json.loads(body)
        except json.JSONDecodeError:
            continue

        method = msg.get("method", "")
        req_id = msg.get("id")

        if method == "initialize":
            _mcp_ok(req_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "source-library", "version": "1.0.0"},
            })

        elif method == "initialized":
            pass  # notification, no response

        elif method == "tools/list":
            _mcp_ok(req_id, {"tools": TOOLS})

        elif method == "tools/call":
            params = msg.get("params", {})
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            try:
                result = _dispatch(tool_name, tool_args)
                _mcp_ok(req_id, {
                    "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
                    "isError": False,
                })
            except Exception as exc:  # noqa: BLE001
                _mcp_ok(req_id, {
                    "content": [{"type": "text", "text": str(exc)}],
                    "isError": True,
                })

        elif req_id is not None:
            _mcp_err(req_id, -32601, f"Method not found: {method!r}")


# ── HTTP server (FastAPI) ─────────────────────────────────────────────────────

HTTP_PORT = 4390


def run_http(port: int = HTTP_PORT) -> None:
    """Serve the six query functions over HTTP on the given port."""
    try:
        from fastapi import FastAPI, Query as Q
        from fastapi.responses import JSONResponse
        import uvicorn
    except ImportError as exc:
        sys.exit(f"HTTP mode requires fastapi and uvicorn: {exc}")

    app = FastAPI(title="Source Library", version="1.0.0")

    @app.get("/quran/verse")
    def quran_verse(surah: int = Q(...), ayat: int = Q(...)):
        return JSONResponse(_dispatch("quran_lookup", {"surah": surah, "ayat": ayat}))

    @app.get("/quran/theme")
    def quran_theme(q: str = Q(...), limit: int = Q(10)):
        return _dispatch("quran_theme_search", {"keyword": q, "limit": limit})

    @app.get("/term/define")
    def term_define(term: str = Q(...)):
        return JSONResponse(_dispatch("word_etymology", {"term": term}))

    @app.get("/etymology")
    def etymology(term: str = Q(...)):
        return JSONResponse(_dispatch("word_etymology", {"term": term}))

    @app.get("/topic/search")
    def topic_search_route(q: str = Q(...), limit: int = Q(10)):
        return _dispatch("topic_search", {"keyword": q, "limit": limit})

    @app.get("/topic/get")
    def topic_get_route(id: int = Q(...)):
        return JSONResponse(_dispatch("topic_get", {"topic_id": id}))

    @app.get("/session/style")
    def session_style(theme: str = Q(...), group_id: int | None = Q(None), limit: int = Q(4)):
        return _dispatch("session_style_fetch", {"theme": theme, "group_id": group_id, "limit": limit})

    @app.get("/health")
    def health():
        return {"status": "ok", "server": "source-library", "version": "1.0.0"}

    print(f"Source Library HTTP server on http://localhost:{port}", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


# ── .mcp.json registration helper ─────────────────────────────────────────────

def _register_mcp() -> None:
    """Add this server to .mcp.json (idempotent)."""
    mcp_file = REPO_ROOT / ".mcp.json"
    data: dict[str, Any] = {}
    if mcp_file.exists():
        data = json.loads(mcp_file.read_text())
    servers = data.setdefault("mcpServers", {})
    if "source-library" in servers:
        print("source-library already registered in .mcp.json")
        return
    servers["source-library"] = {
        "command": sys.executable,
        "args": [str(Path(__file__).resolve()), "--stdio"],
    }
    mcp_file.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Registered source-library in {mcp_file}")


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Source Library dual-interface server")
    parser.add_argument("--stdio",    action="store_true", help="Run MCP stdio transport")
    parser.add_argument("--register", action="store_true", help="Register in .mcp.json and exit")
    parser.add_argument("--port",     type=int, default=HTTP_PORT, help="HTTP port (default 4390)")
    args = parser.parse_args()

    if args.register:
        _register_mcp()
        return

    if args.stdio:
        run_stdio()
    else:
        run_http(args.port)


if __name__ == "__main__":
    main()
