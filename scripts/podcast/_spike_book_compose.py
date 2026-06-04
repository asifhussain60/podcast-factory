"""_spike_book_compose.py — STAGE 1 SPIKE (throwaway; do not productionize as-is).

Composes the whole book from book/book-toc.json: per book-chapter, an Opus pass that
re-voices the source span into modern author-first-person prose under the chapter's
modern title, quotes preserved verbatim, faithful (no abridgement). Carries a voice
card + continuity anchor across chapters. Assembles preface + chapters → book/book.md.

ENRICHMENT NOTE: doctrinal enrichment from the knowledge base is intentionally OFF for
this book — the current corpus is Fatimid-Ismaili doctrine, tradition-mismatched for a
Ghazali Sunni-Sufi text. The book is composed faithfully from the source's own rich
citations; the appropriate (Sunni hadith) corpus is a pluggable step for later.

Idempotent: a chapter whose book/_chunks/book/bk-NNN.md exists is skipped. book.md is
assembled only once every chapter is present.

Usage:
  python3 scripts/podcast/_spike_book_compose.py content/Islamic/ayyuhal-walad/
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

_PODCAST = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_PODCAST))

from _authoring._core import _run_claude_p  # noqa: E402
from _literary import _read_literary_config, _VOICE_INSTRUCTIONS, teaching_loss_findings  # noqa: E402
from _translit import simplify_transliteration  # noqa: E402


def _slice_source(lines: list[str], ranges: list[list[int]]) -> str:
    out: list[str] = []
    for a, b in ranges:
        out.extend(lines[a - 1 : b])  # 1-based inclusive
    text = "\n".join(out)
    text = re.sub(r"<!--\s*PAGE\s*\d+\s*-->", "", text)  # drop page markers
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _quote_spans(text: str) -> list[str]:
    """Italicized transliteration quotes *"..."* / *'...'* — the verbatim scripture/hadith
    as they appear in the SOURCE (used only to count how many quotations a chapter carries)."""
    spans = re.findall(r'\*"([^"]{8,})"\*', text) + re.findall(r"\*'([^']{8,})'\*", text)
    return [s.strip() for s in spans]


def _arabic_run_count(text: str) -> int:
    """Count runs of Arabic-script characters in the output — a sanity signal that
    quotations were rendered in real script rather than left as Latin transliteration."""
    return len(re.findall(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]{2,}", text))


def _compose_prompt(title: str, body: str, cfg: dict, voice_card: str, prev_tail: str) -> str:
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
attribution or reference (surah/verse number, speaker, collection). Do NOT keep the Latin-letter \
transliteration in the output — the Arabic script replaces it. If you are not confident of the exact \
canonical Arabic for a particular quotation, render your best faithful attempt and DO NOT invent a \
reference that is not in the source.

CHAPTER CRAFT
Write this as a single flowing book chapter under its title. Open in a way that draws the reader in, \
let the argument unfold through the specific things the text names, and close with resonance. Avoid \
sub-headings unless the material genuinely demands one. No meta-commentary ("in this chapter…"); \
write the thing, not about the thing.

REGISTER
Contemporary literary English — intimate, direct first person. No archaic diction, no "O such-and-such" \
forms unless they arise naturally.
{anchor}{cont}
OUTPUT
Return ONLY the chapter prose. Do NOT print the title line (it is added separately). No preamble, no \
code fences, no trailing commentary.

SOURCE MATERIAL (this chapter)
{body}"""


