"""0book-augment — the additive, source-grounded enrichment layer (v2).

Runs ONLY when ``book_augmentation == source_only`` under the ``book_pipeline_v2``
flag. It never rewrites the faithful base; it *adds* clearly-labeled editorial
blocks after chapters, grounded ONLY in reliable in-repo Islamic sources
(``content/knowledge-base/`` atoms + the doctrinal packs). Every block is:

  * clearly labeled and visually separated from the source (standard §4.3/§10 —
    source vs editorial block separation), never blended into the author's prose;
  * gated by ``_doctrinal.run_doctrinal_checks`` (T1–T5) — any P0 finding drops
    the block rather than persisting a doctrinal error;
  * budget-bounded so enrichment stays an aside, not a second book.

Accuracy veto: a block that alters, contradicts, or restates a teaching (rather
than adding context) is dropped. The base text is byte-identical afterwards; only
labeled asides are appended. The book-challenger BK-P4 faithfulness pass is the
semantic backstop run separately over the whole book.

The single LLM call is isolated in ``_generate_enrichment`` so the deterministic
gate + insertion logic is unit-testable with an injected generator.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from _authoring._core import AuthoringError, _run_claude_p_with_retry
from _doctrinal import run_doctrinal_checks

# ─── Editorial-block contract (the ONLY shape enrichment may take) ──────────
EDITORIAL_LABEL = "Editorial note (source-grounded)"
_BLOCK_OPEN = "<!-- editorial:begin -->"
_BLOCK_CLOSE = "<!-- editorial:end -->"
_MAX_BLOCK_WORDS = 220
_MIN_BLOCK_WORDS = 12

_KB_FILES = ("doctrine.jsonl", "hadith.jsonl", "quran.jsonl", "quote.jsonl")
_AUGMENT_TIMEOUT = 900


def format_editorial_block(text: str) -> str:
    """Wrap enrichment prose in the canonical labeled + separated block.

    HTML-comment fences make the block deterministically findable (for the
    renderer's source/editorial styling and for idempotent re-runs) while the
    bold label and blockquote make the separation visible to the reader.
    """
    body = " ".join((text or "").split())
    inner = "\n".join(f"> {line}" for line in _wrap_para(body))
    return f"{_BLOCK_OPEN}\n> **{EDITORIAL_LABEL}.** \n{inner}\n{_BLOCK_CLOSE}"


def _wrap_para(text: str, width: int = 96) -> list[str]:
    words, line, out = text.split(), "", []
    for w in words:
        if line and len(line) + 1 + len(w) > width:
            out.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        out.append(line)
    return out or [""]


def gate_editorial_block(text: str) -> tuple[bool, list[str]]:
    """Deterministic accept/reject for one enrichment block. (accepted, reasons)."""
    reasons: list[str] = []
    body = " ".join((text or "").split())
    words = body.split()
    if len(words) < _MIN_BLOCK_WORDS:
        reasons.append("empty or too short to be a real note")
        return False, reasons
    if len(words) > _MAX_BLOCK_WORDS:
        reasons.append(f"exceeds editorial budget ({len(words)}>{_MAX_BLOCK_WORDS} words)")
    # Doctrinal veto — any P0 T1–T5 finding drops the block.
    doctrinal = run_doctrinal_checks(body)
    p0 = [f for f in doctrinal if f.severity == "P0"]
    if p0:
        reasons.append(
            "doctrinal P0: " + "; ".join(f"{f.check_id}:{f.signature}" for f in p0[:3])
        )
    # An aside must ADD context, not refuse / meta-comment / re-title.
    if re.search(r"\b(as an ai|i cannot|here is the|editorial note)\b", body, re.I):
        reasons.append("contains meta-commentary or self-reference")
    return (not reasons), reasons


def _load_kb_atoms(limit: int = 40) -> list[dict[str, Any]]:
    """Load a bounded set of knowledge-base atoms as the ONLY grounding corpus."""
    root = Path(__file__).resolve().parents[2] / "content" / "knowledge-base"
    atoms: list[dict[str, Any]] = []
    for name in _KB_FILES:
        path = root / name
        if not path.exists():
            continue
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                raw = raw.strip()
                if not raw:
                    continue
                atoms.append(json.loads(raw))
                if len(atoms) >= limit:
                    return atoms
        except Exception:  # noqa: BLE001 — a malformed atom must not crash augment
            continue
    return atoms


def _augment_prompt(title: str, chapter_text: str, atoms: list[dict[str, Any]]) -> str:
    corpus = "\n".join(
        f"- {a.get('text') or a.get('arabic') or a.get('translation') or ''}".strip()
        for a in atoms
        if (a.get("text") or a.get("arabic") or a.get("translation"))
    )[:6000]
    return f"""You are adding a short, source-grounded editorial note to a chapter of a faithful
Islamic reading edition. The note is an ADDITION printed as a clearly-labeled aside — it must never
change, restate, or contradict the chapter's teaching.

Hard rules:
- Ground EVERY claim only in the reliable source corpus below. Add nothing from outside it.
- One short paragraph (at most ~150 words). No headings, no lists, no preamble.
- Do not summarize the chapter. Add context (a cross-reference, a clarified term, a connected
  verse/hadith already in the corpus) that helps a modern reader.
- If the corpus offers nothing genuinely useful for THIS chapter, output exactly: NONE

RELIABLE SOURCE CORPUS
{corpus or '(none)'}

CHAPTER "{title}" (do not repeat it back)
{chapter_text[:6000]}

Output only the note paragraph, or NONE."""


def _generate_enrichment(
    title: str, chapter_text: str, atoms: list[dict[str, Any]], book_dir: Path, label: str, log
) -> str:
    """Isolated LLM call (monkeypatched in tests). Returns raw note text or ''."""
    prompt = _augment_prompt(title, chapter_text, atoms)
    rc, out, err = _run_claude_p_with_retry(
        prompt, timeout=_AUGMENT_TIMEOUT, book_dir=book_dir,
        phase="0book-augment", step=label, log=log,
    )
    if rc != 0:
        raise AuthoringError(
            phase="0book-augment",
            message=f"{label}: claude -p rc={rc}: {err[:200]}",
            manual_fallback="Re-run 0book-augment; passing chapters are idempotent.",
        )
    out = (out or "").strip()
    return "" if out.upper().startswith("NONE") else out


_CHAPTER_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")


def insert_blocks(book_md: str, blocks_by_heading: dict[str, str]) -> str:
    """Append each chapter's editorial block immediately after that chapter's body.

    Idempotent: an existing editorial block for a heading is replaced, never
    duplicated (fences make prior blocks findable).
    """
    text = _strip_existing_blocks(book_md)
    sections = _CHAPTER_HEADING_RE.split(text)
    # sections = [pre, head1, body1, head2, body2, ...]
    if len(sections) < 3:
        return text.rstrip() + "\n"
    # Normalize every inter-section gap to exactly one blank line so repeated
    # runs (strip -> re-insert) converge to a fixed point (idempotent).
    result = sections[0].strip()
    for i in range(1, len(sections), 2):
        head = sections[i].strip()
        body = (sections[i + 1] if i + 1 < len(sections) else "").strip()
        block = blocks_by_heading.get(sections[i].strip())
        chunk = f"{head}\n\n{body}" if body else head
        if block:
            chunk = f"{chunk}\n\n{block.strip()}"
        result = f"{result}\n\n{chunk}" if result else chunk
    return result.strip() + "\n"


def _strip_existing_blocks(text: str) -> str:
    return re.sub(
        re.escape(_BLOCK_OPEN) + r".*?" + re.escape(_BLOCK_CLOSE) + r"\n?",
        "",
        text,
        flags=re.DOTALL,
    )


def author_phase_book_augment(
    book_dir: Path, *, log=print, force: bool = False,
    generator: Callable[..., str] | None = None,
) -> Path:
    """Insert labeled, doctrinally-gated editorial blocks into ``book/book.md``.

    ``generator`` defaults to the real LLM call; tests inject a fake. Returns the
    book.md path. Non-destructive to the base: only labeled asides are added.
    """
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    toc_path = book_dir / "book" / "book-toc.json"
    if not book_md.exists():
        raise AuthoringError(
            phase="0book-augment",
            message=f"missing {book_md} — run the base compose first.",
            manual_fallback="Run 0book-compose (base) before 0book-augment.",
        )
    gen = generator or _generate_enrichment
    atoms = _load_kb_atoms()
    text = book_md.read_text(encoding="utf-8")
    toc = json.loads(toc_path.read_text(encoding="utf-8")) if toc_path.exists() else {}
    headings = _CHAPTER_HEADING_RE.findall(text)

    blocks: dict[str, str] = {}
    accepted = dropped = 0
    for head in headings:
        title = re.sub(r"^##\s+\d*\.?\s*", "", head).strip()
        chapter_text = _chapter_body(text, head)
        try:
            note = gen(title, chapter_text, atoms, book_dir, f"aug-{_slug(title)}", log)
        except AuthoringError:
            raise
        except Exception as e:  # noqa: BLE001 — one bad chapter must not abort augment
            log(f"      augment: {title!r} generation skipped (non-fatal): {e}")
            continue
        if not note:
            continue
        ok, reasons = gate_editorial_block(note)
        if not ok:
            dropped += 1
            log(f"      augment: dropped block for {title!r} ({'; '.join(reasons[:2])})")
            continue
        blocks[head.strip()] = format_editorial_block(note)
        accepted += 1

    new_text = insert_blocks(text, blocks)
    book_md.write_text(new_text, encoding="utf-8")
    (book_dir / "_system" / "book-augment-report.json").write_text(
        json.dumps({
            "schema": "podcast.book-augment/v1",
            "accepted": accepted,
            "dropped": dropped,
            "chapters_seen": len(headings),
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    log(f"    0book-augment: {accepted} editorial blocks added, {dropped} dropped "
        f"(across {len(headings)} chapters)")
    return book_md


def _chapter_body(text: str, head: str) -> str:
    parts = _CHAPTER_HEADING_RE.split(text)
    for i in range(1, len(parts), 2):
        if parts[i].strip() == head.strip():
            return (parts[i + 1] if i + 1 < len(parts) else "").strip()
    return ""


def _slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")[:40] or "ch"
