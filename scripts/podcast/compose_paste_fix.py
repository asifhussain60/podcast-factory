"""Paste & Fix cleanup helpers for compose_articulate.py."""

from __future__ import annotations

import re
from pathlib import Path

from _authoring._core import AuthoringError, _run_claude_p_with_retry, pure_text_call_options
from _book_companion_prompts import parse_cards
from _book_edits import anchor_key
from _book_voice_gates import revoice_gates
from _pipeline_flags import narrative_frame, narrator_subject
from _scholar_bridge import ScholarBridgeError
from _scholar_bridge import prepare as scholar_prepare
from _student_reader import chapter_budget, dedupe, gate_finding, select
from _student_reader_prompts import build_prompt, evidence_block
from _student_reader_store import section_key
from student_reader_notes import ask_scholar

_IMG_MD_RE = re.compile(r"(?m)^(!\[[^\]]*\]\(([^)]+)\))\s*$")
_SPLIT_BLANK_RE = re.compile(r"\n[ \t]*\n+")
_STRUCTURAL_RE = re.compile(r"^(#{1,6}\s+|>\s?|!\[[^\]]*\]\(|[-*+]\s+|\d+\.\s+|```|<!--|\|)")
_TERMINAL_RE = re.compile(r"""[.!?;:。؟…]["')\]]*$""")
_CONTINUATION_RE = re.compile(r"""^[a-z,;:)\]\-–—]""")
_ARABIC_RE = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]")
_CAPS_TRANSCRIPT_RE = re.compile(r"^[A-Z][A-Z' \-]{1,29}$")
_HEADING_CITATION_RE = re.compile(r"\[[^\]]*\d{1,3}:\d{1,3}[^\]]*\]")
_HEADING_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’.-]*")
_HEADING_STOPWORDS = {
    "a",
    "an",
    "and",
    "as",
    "for",
    "in",
    "of",
    "or",
    "the",
    "to",
    "vs",
    "vs.",
}


def _is_arabic_only_block(block: str) -> bool:
    text = " ".join(block.split())
    return bool(_ARABIC_RE.search(text)) and not re.search(r"[A-Za-z]", text)


def _looks_like_standalone_heading(block: str) -> bool:
    text = " ".join(block.split())
    if (
        not text
        or "\n" in block
        or _is_arabic_only_block(text)
        or _STRUCTURAL_RE.match(text)
        or _HEADING_CITATION_RE.search(text)
        or _TERMINAL_RE.search(text)
        or len(text) > 72
    ):
        return False
    words = _HEADING_WORD_RE.findall(text)
    if not words or len(words) > 9:
        return False
    if _CAPS_TRANSCRIPT_RE.match(text):
        return True
    untitled = [w for w in words if not w[:1].isupper() and w.casefold() not in _HEADING_STOPWORDS]
    titled = sum(1 for w in words if w[:1].isupper())
    return not untitled and titled >= 1


def _is_prose_block(block: str) -> bool:
    stripped = block.strip()
    if not stripped or _is_arabic_only_block(stripped):
        return False
    if "\n" not in stripped and _CAPS_TRANSCRIPT_RE.match(stripped):
        return False
    if _looks_like_standalone_heading(stripped):
        return False
    return not any(_STRUCTURAL_RE.match(line.strip()) for line in stripped.splitlines() if line.strip())


def _looks_split(prev: str, cur: str) -> bool:
    prev = " ".join(prev.split())
    cur = " ".join(cur.split())
    if not prev or not cur:
        return False
    return (not _TERMINAL_RE.search(prev)) or bool(_CONTINUATION_RE.match(cur))


