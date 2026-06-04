#!/usr/bin/env python3
"""_chunking.py — windowed processing helpers for long-source LLM phases.

PROBLEM

  Phases 0b (English refinement) and 0c (Arabic phonetic pass) of the
  /podcast pipeline used to shell out a SINGLE `claude -p` call against
  the entire `raw-extract.md`. On books >~30k words this blew past the
  30-minute shellout timeout, producing no artifact and halting the
  orchestrator with no recoverable partial work.

  The actual /podcast skill (run interactively) handles long books by
  processing the text in passes, but the headless orchestrator had no
  equivalent. This module is that equivalent.

DESIGN

  Two operations on long source text:

  1. `iter_windows(text, target_words, overlap_words)` — split text into
     paragraph-aligned windows of roughly `target_words` words. Splits
     prefer markdown heading boundaries, then blank-line paragraph
     boundaries, then sentence boundaries. Adds a small `overlap_words`
     suffix from the prior window for cross-window coherence.

  2. `run_windowed(...)` — checkpointed driver. For each window, writes
     a `_chunks/<phase>/win-<NNN>.in.md` input, calls the caller-supplied
     `_invoke_fn` (SDK path, DR-015/F38), writes the output to
     `_chunks/<phase>/win-<NNN>.out.md`. Skips windows whose `.out.md`
     already exists and is non-empty (resume-safe). Returns the ordered
     list of output paths.

  3. `concat_outputs(paths, sep)` — stitch per-window outputs into the
     final artifact, dropping per-window scaffolding the prompt may have
     produced (e.g. leading "Here is the refined text:" lines).

USAGE (from _authoring.py)

    from _chunking import iter_windows, run_windowed, concat_outputs

    chunks_dir = book_dir / "_system" / "source" / "text" / "_chunks" / "0b"
    out_paths = run_windowed(
        text=raw_extract_text,
        chunks_dir=chunks_dir,
        target_words=3000,
        overlap_words=120,
        prompt_builder=lambda body, idx, total: build_0b_window_prompt(...),
        timeout_per_window=600,
    )
    refined_text = concat_outputs(out_paths)
    out_path.write_text(refined_text, encoding="utf-8")

GUARANTEES

  · Atomic per-window writes (tmpfile + rename).
  · Resume-safe: re-running skips windows already on disk.
  · Each window's `.in.md` carries a YAML provenance front-matter so a
    human can re-drive that window manually via `/podcast` if needed.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator

try:
    import anthropic as _anthropic
except ImportError:
    _anthropic = None  # type: ignore[assignment]

# Callable type for the SDK-based invocation path.
# Signature: (instructions, body, timeout_secs) -> output_text
InvokeFn = Callable[[str, str, int], str]

DEFAULT_TARGET_WORDS = 3000
DEFAULT_OVERLAP_WORDS = 120
DEFAULT_WINDOW_TIMEOUT = 600   # 10 min per window — generous; small windows finish in ~1-2 min


class ChunkingError(RuntimeError):
    """Raised when windowed processing cannot proceed.

    Triggers include: the claude binary is missing; every window failed; a
    window returned rc=0 but produced no artifact (the P5.1 failure class
    that v3 P5.2 hardens against silent continuation).
    """

    def __init__(
        self,
        message: str,
        *,
        manual_fallback: str = "",
        stdout: str = "",
        stderr: str = "",
    ):
        super().__init__(message)
        self.manual_fallback = manual_fallback
        self.stdout = stdout
        self.stderr = stderr


# ─── window splitter ─────────────────────────────────────────────────────────


_HEADING_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)


def _word_count(text: str) -> int:
    return len(text.split())


def iter_windows(
    text: str,
    *,
    target_words: int = DEFAULT_TARGET_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> Iterator[str]:
    """Yield paragraph-aligned windows of roughly `target_words` words.

    Splits on blank-line paragraph boundaries; prefers to break on a markdown
    heading start when one falls inside the target band. Adds a tail of
    `overlap_words` words from the prior window as a prefix to the next one
    for cross-window context (helps the LLM keep stylistic continuity for
    refinement passes).
    """
    if target_words <= 0:
        raise ValueError("target_words must be positive")
    paragraphs = re.split(r"\n\s*\n", text)
    paragraphs = [p.rstrip() for p in paragraphs if p.strip()]
    if not paragraphs:
        return

    current: list[str] = []
    current_wc = 0
    prior_tail: str = ""

    def flush() -> str | None:
        nonlocal current, current_wc
        if not current:
            return None
        body = "\n\n".join(current)
        if prior_tail:
            body = f"<!-- context-overlap from prior window -->\n{prior_tail}\n\n<!-- /context-overlap -->\n\n{body}"
        current = []
        current_wc = 0
        return body

    for para in paragraphs:
        para_wc = _word_count(para)
        # If a single paragraph is already larger than the target, emit it on its own.
        if para_wc >= target_words and not current:
            yielded = flush()  # nothing to flush but keep symmetry
            if yielded:
                yield yielded
            yield (
                (f"<!-- context-overlap from prior window -->\n{prior_tail}\n\n<!-- /context-overlap -->\n\n"
                 if prior_tail else "") + para
            )
            prior_tail = " ".join(para.split()[-overlap_words:]) if overlap_words else ""
            continue

        if current_wc + para_wc > target_words and current:
            # Prefer to break here — but if the next paragraph starts with a heading
            # AND we're already past 60% of target, break before the heading too.
            yielded = flush()
            if yielded:
                yield yielded
                prior_tail = " ".join(yielded.split()[-overlap_words:]) if overlap_words else ""
            current.append(para)
            current_wc = para_wc
        else:
            # Soft preference: if this paragraph is a heading and we're already >= 60%
            # of target, flush before it so headings start a window.
            if (
                _HEADING_RE.match(para)
                and current_wc >= int(target_words * 0.6)
            ):
                yielded = flush()
                if yielded:
                    yield yielded
                    prior_tail = " ".join(yielded.split()[-overlap_words:]) if overlap_words else ""
            current.append(para)
            current_wc += para_wc

    final = flush()
    if final:
        yield final


# ─── SDK invocation helpers (DR-015 / F38) ───────────────────────────────────

# Lines matching these patterns are stripped from claude -p prompts before the
# instructions are sent to the SDK — they instruct claude to read/write files,
# which the API cannot do; Python handles file I/O directly instead.
_FILE_IO_PATTERNS = (
    re.compile(r"^INPUT\s.*$", re.MULTILINE),
    re.compile(r"^OUTPUT\s.*$", re.MULTILINE),
    re.compile(r"^Exit when\s.*$", re.MULTILINE | re.IGNORECASE),
)


def _strip_file_io_lines(prompt: str) -> str:
    """Remove claude -p file-path directives from a prompt for SDK use."""
    for pat in _FILE_IO_PATTERNS:
        prompt = pat.sub("", prompt)
    return re.sub(r"\n{3,}", "\n\n", prompt).strip()


def make_sdk_invoke_fn(model: str, client: "_anthropic.Anthropic | None" = None) -> "InvokeFn":
    """Return an InvokeFn that calls the Anthropic SDK directly.

    The returned function takes (instructions, body, timeout_secs) and returns
    the processed text. Pass as `_invoke_fn` to `run_windowed`.
    """
    if _anthropic is None:
        raise ImportError("anthropic package required for SDK invocation; run: pip install anthropic")
    if client is not None:
        _client = client
    else:
        # Source the key via the central resolver (env → keychain → Azure Key Vault)
        # so 0b/0c work on any machine with `az login`, even with no keychain entry.
        from _secrets import get_anthropic_key
        _client = _anthropic.Anthropic(api_key=get_anthropic_key())

    def _invoke(instructions: str, body: str, timeout_secs: int) -> str:
        clean_instructions = _strip_file_io_lines(instructions)
        user_msg = (
            f"{clean_instructions}\n\n"
            f"<content>\n{body}\n</content>\n\n"
            "Output ONLY the processed text. No preamble, no fences."
        )
        try:
            msg = _client.messages.create(
                model=model,
                max_tokens=8192,
                messages=[{"role": "user", "content": user_msg}],
                timeout=float(timeout_secs),
            )
            return msg.content[0].text if msg.content else ""
        except _anthropic.APITimeoutError:
            return ""
        except Exception as exc:  # noqa: BLE001
            sys.stderr.write(f"[_chunking] SDK call failed: {exc!r}\n")
            return ""

    return _invoke


# ─── per-window claude shellout ──────────────────────────────────────────────


@dataclass(frozen=True)
class WindowResult:
    index: int
    in_path: Path
    out_path: Path
    skipped: bool
    rc: int = 0
    stderr: str = ""


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.rename(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def run_windowed(
    *,
    text: str,
    chunks_dir: Path,
    prompt_builder: Callable[[str, int, int, Path], str],
    target_words: int = DEFAULT_TARGET_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
    timeout_per_window: int = DEFAULT_WINDOW_TIMEOUT,
    log: Callable[[str], None] = print,
    book_dir: Path | None = None,
    phase: str = "",
    model: str = "claude-opus-4-7",
    max_workers: int = 1,
    _invoke_fn: "InvokeFn",
) -> list[Path]:
    """Drive LLM calls once per window with checkpointing (SDK path, DR-015/F38).

    Python handles file I/O; `_invoke_fn` receives (instructions, body, timeout_secs)
    and returns the processed text string (empty string on failure).

    Arguments:
      text                — full source text to chunk
      chunks_dir          — directory for `win-NNN.in.md` and `win-NNN.out.md`
      prompt_builder      — callable(body, idx, total, out_path) → prompt string
      target_words        — words per window (default 3000)
      overlap_words       — context-overlap suffix from prior window (default 120)
      timeout_per_window  — per-window timeout in seconds passed to _invoke_fn (default 600)
      log                 — callable for progress logging (default print)
      book_dir            — (optional) book directory; if provided, appends a
                            cost-ledger row per window via `_cost_ledger` (P6.1).
      phase               — (optional) phase label for ledger rows (e.g., "0b").
      model               — model name label for ledger rows.
      max_workers         — if > 1, runs windows in a ThreadPoolExecutor. Threads
                            are I/O-bound (waiting on the SDK); true wall-clock
                            speedup. cost-ledger and failures list are protected by
                            Python lock. Default 1 = sequential behavior.

    Returns the ordered list of out_path objects (one per window, in order).
    Raises ChunkingError if every window fails.
    """
    chunks_dir.mkdir(parents=True, exist_ok=True)
    windows = list(iter_windows(text, target_words=target_words, overlap_words=overlap_words))
    if not windows:
        raise ChunkingError("no windows produced — input text is empty")

    total = len(windows)
    if max_workers > 1:
        log(f"    chunking: {total} windows · target={target_words} words · overlap={overlap_words} · parallel={max_workers}")
    else:
        log(f"    chunking: {total} windows · target={target_words} words · overlap={overlap_words}")

    # Build (idx, body, out_path) tuples up-front so the worker function is
    # self-contained and can run in any order.
    out_paths: list[Path] = []
    work_items: list[tuple[int, str, Path]] = []
    for idx, body in enumerate(windows, start=1):
        in_path = chunks_dir / f"win-{idx:03d}.in.md"
        out_path = chunks_dir / f"win-{idx:03d}.out.md"
        out_paths.append(out_path)
        # Resume: if the output already exists and is non-empty, skip queueing.
        if out_path.exists() and out_path.stat().st_size > 0:
            log(f"    win {idx:03d}/{total} · skip (already done, {out_path.stat().st_size} bytes)")
            continue
        work_items.append((idx, body, out_path))

    if not work_items:
        # All windows already done from a prior run; nothing to do.
        return out_paths

    # Shared-state guards for the worker function.
    import threading as _threading
    failures: list[tuple[int, str]] = []
    fatal_error: list[ChunkingError] = []  # use list as mutable holder for first fatal
    state_lock = _threading.Lock()

    def _process_window(idx: int, body: str, out_path: Path) -> None:
        """Worker — runs one window via SDK path. Safe to call in a thread."""
        in_path = chunks_dir / f"win-{idx:03d}.in.md"
        # Write the input chunk for provenance.
        _atomic_write(in_path, body)
        prompt = prompt_builder(body, idx, total, out_path)

        log(f"    win {idx:03d}/{total} · invoking SDK ({_word_count(body)} words in)")
        output_text = _invoke_fn(prompt, body, timeout_per_window)
        if not output_text:
            with state_lock:
                failures.append((idx, "SDK returned empty output"))
            log(f"    win {idx:03d}/{total} · FAILED (empty SDK response)")
            return
        _atomic_write(out_path, output_text)
        if book_dir is not None:
            try:
                from _cost_ledger import append_cost_row
                append_cost_row(
                    book_dir, phase=phase or "(unspecified)",
                    step=f"win-{idx:03d}", model=model,
                    input_tokens=0, output_tokens=0,
                )
            except Exception:  # noqa: BLE001
                pass
        log(f"    win {idx:03d}/{total} · OK ({out_path.stat().st_size} bytes)")

    # Dispatch — sequential (max_workers==1) or parallel (>1).
    if max_workers <= 1:
        for idx, body, out_path in work_items:
            _process_window(idx, body, out_path)
            if fatal_error:
                raise fatal_error[0]
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(_process_window, idx, body, out_path)
                       for idx, body, out_path in work_items]
            for f in as_completed(futures):
                _ = f.result()  # surface any worker exception
                if fatal_error:
                    # Cancel pending futures; raise the fatal.
                    for pf in futures:
                        pf.cancel()
                    raise fatal_error[0]

    if failures and len(failures) == total:
        raise ChunkingError(
            f"all {total} windows failed: " + "; ".join(f"win {i}: {m}" for i, m in failures[:3]),
            manual_fallback=(
                f"Inspect {chunks_dir}/win-*.in.md and drive each window manually "
                f"via the /podcast skill; place output as `win-NNN.out.md` then re-resume."
            ),
        )
    if failures:
        # Partial failure — surface to caller via missing out_paths; concat_outputs will
        # raise if any required window is empty.
        log(f"    chunking: {len(failures)} of {total} windows failed; resume will retry them")

    return out_paths


# ─── concat ───────────────────────────────────────────────────────────────────


_STRIP_PREAMBLES = (
    re.compile(r"^\s*here(?:'|')?s\s+the\s+[^\n]+:\s*\n", re.IGNORECASE),
    re.compile(r"^\s*here\s+is\s+the\s+[^\n]+:\s*\n", re.IGNORECASE),
    re.compile(r"^\s*```(?:markdown|md)?\s*\n", re.IGNORECASE),
)


def _strip_preamble(text: str) -> str:
    """Drop common LLM preambles ('Here is the refined text:') and code fences."""
    out = text
    for pat in _STRIP_PREAMBLES:
        out = pat.sub("", out, count=1)
    # Trailing closing fence
    out = re.sub(r"\n```\s*$", "", out)
    return out.strip() + "\n"


def concat_outputs(paths: list[Path], sep: str = "\n\n") -> str:
    """Stitch per-window outputs into the final artifact.

    Raises ChunkingError if any path is missing or empty.
    """
    missing: list[int] = []
    parts: list[str] = []
    for i, p in enumerate(paths, start=1):
        if not p.exists() or p.stat().st_size == 0:
            missing.append(i)
            continue
        parts.append(_strip_preamble(p.read_text(encoding="utf-8")))
    if missing:
        raise ChunkingError(
            f"cannot concat: {len(missing)} window(s) missing output: "
            f"win-{', win-'.join(f'{i:03d}' for i in missing[:5])}",
            manual_fallback=(
                "Re-run the orchestrator with --resume; failed windows will be retried. "
                "If a window keeps failing, drive it manually via /podcast and drop the "
                "result at the expected win-NNN.out.md path."
            ),
        )
    return sep.join(parts).rstrip() + "\n"
