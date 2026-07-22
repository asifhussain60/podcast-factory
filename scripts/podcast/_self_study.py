"""_self_study.py — materialize book/book-self-study.md from book.md.

The render-time self-study layer (book-html.mjs, opt-in `selfStudy`) renders
labeled Contextual-note and Study-summary asides from HTML-comment fences. This
module GENERATES that content and injects the fences, producing a separate
``book/book-self-study.md`` — the base ``book/book.md`` is never mutated, so the
reading edition is untouched.

Two per-chapter blocks are added:

  * a source-grounded **Contextual note** — reuses the (fixed) 0book-augment
    enrichment: KB-atom-grounded, doctrinally gated, additive only; and
  * a **Study summary** — Decision 1 (2026-07-17): a LABELED study-summary is the
    explicit, scoped exception to the anti-summary rule. It is drawn ONLY from the
    chapter's own teaching (no outside content, no new claims) and passes a
    faithfulness gate before it is kept.

Both use ``claude -p`` (flat-rate; $0 tracked spend). Idempotent: regenerating
rebuilds book-self-study.md from the clean base each run.
"""

from __future__ import annotations

import re
from pathlib import Path

from _authoring._core import AuthoringError, _run_claude_p_with_retry
from _book_augment import (
    _BLOCK_CLOSE,
    _BLOCK_OPEN,
    _CHAPTER_HEADING_RE,
    _MAX_BLOCK_WORDS,
    _MIN_BLOCK_WORDS,
    _generate_enrichment,
    _load_kb_atoms,
    _slug,
    format_editorial_block,
    gate_editorial_block,
)

# ─── Study-summary block contract (mirrors the editorial fence shape) ───────
SUMMARY_LABEL = "Study summary"
_SUMMARY_OPEN = "<!-- study-summary:begin -->"
_SUMMARY_CLOSE = "<!-- study-summary:end -->"
_SUMMARY_TIMEOUT = 900

# A summary that merely re-teaches, cites the future, or runs long is dropped.
_META_PHRASES = ("in this chapter", "the author", "this summary", "we will", "as we saw")


def check_self_study_markdown(text: str) -> list[dict[str, str]]:
    """Deterministic structural gate over a materialized self-study markdown.

    Returns a list of findings (empty == clean). This is the machine half of the
    Step-7 gate — the fence/label/term-once contract the render layer relies on.
    The SEMANTIC half (summary/note faithfulness) is the book-challenger's job.
    """
    findings: list[dict[str, str]] = []

    def add(check: str, detail: str) -> None:
        findings.append({"check": check, "detail": detail})

    for open_, close_, name in (
        (_BLOCK_OPEN, _BLOCK_CLOSE, "editorial"),
        (_SUMMARY_OPEN, _SUMMARY_CLOSE, "study-summary"),
    ):
        n_open, n_close = text.count(open_), text.count(close_)
        if n_open != n_close:
            add("SS-FENCE-BALANCE", f"{name}: {n_open} begin vs {n_close} end fences")

    # Every fenced aside must carry its bold label line.
    for open_, close_, label in (
        (_BLOCK_OPEN, _BLOCK_CLOSE, "Editorial note"),
        (_SUMMARY_OPEN, _SUMMARY_CLOSE, SUMMARY_LABEL),
    ):
        for m in re.finditer(re.escape(open_) + r"(.*?)" + re.escape(close_), text, re.DOTALL):
            if f"**{label}" not in m.group(1):
                add("SS-ASIDE-LABEL", f"aside missing its '{label}' label")
                break

    return findings


def format_summary_block(text: str) -> str:
    """Wrap a study summary in the canonical labeled + fenced block."""
    from _book_augment import _wrap_para

    body = " ".join((text or "").split())
    inner = "\n".join(f"> {line}" for line in _wrap_para(body))
    return f"{_SUMMARY_OPEN}\n> **{SUMMARY_LABEL}.** \n{inner}\n{_SUMMARY_CLOSE}"


