#!/usr/bin/env python3
"""Serializer between operator-review.md (markdown) and ReviewStruct (dict).

The P22 spec defines operator-review.md as a scaffolded template with these sections:
  §1 Translation issues   — page-anchored rows
  §2 Missing passages     — page-anchored rows
  §3 Glossary additions   — term + definition rows
  §4 Pronunciation        — term + correct pronunciation rows
  §5 Free-form comments   — single textarea
  §6 (intentionally elided in P22; reserved)
  §7 Content range        — body_starts_at_page / body_ends_at_page
  §8 Approval             — "[x] I approve this transcript" checkbox

This module is the load-bearing contract between the browser SPA and the
pipeline. operator-review.md remains the SOURCE OF TRUTH that the pipeline
reads on --approve-transcript resume. The studio app keeps it in sync via:

   ReviewStruct  →  serialize_to_markdown()  →  operator-review.md
                ←  parse_from_markdown()    ←  operator-review.md

Round-trip is byte-stable modulo trailing-whitespace normalization (asserted
by test_review_serializer.py).

P25.7 (AI assist layer) adds an OPTIONAL §9 AI-suggestions block that the
pipeline IGNORES on resume but the studio uses to persist accepted/dismissed
state across sessions. The section is delimited by HTML comments so even if
the pipeline reads it, it doesn't affect prompt assembly.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

# Marker constants — must match what the pipeline prompt-assembly expects
SECTION_MARKER = "## §"  # journal pattern
APPROVE_MARKER_CHECKED = "[x] I approve this transcript"
APPROVE_MARKER_UNCHECKED = "[ ] I approve this transcript"
AI_BLOCK_START = "<!-- ai-suggestions-start: operator-review-studio P25.7 -->"
AI_BLOCK_END = "<!-- ai-suggestions-end -->"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class FlagRow:
    page: int
    quote: str
    note: str = ""
    recurring_pattern: bool = False


@dataclass
class GlossaryRow:
    term: str
    definition: str


@dataclass
class PronunciationRow:
    term: str
    correct: str


@dataclass
class ContentRange:
    body_starts_at_page: int | None = None
    body_ends_at_page: int | None = None


@dataclass
class AISuggestion:
    """Persisted AI suggestion (accepted or dismissed)."""
    id: str
    page: int
    quote: str
    reason: str
    feature: str       # 'suggest-flags' | 'voice-shift' | etc.
    status: str = "pending"  # 'pending' | 'accepted' | 'dismissed'


@dataclass
class ReviewStruct:
    schema_version: int = SCHEMA_VERSION
    book_slug: str = ""
    translation_issues: list[FlagRow] = field(default_factory=list)
    missing_passages: list[FlagRow] = field(default_factory=list)
    glossary: list[GlossaryRow] = field(default_factory=list)
    pronunciation: list[PronunciationRow] = field(default_factory=list)
    free_form_comments: str = ""
    content_range: ContentRange = field(default_factory=ContentRange)
    approved: bool = False
    ai_suggestions: list[AISuggestion] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ReviewStruct":
        rs = cls()
        rs.schema_version = d.get("schema_version", SCHEMA_VERSION)
        rs.book_slug = d.get("book_slug", "")
        rs.translation_issues = [FlagRow(**r) for r in d.get("translation_issues", [])]
        rs.missing_passages = [FlagRow(**r) for r in d.get("missing_passages", [])]
        rs.glossary = [GlossaryRow(**r) for r in d.get("glossary", [])]
        rs.pronunciation = [PronunciationRow(**r) for r in d.get("pronunciation", [])]
        rs.free_form_comments = d.get("free_form_comments", "")
        cr = d.get("content_range", {})
        rs.content_range = ContentRange(
            body_starts_at_page=cr.get("body_starts_at_page"),
            body_ends_at_page=cr.get("body_ends_at_page"),
        )
        rs.approved = bool(d.get("approved", False))
        rs.ai_suggestions = [AISuggestion(**s) for s in d.get("ai_suggestions", [])]
        return rs


# ---------------------------------------------------------------------------
# Markdown ↔ struct serialization
# ---------------------------------------------------------------------------

def serialize_to_markdown(rs: ReviewStruct) -> str:
    """Render ReviewStruct → operator-review.md text.

    Output format matches the P22 scaffold convention; the pipeline reads
    this on --approve-transcript resume.
    """
    out: list[str] = []
    out.append(f"# Operator review — {rs.book_slug}")
    out.append("")
    out.append(
        "Authored via Operator Review Studio (P25). "
        "Edit any section, then resume the orchestrator with --approve-transcript."
    )
    out.append("")

    out.append("## §1 Translation issues")
    out.append("")
    if not rs.translation_issues:
        out.append("_(none)_")
    else:
        for r in rs.translation_issues:
            out.append(_render_flag_row(r))
    out.append("")

    out.append("## §2 Missing or scrambled passages")
    out.append("")
    if not rs.missing_passages:
        out.append("_(none)_")
    else:
        for r in rs.missing_passages:
            out.append(_render_flag_row(r))
    out.append("")

    out.append("## §3 Glossary additions")
    out.append("")
    if not rs.glossary:
        out.append("_(none)_")
    else:
        for r in rs.glossary:
            out.append(f"- **{r.term}** — {r.definition}")
    out.append("")

    out.append("## §4 Pronunciation corrections")
    out.append("")
    if not rs.pronunciation:
        out.append("_(none)_")
    else:
        for r in rs.pronunciation:
            out.append(f"- **{r.term}** → {r.correct}")
    out.append("")

    out.append("## §5 Free-form comments")
    out.append("")
    out.append(rs.free_form_comments.strip() or "_(none)_")
    out.append("")

    out.append("## §7 Content range")
    out.append("")
    cr = rs.content_range
    if cr.body_starts_at_page is not None:
        out.append(f"- body_starts_at_page: {cr.body_starts_at_page}")
    if cr.body_ends_at_page is not None:
        out.append(f"- body_ends_at_page: {cr.body_ends_at_page}")
    if cr.body_starts_at_page is None and cr.body_ends_at_page is None:
        out.append("_(not set — Phase 0c+ will ingest whole transcript)_")
    out.append("")

    out.append("## §8 Approval")
    out.append("")
    out.append(APPROVE_MARKER_CHECKED if rs.approved else APPROVE_MARKER_UNCHECKED)
    out.append("")

    # AI suggestions block — HTML-commented so the pipeline ignores it
    if rs.ai_suggestions:
        out.append(AI_BLOCK_START)
        out.append("<!-- This block is operator-studio internal state; pipeline ignores it. -->")
        out.append("<!-- Each suggestion JSON: { id, page, quote, reason, feature, status } -->")
        for s in rs.ai_suggestions:
            import json
            out.append(f"<!-- {json.dumps(asdict(s), ensure_ascii=False)} -->")
        out.append(AI_BLOCK_END)
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def _render_flag_row(r: FlagRow) -> str:
    """Render a single flag row in the P22 convention.

    Format (3 lines):
        - **p. 47**
          > "quote text"
          note text _(recurring pattern)_
    """
    lines = [f"- **p. {r.page}**"]
    if r.quote:
        lines.append(f'  > "{r.quote}"')
    if r.note or r.recurring_pattern:
        suffix = " _(recurring pattern)_" if r.recurring_pattern else ""
        lines.append(f"  {r.note}{suffix}")
    return "\n".join(lines)


# Regex patterns for parse_from_markdown
_RE_SECTION = re.compile(r"^## §(\d+)\s+(.+)$")
_RE_FLAG_ROW = re.compile(r"^- \*\*p\.\s*(\d+)\*\*\s*$")
_RE_QUOTE_LINE = re.compile(r'^\s+>\s*"(.*?)"\s*$')
_RE_NOTE_LINE = re.compile(r"^\s{2,}(.+)$")
_RE_GLOSSARY = re.compile(r"^- \*\*([^*]+)\*\*\s+—\s+(.+)$")
_RE_PRONUNCIATION = re.compile(r"^- \*\*([^*]+)\*\*\s+→\s+(.+)$")
_RE_RANGE_KV = re.compile(r"^- (body_starts_at_page|body_ends_at_page):\s*(\d+)")
_RE_AI_COMMENT = re.compile(r"^<!--\s+(\{.+\})\s+-->$")


def parse_from_markdown(text: str, book_slug: str = "") -> ReviewStruct:
    """Parse operator-review.md → ReviewStruct.

    Tolerant: blank sections produce empty lists. Round-trip safe.
    """
    rs = ReviewStruct(book_slug=book_slug)

    current_section = None
    pending_flag: dict[str, Any] | None = None

    def _flush_flag(target: list[FlagRow] | None) -> None:
        nonlocal pending_flag
        if pending_flag and target is not None:
            target.append(FlagRow(**pending_flag))
        pending_flag = None

    free_form_lines: list[str] = []
    in_ai_block = False

    for raw in text.splitlines():
        line = raw.rstrip()

        # Section header
        m = _RE_SECTION.match(line)
        if m:
            # Flush any pending flag before switching section
            _flush_flag(_section_target(rs, current_section))
            # Save free-form if we were in §5
            if current_section == 5:
                rs.free_form_comments = "\n".join(free_form_lines).strip()
                free_form_lines = []
            current_section = int(m.group(1))
            continue

        # AI block markers
        if line == AI_BLOCK_START:
            in_ai_block = True
            continue
        if line == AI_BLOCK_END:
            in_ai_block = False
            continue
        if in_ai_block:
            am = _RE_AI_COMMENT.match(line)
            if am:
                import json
                try:
                    rs.ai_suggestions.append(AISuggestion(**json.loads(am.group(1))))
                except (json.JSONDecodeError, TypeError):
                    pass
            continue

        if current_section in (1, 2):
            target = _section_target(rs, current_section)
            mf = _RE_FLAG_ROW.match(line)
            if mf:
                _flush_flag(target)
                pending_flag = {
                    "page": int(mf.group(1)),
                    "quote": "",
                    "note": "",
                    "recurring_pattern": False,
                }
                continue
            mq = _RE_QUOTE_LINE.match(line)
            if mq and pending_flag is not None:
                pending_flag["quote"] = mq.group(1)
                continue
            mn = _RE_NOTE_LINE.match(line)
            if mn and pending_flag is not None and not line.lstrip().startswith(">"):
                add = mn.group(1).strip()
                if "_(recurring pattern)_" in add:
                    pending_flag["recurring_pattern"] = True
                    add = add.replace("_(recurring pattern)_", "").strip()
                if add:
                    pending_flag["note"] = (pending_flag["note"] + " " + add).strip()
                continue

        elif current_section == 3:
            mg = _RE_GLOSSARY.match(line)
            if mg:
                rs.glossary.append(GlossaryRow(term=mg.group(1).strip(), definition=mg.group(2).strip()))

        elif current_section == 4:
            mp = _RE_PRONUNCIATION.match(line)
            if mp:
                rs.pronunciation.append(PronunciationRow(term=mp.group(1).strip(), correct=mp.group(2).strip()))

        elif current_section == 5:
            if line and not line.startswith("_(none"):
                free_form_lines.append(line)

        elif current_section == 7:
            mr = _RE_RANGE_KV.match(line)
            if mr:
                key, val = mr.group(1), int(mr.group(2))
                if key == "body_starts_at_page":
                    rs.content_range.body_starts_at_page = val
                else:
                    rs.content_range.body_ends_at_page = val

        elif current_section == 8:
            if APPROVE_MARKER_CHECKED in line:
                rs.approved = True

    # End-of-file flush
    _flush_flag(_section_target(rs, current_section))
    if current_section == 5:
        rs.free_form_comments = "\n".join(free_form_lines).strip()

    return rs


def _section_target(rs: ReviewStruct, section: int | None) -> list[FlagRow] | None:
    if section == 1:
        return rs.translation_issues
    if section == 2:
        return rs.missing_passages
    return None


# ---------------------------------------------------------------------------
# Atomic write
# ---------------------------------------------------------------------------

def atomic_write(path: Path, content: str) -> None:
    """Write content to path via tmp + rename (atomic on POSIX)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    # fsync to ensure durability before rename
    with open(tmp, "rb+") as f:
        import os
        os.fsync(f.fileno())
    tmp.replace(path)


def summary_one_line(rs: ReviewStruct) -> str:
    """Build the one-line summary used in git commit messages.

    Example: '3 flags, 1 glossary, range 14–178'
    """
    parts: list[str] = []
    if rs.translation_issues:
        parts.append(f"{len(rs.translation_issues)} flags")
    if rs.missing_passages:
        parts.append(f"{len(rs.missing_passages)} missing")
    if rs.glossary:
        parts.append(f"{len(rs.glossary)} glossary")
    if rs.pronunciation:
        parts.append(f"{len(rs.pronunciation)} pron")
    cr = rs.content_range
    if cr.body_starts_at_page or cr.body_ends_at_page:
        a = cr.body_starts_at_page if cr.body_starts_at_page else "?"
        b = cr.body_ends_at_page if cr.body_ends_at_page else "?"
        parts.append(f"range {a}–{b}")
    return ", ".join(parts) if parts else "no changes"


__all__ = [
    "SCHEMA_VERSION",
    "FlagRow",
    "GlossaryRow",
    "PronunciationRow",
    "ContentRange",
    "AISuggestion",
    "ReviewStruct",
    "serialize_to_markdown",
    "parse_from_markdown",
    "atomic_write",
    "summary_one_line",
]
