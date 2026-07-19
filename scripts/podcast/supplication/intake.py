"""intake.py — step 1. Create the content folder, the branch, and the config.

Everything about placement and branching is DERIVED from the shared resolvers:

    _paths.content_dir(slug, profile=PROFILE)   → content/Supplications/<slug>/
    _branching.branch_name(None, slug, ...)     → Supplications/<slug>

Neither needed a code change to support this lane — registering the content type
in `_rules.CONTENT_TYPE_REGISTRY` was enough. That is the whole point of the
Tranche-1 design: one additive registration, zero routing edits.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _branching  # noqa: E402
import _paths  # noqa: E402

from . import state  # noqa: E402
from .schema import META_FIELDS, SupplicationError, validate_source_language  # noqa: E402

PROFILE = "islamic_supplication"

SERIES_CONFIG_TEMPLATE = """# series-config.yaml — supplication lane (PDF only).
#
# This item is NOT a podcast. It produces exactly one deliverable: a
# facing-column reading PDF. There are no episodes, audio, slide decks, or
# video, and the podcast orchestrator never runs against it.
content_profile: {profile}
bucket: Supplications
slug: {slug}
# source_language is ALWAYS explicit. It selects the script face (Naskh for ar,
# Nastaliq for ur) and the translation prompt, and is never inferred from the
# text — inferring it is how Urdu silently gets translated as Arabic.
source_language: {lang}
deliverables:
  pdf: true
  episodes: false
  audio: false
  slide_decks: false
  video: false
"""


def content_root(slug: str) -> Path:
    return _paths.content_dir(slug, profile=PROFILE)


def branch_for(slug: str) -> str:
    return _branching.branch_name(None, slug, profile=PROFILE)


def run(
    slug: str,
    *,
    source_language: str,
    title_en: str = "",
    meta: dict[str, str] | None = None,
    create_branch: bool = True,
    repo_root: Path | None = None,
) -> Path:
    """Create content/Supplications/<slug>/ and its branch. Idempotent-safe."""
    lang = validate_source_language(source_language)
    if not slug or "/" in slug:
        raise SupplicationError(f"invalid slug {slug!r}")

    book_dir = content_root(slug)
    if book_dir.exists() and any(book_dir.iterdir()):
        raise SupplicationError(f"{book_dir} already exists and is not empty — pick a new slug or remove it.")

    for sub in ("_system", "_system/source", "book"):
        (book_dir / sub).mkdir(parents=True, exist_ok=True)

    (book_dir / "_system" / "series-config.yaml").write_text(
        SERIES_CONFIG_TEMPLATE.format(profile=PROFILE, slug=slug, lang=lang), encoding="utf-8"
    )

    meta = meta or {}
    unknown = set(meta) - set(META_FIELDS)
    if unknown:
        raise SupplicationError(f"unknown metadata field(s): {sorted(unknown)} (allowed: {list(META_FIELDS)})")
    meta_lines = [f"title: {title_en or slug}", f"content_profile: {PROFILE}", "status: draft", "supplication:"]
    meta_lines += [f"  {k}: {meta[k]}" for k in META_FIELDS if meta.get(k)]
    (book_dir / "meta.yml").write_text("\n".join(meta_lines) + "\n", encoding="utf-8")

    state.init(book_dir, slug=slug, source_language=lang)

    if create_branch:
        _create_branch(branch_for(slug), repo_root or _paths.CONTENT_ROOT.parent)

    return book_dir


def _create_branch(branch: str, repo_root: Path) -> None:
    """Branch off develop. Non-fatal if it already exists — never force-moves."""
    existing = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", branch],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if existing.returncode == 0:
        subprocess.run(["git", "checkout", branch], cwd=repo_root, check=True)
        return
    subprocess.run(["git", "checkout", "-b", branch, "develop"], cwd=repo_root, check=True)
