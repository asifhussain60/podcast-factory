"""
Stage A — DB → text + saved images + vision tasks.

For KAHSKOLE only. Emits:
  extracted/kashkole/<NN-binder-slug>/
    <NN-chapter-slug>.md.draft       ← clean Urdu MD with {{IMG:NNN}} placeholders
    <NN-chapter-slug>.meta.yml       ← shelf info + section list + image manifest
    <NN-chapter-slug>-images/
      001.png                         ← decoded image bytes (inline base64)
      002.png
      ...
      vision-tasks.json               ← list of images needing AI processing,
                                         with placement context for each

After running this, the next stage (Claude Code in-conversation) reads each
PNG via the Read tool and writes a sibling NNN.json with OCR + classification
+ citation suggestions. Then finalize.py composes the final .md.
"""
from __future__ import annotations
import argparse, base64, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path

from scripts.db import query_json
from scripts.html_to_md import html_to_md
from scripts.slugify import slugify_urdu


REPO_ROOT = Path(__file__).resolve().parents[3]
EXTRACT_ROOT = REPO_ROOT / "_workspace" / "kashkole-ksessions" / "extracted" / "kashkole"

_INLINE_IMG_RE = re.compile(
    r'<img[^>]*src="data:image/(?P<fmt>png|jpeg|jpg|gif|webp);base64,(?P<b64>[^"]+)"[^>]*>',
    re.IGNORECASE,
)


def _yaml_str(s: str) -> str:
    if s is None or s == "":
        return "''"
    if any(c in s for c in ":#\"'\n[]{},&*!|>%@`"):
        return json.dumps(s, ensure_ascii=False)
    return s


def _extract_inline_images(html: str, image_counter: list[int], images_dir: Path,
                           image_records: list[dict], topic_id: int, topic_label: str) -> str:
    """Replace each <img src='data:image/...'> with a {{IMG:NNN}} placeholder
    and dump the decoded bytes to images_dir/NNN.<fmt>. Returns rewritten HTML.
    image_counter is a single-element list so we can mutate the running counter."""
    def _sub(m: re.Match) -> str:
        fmt = m.group("fmt").lower()
        if fmt == "jpeg":
            fmt = "jpg"
        b64 = m.group("b64").strip()
        try:
            data = base64.b64decode(b64, validate=False)
        except Exception as e:
            image_records.append({
                "placeholder": f"IMG_DECODE_FAIL_T{topic_id}",
                "topic_id": topic_id,
                "topic_label": topic_label,
                "error": f"base64 decode failed: {e}",
            })
            return f"\n[IMG_DECODE_FAIL T{topic_id}]\n"
        image_counter[0] += 1
        idx = image_counter[0]
        fname = f"{idx:03d}.{fmt}"
        (images_dir / fname).write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()[:12]
        image_records.append({
            "placeholder": f"IMG:{idx:03d}",
            "file": f"{images_dir.name}/{fname}",
            "topic_id": topic_id,
            "topic_label": topic_label,
            "bytes": len(data),
            "sha256_12": sha,
            "source": "TopicDataUnicode (inline base64)",
            "status": "awaiting-vision",
        })
        return f"\n{{{{IMG:{idx:03d}}}}}\n"

    return _INLINE_IMG_RE.sub(_sub, html)


