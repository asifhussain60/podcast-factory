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

from _arabic_coverage import arabic_run_spans, arabic_span_is_grounded
from _authoring._core import AuthoringError, _run_claude_p_with_retry
from _book_edits import anchor_key, edited_chapter_keys
from _book_fences import strip_spans
from _corpus_retrieval import RetrievalIndex, UsedLedger, attribute_used
from _doctrinal import run_doctrinal_checks
from _narrator_policy import atom_narrator, disallowed_narrator

# ─── Editorial-block contract (the ONLY shape enrichment may take) ──────────
# "tradition-grounded", not "source-grounded": the atoms come from the
# knowledge-base corpus (other works of the same tradition), and a published
# edition may not label corpus material as this book's own (BK1007,
# challenger 2026-07-22). The note prose must likewise never claim "the
# book's own teaching" for corpus-derived content — see the prompt below.
EDITORIAL_LABEL = "Editorial note (tradition-grounded)"
_BLOCK_OPEN = "<!-- editorial:begin -->"
_BLOCK_CLOSE = "<!-- editorial:end -->"
_MAX_BLOCK_WORDS = 220
_MIN_BLOCK_WORDS = 12

# ``etymology.jsonl`` carries the root/derivative atoms. Its shape already fits
# the retrieval contract (``body.text_en`` for prose, ``term`` /
# ``root_transliteration`` / ``derivatives[].term`` as the high-signal keywords
# ``_corpus_retrieval._atom_keywords`` already weights), so a companion book can
# ground a clarified term in a real root instead of the model's own recall.
_KB_FILES = ("doctrine.jsonl", "hadith.jsonl", "quran.jsonl", "quote.jsonl", "etymology.jsonl")
_AUGMENT_TIMEOUT = 900

# Per-passage retrieval: each chapter draws only the atoms genuinely related to
# ITS text, above a relevance floor, instead of the old fixed 40-atom slice that
# was reused identically on every chapter. Below the floor a chapter simply gets
# no note (never a forced, low-relevance injection).
_ATOMS_PER_CHAPTER = 8
_RELEVANCE_THRESHOLD = 0.08

# Corpus-snippet bounds: KB atoms store their text under ``body.text_en`` and can
# be full chapter chunks (thousands of chars). Trim each to a short grounding
# snippet so MANY diverse atoms fit the corpus budget instead of one giant chunk.
_ATOM_SNIPPET_CHARS = 280
_ATOM_MIN_CHARS = 25
_CORPUS_CHARS = 6000
_MD_HEADER_RE = re.compile(r"(?m)^#+\s.*$")
# Line-leading blockquote markers in model output — stripped before the editorial
# wrap adds its own, so the two can never compound into `> >`.
_QUOTE_PREFIX_RE = re.compile(r"(?m)^[ \t]*>+[ \t]?")
_INLINE_MARKUP_RE = re.compile(r"⟪[^⟫]*⟫")


def atom_text(atom: dict[str, Any]) -> str:
    """The human-readable English text of a KB atom, cleaned for grounding.

    Atoms store their text at ``body.text_en`` (doctrine/hadith/quran/quote all
    share this shape); older/foreign shapes may use a top-level field. Markdown
    headers and inline ``⟪ar:…⟫`` markup are stripped so the corpus is clean prose.
    """
    body = atom.get("body") if isinstance(atom.get("body"), dict) else {}
    text = (
        body.get("text_en")
        or atom.get("text")
        or atom.get("arabic")
        or atom.get("translation")
        or body.get("translation")
        or ""
    )
    text = _MD_HEADER_RE.sub("", text)
    text = _INLINE_MARKUP_RE.sub("", text)
    return " ".join(text.split())


def format_editorial_block(text: str) -> str:
    """Wrap enrichment prose in the canonical labeled + separated block.

    HTML-comment fences make the block deterministically findable (for the
    renderer's source/editorial styling and for idempotent re-runs) while the
    bold label and blockquote make the separation visible to the reader.

    The model's prose is stripped of any blockquote markers it wrote for itself
    BEFORE the wrap adds exactly one. A model that opened its own quote used to
    have that marker preserved by the whitespace collapse below and then get a
    second one here, and `> > **A clarified term for this chapter.**` reached the
    reading edition with the ">" printed mid-sentence (the-master-and-the-disciple,
    chapter 2). Stripping is per LINE and before the collapse, so a ">" inside
    the prose itself is untouched.
    """
    body = " ".join(_QUOTE_PREFIX_RE.sub("", text or "").split())
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


