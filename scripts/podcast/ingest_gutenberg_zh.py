#!/usr/bin/env python3
"""ingest_gutenberg_zh.py — Chinese Project-Gutenberg HTML → volume slice → English.

The pipeline's PDF ingest (ingest_source.py) is PDF-only and assumes Arabic. This
script handles a Project-Gutenberg Classical/Traditional-Chinese HTML source (the
first `source_language: zh` book — Journey to the West, 西遊記) in two clean stages:

  STAGE 1 — split (deterministic, no LLM spend):
    Parse the Gutenberg HTML, strip boilerplate, detect chapter headings
    (`<p>第N回  <title>…</p>`), group paragraphs into chapters, select a chapter
    RANGE for one volume, and write the sliced Chinese source with explicit
    `<!-- chapter N -->` markers to the target volume's source dir.

  STAGE 2 — translate (--translate, Claude on Max, Tier-2 spend):
    Translate each selected chapter into fluent literary English via `claude -p`
    (flat-rate Max engine, cost-ledgered), preserving the `<!-- chapter N -->`
    markers, and write `raw-extract.md` so the orchestrator resumes at 0b.

The two stages are separate so the volume split (Step-1 setup, free) is decoupled
from the translation run (Step-1 upstream, metered/notional).

USAGE
    # Stage 1 — slice ch 1–33 of the series source into the vol-1 book (no spend):
    python3 scripts/podcast/ingest_gutenberg_zh.py \
        --source content/Fiction/journey-to-the-west/_system/source/journey-to-the-west-zh.gutenberg.html \
        --out-book journey-to-the-west-vol-1 --chapters 1-33

    # Stage 2 — translate the sliced Chinese → English raw-extract.md:
    python3 scripts/podcast/ingest_gutenberg_zh.py --out-book journey-to-the-west-vol-1 --translate

OUTPUTS (under <out-book>/_system/source/text/)
    chinese-source.md   sliced Chinese chapters with <!-- chapter N --> markers (Stage 1)
    raw-extract.md      English translation, same markers (Stage 2 — feeds 0b)
    ingest-provenance.json
"""
from __future__ import annotations

import argparse
import html as _html
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _paths import content_dir, find_content  # noqa: E402

# NOTE on numbering: this Gutenberg edition (#23962) uses an INCONSISTENT chapter
# numeral convention — positional digit strings (一一=11, 一○=10 using ○ U+25CB as
# zero, 一○○=100) MIXED with standard forms (十四=14, 八十七=87). Relying on the
# printed numeral is therefore fragile. We number chapters by SEQUENCE OF
# APPEARANCE (robust, contiguous 1..N) and keep the printed numeral only as a
# display label. All 100 chapters are detected once the numeral class includes ○.

_START_RE = re.compile(r"\*\*\* START OF THE PROJECT GUTENBERG")
_END_RE = re.compile(r"\*\*\* END OF THE PROJECT GUTENBERG")
# A chapter heading paragraph: <p ...>第<numeral>回   <title></p>. The numeral class
# covers standard (一-十百千) AND positional-zero forms (○ U+25CB, 〇 U+3007, 零).
_CHAPTER_RE = re.compile(
    r"<p[^>]*>\s*第([一二三四五六七八九十百千零○〇]+)回\s+([^<]*)</p>", re.UNICODE)
_P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.DOTALL | re.UNICODE)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(s: str) -> str:
    return _html.unescape(_TAG_RE.sub("", s)).strip()


def parse_chapters(html: str) -> list[dict]:
    """Return [{num, title, body}] for every 第N回 chapter in the PG content body."""
    # Trim to the content between START and END boilerplate markers.
    start = _START_RE.search(html)
    end = _END_RE.search(html)
    body_html = html[start.end() if start else 0: end.start() if end else len(html)]

    # Find chapter heading positions.
    heads = list(_CHAPTER_RE.finditer(body_html))
    if not heads:
        raise ValueError("no 第N回 chapter headings found — is this the right HTML?")

    chapters: list[dict] = []
    for i, h in enumerate(heads):
        title = _strip_tags(h.group(2))
        seg_start = h.end()
        seg_end = heads[i + 1].start() if i + 1 < len(heads) else len(body_html)
        seg_html = body_html[seg_start:seg_end]
        paras = [_strip_tags(m.group(1)) for m in _P_RE.finditer(seg_html)]
        paras = [p for p in paras if p]
        chapters.append({
            "num": i + 1,                 # canonical chapter index = sequence position
            "label": h.group(1),          # printed numeral as-is (display only)
            "title": title,
            "body": "\n\n".join(paras),
        })
    return chapters


def _parse_range(spec: str, max_n: int) -> tuple[int, int]:
    if "-" in spec:
        a, b = spec.split("-", 1)
        lo, hi = int(a), int(b)
    else:
        lo = hi = int(spec)
    return max(1, lo), min(max_n, hi)


def _out_book_dir(arg: str) -> Path:
    found = find_content(arg)
    if found:
        return found[2]
    # Not yet created — resolve its canonical path via the bucket resolver.
    return content_dir(arg)


def _render_chinese(chapters: list[dict]) -> str:
    out: list[str] = []
    for ch in chapters:
        out.append(f"<!-- chapter {ch['num']} -->")
        out.append(f"# 第{ch.get('label', ch['num'])}回　{ch['title']}")
        out.append("")
        out.append(ch["body"])
        out.append("")
    return "\n".join(out).strip() + "\n"


