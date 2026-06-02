#!/usr/bin/env python3
"""extract_chapter.py — Capability-first extractor for the /podcast skill.

Resolves a chapter reference to a source file, reads its sidecar contract,
and emits a deterministic NotebookLM Audio Overview bundle: 00-framing.md,
02-key-passages.md, 03-context-pack.md,
04-discussion-spine.md, 99-show-notes.md.

INVOCATION

  python3 scripts/podcast/extract_chapter.py <chapter-ref>
  python3 scripts/podcast/extract_chapter.py <chapter-ref> --contract <path>
  python3 scripts/podcast/extract_chapter.py <chapter-ref> --force

CHAPTER REF RESOLUTION

  1. Literal path (absolute or repo-relative) → used as-is.
  2. `<book-slug>/<ref>` shorthand → resolves within that book only.
  3. Bare `<ref>` → searches every
     _workspace/*/*/chapters/<ref>.txt. If more than one book
     owns the same chapter slug, the script refuses with a disambiguation
     error rather than silently picking the alphabetically-first match.

CONTRACT RESOLUTION

  1. --contract <path> (explicit)
  2. _workspace/<category>/<book-slug>/chapter-contracts/<chapter-slug>.yml
  3. Falls back to a generated stub at the location above, with [TODO] markers.

OUTPUT (per contract.source_type)

  book-chapter:  content/drafts/<book_slug>/...
  article:       _workspace/articles/<book_slug>/...

  ├── chapters/ch##-<slug>.txt                       (chapter copy; SOURCE upload; THE refinement target)
  ├── _system/episode-drafts/EP##-<slug>/
  │   ├── 00-framing.md         (CUSTOMIZE PROMPT body — fed to build_episode_txt.py)
  │   ├── 02-key-passages.md    (scaffold with anchor markers)
  │   ├── 03-context-pack.md    (scaffold)
  │   ├── 04-discussion-spine.md (N beat templates per length_target)
  │   └── 99-show-notes.md      (optional, from contract.show_notes)
  └── (build_episode_txt.py emits episodes/EP##-<slug>.txt downstream)

  NOTE: No `01-source-primary.md` — the chapter file IS the source under v3.4's
  two-file deliverable model (SKILL.md §0 Invariant 1).

DETERMINISM GUARANTEE

  Same chapter + same contract → byte-identical bundle scaffolding.
  No timestamps, no random ordering, no environment-dependent paths.
  Content slots requiring downstream LLM authoring are clearly marked
  with [LLM-SELECT], [LLM-FILL], or [TODO].

BOUNDARY (SKILL.md §9)

  This script reads ONLY content/podcast/**. Memoir content
  (content/babu-memoir/**) is out of scope and refused by the adapter
  via PROHIBITED_PATH_PREFIXES.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from _paths import REPO_ROOT
from typing import Any

# Re-export helpers so existing callers that do
#   `from extract_chapter import X`
# continue to work without modification.
from _extract_helpers import *  # noqa: F401, F403
from _extract_helpers import (
    load_yaml, assert_boundary_safe, PROHIBITED_PATH_PREFIXES,
    CH_PREFIX_RE, ResolvedChapter,
    Contract, REQUIRED_FIELDS,
    contract_path_for, load_contract, stub_contract, validate_contract,
    CONTRACT_META_PROSE_TELLS, CONTRACT_META_PROSE_REGEX, CONTRACT_LINTED_FIELDS,
    lint_contract_meta_prose,
    fmt_list, render_framing, render_key_passages, render_context_pack,
    render_discussion_spine, render_show_notes,
)

# ─────────────────────────────────────────────────────────────────────────────
# Repo layout
# ─────────────────────────────────────────────────────────────────────────────

CONTENT_DIR = REPO_ROOT / "content"
PODCAST_DIR = CONTENT_DIR / "podcast"
LIBRARY_DIR = PODCAST_DIR / "library"  # legacy (retired 2026-05-23); kept for stragglers

# Post-restructure 2026-05-23: in-flight books live at content/drafts/<book>/
# and shipped books at content/published/books/<book>/.
DRAFTS_DIR = CONTENT_DIR / "drafts"
PUBLISHED_BOOKS_DIR = CONTENT_DIR / "published" / "books"

HANDBOOK_DIR = PODCAST_DIR / ".skill" / "handbook"


def _chapter_lookup_roots() -> list[Path]:
    """The directories under which to search for `<book>/chapters/<ref>.txt`."""
    return [DRAFTS_DIR, PUBLISHED_BOOKS_DIR, LIBRARY_DIR]


def _book_glob(book_slug: str, bare_ref: str) -> list[Path]:
    """Glob `<root>/<book_slug>/chapters/<bare_ref>.txt` across all known roots."""
    out: list[Path] = []
    for root in _chapter_lookup_roots():
        flat = root / book_slug / "chapters" / f"{bare_ref}.txt"
        if flat.exists():
            out.append(flat)
        out.extend(root.glob(f"*/{book_slug}/chapters/{bare_ref}.txt"))
    return out


def _all_chapter_paths(ref: str) -> list[Path]:
    """Find every `<root>/<book>/chapters/<ref>.txt`."""
    out: list[Path] = []
    for root in _chapter_lookup_roots():
        out.extend(p for p in root.glob(f"*/chapters/{ref}.txt") if p.is_file())
        out.extend(p for p in root.glob(f"*/*/chapters/{ref}.txt") if p.is_file())
    return out


def resolve_chapter_ref(ref: str) -> ResolvedChapter:
    """Resolve a chapter ref string to a (path, source-bucket, num, slug).

    Resolution order (first definitive match wins; ambiguity is an error):

      1. Literal path (absolute or repo-relative) → used as-is.
      2. `<book-slug>/<ref>` shorthand → forces resolution within one book.
      3. Bare `<ref>` → searched across every
         `library/<category>/<book>/chapters/<ref>.txt`.
    """

    def parse_chapter_filename(p: Path) -> tuple[int | None, str]:
        stem = p.stem
        m = CH_PREFIX_RE.match(stem)
        if m:
            return int(m.group(1)), m.group(2)
        return None, stem

    # 1. Literal path
    literal = Path(ref)
    if not literal.is_absolute():
        literal = (REPO_ROOT / ref).resolve()
    if literal.exists() and literal.is_file():
        assert_boundary_safe(literal, CONTENT_DIR)
        try:
            rel = literal.relative_to(CONTENT_DIR)
            parts = rel.parts
            if parts[0] == "podcast" and len(parts) >= 4 and parts[1] == "library":
                bucket = parts[3]
            elif parts[0] == "podcast" and len(parts) >= 2:
                bucket = parts[1]
            else:
                bucket = parts[0]
        except ValueError:
            bucket = "unknown"
        num, slug = parse_chapter_filename(literal)
        return ResolvedChapter(literal, bucket, num, slug)

    # 2. `<book-slug>/<ref>` shorthand: explicit book scoping.
    if "/" in ref and not ref.startswith("/"):
        book_slug, bare_ref = ref.split("/", 1)
        candidates = _book_glob(book_slug, bare_ref)
        if len(candidates) == 1:
            cand = candidates[0]
            assert_boundary_safe(cand, CONTENT_DIR)
            num, slug = parse_chapter_filename(cand)
            return ResolvedChapter(cand, book_slug, num, slug)
        if len(candidates) > 1:
            sys.exit(
                f"ERROR: book-slug {book_slug!r} resolves to multiple paths. Found:\n"
                + "\n".join(f"    {c}" for c in candidates)
            )

    # 3. Bare `<ref>`: search every {drafts,published,legacy-library}/<book>/chapters/.
    matches = _all_chapter_paths(ref)
    if len(matches) == 1:
        cand = matches[0]
        assert_boundary_safe(cand, CONTENT_DIR)
        num, slug = parse_chapter_filename(cand)
        bucket = cand.parents[1].name
        return ResolvedChapter(cand, bucket, num, slug)
    if len(matches) > 1:
        sys.exit(
            f"ERROR: chapter ref {ref!r} matches in {len(matches)} books:\n"
            + "\n".join(f"    {c.parents[1].name}/  →  {c.relative_to(REPO_ROOT)}"
                        for c in matches) +
            f"\n  Disambiguate by passing `<book-slug>/{ref}` "
            f"(e.g. `<book-slug>/{ref}`) or the full repo-relative path."
        )

    sys.exit(
        f"ERROR: could not resolve chapter ref {ref!r}.\n"
        f"  Tried:\n"
        f"    {literal}\n"
        f"    {DRAFTS_DIR}/*/chapters/{ref}.txt\n"
        f"    {DRAFTS_DIR}/*/*/chapters/{ref}.txt\n"
        f"    {PUBLISHED_BOOKS_DIR}/*/chapters/{ref}.txt\n"
        f"    {LIBRARY_DIR}/*/*/chapters/{ref}.txt   (legacy)\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Episode number assignment
# ─────────────────────────────────────────────────────────────────────────────


def next_episode_number(bucket_root: Path) -> int:
    """Scan existing _system/episode-drafts/EP##-* and return next monotonic."""
    drafts = bucket_root / "_system" / "episode-drafts"
    if not drafts.exists():
        return 1
    highest = 0
    for d in drafts.iterdir():
        if not d.is_dir():
            continue
        m = re.match(r"^EP(\d+)-", d.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


# ─────────────────────────────────────────────────────────────────────────────
# Emit
# ─────────────────────────────────────────────────────────────────────────────


def write_if_needed(path: Path, content: str, force: bool, written: list[Path], skipped: list[Path]) -> None:
    if path.exists() and not force:
        existing = path.read_text(encoding="utf-8")
        if existing == content:
            skipped.append(path)
            return
        sys.exit(
            f"ERROR: {path} already exists and differs from the new render.\n"
            f"  Re-run with --force to overwrite, or diff manually."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    written.append(path)


def emit_bundle(chapter: ResolvedChapter, c: Contract, force: bool) -> None:
    bucket = chapter.source_bucket
    if c.get("source_type") == "book-chapter" and c.get("book_slug"):
        bucket = c.get("book_slug")
    # bucket_root derived from the resolved chapter path. Chapter file is at:
    #   - legacy:    library/<category>/<book>/chapters/<file>.txt → parents[1] = <book>
    #   - drafts:    content/drafts/<book>/chapters/<file>.txt    → parents[1] = <book>
    #   - published: content/published/books/<book>/chapters/<file>.txt → parents[1] = <book>
    bucket_root = chapter.path.parents[1]
    from _rules import ALLOWED_CATEGORIES as _CATS  # noqa: PLC0415
    valid_root_ancestors = {"library", "drafts", "books"} | set(_CATS)
    if bucket_root.parent.name not in valid_root_ancestors:
        sys.exit(
            f"ERROR: resolved chapter is not under a canonical root.\n"
            f"  bucket_root={bucket_root}\n"
            f"  bucket_root.parent.name={bucket_root.parent.name!r}\n"
            f"  Expected one of: {sorted(valid_root_ancestors)} (which means the\n"
            f"  chapter must live at content/drafts/<book>/chapters/, content/\n"
            f"  published/books/<book>/chapters/, or the legacy content/podcast/\n"
            f"  library/<category>/<book>/chapters/).\n"
            f"  This usually means a literal-path resolution outside the canonical\n"
            f"  layout. Move the chapter to one of the supported roots."
        )

    ep_num = c.get("episode_number") or chapter.chapter_number or next_episode_number(bucket_root)
    slug = c.get("slug")
    ep_id = f"EP{ep_num:02d}-{slug}"

    chapter_text = chapter.path.read_text(encoding="utf-8")

    # Word-count band check — surfaces collisions with NotebookLM's Audio Overview limits
    # at extract time, not at build time.
    word_count = len(chapter_text.split())
    band_warnings: list[str] = []
    if word_count > 9500:
        band_warnings.append(
            f"  WARN: chapter is {word_count} words — over the 9,500 word soft ceiling.\n"
            f"        NotebookLM starts summarizing aggressively past this point.\n"
            f"        build_episode_txt.py HARD-refuses chapters > 12,000 words.\n"
            f"        Paths: (a) refine the chapter file ({chapter.path.name}) in place\n"
            f"        down to ≤9,500 words; (b) split into two derivative chapters\n"
            f"        with distinct slugs; (c) accept the summarization tradeoff —\n"
            f"        appropriate for `extended` tier dense doctrinal chapters where\n"
            f"        density matters more than precise length."
        )
    elif word_count > 4500 and c.get("length_target") != "longer":
        band_warnings.append(
            f"  WARN: chapter is {word_count} words but length_target is "
            f"{c.get('length_target')!r}. Consider length_target: longer."
        )
    elif word_count < 500:
        band_warnings.append(
            f"  WARN: chapter is {word_count} words — under the 500 word floor. "
            f"Hosts will resort to filler."
        )

    # 1. Chapter copy — always write to the SAME filename we resolved from (Bug X4 fix).
    chapter_out = chapter.path

    # 2. Bundle scaffolding → _system/episode-drafts/EP##-<slug>/
    draft_dir = bucket_root / "_system" / "episode-drafts" / ep_id

    written: list[Path] = []
    skipped: list[Path] = []

    write_if_needed(chapter_out, chapter_text, force, written, skipped)
    write_if_needed(draft_dir / "00-framing.md", render_framing(c, chapter, ep_num), force, written, skipped)
    # 02-/03-/04- scaffolds RETIRED 2026-05-25 (F30 scholarly-rubric triage).
    # render_key_passages / render_context_pack / render_discussion_spine are kept in
    # _extract_helpers.py so a future "revive steering layer" decision can re-enable them —
    # but no caller invokes them today.
    # write_if_needed(draft_dir / "02-key-passages.md", render_key_passages(c, chapter), force, written, skipped)
    # write_if_needed(draft_dir / "03-context-pack.md", render_context_pack(c, chapter), force, written, skipped)
    # write_if_needed(draft_dir / "04-discussion-spine.md", render_discussion_spine(c, chapter), force, written, skipped)
    write_if_needed(draft_dir / "99-show-notes.md", render_show_notes(c, chapter, ep_num), force, written, skipped)

    if c.path is None:
        stub_dest = contract_path_for(chapter)
        stub_yaml = render_stub_contract_yaml(c.raw)
        write_if_needed(stub_dest, stub_yaml, force, written, skipped)
        print(f"NOTE: no contract found — wrote stub at {stub_dest.relative_to(REPO_ROOT)}. Edit it and re-run with --force.")

    print(f"\nExtracted EP{ep_num:02d}-{slug} from {chapter.path.name}")
    print(f"  Source bucket: {bucket}")
    print(f"  Episode draft: {draft_dir.relative_to(REPO_ROOT)}")
    print(f"  Chapter words: {word_count}")
    print(f"  Files written: {len(written)}")
    print(f"  Files unchanged: {len(skipped)}")
    if band_warnings:
        print()
        for w in band_warnings:
            print(w)
    if written:
        print("\n  Written:")
        for p in written:
            print(f"    {p.relative_to(REPO_ROOT)}")
    if skipped:
        print("\n  Unchanged (deterministic re-render):")
        for p in skipped:
            print(f"    {p.relative_to(REPO_ROOT)}")
    print(f"\nNext: build the customize-prompt episode txt:")
    print(f"  python3 scripts/podcast/build_episode_txt.py {bucket_root.relative_to(REPO_ROOT)} {ep_id}")


def render_stub_contract_yaml(stub: dict[str, Any]) -> str:
    """Minimal YAML emitter for the stub contract. Only handles the schema we use."""
    out = ["# chapter-contract.yml — auto-generated stub. Edit and re-run extract_chapter.py --force.", ""]
    for k, v in stub.items():
        if v is None:
            out.append(f"{k}: null")
        elif isinstance(v, bool):
            out.append(f"{k}: {'true' if v else 'false'}")
        elif isinstance(v, (int, float)):
            out.append(f"{k}: {v}")
        elif isinstance(v, list):
            if not v:
                out.append(f"{k}: []")
            else:
                out.append(f"{k}:")
                for item in v:
                    out.append(f"  - {item}")
        elif isinstance(v, dict):
            if not v:
                out.append(f"{k}: {{}}")
            else:
                out.append(f"{k}:")
                for kk, vv in v.items():
                    if vv is None:
                        out.append(f"  {kk}: null")
                    elif isinstance(vv, list):
                        if not vv:
                            out.append(f"  {kk}: []")
                        else:
                            out.append(f"  {kk}:")
                            for item in vv:
                                out.append(f"    - {item}")
                    else:
                        out.append(f"  {kk}: {vv}")
        else:
            s = str(v)
            if "\n" in s or ":" in s or s.startswith(("'", '"')):
                out.append(f'{k}: "{s}"')
            else:
                out.append(f"{k}: {s}")
    return "\n".join(out) + "\n"


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Extract a chapter into a deterministic NotebookLM Audio Overview bundle.",
    )
    ap.add_argument("chapter_ref", help="Chapter path, slug, or basename (e.g. ch01-man).")
    ap.add_argument("--contract", type=Path, default=None,
                    help="Explicit contract file. Default: _workspace/<category>/<book>/chapter-contracts/<slug>.yml")
    ap.add_argument("--force", action="store_true",
                    help="Overwrite existing bundle files even if they differ.")
    args = ap.parse_args()

    chapter = resolve_chapter_ref(args.chapter_ref)
    c = load_contract(args.contract, chapter)
    validate_contract(c, chapter)
    lint_contract_meta_prose(c)
    emit_bundle(chapter, c, args.force)


if __name__ == "__main__":
    main()