def gate_summary(text: str) -> tuple[bool, list[str]]:
    """Deterministic accept/reject for one study summary. (accepted, reasons)."""
    reasons: list[str] = []
    body = " ".join((text or "").split())
    words = len(body.split())
    if not body or body.upper().startswith("NONE"):
        return False, ["empty/NONE"]
    if words < _MIN_BLOCK_WORDS:
        reasons.append(f"too short ({words}w)")
    if words > _MAX_BLOCK_WORDS:
        reasons.append(f"too long ({words}w)")
    low = body.lower()
    for phrase in _META_PHRASES:
        if phrase in low:
            reasons.append(f"meta/self-referential: {phrase!r}")
            break
    if body.count("#") or _SUMMARY_OPEN in body:
        reasons.append("contains markup")
    return (not reasons), reasons


def _summary_prompt(title: str, chapter_text: str) -> str:
    return f"""You are writing a short STUDY SUMMARY for a self-study reading edition — a study
aid printed as a clearly-labeled box after the chapter. It condenses what the chapter itself
teaches so a reader studying without a teacher can review the essentials.

Hard rules:
- Draw ONLY from the chapter below. Add nothing from outside it; introduce no new claim,
  ruling, name, citation, or example that is not already in the chapter.
- 2 to 4 sentences, plain declarative prose. No heading, no list, no preamble, no meta
  ("in this chapter", "the author"), no reference to other chapters.
- State the chapter's key teachings directly, as settled points — not a description of the
  chapter. If the chapter is too slight to summarize faithfully, output exactly: NONE

CHAPTER "{title}"
{chapter_text[:7000]}

Output only the summary prose, or NONE."""


def _generate_summary(title: str, chapter_text: str, book_dir: Path, label: str, log) -> str:
    rc, out, err = _run_claude_p_with_retry(
        _summary_prompt(title, chapter_text),
        timeout=_SUMMARY_TIMEOUT,
        book_dir=book_dir,
        phase="0book-self-study",
        step=label,
        log=log,
    )
    if rc != 0:
        raise AuthoringError(
            phase="0book-self-study",
            message=f"{label}: claude -p rc={rc}: {err[:200]}",
            manual_fallback="Re-run --self-study; passing chapters are idempotent.",
        )
    out = (out or "").strip()
    return "" if out.upper().startswith("NONE") else out


def _strip_all_fences(text: str) -> str:
    """Remove any prior editorial + study-summary fenced blocks (idempotency)."""
    for open_, close_ in ((_BLOCK_OPEN, _BLOCK_CLOSE), (_SUMMARY_OPEN, _SUMMARY_CLOSE)):
        text = re.sub(re.escape(open_) + r".*?" + re.escape(close_) + r"\n?", "", text, flags=re.DOTALL)
    return text


# ─── Intra-chapter sub-headings (Step 6 / Decision 2) ───────────────────────
# Source-derived sub-headings already render (renderMd turns the source's own
# unnumbered ## markers into section headings). This is the LIGHT AI pass for
# chapters that have NONE: conservative, navigation-only titles, skipped on any
# anchor miss. Titles add no teaching.
_NUMBERED_RE = re.compile(r"^##\s+\d+\.\s+")
_SUBHEADING_MIN_WORDS = 600  # only sub-title genuinely long, unbroken chapters
_SUBHEADING_MAX = 4
_SUBHEADING_TIMEOUT = 900


def _iter_chapters(text: str) -> tuple[str, list[list[str]]]:
    """Group ``## `` sections into (preamble, [[head, body], ...]) CHAPTERS.

    A chapter head is a numbered ``## N. Title`` or the FIRST heading (the
    preface). An unnumbered, non-first heading is a source SUB-SECTION and is
    folded back into the current chapter's body — so summaries/notes are keyed to
    real chapters, never to a source sub-heading or an AI-inserted sub-title.
    """
    parts = _CHAPTER_HEADING_RE.split(text)
    pre = parts[0]
    chapters: list[list[str]] = []
    seen = False
    for i in range(1, len(parts), 2):
        head = parts[i].strip()
        body = (parts[i + 1] if i + 1 < len(parts) else "").strip()
        if _NUMBERED_RE.match(head) or not seen:
            chapters.append([head, body])
            seen = True
        elif chapters:
            chapters[-1][1] = f"{chapters[-1][1]}\n\n{head}\n\n{body}".strip()
        else:
            pre = f"{pre}\n\n{head}\n\n{body}"
    return pre, chapters


