"""_cloudflare_preflight.py — prove the Cloudflare token can do the job BEFORE a publish starts.

2026-09-19 (isaf-al-talib): every remote read and write returned "Authentication error
[code: 10000]" from deep inside publish. `wrangler whoami` still succeeded — the token was real,
just not permitted to touch D1 or R2 — and the existing account check (`account_ok`) can only see
the first half of that. So this probes the three things a publish actually needs, one cheap
read-only call each: the account, the database, the media bucket. It runs ALL three even when one
fails (one report shows everything wrong), turns Cloudflare's error text into a remedy, and never
prints the token.

The token itself is Asif's to mint and store; nothing here enters or rotates a credential.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from _production_publish import ACCOUNT_ID, ACCOUNT_NAME, KEYCHAIN_SERVICE
from _wrangler import run as _wrangler_run

DB_NAME = "podcast-listener"
PROBE_TIMEOUT = 60.0
_TOKEN_SHAPE = re.compile(r"[A-Za-z0-9_-]{40}")
_ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
RUNBOOK = "infra/cloudflare/README.md (section: Rotating the API token)"


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str = ""


@dataclass(frozen=True)
class Result:
    checks: tuple[Check, ...]
    secret: str = ""

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)

    def explain(self) -> str:
        """A plain-language report of what failed and what to do. Empty only when everything passed."""
        failed = [c for c in self.checks if not c.ok]
        if not failed:
            return ""
        lines = ["Cloudflare is not ready for a remote publish:"]
        remedies: list[str] = []
        for c in failed:
            lines.append(f"  ✗ {c.name}: {c.detail or 'failed without saying why'}")
            r = remedy_for(c.detail)
            if r not in remedies:
                remedies.append(r)
        lines.append("What to do:")
        lines.extend(f"  - {r}" for r in remedies)
        return "\n".join(lines)


def _scrub(text: str, secret: str) -> str:
    return text.replace(secret, "«token»") if secret else text


def token_shape_problem(token: str) -> str | None:
    """None when `token` looks like a Cloudflare API token; else why it cannot be one.

    Purely local. isaf-al-talib, 2026-09-19: the keychain item held 13 characters — an API token is
    exactly 40 — and the only symptom was three different error codes from three different calls.
    Only the LENGTH is ever reported, never any part of the value.
    """
    if _TOKEN_SHAPE.fullmatch(token):
        return None
    return (
        f"the stored token is {len(token)} characters or contains characters an API token never has; a Cloudflare "
        "API token is exactly 40 letters, digits, '-' and '_'. The keychain item holds something else "
        "(a truncated paste, quotes, a 'Bearer ' prefix, a placeholder, or a different credential)"
    )


def _summary(proc: "subprocess.CompletedProcess[str]", secret: str) -> str:
    text = _ANSI.sub("", _scrub((proc.stderr or proc.stdout or "").strip(), secret))
    return " ".join(text.split())[:240] or "no output"


def remedy_for(detail: str) -> str:
    low = detail.lower()
    if "api token is exactly 40" in low:
        return (
            "re-store the real token. Create it as in the runbook, then store it with the prompt form so it never "
            f'touches shell history: security add-generic-password -U -a "$USER" -s {KEYCHAIN_SERVICE} -w — '
            f"then verify: python3 scripts/podcast/_cloudflare_preflight.py. Steps: {RUNBOOK}."
        )
    if "10000" in low or "authentication error" in low:
        return (
            "Cloudflare recognised the token but refused it — it is missing PERMISSION. Mint a token limited to "
            f"the {ACCOUNT_NAME} account with: D1 Edit, Workers R2 Storage Edit, Workers Scripts Edit. "
            f"Rotation steps: {RUNBOOK}."
        )
    if "6111" in low or "invalid format" in low:
        return (
            "the stored token has stray whitespace or a newline in it. Re-store it with the prompt form so the "
            f'value never touches shell history: security add-generic-password -U -a "$USER" -s {KEYCHAIN_SERVICE} -w'
        )
    if "did not answer" in low or "timed out" in low:
        return "Cloudflare did not answer in time — check the network, then re-run. Nothing was written."
    if "another account" in low or "does not resolve" in low:
        return (
            f"the token belongs to a different Cloudflare account. It must resolve to {ACCOUNT_NAME} "
            f"(the one that holds safinaverse.com). Rotation steps: {RUNBOOK}."
        )
    return f"read the message above, then see {RUNBOOK}."


def check_remote_access(env: dict[str, str], listener_dir: Path, *, run=_wrangler_run) -> Result:
    """Probe account, database and media bucket. Never raises; never writes; never prints the token."""
    secret = env.get("CLOUDFLARE_API_TOKEN", "")
    shape = token_shape_problem(secret)
    if shape:  # cannot be a valid token: do not send it anywhere
        return Result((Check("token", False, shape),), secret)
    probes = (
        ("account", ["npx", "wrangler", "whoami"]),
        (
            "database",
            ["npx", "wrangler", "d1", "execute", DB_NAME, "--remote", "--command", "SELECT 1 AS ok;"],
        ),
        ("storage", ["npx", "wrangler", "r2", "bucket", "list"]),
    )
    checks: list[Check] = []
    for name, argv in probes:
        try:
            proc = run(argv, cwd=str(listener_dir), env=env, timeout=PROBE_TIMEOUT)
        except (OSError, subprocess.SubprocessError) as error:
            checks.append(Check(name, False, _scrub(f"Cloudflare did not answer: {error}", secret)))
            continue
        if name == "account" and proc.returncode == 0 and ACCOUNT_ID not in (proc.stdout or ""):
            checks.append(Check(name, False, f"the token does not resolve to {ACCOUNT_NAME} (another account)"))
        elif proc.returncode != 0:
            checks.append(Check(name, False, _summary(proc, secret)))
        else:
            checks.append(Check(name, True))
    return Result(tuple(checks), secret)


def require_remote_access(listener_dir: Path, env: dict[str, str] | None = None) -> None:
    """Raise RuntimeError with the full report unless every probe passes. Call before any remote step."""
    if env is None:
        from _production_publish import cloudflare_env

        env = cloudflare_env()
    result = check_remote_access(env, listener_dir)
    if not result.ok:
        raise RuntimeError(result.explain())


def prepare_remote(listener_dir: Path) -> str | None:
    """Resolve the token into os.environ and prove it works. None = ready; else the report to print.

    The one call every remote entry point makes, in place of the eight-line
    `cloudflare_env()` + `account_ok()` block each of them used to repeat.
    """
    import os

    from _production_publish import cloudflare_env

    try:
        env = cloudflare_env()
    except RuntimeError as error:
        return str(error)
    os.environ.update(env)
    result = check_remote_access(dict(os.environ), listener_dir)
    return None if result.ok else result.explain()


def main() -> int:
    listener = Path(__file__).resolve().parents[2] / "listener"
    try:
        require_remote_access(listener)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2
    print("cloudflare preflight: ok (account, database, storage)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
