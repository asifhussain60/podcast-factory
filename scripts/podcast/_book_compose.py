"""_book_compose.py — Phase 0book-compose: whole-book revoice for the reading edition.

Composes BOOK_DIR/book/book.md from book/book-toc.json: per book-chapter, an Opus
pass that re-voices the source span into modern author-first-person prose under the
chapter's modern title — Arabic quotations rendered in actual Arabic script (blockquote)
with the English translation beneath, faithful (no abridgement, no teaching lost). A
voice card + continuity anchor carry the register and flow across chapters. The assembled
book.md is folded to plain transliteration (Kimiya al-Sa'ada, not Kīmiyāʾ al-Saʿāda).

Reuses the faithfulness helpers from _literary.py. Runs on Opus / flat-rate Max.

ENRICHMENT: independent doctrinal enrichment is a pluggable step that waits for a
tradition-appropriate corpus (the current knowledge base is tradition-mismatched for
Sunni-Sufi sources). v1 composes faithfully from the source's own citations.

Idempotent: a chapter whose book/_chunks/book/bk-NNN.md exists is skipped; book.md is
assembled once every chapter is present.

Standalone:
  python3 _book_compose.py <BOOK_DIR>
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from _authoring._core import AuthoringError, _run_claude_p
from _literary import _read_literary_config, _VOICE_INSTRUCTIONS, teaching_loss_findings
from _translit import simplify_transliteration

# Per-chapter wall budgets. 420s proved too tight in practice (2026-06-11:
# a 631-word chapter ran ~16 min on Opus and the whole phase aborted at
# chapter 1); compose calls re-voice full chapters, so give them the same
# order of budget as phase-0d authoring calls.
_COMPOSE_TIMEOUT = 900
_RETRY_TIMEOUT = 1350

_PAGE_MARK = re.compile(r"<!--\s*page\s*(\d+)\s*-->", re.IGNORECASE)


def _slice_source(lines: list[str], ranges: list[list[int]]) -> str:
    out: list[str] = []
    for a, b in ranges:
        out.extend(lines[a - 1 : b])  # 1-based inclusive
    text = "\n".join(out)
    text = _PAGE_MARK.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _line_pages(lines: list[str]) -> list[int]:
    """Source page carried by each line of the line-numbered design input.

    Lines before the first ``<!-- page N -->`` marker belong to page 1."""
    pages: list[int] = []
    cur = 1
    for ln in lines:
        m = _PAGE_MARK.search(ln)
        if m:
            cur = int(m.group(1))
        pages.append(cur)
    return pages


def _pages_for_ranges(line_pages: list[int], ranges: list[list[int]]) -> list[int]:
    out: set[int] = set()
    for a, b in ranges:
        lo, hi = max(1, a), min(len(line_pages), b)
        out.update(line_pages[lo - 1 : hi])
    return sorted(out)


def _load_arabic_pages(book_dir: Path) -> dict[int, str] | None:
    """Per-page Arabic OCR ground truth from Phase 0a, when the source was Arabic script.

    Returns None for books without an Arabic OCR extract (fiction, technical, English
    sources) — composition then behaves exactly as before."""
    src = book_dir / "_system" / "source" / "ocr" / "raw-extract.md"
    if not src.exists():
        return None
    text = src.read_text(encoding="utf-8")
    if _arabic_run_count(text) < 50:
        return None
    pages: dict[int, str] = {}
    cur: int | None = None
    buf: list[str] = []
    for ln in text.split("\n"):
        m = _PAGE_MARK.search(ln)
        if m:
            if cur is not None:
                pages[cur] = "\n".join(buf).strip()
            cur, buf = int(m.group(1)), []
        elif cur is not None:
            buf.append(ln)
    if cur is not None:
        pages[cur] = "\n".join(buf).strip()
    return pages or None


def _translit_quote_count(text: str) -> int:
    """How many italicized transliteration quotes the SOURCE carries (for reporting)."""
    return len(re.findall(r'\*"[^"]{8,}"\*', text) + re.findall(r"\*'[^']{8,}'\*", text))


def _arabic_run_count(text: str) -> int:
    return len(re.findall(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]{2,}", text))


def _arabic_ground_truth_block(arabic_src: str) -> str:
    if not arabic_src:
        return ""
    return f"""
ARABIC SOURCE — GROUND TRUTH (the original pages this chapter is drawn from)
The original ARABIC of this chapter's source pages is reproduced below, from a machine OCR of the printed \
book — it may carry stray footnote digits, broken letters, or misplaced marks. When rendering quotations, \
poetry, sermons, and reported sayings in Arabic script, TRANSCRIBE them from this source rather than from \
memory — silently correct obvious OCR artifacts and add full vowelling. EXCEPTION: Quranic verses must \
still use the precise canonical mushaf text. If a passage you need is not present in this source, fall \
back to the rule above (best faithful attempt, no invented reference).