def _subheading_prompt(title: str, body: str, n: int) -> str:
    return f"""You are proposing up to {n} short NAVIGATION sub-headings for one long chapter of a
self-study reading edition, so the reader can find their place. They are labels only — they add
no teaching and must not paraphrase or editorialize.

For each sub-heading output one line: TITLE || ANCHOR
- TITLE: a short noun phrase, <= 6 words, no trailing punctuation.
- ANCHOR: copy the FIRST 8-12 words of the paragraph the sub-heading should sit ABOVE, VERBATIM
  from the chapter (so it can be located exactly). Never anchor the very first paragraph.
Choose natural topic shifts only; fewer is better. If the chapter does not need sub-headings,
output exactly: NONE

CHAPTER "{title}"
{body[:9000]}

Output only TITLE || ANCHOR lines, or NONE."""


def _generate_subheadings(title: str, body: str, book_dir: Path, log) -> list[tuple[str, str]]:
    """Return [(title, anchor), ...] from the model; [] on NONE/failure."""
    rc, out, err = _run_claude_p_with_retry(
        _subheading_prompt(title, body, _SUBHEADING_MAX),
        timeout=_SUBHEADING_TIMEOUT,
        book_dir=book_dir,
        phase="0book-self-study",
        step=f"subhead-{_slug(title)}",
        log=log,
    )
    if rc != 0 or not out or out.strip().upper().startswith("NONE"):
        return []
    pairs: list[tuple[str, str]] = []
    for line in out.splitlines():
        if "||" not in line:
            continue
        t, _, a = line.partition("||")
        t, a = t.strip().lstrip("#").strip(), a.strip()
        if t and a and len(t.split()) <= 8:
            pairs.append((t, a))
    return pairs[:_SUBHEADING_MAX]


def _insert_subheadings(body: str, pairs: list[tuple[str, str]], log, title: str) -> str:
    """Insert ``## <sub-title>`` before each paragraph whose text starts with ANCHOR.

    Conservative: an anchor that is missing OR occurs more than once is skipped
    (never guessed), mirroring the slide-import anchor discipline.
    """
    paras = re.split(r"\n{2,}", body)
    norm = [" ".join(p.split()) for p in paras]
    for sub_title, anchor in pairs:
        key = " ".join(anchor.split()).lower()
        hits = [i for i, p in enumerate(norm) if p.lower().startswith(key)]
        if len(hits) != 1 or hits[0] == 0:
            log(
                f"      self-study: sub-heading {sub_title!r} skipped (anchor {'ambiguous' if len(hits) > 1 else 'not found'})"
            )
            continue
        idx = hits[0]
        if paras[idx].lstrip().startswith("## "):
            continue
        paras[idx] = f"## {sub_title}\n\n{paras[idx]}"
    return "\n\n".join(paras)


def _has_internal_subheadings(body: str) -> bool:
    return bool(re.search(r"(?m)^##\s+\S", body))


# ─── Inline term definitions at first use (Step 3) ──────────────────────────
# A self-study reader meets unfamiliar terms; the FIRST time a glossary term
# appears in the prose we inline "term (short definition)". Conservative: only
# CONCEPT terms (the model drops names/titles), only plain-prose lines (never
# Arabic script, blockquotes, headings or fences), whole-phrase match, once per
# book. Definitions come from claude -p (flat-rate), grounded in scholarly usage.
_TERM_TIMEOUT = 900
_MAX_TERMS = 60