def gate_editorial_block(text: str, atoms: list[dict[str, Any]] | None = None) -> tuple[bool, list[str]]:
    """Deterministic accept/reject for one enrichment block. (accepted, reasons).

    ``atoms`` is the corpus the note was grounded in. When supplied, any Arabic
    script in the note must be copied from it — an editorial aside is the one place
    in the edition where the model writes freely, so it is the one place Arabic can
    enter from memory rather than from a source.
    """
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
        reasons.append("doctrinal P0: " + "; ".join(f"{f.check_id}:{f.signature}" for f in p0[:3]))
    # An aside must ADD context, not refuse / meta-comment / re-title.
    if re.search(r"\b(as an ai|i cannot|here is the|editorial note)\b", body, re.I):
        reasons.append("contains meta-commentary or self-reference")
    # Arabic script must be COPIED from the corpus the note was grounded in.
    if atoms is not None:
        corpus_arabic = "\n".join(_atom_arabic(a) for a in atoms)
        for span in arabic_run_spans(body, min_chars=2):
            if not arabic_span_is_grounded(span, corpus_arabic):
                reasons.append(f"Arabic not copied from the corpus: {span[:40]}")
                break
    return (not reasons), reasons


def _atom_arabic(atom: dict[str, Any]) -> str:
    """Every Arabic string an atom carries — the allowed Arabic for a note built on it."""
    body = atom.get("body") if isinstance(atom.get("body"), dict) else {}
    return "\n".join(
        str(body[k]) for k in ("arabic", "text_ar", "root") if isinstance(body.get(k), str) and body[k].strip()
    )