def _compose_one(title: str, body: str, cfg: dict, voice_card: str, prev_tail: str,
                 book_dir: pathlib.Path, label: str) -> str:
    prompt = _compose_prompt(title, body, cfg, voice_card, prev_tail)
    rc, out, err = _run_claude_p(prompt, timeout=420, book_dir=book_dir,
                                 phase="0book-compose(spike)", step=label)
    out = (out or "").strip()
    if rc != 0:
        raise RuntimeError(f"{label}: claude -p rc={rc}: {err[:400]}")

    # anti-abridgement: one retry if it came back materially short
    sw = len(body.split())
    if sw >= 200 and len(out.split()) < 0.7 * sw:
        print(f"   {label}: short ({len(out.split())}/{sw}w) — retry (anti-abridge)")
        rc2, out2, _ = _run_claude_p(
            prompt + "\n\nYOUR PREVIOUS ATTEMPT WAS TOO SHORT — it summarized. Re-voice the FULL "
            "material; omit nothing; output about the same length as the source.",
            timeout=520, book_dir=book_dir, phase="0book-compose(spike)", step=f"{label}-retry")
        if rc2 == 0 and len(out2.split()) > len(out.split()):
            out = out2.strip()
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: _spike_book_compose.py <BOOK_DIR>", file=sys.stderr)
        return 2
    book_dir = pathlib.Path(sys.argv[1]).resolve()
    toc_path = book_dir / "book" / "book-toc.json"
    refined = book_dir / "_system" / "source" / "text" / "refined-english.md"
    if not toc_path.exists():
        print(f"ERROR: run _spike_book_design first (no {toc_path})", file=sys.stderr)
        return 1

    toc = json.loads(toc_path.read_text(encoding="utf-8"))
    lines = refined.read_text(encoding="utf-8").split("\n")
    cfg = _read_literary_config(book_dir)
    chunks_dir = book_dir / "book" / "_chunks" / "book"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    print(f"[spike-compose] {book_dir.name}: voice={cfg.get('narrator_subject')!r} · "
          f"{len(toc.get('chapters', []))} chapters")

    voice_card = ""
    prev_tail = ""
    for ch in toc.get("chapters", []):
        idx = ch.get("bk_index")
        title = ch.get("title", f"Chapter {idx}")
        label = f"bk-{idx:02d}"
        out_path = chunks_dir / f"{label}.md"
        body = _slice_source(lines, ch.get("source_line_ranges", []))

        if out_path.exists() and out_path.read_text(encoding="utf-8").strip():
            prose = out_path.read_text(encoding="utf-8")
        else:
            print(f"   {label}: {title}  ({len(body.split())} src words) → Opus…")
            prose = _compose_one(title, body, cfg, voice_card, prev_tail, book_dir, label)
            findings = teaching_loss_findings(body, prose)
            qsrc = len(_quote_spans(body))
            qar = _arabic_run_count(prose)
            note = ""
            if findings:
                note += " | GUARD: " + "; ".join(findings)
            note += f" | arabic blocks {qar} (src had {qsrc} translit quotes)"
            out_path.write_text(prose.rstrip() + "\n", encoding="utf-8")
            print(f"   {label}: {len(prose.split())} words written{note}")

        # update anchors for the next chapter
        if not voice_card:
            voice_card = " ".join(prose.split()[:60])
        prev_tail = " ".join(prose.split()[-120:])

    # assemble only when every chapter is present
    chapters = toc.get("chapters", [])
    missing = [f"bk-{c['bk_index']:02d}" for c in chapters
               if not (chunks_dir / f"bk-{c['bk_index']:02d}.md").exists()]
    if missing:
        print(f"[spike-compose] not assembling book.md — missing {missing}. Re-run to continue.")
        return 0

    # preface
    pf = toc.get("preface", {})
    parts: list[str] = [f"# {toc.get('book_title', book_dir.name)}\n"]
    if pf.get("include"):
        pf_path = chunks_dir / "preface.md"
        if pf_path.exists() and pf_path.read_text(encoding="utf-8").strip():
            preface = pf_path.read_text(encoding="utf-8").strip()
        else:
            pbody = _slice_source(lines, pf.get("source_line_ranges", [])) or \
                "(The disciple's question that prompted this letter.)"
            print(f"   preface: {pf.get('title')!r} → Opus…")
            ptitle = pf.get("title", "Preface")
            pprompt = _compose_prompt(
                ptitle,
                pbody + "\n\n(Write this as a short, warm preface — at most a few paragraphs — that "
                "orients today's reader to the letter that follows: who is speaking, to whom, and why "
                "it still matters across the centuries.)",
                cfg, "", "")
            rc, preface, _ = _run_claude_p(pprompt, timeout=300, book_dir=book_dir,
                                           phase="0book-compose(spike)", step="preface")
            preface = (preface or "").strip()
            pf_path.write_text(preface + "\n", encoding="utf-8")
        parts.append(f"## {pf.get('title', 'Preface')}\n\n{preface}\n")

    for ch in chapters:
        label = f"bk-{ch['bk_index']:02d}"
        prose = (chunks_dir / f"{label}.md").read_text(encoding="utf-8").strip()
        parts.append(f"## {ch['bk_index']}. {ch['title']}\n\n{prose}\n")

    book_md = book_dir / "book" / "book.md"
    # Plain transliteration for the reading edition: fold scholarly diacritics
    # (Kīmiyāʾ al-Saʿāda → Kimiya al-Sa'ada). Arabic script is left untouched.
    assembled = simplify_transliteration("\n".join(parts).rstrip() + "\n")
    book_md.write_text(assembled, encoding="utf-8")
    total = len(book_md.read_text(encoding='utf-8').split())
    print(f"[spike-compose] assembled {book_md} · {total} words across {len(chapters)} chapters + preface")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
