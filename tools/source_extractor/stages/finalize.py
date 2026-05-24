"""Stage C — substitute {{IMG:NNN}} placeholders, run adapter inline-citation
cleanup, append per-section curated-citation footers, produce the final
raw-extract.md (no .draft suffix).

Generic: works against any SourceAdapter. The adapter supplies the optional
Quran corpus, inline-citation cleanup, and curated-citation footer rendering.

Stage B (in-conversation Claude vision) happens between prepare and finalize.
It writes per-image JSON sidecars at _system/source/images/NNN.json which this
stage substitutes into the draft.
"""
from __future__ import annotations
import json, re
from pathlib import Path

from ..adapters.base import SourceAdapter, BookIds
from ..bundle import (
    bundle_paths,
    update_bundle_yml_stage,
    update_provenance_finalize,
)


# Image refs in raw-extract.md are relative to text/, which sits next to
# images/ under _system/source/. So images live at "../images/NNN.png".
_IMG_REL_PREFIX = "../images"


def _render_image_block(sidecar: dict, image_index: str) -> str:
    cls = sidecar.get("classification", "other")
    alt = (sidecar.get("alt_text") or "").strip()
    arabic = (sidecar.get("arabic_text") or "").strip()
    urdu = (sidecar.get("urdu_text") or "").strip()
    english = (sidecar.get("english_text") or "").strip()
    notes = (sidecar.get("notes") or "").strip()
    citation = sidecar.get("suggested_citation")

    rel = f"{_IMG_REL_PREFIX}/{image_index}.png"

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
            f"*(from image; see _provenance.json for validation)*"
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
    """Stage C entry point. Returns the final raw-extract.md path."""
    meta = adapter.resolve_book(ids)
    paths = bundle_paths(extract_root, meta)

    draft = paths.raw_extract_draft.read_text(encoding="utf-8")
    vision_tasks = json.loads(paths.vision_tasks.read_text(encoding="utf-8"))

    corpus = adapter.get_quran_corpus()

    # 1. Substitute {{IMG:NNN}} placeholders with rendered image blocks
    image_index_results: dict[str, dict] = {}
    for img in vision_tasks["images"]:
        ph = img["placeholder"]
        if not ph.startswith("IMG:"):
            continue
        idx = ph.split(":", 1)[1]
        sidecar_path = paths.images_dir / f"{idx}.json"
        if sidecar_path.exists():
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            block = _render_image_block(sidecar, idx)
            draft = draft.replace(f"{{{{IMG:{idx}}}}}", block)
            image_index_results[idx] = sidecar
        else:
            placeholder_note = (
                f"\n[image {idx}: AI vision pending — "
                f"see {_IMG_REL_PREFIX}/{idx}.png]\n"
            )
            draft = draft.replace(f"{{{{IMG:{idx}}}}}", placeholder_note)

    # 2. Adapter-specific inline citation cleanup
    draft, citation_replacements = adapter.cleanup_inline_citations(draft, corpus)

    # 3. Per-section curated-citation footers
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

    # 4. Tidy whitespace, write final raw-extract.md
    draft = re.sub(r"\n{3,}", "\n\n", draft).strip() + "\n"
    paths.raw_extract_final.write_text(draft, encoding="utf-8")

    # 5. Update bundle.yml: stage -> finalized, append finalize block
    finalize_block = {
        "inline_citations_resolved": len(citation_replacements),
        "inline_citation_refs": [
            {
                "surah": r["surah"],
                "start": r["start_ayat"],
                "end": r["end_ayat"],
            }
            for r in citation_replacements
        ],
        "images": [
            {
                "placeholder": f"IMG:{idx}",
                "classification": sc.get("classification", "?"),
                "confidence": sc.get("confidence"),
            }
            for idx, sc in sorted(image_index_results.items())
        ],
    }
    update_bundle_yml_stage(paths, "finalized", finalize_block)

    # 6. Update _provenance.json
    update_provenance_finalize(
        paths,
        image_classifications={
            idx: sc.get("classification", "?")
            for idx, sc in image_index_results.items()
        },
        citation_replacements=len(citation_replacements),
    )

    # 7. Delete the .draft (only kept during development)
    paths.raw_extract_draft.unlink()

    return paths.raw_extract_final
