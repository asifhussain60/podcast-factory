#!/usr/bin/env python3
"""ab_compare_episode.py — A/B comparison report between a NotebookLM
reference transcript and our generated framing + notebooklm bundle.

INTENT

After per-chapter authoring produces a framing.md + notebooklm-bundle, we
want to know what topical ground the prior NotebookLM episode (the
reference MP3 the user generated independently before this pipeline) covered
vs. what our generated framing covers. The diff lets the author decide:
  - Did our framing miss a topic the reference covered? (gap to close)
  - Did our framing add a topic the reference didn't? (curator addition,
    keep or drop based on chapter contract)
  - Did our framing handle a topic differently? (preserve our version
    unless the difference loses fidelity to the source)

USAGE

  python3 scripts/podcast/ab_compare_episode.py \\
      --book-dir content/drafts/the-master-and-the-disciple \\
      --episode EP01-scholar-and-seeker \\
      --reference-transcript audits/ab-reference/transcripts/Chapter_1_Scholar_and_Seeker.txt

OUTPUTS

  BOOK_DIR/audits/ab-reference/reports/EP##-<slug>.ab-report.md

This is intentionally STRUCTURAL, not semantic. Headline numbers + topic
keyword coverage + named-entity overlap. Author decides what to do with it.
Cheap to run; rerun after every framing iteration.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\-]+")
SENTENCE_RE = re.compile(r"[^.!?\n]+[.!?]")
PROPER_NOUN_RE = re.compile(r"\b([A-Z][a-z]{2,}(?:[ -][A-Z][a-z]{2,})*)\b")
STOP_PROPER = {
    "The", "A", "An", "In", "Of", "And", "Or", "If", "He", "She", "It",
    "They", "We", "You", "I", "His", "Her", "Their", "Our", "My", "Your",
    "This", "That", "These", "Those", "Then", "When", "Where", "What",
    "Who", "Why", "How", "But", "So", "For", "Yet", "Now", "There", "Here",
    "On", "At", "By", "To", "Be", "Is", "Was", "Are", "Were", "Have", "Has",
    "Had", "Do", "Does", "Did", "Can", "Could", "Will", "Would", "Should",
    "May", "Might", "Must", "Chapter", "Book", "Hello", "Welcome", "Today",
    "Right", "Yeah", "Like", "OK", "Okay",
}


def proper_nouns(text: str) -> Counter:
    """Capitalized multi-word phrases at ≥3 chars, excluding stop list."""
    return Counter(
        m for m in PROPER_NOUN_RE.findall(text)
        if m.split()[0] not in STOP_PROPER
    )


def word_count(text: str) -> int:
    return len(WORD_RE.findall(text))


def sentence_count(text: str) -> int:
    return len(SENTENCE_RE.findall(text))


def find_framing_path(book_dir: Path, episode: str) -> Path | None:
    candidates = [
        book_dir / "_system" / "episode-drafts" / episode / "00-framing.md",
        book_dir / "framings" / f"{episode}.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def find_notebooklm_bundle(book_dir: Path, episode: str) -> list[Path]:
    base = book_dir / "_system" / "episode-drafts" / episode
    if not base.is_dir():
        return []
    return sorted(base.glob("*.md"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--book-dir", required=True, type=Path)
    ap.add_argument("--episode", required=True, help="e.g. EP01-scholar-and-seeker")
    ap.add_argument(
        "--reference-transcript",
        required=True,
        type=Path,
        help="path to the NotebookLM reference MP3's transcript (.txt)",
    )
    args = ap.parse_args()

    book_dir: Path = args.book_dir.resolve()
    ref_path: Path = args.reference_transcript.resolve()
    if not ref_path.exists():
        # Allow relative to BOOK_DIR
        candidate = (book_dir / args.reference_transcript).resolve()
        if candidate.exists():
            ref_path = candidate
        else:
            sys.stderr.write(f"reference transcript not found: {args.reference_transcript}\n")
            return 2

    ref_text = ref_path.read_text(encoding="utf-8")

    framing_path = find_framing_path(book_dir, args.episode)
    if framing_path is None:
        sys.stderr.write(
            f"framing not found for {args.episode} — expected at "
            f"_system/episode-drafts/{args.episode}/00-framing.md or "
            f"framings/{args.episode}.md\n"
        )
        return 3
    framing_text = framing_path.read_text(encoding="utf-8")

    bundle_paths = find_notebooklm_bundle(book_dir, args.episode)
    bundle_text = "\n\n".join(p.read_text(encoding="utf-8") for p in bundle_paths)

    ref_wc = word_count(ref_text)
    framing_wc = word_count(framing_text)
    bundle_wc = word_count(bundle_text)
    ref_sc = sentence_count(ref_text)

    ref_props = proper_nouns(ref_text)
    framing_props = proper_nouns(framing_text)
    bundle_props = proper_nouns(bundle_text)

    # Overlap analysis
    ref_top = [p for p, c in ref_props.most_common(40) if c >= 2]
    ours_combined = framing_props + bundle_props
    overlap = [p for p in ref_top if p in ours_combined]
    missing_in_ours = [p for p in ref_top if p not in ours_combined]
    ours_only = sorted(
        (p for p in ours_combined if p not in ref_props and ours_combined[p] >= 2),
        key=lambda p: -ours_combined[p],
    )[:25]

    out_dir = book_dir / "audits" / "ab-reference" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.episode}.ab-report.md"

    lines = []
    lines.append(f"# A/B reference comparison — {args.episode}")
    lines.append("")
    lines.append("**Purpose:** compare our generated framing + notebooklm bundle against the prior NotebookLM episode the user generated independently. Topical coverage check, not a semantic-equivalence test.")
    lines.append("")
    lines.append("## Files compared")
    lines.append("")
    lines.append(f"- **Reference transcript:** `{ref_path.relative_to(book_dir) if ref_path.is_relative_to(book_dir) else ref_path}`")
    lines.append(f"- **Our framing:** `{framing_path.relative_to(book_dir)}`")
    if bundle_paths:
        lines.append(f"- **Our notebooklm bundle:** {len(bundle_paths)} files at `{bundle_paths[0].parent.relative_to(book_dir)}/`")
    lines.append("")
    lines.append("## Headline numbers")
    lines.append("")
    lines.append(f"- Reference transcript: **{ref_wc:,} words / {ref_sc:,} sentences**")
    lines.append(f"- Our framing: **{framing_wc:,} words**")
    lines.append(f"- Our bundle: **{bundle_wc:,} words ({len(bundle_paths)} files)**")
    if ref_wc:
        ratio = (framing_wc + bundle_wc) / ref_wc
        lines.append(f"- Our-total / reference ratio: **{ratio:.2f}×**")
    lines.append("")
    lines.append("## Reference top-25 proper nouns (freq ≥ 2)")
    lines.append("")
    if not ref_top:
        lines.append("_(no significant proper nouns found in reference)_")
    else:
        lines.append("| Term | Ref count | In our framing | In our bundle | Status |")
        lines.append("|---|---|---|---|---|")
        for p in ref_top[:25]:
            in_f = framing_props.get(p, 0)
            in_b = bundle_props.get(p, 0)
            status = "✓ covered" if (in_f or in_b) else "✗ missing"
            lines.append(f"| {p} | {ref_props[p]} | {in_f} | {in_b} | {status} |")
    lines.append("")
    lines.append("## Coverage summary")
    lines.append("")
    lines.append(f"- Reference top-25 covered in our work: **{len(overlap)}/{len(ref_top)}**")
    if missing_in_ours:
        lines.append("")
        lines.append("### Reference terms NOT in our work (potential gap)")
        lines.append("")
        for p in missing_in_ours[:15]:
            # Pull a sample sentence from the reference containing the term
            sample = ""
            for sent in SENTENCE_RE.finditer(ref_text):
                if p in sent.group():
                    sample = sent.group().strip()[:200]
                    break
            lines.append(f"- **{p}** (ref count: {ref_props[p]})")
            if sample:
                lines.append(f"  > {sample}…")
    if ours_only:
        lines.append("")
        lines.append("### Terms in OUR work not in reference (curator addition)")
        lines.append("")
        for p in ours_only[:15]:
            lines.append(f"- **{p}** (our count: {ours_combined[p]})")
    lines.append("")
    lines.append("## Author action checklist")
    lines.append("")
    lines.append("- [ ] Review each **missing** term above — is it a real topical gap, or just spelling drift (e.g. reference says 'Hujjah', we say 'Hujjah' but with different transliteration)?")
    lines.append("- [ ] Review **curator addition** terms — are they intentional enrichment from the chapter source, or out-of-scope topics? Cross-check against `chapter-contracts/<slug>.yml` key_tensions.")
    lines.append("- [ ] If the our-total/reference ratio is < 0.6× — our framing may be under-developed relative to the reference. Consider whether the contract length_target is right.")
    lines.append("- [ ] If the ratio is > 2.0× — our framing may be over-developed. Trim or move enrichment to a separate Customize-prompt layer.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("_Generated by `scripts/podcast/ab_compare_episode.py`. Re-run after each framing iteration to track convergence._")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_path.relative_to(book_dir)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
