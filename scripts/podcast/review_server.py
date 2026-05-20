#!/usr/bin/env python3
"""FastAPI backend for the Operator Review Studio (P25.1).

Runs on localhost:8766. Sibling to the planned P8 dashboard at :8765.
Speaks JSON over HTTP; SSE for the resume-log stream.

Endpoints (REST):
  GET  /api/books                              — list books across worktree roots
  GET  /api/books/{slug}                       — single book metadata + state
  GET  /api/books/{slug}/transcript            — refined-english.md text + page index
  GET  /api/books/{slug}/review                — parsed operator-review.md struct
  PUT  /api/books/{slug}/review                — write struct → markdown (atomic)
  GET  /api/books/{slug}/mtime                 — operator-review.md mtime (for external-edit detection)
  POST /api/books/{slug}/approve               — write [x] approve + git commit + fire resume
  GET  /api/books/{slug}/resume-log            — SSE stream of subprocess stdout
  DELETE /api/books/{slug}/resume-log          — kill resume subprocess

AI endpoints (P25.7):
  POST /api/books/{slug}/ai/{feature}          — dispatch to _review_ai.run_feature
  GET  /api/books/{slug}/ai/budget             — remaining budget for this book

Configuration:
  --repo-root <path>                           — single-worktree mode (default)
  --config ~/.journal-worktrees.yaml           — multi-worktree mode
  --port 8766                                  — bind port (default 8766)

NO new API keys. All AI calls go through `claude -p` subprocess, which uses
the operator's existing Claude CLI auth (identical to orchestrate_book.py).

Boundary: every write path validates the resolved path lives under a
configured worktree root. Refuses otherwise.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

# Ensure sibling imports work
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

try:
    from fastapi import FastAPI, HTTPException, Query, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import StreamingResponse, JSONResponse
    from pydantic import BaseModel
except ImportError:
    print("FastAPI not installed. Run: pip install fastapi uvicorn", file=sys.stderr)
    raise

import _review_ai
import _review_serializer as serializer


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class Config:
    worktree_roots: list[Path] = []

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "Config":
        c = cls()
        if args.config:
            cfg_path = Path(args.config).expanduser()
            if cfg_path.exists():
                import yaml
                data = yaml.safe_load(cfg_path.read_text())
                for p in data.get("worktrees", []):
                    c.worktree_roots.append(Path(p).expanduser().resolve())
        if args.repo_root:
            c.worktree_roots.append(Path(args.repo_root).expanduser().resolve())
        if not c.worktree_roots:
            c.worktree_roots.append(Path.cwd().resolve())
        return c


CONFIG = Config()


# ---------------------------------------------------------------------------
# Path resolution + boundary
# ---------------------------------------------------------------------------

BOOK_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")


def resolve_book_dir(slug: str) -> tuple[Path, Path]:
    """Return (book_dir, worktree_root) for the slug.

    Searches all configured worktree roots. Raises 404 if not found.
    Raises 422 if slug is malformed.
    """
    if not BOOK_SLUG_RE.match(slug):
        raise HTTPException(status_code=422, detail=f"invalid slug: {slug!r}")
    for root in CONFIG.worktree_roots:
        bd = root / "content" / "podcast" / "library" / "books" / slug
        if bd.is_dir():
            return bd, root
    raise HTTPException(status_code=404, detail=f"book {slug!r} not found in any worktree root")


def assert_path_inside_worktree(path: Path, worktree_root: Path) -> None:
    """Refuse if path escapes worktree_root."""
    try:
        path.resolve().relative_to(worktree_root.resolve())
    except ValueError as e:
        raise HTTPException(status_code=403, detail=f"path escape: {path} not under {worktree_root}") from e


# ---------------------------------------------------------------------------
# Lifespan + subprocess tracking
# ---------------------------------------------------------------------------

RESUME_PROCS: dict[str, subprocess.Popen[str]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Cleanup any in-flight resume subprocesses
    for slug, proc in list(RESUME_PROCS.items()):
        try:
            proc.terminate()
        except ProcessLookupError:
            pass


app = FastAPI(
    title="Operator Review Studio API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*", "http://127.0.0.1:*"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class FlagRowIn(BaseModel):
    page: int
    quote: str = ""
    note: str = ""
    recurring_pattern: bool = False


class GlossaryRowIn(BaseModel):
    term: str
    definition: str


class PronunciationRowIn(BaseModel):
    term: str
    correct: str


class ContentRangeIn(BaseModel):
    body_starts_at_page: int | None = None
    body_ends_at_page: int | None = None


class AISuggestionIn(BaseModel):
    id: str
    page: int
    quote: str
    reason: str
    feature: str
    status: str = "pending"


class ReviewIn(BaseModel):
    schema_version: int = 1
    book_slug: str = ""
    translation_issues: list[FlagRowIn] = []
    missing_passages: list[FlagRowIn] = []
    glossary: list[GlossaryRowIn] = []
    pronunciation: list[PronunciationRowIn] = []
    free_form_comments: str = ""
    content_range: ContentRangeIn = ContentRangeIn()
    approved: bool = False
    ai_suggestions: list[AISuggestionIn] = []


class ApprovePayload(BaseModel):
    commit_message: str | None = None
    mode: str = "fire"  # 'fire' | 'copy'


class AIPayload(BaseModel):
    params: dict[str, Any] = {}
    force_refresh: bool = False


# ---------------------------------------------------------------------------
# Book discovery
# ---------------------------------------------------------------------------

def _book_state(book_dir: Path) -> dict[str, Any]:
    """Read state.json + derive a summary."""
    state_path = book_dir / "state.json"
    state: dict[str, Any] = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    # Page count heuristic
    refined = book_dir / "_system" / "source" / "text" / "refined-english.md"
    page_count = 0
    if refined.exists():
        try:
            text = refined.read_text(encoding="utf-8", errors="ignore")
            page_count = len(re.findall(r"<!--\s*page\s+\d+", text)) or text.count("\n## p.") or 0
        except OSError:
            pass

    # Review file presence
    review_path = book_dir / "operator-review.md"

    return {
        "slug": book_dir.name,
        "phase_status": state.get("phase_status", "unknown"),
        "current_phase": state.get("current_phase", ""),
        "page_count": page_count,
        "ocr_confidence": state.get("ocr_confidence"),
        "has_review_file": review_path.exists(),
        "has_transcript": refined.exists(),
        "review_mtime": review_path.stat().st_mtime if review_path.exists() else None,
    }


@app.get("/api/books")
def list_books() -> dict[str, Any]:
    """List all books found across configured worktree roots."""
    books: list[dict[str, Any]] = []
    for root in CONFIG.worktree_roots:
        books_dir = root / "content" / "podcast" / "library" / "books"
        if not books_dir.is_dir():
            continue
        for bd in sorted(books_dir.iterdir()):
            if not bd.is_dir():
                continue
            try:
                info = _book_state(bd)
                info["worktree_root"] = str(root)
                books.append(info)
            except (OSError, ValueError):
                continue
    return {"worktree_roots": [str(r) for r in CONFIG.worktree_roots], "books": books}


@app.get("/api/books/{slug}")
def get_book(slug: str) -> dict[str, Any]:
    book_dir, root = resolve_book_dir(slug)
    info = _book_state(book_dir)
    info["worktree_root"] = str(root)
    return info


# ---------------------------------------------------------------------------
# Transcript
# ---------------------------------------------------------------------------

@app.get("/api/books/{slug}/transcript")
def get_transcript(slug: str) -> dict[str, Any]:
    book_dir, root = resolve_book_dir(slug)
    refined = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if not refined.exists():
        raise HTTPException(status_code=404, detail="refined-english.md not found")
    text = refined.read_text(encoding="utf-8", errors="replace")
    sig = serializer.atomic_write.__doc__  # placeholder; using sha256 directly below
    sig = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    # Build page index: list of (page_number, char_offset)
    page_index: list[dict[str, int]] = []
    for m in re.finditer(r"<!--\s*page\s+(\d+)\s*-->", text):
        page_index.append({"page": int(m.group(1)), "offset": m.start()})

    return {
        "slug": slug,
        "text": text,
        "source_signature": sig,
        "page_index": page_index,
        "char_count": len(text),
    }


# ---------------------------------------------------------------------------
# Review CRUD
# ---------------------------------------------------------------------------

@app.get("/api/books/{slug}/review")
def get_review(slug: str) -> dict[str, Any]:
    book_dir, root = resolve_book_dir(slug)
    review_path = book_dir / "operator-review.md"
    if not review_path.exists():
        # Return empty struct (P22 scaffolds it on halt; if missing, operator can populate)
        return serializer.ReviewStruct(book_slug=slug).to_dict()
    text = review_path.read_text(encoding="utf-8")
    rs = serializer.parse_from_markdown(text, book_slug=slug)
    d = rs.to_dict()
    d["mtime"] = review_path.stat().st_mtime
    return d


@app.put("/api/books/{slug}/review")
def put_review(slug: str, body: ReviewIn) -> dict[str, Any]:
    book_dir, root = resolve_book_dir(slug)
    review_path = book_dir / "operator-review.md"
    assert_path_inside_worktree(review_path, root)

    rs = serializer.ReviewStruct.from_dict(body.model_dump())
    rs.book_slug = slug
    text = serializer.serialize_to_markdown(rs)
    serializer.atomic_write(review_path, text)

    return {
        "ok": True,
        "slug": slug,
        "mtime": review_path.stat().st_mtime,
        "bytes_written": len(text.encode("utf-8")),
    }


@app.get("/api/books/{slug}/mtime")
def get_mtime(slug: str) -> dict[str, Any]:
    book_dir, _ = resolve_book_dir(slug)
    review_path = book_dir / "operator-review.md"
    return {
        "exists": review_path.exists(),
        "mtime": review_path.stat().st_mtime if review_path.exists() else None,
    }


# ---------------------------------------------------------------------------
# Approve + Resume
# ---------------------------------------------------------------------------

@app.post("/api/books/{slug}/approve")
def approve(slug: str, body: ApprovePayload) -> dict[str, Any]:
    book_dir, root = resolve_book_dir(slug)
    review_path = book_dir / "operator-review.md"
    assert_path_inside_worktree(review_path, root)

    # Ensure approval mark is set
    if review_path.exists():
        text = review_path.read_text(encoding="utf-8")
        rs = serializer.parse_from_markdown(text, book_slug=slug)
        if not rs.approved:
            rs.approved = True
            serializer.atomic_write(review_path, serializer.serialize_to_markdown(rs))
    else:
        raise HTTPException(status_code=400, detail="operator-review.md does not exist; cannot approve")

    # Build commit message
    commit_msg = body.commit_message or (
        f"podcast({slug}): operator transcript review — {serializer.summary_one_line(rs)}"
    )

    # Git commit (best-effort)
    git_result: dict[str, Any] = {"committed": False}
    try:
        subprocess.run(["git", "add", str(review_path.relative_to(root))], cwd=str(root), check=True, capture_output=True, timeout=10)
        cm = subprocess.run(
            ["git", "commit", "-m", commit_msg, "--no-verify"],
            cwd=str(root), capture_output=True, text=True, timeout=15,
        )
        if cm.returncode == 0:
            git_result = {"committed": True, "message": commit_msg}
        else:
            git_result = {"committed": False, "stderr": cm.stderr[:400]}
    except (subprocess.SubprocessError, OSError) as e:
        git_result = {"committed": False, "error": str(e)}

    if body.mode == "copy":
        cmd = f"python3 scripts/podcast/orchestrate_book.py --resume {slug} --approve-transcript"
        return {
            "ok": True,
            "mode": "copy",
            "command": cmd,
            "cwd": str(root),
            "git": git_result,
        }

    # Fire mode: spawn the resume subprocess detached
    # Stream output via SSE on /resume-log
    try:
        proc = subprocess.Popen(
            ["python3", "scripts/podcast/orchestrate_book.py", "--resume", slug, "--approve-transcript"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        RESUME_PROCS[slug] = proc
        # Persist PID
        pid_path = book_dir / "_system" / "resume-pid"
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(str(proc.pid))
        return {
            "ok": True,
            "mode": "fire",
            "pid": proc.pid,
            "git": git_result,
        }
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"could not spawn resume: {e}") from e


@app.get("/api/books/{slug}/resume-log")
async def resume_log(slug: str) -> StreamingResponse:
    proc = RESUME_PROCS.get(slug)
    if not proc:
        raise HTTPException(status_code=404, detail="no in-flight resume for this book")

    async def gen():
        loop = asyncio.get_event_loop()
        while True:
            if proc.stdout is None:
                break
            line = await loop.run_in_executor(None, proc.stdout.readline)
            if not line:
                # Process ended
                rc = proc.wait(timeout=1) if proc.poll() is not None else None
                yield f"event: end\ndata: {{\"rc\": {rc}}}\n\n"
                RESUME_PROCS.pop(slug, None)
                break
            yield f"data: {json.dumps({'line': line.rstrip()})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.delete("/api/books/{slug}/resume-log")
def cancel_resume(slug: str) -> dict[str, Any]:
    proc = RESUME_PROCS.get(slug)
    if not proc:
        raise HTTPException(status_code=404, detail="no in-flight resume")
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    finally:
        RESUME_PROCS.pop(slug, None)
    return {"ok": True, "cancelled": True}


# ---------------------------------------------------------------------------
# AI endpoints (P25.7)
# ---------------------------------------------------------------------------

@app.post("/api/books/{slug}/ai/{feature}")
def ai_endpoint(slug: str, feature: str, body: AIPayload) -> dict[str, Any]:
    book_dir, root = resolve_book_dir(slug)
    refined = book_dir / "_system" / "source" / "text" / "refined-english.md"

    if feature in {"summarize", "arabic", "preflight", "voice-shift", "episode-plan", "suggest-flags", "content-range"} and not refined.exists():
        raise HTTPException(status_code=400, detail="refined-english.md not present; cannot run AI feature")

    source_signature = ""
    if refined.exists():
        text = refined.read_text(encoding="utf-8", errors="ignore")
        source_signature = "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    try:
        result = _review_ai.run_feature(
            feature=feature,
            book_dir=book_dir,
            worktree_root=root,
            source_signature=source_signature,
            params=body.params,
            force_refresh=body.force_refresh,
        )
    except _review_ai.BudgetExceeded as e:
        raise HTTPException(status_code=429, detail={"error": "budget exceeded", "feature": e.feature, "remaining": e.remaining}) from e
    except _review_ai.BoundaryViolation as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e

    return {
        "ok": True,
        "feature": result.feature,
        "model": result.model,
        "cached": result.cached,
        "cost_usd": result.cost_usd,
        "elapsed_sec": result.elapsed_sec,
        "payload": result.payload,
    }


@app.get("/api/books/{slug}/ai/budget")
def ai_budget(slug: str) -> dict[str, Any]:
    book_dir, _ = resolve_book_dir(slug)
    spent = _review_ai.book_ai_spend_so_far(book_dir)
    return {
        "spent_usd": round(spent, 4),
        "budget_usd": _review_ai.BOOK_AI_BUDGET_USD,
        "remaining_usd": round(_review_ai.BOOK_AI_BUDGET_USD - spent, 4),
    }


# ---------------------------------------------------------------------------
# Health + meta
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "service": "operator-review-studio",
        "worktree_roots": [str(r) for r in CONFIG.worktree_roots],
        "in_flight_resumes": list(RESUME_PROCS.keys()),
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Operator Review Studio FastAPI backend")
    p.add_argument("--repo-root", default=None, help="Path to a single worktree (default: cwd)")
    p.add_argument("--config", default=None, help="Path to ~/.journal-worktrees.yaml for multi-worktree mode")
    p.add_argument("--port", type=int, default=8766)
    p.add_argument("--host", default="127.0.0.1")
    args = p.parse_args(argv)

    global CONFIG
    CONFIG = Config.from_args(args)

    print(f"[review-server] worktree_roots: {[str(r) for r in CONFIG.worktree_roots]}", file=sys.stderr)
    print(f"[review-server] listening on http://{args.host}:{args.port}", file=sys.stderr)

    try:
        import uvicorn
    except ImportError:
        print("uvicorn not installed. Run: pip install uvicorn", file=sys.stderr)
        return 1

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