def _load_kb_atoms(limit: int = 40) -> list[dict[str, Any]]:
    """Load a bounded, type-balanced set of knowledge-base atoms as the corpus.

    A per-file quota guarantees verses, hadith, quotes AND doctrine are all
    represented — a flat first-N read would fill the whole budget from
    ``doctrine.jsonl`` alone (it is the first file and larger than ``limit``),
    starving the corpus of scripture the model could cross-reference.
    """
    root = Path(__file__).resolve().parents[2] / "content" / "knowledge-base"
    per_file = max(1, limit // len(_KB_FILES))
    atoms: list[dict[str, Any]] = []
    for name in _KB_FILES:
        path = root / name
        if not path.exists():
            continue
        taken = 0
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                if taken >= per_file or len(atoms) >= limit:
                    break
                raw = raw.strip()
                if not raw:
                    continue
                atom = json.loads(raw)
                if disallowed_narrator(atom_narrator(atom)):
                    continue
                atoms.append(atom)
                taken += 1
        except Exception:
            continue
    return atoms[:limit]


def _load_all_kb_atoms() -> list[dict[str, Any]]:
    """Load the ENTIRE knowledge-base corpus for per-passage retrieval.

    Unlike ``_load_kb_atoms`` (a fixed head-of-file slice, kept only for the
    self-study path's back-compat), this reads every atom so the retrieval index
    can pick the ones actually relevant to each chapter.
    """
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
                atom = json.loads(raw)
                if disallowed_narrator(atom_narrator(atom)):
                    continue
                atoms.append(atom)
        except Exception:
            continue
    return atoms


def _atom_label(atom: dict[str, Any]) -> str:
    """Prefix that tells the model WHAT a corpus line is, when the prose alone hides it.

    An etymology atom's ``text_en`` reads as free prose ("The root means to sell…")
    with the term itself only in a sibling field, so an unlabeled line cannot be
    cited accurately. Every other atom type reads as its own citation already and
    gets no prefix — the corpus stays flat prose except where a label earns itself.
    """
    if atom.get("type") != "etymology":
        return ""
    body = atom.get("body") if isinstance(atom.get("body"), dict) else {}
    term = str(body.get("term") or "").strip()
    root = str(body.get("root_transliteration") or "").strip()
    if not term:
        return ""
    return f"ETYMOLOGY — {term}" + (f" (root {root})" if root else "") + ": "


def _augment_prompt(title: str, chapter_text: str, atoms: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for a in atoms:
        snippet = atom_text(a)
        if len(snippet) >= _ATOM_MIN_CHARS:
            lines.append(f"- {_atom_label(a)}{snippet[:_ATOM_SNIPPET_CHARS]}")
    corpus = "\n".join(lines)[:_CORPUS_CHARS]
    return f"""You are adding a short, tradition-grounded editorial note to a chapter of a faithful
Islamic reading edition. The note is an ADDITION printed as a clearly-labeled aside — it must never
change, restate, or contradict the chapter's teaching.

Hard rules:
- Ground EVERY claim only in the reliable source corpus below. Add nothing from outside it.
- The corpus lines come from OTHER works of the same tradition, NOT from this book. Never attribute
  them to this book: no "the book's own teaching", no "elsewhere in this same teaching", no "this
  chapter elsewhere". Introduce them honestly — "a related teaching preserved in this tradition",
  "the wider tradition records", or name nothing at all.
- One short paragraph (at most ~150 words). No headings, no lists, no preamble.
- Do not summarize the chapter. Add context (a cross-reference, a clarified term, a connected
  verse/hadith already in the corpus) that helps a modern reader.
- When a corpus line marked ETYMOLOGY explains a term this chapter actually leans on, prefer it:
  the root and its derivatives are exactly the kind of clarification a reader cannot supply alone.
- Any Arabic script you write MUST be copied character-for-character from a corpus line above.
  Never reconstruct Arabic from memory. If you cannot copy it, write the term in plain English only.
- If the corpus offers nothing genuinely useful for THIS chapter, output exactly: NONE

RELIABLE SOURCE CORPUS
{corpus or "(none)"}

CHAPTER "{title}" (do not repeat it back)
{chapter_text[:6000]}

Output only the note paragraph, or NONE."""


def _generate_enrichment(
    title: str, chapter_text: str, atoms: list[dict[str, Any]], book_dir: Path, label: str, log
) -> str:
    """Isolated LLM call (monkeypatched in tests). Returns raw note text or ''."""
    prompt = _augment_prompt(title, chapter_text, atoms)
    rc, out, err = _run_claude_p_with_retry(
        prompt,
        timeout=_AUGMENT_TIMEOUT,
        book_dir=book_dir,
        phase="0book-augment",
        step=label,
        log=log,
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


def insert_blocks(book_md: str, blocks_by_position: dict[int, str]) -> str:
    """Append each chapter's editorial block immediately after that chapter's body.

    Keyed by 1-based section POSITION, not by heading text. Heading text is not
    unique — two chapters may legitimately carry the same title — and keying by it
    gave both of them whichever block was generated last while the other silently
    got none.

    Idempotent: an existing editorial block for a section is replaced, never
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
        block = blocks_by_position.get(i // 2 + 1)
        chunk = f"{head}\n\n{body}" if body else head
        if block:
            chunk = f"{chunk}\n\n{block.strip()}"
        result = f"{result}\n\n{chunk}" if result else chunk
    return result.strip() + "\n"


def _strip_existing_blocks(text: str) -> str:
    """Remove prior editorial blocks so a re-run replaces rather than stacks.

    Matches the bare-marker form too (see ``_book_fences``): a block whose fence a
    Composer round-trip flattened is still THIS pass's own prior output, and
    failing to recognise it is how the same aside ends up printed twice.
    """
    return strip_spans(text, "editorial", trailing=r"\n?")


def author_phase_book_augment(
    book_dir: Path,
    *,
    log=print,
    force: bool = False,
    generator: Callable[..., str] | None = None,
) -> Path:
    """Insert labeled, doctrinally-gated editorial blocks into ``book/book.md``.

    ``generator`` defaults to the real LLM call; tests inject a fake. Returns the
    book.md path. Non-destructive to the base: only labeled asides are added.
    """
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        raise AuthoringError(
            phase="0book-augment",
            message=f"missing {book_md} — run the base compose first.",
            manual_fallback="Run 0book-compose (base) before 0book-augment.",
        )
    gen = generator or _generate_enrichment
    text = book_md.read_text(encoding="utf-8")
    headings = _CHAPTER_HEADING_RE.findall(text)
    # A chapter the human authored in the Book Composer gets no editorial block:
    # an aside is an addition to the pipeline's own prose, and adding one to
    # someone else's page — every run, unasked — is not enrichment.
    authored = set() if force else edited_chapter_keys(book_dir)

    # One retrieval index over the WHOLE corpus, queried per chapter; a per-book
    # ledger so no atom is injected into more than one chapter of THIS book (a
    # within-book rule only — atoms are free to reappear in other books).
    index = RetrievalIndex(_load_all_kb_atoms())
    ledger = UsedLedger(book_dir).reset()

    blocks: dict[int, str] = {}
    per_chapter: list[dict[str, Any]] = []
    accepted = dropped = no_relevant = 0
    authored_skipped = 0
    for position, head in enumerate(headings, start=1):
        title = re.sub(r"^##\s+\d*\.?\s*", "", head).strip()
        if anchor_key(head) in authored:
            authored_skipped += 1
            per_chapter.append({"chapter": title, "selected": [], "note": "Composer edit — not augmented"})
            continue
        chapter_text = _chapter_body(text, position)
        selected = index.select(
            chapter_text,
            k=_ATOMS_PER_CHAPTER,
            threshold=_RELEVANCE_THRESHOLD,
            exclude_ids=ledger.used(),
        )
        if not selected:
            no_relevant += 1
            per_chapter.append({"chapter": title, "selected": [], "note": "no atom above relevance floor"})
            continue
        atoms = [s.atom for s in selected]
        try:
            note = gen(title, chapter_text, atoms, book_dir, f"aug-{_slug(title)}", log)
        except AuthoringError:
            raise
        except Exception as e:
            log(f"      augment: {title!r} generation skipped (non-fatal): {e}")
            continue
        if not note:
            continue
        ok, reasons = gate_editorial_block(note, atoms)
        if not ok:
            dropped += 1
            log(f"      augment: dropped block for {title!r} ({'; '.join(reasons[:2])})")
            continue
        # Mark only the atoms the note actually drew on as used, so later chapters
        # are not starved of good atoms that were merely shown but never woven in.
        used_ids = attribute_used(note, atoms)
        ledger.record(used_ids)
        blocks[position] = format_editorial_block(note)
        accepted += 1
        per_chapter.append(
            {
                "chapter": title,
                "selected": [{"id": s.id, "score": round(s.score, 4)} for s in selected],
                "used": used_ids,
            }
        )

    new_text = insert_blocks(text, blocks)
    book_md.write_text(new_text, encoding="utf-8")
    (book_dir / "_system" / "book-augment-report.json").write_text(
        json.dumps(
            {
                "schema": "podcast.book-augment/v3",
                "accepted": accepted,
                "dropped": dropped,
                "chapters_seen": len(headings),
                "chapters_no_relevant_atom": no_relevant,
                "chapters_composer_authored": authored_skipped,
                "atoms_per_chapter": _ATOMS_PER_CHAPTER,
                "relevance_threshold": _RELEVANCE_THRESHOLD,
                "per_chapter": per_chapter,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    log(
        f"    0book-augment: {accepted} editorial blocks added, {dropped} dropped, "
        f"{no_relevant} chapters had no relevant atom (across {len(headings)} chapters)"
        + (f", {authored_skipped} Composer-authored and left alone" if authored_skipped else "")
    )
    return book_md


def _chapter_body(text: str, position: int) -> str:
    """The body of the 1-based ``position``-th ``##`` section.

    By position rather than by heading text, for the same reason ``insert_blocks``
    is: two chapters may share a title, and matching on the text handed both of
    them the FIRST one's body — so the second was enriched against a page it does
    not contain.
    """
    parts = _CHAPTER_HEADING_RE.split(text)
    i = position * 2 - 1
    if 1 <= i < len(parts):
        return (parts[i + 1] if i + 1 < len(parts) else "").strip()
    return ""


def _slug(text: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")[:40] or "ch"
