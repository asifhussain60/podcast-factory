#!/usr/bin/env python3
"""weave_source.py — merge Asif's twenty lectures INTO the book's chapter prose.

Why this, and not the pipeline's merge tool
-------------------------------------------
`multi_source_synthesis.py` is the repo's spine-plus-augmentation route, and it
is built for LECTURE TRANSCRIPTS as the spine: its prompt grants itself leave to
"reorganize into a logical themed flow with H2 headings" and to "denoise
off-topic asides / filler / repetition", and it targets 55-95% of the source
length because it assumes a quarter to a half of the words are oral redundancy.
Our spine is a published book of tight scholarly prose. Pointed at it, that tool
would dissolve five deliberate chapters into invented sections and score cutting
a third of the book a success.

So the weave happens HERE, before the pipeline, at the source. The five chapters
stay exactly five chapters; everything downstream simply reads a source that
already carries both voices.

The contract (Asif, 2026-08-05: "weave the teaching into the prose itself
without creating duplicate content")
------------------------------------------------------------------------------
His lectures are not commentary standing apart from the book — they cover the
same ground, often sentence for sentence. Session one opens by paraphrasing
chapter one's own opening and stopping to define "quintessential" in brackets.
So the merge is a MERGE, never a concatenation:

  * every teaching in the printed chapter survives;
  * where the lecture covers the same point, his plainer wording REPLACES the
    dense phrasing rather than following it;
  * where the lecture adds something the chapter lacks - a definition, a verse
    quoted in full, an explanation of a term - it is folded in where it belongs;
  * where the lecture goes somewhere the chapter never goes, it is left out;
  * no point is ever made twice in different words. That is the primary rule.

Attribution stays in the repo even though it is deliberately absent from the
page: `_system/source/weave-provenance.json` records, per chapter, which
sessions were offered and what the pass reported doing with them.

Usage
-----
    python3 content/Islamic/spiritual-ethos/_system/weave_source.py --chapter 1
    python3 content/Islamic/spiritual-ethos/_system/weave_source.py --all
    python3 content/Islamic/spiritual-ethos/_system/weave_source.py --all --force
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BOOK = Path(__file__).resolve().parent.parent
REPO = BOOK.parents[2]
sys.path.insert(0, str(REPO / "scripts" / "podcast"))

from _authoring._core import _run_claude_p_with_retry  # noqa: E402

LECTURES = (
    REPO
    / "content/_shared/source-library/extracted/ksessions"
    / "07-spiritual-ethos-of-ali/_system/source/text/raw-extract.md"
)
SOURCE = BOOK / "_system/source/text/raw-extract.md"
FAITHFUL = BOOK / "_system/source/text/raw-extract.faithful.md"
PROVENANCE = BOOK / "_system/source/weave-provenance.json"

# Which of his sessions speak to which chapter. Derived from his own category
# structure, which tracks the book closely: "Spirit Of Intellect" is chapter
# one's second half, "Justice" is chapter two and the Letter, and the Kumayl
# discourse is studied in chapter one but is also where he teaches spiritual
# knowledge and remembrance, which is chapter three's whole subject.
#
# Chapter three has no section of its own -- Asif said so before any of this was
# read, and the data agrees. It draws on the Kumayl sessions where they already
# speak to remembrance, and gets nothing invented to make up the difference.
CHAPTER_SESSIONS: dict[int, list[int]] = {
    1: [1242, 88, 89, 90, 91, 112],
    2: [162, 169, 204, 205, 208],
    3: [113, 114, 116, 202, 112],
    4: [92],
    5: [203, 201, 206, 210],
}

_WINDOW_WORDS = 1800
_MAX_LECTURE_WORDS = 6000
_MIN_KEEP_RATIO = 0.95  # a woven chapter may grow; it may not shrink


def _sessions() -> dict[int, tuple[str, str]]:
    """{session_id: (title, body)} from the extracted lecture bundle."""
    text = LECTURES.read_text(encoding="utf-8")
    parts = re.split(r"<!-- section \d+ \(id=(\d+), raw_sort=\d+\): ([^>]*?) -->", text)
    out: dict[int, tuple[str, str]] = {}
    for i in range(1, len(parts) - 1, 3):
        out[int(parts[i])] = (parts[i + 1].strip(), parts[i + 2].strip())
    return out


def _chapters(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    parts = re.split(r"(?m)^## (.+)$", text)
    return [(parts[i].strip(), parts[i + 1].strip()) for i in range(1, len(parts) - 1, 2)]


def _windows(body: str) -> list[str]:
    paras = [p for p in body.split("\n\n") if p.strip()]
    windows: list[list[str]] = [[]]
    count = 0
    for p in paras:
        n = len(p.split())
        if count and count + n > _WINDOW_WORDS:
            windows.append([])
            count = 0
        windows[-1].append(p)
        count += n
    return ["\n\n".join(w) for w in windows if w]


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{5,}", text.lower())}


def _relevant_lectures(window: str, bodies: list[tuple[str, str]]) -> str:
    """The lecture passages closest to this window, within a word budget.

    Lexical overlap, deliberately simple. The lectures and the chapter are about
    the same paragraphs in the same book, so shared vocabulary is a strong signal
    and there is no embedding step in this repo to reach for.
    """
    target = _tokens(window)
    scored: list[tuple[float, str, str]] = []
    for title, body in bodies:
        for chunk in _chunk(body):
            toks = _tokens(chunk)
            if not toks:
                continue
            scored.append((len(target & toks) / len(target | toks), title, chunk))
    scored.sort(key=lambda s: -s[0])

    picked: list[str] = []
    used = 0
    for score, title, chunk in scored:
        if score <= 0.02:
            break
        n = len(chunk.split())
        if used + n > _MAX_LECTURE_WORDS:
            continue
        picked.append(f"[from his session: {title}]\n{chunk}")
        used += n
    return "\n\n".join(picked)


def _chunk(body: str, size: int = 700) -> list[str]:
    paras = [p for p in body.split("\n\n") if p.strip()]
    out: list[list[str]] = [[]]
    count = 0
    for p in paras:
        n = len(p.split())
        if count and count + n > size:
            out.append([])
            count = 0
        out[-1].append(p)
        count += n
    return ["\n\n".join(c) for c in out if c]


def _prompt(chapter_title: str, window: str, lectures: str, tail: str) -> str:
    continuity = (
        f"\nCONTINUITY\nThis passage continues a chapter already under way. The previous "
        f"passage ended with the words below. Carry straight on; do not re-introduce the "
        f"chapter and do not repeat these words:\n{tail}\n"
        if tail
        else ""
    )
    return f"""You are preparing the source text of a reading edition. You are given one passage
