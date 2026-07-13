"""book/visuals/index.json — the candidate asset library (v2 producer side).

Under ``book_pipeline_v2`` the illustrate + slide-import producers STOP injecting
figures into book.md. Instead they emit every generated visual as a *candidate*
into ``book/visuals/`` and register it in ``book/visuals/index.json``. The human
then curates placement in the Astro Book Composer (Phase 4), which writes
``book/visual-layout.json`` (consumed by the renderer, Phase 2). book.md stays
diagram-free.

Index schema ``book.visuals-index/v1``: ``{schema, visuals: [ {id, type, aspect,
caption, file, suggested_anchor, cleaned, embedded_title} ]}``. ``file`` is the
basename inside ``book/visuals/``. ``embedded_title`` lets the renderer suppress a
duplicated caption when a slide already bakes its title into the image.

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
    except Exception:  # noqa: BLE001
        return []


def write_index(book_dir: Path, visuals: list[dict[str, Any]]) -> Path:
    p = index_path(book_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps({"schema": VISUALS_SCHEMA, "visuals": visuals}, indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    return p


def merge_entries(book_dir: Path, new_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Idempotently merge entries by id, preserving prior order for stable diffs."""
    existing = {e.get("id"): e for e in load_index(book_dir)}
    order = [e.get("id") for e in load_index(book_dir)]
    for e in new_entries:
        if e.get("id") not in existing:
            order.append(e.get("id"))
        existing[e.get("id")] = e
    merged = [existing[i] for i in order if i in existing]
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
        from PIL import Image  # noqa: PLC0415

        with Image.open(src) as im:
            w, h = im.size
            band = int(h * _WATERMARK_BAND_FRAC)
            if band <= 0 or band >= h:
                im.save(dst)
                return False
            im.crop((0, 0, w, h - band)).save(dst)
            return True
    except Exception:  # noqa: BLE001 — Pillow absent or image unreadable
        try:
            shutil.copy2(src, dst)
        except Exception:  # noqa: BLE001
            return False
        return False


def emit_diagram_candidates(
    book_dir: Path, manifest: list[dict[str, Any]], *, log=print
) -> list[dict[str, Any]]:
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
        except Exception as exc:  # noqa: BLE001
            log(f"      visuals: copy failed for {svg_src.name}: {exc}")
            continue
        entries.append({
            "id": vid,
            "type": str(e.get("structure_type") or e.get("diagram_type") or "diagram"),
            "aspect": "",
            "caption": str(e.get("caption") or ""),
            "file": fname,
            "suggested_anchor": str(e.get("section") or e.get("anchor_text") or ""),
            "cleaned": True,
            "embedded_title": "",
        })
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
        out.append({
            "id": vid,
            "type": vtype,
            "aspect": "",
            "caption": title,
            "file": fname,
            "suggested_anchor": anchor,
            "cleaned": cleaned,
            "embedded_title": title,  # slides bake the title in -> caption de-dup
        })
    log(f"      visuals: registered {len(out)} slide candidate(s)")
    return out
