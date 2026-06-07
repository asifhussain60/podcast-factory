#!/usr/bin/env python3
"""Build the NotebookLM pronunciation-probe bundle from ranked probe terms.

Consumes ``_system/probe/probe-terms.json`` (from score_pronunciation_risk.py)
and emits, under ``_system/probe/EP00-pronunciation-probe/``:

  - 00-framing.md          the Customize Prompt to paste into NotebookLM
  - pronunciation-probe.md the SOURCE to upload (a conversational walkthrough
                           that names each target term in context, segmented so
                           the audio maps to the checklist)
  - listen-checklist.md    the listen-once + corrections intake form
  - README.md              upload instructions incl. the NotebookLM settings table

Deterministic (no LLM): the source is a templated conversational walkthrough.
NotebookLM conversationalises it into two-host dialogue; our only goal is to
force every target term to be spoken so its rendering can be judged. The framing
supplies the INTENDED house-style pronunciation, so the probe also tests whether
NotebookLM honours the respelling at all.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Pull normalize_key from the shared ledger so keys match exactly.
_PROBE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROBE_DIR.parent / "knowledge"))
from pronunciation_ledger import normalize_key  # noqa: E402

def _load_library(book_dir: Path) -> dict[str, dict]:
    """Return a dict keyed by normalize_key(term) from pronunciations.jsonl.

    The library lives at content/knowledge-base/pronunciations.jsonl —
    two levels above the book slug (content/<Bucket>/<slug>/).
    Falls back gracefully if the file is absent.
    """
    lib_path = book_dir.parent.parent / "knowledge-base" / "pronunciations.jsonl"
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


def _carrier(term: str, snippet: str) -> str:
    """A neutral sentence that puts the term in the hosts' mouths.

    Ontology-neutral on purpose: the segment bucket is a best-effort guess, so
    the source never asserts a term IS a person/place (which mislabels common
    nouns like "Sharia"). It just names the term and, if a real first-occurrence
    snippet exists, gives that as context.
    """
    ctx = snippet.strip().rstrip(".")
    base = f"**{term}**"
    if ctx:
        return f"{base} — as in: “{ctx}”"
    return base


def build_source(data: dict) -> str:
    slug = data["book_slug"]
    by_seg: dict[str, list[dict]] = {s: [] for s in SEGMENT_ORDER}
    for t in data["terms"]:
        by_seg.setdefault(t["segment"], []).append(t)

    lines: list[str] = [
        f"# Pronunciation walkthrough — {slug}",
        "",
        "This is a short spoken walkthrough whose ONLY purpose is to say a set of",
        "Arabic-derived terms aloud, in order, so their pronunciation can be checked.",
        "Walk through every numbered item in sequence. For each item, say the term",
        "clearly, give the one-line context, and move on. Do not skip any item.",
        "",
    ]
    for seg in SEGMENT_ORDER:
        items = by_seg.get(seg) or []
        if not items:
            continue
        lines.append(f"## {SEGMENT_TITLES[seg]}")
        lines.append("")
        for t in items:
            lib = t.get("_library", {})
            if lib.get("status") == "unfixable" and lib.get("gloss"):
                gloss = lib["gloss"]
                lines.append(
                    f"{t['n']}. Do NOT say the Arabic term **{t['term']}**. "
                    f'Instead say the English phrase "{gloss}".'
                )
            else:
                lines.append(f"{t['n']}. Next, say {_carrier(t['term'], t.get('snippet', ''))}.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_framing(data: dict) -> str:
    slug = data["book_slug"]
    lines: list[str] = [
        f"# Framing — pronunciation probe ({slug})",
        "",
        "## Goal",
        "",
        "Produce a SHORT (3-5 minute) focused two-host segment that walks through",
        "the numbered terms in the source IN ORDER. The hosts must SAY each term",
        "aloud clearly. This is a pronunciation check, not a discussion — keep",
        "commentary minimal and make sure no numbered term is skipped.",
        "",
        "## Pronunciation",
        "",
        "Say each term ONCE. Do not double or spell-then-say.",
        "",
    ]
    needs_authoring: list[dict] = []
    for t in data["terms"]:
        lib = t.get("_library", {})
        lib_status = lib.get("status")

        if lib_status == "unfixable" and lib.get("gloss"):
            # User marked "Use English translation instead" — tell NLM to skip the Arabic.
            lines.append(f"- Do NOT say **{t['term']}** — say \"{lib['gloss']}\" instead.")
        elif lib_status == "confirmed" and lib.get("phonetic"):
            # Use the saved (human-verified) phonetic from the library.
            lines.append(f"- {t['term']}: {lib['phonetic']}")
        elif t.get("house_style_ok", True) and t.get("phonetic"):
            # Fall back to the probe-terms.json baseline phonetic.
            lines.append(f"- {t['term']}: {t['phonetic']}")
        else:
            # No valid spoken respelling yet — let NLM render naturally.
            needs_authoring.append(t)

    if needs_authoring:
        lines += [
            "",
            "The following terms have no validated respelling yet — say them as",
            "naturally as you can; we are listening to judge the raw rendering:",
        ]
        for t in needs_authoring:
            lines.append(f"- {t['term']}")
    lines += [
        "",
        "Arabic citations: speak ONCE at first occurrence, then English meaning.",
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
        "- In the **OK?** column put `y` if pronounced correctly, `n` if wrong.",
        "- For a wrong term, put a better house-style respelling in **Fix**",
        "  (lowercase, hyphen-syllables, CAPS = stress). e.g. `gha-zaa-lee`.",
        "- If NotebookLM simply cannot say it no matter what, write `GLOSS: <english",
        "  substitute>` in **Fix** (e.g. `GLOSS: the theologian al-Ghazali`).",
        "- Leave **Fix** blank when OK = y.",
        "",
        "The applier (phase 0probe) reads this table: `y` -> confirm the intended",
        "phonetic in the library; a respelling -> confirm the corrected form; a",
        "`GLOSS:` -> mark the term unfixable with that substitute.",
        "",
        "| n | term | intended | OK? | Fix |",
        "|---|------|----------|-----|-----|",
    ]
    for t in data["terms"]:
        if t.get("house_style_ok", True) and t.get("phonetic"):
            intended = t["phonetic"]
        else:
            intended = "_(needs respelling)_"
        lines.append(f"| {t['n']} | {t['term']} | {intended} |  |  |")
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
        "[EP00 — Pronunciation probe](00-framing.md) | Deep Dive | Shorter |\n\n"
        "(This diagnostic uses **Shorter** on purpose — it is a 3-5 min check, not a\n"
        "chapter/episode upload, which default to Long.)\n\n"
        "1. New notebook -> upload `pronunciation-probe.md` as the source.\n"
        "2. Customize -> paste `00-framing.md` into the prompt box.\n"
        "3. Generate the Audio Overview (use the **Shorter** length).\n"
        "4. Listen once with `listen-checklist.md` open; mark OK? / Fix per term.\n"
        "5. Save the filled checklist; resume the orchestrator to apply corrections.\n\n"
        "Note: NotebookLM is non-deterministic. The probe shifts the odds toward\n"
        "correct pronunciation and surfaces terms it can NEVER say (mark those\n"
        "`GLOSS:`) — it is not a guarantee of a perfect final render.\n"
    )


def build_bundle(book_dir: Path) -> Path:
    data_path = book_dir / "_system" / "probe" / "probe-terms.json"
    if not data_path.exists():
        raise FileNotFoundError(
            f"{data_path} missing — run score_pronunciation_risk.py first"
        )
    data = json.loads(data_path.read_text(encoding="utf-8"))
    if not data.get("terms"):
        raise ValueError("probe-terms.json has no terms (nothing to probe)")

    # Enrich each term with its library entry (confirmed phonetic or unfixable gloss).
    lib = _load_library(book_dir)
    for t in data["terms"]:
        key = normalize_key(t["term"])
        if key in lib:
            t["_library"] = lib[key]

    out_dir = book_dir / "_system" / "probe" / "EP00-pronunciation-probe"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "pronunciation-probe.md").write_text(build_source(data), encoding="utf-8")
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
