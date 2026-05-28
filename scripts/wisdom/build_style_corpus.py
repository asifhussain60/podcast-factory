"""build_style_corpus.py — Wave I (I0b): Extract KSessions teaching-style corpus.

Reads the KSessions SQL dump (UTF-16 LE, SQL Server format) and extracts plain-
text passages from Groups 3 (Wise Reminder), 17 (Ikhwan — Cat 51 only), and 18
(Asaas Al-Taveel) plus Session 2346 (Isbat al-Imamah / Necessity Of Imam).

Strips HTML. Writes two outputs:
  - scripts/wisdom/_style_corpus.jsonl: raw passages (gitignored, used by rewrite)
  - content/_shared/source-library/style-imprint.md: distilled ≤800-word guide

CLI usage:
    python3 scripts/wisdom/build_style_corpus.py [--sql-path PATH]
    python3 scripts/wisdom/build_style_corpus.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent.parent
sys.path.insert(0, str(_REPO / "scripts" / "podcast"))

KSESSIONS_SQL = _REPO / "CONTENT" / "_shared" / "source-library" / "KSessions.sql"
STYLE_CORPUS_JSONL = _HERE / "_style_corpus.jsonl"
STYLE_IMPRINT_MD = _REPO / "content" / "_shared" / "source-library" / "style-imprint.md"
STYLE_GROUPS = {3, 17, 18}
ISBAT_SESSION_ID = 2346


class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts)


def strip_html(raw: str) -> str:
    """Strip HTML tags and return clean plain text."""
    parser = _HTMLStripper()
    parser.feed(raw)
    text = parser.get_text()
    # Clean up extra whitespace
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


def _load_sql_content(sql_path: Path) -> str:
    """Read SQL file with UTF-16 LE encoding (SQL Server dump format)."""
    try:
        return sql_path.read_text(encoding="utf-16-le")
    except UnicodeDecodeError:
        # Fallback: try utf-16 with BOM detection
        return sql_path.read_text(encoding="utf-16")


def parse_groups(content: str) -> dict[int, str]:
    """Parse Groups table. Returns {group_id: group_name}."""
    result = {}
    for m in re.finditer(
        r"INSERT \[dbo\]\.\[Groups\][^V]*VALUES\s*\((\d+),\s*N'([^']+)'",
        content, re.DOTALL
    ):
        result[int(m.group(1))] = m.group(2)
    return result


def parse_sessions(content: str) -> dict[int, int]:
    """Parse Sessions table. Returns {session_id: group_id}."""
    result = {}
    for m in re.finditer(
        r"INSERT \[dbo\]\.\[Sessions\][^V]*VALUES\s*\((\d+),\s*(\d+),",
        content, re.DOTALL
    ):
        result[int(m.group(1))] = int(m.group(2))
    return result


def parse_summaries(content: str) -> list[dict]:
    """Parse SessionSummary table. Returns list of {session_id, title, text}."""
    results = []
    # Match: INSERT ... VALUES (id, session_id, seq, N'title', N'content', ...)
    pattern = re.compile(
        r"INSERT \[dbo\]\.\[SessionSummary\][^V]*VALUES\s*\("
        r"(\d+),\s*(\d+),\s*(\d+),\s*N'((?:[^']|'')*)',\s*N'((?:[^']|'')*)'",
        re.DOTALL
    )
    for m in pattern.finditer(content):
        session_id = int(m.group(2))
        title = m.group(4).replace("''", "'")
        raw_html = m.group(5).replace("''", "'")
        text = strip_html(raw_html)
        if text and len(text) > 40:
            results.append({
                "session_id": session_id,
                "title": title,
                "text": text,
            })
    return results


def build_corpus(sql_path: Path) -> list[dict]:
    """Extract style passages from target groups."""
    print(f"Loading {sql_path.name} ({sql_path.stat().st_size // (1024*1024)}MB)…")
    content = _load_sql_content(sql_path)

    groups = parse_groups(content)
    sessions = parse_sessions(content)
    summaries = parse_summaries(content)

    target_sessions = {
        sid for sid, gid in sessions.items()
        if gid in STYLE_GROUPS
    }
    target_sessions.add(ISBAT_SESSION_ID)

    corpus = []
    for summary in summaries:
        sid = summary["session_id"]
        if sid not in target_sessions:
            continue
        gid = sessions.get(sid, 0)
        corpus.append({
            "session_id": sid,
            "group_id": gid,
            "group_name": groups.get(gid, f"Group {gid}"),
            "title": summary["title"],
            "text": summary["text"],
        })

    print(f"Extracted {len(corpus)} style passages from {len(target_sessions)} sessions.")
    return corpus


def distill_style_imprint(corpus: list[dict]) -> str:
    """Build a ≤800-word style guide from the corpus.

    The guide captures Asif's three signature teaching patterns:
    1. Recap + bridge opening
    2. Arabic term + immediate English gloss
    3. Teaching by contrast / explicit enumerated structure
    """
    # Sample passages from each group for illustration
    by_group: dict[int, list[str]] = {}
    for entry in corpus:
        gid = entry["group_id"]
        by_group.setdefault(gid, []).append(entry["text"])

    # Take up to 3 representative passages per group (first 200 chars each)
    samples = {}
    for gid, texts in by_group.items():
        samples[gid] = [t[:200] for t in texts[:3]]

    guide_lines = [
        "# Teaching Style Guide — Asif Hussain (KSessions Corpus)",
        "",
        "This guide distils three signature patterns from Asif's delivered lectures.",
        "Apply these patterns when rewriting chapter text to match his teaching register.",
        "",
        "## Pattern 1: Recap + Bridge Opening",
        "",
        "Every session opens with a one-paragraph recap of the previous session,",
        "then a bridge sentence framing the day's question. Never starts cold.",
        "",
        "Example shape:",
        "> 'Last time we established that... Today the question before us is...'",
        "",
        "## Pattern 2: Arabic Term + Immediate English Gloss",
        "",
        "Arabic terms are never left hanging. The English meaning follows immediately",
        "in parentheses or after an em-dash.",
        "",
        "Example shape:",
        "> 'The concept of *fitra* — our natural disposition — tells us...'",
        "> 'This is what the Quran means by *'aql* (the reasoning faculty).'",
        "",
        "## Pattern 3: Teaching by Contrast or Enumerated Structure",
        "",
        "Structure is made visible. Each element is given a *why*.",
        "Contrasts are named explicitly. Lists are numbered, not implicit.",
        "",
        "Example shape:",
        "> 'There are three reasons Islam permits X. First... Second... Third...'",
        "> 'The difference between X and Y is not Z but rather W.'",
        "",
        "## Hard Rules for Rewriters",
        "",
        "- **Never add content not in the source** — rephrase, do not expand.",
        "- **Protected content survives verbatim**: Quran verses, hadith, poetry,",
        "  esoteric/ta'wil passages, sharia rulings. Wrap these — never replace.",
        "- **No cold openings**: every rewritten chapter must begin with context.",
        "- **Arabic glossing is mandatory**: every Arabic term needs an English gloss.",
        "",
    ]

    # Add representative group passages as context
    group_names = {3: "Wise Reminder", 17: "Ikhwan", 18: "Asaas Al-Taveel"}
    guide_lines.append("## Representative Passages (for tone reference)")
    guide_lines.append("")
    for gid in sorted(samples.keys()):
        if not samples[gid]:
            continue
        gname = group_names.get(gid, f"Group {gid}")
        guide_lines.append(f"### {gname}")
        guide_lines.append("")
        for sample in samples[gid][:2]:
            guide_lines.append(f"> {sample.replace(chr(10), ' ')}")
            guide_lines.append("")

    guide = "\n".join(guide_lines)
    # Enforce ≤800 words
    words = guide.split()
    if len(words) > 800:
        guide = " ".join(words[:800]) + "\n\n*(truncated to 800 words)*"
    return guide


def main() -> None:
    parser = argparse.ArgumentParser(description="Build KSessions style corpus.")
    parser.add_argument("--sql-path", type=Path, default=KSESSIONS_SQL,
                        help="Path to KSessions.sql dump")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse only; do not write output files")
    args = parser.parse_args()

    if not args.sql_path.exists():
        print(f"ERROR: SQL dump not found: {args.sql_path}", file=sys.stderr)
        sys.exit(1)

    corpus = build_corpus(args.sql_path)
    if not corpus:
        print("ERROR: No passages extracted. Check SQL path and group IDs.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"[DRY RUN] Would write {len(corpus)} passages to corpus JSONL.")
        print(f"[DRY RUN] Would write style-imprint.md ({len(distill_style_imprint(corpus).split())} words).")
        return

    # Write corpus JSONL (gitignored)
    STYLE_CORPUS_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with STYLE_CORPUS_JSONL.open("w", encoding="utf-8") as fh:
        for entry in corpus:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Wrote {len(corpus)} passages → {STYLE_CORPUS_JSONL.relative_to(_REPO)}")

    # Write style imprint
    STYLE_IMPRINT_MD.parent.mkdir(parents=True, exist_ok=True)
    imprint = distill_style_imprint(corpus)
    STYLE_IMPRINT_MD.write_text(imprint, encoding="utf-8")
    word_count = len(imprint.split())
    print(f"Wrote style-imprint.md ({word_count} words) → {STYLE_IMPRINT_MD.relative_to(_REPO)}")


if __name__ == "__main__":
    main()
