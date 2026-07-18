#!/usr/bin/env python3
"""tighten_source.py — advisory pass that flags non-essential prose in chapter
source files so NotebookLM gets a tighter signal without losing dialectical
or doctrinal substance.

GOAL: TIGHTEN, NOT SHORTEN

  The objective is density-per-word, not word-count reduction. If a chapter's
  proposed cuts exceed `drastic_reduction_threshold` (default 15%), the
  chapter is RED-FLAGGED in the report — a large cut is a smell, not a win.
  The right outcome is usually 3-10% removal of decorative scaffolding, with
  the dialectical/doctrinal substance fully preserved.

DESIGN

  Per-chapter Claude-judge (Sonnet) reads each chapter and returns candidate
  cuts as JSON in four categories:

    editorial-bridge      — pipeline-added connective tissue
    cross-tradition-import— decorative quotations not in the source text
    restatement           — explicit recap of what was just developed
    meta-narration        — second-person guide voice with no doctrinal content

  After per-chapter passes, a cohesion pass checks whether any proposed cut
  is referenced or set up by a later chapter (so we do not orphan callbacks).

  Output: <book_dir>/_system/tighten-report.md with one section per chapter,
  proposed-diff blocks, accept/reject checkboxes, running word-count delta,
  cohesion warnings inline.

  --apply ch07,ch11   writes <ch>.tightened.txt siblings in chapters/.
                      ONLY cuts marked `- [x]` in tighten-report.md are
                      applied. Default unchecked = not accepted = not cut.
                      Never overwrites the original.

CONFIG

  Optional per-book config at <book_dir>/_system/tighten-config.yml:
    categories, protect, min_confidence, drastic_reduction_threshold, budget_usd

USAGE

  # Dry-run (no LLM, no writes):
  python3 scripts/podcast/tighten_source.py \\
      --book-dir content/drafts/kitab-al-riyad --dry-run

  # Real per-chapter pass + report:
  python3 scripts/podcast/tighten_source.py \\
      --book-dir content/drafts/kitab-al-riyad

  # Apply two chapters' accepted cuts (advisory; writes .tightened.txt):
  python3 scripts/podcast/tighten_source.py \\
      --book-dir content/drafts/kitab-al-riyad \\
      --apply ch07,ch11

EXIT CODES

  0  — report written; one or more candidates produced
  1  — report written; zero candidates (book is already tight, or LLM failed)
  2  — refused (budget cap, missing chapters/, missing claude CLI)
  3  — bad arguments

SAFETY

  - Advisory by default: NEVER overwrites <ch>.txt; writes .tightened.txt siblings.
  - Protect-list defaults baked in (Imam, Quran, proper names) even with no config.
  - Per-book budget cap default $3.00; refuses past that.
  - Boundary check: refuses if book_dir is not under content/drafts/ or
    content/published/.

Three-file split (DR-005 — files must stay under 600 lines):
  _tighten_helpers.py  — constants, data classes, helpers, prompts, SDK invocation
  tighten_source.py (this) — algorithm (per-chapter / cohesion / apply) + CLI
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

from _tighten_helpers import (
    DEFAULT_DRASTIC_REDUCTION_THRESHOLD,
    EST_COST_COHESION_USD,
    EST_COST_PER_CHAPTER_USD,
    MODEL_COHESION,
    MODEL_PER_CHAPTER,
    ChapterResult,
    CutCandidate,
    append_ledger,
    book_tighten_spend,
    boundary_check,
    build_cohesion_prompt,
    build_per_chapter_prompt,
    extract_json,
    load_cached,
    load_config,
    save_cached,
    source_signature,
    spawn_claude,
)

# --- per-chapter pass ------------------------------------------------------


def run_per_chapter(
    book_dir: Path,
    chapter_path: Path,
    book_title: str,
    book_premise: str,
    cfg: dict,
    force_refresh: bool = False,
    dry_run: bool = False,
) -> ChapterResult:
    chapter_slug = chapter_path.stem
    text = chapter_path.read_text(encoding="utf-8")
    sig = source_signature(text)
    original_words = len(text.split())
    chapter_num = chapter_slug[:4]

    if not force_refresh:
        cached = load_cached(book_dir, chapter_slug, sig)
        if cached is not None:
            return ChapterResult(
                chapter=chapter_slug,
                chapter_path=chapter_path,
                original_words=original_words,
                candidates=cached,
                cached=True,
            )

    if dry_run:
        return ChapterResult(
            chapter=chapter_slug,
            chapter_path=chapter_path,
            original_words=original_words,
            candidates=[],
            error="dry-run (no LLM call)",
        )

    spent = book_tighten_spend(book_dir)
    if spent + EST_COST_PER_CHAPTER_USD > cfg["budget_usd"]:
        return ChapterResult(
            chapter=chapter_slug,
            chapter_path=chapter_path,
            original_words=original_words,
            candidates=[],
            error=f"budget cap reached: spent=${spent:.2f}, cap=${cfg['budget_usd']:.2f}",
        )

    prompt = build_per_chapter_prompt(chapter_path, text, chapter_num, book_title, book_premise, cfg)
    raw = spawn_claude(prompt, MODEL_PER_CHAPTER, book_dir.parent)
    if not raw:
        return ChapterResult(
            chapter=chapter_slug,
            chapter_path=chapter_path,
            original_words=original_words,
            candidates=[],
            error="SDK returned empty (timeout or error)",
        )

    parsed = extract_json(raw)
    if parsed is None or not isinstance(parsed, list):
        return ChapterResult(
            chapter=chapter_slug,
            chapter_path=chapter_path,
            original_words=original_words,
            candidates=[],
            error=f"could not parse JSON from claude (got: {raw[:200]})",
        )

    candidates = []
    for row in parsed:
        try:
            c = CutCandidate(
                chapter=chapter_slug,
                line_start=int(row["line_start"]),
                line_end=int(row["line_end"]),
                anchor_text=str(row["anchor_text"])[:200],
                category=str(row["category"]),
                rationale=str(row["rationale"]),
                confidence=float(row.get("confidence", 0.5)),
                est_words_removed=int(row.get("est_words_removed", 0)),
            )
        except (KeyError, ValueError, TypeError) as e:
            print(f"[tighten] skipping malformed candidate in {chapter_slug}: {e}", file=sys.stderr)
            continue
        if c.confidence < cfg["min_confidence"]:
            continue
        if not cfg["categories"].get(c.category, False):
            continue
        if _trips_protect(c.anchor_text, cfg["protect"]):
            continue
        candidates.append(c)

    append_ledger(book_dir, "tighten/per-chapter", chapter_slug, MODEL_PER_CHAPTER, EST_COST_PER_CHAPTER_USD)
    save_cached(book_dir, chapter_slug, sig, candidates)

    return ChapterResult(
        chapter=chapter_slug,
        chapter_path=chapter_path,
        original_words=original_words,
        candidates=candidates,
    )


def _trips_protect(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        try:
            if re.search(p, text):
                return True
        except re.error:
            if p in text:
                return True
    return False


# --- cohesion pass ---------------------------------------------------------


def run_cohesion(
    book_dir: Path,
    results: list[ChapterResult],
    book_title: str,
    cfg: dict,
    dry_run: bool = False,
) -> None:
    all_candidates = [c for r in results for c in r.candidates]
    if not all_candidates or dry_run:
        return

    spent = book_tighten_spend(book_dir)
    if spent + EST_COST_COHESION_USD > cfg["budget_usd"]:
        print("[tighten] skipping cohesion pass — budget would exceed cap", file=sys.stderr)
        return

    chapters_by_slug = {r.chapter: r.chapter_path.read_text(encoding="utf-8") for r in results}
    prompt = build_cohesion_prompt(all_candidates, chapters_by_slug, book_title)
    raw = spawn_claude(prompt, MODEL_COHESION, book_dir.parent, timeout_sec=300)
    if not raw:
        print("[tighten] cohesion pass returned empty", file=sys.stderr)
        return
    parsed = extract_json(raw)
    if parsed is None or not isinstance(parsed, list):
        print(f"[tighten] cohesion pass: could not parse JSON: {raw[:200]}", file=sys.stderr)
        return
    append_ledger(book_dir, "tighten/cohesion", "cross-chapter", MODEL_COHESION, EST_COST_COHESION_USD)

    for warn in parsed:
        try:
            slug = warn["chapter"]
            anchor = warn["anchor_text"][:60]
            msg = warn["cohesion_warning"]
        except (KeyError, TypeError):
            continue
        for c in all_candidates:
            if c.chapter == slug and c.anchor_text.startswith(anchor[:30]):
                c.cohesion_warning = msg


# --- report rendering ------------------------------------------------------


def render_report(
    book_dir: Path,
    results: list[ChapterResult],
    book_title: str,
    cfg: dict,
) -> Path:
    out = book_dir / "_system" / "tighten-report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# tighten-source report — {book_title}")
    lines.append("")
    lines.append(f"_generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}_")
    lines.append("")
    lines.append("> **Goal: TIGHTEN, not SHORTEN.** This pass flags decorative scaffolding,")
    lines.append("> editorial bridges, and restatement — not load-bearing prose. A chapter")
    lines.append("> with a high proposed-removal % is suspicious, not a win. Healthy")
    lines.append("> tightening is usually 3-10% per chapter.")
    lines.append("")
    lines.append("## At a glance")
    lines.append("")
    total_original = sum(r.original_words for r in results)
    total_proposed = sum(r.proposed_words_removed for r in results)
    pct = (100.0 * total_proposed / total_original) if total_original else 0.0
    n_candidates = sum(len(r.candidates) for r in results)
    n_with_cohesion = sum(1 for r in results for c in r.candidates if c.cohesion_warning)
    threshold = cfg.get("drastic_reduction_threshold", DEFAULT_DRASTIC_REDUCTION_THRESHOLD)
    flagged = [r for r in results if r.original_words > 0 and (r.proposed_words_removed / r.original_words) > threshold]
    lines.append(f"- chapters scanned: **{len(results)}**")
    lines.append(f"- candidate cuts: **{n_candidates}** (of which **{n_with_cohesion}** have cohesion warnings)")
    lines.append(f"- words: original **{total_original:,}**, proposed-removed **{total_proposed:,}** (**{pct:.1f}%**)")
    lines.append(f"- categories enabled: {', '.join(k for k, v in cfg['categories'].items() if v)}")
    lines.append(f"- min_confidence: {cfg['min_confidence']} · drastic-reduction threshold: **{threshold * 100:.0f}%**")
    lines.append(f"- budget: ${book_tighten_spend(book_dir):.2f} / ${cfg['budget_usd']:.2f}")
    lines.append("")
    if flagged:
        lines.append(f"### 🔴 RED-FLAG: chapters exceeding the {threshold * 100:.0f}% drastic-reduction threshold")
        lines.append("")
        lines.append("These chapters propose cutting more than is consistent with 'tightening'.")
        lines.append("Review their candidates carefully — they may be over-flagging substance.")
        lines.append("")
        for r in flagged:
            ratio = (r.proposed_words_removed / r.original_words) if r.original_words else 0
            lines.append(
                f"- **{r.chapter}** — {r.proposed_words_removed:,} words proposed for cut ({ratio * 100:.1f}%)"
            )
        lines.append("")
    else:
        lines.append(f"_no chapters exceed the {threshold * 100:.0f}% drastic-reduction threshold_")
        lines.append("")
    lines.append("## Category legend")
    lines.append("")
    lines.append("- `editorial-bridge` — pipeline-added connective tissue not in source")
    lines.append("- `cross-tradition-import` — decorative quotes grafted from outside the source tradition")
    lines.append("- `restatement` — recap of what was already developed in the same chapter")
    lines.append("- `meta-narration` — second-person guide voice with no doctrinal content")
    lines.append("- `citation-overhead` — bibliographic scaffolding around citations (off by default)")
    lines.append("")
    lines.append("## How to use this report")
    lines.append("")
    lines.append("1. Review each chapter's candidates below. Pay extra attention to any RED-FLAG chapters above.")
    lines.append("2. For each cut you want to accept, flip `- [ ] accept this cut` to `- [x] accept this cut`.")
    lines.append("3. Save the report, then run: `--apply ch07,ch11,...`")
    lines.append("4. The script reads your `[x]` marks and writes `<ch>.tightened.txt` siblings —")
    lines.append("   only marked cuts are applied. Originals are NEVER overwritten.")
    lines.append("5. Diff the .tightened.txt against the original; promote it manually when satisfied.")
    lines.append("")
    lines.append("**Default state of every checkbox is unchecked — doing nothing approves nothing.**")
    lines.append("")

    for r in sorted(results, key=lambda x: x.chapter):
        ratio = (r.proposed_words_removed / r.original_words) if r.original_words else 0
        flag_marker = " 🔴 RED-FLAG" if ratio > threshold else ""
        lines.append(f"## {r.chapter}{flag_marker}")
        lines.append("")
        lines.append(f"- file: `{r.chapter_path.relative_to(book_dir.parent)}`")
        lines.append(f"- original words: **{r.original_words:,}**")
        lines.append(f"- proposed cut: **{r.proposed_words_removed:,}** ({ratio * 100:.1f}%)")
        if ratio > threshold:
            lines.append(
                f"- 🔴 **drastic-reduction threshold exceeded** "
                f"({ratio * 100:.1f}% > {threshold * 100:.0f}%) — "
                f"scrutinise each candidate before accepting; the goal is tightening, not shortening."
            )
        if r.cached:
            lines.append("- _result loaded from cache_")
        if r.error:
            lines.append(f"- error: **{r.error}**")
        lines.append("")
        if not r.candidates:
            lines.append("_no candidates flagged_")
            lines.append("")
            continue
        for i, c in enumerate(r.candidates, 1):
            cid = f"{r.chapter}-{i:02d}"
            lines.append(f"### {cid} `[{c.category}]` — lines {c.line_start}-{c.line_end}")
            lines.append("")
            lines.append(f"- [ ] accept this cut <!-- cid: {cid} -->")
            lines.append(f"- confidence: **{c.confidence:.2f}** · est. words removed: **{c.est_words_removed}**")
            if c.cohesion_warning:
                lines.append(f"- ⚠ **cohesion warning:** {c.cohesion_warning}")
            lines.append("")
            lines.append(f"**Anchor:** `{c.anchor_text}`")
            lines.append("")
            lines.append(f"**Rationale:** {c.rationale}")
            lines.append("")
            lines.append("---")
            lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


# --- apply mode ------------------------------------------------------------


def parse_accepted_cids(report_path: Path) -> set[str]:
    """Parse tighten-report.md and return the set of accepted candidate IDs."""
    if not report_path.exists():
        return set()
    pat = re.compile(r"-\s*\[\s*[xX]\s*\]\s*accept this cut\s*<!--\s*cid:\s*([\w\-.]+)\s*-->")
    out: set[str] = set()
    for line in report_path.read_text(encoding="utf-8").splitlines():
        m = pat.search(line)
        if m:
            out.add(m.group(1))
    return out


def apply_cuts(
    book_dir: Path,
    chapter_slugs: list[str],
    results: list[ChapterResult],
) -> list[Path]:
    """Write .tightened.txt siblings applying ONLY checkbox-accepted cuts."""
    written = []
    chapters_dir = book_dir / "chapters"
    report_path = book_dir / "_system" / "tighten-report.md"
    accepted_cids = parse_accepted_cids(report_path)
    if not accepted_cids:
        print(
            f"[tighten] --apply: no candidates are marked `- [x]` in {report_path}. "
            "Edit the report to mark cuts you accept, then re-run --apply.",
            file=sys.stderr,
        )
        return []
    print(f"[tighten] --apply: {len(accepted_cids)} candidate(s) marked accepted in report.", file=sys.stderr)

    for slug in chapter_slugs:
        slug = slug.strip()
        match = next((r for r in results if r.chapter.startswith(slug)), None)
        if match is None:
            print(f"[tighten] --apply: no chapter matching '{slug}'", file=sys.stderr)
            continue
        if not match.candidates:
            print(f"[tighten] --apply: {match.chapter} has no candidates to apply", file=sys.stderr)
            continue
        accepted_for_chapter = [
            (i, c) for i, c in enumerate(match.candidates, 1) if f"{match.chapter}-{i:02d}" in accepted_cids
        ]
        if not accepted_for_chapter:
            print(
                f"[tighten] --apply: {match.chapter} — 0 of {len(match.candidates)} candidates marked accepted; skipping.",
                file=sys.stderr,
            )
            continue
        text_lines = match.chapter_path.read_text(encoding="utf-8").splitlines()
        drop = set()
        for _, c in accepted_for_chapter:
            for i in range(c.line_start - 1, c.line_end):
                if 0 <= i < len(text_lines):
                    drop.add(i)
        kept = [line for i, line in enumerate(text_lines) if i not in drop]
        out_path = chapters_dir / f"{match.chapter}.tightened.txt"
        out_path.write_text("\n".join(kept) + "\n", encoding="utf-8")
        written.append(out_path)
        n_accepted = len(accepted_for_chapter)
        n_total = len(match.candidates)
        print(f"[tighten] wrote {out_path.relative_to(book_dir.parent)} ({n_accepted}/{n_total} cuts applied)")
    return written


# --- main ------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Advisory tighten-pass for NotebookLM source chapters.")
    parser.add_argument(
        "--book-dir", required=True, help="path to content/drafts/<slug>/ or content/published/books/<slug>/"
    )
    parser.add_argument("--chapter", help="run only this chapter (e.g. ch07). Default: all chapters.")
    parser.add_argument("--all", action="store_true", help="run all chapters (default if --chapter not given)")
    parser.add_argument("--apply", help="comma-separated chapter slugs to apply (e.g. ch07,ch11)")
    parser.add_argument("--dry-run", action="store_true", help="no LLM calls; just show what would run")
    parser.add_argument("--force", action="store_true", help="bypass cache; re-run LLM even if cached")
    parser.add_argument("--no-cohesion", action="store_true", help="skip the cohesion cross-chapter pass")
    parser.add_argument("--json", action="store_true", help="emit JSON to stdout instead of the report path")
    parser.add_argument("--budget", type=float, help="override per-book budget cap (USD)")
    args = parser.parse_args(argv)

    book_dir = Path(args.book_dir).resolve()
    if not book_dir.exists():
        print(f"[tighten] error: book_dir does not exist: {book_dir}", file=sys.stderr)
        return 3
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.exists():
        print(f"[tighten] error: chapters/ not found under {book_dir}", file=sys.stderr)
        return 2

    boundary_check(book_dir)

    cfg = load_config(book_dir)
    if args.budget is not None:
        cfg["budget_usd"] = args.budget

    meta_path = book_dir / "meta.yml"
    book_title = book_dir.name
    book_premise = ""
    if meta_path.exists():
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("title:"):
                book_title = line.split(":", 1)[1].strip().strip('"')
                break
    readme = book_dir / "_README.md"
    if readme.exists():
        book_premise = readme.read_text(encoding="utf-8")[:600]

    chapter_paths = sorted(chapters_dir.glob("ch*.txt"))
    chapter_paths = [p for p in chapter_paths if not p.name.endswith(".tightened.txt")]
    if args.chapter:
        chapter_paths = [p for p in chapter_paths if p.stem.startswith(args.chapter)]
    if not chapter_paths:
        print(f"[tighten] error: no matching chapters in {chapters_dir}", file=sys.stderr)
        return 2

    results: list[ChapterResult] = []
    for cp in chapter_paths:
        print(f"[tighten] {cp.stem} ...", file=sys.stderr)
        r = run_per_chapter(book_dir, cp, book_title, book_premise, cfg, force_refresh=args.force, dry_run=args.dry_run)
        results.append(r)
        if r.error:
            print(f"[tighten]   {r.error}", file=sys.stderr)
        else:
            print(f"[tighten]   {len(r.candidates)} candidates (~{r.proposed_words_removed} words)", file=sys.stderr)

    if not args.no_cohesion:
        run_cohesion(book_dir, results, book_title, cfg, dry_run=args.dry_run)

    report_path = render_report(book_dir, results, book_title, cfg)

    written: list[Path] = []
    if args.apply:
        slugs = [s.strip() for s in args.apply.split(",") if s.strip()]
        written = apply_cuts(book_dir, slugs, results)  # noqa: F841

    if args.json:
        import json as _json

        print(
            _json.dumps(
                [{"chapter": r.chapter, "candidates": [c.to_dict() for c in r.candidates]} for r in results],
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"[tighten] report: {report_path}")

    total_cands = sum(len(r.candidates) for r in results)
    return 0 if total_cands > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
