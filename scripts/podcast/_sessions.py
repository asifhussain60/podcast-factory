#!/usr/bin/env python3
"""_sessions.py — Session grouping for multi-episode books (2026-06-10).

A *session* is a deterministic grouping of episodes by source structure: one
session per source chapter (Part / major division of the source work). It is
applied automatically when a book's planned episode count exceeds
SESSION_EPISODE_THRESHOLD and the plan carries more than one source chapter;
smaller books stay flat (no session fields anywhere — every consumer is
presence-gated).

Locked decisions (Asif, 2026-06-10):
  - Term: "Session" — stored field names are session_*; the display label can
    vary per content profile via SESSION_LABELS (pluggable registry).
  - Boundaries: one session per source Part; uneven sizes accepted as honest.
  - Numbering: global EP numbers stay on disk (EP01..EPnn); session-relative
    numbering ("Session 3, Episode 4") is a display concern only.
  - Physical: metadata everywhere + per-session folders in Google Drive
    delivery only; repo folders stay flat.

Derivation is arithmetic over the Phase 0d TOC plan (source-toc.json) — no
LLM judgement anywhere. Contract stamping appends a clearly-marked block to
each chapter contract; existing session fields are never overwritten.

CLI (backfill a book whose contracts were authored before this module):
  python3 scripts/podcast/_sessions.py <slug> [--dry-run]

Standard: docs/standards/chapter-density.md — "Session grouping".
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Books with more planned episodes than this get sessions automatically.
# Override per book with `sessions: off` (or `sessions: on`) in
# _system/series-config.yaml.
SESSION_EPISODE_THRESHOLD = 8

# Display-label registry per content profile (extensibility-first: one place
# to add a profile-specific label; storage field names never change).
SESSION_LABELS: dict[str, str] = {
    # "islamic_scholarly": "Majlis",   # available if Asif opts in later
}
DEFAULT_SESSION_LABEL = "Session"

_PART_PREFIX = re.compile(
    r"^\s*(part|book|section|volume)\s+([0-9ivxlc]+|one|two|three|four|five|"
    r"six|seven|eight|nine|ten|eleven|twelve)\s*[—–:\-]\s*",
    re.IGNORECASE,
)


def session_label_for_profile(profile: str | None) -> str:
    return SESSION_LABELS.get((profile or "").strip(), DEFAULT_SESSION_LABEL)


def session_title_from_source(source_title: str) -> str:
    """Strip the source's own division prefix ("Part One — ") from a title.

    "Part Two — Spiritual Symbols: The Architecture of Creation"
        → "Spiritual Symbols: The Architecture of Creation"
    Titles without a recognized prefix pass through unchanged.
    """
    cleaned = _PART_PREFIX.sub("", source_title or "").strip()
    return cleaned or (source_title or "").strip()


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-+", "-", s) or "session"


def _config_override(book_dir: Path) -> bool | None:
    """`sessions: on|off` in series-config.yaml, or None when unset."""
    cfg_path = book_dir / "_system" / "series-config.yaml"
    if not cfg_path.exists():
        return None
    try:
        import yaml
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None
    raw = cfg.get("sessions")
    if raw is None:
        return None
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("on", "true", "yes", "1")


def derive_sessions(
    source_chapters: list[dict],
    *,
    threshold: int = SESSION_EPISODE_THRESHOLD,
    force: bool | None = None,
) -> list[dict] | None:
    """Derive the session list from a Phase 0d TOC plan, or None (flat book).

    Returns one dict per session:
      {"session_index", "session_title", "session_slug", "sc_index",
       "episode_numbers": [global ep_nums in order]}

    Flat (None) when: fewer than 2 source chapters, or total episodes <=
    *threshold* — unless *force* (the per-book `sessions:` config override)
    says otherwise.
    """
    if not source_chapters:
        return None
    total_eps = 0
    for sc in source_chapters:
        try:
            total_eps += int(sc.get("episode_count", 1) or 1)
        except (TypeError, ValueError):
            total_eps += 1
    eligible = len(source_chapters) >= 2 and total_eps > threshold
    if force is False or (force is None and not eligible):
        return None
    if len(source_chapters) < 2:
        return None  # a single source chapter can't be split into sessions

    sessions: list[dict] = []
    seen_slugs: set[str] = set()
    for i, sc in enumerate(source_chapters, start=1):
        title = session_title_from_source(str(sc.get("source_title", "")))
        slug = _slugify(title)
        while slug in seen_slugs:
            slug += "-x"
        seen_slugs.add(slug)
        ep_nums = []
        for ep in (sc.get("episodes") or []):
            try:
                ep_nums.append(int(ep["ep_num"]))
            except (KeyError, TypeError, ValueError):
                continue
        sessions.append({
            "session_index": i,
            "session_title": title,
            "session_slug": slug,
            "sc_index": sc.get("sc_index", i),
            "episode_numbers": sorted(ep_nums),
        })
    return sessions


def sessions_for_plan(book_dir: Path, source_chapters: list[dict]) -> list[dict] | None:
    """Derive sessions for an in-memory TOC plan, honoring the book's
    `sessions:` config override. Used by Phase 0d to stamp contracts at
    authoring time (backfill covers books authored before this existed)."""
    return derive_sessions(source_chapters, force=_config_override(book_dir))


def session_for_episode(sessions: list[dict] | None, ep_num: int) -> dict | None:
    """The session dict containing global episode *ep_num*, or None."""
    for s in sessions or []:
        if ep_num in s["episode_numbers"]:
            return s
    return None


def load_sessions_for_book(book_dir: Path) -> list[dict] | None:
    """Derive sessions from the book's TOC plan on disk (None when flat)."""
    toc_path = (book_dir / "_system" / "source" / "text" / "_chunks" / "0d"
                / "source-toc.json")
    if not toc_path.exists():
        return None
    try:
        plan = json.loads(toc_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return derive_sessions(
        plan.get("source_chapters") or [],
        force=_config_override(book_dir),
    )


# ─── contract stamping ────────────────────────────────────────────────────────

def stamp_contract(contract_path: Path, session: dict, ep_num: int) -> bool:
    """Append session fields to a contract that lacks them. Idempotent.

    Returns True when the file was modified. Existing session_* fields are
    never touched (append-only; the LLM-authored YAML is not re-serialized).
    """
    text = contract_path.read_text(encoding="utf-8")
    if re.search(r"^session_index\s*:", text, re.MULTILINE):
        return False
    position = session["episode_numbers"].index(ep_num) + 1
    block = (
        "\n# Session grouping (deterministic — docs/standards/chapter-density.md)\n"
        f"session_index: {session['session_index']}\n"
        f"session_title: {json.dumps(session['session_title'])}\n"
        f"session_slug: {session['session_slug']}\n"
        f"session_episode: {position}\n"
        f"session_episode_count: {len(session['episode_numbers'])}\n"
    )
    contract_path.write_text(text.rstrip("\n") + "\n" + block, encoding="utf-8")
    return True


def stamp_book(book_dir: Path, *, dry_run: bool = False, log=print) -> int:
    """Backfill session fields into every contract of *book_dir*.

    Reads the TOC plan, derives sessions, maps each contract's
    episode_number into its session, appends the fields. Returns the number
    of contracts stamped (0 for flat books — safe no-op).
    """
    sessions = load_sessions_for_book(book_dir)
    if not sessions:
        log(f"  sessions: flat book (below threshold or no plan) — nothing to stamp")
        return 0
    contracts_dir = book_dir / "chapter-contracts"
    stamped = 0
    for path in sorted(contracts_dir.glob("*.yml")):
        try:
            import yaml
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            log(f"  sessions: SKIP {path.name} (unparseable yaml)")
            continue
        if "session_index" in data:
            continue
        try:
            ep_num = int(data.get("episode_number"))
        except (TypeError, ValueError):
            log(f"  sessions: SKIP {path.name} (no episode_number)")
            continue
        session = session_for_episode(sessions, ep_num)
        if session is None:
            log(f"  sessions: SKIP {path.name} (ep {ep_num} not in any session)")
            continue
        if dry_run:
            log(f"  sessions: would stamp {path.name} → "
                f"S{session['session_index']} ({session['session_title']})")
            stamped += 1
            continue
        if stamp_contract(path, session, ep_num):
            log(f"  sessions: stamped {path.name} → "
                f"S{session['session_index']} ({session['session_title']})")
            stamped += 1
    return stamped


def main(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(
        description="Backfill session grouping fields into a book's chapter contracts.")
    p.add_argument("slug", help="Book slug (any bucket).")
    p.add_argument("--dry-run", action="store_true",
                   help="Show the stamping plan without writing.")
    args = p.parse_args(argv)
    from _paths import find_content
    found = find_content(args.slug)
    if found is None:
        print(f"ERROR: no book found for slug {args.slug!r}", file=sys.stderr)
        return 2
    n = stamp_book(found[2], dry_run=args.dry_run)
    print(f"{'Would stamp' if args.dry_run else 'Stamped'} {n} contract(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
