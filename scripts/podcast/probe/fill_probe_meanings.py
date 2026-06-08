#!/usr/bin/env python3
"""Fill concise English translations for probe terms that lack one.

Reads _system/probe/probe-terms.json, sends all terms that are missing a
meaning (or have a meaning longer than 6 words) to Gemini Flash in a single
batch call, and writes the updated meanings back to the same file.

Translations are kept to 1-4 words:
  - Prophets use biblical names (Ibrahim -> Abraham, Isa -> Jesus, ...)
  - Theological concepts get their core meaning, no explanation
  - Terms already confirmed in the pronunciation library are skipped

Usage:
  python3 scripts/podcast/probe/fill_probe_meanings.py <book_dir>
  python3 scripts/podcast/probe/fill_probe_meanings.py <book_dir> --probe <path>
  python3 scripts/podcast/probe/fill_probe_meanings.py <book_dir> --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

_SCRIPTS_PODCAST = Path(__file__).resolve().parents[1]
if str(_SCRIPTS_PODCAST) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_PODCAST))

_GEMINI_MODEL = "gemini-2.5-flash"
_MAX_WORDS_KEEP = 6   # meanings longer than this are condensed too

_SYSTEM_PROMPT = """\
You are translating Arabic terms from Ismaili Islamic theology into concise English.

Rules:
1. Return 1-4 English words only. No explanations, no sentences.
2. For prophets and Quranic figures, use the standard Western/biblical name:
   Ibrahim -> Abraham, Isa -> Jesus, Musa -> Moses, Nuh -> Noah,
   Idris -> Enoch, Yahya -> John, Yunus -> Jonah, Ilyas -> Elijah,
   Yusuf -> Joseph, Dawud -> David, Sulayman -> Solomon, Harun -> Aaron,
   Zakariyya -> Zechariah, Lut -> Lot, Ismail -> Ishmael, Ishaq -> Isaac,
   Hud -> Hud, Salih -> Salih, Shu'ayb -> Jethro, Adam -> Adam.
3. For theological/doctrinal terms, give the core concept in 1-4 words:
   Examples: "Allegorical Interpretation", "Spiritual Guardianship",
   "Speaking Prophet", "Divine Proof", "The Awaited One".
4. For historical figures by name, use "Name, Title" pattern if known,
   or just their transliterated name if unknown.
5. If the current_meaning is already good but too long, condense it.
6. If you do not know a term, return the transliteration unchanged.

Return ONLY a JSON array matching this exact schema:
[{"term": "<Arabic script>", "meaning": "<1-4 word English>"}]

No markdown, no code fences, no extra keys — raw JSON only.
"""


def _gemini_batch(terms_payload: list[dict], api_key: str) -> list[dict]:
    """Call Gemini Flash with a JSON batch of terms; return parsed array."""
    user_text = (
        "Translate these Arabic terms. Return only the JSON array.\n\n"
        + json.dumps(terms_payload, ensure_ascii=False)
    )
    body = json.dumps({
        "system_instruction": {"parts": [{"text": _SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": user_text}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 8192,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }).encode("utf-8")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{_GEMINI_MODEL}:generateContent?key={api_key}"
    )
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            d = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Gemini HTTP {exc.code}: {exc.read().decode(errors='replace')[:400]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini network error: {exc.reason}") from exc

    candidates = d.get("candidates", [])
    if not candidates:
        block = d.get("promptFeedback", {}).get("blockReason", "unknown")
        raise RuntimeError(f"Gemini returned no candidates (blockReason={block})")

    raw = candidates[0]["content"]["parts"][0]["text"].strip()
    # Strip markdown code fences if present despite responseMimeType.
    if raw.startswith("```"):
        raw = "\n".join(raw.splitlines()[1:])
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    return json.loads(raw)


def _needs_fill(term: dict) -> bool:
    """True if the term needs a new or condensed meaning."""
    m = (term.get("meaning") or "").strip()
    if not m:
        return True
    return len(m.split()) > _MAX_WORDS_KEEP


def fill_meanings(probe_path: Path, dry_run: bool = False) -> dict:
    """Read probe-terms.json, fill meanings, write back. Returns counts."""
    data = json.loads(probe_path.read_text(encoding="utf-8"))
    terms: list[dict] = data["terms"]

    to_fill = [t for t in terms if _needs_fill(t)]
    if not to_fill:
        print("All meanings already short — nothing to fill.")
        return {"filled": 0, "skipped": len(terms)}

    print(f"Filling meanings for {len(to_fill)}/{len(terms)} terms via Gemini…")

    # Build minimal payload for the LLM.
    payload = [
        {
            "term": t["term"],
            "transliteration": t.get("transliteration") or t["term"],
            "segment": t.get("segment", "terms"),
            "current_meaning": (t.get("meaning") or "").strip(),
        }
        for t in to_fill
    ]

    sys.path.insert(0, str(_SCRIPTS_PODCAST))
    from _secrets import get_gemini_key  # noqa: E402 — deferred import

    api_key = get_gemini_key()
    results = _gemini_batch(payload, api_key)

    # Build lookup: term (Arabic script) -> meaning.
    new_meanings: dict[str, str] = {}
    for r in results:
        if isinstance(r, dict) and r.get("term") and r.get("meaning"):
            new_meanings[r["term"]] = r["meaning"].strip()

    filled = 0
    for t in terms:
        m = new_meanings.get(t["term"])
        if m:
            if dry_run:
                print(f"  [{t['n']:3d}] {t['term']:25s} -> {m}")
            else:
                t["meaning"] = m
            filled += 1

    if not dry_run:
        probe_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {probe_path} — {filled} meanings filled, {len(terms) - filled} unchanged.")
    else:
        print(f"Dry-run: would fill {filled} meanings.")

    return {"filled": filled, "skipped": len(terms) - filled}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fill concise English meanings for probe terms")
    ap.add_argument("book_dir", type=Path, help="content/<Bucket>/<slug>/")
    ap.add_argument("--probe", type=Path, default=None, help="Override probe-terms.json path")
    ap.add_argument("--dry-run", action="store_true", help="Print proposed meanings, do not write")
    args = ap.parse_args(argv)

    probe_path = args.probe or (args.book_dir / "_system" / "probe" / "probe-terms.json")
    if not probe_path.exists():
        print(f"ERROR: probe-terms.json not found at {probe_path}", file=sys.stderr)
        return 1

    fill_meanings(probe_path, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
