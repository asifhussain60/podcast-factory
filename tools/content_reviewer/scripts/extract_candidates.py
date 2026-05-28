"""Extract ⟪ar:…⟫ candidates from binder 1 raw-extracts, dedupe + count,
write top entries to data/glossary-candidates.txt.

This is the candidate-list generator. The actual curated glossary lives at
data/ismaili-glossary.json and is hand-curated (and FROZEN during the
autonomous rollout).
"""
from __future__ import annotations
import re
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BINDER1_DIR = REPO_ROOT / "CONTENT" / "_shared" / "source-library" / "extracted" / "kashkole" / "07-uloom-mabda-wa-maad"
OUT_FILE = REPO_ROOT / "tools" / "content_reviewer" / "data" / "glossary-candidates.txt"

AR_MARKER_RE = re.compile(r"⟪ar:([^⟫]+)⟫")


def main() -> None:
    counter: Counter[str] = Counter()
    files = sorted(BINDER1_DIR.glob("*/_system/source/text/raw-extract.md"))
    if not files:
        raise SystemExit(f"No raw-extract.md files found under {BINDER1_DIR}")

    for f in files:
        text = f.read_text(encoding="utf-8")
        for m in AR_MARKER_RE.finditer(text):
            phrase = m.group(1).strip()
            # Strip leading/trailing whitespace, ZWNJ, and surrounding quote chars.
            phrase = phrase.strip("‌​ ’‘'\"")
            if not phrase:
                continue
            # Skip very long quotes (>60 chars) — those are full Quran ayat,
            # not glossary candidates.
            if len(phrase) > 60:
                continue
            counter[phrase] += 1

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# Glossary candidates extracted from binder 1 ({len(files)} chapters)")
    lines.append(f"# Total unique phrases: {len(counter)}")
    lines.append(f"# Sorted by frequency desc; phrase ≤ 60 chars only.")
    lines.append("")
    for phrase, count in counter.most_common(400):
        lines.append(f"{count:>4d}  {phrase}")
    OUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE {OUT_FILE}  ({len(counter)} unique, top 400 listed)")


if __name__ == "__main__":
    main()
