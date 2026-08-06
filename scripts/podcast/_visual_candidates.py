"""book/visuals/index.json — the candidate asset library (v2 producer side).

Under ``book_pipeline_v2`` the illustrate + slide-import producers STOP injecting
figures into book.md. Instead they emit every generated visual as a *candidate*
into ``book/visuals/`` and register it in ``book/visuals/index.json``. The human
then curates placement in the Astro Book Composer (Phase 4), which writes
``book/visual-layout.json`` (consumed by the renderer, Phase 2). book.md stays
diagram-free.

Index schema ``book.visuals-index/v1``: ``{schema, visuals: [ {id, type, aspect,
caption, file, suggested_anchor, chapter, cleaned, embedded_title} ]}``. ``file``
is the basename inside ``book/visuals/``. ``embedded_title`` lets the renderer
suppress a duplicated caption when a slide already bakes its title into the image.

``chapter`` (2026-07-22) is the bare ``##`` heading text of the chapter a
candidate belongs to, resolved HERE at emit time — because only the producer has
every surface in hand. The Composer's palette filters candidates by chapter, and
it used to recover the chapter by searching the candidate's ``suggested_anchor``
needle in book.md alone. Slide-deck anchors quote the deck's own narration
(book-slides.md), not the reading edition, so every book-deck slide failed that
search, fell to "book-wide", and flooded the palette of every chapter. The needle
search now happens once, against the surface the needle was actually authored
from; the Composer just normalizes the stamped heading. Empty = genuinely
book-wide (a cover or closing slide), shown on every chapter by design.

Emission is idempotent (keyed by ``id``): re-running replaces an entry, never
duplicates it.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

VISUALS_SCHEMA = "book.visuals-index/v1"
_WATERMARK_BAND_FRAC = 0.07  # NotebookLM stamps its watermark in the bottom band


def visuals_dir(book_dir: Path) -> Path:
    return Path(book_dir) / "book" / "visuals"


def index_path(book_dir: Path) -> Path:
    return visuals_dir(book_dir) / "index.json"


def load_index(book_dir: Path) -> list[dict[str, Any]]:
    p = index_path(book_dir)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return list(data.get("visuals") or [])
    except Exception:
        return []


def write_index(book_dir: Path, visuals: list[dict[str, Any]]) -> Path:
    p = index_path(book_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"schema": VISUALS_SCHEMA, "visuals": visuals}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return p


def prune_missing(book_dir: Path, visuals: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split entries into (on disk, gone). An index may not claim a file it lacks.

    ``merge_entries`` is additive by id and has no removal, so an asset deleted
    from ``book/visuals/`` leaves its entry behind forever. On
    ``the-master-and-the-disciple`` that is exactly what happened: commit ef97c27
    (2026-07-16, subject "0book-design — book-toc.json") removed fourteen diagram
    SVGs and left all twenty-nine entries pointing at them, so the Composer's
    palette offered twenty-nine broken images, fired twenty-nine 404s per chapter
    load, and showed NONE of the fifteen slides that were actually there.

    The producers write their assets BEFORE they register them (`_render_diagrams`
    then `merge_entries`; slide extraction then `merge_entries`), so reconciling
    against the directory after a merge can never drop an entry that was just
    emitted.

    Scoped to entries that NAME a file. An entry carrying no ``file`` at all is
    left where it is: it is malformed rather than stale, it cannot produce a
    request for a missing asset, and the Composer already refuses it at read time
    (``partitionByAsset``). Pruning it here would widen this function from "the
    index may not claim a file it lacks" into "the index may only hold entries I
    recognise", which is a different and much less safe rule.
    """
    directory = visuals_dir(book_dir)
    try:
        on_disk = {p.name for p in directory.iterdir() if p.is_file()}
    except OSError:
        on_disk = set()

    def stale(v: dict[str, Any]) -> bool:
        named = str(v.get("file") or "").strip()
        return bool(named) and named not in on_disk

    kept = [v for v in visuals if not stale(v)]
    gone = [v for v in visuals if stale(v)]
    return kept, gone


def merge_entries(book_dir: Path, new_entries: list[dict[str, Any]], *, log=None) -> list[dict[str, Any]]:
    """Idempotently merge entries by id, preserving prior order for stable diffs.

    Reconciles against the directory on the way out — see ``prune_missing``. A
    dropped entry is NAMED rather than swept silently: the index is tracked in
    git and the assets sometimes are not, so a drop can mean "this book was
    cloned without its diagrams" as easily as "these were deleted".
    """
    existing = {e.get("id"): e for e in load_index(book_dir)}
    order = [e.get("id") for e in load_index(book_dir)]
    for e in new_entries:
        if e.get("id") not in existing:
            order.append(e.get("id"))
        existing[e.get("id")] = e
    merged = [existing[i] for i in order if i in existing]
    merged, gone = prune_missing(book_dir, merged)
    if gone and log:
        names = ", ".join(str(g.get("file")) for g in gone[:5])
        more = f" (+{len(gone) - 5} more)" if len(gone) > 5 else ""
        log(f"    visuals: dropped {len(gone)} index entry/entries with no file on disk — {names}{more}")
    write_index(book_dir, merged)
    return merged


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "asset"


