"""One-shot script: pull Master & Disciple ksessions transcripts from
kashkole-mssql Docker container, convert HTML→markdown, write per-session
files to content/Islamic/the-master-and-the-disciple/augment/.

Usage:
    python3 tools/source_extractor/_pull_ksessions.py
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import textwrap
import uuid
from pathlib import Path

CONTAINER = "kashkole-mssql"


def _sa_password() -> str:
    """Local kashkole-mssql `sa` password, read from the environment.

    Set MSSQL_SA_PASSWORD before running (see .env.example).
    """
    pw = os.environ.get("MSSQL_SA_PASSWORD")
    if not pw:
        raise RuntimeError(
            "MSSQL_SA_PASSWORD is not set. Export the local SQL Server "
            "container's sa password first, e.g. `export MSSQL_SA_PASSWORD=...` "
            "(see .env.example)."
        )
    return pw

REPO_ROOT = Path(__file__).resolve().parents[2]
AUGMENT_DIR = REPO_ROOT / "content/Islamic/the-master-and-the-disciple/augment"
AUGMENT_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = {
    31: ("01", "true-sources-of-knowledge"),
    34: ("02", "spiritual-symbols"),
    35: ("03", "knowledge-vs-actions"),
    37: ("04", "disciple-becomes-master"),
    38: ("05", "unity-and-justice"),
}


def query(sql: str) -> list[dict]:
    tmp_in = f"/tmp/q-{uuid.uuid4().hex}.sql"
    tmp_out = f"/tmp/q-{uuid.uuid4().hex}.json"
    wrapped = f"SET NOCOUNT ON;\nUSE [KSESSIONS];\n{sql}\n"

    subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "sh", "-c", f"cat > {tmp_in}"],
        input=wrapped.encode("utf-8"), check=True,
    )
    subprocess.run(
        ["docker", "exec", CONTAINER,
         "/opt/mssql-tools18/bin/sqlcmd",
         "-S", "localhost", "-U", "sa", "-P", _sa_password(), "-C",
         "-y", "0", "-Y", "0", "-i", tmp_in, "-o", tmp_out],
        check=True,
    )
    raw = subprocess.run(
        ["docker", "exec", CONTAINER, "cat", tmp_out],
        capture_output=True, check=True,
    ).stdout.decode("utf-8")
    subprocess.run(["docker", "exec", CONTAINER, "rm", "-f", tmp_in, tmp_out], check=False)

    lines = [ln.rstrip("\r") for ln in raw.split("\n")]
    payload = [ln for ln in lines
               if ln.strip() and not ln.startswith("Changed database context")]
    return json.loads("".join(payload)) if payload else []


def html_to_md(html: str) -> str:
    """Very light HTML→markdown for ksessions transcript HTML."""
    text = html

    # Headings
    text = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n# \1\n", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n## \1\n", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"\n### \1\n", text, flags=re.DOTALL | re.IGNORECASE)

    # Bold / italic
    text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", text, flags=re.DOTALL | re.IGNORECASE)

    # Paragraphs and line breaks
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Lists
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[ou]l[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</[ou]l>", "\n", text, flags=re.IGNORECASE)

    # Arabic span (ksessions wraps Arabic in <span class="arabic"> or similar)
    text = re.sub(r'<span[^>]*class="[^"]*arabic[^"]*"[^>]*>(.*?)</span>',
                  r"⟪ar:\1⟫", text, flags=re.DOTALL | re.IGNORECASE)

    # IMG_URL placeholder — convert to source-page citation placeholder
    text = re.sub(r'\{\{IMG_URL:Resources/IMAGES/\d+/[^}]+\}\}',
                  "[📄 _source-page-ref: see _system/source/images/_]", text)

    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)

    # HTML entities
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<") \
               .replace("&gt;", ">").replace("&quot;", '"').replace("&#39;", "'")
    text = re.sub(r"&[a-z]+;", " ", text)

    # Collapse excess blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def tag_commentary(text: str) -> str:
    """
    Heuristic tagging pass: mark sections that look like modern teaching
    commentary with [TEACHING-CONTEXT] and book-faithful passages with
    [BOOK-CONTENT].  This is a light pass — the LLM can refine downstream.
    """
    MODERN_SIGNALS = [
        r"\bStarbucks\b", r"\bAmazon\b", r"\bCovid\b", r"\bcoronavirus\b",
        r"\bpandemic\b", r"\bquarantine\b", r"\bprime delivery\b",
        r"\btoilet paper\b", r"\bNetflix\b", r"\bsocial media\b",
        r"\bsmartphone\b", r"\binternet\b", r"\bYouTube\b",
    ]
    pattern = re.compile("|".join(MODERN_SIGNALS), re.IGNORECASE)

    paragraphs = re.split(r"\n{2,}", text)
    tagged = []
    for para in paragraphs:
        if para.strip().startswith("#"):
            tagged.append(para)
        elif re.search(r"⟪ar:", para):
            tagged.append(f"[BOOK-CONTENT]\n{para}")
        elif pattern.search(para):
            tagged.append(f"[TEACHING-CONTEXT]\n{para}")
        elif re.search(r"\bRasul Allah\b|\bHadees\b|\bImam\b|\bQuran\b|\bSura\b"
                       r"|\bAyat\b|\bSyedna\b|\bDaee\b|\bDuat\b|\bWali\b",
                       para, re.IGNORECASE):
            tagged.append(f"[BOOK-CONTENT]\n{para}")
        else:
            tagged.append(para)
    return "\n\n".join(tagged)


def pull_category(cat_id: int, prefix: str, slug: str) -> tuple[str, list[dict]]:
    """Pull all sessions for a category, return combined markdown + session metadata."""

    sessions = query(f"""
        SELECT s.SessionID, s.Sequence, s.SessionName, s.Description,
               st.Transcript AS html
        FROM Sessions s
        LEFT JOIN SessionTranscripts st ON st.SessionID = s.SessionID
        WHERE s.CategoryID = {cat_id} AND s.IsActive = 1
        ORDER BY s.Sequence
        FOR JSON PATH;
    """)

    cat_name = sessions[0].get("CategoryName") if sessions else slug
    lines = [
        f"# {prefix} — {slug.replace('-', ' ').title()}",
        f"",
        f"> Source: KSESSIONS Group 12 (Master and the Disciple), Category {cat_id}",
        f"> Sessions: {len(sessions)}",
        f"",
        "---",
        "",
    ]

    meta_rows = []
    for s in sessions:
        sid = s["SessionID"]
        seq = s["Sequence"]
        name = s["SessionName"]
        desc = s.get("Description") or ""
        html = s.get("html") or ""

        lines.append(f"## Session {seq}: {name}")
        if desc and desc.strip() != "<--- Enter Description --->":
            lines.append(f"*{desc.strip()}*")
        lines.append("")

        if html:
            md = html_to_md(html)
            md = tag_commentary(md)
            lines.append(md)
        else:
            lines.append("_[No transcript available]_")

        lines.append("")
        lines.append("---")
        lines.append("")

        meta_rows.append({"seq": seq, "id": sid, "name": name, "desc": desc})

    return "\n".join(lines), meta_rows


def build_synthesis_header(all_meta: dict[int, list[dict]]) -> str:
    """Build the _synthesis.md front matter / session→chapter mapping guide."""
    CHAPTER_MAPPING = """
