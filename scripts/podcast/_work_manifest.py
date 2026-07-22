"""_work_manifest.py — reader/writer for ``work.yml`` (multi-volume work manifest).

A multi-volume **work** is ONE branch + a parent folder
``content/<Bucket>/<work_slug>/`` containing a ``work.yml`` manifest (ordered
volumes + shared-library pointers) and nested ``vol-NN/`` volume dirs, each a
normal book dir the rest of the pipeline already understands. A single book stays
flat with NO manifest — unchanged on disk.

This module is PURE manifest I/O. It owns the ``work.yml`` schema and the
work↔volume slug mapping, and delegates ALL filesystem path resolution to
``_paths.py`` (the single layout seam). It is imported only by the three
consumers that truly need work-level info: intake, the pause-between-volumes
driver (``orchestrate_work.py``), and the dashboard. No pipeline phase reads it.

SCHEMA (``content/<Bucket>/<work_slug>/work.yml`` — parent of a nested work only):

    work_slug: asaas                 # kebab slug; the work's branch + parent dir name
    title: "Asaas al-Ta'weel"
    content_profile: islamic_scholarly
    bucket: Islamic                  # derived from content_profile (kept for fast reads)
    shared:                          # optional shared-library pointers (relative to work dir)
      pronunciation: _shared/pronunciation.yml
      knowledge: _shared/knowledge
    volumes:                         # ordered; each is a normal book dir under vol-NN/
      - order: 1
        slug: asaas-vol-01           # COMPOSITE slug (slug-legal; works with --resume)
        dir: vol-01                  # dir name under the work dir
        source_pdf: vol-01/_source/asaas-vol-01.pdf   # PDF-sourced volume; OR …
        # source_audio_dir: vol-01/source             # … audio-sourced volume (.mp3
        #   lectures under source/, transcribed by transcribe_audio_book.py). Exactly
        #   one of source_pdf / source_audio_dir is set per volume.
        sources:                     # role-tagged inputs (Q7)
          - path: vol-01/_source/asaas-vol-01.pdf
            role: primary_source
        status: draft                # mirrors the volume's own state; advisory cache
      - order: 2
        slug: asaas-vol-02
        dir: vol-02
        ...

This module does NOT validate volume-entry fields (pure dict I/O), so the
source_pdf vs source_audio_dir choice is enforced by the writer (intake_book.py),
not here.

The composite volume slug is ``<work_slug>-<dir>`` (e.g. ``asaas`` + ``vol-02`` →
``asaas-vol-02``). It is slug-legal so ``--resume asaas-vol-02`` works unchanged.
``_paths`` discovers volume dirs by the ``work.yml`` marker + ``vol-*`` glob WITHOUT
importing this module (no yaml dep, no circular import); this module is the
authoritative reader for the manifest CONTENTS (titles, sources, order, shared).
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths

try:
    import yaml
except Exception as exc:  # pragma: no cover - yaml is a hard dep everywhere else
    raise ImportError("_work_manifest requires PyYAML") from exc

WORK_MANIFEST_NAME = "work.yml"


# ── presence / paths ─────────────────────────────────────────────────────────
def manifest_path(work_dir: Path) -> Path:
    """Return the ``work.yml`` path inside ``work_dir`` (no existence check)."""
    return Path(work_dir) / WORK_MANIFEST_NAME


def has_manifest(dir_: Path) -> bool:
    """True iff ``dir_`` holds a ``work.yml`` — i.e. it is a multi-volume work parent."""
    return manifest_path(dir_).is_file()


def work_dir_for(work_slug: str) -> Path | None:
    """Resolve the on-disk parent dir for ``work_slug`` (must hold a manifest), or None.

    Delegates to ``_paths.find_content`` so the layout seam stays single-sourced.
    """
    found = _paths.find_content(work_slug)
    if not found:
        return None
    _status, _bucket, path = found
    return path if has_manifest(path) else None


# ── slug mapping ─────────────────────────────────────────────────────────────
def work_slug_of(volume_slug: str) -> str | None:
    """Map a COMPOSITE volume slug to its work slug, or None if it isn't one.

    ``asaas-vol-02`` → ``asaas`` **only when** ``content/<B>/asaas/work.yml`` exists.
    A flat book whose name merely ends in ``-vol-N`` (e.g. ``journey-to-the-west-vol-1``)
    returns None — there is no parent manifest, so it is NOT a multi-volume work.
    """
    work, _dir = _split_composite(volume_slug)
    if work is None:
        return None
    return work if work_dir_for(work) is not None else None


def is_volume_slug(slug: str) -> bool:
    """True iff ``slug`` resolves to a volume of an existing multi-volume work."""
    return work_slug_of(slug) is not None


def _split_composite(volume_slug: str) -> tuple[str | None, str | None]:
    """Split ``<work>-<vol-NN>`` → (work, dir). (None, None) if it has no vol suffix."""
    import re

    m = re.match(r"^(?P<work>.+)-(?P<dir>vol-\d+)$", volume_slug.strip())
    if not m:
        return (None, None)
    return (m.group("work"), m.group("dir"))


def composite_slug(work_slug: str, vol_dir: str) -> str:
    """Build the composite volume slug: ``<work_slug>-<vol_dir>``."""
    return f"{work_slug}-{vol_dir}"


# ── read / write ─────────────────────────────────────────────────────────────
def read_manifest(work_dir: Path) -> dict[str, Any] | None:
    """Parse ``work_dir/work.yml`` into a dict, or None if absent/empty/invalid."""
    p = manifest_path(work_dir)
    if not p.is_file():
        return None
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def write_manifest(work_dir: Path, manifest: dict[str, Any]) -> None:
    """Atomically write ``manifest`` to ``work_dir/work.yml`` (temp + os.replace)."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    target = manifest_path(work_dir)
    fd, tmp = tempfile.mkstemp(dir=str(work_dir), prefix=".work.", suffix=".yml.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            yaml.safe_dump(manifest, fh, sort_keys=False, allow_unicode=True)
        os.replace(tmp, target)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


# ── volume queries ───────────────────────────────────────────────────────────
def volumes_of(work_slug: str) -> list[dict[str, Any]]:
    """Return the ordered list of volume entries for ``work_slug`` ([] if not a work)."""
    wd = work_dir_for(work_slug)
    if wd is None:
        return []
    manifest = read_manifest(wd) or {}
    vols = manifest.get("volumes") or []
    if not isinstance(vols, list):
        return []
    return sorted((v for v in vols if isinstance(v, dict)), key=lambda v: v.get("order", 0))


def volume_entry(volume_slug: str) -> dict[str, Any] | None:
    """Return the manifest entry for one composite volume slug, or None."""
    work = work_slug_of(volume_slug)
    if work is None:
        return None
    for v in volumes_of(work):
        if v.get("slug") == volume_slug:
            return v
    return None


def shared_dir(work_slug: str, kind: str) -> Path | None:
    """Resolve a shared-library pointer (e.g. ``pronunciation``/``knowledge``) for a work.

    Returns the absolute path the manifest's ``shared.<kind>`` points to (relative
    to the work dir), or None if the work / pointer is absent.
    """
    wd = work_dir_for(work_slug)
    if wd is None:
        return None
    manifest = read_manifest(wd) or {}
    shared = manifest.get("shared") or {}
    rel = shared.get(kind) if isinstance(shared, dict) else None
    if not rel:
        return None
    return (wd / rel).resolve()
