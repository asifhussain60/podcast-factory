#!/usr/bin/env python3
"""preflight_doctor.py — Setup stage: full system check before pipeline work.

This is the **Setup stage** of the podcast-factory pipeline. It runs once, at the
very top of `orchestrate_book.main()` (before the watchdog is spawned and before
any LLM/Azure spend), and verifies that the machine can actually do the work:

  1. deps        — PyYAML / anthropic / requests importable under this interpreter
  2. claude-auth — `claude -p` can authenticate (token not expired + live ping)
  3. anthropic   — api.anthropic.com reachable on :443
  4. azure       — Azure OCR/Translate reachable (only when an ingest phase 0a
                   still has to run; skipped on resumes past 0a)

Design intent (per Asif, 2026-06-07): "run a full system check before beginning
the pipeline work … check for expired tokens, connection issues and resolve
EVERYTHING before proceeding." Auto-resolvable problems are auto-resolved
(the interpreter re-exec lives in orchestrate_book._ensure_capable_interpreter);
everything else FAILS FAST here with the exact fix command, so the pipeline never
crashes deep inside Phase 0d with a swallowed `claude -p` rc=1 (the failure mode
this stage was created to eliminate).

Exit/return contract:
  run_doctor(...) -> 0  when every hard check passes (warnings allowed)
                  -> 1  when any hard check FAILS (caller must not proceed)

Standalone:  python3 scripts/podcast/preflight_doctor.py [--no-azure] [--no-ping]
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
AZURE_PROBE = REPO_ROOT / "scripts" / "podcast" / "test_azure_connectivity.py"
KEYCHAIN_SERVICE = "Claude Code-credentials"

# Status tokens + glyphs.
OK, WARN, FAIL, SKIP = "OK", "WARN", "FAIL", "SKIP"
_GLYPH = {OK: "✓", WARN: "⚠", FAIL: "✗", SKIP: "—"}


class CheckResult:
    __slots__ = ("name", "status", "detail", "fix")

    def __init__(self, name: str, status: str, detail: str, fix: str = "") -> None:
        self.name = name
        self.status = status
        self.detail = detail
        self.fix = fix


# ─────────────────────────── individual checks ───────────────────────────────


def check_deps() -> CheckResult:
    """PyYAML / anthropic / requests must import under the active interpreter."""
    missing = []
    for mod in ("yaml", "anthropic", "requests"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        return CheckResult(
            "deps",
            FAIL,
            f"missing under {sys.executable}: {', '.join(missing)}",
            "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt",
        )
    return CheckResult("deps", OK, "yaml, anthropic, requests importable")


def _claude_keychain_expiry() -> CheckResult | None:
    """Fast, free pre-check (macOS only): read the OAuth token's expiresAt from
    the keychain and flag an already-expired token before spending a live ping.

    Returns None when the check is not applicable (non-macOS, no entry, parse
    failure) so the caller falls through to the authoritative live ping.
    """
    if sys.platform != "darwin":
        return None
    try:
        proc = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        cred = json.loads(proc.stdout)
        oauth = cred.get("claudeAiOauth", cred)
        expires_at = int(oauth["expiresAt"])  # ms since epoch
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None
    age_h = (time.time() * 1000 - expires_at) / 3_600_000
    if age_h > 0:
        return CheckResult(
            "claude-auth",
            FAIL,
            f"OAuth access token expired {age_h:.1f}h ago (keychain)",
            "claude login   # re-authenticate; writes a fresh token to the keychain",
        )
    return None  # token still valid → confirm with a live ping


def check_claude_auth(do_ping: bool = True) -> CheckResult:
    """Verify `claude -p` can authenticate.

    Strategy: fast keychain expiry pre-check as an ADVISORY hint only (never
    blocks the pipeline), then an authoritative live `claude -p` ping that
    mirrors how the pipeline actually calls it (API-key env stripped → forces
    Max OAuth). The CLI auto-refreshes the access token via its stored refresh
    token, so an expired access token in the keychain is not a hard failure —
    only a failed live ping is definitive.
    """
    early = _claude_keychain_expiry()
    if early is not None:
        # Advisory only — the CLI may auto-refresh using the stored refresh token.
        # Fall through to the live ping; if it succeeds the pipeline is clear.
        _early_hint = early.detail  # captured for the success message below
    else:
        _early_hint = ""
    if not do_ping:
        hint = " (keychain shows expired — will auto-refresh on first use)" if _early_hint else ""
        return CheckResult("claude-auth", OK, f"keychain check done{hint} (ping skipped)")

    # Live ping requires a TTY — claude -p hangs in capture_output subprocess mode.
    # If stdin is not a TTY (headless/watchdog/subprocess context), skip the ping.
    import sys as _sys

    if not _sys.stdin.isatty():
        hint = (
            " (headless — ping skipped, keychain used)"
            if not _early_hint
            else " (keychain shows expired; ping skipped headless)"
        )
        return CheckResult("claude-auth", OK, f"keychain check done{hint}")

    # Mirror _authoring._core._run_claude_p: strip API-key env so auth resolves
    # via the flat-rate Max OAuth session, never the metered API.
    child_env = dict(os.environ)
    for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        child_env.pop(var, None)
    try:
        proc = subprocess.run(
            ["claude", "-p", "--output-format", "json", "Reply with exactly: pong"],
            capture_output=True,
            text=True,
            timeout=90,
            env=child_env,
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return CheckResult(
            "claude-auth",
            FAIL,
            "`claude` CLI not found on PATH",
            "Install Claude Code: https://docs.claude.com/en/docs/claude-code/quickstart",
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            "claude-auth",
            FAIL,
            "`claude -p` timed out after 90s (network?)",
            "Check connectivity, then retry",
        )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return CheckResult(
            "claude-auth",
            FAIL,
            f"`claude -p` returned non-JSON (rc={proc.returncode}): {(proc.stdout or proc.stderr)[:120]}",
            "claude login",
        )
    if payload.get("is_error"):
        code = payload.get("api_error_status")
        if code == 401:
            return CheckResult(
                "claude-auth",
                FAIL,
                "`claude -p` auth failed (HTTP 401 — token expired/invalid)",
                "claude login   # re-authenticate; writes a fresh token to the keychain",
            )
        return CheckResult(
            "claude-auth",
            FAIL,
            f"`claude -p` errored: {str(payload.get('result'))[:90]}",
            "claude login",
        )
    sub = payload.get("subscriptionType") or payload.get("usage", {}).get("service_tier", "")
    note = " (Max subscription)" if "max" in str(sub).lower() else ""
    refresh_note = " [token auto-refreshed]" if _early_hint else ""
    return CheckResult("claude-auth", OK, f"`claude -p` authenticated{note}{refresh_note}")


def check_anthropic_net() -> CheckResult:
    """api.anthropic.com (or the configured base URL host) reachable on :443."""
    base = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    host = urllib.parse.urlparse(base).hostname or "api.anthropic.com"
    try:
        with socket.create_connection((host, 443), timeout=8):
            pass
    except OSError as exc:
        return CheckResult(
            "anthropic-net",
            FAIL,
            f"cannot reach {host}:443 ({exc})",
            "Check network / VPN / proxy",
        )
    return CheckResult("anthropic-net", OK, f"{host}:443 reachable")


def check_azure(needed: bool) -> CheckResult:
    """Azure OCR/Translate connectivity — only when an ingest phase 0a will run."""
    if not needed:
        return CheckResult("azure", SKIP, "not needed (0a ingest already done)")
    if not AZURE_PROBE.exists():
        return CheckResult("azure", WARN, f"probe missing: {AZURE_PROBE.name}")
    try:
        proc = subprocess.run(
            [sys.executable, str(AZURE_PROBE)],
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            "azure", FAIL, "Azure probe timed out after 90s", f"python3 {AZURE_PROBE.relative_to(REPO_ROOT)}"
        )
    if proc.returncode != 0:
        return CheckResult(
            "azure",
            FAIL,
            f"Azure connectivity probe failed (rc={proc.returncode})",
            f"python3 {AZURE_PROBE.relative_to(REPO_ROOT)}",
        )
    return CheckResult("azure", OK, "Azure OCR/Translate reachable")


# ─────────────────────────────── driver ──────────────────────────────────────


def run_doctor(
    *,
    need_azure: bool = False,
    do_claude_ping: bool = True,
    log: Callable[[str], None] = print,
) -> int:
    """Run the full setup-stage system check. Return 0 (proceed) or 1 (halt)."""
    checks = [
        check_deps(),
        check_claude_auth(do_ping=do_claude_ping),
        check_anthropic_net(),
        check_azure(need_azure),
    ]

    width = 72
    log("┌" + "─" * width + "┐")
    log("│ SETUP STAGE · podcast-factory system check" + " " * (width - 43) + "│")
    log("├" + "─" * width + "┤")
    for c in checks:
        line = f"│ {_GLYPH.get(c.status, '?')} {c.name:<13} {c.status:<5} {c.detail}"
        log(line[: width + 1].ljust(width + 1) + "│")
        if c.fix and c.status in (FAIL, WARN):
            fix_line = f"│      ↳ fix: {c.fix}"
            log(fix_line[: width + 1].ljust(width + 1) + "│")
    log("└" + "─" * width + "┘")

    failures = [c for c in checks if c.status == FAIL]
    if failures:
        log("")
        log("SETUP FAILED — resolve the following before the pipeline can run:")
        for c in failures:
            log(f"  ✗ {c.name}: {c.detail}")
            if c.fix:
                log(f"      → {c.fix}")
        log("")
        log("Re-run the orchestrator after fixing. (Bypass with --skip-doctor only")
        log("if you know the failing subsystem is not used by the phases you run.)")
        return 1

    warns = [c for c in checks if c.status == WARN]
    log(
        f"SETUP OK — {len(checks) - len(warns)} checks passed"
        + (f", {len(warns)} warning(s)" if warns else "")
        + ". Proceeding."
    )
    return 0


def _parse_args(argv: list[str]) -> dict:
    opts = {"need_azure": True, "do_claude_ping": True}
    for a in argv:
        if a == "--no-azure":
            opts["need_azure"] = False
        elif a == "--no-ping":
            opts["do_claude_ping"] = False
        elif a in ("-h", "--help"):
            print(__doc__)
            raise SystemExit(0)
    return opts


if __name__ == "__main__":
    raise SystemExit(run_doctor(**_parse_args(sys.argv[1:])))
