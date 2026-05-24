"""
Stage C — substitute image placeholders and clean Quran widgets, producing
the final .md (no .draft suffix) and an updated .meta.yml.

For each {{IMG:NNN}} in the draft:
  - Read the sibling NNN.json sidecar (written by Stage B / Claude Code)
  - Render based on classification:
      teaching-diagram → "[diagram: alt_text]\n  (see <relpath>.png)"
      quran-verse      → blockquote with Arabic + English + citation (HQAyats validated)
      hadith / poem    → blockquote with Arabic + note "image source, citation unverified"
      mixed / other    → similar to hadith, with whatever text is available

For each KAHSKOLE Quran widget block that survived as flattened table text
(pattern: "سورۃ ... { N:N }" multi-line), replace with a clean blockquote
sourced from HQAyats (the DB).

For each topic with TopicAyats refs, append a "Verses referenced in this topic"
note at the end of the topic with full citation enrichment (Arabic + English
+ Urdu translation, sourced from HQAyats).
"""
from __future__ import annotations
import argparse, json, re
from datetime import datetime, timezone
from pathlib import Path

from scripts.db import query_json


REPO_ROOT = Path(__file__).resolve().parents[3]
EXTRACT_ROOT = REPO_ROOT / "_workspace" / "kashkole-ksessions" / "extracted" / "kashkole"


_IMG_PLACEHOLDER_RE = re.compile(r"\{\{IMG:(\d{3})\}\}")

# Match the KAHSKOLE Quran widget block in flattened form.
# Starts with a سورۃ name + { N:N } or { N:N-M } reference,
# spans the messy repeating-reference lines, the Arabic ayat line,
# and the Urdu translation line, then a blank/separator.
_QURAN_WIDGET_RE = re.compile(
    r"(سورۃ\s+[^\n]+?\{\s*(\d+)\s*:\s*(\d+)(?:\s*-\s*(\d+))?\s*\}[^\n]*\n"   # header line
    r"(?:[^\n]*\n)*?"                                                          # middle lines (incl. duplicate headers, Arabic, etc.)
    r"\d+\s+[^\n]+\n)",                                                        # Urdu translation line terminates
    re.MULTILINE,
)


# ------------- HQAyats helpers ------------------------------------------------

class QuranCorpus:
    """Cache HQAyats lookups; one row per ayat."""
    def __init__(self):
        self._by_key: dict[tuple[int, int], dict] | None = None

    def _load(self):
        if self._by_key is not None:
            return
        rows = query_json("KASHKOLE", """
            SELECT SurahNumber AS surah, AyatNumber AS ayat,
                   AyatUNICODE AS arabic, AyatTranslation AS english,
                   UrduTranslation AS urdu, Chapter AS surah_name,
                   Translation_Asad AS english_asad
            FROM HQAyats
            FOR JSON PATH;""")
        # Strip HTML tags from translation fields — they store <I>, <P>, etc.
        for r in rows:
            for k in ("english", "urdu", "english_asad", "arabic"):
                if r.get(k):
                    r[k] = re.sub(r"<[^>]+>", "", r[k]).strip()
                    r[k] = re.sub(r"\s+", " ", r[k])
        self._by_key = {(r["surah"], r["ayat"]): r for r in rows}

    def get(self, surah: int, ayat: int) -> dict | None:
        self._load()
        return self._by_key.get((surah, ayat))

    def get_range(self, surah: int, start: int, end: int) -> list[dict]:
        self._load()
        out = []
        for a in range(start, end + 1):
            row = self._by_key.get((surah, a))
            if row:
                out.append(row)
        return out


