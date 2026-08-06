#!/usr/bin/env python3
"""dump_ksessions.py — extract one KSESSIONS group straight out of the .sql dump.

Why this exists
---------------
`adapters/ksessions.py` is a stub, and `db.py` talks to a live SQL Server inside
a Docker container. Neither is usable on a machine without Docker, and the one
existing ksessions bundle under content/_shared/source-library/extracted/ was
produced by a Phase-1 script that no longer exists in the repo.

This reads the committed dump directly, so a group can be extracted anywhere the
repo is checked out, with no database and no container.

THE DUMP IS UTF-16 LE WITH A BOM. `open(path)` finds nothing at all and fails
silently — always `encoding="utf-16"`. (grep on macOS is ugrep, which decodes it
transparently, so a working grep is not evidence that Python will work.)

Output shape matches the existing bundle exactly, so downstream readers do not
need to care which extractor produced it:

    <out>/_manifest.yml
    <out>/_system/source/<slug>.html          audit anchor, raw concatenated HTML
    <out>/_system/source/text/raw-extract.md  the deliverable
    <out>/_system/source/text/_extraction-notes.md

Arabic runs are wrapped in the ⟪ar:…⟫ markers Phase 0c greps for; section
provenance is preserved as `<!-- section N (id=…) -->` comments.

Usage
-----
    python3 -m tools.source_extractor.dump_ksessions --group 7 \
        --out content/_shared/source-library/extracted/ksessions/07-spiritual-ethos-of-ali

    # one category only
    python3 -m tools.source_extractor.dump_ksessions --group 7 --category 28 --out <dir>
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.source_extractor.html_to_md import html_to_md  # noqa: E402
from tools.source_extractor.slugify import slugify_english as slugify  # noqa: E402

DEFAULT_DUMP = Path("content/_shared/source-library/KSessions.sql")

# Column orders, read off the dump's own INSERT statements.
COLUMNS: dict[str, list[str]] = {
    "Groups": [
        "GroupID",
        "GroupName",
        "GroupImage",
        "GroupDescription",
        "Syllabus",
        "SpeakerID",
        "IsCompleted",
        "IsActive",
        "CreatedDate",
        "ChangedDate",
    ],
    "Categories": [
        "CategoryID",
        "CategoryName",
        "GroupID",
        "IsActive",
        "CreatedDate",
        "ChangedDate",
        "SortOrder",
    ],
    "Sessions": [
        "SessionID",
        "GroupID",
        "Sequence",
        "CategoryID",
        "SessionName",
        "Description",
        "SessionDate",
        "MediaPath",
        "SpeakerID",
        "DeliveryRating",
        "CreatedDate",
        "ChangedDate",
        "IsActive",
        "ImageCount",
        "ImagesFolderPath",
        "ImagesProcessedDate",
    ],
    "SessionTranscripts": [
        "TranscriptID",
        "SessionID",
        "Transcript",
        "CreatedDate",
        "ChangedDate",
    ],
}


def split_values(blob: str) -> list[object]:
    """Split one T-SQL VALUES(...) body into Python values.

    Handles N'…' / '…' with '' escapes, NULL, numbers, and CAST(N'…' AS DateTime).
    Written as a scanner rather than a regex because transcript bodies routinely
    contain commas, parentheses and doubled quotes.
    """
    out: list[object] = []
    i, n = 0, len(blob)
    while i < n:
        while i < n and blob[i] in " \t":
            i += 1
        if i >= n:
            break
        if blob.startswith("CAST(", i):
            depth, j = 0, i
            while j < n:
                if blob[j] == "(":
                    depth += 1
                elif blob[j] == ")":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                elif blob[j] == "'":
                    j += 1
                    while j < n:
                        if blob[j] == "'":
                            if j + 1 < n and blob[j + 1] == "'":
                                j += 2
                                continue
                            break
                        j += 1
                j += 1
            inner = blob[i:j]
            m = re.search(r"N?'((?:[^']|'')*)'", inner)
            out.append(m.group(1).replace("''", "'") if m else None)
            i = j
        elif blob[i] == "N" and i + 1 < n and blob[i + 1] == "'" or blob[i] == "'":
            j = i + 2 if blob[i] == "N" else i + 1
            buf: list[str] = []
            while j < n:
                if blob[j] == "'":
                    if j + 1 < n and blob[j + 1] == "'":
                        buf.append("'")
                        j += 2
                        continue
                    j += 1
                    break
                buf.append(blob[j])
                j += 1
            out.append("".join(buf))
            i = j
        else:
            j = i
            depth = 0
            while j < n and (blob[j] != "," or depth):
                if blob[j] == "(":
                    depth += 1
                elif blob[j] == ")":
                    depth -= 1
                j += 1
            tok = blob[i:j].strip()
            if tok.upper() == "NULL":
                out.append(None)
            else:
                try:
                    out.append(int(tok))
                except ValueError:
                    try:
                        out.append(float(tok))
                    except ValueError:
                        out.append(tok)
            i = j
        while i < n and blob[i] in " \t":
            i += 1
        if i < n and blob[i] == ",":
            i += 1
    return out


def read_tables(dump: Path, tables: set[str]) -> dict[str, list[dict]]:
    """One pass over the dump, collecting INSERT rows for the named tables."""
    rows: dict[str, list[dict]] = {t: [] for t in tables}
    prefixes = {f"INSERT [dbo].[{t}] (": t for t in tables}
    with open(dump, encoding="utf-16") as fh:
        for line in fh:
            if not line.startswith("INSERT "):
                continue
            for prefix, table in prefixes.items():
                if line.startswith(prefix):
                    marker = ") VALUES ("
                    at = line.find(marker)
                    if at == -1:
                        continue
                    body = line[at + len(marker) :].rstrip()
                    if body.endswith(")"):
                        body = body[:-1]
                    vals = split_values(body)
                    cols = COLUMNS[table]
                    rows[table].append(dict(zip(cols, vals)))
                    break
    return rows


def strip_editor_noise(html: str) -> str:
    """Remove Froala/Bootstrap scaffolding that carries no teaching content.

    Deliberately conservative: only structural attributes are dropped. The class
    taxonomy the source-library README marks as protected — esotericBlock,
    previligedBlock, quranWidget, poetry-section, hadees-widget, inlineArabic —
    is never touched, because those carry meaning the pipeline reads later.
    """
    html = re.sub(r'\s+(?:data-[\w-]+|contenteditable|spellcheck)="[^"]*"', "", html)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    return html


def build(group_id: int, dump: Path, out_dir: Path, category_id: int | None) -> int:
    wanted = {"Groups", "Categories", "Sessions", "SessionTranscripts"}
    print(f"reading {dump} (utf-16) ...", flush=True)
    data = read_tables(dump, wanted)

    groups = [g for g in data["Groups"] if g["GroupID"] == group_id]
    if not groups:
        print(f"ERROR: no Groups row with GroupID={group_id}", file=sys.stderr)
        return 1
    group = groups[0]

    cats = sorted(
        (c for c in data["Categories"] if c["GroupID"] == group_id),
        key=lambda c: c.get("SortOrder") or 0,
    )
    cat_by_id = {c["CategoryID"]: c for c in cats}

    sessions = [s for s in data["Sessions"] if s["GroupID"] == group_id]
    if category_id is not None:
        sessions = [s for s in sessions if s["CategoryID"] == category_id]
    sessions.sort(key=lambda s: s.get("Sequence") or 0)

    transcripts = {t["SessionID"]: t["Transcript"] for t in data["SessionTranscripts"]}

    group_name = (group.get("GroupName") or f"group-{group_id}").strip()
    slug = slugify(group_name)

    out_dir.mkdir(parents=True, exist_ok=True)
    src_dir = out_dir / "_system" / "source"
    txt_dir = src_dir / "text"
    txt_dir.mkdir(parents=True, exist_ok=True)

    md: list[str] = [f"# {group_name}\n"]
    md.append(f"\n*Source: ksessions-group, group {group_id} ({group_name}). {len(sessions)} sections.*\n")
    anchor: list[str] = []
    notes: list[str] = []
    current_cat: int | None = None
    covered = 0

    for position, sess in enumerate(sessions, 1):
        sid = sess["SessionID"]
        name = (sess.get("SessionName") or f"session-{sid}").strip()
        html = transcripts.get(sid)

        cat = sess.get("CategoryID")
        if cat != current_cat and cat in cat_by_id:
            current_cat = cat
            md.append(f"\n<!-- category {cat}: {cat_by_id[cat]['CategoryName']} -->\n")

        md.append(f"\n<!-- section {position} (id={sid}, raw_sort={sess.get('Sequence')}): {name} -->\n")

        if not html:
            notes.append(f"- session {sid} ({name}): no SessionTranscripts row — section empty")
            md.append(f"\n## {name}\n\n*(no transcript in the dump)*\n")
            continue

        covered += 1
        anchor.append(f"<!-- session {sid}: {name} -->\n{html}\n")
        body = html_to_md(strip_editor_noise(html)).strip()
        # The transcripts open with their own <h1>; only add a heading when they do not.
        if not body.startswith("#"):
            md.append(f"\n## {name}\n")
        md.append("\n" + body + "\n")

    (src_dir / f"{slug}.html").write_text("\n".join(anchor), encoding="utf-8")
    raw = txt_dir / "raw-extract.md"
    raw.write_text("".join(md), encoding="utf-8")

    (txt_dir / "_extraction-notes.md").write_text(
        "\n".join(notes) + "\n" if notes else "No notable issues.\n", encoding="utf-8"
    )

    items = "\n".join(
        f"    - {{position: {i}, id: {s['SessionID']}, label: {(s.get('SessionName') or '').strip()}, "
        f"category: {s.get('CategoryID')}, has_content: {bool(transcripts.get(s['SessionID']))}}}"
        for i, s in enumerate(sessions, 1)
    )
    (out_dir / "_manifest.yml").write_text(
        f"# generated by tools/source_extractor/dump_ksessions.py at "
        f"{datetime.now(timezone.utc).isoformat()}\n"
        f"source: ksessions\n"
        f"source_kind: ksessions-group\n"
        f"source_backend: sql-dump\n"
        f"dump: {dump}\n"
        f"shelf: {{kind: group, id: {group_id}, name: {group_name}, slug: {slug}}}\n"
        f"categories:\n"
        + "".join(
            f"  - {{id: {c['CategoryID']}, name: {c['CategoryName']}, sort_key: {c.get('SortOrder')}}}\n" for c in cats
        )
        + f"sections:\n  kind: session\n  items:\n{items}\n",
        encoding="utf-8",
    )

    print(f"group {group_id}: {group_name}")
    print(f"  categories : {len(cats)}")
    print(f"  sessions   : {len(sessions)} ({covered} with transcripts)")
    print(f"  markdown   : {raw} ({raw.stat().st_size:,} bytes)")
    print(f"  anchor     : {src_dir / f'{slug}.html'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--group", required=True, type=int)
    ap.add_argument("--category", type=int, default=None)
    ap.add_argument("--dump", type=Path, default=DEFAULT_DUMP)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    if not args.dump.is_file():
        print(f"ERROR: dump not found: {args.dump}", file=sys.stderr)
        return 2
    return build(args.group, args.dump, args.out, args.category)


if __name__ == "__main__":
    raise SystemExit(main())