{arabic_src}
"""


def _compose_prompt(title: str, body: str, cfg: dict, voice_card: str, prev_tail: str,
                    arabic_src: str = "") -> str:
    voice_key = cfg.get("narrator_voice", "author_first_person")
    narrator = cfg.get("narrator_subject", "the author")
    addressee = cfg.get("addressee", "the reader")
    voice_instr = _VOICE_INSTRUCTIONS.get(voice_key, _VOICE_INSTRUCTIONS["author_first_person"]).format(
        narrator_subject=narrator, addressee=addressee)
    anchor = (f"\nVOICE ANCHOR (match this exact register and rhythm — it is your own voice "
              f"established earlier in the book):\n{voice_card}\n") if voice_card else ""
    cont = (f"\nCONTINUITY: the previous chapter ended with —\n\"…{prev_tail}\"\nOpen THIS chapter so "
            f"it flows naturally onward. Do not repeat those lines or recap them.\n") if prev_tail else ""

    return f"""You are {narrator}, preparing a modern reading edition of your letter. Write ONE chapter, \
titled "{title}".

NARRATOR VOICE
{voice_instr}

FAITHFULNESS (absolute)
Preserve every teaching, argument, example, named person, and citation in the source below. \
Do NOT summarize, condense, omit, or shorten. The chapter must be approximately the SAME LENGTH as \
the source material — never shorter. You may modernize the connective prose, but every quotation's \
substance and reference must survive.

ARABIC QUOTATIONS (important — this is a printed book, not audio)
The source gives Arabic quotations (Quranic verses, hadith, reported sayings, poetry) in Latin-letter \
TRANSLITERATION. In your output you MUST replace each transliteration with the actual ARABIC SCRIPT, \
fully vowelled (tashkīl), and place the English translation on the line(s) directly below it. Render \
each quotation as a blockquote — Arabic first, English beneath — like this:

> أَعُوذُ بِاللَّهِ مِنْ عِلْمٍ لَا يَنْفَعُ
>
> "I seek refuge in God from knowledge that does not benefit."

Use the EXACT canonical Arabic: for Quranic verses, the precise mushaf text; for hadith and reported \
sayings, their well-attested Arabic wording; for Arabic poetry, the Arabic lines. Keep any source \
attribution or reference. Do NOT keep the Latin-letter transliteration. If you are not confident of the \
exact canonical Arabic for a quotation, render your best faithful attempt and DO NOT invent a reference.
{_arabic_ground_truth_block(arabic_src)}
CHAPTER CRAFT
Write this as a single flowing book chapter under its title. Open in a way that draws the reader in, let \
the argument unfold through the specific things the text names, and close with resonance. Avoid \
sub-headings unless the material genuinely demands one. No meta-commentary; write the thing, not about it.

REGISTER
Contemporary literary English — intimate, direct first person. No archaic diction.
{anchor}{cont}
OUTPUT
Return ONLY the chapter prose. Do NOT print the title line (it is added separately). No preamble, no \
code fences, no trailing commentary.

