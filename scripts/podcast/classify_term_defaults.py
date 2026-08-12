"""classify_term_defaults.py — smart default language per glossary term.

For each Arabic term, decide whether the audio narrator should SPEAK IT IN ENGLISH
(the term is semantically transparent — a naturalized loanword like Allah/Quran or
a transparent calque like "First Intellect") or RECITE IT IN ARABIC (a technical /
doctrinal term whose meaning the English would lose — ta'wil, nasut, riyat).

Writes back to _system/glossary.yml using ONLY existing schema fields, so there is
no audio-pipeline change (replace_english already drops Arabic recitation):
  - english_override = a concise English rendering, for EVERY term (the reviewer
    sees it in the Arabic-review panel and it's what's used if the term is flipped
    to English).
  - for transparent terms only: decision = "replace_english", decided_by = "auto".

Idempotent + non-destructive: a term already carrying a HUMAN decision
(decided_by != "auto") is never touched. Uses flat-rate Claude Max via
`_run_claude_p` (no API spend), batched.

Usage:
  python3 scripts/podcast/classify_term_defaults.py <slug|book_dir>
  python3 scripts/podcast/classify_term_defaults.py <slug> --dry-run
  python3 scripts/podcast/classify_term_defaults.py <slug> --reclassify   # redo auto rows
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fill_glossary_arabic import emit_glossary_yml, parse_glossary_yml

_LLM_BATCH = 60
_CLAUDE_TIMEOUT = 600
_AUTO = "auto"


def _build_prompt(items: list[tuple[int, dict]]) -> str:
    rows = []
    for i, e in items:
        rows.append(
            f'{i}. term="{e.get("transliteration") or e.get("phonetic")}" '
            f'arabic="{e.get("arabic_script") or ""}" '
            f'context="{(e.get("first_seen_snippet") or "").strip()[:160]}"'
        )
    listing = "\n".join(rows)
    return f"""You decide, for each Arabic term from a scholarly Ismaili / broader Islamic book, \
whether an audio narrator should SPEAK IT IN ENGLISH or RECITE IT IN ARABIC.

- "english": the term's common English rendering is semantically transparent — a naturalised \
loanword the listener already knows (Allah, Quran, Imam, hadith, Kaaba, Shia, Sunni, mosque), \
or a transparent translation/calque they correlate to naturally (First Intellect, the Greatest \
Name, the Night Journey, the House, the Pen, the Tablet). The English carries the meaning.
- "arabic": the term is technical or doctrinal with no transparent everyday English, where \
reciting the Arabic preserves meaning the translation would lose (ta'wil, batin, zahir, nasut, \
lahut, riyat, hujja, walaya, dawr, qa'im, natiq, asas).

ALWAYS include a concise English rendering in "english" (max ~8 words) — it is shown to the \
reviewer regardless of lang, and it is what gets spoken if the term is set to English.

TERMS:
{listing}

Return ONLY a JSON array, one object per term, no prose:
[{{"i": <number>, "lang": "english|arabic", "english": "<concise English>"}}]"""


def _llm(items: list[tuple[int, dict]], book_dir: Path, log) -> dict[int, dict]:
    """Batched Claude-Max judgment. Returns {idx: {"lang":..., "english":...}}."""
    try:
        from _authoring._core import _run_claude_p, pure_json_call_options
    except Exception as e:
        log(f"    [defaults] claude unavailable ({e}) — leaving terms unchanged")
        return {}
    out: dict[int, dict] = {}
    for start in range(0, len(items), _LLM_BATCH):
        batch = items[start : start + _LLM_BATCH]
        rc, text, err = _run_claude_p(
            _build_prompt(batch),
            timeout=_CLAUDE_TIMEOUT,
            book_dir=book_dir,
            phase="audio-script",
            step="term-default-language",
            **pure_json_call_options(),
        )
        if rc != 0:
            log(f"    [defaults] batch rc={rc}: {(err or '')[:120]} — skipped")
            continue
        m = re.search(r"\[.*\]", text or "", re.DOTALL)
        if not m:
            log("    [defaults] no JSON array in reply — batch skipped")
            continue
        try:
            for obj in json.loads(m.group(0)):
                idx = int(obj.get("i"))
                lang = str(obj.get("lang") or "").strip().lower()
                eng = str(obj.get("english") or "").strip()
                if lang in ("english", "arabic"):
                    out[idx] = {"lang": lang, "english": eng}
        except Exception as e:
            log(f"    [defaults] JSON parse failed ({e}) — batch skipped")
    return out


def classify_defaults(entries: list[dict], book_dir: Path, *, reclassify: bool = False, log=print) -> dict[str, int]:
    """Mutate entries in place. Returns {english, arabic, skipped} counts."""
    todo: list[tuple[int, dict]] = []
    skipped = 0
    for i, e in enumerate(entries):
        decided_by = str(e.get("decided_by") or "").strip().lower()
        if decided_by and decided_by != _AUTO:  # human decision — never touch
            skipped += 1
            continue
        if decided_by == _AUTO and not reclassify:  # already auto-classified
            skipped += 1
            continue
        todo.append((i, e))

    counts = {"english": 0, "arabic": 0, "skipped": skipped}
    if not todo:
        return counts
    log(f"    [defaults] {len(todo)} term(s) -> Claude Max")
    verdicts = _llm(todo, book_dir, log)
    for i, e in todo:
        v = verdicts.get(i)
        if not v:
            continue
        if v["english"]:
            e["english_override"] = v["english"]  # display + flip value (all terms)
        if v["lang"] == "english":
            e["decision"] = "replace_english"
            e["decided_by"] = _AUTO
            counts["english"] += 1
        else:
            # Arabic default: keep recited. Clear only a prior AUTO replace decision.
            if str(e.get("decided_by") or "").lower() == _AUTO and e.get("decision") == "replace_english":
                e["decision"] = ""
                e["decided_by"] = ""
            counts["arabic"] += 1
    return counts


def _resolve_book_dir(arg: str) -> Path:
    p = Path(arg)
    if (p / "_system" / "glossary.yml").exists():
        return p
    for base in (Path("content"),):
        for g in base.glob(f"*/{arg}/_system/glossary.yml"):
            return g.parent.parent
    raise SystemExit(f"no glossary.yml for '{arg}'")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("book", help="book slug or book dir")
    ap.add_argument("--dry-run", action="store_true", help="classify but do not write")
    ap.add_argument("--reclassify", action="store_true", help="redo auto-classified rows")
    args = ap.parse_args(argv)

    book_dir = _resolve_book_dir(args.book)
    gloss = book_dir / "_system" / "glossary.yml"
    entries, top = parse_glossary_yml(gloss)
    print(f"{gloss.relative_to(book_dir.parent.parent)} — {len(entries)} terms", file=sys.stderr)

    counts = classify_defaults(entries, book_dir, reclassify=args.reclassify)
    print(
        f"  english (auto-flip): {counts['english']}  ·  arabic (recite): {counts['arabic']}  "
        f"·  skipped: {counts['skipped']}",
        file=sys.stderr,
    )

    if args.dry_run:
        print("  --dry-run: not written", file=sys.stderr)
        return 0
    gloss.write_text(emit_glossary_yml(entries, top), encoding="utf-8")
    print(f"  wrote {gloss.name}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