## Session → Chapter alignment guide

This table maps the 5 teaching sessions onto the book's thematic arc.
Use this during 0d (chapter design) to align chapter boundaries with session content.

| Session | Category | Sessions covered | Likely chapter(s) |
|---------|----------|-----------------|-------------------|
| 01 | True Sources Of Knowledge | 1-4 (Intro, Glorifying Allah, How To Seek, Allegiance) | Ch01–02 |
| 02 | Spiritual Symbols | 5-7 (Root Principles, Symbols Based On Roots, Worldly Symbols) | Ch02–03 |
| 03 | Knowledge vs Actions | 8-11 (Three Levels, Power vs Strength, Acting With Knowledge, Differences/Purifying) | Ch03–04 |
| 04 | Disciple Becomes Master | 12-16 (Rebirth, Returning Home, Ka'ab Al-Ahbaar, Abu Malik Debates Saleh, Description of Religion) | Ch04–05 |
| 05 | Unity & Justice | 17-21 (Who is Allah, Intermediaries, Unbroken Chain, Return To Allah) | Ch05–06 |

## How to use this augment in the V2 pipeline

- **Phase 0d (chapter design)**: read `_synthesis.md` + per-session files alongside
  `_system/source/text/refined-english.md` when deciding chapter boundaries
- **Phase 0e (enrichment)**: pass per-session file for the corresponding chapter(s)
  as supplemental context; filter `[TEACHING-CONTEXT]` blocks unless the episode
  explicitly uses contemporary analogy
- **[BOOK-CONTENT]** tags = safe for direct use in episode framing
- **[TEACHING-CONTEXT]** tags = use only if the episode format calls for
  contemporary bridge material; never attribute to Syedna Jaffer or the book

## Source paths

- Arabic source images: `_system/source/images/page_0001.png` … `page_0095.png`
- OCR Arabic extract: `_system/source/ocr/raw-extract.md`
- OCR English translation: `_system/source/ocr/translated-en.md`
- Curator refined English: `_system/source/text/refined-english.md`
- Stitched PDF: `_system/source/ocr/source-stitched.pdf`
""".strip()
    return CHAPTER_MAPPING


def main():
    print("Pulling ksessions transcripts for Master and the Disciple...")
    all_meta: dict[int, list[dict]] = {}

    for cat_id, (prefix, slug) in CATEGORIES.items():
        fname = f"{prefix}-{slug}.md"
        out_path = AUGMENT_DIR / fname

        if cat_id == 31 and out_path.exists():
            print(f"  {fname}  (skipping — category 31 already exists, re-pulling to augment/)")

        print(f"  Pulling category {cat_id} ({slug})...", end=" ", flush=True)
        content, meta = pull_category(cat_id, prefix, slug)
        out_path.write_text(content, encoding="utf-8")
        all_meta[cat_id] = meta
        print(f"{len(meta)} sessions, {len(content):,} chars → {fname}")

    # Write synthesis file
    syn_path = AUGMENT_DIR / "_synthesis.md"
    syn_lines = [
        "# _synthesis — Master and the Disciple: ksessions augmentation",
        "",
        "> Generated from KSESSIONS database (Group 12, 5 categories, 21 sessions).",
        "> This file is the pipeline entry-point for the augment layer.",
        "",
        build_synthesis_header(all_meta),
        "",
        "---",
        "",
        "## Session inventory",
        "",
    ]
    for cat_id, (prefix, slug) in CATEGORIES.items():
        syn_lines.append(f"### {prefix} — {slug.replace('-', ' ').title()}")
        for s in all_meta.get(cat_id, []):
            syn_lines.append(f"- **{s['seq']}.** {s['name']} — {s['desc'][:80] if s['desc'] and s['desc'].strip() != '<--- Enter Description --->' else '(no description)'}")
        syn_lines.append("")

    syn_path.write_text("\n".join(syn_lines), encoding="utf-8")
    print(f"  _synthesis.md written")

    print(f"\nDone. Files written to {AUGMENT_DIR}/")
    for f in sorted(AUGMENT_DIR.iterdir()):
        size = f.stat().st_size
        print(f"  {f.name:55s}  {size:>8,} bytes")


if __name__ == "__main__":
    main()