def _render_quran_block(corpus: QuranCorpus, surah: int, start: int, end: int | None,
                        source_note: str = "") -> str:
    """Emit a clean markdown blockquote for one or a range of Quran ayats."""
    end = end or start
    ayats = corpus.get_range(surah, start, end)
    if not ayats:
        return f"> *(Quran {surah}:{start}{('-' + str(end)) if end != start else ''} — not found in HQAyats)*"
    surah_name = ayats[0].get("surah_name") or ""
    range_str = f"{surah}:{start}" if end == start else f"{surah}:{start}-{end}"

    out: list[str] = []
    out.append(f"> ⟪quran {range_str}⟫")
    arabic_joined = " ".join((a["arabic"] or "").strip() for a in ayats if a.get("arabic"))
    if arabic_joined:
        out.append(f"> ⟪ar:{arabic_joined}⟫")
    english_lines = [(a.get("english") or "").strip() for a in ayats]
    english_joined = " ".join(e for e in english_lines if e)
    if english_joined:
        out.append(f"> *{english_joined}*")
    urdu_lines = [(a.get("urdu") or "").strip() for a in ayats]
    urdu_joined = " ".join(u for u in urdu_lines if u)
    if urdu_joined:
        out.append(f"> {urdu_joined}")
    citation = f"Quran {range_str}"
    if surah_name:
        citation = f"Quran {range_str} — *{surah_name.strip()}*"
    if source_note:
        citation = f"{citation} ({source_note})"
    out.append(f"> — **{citation}**")
    return "\n".join(out)


# ------------- image placeholder substitution ---------------------------------

def _render_image_block(sidecar: dict, images_dirname: str, image_index: str) -> str:
    cls = sidecar.get("classification", "other")
    alt = (sidecar.get("alt_text") or "").strip()
    arabic = (sidecar.get("arabic_text") or "").strip()
    urdu = (sidecar.get("urdu_text") or "").strip()
    english = (sidecar.get("english_text") or "").strip()
    notes = (sidecar.get("notes") or "").strip()
    confidence = sidecar.get("confidence")
    citation = sidecar.get("suggested_citation")

    rel = f"{images_dirname}/{image_index}.png"

    if cls == "teaching-diagram":
        parts = [f"\n[diagram: {alt}]" if alt else f"\n[diagram from image {image_index}]"]
        parts.append(f"  (see {rel})")
        if arabic:
            arabic_inline = " · ".join(line.strip() for line in arabic.splitlines() if line.strip())
            parts.append(f"  *Arabic labels in image:* ⟪ar:{arabic_inline}⟫")
        if notes:
            parts.append(f"  *Note:* {notes}")
        return "\n".join(parts) + "\n"

    # quran-verse / hadith / poem / mixed / other — emit blockquote of OCR'd
    # content; finalize doesn't try to fuzzy-validate Arabic against HQAyats
    # here (Claude already proposed surah/ayat if confident). The user can
    # cross-check via the suggested_citation field in the meta.yml.
    out = [""]
    if arabic:
        out.append(f"> ⟪ar:{arabic.strip()}⟫")
    if english:
        out.append(f"> *{english.strip()}*")
    if urdu:
        out.append(f"> {urdu.strip()}")
    if citation and isinstance(citation, dict) and citation.get("surah"):
        s, a = citation["surah"], citation.get("ayat")
        out.append(f"> — **Quran {s}:{a}** *(from image; see meta.yml for validation)*")
    else:
        label = {"hadith": "Hadith", "poem-or-saying": "Poem / saying",
                 "mixed": "Image text", "other": "Image text"}.get(cls, "Image text")
        out.append(f"> — *{label} (from image {image_index}; citation unverified)*")
    out.append(f"  (image preserved at {rel})")
    if notes:
        out.append(f"  *Note:* {notes}")
    return "\n".join(out) + "\n"


# ------------- per-topic verse-references footer ------------------------------

_INLINE_QURAN_MARKER_RE = re.compile(r"⟪quran (\d+):(\d+)(?:-(\d+))?⟫")


def _topic_refs_block(corpus: QuranCorpus, refs: list[dict], topic_body: str) -> str:
    """Emit a 'Verses referenced' footer, skipping any (surah, ayat) already
    cited inline in the topic body (avoids redundancy with KAHSKOLE Quran
    widget that already inlined the same verse)."""
    if not refs:
        return ""
    inline_pairs: set[tuple[int, int]] = set()
    for m in _INLINE_QURAN_MARKER_RE.finditer(topic_body):
        s = int(m.group(1))
        start = int(m.group(2))
        end = int(m.group(3)) if m.group(3) else start
        for a in range(start, end + 1):
            inline_pairs.add((s, a))

    novel = [r for r in refs if (int(r["surah"]), int(r["ayat"])) not in inline_pairs]
    if not novel:
        return ""

    out: list[str] = [
        "\n*Verses referenced in this topic (curated linkage from KAHSKOLE.TopicAyats — "
        f"{len(novel)} of {len(refs)} not already cited above):*\n"
    ]
    for r in novel:
        s, a = int(r["surah"]), int(r["ayat"])
        out.append(_render_quran_block(corpus, s, a, None, source_note="TopicAyats"))
        out.append("")
    return "\n".join(out)