def _glossary_terms(book_dir: Path) -> list[str]:
    """Transliterated glossary terms, longest-first so multi-word terms win."""
    path = book_dir / "_system" / "glossary.yml"
    if not path.exists():
        return []
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    terms = set()
    for e in data.get("entries") or []:
        t = str(e.get("transliteration") or e.get("phonetic") or "").strip()
        if 2 < len(t) <= 40:
            terms.add(t)
    return sorted(terms, key=lambda s: (-len(s), s.lower()))


def _is_plain_prose_line(line: str) -> bool:
    s = line.lstrip()
    if not s or s.startswith(("#", ">", "<!--", "<", "-", "*", "|")):
        return False
    # skip lines carrying Arabic script (mushaf / inline Arabic)
    return not re.search(r"[؀-ۿ]", line)


def _term_defs_prompt(items: list[tuple[str, str]]) -> str:
    listing = "\n".join(f"- {t} — context: {ctx}" for t, ctx in items)
    return f"""For a self-study Islamic reading edition, write a VERY short gloss for each term below, to
be printed inline the first time the term appears: term (definition).

Rules:
- Define CONCEPTS only. If a term is a proper name, a place, a book title, or otherwise not a
  concept a student needs defined, output its definition as exactly: SKIP
- Each definition <= 10 words, plain, grounded in standard Islamic scholarly usage, no citation,
  no "refers to"/"is the", just the gloss. Match the sense shown by the context.
- Output one line per term, EXACTLY: term :: definition   (or)   term :: SKIP

TERMS
{listing}

Output only the `term :: ...` lines."""


def _generate_term_defs(items: list[tuple[str, str]], book_dir: Path, log) -> dict[str, str]:
    rc, out, err = _run_claude_p_with_retry(
        _term_defs_prompt(items),
        timeout=_TERM_TIMEOUT,
        book_dir=book_dir,
        phase="0book-self-study",
        step="term-defs",
        log=log,
    )
    if rc != 0 or not out:
        return {}
    defs: dict[str, str] = {}
    for line in out.splitlines():
        if "::" not in line:
            continue
        term, _, d = line.partition("::")
        term, d = term.strip().lstrip("-").strip(), d.strip()
        if term and d and d.upper() != "SKIP" and len(d.split()) <= 12:
            defs[term] = d
    return defs


def _apply_term_definitions(text: str, book_dir: Path, log) -> tuple[str, int]:
    """Inline `term (definition)` at each glossary term's first prose occurrence."""
    terms = _glossary_terms(book_dir)
    if not terms:
        return text, 0
    lines = text.split("\n")

    # First pass: find each term's first plain-prose line + a short context.
    first: dict[str, int] = {}
    context: dict[str, str] = {}
    patterns = {t: re.compile(rf"(?<![\w-])({re.escape(t)})(?![\w-])", re.IGNORECASE) for t in terms}
    for i, line in enumerate(lines):
        if not _is_plain_prose_line(line):
            continue
        for t in terms:
            if t in first:
                continue
            m = patterns[t].search(line)
            if m:
                first[t] = i
                context[t] = " ".join(line.split())[:160]
    if not first:
        return text, 0

    items = [(t, context[t]) for t in list(first)[:_MAX_TERMS]]
    defs = _generate_term_defs(items, book_dir, log)
    if not defs:
        return text, 0

    inserted = 0
    for t, i in first.items():
        d = defs.get(t)
        if not d:
            continue
        line = lines[i]
        # skip if the first occurrence is already parenthesised
        m = patterns[t].search(line)
        if not m:
            continue
        after = line[m.end() : m.end() + 1]
        if after == "(":
            continue
        lines[i] = line[: m.end()] + f" ({d})" + line[m.end() :]
        inserted += 1
    return "\n".join(lines), inserted