def repair_split_paragraphs(body: str) -> tuple[str, list[dict]]:
    """Repair paste damage that broke one sentence or paragraph into fragments."""
    blocks = [
        b.strip() for b in _SPLIT_BLANK_RE.split(body.replace("\r\n", "\n").replace("\r", "\n").strip()) if b.strip()
    ]
    out: list[str] = []
    changes: list[dict] = []
    for block in blocks:
        current = block
        if _is_prose_block(current) and "\n" in current:
            joined = " ".join(line.strip() for line in current.splitlines() if line.strip())
            if joined != current:
                changes.append({"kind": "soft-line-join", "before": current[:120], "after": joined[:120]})
                current = joined
        if out and _is_prose_block(out[-1]) and _is_prose_block(current) and _looks_split(out[-1], current):
            before = out[-1]
            out[-1] = f"{' '.join(out[-1].split())} {' '.join(current.split())}"
            changes.append({"kind": "split-sentence-join", "before": before[:120], "after": out[-1][:120]})
        else:
            out.append(current)
    return "\n\n".join(out).strip(), changes


def promote_standalone_headings(body: str) -> tuple[str, list[dict]]:
    """Turn paste-surviving title lines into markdown subheadings."""
    blocks = [
        b.strip() for b in _SPLIT_BLANK_RE.split(body.replace("\r\n", "\n").replace("\r", "\n").strip()) if b.strip()
    ]
    out: list[str] = []
    changes: list[dict] = []
    for block in blocks:
        if _looks_like_standalone_heading(block):
            promoted = f"### {' '.join(block.split())}"
            changes.append({"kind": "heading-promoted", "before": block[:120], "after": promoted})
            out.append(promoted)
        else:
            out.append(block)
    return "\n\n".join(out).strip(), changes