def prepare_kahskole_chapter(binder_id: int, chapter_id: int) -> Path:
    binder = query_json("KASHKOLE", f"""
        SELECT BinderID AS id, BinderName AS name, BinderOrder AS sort_key
        FROM Binders WHERE BinderID = {binder_id} FOR JSON PATH;""")[0]

    bc = query_json("KASHKOLE", f"""
        SELECT bc.BinderChapterOrder AS book_sort_key, c.ChapterID AS id, c.ChapterName AS name
        FROM BinderChapters bc JOIN Chapters c ON c.ChapterID = bc.ChapterID
        WHERE bc.BinderID = {binder_id} AND bc.ChapterID = {chapter_id} FOR JSON PATH;""")[0]

    topics = query_json("KASHKOLE", f"""
        SELECT ct.ChapterTopicOrder AS raw_sort,
               t.TopicID AS id, t.TopicName AS name, t.TopicNameEnglish AS name_en,
               td.TopicUnicode AS html
        FROM ChapterTopics ct
        JOIN Topics t ON t.TopicID = ct.TopicID
        LEFT JOIN TopicDataUnicode td ON td.TopicID = t.TopicID
        WHERE ct.ChapterID = {chapter_id}
        ORDER BY ct.ChapterTopicOrder
        FOR JSON PATH;""")

    # Pre-curated Quran citations from TopicAyats (the human-curated linkage)
    ayats_in_chapter = query_json("KASHKOLE", f"""
        SELECT ta.TopicID, ta.Surah, ta.Ayat
        FROM TopicAyats ta
        JOIN ChapterTopics ct ON ct.TopicID = ta.TopicID
        WHERE ct.ChapterID = {chapter_id}
        ORDER BY ct.ChapterTopicOrder, ta.Surah, ta.Ayat
        FOR JSON PATH;""")

    topic_ayats: dict[int, list[dict]] = {}
    for r in ayats_in_chapter:
        topic_ayats.setdefault(r["TopicID"], []).append({"surah": r["Surah"], "ayat": r["Ayat"]})

    # Compute shelf + book filesystem prefixes
    all_binders = query_json("KASHKOLE",
        "SELECT BinderID AS id FROM Binders ORDER BY BinderOrder, BinderID FOR JSON PATH;")
    shelf_prefix = [b["id"] for b in all_binders].index(binder_id) + 1

    chaps_in_binder = query_json("KASHKOLE", f"""
        SELECT ChapterID AS id FROM BinderChapters
        WHERE BinderID = {binder_id} ORDER BY BinderChapterOrder, ChapterID FOR JSON PATH;""")
    book_prefix = [c["id"] for c in chaps_in_binder].index(chapter_id) + 1

    shelf_slug = slugify_urdu(binder["name"], binder["id"])
    book_slug = slugify_urdu(bc["name"], bc["id"])

    shelf_dir = EXTRACT_ROOT / f"{shelf_prefix:02d}-{shelf_slug}"
    shelf_dir.mkdir(parents=True, exist_ok=True)

    book_stem = f"{book_prefix:02d}-{book_slug}"
    md_draft_path = shelf_dir / f"{book_stem}.md.draft"
    meta_path = shelf_dir / f"{book_stem}.meta.yml"
    images_dir = shelf_dir / f"{book_stem}-images"
    images_dir.mkdir(exist_ok=True)

    # Walk topics, decode inline images, build draft MD
    image_counter = [0]
    image_records: list[dict] = []
    sections_meta: list[dict] = []
    extraction_notes: list[str] = []

    md_lines: list[str] = []
    md_lines.append(f"# {bc['name']}\n")
    md_lines.append(f"*Source: KAHSKOLE, Binder {binder['id']} ({binder['name']}), "
                    f"Chapter {bc['id']}. {len(topics)} topics.*\n")

    for pos, t in enumerate(topics, 1):
        label = t["name"] or f"Topic {t['id']}"
        topic_imgs_before = image_counter[0]
        html = t.get("html")
        if html:
            html_with_placeholders = _extract_inline_images(
                html, image_counter, images_dir, image_records, t["id"], label,
            )
            md_body = html_to_md(html_with_placeholders)
        else:
            md_body = ""
            extraction_notes.append(
                f"Topic T{t['id']} ({label}) at order {t['raw_sort']} has no "
                f"Unicode content (image-only or empty). Section emitted empty."
            )

        topic_imgs_after = image_counter[0]
        imgs_here = topic_imgs_after - topic_imgs_before

        sections_meta.append({
            "position": pos,
            "id": t["id"],
            "raw_sort": t["raw_sort"],
            "label": label,
            "name_en": t.get("name_en"),
            "has_content": bool(html),
            "image_count_inline": imgs_here,
            "topic_ayats": topic_ayats.get(t["id"], []),
        })

        md_lines.append(f"\n<!-- section {pos} (id={t['id']}, raw_sort={t['raw_sort']}): {label} -->\n")
        if md_body.strip():
            md_lines.append(md_body)
        else:
            md_lines.append(f"\n*(no Unicode content — see meta.yml)*\n")

    md_draft_path.write_text("".join(md_lines), encoding="utf-8")

    # vision-tasks.json — list of images needing AI processing
    vision_tasks = {
        "book": {
            "binder_id": binder["id"],
            "binder_name": binder["name"],
            "chapter_id": bc["id"],
            "chapter_name": bc["name"],
        },
        "images": image_records,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "instructions": (
            "For each image in `images`, read the file via the Read tool and "
            "write a sibling JSON file (same name, .json extension) with the "
            "schema: {classification, arabic_text, urdu_text, english_text, "
            "suggested_citation: {surah, ayat} | null, alt_text, confidence, "
            "notes}. classification ∈ "
            "{quran-verse, hadith, poem-or-saying, teaching-diagram, mixed, other}. "
            "For quran-verse, propose surah+ayat from your reading; finalize.py "
            "validates against HQAyats. For teaching-diagram, give a 1-2 sentence "
            "alt_text describing what it shows."
        ),
    }
    (images_dir / "vision-tasks.json").write_text(
        json.dumps(vision_tasks, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # meta.yml
    yaml_lines = [
        f"# generated by scripts/prepare.py at {datetime.now(timezone.utc).isoformat()}",
        f"source: kashkole",
        f"stage: prepared",
        f"shelf:",
        f"  kind: binder",
        f"  id: {binder['id']}",
        f"  name: {_yaml_str(binder['name'])}",
        f"  sort_key: {binder['sort_key']}",
        f"  slug: {shelf_slug}",
        f"  prefix: {shelf_prefix:02d}",
        f"book:",
        f"  kind: chapter",
        f"  id: {bc['id']}",
        f"  name: {_yaml_str(bc['name'])}",
        f"  sort_key: {bc['book_sort_key']}",
        f"  slug: {book_slug}",
        f"  prefix: {book_prefix:02d}",
        f"counts:",
        f"  topics: {len(topics)}",
        f"  topics_with_content: {sum(1 for s in sections_meta if s['has_content'])}",
        f"  inline_images: {len(image_records)}",
        f"  topic_ayats_refs: {sum(len(s['topic_ayats']) for s in sections_meta)}",
        f"sections:",
        f"  kind: topic",
        f"  items:",
    ]
    for s in sections_meta:
        yaml_lines.append(f"    - position: {s['position']}")
        yaml_lines.append(f"      id: {s['id']}")
        yaml_lines.append(f"      raw_sort: {s['raw_sort']}")
        yaml_lines.append(f"      label: {_yaml_str(s['label'])}")
        if s.get("name_en"):
            yaml_lines.append(f"      name_en: {_yaml_str(s['name_en'])}")
        yaml_lines.append(f"      has_content: {str(s['has_content']).lower()}")
        yaml_lines.append(f"      image_count_inline: {s['image_count_inline']}")
        if s["topic_ayats"]:
            yaml_lines.append(f"      topic_ayats:")
            for a in s["topic_ayats"]:
                yaml_lines.append(f"        - {{ surah: {a['surah']}, ayat: {a['ayat']} }}")
        else:
            yaml_lines.append(f"      topic_ayats: []")
    if extraction_notes:
        yaml_lines.append("extraction_notes:")
        for n in extraction_notes:
            yaml_lines.append(f"  - {_yaml_str(n)}")
    else:
        yaml_lines.append("extraction_notes: []")

    meta_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    return shelf_dir / book_stem


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--binder", type=int, required=True)
    ap.add_argument("--chapter", type=int, required=True)
    args = ap.parse_args()
    stem = prepare_kahskole_chapter(args.binder, args.chapter)
    print(f"PREPARED: {stem}.*")
    print(f"  draft:  {stem}.md.draft")
    print(f"  meta:   {stem}.meta.yml")
    print(f"  images: {stem}-images/")
    tasks_path = Path(f"{stem}-images/vision-tasks.json")
    if tasks_path.exists():
        with tasks_path.open() as f:
            tasks = json.load(f)
        print(f"  vision tasks: {len(tasks['images'])} images awaiting processing")


if __name__ == "__main__":
    main()
