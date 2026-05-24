"""Stage C — substitute {{IMG:NNN}} placeholders, run adapter inline-citation
cleanup, append per-section curated-citation footers, produce the final .md.

Generic: works against any SourceAdapter. The adapter supplies the (optional)
Quran corpus, inline-citation cleanup logic, and curated-citation footer
rendering.

Stage B (in-conversation Claude vision) happens between prepare and finalize.
It writes per-image JSON sidecars at images_dir/NNN.json which this stage
substitutes into the draft.
"""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path

from ..adapters.base import SourceAdapter, BookIds


def _render_image_block(sidecar: dict, images_dirname: str, image_index: str) -> str:
    cls = sidecar.get("classification", "other")
    alt = (sidecar.get("alt_text") or "").strip()
    arabic = (sidecar.get("arabic_text") or "").strip()
    urdu = (sidecar.get("urdu_text") or "").strip()
    english = (sidecar.get("english_text") or "").strip()
    notes = (sidecar.get("notes") or "").strip()
    citation = sidecar.get("suggested_citation")

    rel = f"{images_dirname}/{image_index}.png"

    if cls == "teaching-diagram":
        parts = [
            f"\n[diagram: {alt}]" if alt
            else f"\n[diagram from image {image_index}]"
        ]
        parts.append(f"  (see {rel})")
        if arabic:
            arabic_inline = " · ".join(
                line.strip() for line in arabic.splitlines() if line.strip()
            )
            parts.append(f"  *Arabic labels in image:* ⟪ar:{arabic_inline}⟫")
        if notes:
            parts.append(f"  *Note:* {notes}")
        return "\n".join(parts) + "\n"

    out = [""]
    if arabic:
        out.append(f"> ⟪ar:{arabic.strip()}⟫")
    if english:
        out.append(f"> *{english.strip()}*")
    if urdu:
        out.append(f"> {urdu.strip()}")
    if citation and isinstance(citation, dict) and citation.get("surah"):
        s, a = citation["surah"], citation.get("ayat")
        out.append(
            f"> — **Quran {s}:{a}** "
            f"*(from image; see meta.yml for validation)*"
        )
    else:
        label = {
            "hadith": "Hadith",
            "poem-or-saying": "Poem / saying",
            "mixed": "Image text",
            "other": "Image text",
        }.get(cls, "Image text")
        out.append(
            f"> — *{label} (from image {image_index}; citation unverified)*"
        )
    out.append(f"  (image preserved at {rel})")
    if notes:
        out.append(f"  *Note:* {notes}")
    return "\n".join(out) + "\n"


_SECTION_MARKER_RE = re.compile(
    r"(<!-- section (\d+) \(id=(\d+), raw_sort=(\d+)\): [^>]+? -->\n)"
)


def finalize_book(
    adapter: SourceAdapter,
    ids: BookIds,
    extract_root: Path,
) -> Path:
    """Stage C entry point. Returns the final .md path."""
    meta = adapter.resolve_book(ids)

    shelf_dir = (
        extract_root / meta.source_name
        / f"{meta.shelf_prefix:02d}-{meta.shelf_slug}"
    )
    book_stem = f"{meta.book_prefix:02d}-{meta.book_slug}"

    draft_path = shelf_dir / f"{book_stem}.md.draft"
    meta_path = shelf_dir / f"{book_stem}.meta.yml"
    images_dir = shelf_dir / f"{book_stem}-images"
    vision_tasks_path = images_dir / "vision-tasks.json"

    draft = draft_path.read_text(encoding="utf-8")
    vision_tasks = json.loads(vision_tasks_path.read_text(encoding="utf-8"))

    corpus = adapter.get_quran_corpus()

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
                f"\n[image {idx}: AI vision pending — "
                f"see {images_dirname}/{idx}.png]\n"
            )
            draft = draft.replace(f"{{{{IMG:{idx}}}}}", placeholder_note)

    # 2. Adapter-specific inline citation cleanup (e.g., KAHSKOLE Quran widgets)
    draft, citation_replacements = adapter.cleanup_inline_citations(draft, corpus)

    # 3. Per-section curated-citation footer (e.g., KAHSKOLE TopicAyats)
    matches = list(_SECTION_MARKER_RE.finditer(draft))
    if matches:
        new_parts: list[str] = []
        last_end = 0
        for i, m in enumerate(matches):
            section_id = int(m.group(3))
            this_start = m.start()
            this_section_end = (
                matches[i + 1].start() if i + 1 < len(matches) else len(draft)
            )
            new_parts.append(draft[last_end:this_start])
            section_body = draft[this_start:this_section_end]

            curated_refs = adapter.get_section_curated_citations(section_id)
            footer = (
                adapter.render_curated_citation_footer(
                    section_body, curated_refs, corpus
                )
                if curated_refs else ""
            )
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
    final_md = shelf_dir / f"{book_stem}.md"
    final_md.write_text(draft, encoding="utf-8")

    # 6. Update meta.yml
    meta_yaml = meta_path.read_text(encoding="utf-8")
    meta_lines = meta_yaml.splitlines()
    new_meta_lines = []
    for line in meta_lines:
        if line.startswith("stage: "):
            new_meta_lines.append("stage: finalized")
        else:
            new_meta_lines.append(line)
    new_meta_lines.append("")
    new_meta_lines.append("finalize:")
    new_meta_lines.append(
        f"  finalized_at: {datetime.now(timezone.utc).isoformat()}"
    )
    new_meta_lines.append(
        f"  quran_widgets_resolved: {len(citation_replacements)}"
    )
    if citation_replacements:
        new_meta_lines.append(f"  quran_widget_refs:")
        for r in citation_replacements:
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

    # 7. Delete the .md.draft (only kept it for development)
    draft_path.unlink()

    return final_md
