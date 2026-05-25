#!/usr/bin/env python3
"""audit_bundle_gemini.py — Gemini-API mirror of audit_bundle.py.

Same Gem prompt, same JSON output schema as [audit_bundle.py](audit_bundle.py),
but hits the Gemini API directly instead of shelling out to `claude -p`. The
two scripts are interchangeable from the orchestrator's perspective; running
both per chapter gives a two-model audit gate.

USAGE

    python3 scripts/podcast/audit_bundle_gemini.py <bundle_dir>
    python3 scripts/podcast/audit_bundle_gemini.py --packed <packed.md>
    python3 scripts/podcast/audit_bundle_gemini.py <bundle_dir> --json-only
    python3 scripts/podcast/audit_bundle_gemini.py <bundle_dir> --model gemini-2.5-pro

EXIT CODES

  0 = audit ran, output written
  1 = invalid input
  2 = Gemini API call failed
  3 = output parsing failed (no claude-code-fixes block)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GEM_PROMPT_PATH = REPO_ROOT / "prompts" / "gemini-bundle-auditor.md"
DEFAULT_MODEL = "gemini-2.5-pro"
KEYCHAIN_SERVICE = "gemini_api_key"


class AuditError(RuntimeError):
    """Raised when the audit cannot complete."""


def _load_gem_prompt() -> str:
    if not GEM_PROMPT_PATH.exists():
        raise AuditError(f"Gem prompt file not found at {GEM_PROMPT_PATH}.")
    raw = GEM_PROMPT_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"##\s+BEGIN GEM PROMPT\s*\n(.*?)\n##\s+END GEM PROMPT",
        raw,
        re.DOTALL,
    )
    if not match:
        raise AuditError(f"BEGIN/END GEM PROMPT markers missing in {GEM_PROMPT_PATH}.")
    return match.group(1).strip()


def _load_api_key() -> str:
    """Read the Gemini API key from macOS keychain.

    Mirrors the Azure-key pattern used elsewhere in this repo — no env vars,
    no .env files. The key lives in keychain under service=`gemini_api_key`.
    """
    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env_key:
        return env_key.strip()
    user = os.environ.get("USER", "")
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", user, "-w"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AuditError("`security` CLI not found. Are you on macOS?") from exc
    if result.returncode != 0:
        raise AuditError(
            f"Could not read keychain entry service={KEYCHAIN_SERVICE} account={user}. "
            f"Add it with: security add-generic-password -s {KEYCHAIN_SERVICE} -a $USER -w <key>"
        )
    return result.stdout.strip()


def _pack_bundle_inline(bundle_dir: Path) -> Path:
    from importlib.util import spec_from_file_location, module_from_spec

    packer_path = Path(__file__).resolve().parent / "pack_bundle_for_gemini.py"
    spec = spec_from_file_location("pack_bundle_for_gemini", packer_path)
    if spec is None or spec.loader is None:
        raise AuditError(f"Cannot import packer from {packer_path}")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    tmp = Path(tempfile.mkdtemp(prefix="audit-bundle-gemini-")) / f"{bundle_dir.name}.packed.md"
    rc = mod.pack(bundle_dir=bundle_dir, out_path=tmp, include_pdfs=False, max_mb=90)
    if rc not in (0, 2):
        raise AuditError(f"packer exited with code {rc}")
    return tmp


def _run_gemini(system_prompt: str, packed_text: str, model: str, timeout: int = 600) -> str:
    """Call Gemini with the Gem prompt as system_instruction + packed bundle as user content."""
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise AuditError(
            "google-genai SDK not installed. Run: pip3 install google-genai"
        ) from exc

    api_key = _load_api_key()
    client = genai.Client(api_key=api_key)

    user_content = (
        "## Consolidated bundle (input)\n\n"
        + packed_text
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.2,
            ),
        )
    except Exception as exc:
        raise AuditError(f"Gemini API call failed: {exc}") from exc

    if not response.text:
        raise AuditError("Gemini returned an empty response.")
    return response.text


def _extract_fixes_json(audit_md: str) -> list[dict]:
    match = re.search(
        r"```claude-code-fixes\s*\n(.*?)\n```",
        audit_md,
        re.DOTALL,
    )
    if not match:
        raise AuditError(
            "No `claude-code-fixes` fenced block found in Gemini output. "
            "Either the model deviated from the Gem prompt, or the prompt itself drifted."
        )
    payload = match.group(1).strip()
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise AuditError(f"claude-code-fixes block is not valid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise AuditError("claude-code-fixes block must be a JSON array.")
    return data


def audit_bundle_gemini(
    bundle_dir: Path | None,
    packed_file: Path | None,
    out_path: Path | None,
    json_only: bool,
    model: str,
) -> int:
    if bundle_dir is None and packed_file is None:
        print("error: provide either a bundle_dir or --packed", file=sys.stderr)
        return 1
    if bundle_dir and not bundle_dir.exists():
        print(f"error: bundle directory not found: {bundle_dir}", file=sys.stderr)
        return 1
    if packed_file and not packed_file.exists():
        print(f"error: packed file not found: {packed_file}", file=sys.stderr)
        return 1

    try:
        gem_prompt = _load_gem_prompt()
        if packed_file is None:
            assert bundle_dir is not None
            packed_file = _pack_bundle_inline(bundle_dir)
            print(f"packed bundle to {packed_file}", file=sys.stderr)
        packed_text = packed_file.read_text(encoding="utf-8")
        print(f"calling Gemini ({model})...", file=sys.stderr)
        audit_md = _run_gemini(gem_prompt, packed_text, model)
        fixes = _extract_fixes_json(audit_md)
    except AuditError as exc:
        print(f"audit failed: {exc}", file=sys.stderr)
        msg = str(exc).lower()
        if "gemini api call failed" in msg or "empty response" in msg:
            return 2
        if "claude-code-fixes" in msg or "begin/end gem prompt" in msg:
            return 3
        return 1

    if json_only:
        sys.stdout.write(json.dumps(fixes, indent=2) + "\n")
    else:
        if out_path is None:
            if bundle_dir is not None:
                out_path = bundle_dir.parent / f"{bundle_dir.name}.gemini-audit.md"
            else:
                assert packed_file is not None
                out_path = packed_file.with_suffix(".gemini-audit.md")
        out_path.write_text(audit_md, encoding="utf-8")
        print(f"wrote Gemini audit report to {out_path}")
        print(f"  findings: {len(fixes)}")
        sev: dict = {}
        for f in fixes:
            sev[f.get("severity", "?")] = sev.get(f.get("severity", "?"), 0) + 1
        if sev:
            summary = ", ".join(f"{k}={v}" for k, v in sorted(sev.items()))
            print(f"  by severity: {summary}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit a podcast bundle for NotebookLM-ready quality using Gemini.",
    )
    parser.add_argument("bundle_dir", type=Path, nargs="?", default=None)
    parser.add_argument("--packed", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--json-only", action="store_true")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Gemini model (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    return audit_bundle_gemini(
        bundle_dir=args.bundle_dir.resolve() if args.bundle_dir else None,
        packed_file=args.packed.resolve() if args.packed else None,
        out_path=args.out.resolve() if args.out else None,
        json_only=args.json_only,
        model=args.model,
    )


if __name__ == "__main__":
    sys.exit(main())