def build_self_study_markdown(
    book_dir: Path,
    *,
    log=print,
    with_notes: bool = True,
    with_subheadings: bool = True,
    with_term_defs: bool = True,
) -> Path:
    """Generate book/book-self-study.md from book/book.md. Returns its path."""
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        raise AuthoringError(
            phase="0book-self-study",
            message=f"missing {book_md} — run 0book-compose first.",
            manual_fallback="Run 0book-compose (base) before --self-study.",
        )

    text = _strip_all_fences(book_md.read_text(encoding="utf-8"))
    atoms = _load_kb_atoms() if with_notes else []
    pre, chapters = _iter_chapters(text)

    out_parts = [pre.strip()] if pre.strip() else []
    summaries = notes = subheads = dropped = 0
    for head, body in chapters:
        title = re.sub(r"^##\s+\d*\.?\s*", "", head).strip()

        # Step 6 — sub-headings on the BODY, before blocks are appended. Only for
        # long chapters with no source sub-headings of their own.
        if with_subheadings and len(body.split()) >= _SUBHEADING_MIN_WORDS and not _has_internal_subheadings(body):
            try:
                pairs = _generate_subheadings(title, body, book_dir, log)
            except Exception as e:
                pairs = []
                log(f"      self-study: sub-headings for {title!r} skipped ({e})")
            if pairs:
                new_body = _insert_subheadings(body, pairs, log, title)
                subheads += (
                    new_body.count("\n## ")
                    + (1 if new_body.lstrip().startswith("## ") else 0)
                    - body.count("\n## ")
                    - (1 if body.lstrip().startswith("## ") else 0)
                )
                body = new_body

        blocks: list[str] = []
        if with_notes:
            try:
                note = _generate_enrichment(title, body, atoms, book_dir, f"note-{_slug(title)}", log)
            except AuthoringError:
                raise
            except Exception as e:
                note = ""
                log(f"      self-study: note for {title!r} skipped ({e})")
            if note:
                ok, reasons = gate_editorial_block(note)
                if ok:
                    blocks.append(format_editorial_block(note))
                    notes += 1
                else:
                    dropped += 1
                    log(f"      self-study: dropped note for {title!r} ({'; '.join(reasons[:2])})")

        try:
            summary = _generate_summary(title, body, book_dir, f"summary-{_slug(title)}", log)
        except AuthoringError:
            raise
        except Exception as e:
            summary = ""
            log(f"      self-study: summary for {title!r} skipped ({e})")
        if summary:
            ok, reasons = gate_summary(summary)
            if ok:
                blocks.append(format_summary_block(summary))
                summaries += 1
            else:
                dropped += 1
                log(f"      self-study: dropped summary for {title!r} ({'; '.join(reasons[:2])})")

        chunk = f"{head}\n\n{body.strip()}" if body.strip() else head
        if blocks:
            chunk = f"{chunk}\n\n" + "\n\n".join(blocks)
        out_parts.append(chunk)

    assembled = "\n\n".join(out_parts).strip() + "\n"

    # Step 3 — inline term definitions at first use (book-wide, after assembly so
    # "first use" is truly the first across the whole book).
    terms = 0
    if with_term_defs:
        try:
            assembled, terms = _apply_term_definitions(assembled, book_dir, log)
        except Exception as e:
            log(f"      self-study: term definitions skipped ({e})")

    out_md = book_dir / "book" / "book-self-study.md"
    out_md.write_text(assembled, encoding="utf-8")
    log(
        f"    0book-self-study: wrote {out_md.name} "
        f"({summaries} summaries, {notes} notes, {subheads} sub-headings, "
        f"{terms} term defs, {dropped} dropped, {len(chapters)} chapters)"
    )

    # Step 7 (deterministic half) — structural gate over the materialized md.
    # Non-blocking: a broken self-study edition never stops the podcast ship.
    findings = check_self_study_markdown(assembled)
    (book_dir / "_system").mkdir(exist_ok=True)
    (book_dir / "_system" / "self-study-checks.json").write_text(
        __import__("json").dumps({"schema": "podcast.self-study-checks/v1", "findings": findings}, indent=2) + "\n",
        encoding="utf-8",
    )
    if findings:
        log(f"    0book-self-study: {len(findings)} structural finding(s) — see _system/self-study-checks.json")
    return out_md