def _strip_model_markdown(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^```(?:markdown)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text).strip()
    if text.startswith("## "):
        lines = text.splitlines()
        lines = lines[1:]
        while lines and not lines[0].strip():
            lines.pop(0)
        text = "\n".join(lines).strip()
    return text


def _image_paths(body: str) -> set[str]:
    return {m.group(2) for m in _IMG_MD_RE.finditer(body)}


def _scholar_continuity_prompt(heading: str, base_body: str, repaired_body: str, prepared: dict) -> str:
    return f"""You are the Book Composer's Paste & Fix continuity repair pass for a Sessions-lane Ismaili lecture chapter.

Use the Ismaili Scholar grounding and voice below to repair ONLY the pasted chapter's paragraph flow and explanatory continuity.

Rules:
- Return ONLY the repaired chapter body as markdown. Do not include the chapter's `##` heading.
- Join split sentences and one-line fragments into coherent paragraphs.
- Keep headings, blockquotes, Arabic script, Qur'an citations, lists, and image markdown exactly where they belong.
- You may add a short connecting explanation only where the pasted text has a real gap that would stop a student reader.
- Do not invent doctrine, sources, stories, analogies, or citations. Use only the base chapter, pasted chapter, and Scholar grounding supplied here.
- Preserve the teaching content and all Arabic-script runs from the pasted chapter.

Scholar grounding/context:
{prepared.get("user", "")}

Book's current chapter body before paste:
<<<BASE_CHAPTER
{base_body}
BASE_CHAPTER>>>

Pasted chapter after deterministic paragraph repair:
<<<PASTED_CHAPTER
{repaired_body}
PASTED_CHAPTER>>>
"""


def scholar_continuity_repair(
    book_dir: Path,
    heading: str,
    base_body: str,
    repaired_body: str,
    *,
    log=print,
) -> tuple[str, list[dict]]:
    """Ask the Ismaili Scholar context to repair continuity, then gate it."""
    try:
        prepared = scholar_prepare(
            concept=heading,
            context=repaired_body,
            chapter_context=base_body,
            book_title=book_dir.name,
            question=(
                "Where this pasted lecture chapter has split paragraphs or a "
                "missing explanatory bridge, repair the flow without adding new doctrine."
            ),
        )
    except ScholarBridgeError as e:
        return repaired_body, [{"kind": "scholar-continuity", "status": "skipped", "reason": str(e)}]

    try:
        rc, out, err = _run_claude_p_with_retry(
            _scholar_continuity_prompt(heading, base_body, repaired_body, prepared),
            timeout=900,
            book_dir=book_dir,
            phase="compose-paste-fix",
            step=f"scholar-continuity-{anchor_key(heading)[:48]}",
            log=log,
            **pure_text_call_options(),
        )
    except AuthoringError as e:
        return repaired_body, [{"kind": "scholar-continuity", "status": "skipped", "reason": str(e)}]
    if rc != 0:
        return repaired_body, [{"kind": "scholar-continuity", "status": "skipped", "reason": (err or out)[:240]}]

    candidate = _strip_model_markdown(out)
    gate = revoice_gates(
        repaired_body,
        candidate,
        check_opening=False,
        frame=narrative_frame(book_dir),
        narrator_subject=narrator_subject(book_dir),
    )
    dropped_images = sorted(_image_paths(repaired_body) - _image_paths(candidate))
    if dropped_images:
        gate.append("image markdown dropped: " + ", ".join(dropped_images[:3]))
    if gate:
        return repaired_body, [{"kind": "scholar-continuity", "status": "reverted", "findings": gate}]
    return candidate, [
        {
            "kind": "scholar-continuity",
            "status": "kept",
            "grounded": int(prepared.get("grounded") or 0),
            "morphology": bool(prepared.get("morphology")),
        }
    ]


def student_readability_review(
    book_dir: Path,
    heading: str,
    body: str,
    *,
    log=print,
    scholar_adapter=ask_scholar,
) -> dict:
    """Read the fixed body as a student and prepare proposed Companion cards.

    Paste & Fix remains a check step: this function writes nothing. The Composer
    files these note payloads only if the user applies the fixed chapter.
    """
    budget = chapter_budget(len(body.split()))
    prompt = build_prompt(heading, body, evidence_block(heading, body), budget)
    try:
        rc, out, err = _run_claude_p_with_retry(
            prompt,
            timeout=900,
            book_dir=book_dir,
            phase="0book-student-reader",
            step=f"paste-fix-student-{anchor_key(heading)[:48]}",
            log=log,
            **pure_text_call_options(),
        )
    except AuthoringError as e:
        return {"status": "skipped", "reason": str(e), "questions": []}
    if rc != 0:
        return {"status": "skipped", "reason": (err or out)[:240], "questions": []}

    try:
        candidates = parse_cards(out)
    except Exception as e:
        return {"status": "skipped", "reason": f"unreadable student-reader output: {e}", "questions": []}

    gated, dropped = [], []
    for candidate in candidates:
        ok, reasons = gate_finding(candidate, body)
        if ok:
            gated.append(candidate)
        else:
            dropped.append({"quote": candidate.get("quote"), "reasons": reasons})
    chosen = select(dedupe(gated), body, budget)
    chapter_key = section_key(heading)
    chapter = {"key": chapter_key, "title": heading, "prose": body}
    book_title = book_dir.name
    meta = book_dir / "meta.yml"
    if meta.exists():
        for line in meta.read_text(encoding="utf-8").splitlines():
            if line.startswith("title:"):
                book_title = line.split(":", 1)[1].strip().strip("\"'") or book_title
                break
    answered = [scholar_adapter(c, chapter, book_dir, book_title, log) for c in chosen]
    notes = [a["note"] for a in answered if a and a.get("note")]
    unsourced = [a for a in answered if a and a.get("dropped") == "unsourced"]
    return {
        "status": "checked",
        "budget": budget,
        "proposed": len(candidates),
        "gated_out": dropped,
        "companion_notes": notes,
        "answered": len(notes),
        "unanswered": sum(1 for a in answered if a is None),
        "unsourced": [{"quote": u["quote"], "question": u["question"]} for u in unsourced],
        "questions": [
            {
                "defect": c.get("defect"),
                "question": c.get("question"),
                "quote": c.get("quote"),
            }
            for c in chosen
        ],
    }