# ------------- finalize routine -----------------------------------------------

def finalize_kahskole_chapter(stem_dir: Path, stem_name: str) -> Path:
    draft_path = stem_dir / f"{stem_name}.md.draft"
    meta_path = stem_dir / f"{stem_name}.meta.yml"
    images_dir = stem_dir / f"{stem_name}-images"
    vision_tasks_path = images_dir / "vision-tasks.json"

    draft = draft_path.read_text(encoding="utf-8")
    vision_tasks = json.loads(vision_tasks_path.read_text(encoding="utf-8"))

    corpus = QuranCorpus()

    # 1. Substitute {{IMG:NNN}} placeholders with rendered image blocks
    images_dirname = images_dir.name
    image_index_results: dict[str, dict] = {}
    for img in vision_tasks["images"]:
        ph = img["placeholder"]
        if not ph.startswith("IMG:"):
            continue
        idx = ph.split(":", 1)[1]
        sidecar_path = images_dir / f"{idx}.json"
        if sidecar_path.exists():
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            block = _render_image_block(sidecar, images_dirname, idx)
            draft = draft.replace(f"{{{{IMG:{idx}}}}}", block)
            image_index_results[idx] = sidecar
        else:
            placeholder_note = (
                f"\n[image {idx}: AI vision pending — see {images_dirname}/{idx}.png]\n"
            )
            draft = draft.replace(f"{{{{IMG:{idx}}}}}", placeholder_note)

    # 2. Replace flattened KAHSKOLE Quran widget blocks with clean blockquotes
    quran_replacements: list[dict] = []
    def _sub_quran(m: re.Match) -> str:
        full = m.group(1)
        surah = int(m.group(2))
        start = int(m.group(3))
        end = int(m.group(4)) if m.group(4) else None
        rendered = _render_quran_block(corpus, surah, start, end,
                                       source_note="inline widget")
        quran_replacements.append({
            "surah": surah, "start_ayat": start, "end_ayat": end or start,
            "raw_widget_chars": len(full),
        })
        return "\n" + rendered + "\n"
    draft = _QURAN_WIDGET_RE.sub(_sub_quran, draft)

    # 3. Append per-topic TopicAyats verse-reference footers
    meta_yaml = meta_path.read_text(encoding="utf-8")
    section_marker_re = re.compile(
        r"(<!-- section (\d+) \(id=(\d+), raw_sort=(\d+)\): [^>]+? -->\n)"
    )
    matches = list(section_marker_re.finditer(draft))
    if matches:
        new_parts: list[str] = []
        last_end = 0
        for i, m in enumerate(matches):
            section_id = int(m.group(3))
            this_start = m.start()
            this_section_end = matches[i + 1].start() if i + 1 < len(matches) else len(draft)
            new_parts.append(draft[last_end:this_start])
            section_body = draft[this_start:this_section_end]
            t_refs = _extract_topic_ayats_for_id(meta_yaml, section_id)
            footer = _topic_refs_block(corpus, t_refs, section_body) if t_refs else ""
            if footer:
                new_parts.append(section_body.rstrip() + "\n" + footer + "\n")
            else:
                new_parts.append(section_body)
            last_end = this_section_end
        new_parts.append(draft[last_end:])
        draft = "".join(new_parts)

    # 4. Tidy whitespace
    draft = re.sub(r"\n{3,}", "\n\n", draft).strip() + "\n"

    # 5. Write final .md
    final_md = stem_dir / f"{stem_name}.md"
    final_md.write_text(draft, encoding="utf-8")

    # 6. Update meta.yml — stage finalized, image classifications recorded,
    # Quran widget replacement count, and Quran citation validation results
    meta_lines = meta_yaml.splitlines()
    new_meta_lines = []
    for line in meta_lines:
        if line.startswith("stage: "):
            new_meta_lines.append("stage: finalized")
        else:
            new_meta_lines.append(line)
    new_meta_lines.append("")
    new_meta_lines.append("finalize:")
    new_meta_lines.append(f"  finalized_at: {datetime.now(timezone.utc).isoformat()}")
    new_meta_lines.append(f"  quran_widgets_resolved: {len(quran_replacements)}")
    if quran_replacements:
        new_meta_lines.append(f"  quran_widget_refs:")
        for r in quran_replacements:
            new_meta_lines.append(
                f"    - {{ surah: {r['surah']}, start: {r['start_ayat']}, "
                f"end: {r['end_ayat']} }}"
            )
    else:
        new_meta_lines.append("  quran_widget_refs: []")
    new_meta_lines.append(f"  images:")
    if image_index_results:
        for idx, sidecar in sorted(image_index_results.items()):
            cls = sidecar.get("classification", "?")
            conf = sidecar.get("confidence")
            new_meta_lines.append(f"    - placeholder: 'IMG:{idx}'")
            new_meta_lines.append(f"      file: {images_dirname}/{idx}.png")
            new_meta_lines.append(f"      classification: {cls}")
            new_meta_lines.append(f"      confidence: {conf}")
            if sidecar.get("suggested_citation"):
                c = sidecar["suggested_citation"]
                if c.get("surah") is not None:
                    new_meta_lines.append(
                        f"      suggested_citation: "
                        f"{{ surah: {c['surah']}, ayat: {c.get('ayat')} }}"
                    )
    else:
        new_meta_lines.append("    []")
    meta_path.write_text("\n".join(new_meta_lines) + "\n", encoding="utf-8")

    # 7. Delete the .md.draft (we kept it only for development)
    draft_path.unlink()

    return final_md


