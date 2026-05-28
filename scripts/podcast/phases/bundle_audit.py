"""phases/bundle_audit.py — Phase 0g dual-auditor bundle sweep (F30).

Extracted from orchestrate_book.py (A4 split). Authority: plan.md §A4.

Exports:
  _gemini_key_available   — probe macOS keychain for Gemini API key
  phase_0g_audit_bundles  — run Claude + Gemini auditors over every chapter bundle
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _paths import REPO_ROOT  # noqa: E402

AUDIT_BUNDLE_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "audit_bundle.py"
AUDIT_BUNDLE_GEMINI_SCRIPT = REPO_ROOT / "scripts" / "podcast" / "audit_bundle_gemini.py"


def _info(msg: str) -> None:
    print(msg)


def _err(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)


def _gemini_key_available() -> bool:
    """Check whether Gemini API key exists in macOS keychain."""
    try:
        proc = subprocess.run(
            ["security", "find-generic-password", "-s", "gemini_api_key"],
            capture_output=True, text=True, timeout=5,
        )
        return proc.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def phase_0g_audit_bundles(book_dir: Path, chapter_slugs: list[str]) -> dict:
    """Run dual auditor (Claude + Gemini) against every per-chapter bundle.

    For each completed chapter EP##-<slug>, locates the bundle at
    BOOK_DIR/_system/episode-drafts/EP##-<slug>/, shells out to both
    audit_bundle.py and audit_bundle_gemini.py in parallel. Reports land in
    BOOK_DIR/audits/<EP-slug>.audit.{claude,gemini}.md.

    Idempotent: skip a chapter if both reports are newer than bundle's framing.md.
    Returns a per-chapter outcome dict for the summary write.
    """
    drafts_dir = book_dir / "_system" / "episode-drafts"
    audits_dir = book_dir / "audits"
    audits_dir.mkdir(parents=True, exist_ok=True)
    gemini_ok = _gemini_key_available()
    if not gemini_ok:
        _info(
            "  gemini key not found in keychain (service=gemini_api_key); "
            "skipping Gemini auditor (Claude auditor still runs)."
        )

    outcomes: dict[str, dict] = {}
    for slug in chapter_slugs:
        bundle_dir = next(
            (d for d in sorted(drafts_dir.glob("EP*")) if d.name.endswith(f"-{slug}")),
            None,
        )
        if bundle_dir is None or not bundle_dir.is_dir():
            outcomes[slug] = {"status": "missing-bundle", "p0": 0, "p1": 0, "p2": 0}
            _info(f"  [{slug}] no bundle dir under {drafts_dir.relative_to(book_dir)} — skipped")
            continue

        ep_label = bundle_dir.name
        claude_audit = audits_dir / f"{ep_label}.audit.claude.md"
        gemini_audit = audits_dir / f"{ep_label}.audit.gemini.md"

        framing = bundle_dir / "00-framing.md"
        framing_mtime = framing.stat().st_mtime if framing.exists() else 0.0
        both_fresh = (
            claude_audit.exists() and claude_audit.stat().st_mtime > framing_mtime
            and (
                not gemini_ok
                or (gemini_audit.exists() and gemini_audit.stat().st_mtime > framing_mtime)
            )
        )
        if both_fresh:
            _info(f"  [{slug}] audits up-to-date, skipping")
            outcomes[slug] = {"status": "skipped-fresh"}
            continue

        _info(f"  [{slug}] auditing bundle {bundle_dir.name}/ (Claude{' + Gemini' if gemini_ok else ''})")

        procs: list[tuple[str, subprocess.Popen]] = []
        procs.append((
            "claude",
            subprocess.Popen(
                [sys.executable, str(AUDIT_BUNDLE_SCRIPT), str(bundle_dir),
                 "--out", str(claude_audit)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            ),
        ))
        if gemini_ok:
            procs.append((
                "gemini",
                subprocess.Popen(
                    [sys.executable, str(AUDIT_BUNDLE_GEMINI_SCRIPT), str(bundle_dir),
                     "--out", str(gemini_audit)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                ),
            ))

        per_auditor: dict[str, dict] = {}
        for name, p in procs:
            try:
                out, err = p.communicate(timeout=900)
            except subprocess.TimeoutExpired:
                p.kill()
                per_auditor[name] = {"rc": -1, "error": "timeout-900s"}
                continue
            per_auditor[name] = {"rc": p.returncode, "stderr": err.strip()[-400:] if err else ""}

        sev_total = {"p0": 0, "p1": 0, "p2": 0}
        for name, report_path in (("claude", claude_audit), ("gemini", gemini_audit)):
            if name not in per_auditor or per_auditor[name].get("rc") != 0 or not report_path.exists():
                continue
            try:
                text = report_path.read_text(encoding="utf-8")
                m = re.search(r"```claude-code-fixes\s*\n(.*?)\n```", text, re.DOTALL)
                if not m:
                    continue
                fixes = json.loads(m.group(1).strip())
                for f in fixes:
                    sev = str(f.get("severity", "")).lower()
                    if sev in ("p0", "critical"):
                        sev_total["p0"] += 1
                    elif sev in ("p1", "high"):
                        sev_total["p1"] += 1
                    elif sev in ("p2", "medium", "low"):
                        sev_total["p2"] += 1
            except (json.JSONDecodeError, OSError):
                continue

        outcomes[slug] = {
            "status": "audited",
            "ep_label": ep_label,
            "claude_rc": per_auditor.get("claude", {}).get("rc"),
            "gemini_rc": per_auditor.get("gemini", {}).get("rc"),
            **sev_total,
        }
        _info(
            f"  [{slug}] done · P0={sev_total['p0']} P1={sev_total['p1']} P2={sev_total['p2']}"
        )

    summary = audits_dir / "0g-audit-summary.md"
    lines = [
        f"# Phase 0g bundle-audit summary — {book_dir.name}",
        "",
        "Dual-auditor sweep (Claude + Gemini) over every per-chapter NotebookLM bundle.",
        "Findings are informational — review at finalize halt before publish.",
        "",
        "| Episode | Status | Claude rc | Gemini rc | P0 | P1 | P2 |",
        "|---|---|---|---|---|---|---|",
    ]
    for slug, o in outcomes.items():
        if o.get("status") != "audited":
            lines.append(f"| `{slug}` | {o.get('status')} | — | — | — | — | — |")
            continue
        lines.append(
            f"| `{o['ep_label']}` | audited | {o.get('claude_rc')} | "
            f"{o.get('gemini_rc') if o.get('gemini_rc') is not None else '—'} | "
            f"{o.get('p0', 0)} | {o.get('p1', 0)} | {o.get('p2', 0)} |"
        )
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _info(f"  wrote audit summary: {summary.relative_to(book_dir)}")
    return outcomes