of a scholarly book, and passages from a lecture series the book's own reader
taught on this exact material. Produce ONE continuous passage carrying both.

THE PRIMARY RULE: NO DUPLICATION.
The lecture covers the same ground as the book, often sentence for sentence. It
frequently restates the book's own opening in plainer words and stops to define
a hard term. You must never let the same point appear twice in different words.
Where both cover a point, write it ONCE, in the clearer wording.
{continuity}
WHAT TO DO
- Every teaching, argument, example, named person, citation, Quran verse and
  hadith in THE BOOK PASSAGE must survive. Nothing is dropped or summarized.
- Where the lecture says the same thing more plainly, use the plainer wording in
  place of the book's denser phrasing. This is the point of the exercise.
- Where the lecture supplies something the passage lacks - a definition of a
  technical term, a verse quoted in full with its translation, an explanation of
  a term the book uses without one - fold it into the sentence or paragraph where
  it belongs, as part of the prose.
- Where the lecture goes somewhere this passage never goes, LEAVE IT OUT. It
  belongs to another chapter or to no chapter.
- Keep every Arabic-script run exactly as it appears. Never romanize one away and
  never drop one. Markers of the form BRACKET-ar: ... are Arabic and are content.
- Keep the honorific form the passage already uses for names.

WHAT NOT TO DO
- Do not add facts, analogies, or explanations that appear in NEITHER text.
- Do not write a note, an aside, a bracketed comment, or an editorial remark.
  There is one voice on the page.
- Do not add headings, and do not reorganize the passage's order.
- Do not shorten. The result should be at least as long as the book passage.

AFTER the prose, append exactly one block, and nothing after it:

===WEAVE-NOTES===
USED: <the session titles you actually drew on, comma separated, or "none">
ADDED: <one line on what the lecture contributed that the book lacked>
===END-NOTES===

OUTPUT
Return the woven prose, then that one block. No title line, no preamble, no code
fences.

CHAPTER "{chapter_title}"

THE BOOK PASSAGE
{window}

HIS LECTURE PASSAGES ON THIS MATERIAL
{lectures if lectures else "(nothing closely matching this passage)"}"""


_NOTES_RE = re.compile(r"===WEAVE-NOTES===(.*?)===END-NOTES===", re.S)


def _split_notes(out: str) -> tuple[str, str]:
    m = _NOTES_RE.search(out)
    if not m:
        return out.strip(), ""
    return out[: m.start()].strip(), m.group(1).strip()


def _arabic_runs(text: str) -> int:
    return len(re.findall(r"[؀-ۿ]{2,}", text))


def _gate(window: str, woven: str) -> list[str]:
    """Deterministic refusals. A failing window keeps the book's own prose."""
    fails: list[str] = []
    if not woven.strip():
        return ["empty output"]
    base_n, new_n = len(window.split()), len(woven.split())
    if new_n < base_n * _MIN_KEEP_RATIO:
        fails.append(f"shortened: {new_n} words vs {base_n} in the book passage")
    base_ar, new_ar = _arabic_runs(window), _arabic_runs(woven)
    if new_ar < base_ar:
        fails.append(f"Arabic runs lost: {new_ar} vs {base_ar}")
    if "===WEAVE-NOTES===" in woven:
        fails.append("notes block leaked into the prose")
    for marker in ("Editorial note", "[note:", "> **A note"):
        if marker in woven and marker not in window:
            fails.append(f"editorial aside added ({marker!r}) — this weave has one voice")
    return fails