def clean_slide_watermark(src: Path, dst: Path) -> bool:
    """Crop the NotebookLM watermark band off the bottom of a slide raster.

    Returns True if a real crop happened, False if it fell back to a plain copy
    (Pillow missing / unreadable image). Never raises — a bad image just copies.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image

        with Image.open(src) as im:
            w, h = im.size
            band = int(h * _WATERMARK_BAND_FRAC)
            if band <= 0 or band >= h:
                im.save(dst)
                return False
            im.crop((0, 0, w, h - band)).save(dst)
            return True
    except Exception:
        try:
            shutil.copy2(src, dst)
        except Exception:
            return False
        return False


def _chapter_sections(text: str) -> list[tuple[str, str]]:
    """[(bare_heading, lowercased_body)] for each ``## `` section of a surface."""
    parts = re.split(r"(?m)^##\s+(.+)$", text)
    # parts: [preamble, heading1, body1, heading2, body2, ...]
    return [(parts[i].strip(), parts[i + 1].lower()) for i in range(1, len(parts) - 1, 2)]


def resolve_candidate_chapter(book_dir: Path, anchor: str) -> str:
    """Bare heading of the chapter an anchor points into.

    Two rungs, mirroring the Composer's resolver but run where every surface is
    on disk. First: the anchor IS a chapter heading (illustrate manifests put
    the section name there) — compared through ``_book_edits.anchor_key``, the
    fixture-pinned normalizer, never a re-implementation. Second: the anchor is
    a passage needle (first 60 chars, lowercased) searched through each
    surface's sections — book-slides.md FIRST, because deck manifests author
    their anchors from the narration, then book.md. Returns "" when
    unresolvable, which the Composer treats as book-wide.
    """
    from _book_edits import anchor_key

    needle = (anchor or "").strip().lower()[:60]
    if not needle:
        return ""
    ak = anchor_key(anchor)
    surfaces: list[list[tuple[str, str]]] = []
    for name in ("book-slides.md", "book.md"):
        f = Path(book_dir) / "book" / name
        if f.exists():
            surfaces.append(_chapter_sections(f.read_text(encoding="utf-8")))
    if ak:
        for sections in surfaces:
            for heading, _body in sections:
                if anchor_key(heading) == ak:
                    return heading
    for sections in surfaces:
        for heading, body in sections:
            if needle in body:
                return heading
    return ""


def emit_diagram_candidates(book_dir: Path, manifest: list[dict[str, Any]], *, log=print) -> list[dict[str, Any]]:
    """Copy generated diagram SVGs into book/visuals/ and register them.

    ``manifest`` is the 0book-illustrate manifest (diagram_id/section/caption/
    svg_path/structure_type). Diagrams are already clean (no watermark).
    """
    vdir = visuals_dir(book_dir)
    vdir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for e in manifest:
        svg_src = Path(e.get("svg_path", ""))
        if not svg_src.exists():
            continue
        vid = _safe_name(str(e.get("diagram_id") or svg_src.stem))
        fname = f"{vid}.svg"
        try:
            shutil.copy2(svg_src, vdir / fname)
        except Exception as exc:
            log(f"      visuals: copy failed for {svg_src.name}: {exc}")
            continue
        anchor = str(e.get("section") or e.get("anchor_text") or "")
        entries.append(
            {
                "id": vid,
                "type": str(e.get("structure_type") or e.get("diagram_type") or "diagram"),
                "aspect": "",
                "caption": str(e.get("caption") or ""),
                "file": fname,
                "suggested_anchor": anchor,
                "chapter": str(e.get("chapter") or "") or resolve_candidate_chapter(book_dir, anchor),
                "cleaned": True,
                "embedded_title": "",
            }
        )
    log(f"      visuals: registered {len(entries)} diagram candidate(s)")
    return entries


def emit_slide_candidates(
    book_dir: Path,
    entries: list[dict[str, Any]],
    pages: dict[int, str],
    svg_overrides: dict[int, Path] | None = None,
    *,
    log=print,
) -> list[dict[str, Any]]:
    """Watermark-clean slide rasters (or copy vector replicas) into book/visuals/.

    ``entries`` are slide manifest entries (page/anchor_text/title). ``pages`` maps
    page -> repo-relative raster path. ``svg_overrides`` maps page -> a verified
    vector replica (preferred over the raster; already clean).
    """
    svg_overrides = svg_overrides or {}
    vdir = visuals_dir(book_dir)
    vdir.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    for e in entries:
        page = e.get("page")
        title = str(e.get("title") or "")
        anchor = str(e.get("anchor_text") or "")
        vid = f"slide-{page}"
        if page in svg_overrides and Path(svg_overrides[page]).exists():
            fname = f"{vid}.svg"
            shutil.copy2(svg_overrides[page], vdir / fname)
            cleaned, vtype = True, "slide-vector"
        elif page in pages and (book_dir / pages[page]).exists():
            src = book_dir / pages[page]
            fname = f"{vid}{src.suffix.lower()}"
            cleaned = clean_slide_watermark(src, vdir / fname)
            vtype = "slide"
        else:
            continue
        out.append(
            {
                "id": vid,
                "type": vtype,
                "aspect": "",
                "caption": title,
                "file": fname,
                "suggested_anchor": anchor,
                "chapter": str(e.get("chapter") or "") or resolve_candidate_chapter(book_dir, anchor),
                "cleaned": cleaned,
                "embedded_title": title,  # slides bake the title in -> caption de-dup
            }
        )
    log(f"      visuals: registered {len(out)} slide candidate(s)")
    return out
