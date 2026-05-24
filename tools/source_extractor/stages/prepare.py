"""Stage A — adapter → draft markdown + extracted PNG images + vision-tasks.json.

Generic: works against any SourceAdapter. The adapter supplies schema-specific
section retrieval + slugs; this stage handles the filesystem mechanics, inline
base64 image decoding, and metadata emission.

Output layout (preserved from Phase 1 for now — BOOK_DIR shape comes in Phase B):

  <extract_root>/<source_name>/<NN-shelf-slug>/
    <MM-book-slug>.md.draft       ← markdown with {{IMG:NNN}} placeholders
    <MM-book-slug>.meta.yml       ← shelf/book/sections metadata + curated citations
    <MM-book-slug>-images/
      001.png                      ← decoded image bytes (inline base64)
      002.png
      ...
      vision-tasks.json            ← list of images awaiting in-conversation vision
"""
from __future__ import annotations
import base64, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path

from ..adapters.base import SourceAdapter, BookIds
from ..html_to_md import html_to_md
from ..yaml_lite import yaml_str


_INLINE_IMG_RE = re.compile(
    r'<img[^>]*src="data:image/(?P<fmt>png|jpeg|jpg|gif|webp);base64,(?P<b64>[^"]+)"[^>]*>',
    re.IGNORECASE,
)


def _extract_inline_images(
    html: str,
    image_counter: list[int],
    images_dir: Path,
    image_records: list[dict],
    section_id: int,
    section_label: str,
) -> str:
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
                "placeholder": f"IMG_DECODE_FAIL_T{section_id}",
                "section_id": section_id,
                "section_label": section_label,
                "error": f"base64 decode failed: {e}",
            })
            return f"\n[IMG_DECODE_FAIL T{section_id}]\n"
        image_counter[0] += 1
        idx = image_counter[0]
        fname = f"{idx:03d}.{fmt}"
        (images_dir / fname).write_bytes(data)
        sha = hashlib.sha256(data).hexdigest()[:12]
        image_records.append({
            "placeholder": f"IMG:{idx:03d}",
            "file": f"{images_dir.name}/{fname}",
            "section_id": section_id,
            "section_label": section_label,
            "bytes": len(data),
            "sha256_12": sha,
            "source": "section html (inline base64)",
            "status": "awaiting-vision",
        })
        return f"\n{{{{IMG:{idx:03d}}}}}\n"

    return _INLINE_IMG_RE.sub(_sub, html)