def _translate_prompt(num: int, title: str, body: str) -> str:
    return (
        "You are translating a chapter of the 16th-century Chinese novel 西遊記 "
        "(Journey to the West) into fluent, vivid LITERARY ENGLISH for a narrative "
        "audiobook/podcast. Translate the meaning faithfully — do NOT summarize, "
        "abridge, or omit events. Render the prose as natural modern English "
        "storytelling; render embedded poems as set-apart English verse. Keep "
        "proper names in consistent pinyin-style romanization (Sun Wukong, "
        "Tripitaka/Tang Monk, etc.). Output ONLY the translated chapter text — no "
        "preamble, no notes, no Chinese.\n\n"
        f"Begin your output with the marker line `<!-- chapter {num} -->` then a "
        f"heading line `# Chapter {num}: <an evocative English title>`.\n\n"
        f"SOURCE (Chinese, chapter {num} — 第{num}回 {title}):\n\n{body}"
    )


def translate_volume(book_dir: Path, *, model_flag: str | None, timeout: int) -> Path:
    """Stage 2: translate the sliced Chinese source → English raw-extract.md."""
    from _authoring._core import _run_claude_p
    from _cost_ledger import parse_text_from_json_stdout

    text_dir = book_dir / "_system" / "source" / "text"
    zh_path = text_dir / "chinese-source.md"
    out_path = text_dir / "raw-extract.md"
    if not zh_path.exists():
        sys.exit(f"ERROR: {zh_path} not found — run Stage 1 (split) first.")

    zh = zh_path.read_text(encoding="utf-8")
    # Re-split the sliced source by its <!-- chapter N --> markers.
    parts = re.split(r"<!-- chapter (\d+) -->", zh)
    # parts = ['', '1', '<body1>', '2', '<body2>', ...]
    pairs = [(int(parts[i]), parts[i + 1]) for i in range(1, len(parts) - 1, 2)]
    if not pairs:
        sys.exit("ERROR: no <!-- chapter N --> markers in chinese-source.md")

    translated: list[str] = []
    for num, chunk in pairs:
        # Recover title + body from the chunk (heading line then body).
        m = re.search(r"#\s*第\d+回[　\s]+(.*)", chunk)
        title = (m.group(1).strip() if m else "")
        body = chunk.strip()
        print(f"  translating chapter {num} ({len(body):,} chars)…")
        rc, stdout, stderr = _run_claude_p(
            _translate_prompt(num, title, body),
            book_dir=book_dir, phase="0a-translate", step=f"ch{num:03d}",
            model_flag=model_flag, timeout=timeout,
        )
        if rc != 0:
            sys.exit(f"ERROR: claude -p failed for chapter {num} (rc={rc}): {stderr[:300]}")
        text = parse_text_from_json_stdout(stdout).strip()
        if f"<!-- chapter {num} -->" not in text:
            text = f"<!-- chapter {num} -->\n{text}"
        translated.append(text)

    out_path.write_text("\n\n".join(translated).strip() + "\n", encoding="utf-8")
    print(f"  wrote {out_path} ({len(pairs)} chapters)")
    return out_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ingest_gutenberg_zh.py",
                                 description="Chinese Gutenberg HTML → volume slice → English.")
    ap.add_argument("--source", help="Path to the Gutenberg Chinese HTML (Stage 1).")
    ap.add_argument("--out-book", required=True, help="Target volume slug or path.")
    ap.add_argument("--chapters", help="Chapter range to slice, e.g. '1-33' (Stage 1).")
    ap.add_argument("--translate", action="store_true",
                    help="Stage 2: translate the sliced Chinese source to English.")
    ap.add_argument("--model", default=None, help="Model flag for translation (e.g. claude-opus-4-8).")
    ap.add_argument("--timeout", type=int, default=900, help="Per-chapter translate timeout (s).")
    args = ap.parse_args(argv)

    book_dir = _out_book_dir(args.out_book)
    text_dir = book_dir / "_system" / "source" / "text"

    if args.translate:
        translate_volume(book_dir, model_flag=args.model, timeout=args.timeout)
        return 0

    # Stage 1 — split
    if not args.source or not args.chapters:
        sys.exit("ERROR: Stage 1 needs --source and --chapters (or use --translate for Stage 2).")
    src = Path(args.source).expanduser()
    if not src.is_file():
        sys.exit(f"ERROR: source not found: {src}")

    chapters = parse_chapters(src.read_text(encoding="utf-8", errors="ignore"))
    max_n = max(c["num"] for c in chapters)
    lo, hi = _parse_range(args.chapters, max_n)
    selected = [c for c in chapters if lo <= c["num"] <= hi]
    if not selected:
        sys.exit(f"ERROR: no chapters in range {lo}-{hi} (book has {max_n} chapters)")

    text_dir.mkdir(parents=True, exist_ok=True)
    zh_path = text_dir / "chinese-source.md"
    zh_path.write_text(_render_chinese(selected), encoding="utf-8")

    prov = {
        "source": str(src),
        "source_language": "zh-Hant",
        "total_chapters_in_source": max_n,
        "selected_range": [lo, hi],
        "selected_count": len(selected),
        "selected_chapters": [c["num"] for c in selected],
    }
    (text_dir / "ingest-provenance.json").write_text(json.dumps(prov, indent=2) + "\n",
                                                     encoding="utf-8")
    words = sum(len(c["body"]) for c in selected)
    print(f"Stage 1 split: chapters {lo}-{hi} ({len(selected)} of {max_n}) → {zh_path}")
    print(f"  {words:,} Chinese chars. Next: --translate to produce raw-extract.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