SOURCE MATERIAL (this chapter)
{body}"""


def _compose_one(title: str, body: str, cfg: dict, voice_card: str, prev_tail: str,
                 book_dir: Path, label: str, log, arabic_src: str = "") -> str:
    prompt = _compose_prompt(title, body, cfg, voice_card, prev_tail, arabic_src=arabic_src)
    rc, out, err = _run_claude_p(prompt, timeout=_COMPOSE_TIMEOUT, book_dir=book_dir,
                                 phase="0book-compose", step=label)
    out = (out or "").strip()
    if rc != 0:
        raise AuthoringError(
            phase="0book-compose",
            message=f"{label}: claude -p rc={rc}: {err[:300]}",
            manual_fallback="Re-run the phase to resume from the last completed chapter.")
    sw = len(body.split())
    if sw >= 200 and len(out.split()) < 0.7 * sw:
        log(f"      {label}: short ({len(out.split())}/{sw}w) — retry (anti-abridge)")
        rc2, out2, _ = _run_claude_p(
            prompt + "\n\nYOUR PREVIOUS ATTEMPT WAS TOO SHORT — it summarized. Re-voice the FULL "
            "material; omit nothing; output about the same length as the source.",
            timeout=_RETRY_TIMEOUT, book_dir=book_dir, phase="0book-compose", step=f"{label}-retry")
        if rc2 == 0 and len(out2.split()) > len(out.split()):
            out = out2.strip()
    return out


def author_phase_book_compose(book_dir: Path, *, log=print) -> Path:
    book_dir = Path(book_dir).resolve()
    toc_path = book_dir / "book" / "book-toc.json"
    if not toc_path.exists():
        raise AuthoringError(
            phase="0book-compose",
            message=f"missing {toc_path} — run 0book-design first.",
            manual_fallback="python3 -m _authoring._book_design <BOOK_DIR>")

    toc = json.loads(toc_path.read_text(encoding="utf-8"))
    refined = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if not refined.exists():
        raise AuthoringError(
            phase="0book-compose",
            message=f"missing {refined} (the line-numbered design input).",
            manual_fallback="Ensure the refined source used by 0book-design is present.")
    lines = refined.read_text(encoding="utf-8").split("\n")
    cfg = _read_literary_config(book_dir)
    chunks_dir = book_dir / "book" / "_chunks" / "book"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    chapters = toc.get("chapters", [])
    arabic_pages = _load_arabic_pages(book_dir)
    line_pages = _line_pages(lines) if arabic_pages else []

    def _arabic_for(ranges: list[list[int]]) -> tuple[str, str]:
        """(arabic_src, page-span label) for a chapter's source line ranges."""
        if not arabic_pages or not ranges:
            return "", ""
        nums = [n for n in _pages_for_ranges(line_pages, ranges) if n in arabic_pages]
        if not nums:
            return "", ""
        return "\n\n".join(arabic_pages[n] for n in nums), f"pp.{nums[0]}-{nums[-1]}"

    log(f"    0book-compose: {book_dir.name}: voice={cfg.get('narrator_subject')!r} · {len(chapters)} chapters"
        + (f" · arabic ground truth: {len(arabic_pages)} OCR pages" if arabic_pages else ""))

    voice_card, prev_tail = "", ""
    for ch in chapters:
        idx = ch.get("bk_index")
        title = ch.get("title", f"Chapter {idx}")
        label = f"bk-{idx:02d}"
        out_path = chunks_dir / f"{label}.md"
        body = _slice_source(lines, ch.get("source_line_ranges", []))
        if out_path.exists() and out_path.read_text(encoding="utf-8").strip():
            prose = out_path.read_text(encoding="utf-8")
        else:
            arabic_src, span = _arabic_for(ch.get("source_line_ranges", []))
            log(f"      {label}: {title} ({len(body.split())} src words"
                + (f", arabic {span}" if span else "") + ") -> Opus")
            prose = _compose_one(title, body, cfg, voice_card, prev_tail, book_dir, label, log,
                                 arabic_src=arabic_src)
            findings = teaching_loss_findings(body, prose)
            note = (" | GUARD: " + "; ".join(findings)) if findings else ""
            note += f" | arabic blocks {_arabic_run_count(prose)} (src {_translit_quote_count(body)} translit quotes)"
            out_path.write_text(prose.rstrip() + "\n", encoding="utf-8")
            log(f"      {label}: {len(prose.split())} words{note}")
        if not voice_card:
            voice_card = " ".join(prose.split()[:60])
        prev_tail = " ".join(prose.split()[-120:])

    # preface
    pf = toc.get("preface", {})
    parts: list[str] = [f"# {toc.get('book_title', book_dir.name)}\n"]
    if pf.get("include"):
        pf_path = chunks_dir / "preface.md"
        if pf_path.exists() and pf_path.read_text(encoding="utf-8").strip():
            preface = pf_path.read_text(encoding="utf-8").strip()
        else:
            pbody = _slice_source(lines, pf.get("source_line_ranges", [])) or \
                "(The question that prompted this work.)"
            log(f"      preface: {pf.get('title')!r} -> Opus")
            p_arabic, _ = _arabic_for(pf.get("source_line_ranges", []))
            pprompt = _compose_prompt(
                pf.get("title", "Preface"),
                pbody + "\n\n(Write this as a short, warm preface — at most a few paragraphs — that "
                "orients today's reader to the work that follows: who is speaking, to whom, and why it "
                "still matters across the centuries.)", cfg, "", "", arabic_src=p_arabic)
            rc, preface, _ = _run_claude_p(pprompt, timeout=300, book_dir=book_dir,
                                           phase="0book-compose", step="preface")
            preface = (preface or "").strip()
            pf_path.write_text(preface + "\n", encoding="utf-8")
        parts.append(f"## {pf.get('title', 'Preface')}\n\n{preface}\n")

    for ch in chapters:
        label = f"bk-{ch['bk_index']:02d}"
        prose = (chunks_dir / f"{label}.md").read_text(encoding="utf-8").strip()
        parts.append(f"## {ch['bk_index']}. {ch['title']}\n\n{prose}\n")

    # Plain transliteration for the reading edition; Arabic script untouched.
    book_md = book_dir / "book" / "book.md"
    book_md.write_text(simplify_transliteration("\n".join(parts).rstrip() + "\n"), encoding="utf-8")
    log(f"    0book-compose: assembled book.md · {len(book_md.read_text(encoding='utf-8').split())} words")
    return book_md


def main() -> int:
    import sys
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: python3 _book_compose.py <BOOK_DIR>", file=sys.stderr)
        return 2
    try:
        author_phase_book_compose(Path(args[0]))
        return 0
    except AuthoringError as e:
        print(f"ERROR [{e.phase}]: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
