#!/usr/bin/env python3
"""Build the NotebookLM pronunciation-probe bundle from ranked probe terms.

Consumes ``_system/probe/probe-terms.json`` (from score_pronunciation_risk.py)
and emits, under ``_system/probe/EP00-pronunciation-probe/``:

  - 00-framing.md          the Customize Prompt to paste into NotebookLM
  - pronunciation-probe.md the SOURCE to upload (a GLOSSARY: one numbered entry
                           per term, each with the spoken form and the sentence
                           it appears in, so the audio maps to the checklist)
  - listen-checklist.md    the listen-once + corrections intake form
  - README.md              upload instructions incl. the NotebookLM settings table

Deterministic (no LLM). The source is a glossary rather than a script, and that
distinction was learned the hard way: run 1 (2026-08-01) phrased every item as a
stage direction — "1. Next, say **wa-LAA-ya** — as in: ..." — and NotebookLM did
what it does with any source, conversationalising it into a themed discussion
ABOUT a glossary that named 9 of 39 terms. Instructions addressed to the hosts
belong in the framing; the source has to be something a host can plausibly read.

Every term is rendered through ``term_render.render_for_audio``. That is usually
an English word or a plain transliteration, because the ladder's lower rungs
never produce a respelling — but rung 0, the book's own override table, passes a
human's respelling through, and whether those survive is precisely what the
probe is for. Run 1's evidence: of seven respellings heard, the two that were
two syllables with no internal article survived (``tow-HEED``, ``tash-BEEH``) and
the other five were read literally as separate words ("wa la ya" for
``wa-LAA-ya``, "KHU Tiba" for ``KHUT-bah``), while the plain transliteration
tested came out perfect. Consistent with the asaas-vol-1 finding that this TTS
reads ``JAA-far`` as "J.A. Far" and ``is-raa-FEEL`` as "Israel, feel".
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Pull shared helpers from the knowledge package so keys + rendering match exactly.
_PROBE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROBE_DIR.parent / "knowledge"))
import term_render
from pronunciation_ledger import normalize_key


def _spoken(t: dict) -> dict:
    """Return the rendered spoken form for a probe term dict.

    Reads the render computed in build_bundle (stashed under ``_render``); falls
    back to a bare transliteration render if absent (e.g. older probe-terms.json).
    """
    r = t.get("_render")
    if r:
        return r
    translit = t.get("transliteration") or t.get("meaning") or t["term"]
    res = term_render.render_for_audio(translit)
    return {"text": res.text, "is_english": res.is_english, "tier": res.tier}


def _load_library(book_dir: Path) -> dict[str, dict]:
    """Return a dict keyed by normalize_key(term) from pronunciations.jsonl.

    The library lives at content/knowledge-base/pronunciations.jsonl. Anchored to
    the repo root via _PROBE_DIR (not counting levels above book_dir, which is
    wrong for nested volumes content/<Bucket>/<container>/<vol>/).
    Falls back gracefully if the file is absent.
    """
    lib_path = _PROBE_DIR.parents[2] / "content" / "knowledge-base" / "pronunciations.jsonl"
    if not lib_path.exists():
        return {}
    result: dict[str, dict] = {}
    for raw in lib_path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        entry = json.loads(raw)
        key = entry.get("key") or normalize_key(entry.get("term", ""))
        result[key] = entry
    return result


SEGMENT_TITLES = {
    "names": "Part 1 — People and scholar names",
    "places": "Part 2 — Places",
    "terms": "Part 3 — Technical and doctrinal terms",
}
SEGMENT_ORDER = ("names", "places", "terms")


# A sentence worth putting in a host's mouth: long enough to carry the term
# naturally, short enough to read aloud without becoming a lecture.
_CARRIER_MIN_CHARS = 40
# The real constraint is "one sentence", which the split already guarantees; the
# ceiling only keeps a runaway paragraph out. It is generous because this corpus
# writes long, and a term whose only sentence is rejected gets NO carrier at all
# — at 260 that silently cost al-Kirmani (286), tawhid (349) and tashbih (351).
_CARRIER_MAX_CHARS = 400
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def mine_carriers(book_dir: Path, terms: list[dict]) -> dict[str, tuple[str, str]]:
    """``{term_key: (sentence, chapter_stem)}`` mined from the real chapters.

    The probe's whole claim is that settling these terms once settles them for
    every chapter, so its sentences are drawn FROM those chapters rather than
    from a template — the hosts meet each term in the prose they will actually
    be given, and the bundle samples the whole book instead of standing beside
    it. Chapters are walked in order and the first clean sentence wins, so the
    same book always produces the same bundle.

    Falls back to nothing for a term no chapter mentions; ``build_source`` then
    uses the glossary's first-occurrence snippet as before.
    """
    chapters_dir = Path(book_dir) / "chapters"
    if not chapters_dir.is_dir():
        return {}
    wanted = {normalize_key(t.get("transliteration") or t["term"]): t for t in terms}
    out: dict[str, tuple[str, str]] = {}
    for chapter in sorted(chapters_dir.glob("*.txt")):
        text = chapter.read_text(encoding="utf-8")
        for raw in _SENTENCE_SPLIT.split(re.sub(r"\s+", " ", text)):
            # A quotation that opens mid-sentence leaves its blockquote marker
            # inside the flattened line ("raised it before the people: > Whoever's
            # master I am"), and a stray ">" read aloud is noise.
            sentence = re.sub(r"\s*>\s*", " ", raw).strip()
            if not (_CARRIER_MIN_CHARS <= len(sentence) <= _CARRIER_MAX_CHARS):
                continue
            if sentence.startswith(("#", ">", "-", "*", "|")):
                continue  # a heading, quotation or list row, not running prose
            norm = normalize_key(sentence)
            for key, _term in wanted.items():
                if key in out or not key:
                    continue
                # A hyphen is a BOUNDARY, not a blocker: the prose writes
                # "ruh al-nutq", and excluding a preceding hyphen made the term
                # unfindable in the only sentence that contains it. Letters and
                # digits still block, so `nass` does not match inside `nassab`.
                if re.search(r"(?<![a-z0-9])" + re.escape(key) + r"(?![a-z0-9])", norm):
                    out[key] = (sentence, chapter.stem)
    return out


# Function words a readable lowercase-leading snippet may open on. Anything else
# lowercase at the start is a truncated word, not a sentence beginning.
_OPENERS = frozenset(
    "the a an and but or so in on of for to at by from with as when where while "
    "he she it they we his her their its this that these those is are was were "
    "has have had not no if then than after before over under through".split()
)


def _is_readable_context(snippet: str) -> bool:
    """False when the snippet is a mid-word slice rather than readable prose.

    The glossary's ``first_seen_snippet`` is a fixed-width window around the
    term's first occurrence, so it routinely begins mid-word — "irming the
    Imamate, in Arabic the Kitab ithbat al-imama, by Ahmad b. Ibrahim
    al-Naysab". A host reading that aloud is testing the fragment, not the term,
    so the term is better off named on its own.

    A capital opens a sentence; a lowercase word opens a legitimate mid-sentence
    excerpt only when it is a function word. "the Zamrukh spoke" passes and
    "irming the Imamate" does not, without either needing a dictionary.
    """
    s = snippet.strip().lstrip("\"“'([")
    if not s:
        return False
    first = re.split(r"[^A-Za-z'-]", s, maxsplit=1)[0]
    return bool(first) and (first[0].isupper() or first.lower() in _OPENERS)


def _carrier(term: str, snippet: str) -> str:
    """A neutral sentence that puts the term in the hosts' mouths.

    Ontology-neutral on purpose: the segment bucket is a best-effort guess, so
    the source never asserts a term IS a person/place (which mislabels common
    nouns like "Sharia"). It just names the term and, if a readable
    first-occurrence snippet exists, gives that as context.
    """
    ctx = snippet.strip().rstrip(".")
    base = f"**{term}**"
    if ctx and _is_readable_context(ctx):
        return f"{base} — as in: “{ctx}”"
    return base


def build_source(data: dict, carriers: dict[str, tuple[str, str]] | None = None) -> str:
    slug = data["book_slug"]
    carriers = carriers or {}
    by_seg: dict[str, list[dict]] = {s: [] for s in SEGMENT_ORDER}
    for t in data["terms"]:
        by_seg.setdefault(t["segment"], []).append(t)

    sampled = sorted({chapter for _s, chapter in carriers.values()})
    total = len(data["terms"])
    # A GLOSSARY, not a script. Run 1 (2026-08-01) phrased every item as a stage
    # direction — "1. Next, say **wa-LAA-ya** — as in: ..." — and NotebookLM did
    # what it does with any source: it conversationalised it, producing a themed
    # discussion ABOUT a glossary and naming 9 of 39 terms. Instructions
    # addressed to the hosts belong in the framing; the source has to be
    # something a host can plausibly READ. Entries carry no imperative now, and
    # each is a heading the model can walk.
    lines: list[str] = [
        f"# Term glossary — {slug}",
        "",
        f"A glossary of {total} terms used in this book. Each entry gives the term, the",
        "way it is said aloud, and the sentence it appears in.",
        "",
    ]
    if sampled:
        lines += [
            f"Every quoted sentence is taken verbatim from the book, across "
            f"{len(sampled)} chapter{'s' if len(sampled) != 1 else ''}, so each term appears in the",
            "prose it belongs to.",
            "",
        ]
    for seg in SEGMENT_ORDER:
        items = by_seg.get(seg) or []
        if not items:
            continue
        lines.append(f"## {SEGMENT_TITLES[seg]}")
        lines.append("")
        for t in items:
            sp = _spoken(t)
            translit = t.get("transliteration") or t["term"]
            mined = carriers.get(normalize_key(translit))
            lines.append(f"### {t['n']}. {translit}")
            lines.append("")
            lines.append(f"Said aloud: {sp['text']}")
            if mined:
                lines.append("")
                lines.append(f"In the book: “{mined[0]}”")
            elif t.get("snippet") and _is_readable_context(t["snippet"]):
                lines.append("")
                lines.append(f"In the book: “{t['snippet'].strip().rstrip('.')}”")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_framing(data: dict) -> str:
    slug = data["book_slug"]
    lines: list[str] = [
        f"# Framing — pronunciation probe ({slug})",
        "",
        "Do not read this prompt aloud.",
        "",
        "## Goal",
        "",
        # Run 1 asked for "a short focused segment that walks through the terms"
        # and got a themed essay covering 9 of 39. The count, the ban on theming,
        # and the explicit per-entry shape are all responses to that.
        f"Read the glossary aloud. It has exactly {len(data['terms'])} numbered entries and every",
        f"single one must be spoken — entry 1 through entry {len(data['terms'])}, in that order.",
        "",
        "For each entry, do exactly this and nothing else:",
        "  1. Say the term, using the 'Said aloud' form given for it.",
        "  2. Read its 'In the book' sentence.",
        "  3. Move straight to the next entry.",
        "",
        "This is a pronunciation check, not an episode. Do NOT organise the",
        "entries into themes. Do NOT group them, skip them, summarise them, or",
        "discuss what they mean. Do NOT open with a hook or close with a",
        "reflection. If time is short, speak faster — never drop an entry.",
        "",
        "## Do not (forbidden vocabulary and framings)",
        "",
        "Never say: wow, right?, that's so interesting, it's fascinating, it's",
        "profound, deep dive, today we'll discuss. No reactions, no filler, no",
        "commentary between entries.",
        "",
        "## Pronunciation",
        "",
        # The instruction here used to end "and never say a hyphenated or
        # capitalised respelling" — written when the ladder could not produce
        # one. Rung 0 now passes a human's respelling through, so that sentence
        # forbade the very list printed beneath it. A probe whose framing
        # contradicts its own list tests nothing: it is the same defect, in the
        # same slot, as the block this whole change set exists to fix.
        "Say each term ONCE, exactly as written below. Some entries are written",
        "as respellings — hyphens mark syllable breaks and CAPITALS mark the",
        "stressed syllable, so read the syllables as one fluent word and never",
        "spell a word out letter by letter. Never say the original spelling and",
        "another form back-to-back.",
        "",
        "Say these names and terms just as written:",
    ]
    english_subs: list[tuple[dict, str]] = []
    for t in data["terms"]:
        sp = _spoken(t)
        if sp.get("is_english"):
            # An English substitute replaces the Arabic — call it out separately.
            english_subs.append((t, sp["text"]))
        else:
            lines.append(f"- {sp['text']}")

    if english_subs:
        lines += [
            "",
            "Where an English phrase is given, say the English — do NOT say the",
            "Arabic word it replaces:",
        ]
        for t, english in english_subs:
            lines.append(f'- say "{english}"')
    lines += [
        "",
        "Arabic citations: speak ONCE at first occurrence, then the English meaning.",
        "",
    ]
    return "\n".join(lines) + "\n"


def build_checklist(data: dict) -> str:
    slug = data["book_slug"]
    lines = [
        f"# Listen checklist + corrections — {slug}",
        "",
        "Generate the probe in NotebookLM, listen ONCE, and mark each term.",
        "",
        # These instructions used to say the rendered column is "never a
        # respelling" and forbid writing one as a fix. Rung 0 of the ladder now
        # passes a human's respelling through, so the column is full of them —
        # and whether they work is the open question this probe exists to
        # settle. Telling the listener not to record one would make the answer
        # unrecordable.
        "- The **rendered** column is what the hosts were told to say. It may be a",
        "  respelling (from this book's override table), an English word, or the",
        "  plain transliteration — whichever the term ladder resolved.",
        "- In the **OK?** column put `y` if it was pronounced correctly, `n` if wrong.",
        "- For a wrong term, put in **Fix** either a different spoken form to try",
        "  next round, or — if you think nothing written will ever work — a plain",
        "  English substitute the hosts should say instead (e.g. `the pillars`).",
        "- Worth noting beside an `n`: what you actually HEARD. It seeds the",
        "  mangle-map, so the next audit catches the same misreading by itself.",
        "- Leave **Fix** blank when OK = y.",
        "",
        "The applier reads this table: `y` -> confirm the rendered form in the",
        "cross-book library, so no later book re-derives it; a different spoken",
        "form -> retry it; an English substitute -> store it as the term's gloss",
        "and stop asking the hosts to say the Arabic at all.",
        "",
        "| n | term | rendered | OK? | Fix |",
        "|---|------|----------|-----|-----|",
    ]
    for t in data["terms"]:
        sp = _spoken(t)
        translit = t.get("transliteration") or t.get("meaning") or t["term"]
        lines.append(f"| {t['n']} | {translit} | {sp['text']} |  |  |")
    lines.append("")
    return "\n".join(lines) + "\n"


def build_readme(data: dict) -> str:
    slug = data["book_slug"]
    n = data["top_n"]
    return (
        f"# Pronunciation probe — {slug}\n\n"
        f"A one-time pronunciation check covering the {n} highest-risk Arabic terms in\n"
        "this book, BEFORE any episode is generated. Catch and fix mispronunciations\n"
        "here, and every chapter (and future book, via the shared library) inherits the\n"
        "corrections.\n\n"
        "## Generate this in NotebookLM\n\n"
        "Click the Chapters cell to open the SOURCE to upload; the Episodes cell to\n"
        "open the FRAMING to paste into Customize.\n\n"
        "| Chapters | Episodes | Deep dive or debate | Length |\n"
        "|---|---|---|---|\n"
        "| [(pronunciation probe)](pronunciation-probe.md) | "
        "[EP00 — Pronunciation probe](00-framing.md) | Deep Dive | Default |\n\n"
        "(Length is a real variable here, not a formality. Run 1 on 2026-08-01 used\n"
        "**Shorter** for 39 terms — five minutes, seven seconds a term — and the model\n"
        "spent its budget on theme instead, naming 9. Use **Default**, or probe fewer\n"
        "terms: `run_pronunciation_probe.py <slug> --top-n 15 --rebuild`. Settled terms\n"
        "drop out of the next run, so a short list is a batch, not a compromise.)\n\n"
        "1. New notebook -> upload `pronunciation-probe.md` as the source.\n"
        "2. Customize -> paste `00-framing.md` into the prompt box.\n"
        "3. Generate the Audio Overview (**Default** length; see the note above).\n"
        "4. Listen once with `listen-checklist.md` open; mark OK? / Fix per term.\n"
        "5. Save the filled checklist; resume the orchestrator to apply corrections.\n\n"
        "Note: NotebookLM is non-deterministic. The probe shifts the odds toward\n"
        "correct pronunciation and surfaces terms it can NEVER say (mark those\n"
        "`GLOSS:`) — it is not a guarantee of a perfect final render.\n"
    )


def build_bundle(book_dir: Path) -> Path:
    data_path = book_dir / "_system" / "probe" / "probe-terms.json"
    if not data_path.exists():
        raise FileNotFoundError(f"{data_path} missing — run score_pronunciation_risk.py first")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    if not data.get("terms"):
        raise ValueError("probe-terms.json has no terms (nothing to probe)")

    # Enrich each term with its library entry (confirmed phonetic or unfixable gloss).
    lib = _load_library(book_dir)
    for t in data["terms"]:
        key = normalize_key(t["term"])
        if key in lib:
            t["_library"] = lib[key]

    # Compute the spoken render for every term through the SAME ladder the
    # framing compiler uses, so what the probe puts in the hosts' mouths is what
    # the episodes will. That includes the book's override table: an override is
    # an untested belief about how a term sounds, and hearing it is the point.
    # Keyed off the transliteration (the `term` field is raw script).
    # Book-mined glosses are deliberately NOT consulted — see the same note in
    # _pronunciation_block.compile_entries. Two extra reasons apply here: a term
    # replaced by an English gloss is never SPOKEN, so a probe entry for it
    # tests nothing; and the miner's reversals landed in this very bundle
    # ("vicegerent -> khalifa", "ya'sub -> You are the chief").
    tables = term_render.load_tables()
    overrides = term_render.load_book_overrides(book_dir)
    for t in data["terms"]:
        translit = t.get("transliteration") or t.get("meaning") or t["term"]
        ledger_entry = lib.get(normalize_key(translit)) or t.get("_library")
        res = term_render.render_for_audio(
            translit,
            segment=t.get("segment"),
            ledger_entry=ledger_entry,
            book_overrides=overrides,
            tables=tables,
        )
        t["_render"] = {"text": res.text, "is_english": res.is_english, "tier": res.tier}

    # Deduplicate by normalized key — keeps the first (highest-ranked) occurrence.
    # Prevents the same Arabic concept from appearing twice when the probe-terms.json
    # has both a plain and a diacritic/hamza variant (e.g. "Sharia" + "Shariʿa").
    seen: set[str] = set()
    deduped: list[dict] = []
    for t in data["terms"]:
        key = normalize_key(t["term"])
        if key not in seen:
            seen.add(key)
            deduped.append(t)

    # Reorder in segment presentation order (names → places → terms), then renumber
    # 1-N continuously.  Without this, Part 2 (places) might show n=59,108 while
    # Part 3 (terms) restarts at n=1, which breaks the listen-checklist and confuses
    # a reviewer trying to follow along.
    seg_buckets: dict[str, list[dict]] = {s: [] for s in SEGMENT_ORDER}
    for t in deduped:
        seg_buckets.setdefault(t["segment"], []).append(t)
    ordered: list[dict] = []
    for seg in SEGMENT_ORDER:
        ordered.extend(seg_buckets.get(seg, []))
    for i, t in enumerate(ordered, start=1):
        t["n"] = i
    data = {**data, "terms": ordered}

    carriers = mine_carriers(book_dir, data["terms"])

    out_dir = book_dir / "_system" / "probe" / "EP00-pronunciation-probe"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pronunciation-probe.md").write_text(build_source(data, carriers), encoding="utf-8")
    (out_dir / "00-framing.md").write_text(build_framing(data), encoding="utf-8")
    (out_dir / "listen-checklist.md").write_text(build_checklist(data), encoding="utf-8")
    (out_dir / "README.md").write_text(build_readme(data), encoding="utf-8")
    return out_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the NotebookLM pronunciation-probe bundle")
    ap.add_argument("book_dir", type=Path, help="content/<Bucket>/<slug>/")
    args = ap.parse_args(argv)
    out_dir = build_bundle(args.book_dir)
    print(f"probe bundle -> {out_dir}")
    for f in sorted(out_dir.iterdir()):
        print(f"  {f.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
