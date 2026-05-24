"""Stage A — adapter → BOOK_DIR bundle.

Generic: works against any SourceAdapter. Output is a podcast-pipeline-ready
bundle (see bundle.py for the layout contract). Stage B (in-conversation
Claude vision) runs between prepare and finalize.
"""
from __future__ import annotations
import base64, hashlib, json, re
from datetime import datetime, timezone
from pathlib import Path

from ..adapters.base import SourceAdapter, BookIds
from ..html_to_md import html_to_md
from ..bundle import (
    bundle_paths,
    ensure_bundle_dirs,
    write_bundle_yml,
    write_provenance,
    write_readme,
    write_audit_anchor_html,
    write_extraction_notes,
)


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
            "file": f"_system/source/images/{fname}",
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
    """Stage A entry point. Returns the bundle root directory."""
    meta = adapter.resolve_book(ids)
    sections = adapter.get_book_sections(ids)
    labels = adapter.labels

    paths = bundle_paths(extract_root, meta)
    ensure_bundle_dirs(paths)

    # Audit anchor: concatenated raw HTML (provenance, never modified)
    write_audit_anchor_html(paths, meta, labels, sections)

    # Walk sections: extract images, build draft markdown
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
        f"{len(sections)} {labels.section_label}s. "
        f"Language: {meta.source_language}.*\n"
    )

    for section in sections:
        imgs_before = image_counter[0]
        if section.html:
            html_with_placeholders = _extract_inline_images(
                section.html,
                image_counter,
                paths.images_dir,
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
            "curated_citations": curated_refs,
        })

        md_lines.append(
            f"\n<!-- section {section.position} "
            f"(id={section.id}, raw_sort={section.raw_sort}): {section.label} -->\n"
        )
        if md_body.strip():
            md_lines.append(md_body)
        else:
            md_lines.append(f"\n*(no Unicode content — see _extraction-notes.md)*\n")

    paths.raw_extract_draft.write_text("".join(md_lines), encoding="utf-8")

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
            "For each image in `images`, read the file via the Read tool "
            "(paths are relative to the bundle root) and write a sibling "
            "JSON file next to the PNG (same basename, .json extension) "
            "with the schema: {classification, arabic_text, urdu_text, "
            "english_text, suggested_citation: {surah, ayat} | null, "
            "alt_text, confidence, notes}. classification ∈ "
            "{quran-verse, hadith, poem-or-saying, teaching-diagram, mixed, other}. "
            "For quran-verse, propose surah+ayat from your reading; finalize "
            "validates against the adapter's Quran corpus. For teaching-diagram, "
            "give a 1-2 sentence alt_text describing what it shows."
        ),
    }
    paths.vision_tasks.write_text(
        json.dumps(vision_tasks, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # _extraction-notes.md
    write_extraction_notes(paths, meta, extraction_notes)

    # _provenance.json
    write_provenance(
        paths, meta, labels,
        db_name="KASHKOLE" if meta.source_name == "kashkole" else meta.source_name.upper(),
        section_query_count=len(sections),
        stage="prepared",
    )

    # bundle.yml + _README.md (root-level)
    write_bundle_yml(paths, meta, labels, sections_meta, len(image_records),
                     stage="prepared")
    write_readme(
        paths, meta, labels,
        section_count=len(sections),
        sections_with_content=sum(1 for s in sections_meta if s["has_content"]),
        image_count=len(image_records),
    )

    return paths.root
