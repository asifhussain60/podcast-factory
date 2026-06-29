#!/usr/bin/env python3
"""gemini_chat.py — multi-turn CLI chat client for Gemini.

Maintains full conversation history, supports a custom system instruction
(persona / Gem), and injects knowledge files into the first user turn.

Usage:
    python3 scripts/gemini_chat.py [--system FILE_OR_TEXT] [FILE ...]

Auth:
    Set GEMINI_API_KEY in the environment (or in a .env file at the repo root).

Knowledge files:
    Positional arguments are paths to knowledge files.
    < 20 MB  -> read as text, injected inline in the first user turn.
    >= 20 MB -> uploaded via the Files API; URI embedded in the first user turn.

System instruction:
    --system can be either a file path (read as text) or a literal text string.
    Alternatively set GEMINI_SYSTEM_INSTRUCTION in the environment.
    If neither is provided, the model runs with no system instruction.
"""
from __future__ import annotations

import argparse
import mimetypes
import os
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_FILE_SIZE_THRESHOLD = 20 * 1024 * 1024  # 20 MB in bytes
# gemini-2.0-flash (unversioned) is retired (404). Use the pipeline-standard
# versioned alias. Override with GEMINI_MODEL env var if needed.
_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# ── env / dotenv ──────────────────────────────────────────────────────────────

def _load_env() -> None:
    """Load .env from the repo root if present (python-dotenv, best-effort)."""
    env_path = _REPO / ".env"
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            pass  # python-dotenv optional; env var must be set another way


def _get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        sys.exit(
            "ERROR: GEMINI_API_KEY is not set.\n"
            "  Set it in the environment, or add it to a .env file at the repo root.\n"
            "  See docs/gemini-chat.md for setup instructions."
        )
    return key


# ── argument parsing ──────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Multi-turn CLI chat with Gemini. Type 'exit' to quit.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--system",
        metavar="FILE_OR_TEXT",
        default=None,
        help=(
            "System instruction for the model. Either a path to a text file "
            "or a literal string. Overrides GEMINI_SYSTEM_INSTRUCTION env var."
        ),
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help=(
            "Optional knowledge files to inject into the first user turn. "
            "Files < 20 MB are read inline; larger files are uploaded via the Files API."
        ),
    )
    return parser.parse_args()


# ── system instruction ────────────────────────────────────────────────────────

def _resolve_system_instruction(raw: str | None) -> str | None:
    """Return the system instruction text, or None if not configured."""
    if raw is None:
        raw = os.environ.get("GEMINI_SYSTEM_INSTRUCTION", "").strip() or None
    if raw is None:
        return None
    # If it looks like a file path and the file exists, read it.
    candidate = Path(raw)
    if candidate.exists() and candidate.is_file():
        return candidate.read_text(encoding="utf-8").strip()
    return raw.strip() or None


# ── knowledge file handling ───────────────────────────────────────────────────

def _mime_for(path: Path) -> str:
    """Best-effort MIME type for a file path."""
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "text/plain"


def _load_knowledge_files(
    paths: list[str],
    client,
    types,
) -> list:
    """Return a list of Part objects ready to include in a user turn.

    Files < 20 MB are read and injected inline as text parts (or bytes parts
    for non-text MIME types). Files >= 20 MB are uploaded via the Files API
    and referenced by URI.
    """
    parts = []
    for raw_path in paths:
        p = Path(raw_path).expanduser().resolve()
        if not p.exists():
            print(f"  [warning] knowledge file not found, skipping: {p}", file=sys.stderr)
            continue
        size = p.stat().st_size
        mime = _mime_for(p)
        if size >= _FILE_SIZE_THRESHOLD:
            print(f"  Uploading {p.name} ({size // (1024*1024)} MB) via Files API ...", end=" ", flush=True)
            try:
                uploaded = client.files.upload(file=p, config={"mime_type": mime})
                parts.append(types.Part.from_uri(file_uri=uploaded.uri, mime_type=mime))
                print("done")
            except Exception as e:
                print(f"\n  [warning] Files API upload failed for {p.name}: {e}", file=sys.stderr)
        else:
            # Inline injection: read as UTF-8 text for text/* types; bytes otherwise.
            if mime.startswith("text/") or mime in ("application/json", "application/yaml"):
                try:
                    content = p.read_text(encoding="utf-8", errors="replace")
                    parts.append(types.Part.from_text(text=f"[Knowledge file: {p.name}]\n\n{content}"))
                    print(f"  Loaded {p.name} inline ({len(content):,} chars)")
                except Exception as e:
                    print(f"  [warning] could not read {p.name}: {e}", file=sys.stderr)
            else:
                try:
                    data = p.read_bytes()
                    parts.append(types.Part.from_bytes(data=data, mime_type=mime))
                    print(f"  Loaded {p.name} inline ({size:,} bytes, {mime})")
                except Exception as e:
                    print(f"  [warning] could not read {p.name}: {e}", file=sys.stderr)
    return parts


# ── chat loop ─────────────────────────────────────────────────────────────────

def _run(args: argparse.Namespace, api_key: str) -> None:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("ERROR: google-genai is not installed.\n  Run: pip3 install google-genai")

    client = genai.Client(api_key=api_key)

    # Build system instruction
    system_text = _resolve_system_instruction(args.system)

    # Build chat config
    config = types.GenerateContentConfig(
        system_instruction=system_text,
    )

    # Create the chat session (history is managed internally by the SDK).
    chat = client.chats.create(model=_MODEL, config=config)

    print(f"\nGemini chat — model: {_MODEL}")
    if system_text:
        preview = system_text[:80].replace("\n", " ")
        print(f"System: {preview}{'...' if len(system_text) > 80 else ''}")
    if args.files:
        print("Loading knowledge files...")

    # Prepare knowledge file parts (if any).
    knowledge_parts = _load_knowledge_files(args.files or [], client, types)

    print('\nType your message. Type "exit" to quit.\n')

    first_turn = True
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if user_input.lower() == "exit":
            print("Exiting.")
            break
        if not user_input:
            continue

        # On the first turn, prepend knowledge file parts to the message.
        if first_turn and knowledge_parts:
            message = knowledge_parts + [types.Part.from_text(text=user_input)]
            first_turn = False
        else:
            message = user_input
            first_turn = False

        try:
            response = chat.send_message(message)
        except Exception as e:
            _handle_api_error(e)
            continue

        print(f"\nGemini: {response.text}\n")


def _handle_api_error(exc: Exception) -> None:
    """Print a human-readable error, never a raw traceback."""
    name = type(exc).__name__
    msg = str(exc)
    # google-genai raises google.api_core.exceptions types; surface the message.
    if "API_KEY" in msg.upper() or "INVALID_ARGUMENT" in msg.upper():
        print(f"\nError: authentication or request error — {msg}\n", file=sys.stderr)
    elif "RESOURCE_EXHAUSTED" in msg.upper() or "429" in msg:
        print("\nError: rate limit exceeded. Wait a moment and try again.\n", file=sys.stderr)
    elif "DEADLINE_EXCEEDED" in msg.upper() or "timeout" in msg.lower():
        print("\nError: request timed out. Try a shorter message.\n", file=sys.stderr)
    elif "SAFETY" in msg.upper():
        print("\nError: response blocked by safety filters.\n", file=sys.stderr)
    else:
        print(f"\nError ({name}): {msg}\n", file=sys.stderr)


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    _load_env()
    args = _parse_args()
    api_key = _get_api_key()
    _run(args, api_key)


if __name__ == "__main__":
    main()
