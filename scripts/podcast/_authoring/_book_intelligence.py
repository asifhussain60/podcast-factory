"""_authoring/_book_intelligence.py — Phase 0ci: Book Intelligence gap analysis.

Cross-references the refined source text against the book's KSessions augment
files to identify content gaps, ambiguities, and modern analogy candidates.
Writes _system/gap-analysis.md and, for Islamic scholarly content, raises
AuthoringHalt so the human reviews the gap analysis before Phase 0d (chapter
design) begins.

Fits into the A4 split package alongside _refine (0b/0c), _chapter_design (0d),
and _enrichment (0e).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ._core import (  # noqa: E402
    AuthoringError,
    AuthoringHalt,
    DEFAULT_TIMEOUT,
    _run_claude_p,
)
from _content_profile import is_islamic_scholarly  # noqa: E402


def author_phase_0ci(book_dir: Path, *, timeout: int = DEFAULT_TIMEOUT, log=print) -> str:
    """Phase 0ci: cross-reference refined text against augment files to find gaps.

    Outputs:
      _system/gap-analysis.md — structured gap analysis with [MISSING], [PARTIAL],
                                 [CLARIFIED], and [ANALOGY] tags.

    For Islamic scholarly content, raises AuthoringHalt after writing the file so
    the human reviews before Phase 0d runs.

    Skip conditions:
      - No augment/*.md files exist (nothing to cross-reference against).
      - The book is not Islamic scholarly content (gap analysis not applicable).
    """
    book_slug = book_dir.name
    refined_path = book_dir / "_system" / "source" / "text" / "refined-english.md"
    augment_dir = book_dir / "augment"
    out_path = book_dir / "_system" / "gap-analysis.md"

    if not refined_path.exists():
        raise AuthoringError(
            phase="0ci",
            message=f"prerequisite missing: {refined_path} (Phase 0b should have produced this)",
            manual_fallback="Run Phase 0b first.",
        )

    # If no augment files exist, nothing to cross-reference — skip gracefully.
    augment_files = sorted(augment_dir.glob("[0-9]*.md")) if augment_dir.exists() else []
    if not augment_files:
        log("  phase 0ci · no augment/*.md files found — skipping gap analysis")
        return "0ci skipped: no augment files to cross-reference"

    # If the book is not Islamic scholarly, skip (gap analysis is only wired for Islamic content).
    if not is_islamic_scholarly(book_dir):
        log("  phase 0ci · not Islamic scholarly content — skipping gap analysis")
        return "0ci skipped: not Islamic scholarly content"

    # Collect augment content (limit each file to avoid context overload).
    MAX_CHARS_PER_FILE = 8_000
    augment_sections: list[str] = []
    for afile in augment_files:
        text = afile.read_text(encoding="utf-8")[:MAX_CHARS_PER_FILE]
        augment_sections.append(f"### {afile.stem}\n\n{text}")
    augment_block = "\n\n---\n\n".join(augment_sections)

    refined_text = refined_path.read_text(encoding="utf-8")
    # Limit refined text to 20k chars to keep the prompt manageable.
    refined_excerpt = refined_text[:20_000]

    synthesis_path = augment_dir / "_synthesis.md"
    synthesis_block = ""
    if synthesis_path.exists():
        synthesis_block = (
            f"\n\n## Session → Chapter alignment\n\n"
            f"{synthesis_path.read_text(encoding='utf-8')[:3_000]}"
        )

    prompt = (
        f"You are driving Phase 0ci (Book Intelligence Gap Analysis) of the /podcast skill "
        f"on book-slug `{book_slug}`.\n\n"
        f"## Your task\n\n"
        f"Cross-reference the refined source text (below) against the KSessions augment files "
        f"(pre-processed Ismaili/Islamic wisdom synthesis). Produce a structured gap analysis "
        f"that the chapter designer (Phase 0d) can use to draw chapter boundaries and enrich "
        f"episode framing.\n\n"
        f"## Output format\n\n"
        f"Write a markdown file to `{out_path}` using EXACTLY these tags:\n\n"
        f"- `[MISSING]` — the source text refers to a concept, name, or tradition without "
        f"  explaining it; the augment files contain relevant context that is absent from the "
        f"  source. State: (a) the passage in the source, (b) what is missing, "
        f"  (c) the augment content that fills it.\n\n"
        f"- `[PARTIAL]` — the source text touches a concept but leaves it ambiguous or "
        f"  incomplete. State: (a) the passage, (b) the ambiguity, (c) the clarification "
        f"  from the augment or from established Ismaili scholarship.\n\n"
        f"- `[CLARIFIED]` — a term or concept that initially reads as opaque but can be "
        f"  firmly clarified from the augment. Provide a one-line plain-English gloss "
        f"  suitable for episode framing.\n\n"
        f"- `[ANALOGY]` — an esoteric passage where a modern practical analogy would help "
        f"  a non-specialist listener grasp the concept. Propose the analogy and tag it "
        f"`[TEACHING-CONTEXT]` (never attribute to the book's author).\n\n"
        f"## Scope rules\n\n"
        f"- Ground ALL findings in the source text + augment files. Do NOT invent doctrine.\n"
        f"- `[MISSING]` and `[PARTIAL]` must cite the source passage (first 10 words + ¶ "
        f"  reference if available).\n"
        f"- Limit output to the 10 most significant findings per tag category. "
        f"  Quality over quantity.\n"
        f"- Write in academic but accessible English. No jargon without a gloss.\n\n"
        f"## Source text (refined-english.md, first 20 000 chars)\n\n"
        f"```\n{refined_excerpt}\n```\n\n"
        f"## KSessions augment files\n\n"
        f"{augment_block}"
        f"{synthesis_block}\n\n"
        f"Exit when `{out_path}` is written and non-empty."
    )

    log("  phase 0ci · running gap analysis (one LLM call)")
    rc, stdout, stderr = _run_claude_p(
        prompt,
        timeout=timeout,
        book_dir=book_dir,
        phase="0ci",
        step="gap-analysis",
    )

    # Stdout fallback: if Claude wrote the content to stdout instead of using Write tool.
    if not out_path.exists() and stdout and stdout.strip():
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(stdout.strip(), encoding="utf-8")
        log("  phase 0ci · gap-analysis.md recovered from stdout")

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise AuthoringError(
            phase="0ci",
            message="Phase 0ci produced no gap-analysis.md artifact",
            manual_fallback=(
                "Run manually: read refined-english.md + augment/*.md, "
                f"write {out_path} with [MISSING]/[PARTIAL]/[CLARIFIED]/[ANALOGY] sections."
            ),
        )

    log(f"  phase 0ci · gap-analysis.md written ({out_path.stat().st_size} bytes)")

    raise AuthoringHalt(
        phase="0ci",
        message=(
            f"Book intelligence gap analysis ready for review: {out_path}\n"
            "Review [MISSING] and [PARTIAL] findings before Phase 0d draws chapter boundaries.\n"
            "[ANALOGY] candidates marked [TEACHING-CONTEXT] — use only if the episode format calls for it."
        ),
        manual_fallback=(
            f"1. Review {out_path}\n"
            "2. Edit or annotate as needed (add notes, reject candidates, confirm clarifications).\n"
            "3. Resume: python3 scripts/podcast/orchestrate_book.py --resume <slug>"
        ),
    )