def weave_chapter(index: int, title: str, body: str, sess: dict, log) -> tuple[str, dict]:
    bodies = [sess[s] for s in CHAPTER_SESSIONS.get(index, []) if s in sess]
    record: dict = {
        "chapter": index,
        "title": title,
        "sessions_offered": [sess[s][0] for s in CHAPTER_SESSIONS.get(index, []) if s in sess],
        "windows": [],
        "base_words": len(body.split()),
    }
    if not bodies:
        record["status"] = "no-sessions"
        record["woven_words"] = record["base_words"]
        return body, record

    out_parts: list[str] = []
    tail = ""
    for w_i, window in enumerate(_windows(body), 1):
        lectures = _relevant_lectures(window, bodies)
        label = f"ch{index:02d}-w{w_i:02d}"
        rc, out, err = _run_claude_p_with_retry(
            _prompt(title, window, lectures, tail),
            timeout=900,
            book_dir=BOOK,
            phase="weave-source",
            step=label,
            log=log,
        )
        if rc != 0:
            log(f"      {label}: call failed ({err[:120]}) — keeping the book's prose")
            out_parts.append(window)
            record["windows"].append({"window": w_i, "status": "failed"})
            continue
        woven, notes = _split_notes(out)
        fails = _gate(window, woven)
        if fails:
            log(f"      {label}: reverted — {'; '.join(fails[:2])}")
            out_parts.append(window)
            record["windows"].append({"window": w_i, "status": "reverted", "gates": fails})
            continue
        out_parts.append(woven)
        tail = " ".join(woven.split()[-40:])
        record["windows"].append(
            {
                "window": w_i,
                "status": "woven",
                "base_words": len(window.split()),
                "woven_words": len(woven.split()),
                "lecture_words_offered": len(lectures.split()),
                "notes": notes,
            }
        )
        log(f"      {label}: {len(window.split())} -> {len(woven.split())} words")

    new_body = "\n\n".join(out_parts)
    record["woven_words"] = len(new_body.split())
    record["status"] = "woven"
    return new_body, record


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chapter", type=int, action="append", help="1-5; repeatable")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true", help="re-weave from the faithful source")
    args = ap.parse_args()
    if not args.all and not args.chapter:
        ap.error("pass --chapter N or --all")

    def log(msg: str) -> None:
        print(msg, flush=True)

    if not FAITHFUL.exists():
        FAITHFUL.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
        log(f"kept the faithful source at {FAITHFUL.relative_to(REPO)}")

    read_from = FAITHFUL if args.force else SOURCE
    chapters = _chapters(read_from)
    header = read_from.read_text(encoding="utf-8").split("\n## ")[0].rstrip()
    sess = _sessions()
    wanted = set(range(1, len(chapters) + 1)) if args.all else set(args.chapter)

    prov = json.loads(PROVENANCE.read_text()) if PROVENANCE.exists() and not args.force else {}
    prov.setdefault("chapters", {})

    # Bodies are held here and flushed to disk after EVERY chapter, not once at
    # the end. The first run wrote only on completion, was interrupted during
    # chapter three, and lost chapter two entirely along with it -- an hour of
    # finished work that existed only in memory. A chapter costs ~20 minutes;
    # losing one is a nuisance, losing all of them is not.
    bodies = {i: body for i, (_, body) in enumerate(chapters, 1)}

    def flush() -> None:
        out = [header, ""]
        for i, (title, _) in enumerate(chapters, 1):
            out.extend([f"## {title}", "", bodies[i], ""])
        SOURCE.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
        prov["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        prov["contract"] = "weave inline, no duplicate content; attribution kept here, not on the page"
        PROVENANCE.write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")

    for i, (title, body) in enumerate(chapters, 1):
        if i not in wanted:
            continue
        log(f"  chapter {i}: {title}")
        bodies[i], record = weave_chapter(i, title, body, sess, log)
        prov["chapters"][str(i)] = record
        flush()
        log(f"      saved — chapter {i} is on disk")

    flush()
    log(f"\nwrote {SOURCE.relative_to(REPO)}")
    for i, rec in sorted(prov["chapters"].items(), key=lambda kv: int(kv[0])):
        log(f"  ch{i}: {rec['base_words']:,} -> {rec['woven_words']:,} words  ({rec['status']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