def prepare_book(
    adapter: SourceAdapter,
    ids: BookIds,
    extract_root: Path,
) -> Path:
    """Stage A entry point. Returns the book stem path
    (e.g. <extract_root>/<source>/<NN-shelf>/<MM-book>) without extension."""
    meta = adapter.resolve_book(ids)
    sections = adapter.get_book_sections(ids)
    labels = adapter.labels

    shelf_dir = (
        extract_root / meta.source_name
        / f"{meta.shelf_prefix:02d}-{meta.shelf_slug}"
    )
    shelf_dir.mkdir(parents=True, exist_ok=True)

    book_stem = f"{meta.book_prefix:02d}-{meta.book_slug}"
    md_draft_path = shelf_dir / f"{book_stem}.md.draft"
    meta_path = shelf_dir / f"{book_stem}.meta.yml"
    images_dir = shelf_dir / f"{book_stem}-images"
    images_dir.mkdir(exist_ok=True)

    image_counter = [0]
    image_records: list[dict] = []
    sections_meta: list[dict] = []
    extraction_notes: list[str] = []

    md_lines: list[str] = []
    md_lines.append(f"# {meta.book_name}\n")
    md_lines.append(
        f"*Source: {meta.source_name.upper()}, {labels.shelf_label.capitalize()} "
        f"{meta.shelf_id} ({meta.shelf_name}), "
        f"{labels.book_label.capitalize()} {meta.book_id}. "
        f"{len(sections)} {labels.section_label}s.*\n"
    )

    for section in sections:
        imgs_before = image_counter[0]
        if section.html:
            html_with_placeholders = _extract_inline_images(
                section.html,
                image_counter,
                images_dir,
                image_records,
                section.id,
                section.label,
            )
            md_body = html_to_md(html_with_placeholders)
        else:
            md_body = ""
            extraction_notes.append(
                f"{labels.section_label.capitalize()} T{section.id} "
                f"({section.label}) at order {section.raw_sort} has no "
                f"Unicode content (image-only or empty). Section emitted empty."
            )

        imgs_after = image_counter[0]
        imgs_here = imgs_after - imgs_before

        curated_refs = adapter.get_section_curated_citations(section.id)

        sections_meta.append({
            "position": section.position,
            "id": section.id,
            "raw_sort": section.raw_sort,
            "label": section.label,
            "name_en": section.extras.get("name_en"),
            "has_content": bool(section.html),
            "image_count_inline": imgs_here,
            "topic_ayats": curated_refs,
        })

        md_lines.append(
            f"\n<!-- section {section.position} "
            f"(id={section.id}, raw_sort={section.raw_sort}): {section.label} -->\n"
        )
        if md_body.strip():
            md_lines.append(md_body)
        else:
            md_lines.append(f"\n*(no Unicode content — see meta.yml)*\n")

    md_draft_path.write_text("".join(md_lines), encoding="utf-8")

    # vision-tasks.json
    vision_tasks = {
        "book": {
            f"{labels.shelf_label}_id": meta.shelf_id,
            f"{labels.shelf_label}_name": meta.shelf_name,
            f"{labels.book_label}_id": meta.book_id,
            f"{labels.book_label}_name": meta.book_name,
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
            "For quran-verse, propose surah+ayat from your reading; finalize "
            "validates against the adapter's Quran corpus. For teaching-diagram, "
            "give a 1-2 sentence alt_text describing what it shows."
        ),
    }
    (images_dir / "vision-tasks.json").write_text(
        json.dumps(vision_tasks, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # meta.yml
    yaml_lines = [
        f"# generated by tools/source_extractor at "
        f"{datetime.now(timezone.utc).isoformat()}",
        f"source: {meta.source_name}",
        f"source_language: {meta.source_language}",
        f"stage: prepared",
        f"shelf:",
        f"  kind: {labels.shelf_label}",
        f"  id: {meta.shelf_id}",
        f"  name: {yaml_str(meta.shelf_name)}",
        f"  sort_key: {meta.shelf_sort_key}",
        f"  slug: {meta.shelf_slug}",
        f"  prefix: {meta.shelf_prefix:02d}",
        f"book:",
        f"  kind: {labels.book_label}",
        f"  id: {meta.book_id}",
        f"  name: {yaml_str(meta.book_name)}",
        f"  sort_key: {meta.book_sort_key}",
        f"  slug: {meta.book_slug}",
        f"  prefix: {meta.book_prefix:02d}",
        f"counts:",
        f"  sections: {len(sections)}",
        f"  sections_with_content: "
        f"{sum(1 for s in sections_meta if s['has_content'])}",
        f"  inline_images: {len(image_records)}",
        f"  curated_citation_refs: "
        f"{sum(len(s['topic_ayats']) for s in sections_meta)}",
        f"sections:",
        f"  kind: {labels.section_label}",
        f"  items:",
    ]
    for s in sections_meta:
        yaml_lines.append(f"    - position: {s['position']}")
        yaml_lines.append(f"      id: {s['id']}")
        yaml_lines.append(f"      raw_sort: {s['raw_sort']}")
        yaml_lines.append(f"      label: {yaml_str(s['label'])}")
        if s.get("name_en"):
            yaml_lines.append(f"      name_en: {yaml_str(s['name_en'])}")
        yaml_lines.append(f"      has_content: {str(s['has_content']).lower()}")
        yaml_lines.append(f"      image_count_inline: {s['image_count_inline']}")
        if s["topic_ayats"]:
            yaml_lines.append(f"      topic_ayats:")
            for a in s["topic_ayats"]:
                yaml_lines.append(
                    f"        - {{ surah: {a['surah']}, ayat: {a['ayat']} }}"
                )
        else:
            yaml_lines.append(f"      topic_ayats: []")
    if extraction_notes:
        yaml_lines.append("extraction_notes:")
        for n in extraction_notes:
            yaml_lines.append(f"  - {yaml_str(n)}")
    else:
        yaml_lines.append("extraction_notes: []")

    meta_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    return shelf_dir / book_stem
