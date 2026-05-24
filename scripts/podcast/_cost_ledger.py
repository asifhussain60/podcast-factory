#!/usr/bin/env python3
"""Cost ledger writer for the podcast pipeline (P6.1).

Appends one JSON-line per `claude -p` invocation to
    <book_dir>/_system/cost-ledger.jsonl

Schema (one row per call):
    {
      "ts":             "<ISO-8601 UTC>",
      "phase":          "05-refine-english",
      "step":           "win-007"  | "ch01-frame-and-first-counsel" | "(toc)" | …,
      "model":          "claude-opus-4-7"  | "claude-sonnet-4-6" | …,
      "input_tokens":   <int>,
      "output_tokens":  <int>,
      "cache_read":     <int>,
      "cache_create":   <int>,
      "cost_usd":       <float>
    }

Pricing table is a module constant. Unknown models emit a structured warning
to stderr (not a silent zero — per P6.1 acceptance).

Used by:
  • scripts/podcast/_chunking.py  (after each windowed claude -p)
  • scripts/podcast/_authoring.py (after each phase claude -p)
  • scripts/podcast/cost_ledger_summary.py  (read-only consumer; P6.2)
  • scripts/podcast/run_wave.py    (W3 cost-cap pre-flight; already wired)
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

# Pricing per million tokens (USD). Source: Anthropic public pricing as of
# 2026-05; refresh as Anthropic updates. Cache reads are 10% of input; cache
# writes are 125% of input (per Anthropic prompt-caching docs).
#
# Each entry: (input_usd_per_million, output_usd_per_million,
#              cache_read_usd_per_million, cache_create_usd_per_million)
PRICING_USD_PER_MILLION_TOKENS: dict[str, tuple[float, float, float, float]] = {
    # Claude 4.x family (current as of 2026-05)
    "claude-opus-4-7":     (15.00, 75.00, 1.50, 18.75),
    "claude-opus-4-6":     (15.00, 75.00, 1.50, 18.75),
    "claude-sonnet-4-6":   ( 3.00, 15.00, 0.30,  3.75),
    "claude-haiku-4-5-20251001": (0.80, 4.00, 0.08, 1.00),

    # Claude 3.5/3.7 family (legacy compat — kept for trainer-historic ledgers)
    "claude-3-7-sonnet-20250219": (3.00, 15.00, 0.30, 3.75),
    "claude-3-5-sonnet-20241022": (3.00, 15.00, 0.30, 3.75),
    "claude-3-5-haiku-20241022":  (0.80, 4.00, 0.08, 1.00),
}


@dataclass(frozen=True)
class CostRow:
    ts: str
    phase: str
    step: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_read: int
    cache_create: int
    cost_usd: float


def compute_cost_usd(
    model: str,
    *,
    input_tokens: int,
    output_tokens: int,
    cache_read: int = 0,
    cache_create: int = 0,
) -> float:
    """Multiply token counts by the model's per-million-token price.

    Unknown models emit a structured warning to stderr and return 0.0 — never
    a silent zero. Per P6.1 acceptance.
    """
    pricing = PRICING_USD_PER_MILLION_TOKENS.get(model)
    if pricing is None:
        sys.stderr.write(
            f'[_cost_ledger] WARNING: unknown model {model!r} — '
            f"cost row will record 0.0 USD. Add the model to "
            f"PRICING_USD_PER_MILLION_TOKENS in scripts/podcast/_cost_ledger.py "
            f"to enable accurate pricing.\n"
        )
        return 0.0
    in_p, out_p, cr_p, cc_p = pricing
    cost = (
        input_tokens   * in_p  +
        output_tokens  * out_p +
        cache_read     * cr_p  +
        cache_create   * cc_p
    ) / 1_000_000.0
    return round(cost, 6)


def _now_iso() -> str:
    # F6 fix (2026-05-21): datetime.UTC is Python 3.11+. Use timezone.utc for
    # Python 3.9 / 3.10 compatibility (Air session runs 3.9). The two are
    # equivalent under the hood; UTC was added as an alias in 3.11.
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_cost_row(
    book_dir: Path,
    *,
    phase: str,
    step: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_read: int = 0,
    cache_create: int = 0,
    ts: str | None = None,
) -> CostRow:
    """Append a single row to <book_dir>/_system/cost-ledger.jsonl.

    Returns the constructed `CostRow`. The function is idempotent in the
    'safe-to-call-multiple-times' sense: each call appends one new row. If the
    caller invokes it twice for the same logical event, two rows result —
    callers must enforce one-row-per-call.
    """
    cost = compute_cost_usd(
        model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read=cache_read,
        cache_create=cache_create,
    )
    row = CostRow(
        ts=ts or _now_iso(),
        phase=phase,
        step=step,
        model=model,
        input_tokens=int(input_tokens),
        output_tokens=int(output_tokens),
        cache_read=int(cache_read),
        cache_create=int(cache_create),
        cost_usd=cost,
    )
    ledger = book_dir / "_system" / "cost-ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(row)) + "\n")
    return row


# ── Token-usage extraction from `claude -p` stdout ───────────────────────────
#
# Claude Code CLI emits a final usage summary line at the end of its output.
# The format is documented in `claude --help`; we parse it tolerantly here.

# Patterns we try to find in stdout. Tested against multiple `claude -p` output
# samples; each pattern is anchored to the variant most recently observed.
_USAGE_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    # Most common: "Tokens: 12345 in, 6789 out, cache: 1024 read, 0 create"
    ("input",        re.compile(r"(\d+)\s*in\b", re.IGNORECASE)),
    ("output",       re.compile(r"(\d+)\s*out\b", re.IGNORECASE)),
    ("cache_read",   re.compile(r"cache[^\n]*?(\d+)\s*read\b", re.IGNORECASE)),
    ("cache_create", re.compile(r"cache[^\n]*?(\d+)\s*create\b", re.IGNORECASE)),
)


def parse_usage_from_stdout(stdout: str) -> dict[str, int]:
    """Best-effort extraction of token counts from `claude -p` stdout.

    Returns a dict with keys `input`, `output`, `cache_read`, `cache_create`,
    plus an optional `cost_usd` from Claude's own ledger when JSON-format
    output is detected (more authoritative than our PRICING_USD_PER_MILLION
    table). Missing or unparseable fields default to 0. Never raises.

    Two input shapes supported:
      1. Legacy text-format stdout (pre-2026-05 `claude -p` output): uses
         the regex patterns in _USAGE_PATTERNS.
      2. JSON-format stdout (`claude -p --output-format json`, 2026-05+):
         parses the single JSON line and reads `usage.input_tokens`,
         `usage.output_tokens`, `usage.cache_read_input_tokens`,
         `usage.cache_creation_input_tokens`, plus `total_cost_usd`.

    The JSON path is preferred when both could parse (it's authoritative);
    text-path stays in for legacy stdout that callers may still feed in.
    """
    out = {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0, "cost_usd": 0.0}
    if not stdout:
        return out
    # Try JSON-format first. The CLI emits ONE JSON object per call when
    # --output-format=json is set; stream-json emits multiple lines.
    stripped = stdout.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
            usage = data.get("usage") or {}
            out["input"] = int(usage.get("input_tokens", 0))
            out["output"] = int(usage.get("output_tokens", 0))
            out["cache_read"] = int(usage.get("cache_read_input_tokens", 0))
            out["cache_create"] = int(usage.get("cache_creation_input_tokens", 0))
            out["cost_usd"] = float(data.get("total_cost_usd", 0.0))
            return out
        except (ValueError, TypeError, KeyError):
            pass  # Fall through to text-format regex
    # Legacy text-format regex
    for key, pat in _USAGE_PATTERNS:
        m = pat.search(stdout)
        if m:
            try:
                out[key] = int(m.group(1))
            except (ValueError, IndexError):
                pass
    return out


def parse_text_from_json_stdout(stdout: str) -> str:
    """Extract the LLM's text response from `claude -p --output-format json` stdout.

    Returns the `result` field. If stdout isn't valid JSON, returns it
    unchanged (legacy text-format path).
    """
    stripped = stdout.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return stdout
    try:
        data = json.loads(stripped)
        return str(data.get("result", "") or stdout)
    except (ValueError, TypeError):
        return stdout


def append_from_claude_p_stdout(
    book_dir: Path,
    *,
    phase: str,
    step: str,
    model: str,
    stdout: str,
    ts: str | None = None,
) -> CostRow:
    """Convenience: parse usage out of claude -p stdout, then append.

    This is the canonical call site for the call-site wrappers in
    `_chunking.py` and `_authoring.py` once P6.1 integrates with those.
    """
    usage = parse_usage_from_stdout(stdout)
    # If the JSON path produced an authoritative cost_usd, prefer it over
    # our PRICING_USD_PER_MILLION calculation (Claude's own ledger is
    # authoritative for any model + tier combination).
    if usage.get("cost_usd", 0.0) > 0:
        row = CostRow(
            ts=ts or _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            phase=phase,
            step=step,
            model=model,
            input_tokens=int(usage["input"]),
            output_tokens=int(usage["output"]),
            cache_read=int(usage["cache_read"]),
            cache_create=int(usage["cache_create"]),
            cost_usd=float(usage["cost_usd"]),
        )
        ledger_path = book_dir / "_system" / "cost-ledger.jsonl"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(row)) + "\n")
        return row
    # Fall through to the legacy path that computes from PRICING_USD_PER_MILLION
    return append_cost_row(
        book_dir,
        phase=phase,
        step=step,
        model=model,
        input_tokens=usage["input"],
        output_tokens=usage["output"],
        cache_read=usage["cache_read"],
        cache_create=usage["cache_create"],
        ts=ts,
    )
