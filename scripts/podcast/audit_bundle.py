#!/usr/bin/env python3
"""audit_bundle.py — Claude-native podcast-bundle auditor mirror of the Gemini Gem.

Same rubric, same JSON output schema as the Gemini 'Podcast Bundle Auditor'
Gem (see [_workspace/prompts/gemini-bundle-auditor.md](../../_workspace/prompts/gemini-bundle-auditor.md)),
but runs against a bundle directory locally via `claude -p` (Claude Code
headless mode) — the same LLM-shellout pattern already used by the rest of the
podcast pipeline (see [_authoring.py](_authoring.py)).

This script is the in-repo half of the dual-auditor design:

  * `pack_bundle_for_gemini.py` + the Gem  →  cross-model audit, same family
    as NotebookLM's hosts, requires a manual upload/copy-paste round-trip.
  * `audit_bundle.py`                     →  same-model audit, no round-trip,
    integrates with the orchestrator phase ladder (intended future slot:
    optional phase 0g, between enrich and the review halt).

USAGE

    # Audit any bundle directory; emit the markdown audit + claude-code-fixes JSON.
    python3 scripts/podcast/audit_bundle.py <bundle_dir>

    # Just the JSON fix list (suitable for piping into Claude Code).
    python3 scripts/podcast/audit_bundle.py <bundle_dir> --json-only

    # Audit a previously packed consolidated file (skip the pack step).
    python3 scripts/podcast/audit_bundle.py --packed <packed.md>

    # Write the audit report to a specific path.
    python3 scripts/podcast/audit_bundle.py <bundle_dir> --out audit.md

EXIT CODES

  0 = audit ran, output written
  1 = invalid input (bundle missing, packed file missing, etc.)
  2 = claude -p shell-out returned non-zero
  3 = output parsing failed (no claude-code-fixes block found)

DESIGN NOTES

  - The prompt sent to `claude -p` is the exact Gem prompt from
    [_workspace/prompts/gemini-bundle-auditor.md](../../_workspace/prompts/gemini-bundle-auditor.md),
    so any audit-rubric change happens in one place. This script reads that
    file at runtime; if the prompt file is missing the script bails with a
    clear error.

  - The packed-markdown intake format is shared with the Gemini Gem, so the
    same `<!-- FILE: ... -->` virtual-path convention applies — fixes emitted
    by this script point to real files in the bundle directory.

  - The orchestrator integration is intentionally NOT wired up here. To slot
    this in as phase 0g, add a `phase_0g_audit` step to _phases.py and call
    audit_bundle() from there. That's a follow-up change, not part of this
    file.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GEM_PROMPT_PATH = REPO_ROOT / "prompts" / "gemini-bundle-auditor.md"


class AuditError(RuntimeError):
    """Raised when the audit cannot complete."""


def _load_gem_prompt() -> str:
    """Extract the BEGIN/END GEM PROMPT block from the canonical prompt file.

    Keeping the prompt in one place (the .md file) makes the rubric a
    single-source artifact rather than something duplicated in code.
    """
    if not GEM_PROMPT_PATH.exists():
        raise AuditError(
            f"Gem prompt file not found at {GEM_PROMPT_PATH}. "
            f"Restore _workspace/prompts/gemini-bundle-auditor.md before running this audit."
        )
    raw = GEM_PROMPT_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"##\s+BEGIN GEM PROMPT\s*\n(.*?)\n##\s+END GEM PROMPT",
        raw,
        re.DOTALL,
    )
    if not match:
        raise AuditError(
            f"Could not find BEGIN/END GEM PROMPT markers in {GEM_PROMPT_PATH}. "
            f"The prompt file structure has drifted; fix the markers before re-running."
        )
    return match.group(1).strip()


def _pack_bundle_inline(bundle_dir: Path) -> Path:
    """Pack the bundle into a temp consolidated markdown file."""
    from importlib.util import spec_from_file_location, module_from_spec

    packer_path = Path(__file__).resolve().parent / "pack_bundle_for_gemini.py"
    spec = spec_from_file_location("pack_bundle_for_gemini", packer_path)
    if spec is None or spec.loader is None:
        raise AuditError(f"Cannot import packer from {packer_path}")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    tmp = Path(tempfile.mkdtemp(prefix="audit-bundle-")) / f"{bundle_dir.name}.packed.md"
    rc = mod.pack(bundle_dir=bundle_dir, out_path=tmp, include_pdfs=False, max_mb=90)
    if rc not in (0, 2):  # 2 = packed with drops, still usable
        raise AuditError(f"packer exited with code {rc}")
    return tmp


def _run_claude(prompt: str, packed_text: str, timeout: int = 600) -> str:
    """Shell out to `claude -p` with the gem prompt + packed bundle as stdin.

    The pipeline already uses this pattern in [_authoring.py](_authoring.py) for every
    LLM phase — keeping it consistent here means cost ledgers, retries, and
    permissions all behave the same way.
    """
    full_prompt = (
        prompt
        + "\n\n---\n\n"
        + "## Consolidated bundle (input)\n\n"
        + packed_text
    )
    try:
        result = subprocess.run(
            ["claude", "-p", full_prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AuditError(
            "`claude` CLI not on PATH. Install Claude Code or run this from a shell that has it."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise AuditError(f"claude -p timed out after {timeout}s") from exc

    if result.returncode != 0:
        raise AuditError(
            f"claude -p exited with code {result.returncode}.\n"
            f"stderr:\n{result.stderr}"
        )
    return result.stdout


def _extract_fixes_json(audit_md: str) -> list[dict]:
    """Pull the claude-code-fixes JSON array out of the audit markdown."""
    match = re.search(
        r"```claude-code-fixes\s*\n(.*?)\n```",
        audit_md,
        re.DOTALL,
    )
    if not match:
        raise AuditError(
            "No `claude-code-fixes` fenced block found in audit output. "
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


def audit_bundle(
    bundle_dir: Path | None,
    packed_file: Path | None,
    out_path: Path | None,
    json_only: bool,
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
        audit_md = _run_claude(gem_prompt, packed_text)
        fixes = _extract_fixes_json(audit_md)
    except AuditError as exc:
        print(f"audit failed: {exc}", file=sys.stderr)
        # Distinguish prompt/parse errors (3) from claude exit failures (2).
        msg = str(exc).lower()
        if "claude -p exited" in msg or "claude -p timed out" in msg or "claude` cli" in msg:
            return 2
        if "fix list" in msg or "claude-code-fixes" in msg or "begin/end gem prompt" in msg:
            return 3
        return 1

    if json_only:
        sys.stdout.write(json.dumps(fixes, indent=2) + "\n")
    else:
        if out_path is None:
            if bundle_dir is not None:
                out_path = bundle_dir.parent / f"{bundle_dir.name}.audit.md"
            else:
                assert packed_file is not None
                out_path = packed_file.with_suffix(".audit.md")
        out_path.write_text(audit_md, encoding="utf-8")
        print(f"wrote audit report to {out_path}")
        print(f"  findings: {len(fixes)}")
        sev = {}
        for f in fixes:
            sev[f.get("severity", "?")] = sev.get(f.get("severity", "?"), 0) + 1
        if sev:
            summary = ", ".join(f"{k}={v}" for k, v in sorted(sev.items()))
            print(f"  by severity: {summary}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit a podcast bundle for NotebookLM-ready quality using Claude.",
    )
    parser.add_argument(
        "bundle_dir",
        type=Path,
        nargs="?",
        default=None,
        help="Path to the bundle directory. Mutually exclusive with --packed.",
    )
    parser.add_argument(
        "--packed",
        type=Path,
        default=None,
        help="Path to a pre-packed consolidated markdown file. Skips the pack step.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Where to write the audit markdown. Default: <bundle>.audit.md next to the bundle.",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Print only the claude-code-fixes JSON array to stdout (suitable for piping).",
    )
    args = parser.parse_args()

    return audit_bundle(
        bundle_dir=args.bundle_dir.resolve() if args.bundle_dir else None,
        packed_file=args.packed.resolve() if args.packed else None,
        out_path=args.out.resolve() if args.out else None,
        json_only=args.json_only,
    )


if __name__ == "__main__":
    sys.exit(main())
