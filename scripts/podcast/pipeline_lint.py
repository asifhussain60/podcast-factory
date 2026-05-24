#!/usr/bin/env python3
"""pipeline_lint.py — deterministic $0 pre-flight gate for per-chapter authoring.

The orchestrator's per_chapter_pass spends ~$1-2 of LLM cost before
build_episode_txt runs and surfaces structural mismatches in the framing.
This script runs every deterministic check build_episode_txt enforces
WITHOUT calling any LLM, so the author can iterate on the structural
fit at zero cost before the orchestrator commits to a real per-chapter
authoring cycle.

USAGE

  # Lint one episode's chapter + framing pair:
  python3 scripts/podcast/pipeline_lint.py \\
      --book-dir content/drafts/the-master-and-the-disciple \\
      --episode  EP05-father-revealed-and-the-faces-of-seeking

  # Lint every episode's chapter + framing in a book:
  python3 scripts/podcast/pipeline_lint.py \\
      --book-dir content/drafts/the-master-and-the-disciple --all

  # JSON output for orchestrator consumption:
  python3 scripts/podcast/pipeline_lint.py --book-dir ... --episode ... --json

EXIT CODES

  0  — all P0 + structural checks passed (P1 FLAGs may exist; non-blocking)
  1  — at least one P0 check failed; build would refuse
  2  — couldn't run (missing chapter, missing framing, etc.)

WHAT IT CHECKS (the framing + chapter pair)

  Framing structural:
    - `## Pronunciation` section present with imperative lines
    - `## Do not` DENY block present with required phrases
    - R-NO-READ-PROMPT closing guard
    - Word band [150, 3700]
    - Required structural sections (name discipline, dramatic arc, etc.)
  Chapter content:
    - No inline phonetics (R-PHONETICS-OUT)
    - No meta-prose tells
    - No HTML comments
    - No honorific repetition
    - No manuscript-meta editorial
    - Doctrinal scan (T3 forbidden phrases)
  Contract (if debate-mode):
    - Host role parity (Q4)
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))


def _run_check(check_name: str, fn, *args) -> dict:
    """Run a build_episode_txt assertion; capture stdout/stderr/exit.

    Returns a finding dict with severity P0 (sys.exit fired) or P1 (FLAG emitted).
    """
    captured_out = io.StringIO()
    captured_err = io.StringIO()
    exit_code = None
    exit_msg = ""
    try:
        with redirect_stdout(captured_out), redirect_stderr(captured_err):
            fn(*args)
    except SystemExit as e:
        exit_code = e.code if isinstance(e.code, int) else 1
        exit_msg = str(e) if not isinstance(e.code, int) else (captured_err.getvalue() or captured_out.getvalue())
    except Exception as e:
        exit_code = 99
        exit_msg = f"{type(e).__name__}: {e}"
    stderr = captured_err.getvalue()
    # P1 FLAGs are written to stderr without sys.exit
    p1_flags = [ln for ln in stderr.splitlines() if ln.startswith("FLAG (P1)")]
    severity = None
    msg = ""
    if exit_code:
        severity = "P0"
        msg = exit_msg or stderr or captured_out.getvalue() or f"rc={exit_code}"
    elif p1_flags:
        severity = "P1"
        msg = "\n".join(p1_flags)
    if severity:
        return {
            "check": check_name,
            "severity": severity,
            "message": msg.strip()[:1500],
        }
    return None


def lint_chapter_and_framing(book_dir: Path, episode_id: str) -> dict:
    """Run every applicable build_episode_txt assertion. Return a report dict."""
    import build_episode_txt as B

    # Resolve files (mirror build's logic)
    ch_num, ch_slug = (None, None)
    m = re.match(r"^EP(\d+)-(.+)$", episode_id)
    if m:
        ch_num, ch_slug = int(m.group(1)), m.group(2)
    chapters_dir = book_dir / "chapters"
    framing_path = book_dir / "_system" / "episode-drafts" / episode_id / "00-framing.md"

    findings: list[dict] = []
    inventory: dict = {
        "book_dir": str(book_dir.relative_to(Path.cwd()) if str(book_dir).startswith(str(Path.cwd())) else book_dir),
        "episode_id": episode_id,
        "chapter_resolved": None,
        "framing_resolved": None,
    }

    # Chapter resolution
    chapter_path = None
    if ch_slug:
        for p in chapters_dir.glob(f"ch*-{ch_slug}.txt"):
            chapter_path = p
            break
    if not chapter_path or not chapter_path.exists():
        return {
            "verdict": "BLOCKED",
            "findings": [{"check": "resolve-chapter", "severity": "P0",
                          "message": f"chapter file matching ch*-{ch_slug}.txt not found in {chapters_dir}"}],
            "inventory": inventory,
        }
    inventory["chapter_resolved"] = str(chapter_path.relative_to(book_dir))
    chapter_text = chapter_path.read_text(encoding="utf-8")

    # Chapter-side checks
    for name, fn, args in [
        ("chapter.no-meta-prose", B.assert_no_meta_prose, (chapter_text, chapter_path, "chapter (SOURCE)")),
        ("chapter.no-html-comments", B.assert_no_html_comments, (chapter_text, chapter_path, "chapter (SOURCE)")),
        ("chapter.no-inline-phonetics", B.assert_no_inline_phonetics, (chapter_text, chapter_path)),
        ("chapter.no-abbreviations", B.assert_no_abbreviations, (chapter_text, chapter_path)),
        ("chapter.no-arabic-transliteration", B.assert_no_arabic_transliteration, (chapter_text, chapter_path, "chapter (SOURCE)")),
        ("chapter.no-arabic-surah-names", B.assert_no_arabic_surah_names, (chapter_text, chapter_path, "chapter (SOURCE)")),
        ("chapter.no-manuscript-meta", B.assert_chapter_no_manuscript_meta, (chapter_text, chapter_path)),
        ("chapter.doctrinal-clean", B.assert_doctrinal_clean, (chapter_text, chapter_path)),
    ]:
        f = _run_check(name, fn, *args)
        if f:
            findings.append(f)

    # Framing checks
    if not framing_path.exists():
        findings.append({"check": "resolve-framing", "severity": "P0",
                         "message": f"framing not found at {framing_path}"})
    else:
        inventory["framing_resolved"] = str(framing_path.relative_to(book_dir))
        framing_text = framing_path.read_text(encoding="utf-8")
        # Strip HTML comments + Upload checklist tail before checks (same as build's prep)
        cleaned = re.sub(r"<!--.*?-->", "", framing_text, flags=re.DOTALL)
        cleaned = re.sub(r"\n##\s+Upload\s+checklist.*?$", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
        for name, fn, args in [
            ("framing.no-html-comments", B.assert_no_html_comments, (framing_text, framing_path, "framing (CUSTOMIZE PROMPT)")),
            ("framing.pronunciation-imperative", B.assert_framing_pronunciation_imperative, (cleaned, framing_path)),
            ("framing.deny-block", B.assert_framing_deny_block, (cleaned, framing_path)),
            ("framing.no-modern-artifacts", B.assert_framing_no_modern_artifacts, (cleaned, framing_path)),
            ("framing.honorific-bounded", B.assert_framing_honorific_bounded_both_sides, (cleaned, framing_path)),
            ("framing.no-arabic-surah-names", B.assert_no_arabic_surah_names, (cleaned, framing_path, "framing (CUSTOMIZE PROMPT)")),
            ("framing.alqaab-paraphrased", B.assert_alqaab_only_established_or_paraphrased, (cleaned, framing_path, "framing (CUSTOMIZE PROMPT)")),
            ("framing.name-discipline-section", B.assert_framing_has_name_discipline_section, (cleaned, framing_path)),
            ("framing.dramatic-arc-structure", B.assert_framing_dramatic_arc_structure, (cleaned, framing_path)),
            ("framing.challenger-friction-patterns", B.assert_framing_challenger_friction_lists_patterns, (cleaned, framing_path)),
            ("framing.analogy-cap-declared", B.assert_framing_analogy_cap_declared, (cleaned, framing_path)),
            ("framing.analogy-cap-strict", B.assert_framing_analogy_cap_strict, (cleaned, framing_path)),
        ]:
            f = _run_check(name, fn, *args)
            if f:
                findings.append(f)
        # Word band
        n = len(cleaned.split())
        if n < B.FRAMING_WORD_MIN or n > B.FRAMING_WORD_MAX:
            findings.append({
                "check": "framing.word-band",
                "severity": "P0",
                "message": f"framing word count {n} outside [{B.FRAMING_WORD_MIN}, {B.FRAMING_WORD_MAX}]",
            })

    # Contract-side checks (debate mode → host role parity)
    contracts_dir = book_dir / "chapter-contracts"
    contract_path = contracts_dir / f"{ch_slug}.yml" if ch_slug else None
    if contract_path and contract_path.exists():
        # Minimal YAML read for debate block
        ct = contract_path.read_text(encoding="utf-8")
        if "episode_format: debate" in ct:
            contract = _parse_debate_block(ct)
            host_findings = B.validate_host_role_parity(contract)
            for hf in host_findings:
                findings.append({"check": "contract.host-role-parity", "severity": "P0", "message": hf})

    # Compute verdict
    p0 = [f for f in findings if f["severity"] == "P0"]
    p1 = [f for f in findings if f["severity"] == "P1"]
    if p0:
        verdict = "BLOCKED"
    elif p1:
        verdict = "SHIP-WITH-CAUTION"
    else:
        verdict = "SHIP-READY"

    return {
        "verdict": verdict,
        "p0_count": len(p0),
        "p1_count": len(p1),
        "findings": findings,
        "inventory": inventory,
    }


def _parse_debate_block(yaml_text: str) -> dict:
    """Minimal parser to extract contract.debate.host_a.role + host_b.role."""
    debate = {"host_a": {}, "host_b": {}}
    in_debate = False
    current_host = None
    for line in yaml_text.splitlines():
        if line.startswith("debate:"):
            in_debate = True
            continue
        if in_debate and line.startswith(("  host_a:", "  host_b:")):
            current_host = "host_a" if "host_a" in line else "host_b"
            continue
        if in_debate and current_host and line.startswith("    role:"):
            role = line.split(":", 1)[1].strip().strip('"').strip("'")
            debate[current_host]["role"] = role
            current_host = None
        if in_debate and not line.startswith((" ", "\t")) and line.strip():
            break
    return {"debate": debate}


def _print_report_text(report: dict) -> None:
    inv = report["inventory"]
    print(f"book: {inv['book_dir']}")
    print(f"episode: {inv['episode_id']}")
    print(f"chapter: {inv['chapter_resolved'] or 'NOT-RESOLVED'}")
    print(f"framing: {inv['framing_resolved'] or 'NOT-RESOLVED'}")
    print(f"verdict: {report['verdict']}  ({report.get('p0_count', 0)} P0, {report.get('p1_count', 0)} P1)")
    print()
    for f in report["findings"]:
        sev = f["severity"]
        marker = "✗" if sev == "P0" else "⚠"
        msg_first_line = f["message"].splitlines()[0] if f["message"] else ""
        print(f"  {marker} [{sev}] {f['check']}: {msg_first_line[:140]}")
    print()
    if report["verdict"] != "SHIP-READY":
        print("Detail follows. See each check's documentation in build_episode_txt.py.")
        print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--book-dir", required=True, type=Path)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--episode", help="EP##-<slug>")
    g.add_argument("--all", action="store_true", help="Every episode in book.")
    ap.add_argument("--json", action="store_true", help="Emit JSON report (for orchestrator consumption).")
    args = ap.parse_args()

    book_dir: Path = args.book_dir.resolve()
    if not book_dir.is_dir():
        sys.stderr.write(f"book-dir not found: {book_dir}\n")
        return 2

    if args.all:
        ep_dir = book_dir / "_system" / "episode-drafts"
        episodes = sorted(p.name for p in ep_dir.iterdir() if p.is_dir() and p.name.startswith("EP"))
    else:
        episodes = [args.episode]

    overall_rc = 0
    reports = []
    for ep_id in episodes:
        report = lint_chapter_and_framing(book_dir, ep_id)
        reports.append(report)
        if report["verdict"] == "BLOCKED":
            overall_rc = 1
        if not args.json:
            _print_report_text(report)
            print("─" * 72)

    if args.json:
        print(json.dumps(reports if args.all else reports[0], indent=2))

    return overall_rc


if __name__ == "__main__":
    sys.exit(main())