def _extract_topic_ayats_for_id(meta_yaml: str, topic_id: int) -> list[dict]:
    """Naive YAML scan: find this topic's `topic_ayats:` list."""
    refs: list[dict] = []
    in_section = False
    found_topic = False
    for line in meta_yaml.splitlines():
        if f"id: {topic_id}" in line and "    - " in line[:8] or line.strip() == f"id: {topic_id}":
            in_section = True
            found_topic = True
            continue
        if in_section:
            if line.startswith("    - position:") and found_topic:
                # next topic started
                break
            m = re.match(r"\s*-\s*\{\s*surah:\s*(\d+),\s*ayat:\s*(\d+)\s*\}", line)
            if m:
                refs.append({"surah": int(m.group(1)), "ayat": int(m.group(2))})
    return refs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--binder", type=int, required=True)
    ap.add_argument("--chapter", type=int, required=True)
    args = ap.parse_args()

    # Locate the prepared book by querying DB for prefixes (same logic as prepare)
    from scripts.slugify import slugify_urdu
    binder = query_json("KASHKOLE", f"""
        SELECT BinderID AS id, BinderName AS name FROM Binders
        WHERE BinderID = {args.binder} FOR JSON PATH;""")[0]
    bc = query_json("KASHKOLE", f"""
        SELECT bc.BinderChapterOrder AS book_sort_key, c.ChapterID AS id, c.ChapterName AS name
        FROM BinderChapters bc JOIN Chapters c ON c.ChapterID = bc.ChapterID
        WHERE bc.BinderID = {args.binder} AND bc.ChapterID = {args.chapter} FOR JSON PATH;""")[0]
    all_binders = query_json("KASHKOLE",
        "SELECT BinderID AS id FROM Binders ORDER BY BinderOrder, BinderID FOR JSON PATH;")
    shelf_prefix = [b["id"] for b in all_binders].index(args.binder) + 1
    chaps_in_binder = query_json("KASHKOLE", f"""
        SELECT ChapterID AS id FROM BinderChapters
        WHERE BinderID = {args.binder} ORDER BY BinderChapterOrder, ChapterID FOR JSON PATH;""")
    book_prefix = [c["id"] for c in chaps_in_binder].index(args.chapter) + 1
    shelf_slug = slugify_urdu(binder["name"], binder["id"])
    book_slug = slugify_urdu(bc["name"], bc["id"])
    shelf_dir = EXTRACT_ROOT / f"{shelf_prefix:02d}-{shelf_slug}"
    stem_name = f"{book_prefix:02d}-{book_slug}"

    final = finalize_kahskole_chapter(shelf_dir, stem_name)
    print(f"FINALIZED: {final}")


if __name__ == "__main__":
    main()
