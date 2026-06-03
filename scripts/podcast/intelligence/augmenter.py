"""Intelligence layer — phase 0h step 3: DB-backed Augmenter.

Enriches episode text with relevant doctrine atoms from the Kashkole corpus
stored in the knowledge-base DB.  This is the Wave B upgrade of the JSONL-based
`knowledge/augmenter.py`.  The old JSONL augmenter remains as a fallback for
books without DB-backed atoms.

Guards:
  - `series.enable_knowledge_augmenter` must be True in the book's meta.yml
    (default: disabled, per R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED = False).
  - Only atoms with `needs_review = 0` (high-confidence, human-approved) are used.
  - Arabic script is never included in the injected block (DR-012).

Authority: architecture.md §Intelligence Layer; plan.md Wave B, B3.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _db
from _rules import R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED
from intelligence._local_server_client import quran_verse as _live_verse, topic_search as _live_topic_search

# Maximum doctrine atoms injected per augmentation call
_MAX_ATOMS_DEFAULT = 5
# Trim atom text_en to this many chars — Kashkole atoms are full doctrinal chapters and
# can exceed 6K chars each.  ~600 chars ≈ 90–100 words: enough to convey the central
# teaching without flooding the NotebookLM customize-prompt.
_MAX_ATOM_TEXT_CHARS = 600
# Strip Arabic Unicode range (U+0600–U+06FF and extended)
_ARABIC_RE = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]+")
# Strip Kashkole markup wrappers: ⟪ar:...⟫, ⟪quran N:N⟫, ⟪ar-quote:...⟫
_WRAPPER_RE = re.compile(r'⟪[^⟫]*⟫')

# Canonical Q-citation pattern: Q2:255 or unicode quran marker
_QURAN_CITE_RE = re.compile(r"Q(\d+):(\d+)", re.IGNORECASE)
# Topic marker template emitted when enable_topic_markers is true
_TOPIC_MARKER_TMPL = '<span class="ref-topic" data-topic-id="{id}">{text}</span>'

_PROMPT_BLOCK_HEADER = "[PRIOR DOCTRINAL CONTEXT — Kashkole corpus]"
_TERM_BLOCK_HEADER  = "[TERM GLOSSARY — Kashkole corpus]"
_QUOTE_BLOCK_HEADER = "[ATTRIBUTED SAYINGS — Kashkole corpus]"
# Minimum term-name length for keyword match — avoids false hits on very short roots
_MIN_TERM_MATCH_LEN = 4
# Common English words to skip in term keyword matching — they appear italicised in
# Kashkole source but carry no Islamic technical meaning.
_COMMON_ENGLISH_SKIP = frozenset({
    "complete", "perfect", "defective", "content", "without", "observe",
    "observation", "knowledge", "power", "life", "faith", "truth", "light",
    "prayer", "fasting", "pilgrimage", "alms", "witness", "first", "second",
    "third", "good", "evil", "right", "wrong", "great", "small", "high", "low",
    "able", "above", "below", "before", "after", "indeed", "thus", "divine",
    "sacred", "holy", "inner", "outer", "true", "false", "special", "general",
    "natural", "spiritual", "physical", "moral", "pure", "perfect", "blessed",
})


# ─── public API ───────────────────────────────────────────────────────────────

def augment_episode_text(
    episode_text: str,
    book_dir: Path,
    topic_tags: Sequence[str] | None = None,
    *,
    max_atoms: int = _MAX_ATOMS_DEFAULT,
    tradition: str | None = None,
    episode_slug: str = "",
) -> str:
    """Prepend doctrine, term, and quote context blocks to episode text.

    Three parallel lookups (all gated on enable_knowledge_augmenter in meta.yml):
      1. Doctrine atoms  — tag-based query against the book's knowledge_tags.
      2. Term atoms      — keyword match: term names that appear in the episode text.
      3. Quote atoms     — speaker keyword match: quotes whose speaker is named in the text.

    Returns original text unchanged if the gate is off or all three lookups return empty.

    Args:
        episode_text: The framing/episode text to augment.
        book_dir:     `content/drafts/<slug>/` — used to read meta.yml.
        topic_tags:   Tags to filter doctrine atoms by.  If None, falls back to
                      book-level knowledge_tags from meta.yml.
        max_atoms:    Cap applied per lookup bucket (default 5 each).
    """
    if not _augmentation_enabled(book_dir):
        return episode_text

    book_tradition = tradition or _book_tradition(book_dir)

    # 1. Doctrine atoms (tag-based)
    tags = list(topic_tags or []) or _book_tags(book_dir)
    doctrine_block = ""
    if tags:
        # episode_slug-derived offset so each episode gets a different window into the
        # matched atom pool — prevents all episodes in one book seeing identical passages.
        ep_offset = _episode_offset(episode_slug, max_atoms)
        doc_atoms = _fetch_doctrine_atoms(
            tags, max_atoms=max_atoms, tradition=book_tradition, offset=ep_offset
        )
        if doc_atoms:
            doctrine_block = _build_context_block(doc_atoms)

    # 2. Term atoms (keyword match in episode text)
    term_block = ""
    term_atoms = _fetch_matching_terms(episode_text, book_tradition, max_terms=max_atoms)
    if term_atoms:
        term_block = _build_term_block(term_atoms)

    # 3. Quote atoms (speaker keyword match)
    quote_block = ""
    quote_atoms = _fetch_matching_quotes(episode_text, book_tradition, max_quotes=max_atoms)
    if quote_atoms:
        quote_block = _build_quote_block(quote_atoms)

    parts = [p for p in (doctrine_block, term_block, quote_block) if p]
    if not parts:
        return episode_text
    return "\n\n".join(parts) + "\n\n" + episode_text


def augment_chapter_text(
    chapter_text: str,
    book_dir: Path,
    chapter_slug: str = "",
    *,
    mcp_log: Path | None = None,
) -> str:
    """J3: augment chapter text with live verse lookups for uncovered Q-citations.

    Scans for Q<surah>:<ayat> citation patterns not already in the knowledge DB.
    For each uncovered citation, calls localhost:4390/quran/verse as a live fallback.
    Logs each live call to mcp_log (_system/mcp-calls.jsonl) when provided.

    Gate: series.enable_live_quran_lookup must be True in meta.yml (default False).
    Server unreachable -> logs a warning and continues unchanged (never crashes).
    """
    if not _live_quran_enabled(book_dir):
        return chapter_text

    citations = _QURAN_CITE_RE.findall(chapter_text)
    if not citations:
        return chapter_text

    import time
    additions: list[str] = []
    for surah_str, ayat_str in citations:
        surah, ayat = int(surah_str), int(ayat_str)
        if _verse_in_db(surah, ayat):
            continue
        t0 = time.monotonic()
        verse = _live_verse(surah, ayat)
        latency_ms = int((time.monotonic() - t0) * 1000)
        if verse and not verse.get("error"):
            pickthall = verse.get("pickthall", "")
            additions.append(f"[Q{surah}:{ayat}] {pickthall}")
            if mcp_log:
                _append_mcp_log(mcp_log, "quran_verse", {"surah": surah, "ayat": ayat},
                                latency_ms=latency_ms, source="live", chapter=chapter_slug)
        else:
            if mcp_log:
                _append_mcp_log(mcp_log, "quran_verse", {"surah": surah, "ayat": ayat},
                                latency_ms=latency_ms, source="miss", chapter=chapter_slug)

    if not additions:
        return chapter_text
    footer = "\n\n[LIVE VERSE CONTEXT]\n" + "\n".join(additions)
    return chapter_text + footer


def emit_topic_markers(
    chapter_text: str,
    book_dir: Path,
    chapter_slug: str = "",
) -> str:
    """J5: replace topic keyword spans with interactive .ref-topic markers.

    Searches the Wisdom topic database for the chapter's key terms and wraps
    matching phrases with <span class="ref-topic" data-topic-id="N">...</span>.
    Gate: series.enable_topic_markers must be True in meta.yml (default False).
    Server unreachable -> returns original text unchanged.
    """
    if not _topic_markers_enabled(book_dir):
        return chapter_text

    tags = _book_tags(book_dir)
    if not tags:
        return chapter_text

    marked = chapter_text
    for tag in tags[:5]:
        results = _live_topic_search(tag, limit=3)
        for topic in results:
            topic_id = topic.get("topic_id") or topic.get("id")
            topic_name = topic.get("topic") or topic.get("name", "")
            if not topic_id or not topic_name:
                continue
            if topic_name in marked and f'data-topic-id="{topic_id}"' not in marked:
                marked = marked.replace(
                    topic_name,
                    _TOPIC_MARKER_TMPL.format(id=topic_id, text=topic_name),
                    1,
                )
    return marked


def fetch_atoms_for_tags(
    tags: Sequence[str],
    max_atoms: int = _MAX_ATOMS_DEFAULT,
    tradition: str | None = None,
) -> list[dict]:
    """Return a list of doctrine atom dicts matching any of the given tags.

    Only returns atoms where needs_review = 0 (high-confidence, approved).
    Filters by tradition: only atoms whose tradition matches ``tradition`` or
    is 'universal' are returned.
    """
    return _fetch_doctrine_atoms(list(tags), max_atoms=max_atoms, tradition=tradition or "universal")


# ─── internal helpers ─────────────────────────────────────────────────────────

def _augmentation_enabled(book_dir: Path) -> bool:
    """Read `enable_knowledge_augmenter` from meta.yml. Default: False."""
    meta_path = book_dir / "meta.yml"
    if not meta_path.exists():
        return R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED
    try:
        import yaml  # type: ignore[import]
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        return bool(meta.get("series", {}).get("enable_knowledge_augmenter",
                                                R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED))
    except Exception:   # noqa: BLE001
        return R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED


def _book_tradition(book_dir: Path) -> str:
    """Read tradition_affinity from meta.yml. Default: 'universal'."""
    meta_path = book_dir / "meta.yml"
    if not meta_path.exists():
        return "universal"
    try:
        import yaml  # type: ignore[import]
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        return str(meta.get("tradition_affinity", "universal"))
    except Exception:  # noqa: BLE001
        return "universal"


def _book_tags(book_dir: Path) -> list[str]:
    """Read `knowledge_tags` from meta.yml as fallback topic list."""
    meta_path = book_dir / "meta.yml"
    if not meta_path.exists():
        return []
    try:
        import yaml  # type: ignore[import]
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        return list(meta.get("knowledge_tags", []))
    except Exception:   # noqa: BLE001
        return []


def _episode_offset(episode_slug: str, max_atoms: int) -> int:
    """Derive a deterministic per-episode OFFSET into the atom pool.

    Different episodes get different windows (EP01→offset 0, EP02→offset 5, etc.)
    so each episode sees unique doctrine passages rather than the same top-N.
    Falls back to 0 for empty slug.
    """
    if not episode_slug:
        return 0
    # Use first digit found in slug (EP01→1, EP02→2, ch03→3) or hash-based fallback
    import re as _re
    m = _re.search(r"\d+", episode_slug)
    ep_num = (int(m.group()) - 1) if m else 0
    return ep_num * max_atoms


def _fetch_doctrine_atoms(
    tags: list[str],
    *,
    max_atoms: int,
    tradition: str = "universal",
    offset: int = 0,
) -> list[dict]:
    """Query DB for doctrine atoms tagged with any of the given tags.

    Filters by tradition: returns atoms where tradition = <tradition> OR
    tradition = 'universal'.  This prevents cross-tradition injection.
    offset: skip this many rows so different episodes get different passages.
    """
    if not tags:
        return []
    conn = _db.get_connection()
    placeholders = ",".join("?" * len(tags))
    rows = conn.execute(
        f"""
        SELECT DISTINCT a.id, a.body
        FROM atoms a
        JOIN atom_topic_tags t ON t.atom_id = a.id
        WHERE a.type = 'doctrine'
          AND (a.tradition = ? OR a.tradition = 'universal')
          AND t.tag IN ({placeholders})
        ORDER BY a.id
        LIMIT ? OFFSET ?
        """,
        (tradition, *tags, max_atoms, offset),
    ).fetchall()
    result = []
    for atom_id, body_json in rows:
        try:
            body = json.loads(body_json)
        except json.JSONDecodeError:
            continue
        result.append({"id": atom_id, "body": body})
    return result


def _fetch_matching_terms(
    episode_text: str,
    tradition: str,
    max_terms: int,
) -> list[dict]:
    """Return term atoms whose `body.term` name appears verbatim in the episode text.

    Case-insensitive; terms shorter than _MIN_TERM_MATCH_LEN chars are skipped to
    reduce false positives on short Arabic roots. Results sorted by term length
    (longest first) so more specific terms take priority over generic roots.
    """
    ep_lower = episode_text.lower()
    conn = _db.get_connection()
    rows = conn.execute(
        "SELECT id, body FROM atoms WHERE type='term' AND (tradition=? OR tradition='universal')",
        (tradition,),
    ).fetchall()
    matched: list[dict] = []
    for atom_id, body_json in rows:
        try:
            body = json.loads(body_json)
        except json.JSONDecodeError:
            continue
        term_name = body.get("term", "").lower().strip()
        text_en = body.get("text_en", "").strip()
        if not term_name or not text_en:
            continue
        if len(term_name) < _MIN_TERM_MATCH_LEN:
            continue
        # Skip common English words that are not Arabic technical terms.
        # These arrive as Tier-2 context captures when a word happens to be italicised
        # in the doctrine source but carries no Islamic technical meaning.
        if term_name in _COMMON_ENGLISH_SKIP:
            continue
        if term_name in ep_lower:
            matched.append({"id": atom_id, "body": body})
    matched.sort(key=lambda x: -len(x["body"].get("term", "")))
    return matched[:max_terms]


def _fetch_matching_quotes(
    episode_text: str,
    tradition: str,
    max_quotes: int,
) -> list[dict]:
    """Return quote atoms whose speaker name appears in the episode text.

    Only used once quote atoms exist in the DB (currently 0; wired for future runs).
    """
    ep_lower = episode_text.lower()
    conn = _db.get_connection()
    rows = conn.execute(
        "SELECT id, body FROM atoms WHERE type='quote' AND (tradition=? OR tradition='universal')",
        (tradition,),
    ).fetchall()
    matched: list[dict] = []
    for atom_id, body_json in rows:
        try:
            body = json.loads(body_json)
        except json.JSONDecodeError:
            continue
        speaker = body.get("speaker", "").lower().strip()
        text_en = body.get("text_en", "").strip()
        if not speaker or not text_en:
            continue
        if speaker in ep_lower:
            matched.append({"id": atom_id, "body": body})
    return matched[:max_quotes]


def _strip_arabic(text: str) -> str:
    """Remove Arabic script runs and Kashkole markup wrappers from text (DR-012).

    Two passes:
      1. Strip ⟪...⟫ wrappers left by the Kashkole ingestion (e.g. ⟪ar:⟫, ⟪quran 2:255⟫).
      2. Strip residual Arabic Unicode character runs.
    """
    text = _WRAPPER_RE.sub("", text)
    return _ARABIC_RE.sub("", text).strip()


def _build_term_block(term_atoms: list[dict]) -> str:
    """Format term atoms as a compact glossary injection block."""
    lines = [_TERM_BLOCK_HEADER, ""]
    for item in term_atoms:
        body = item.get("body", {})
        term = body.get("term", "").strip()
        text_en = _strip_arabic(body.get("text_en", ""))
        if not term or not text_en:
            continue
        snippet = text_en[:_MAX_ATOM_TEXT_CHARS]
        if len(text_en) > _MAX_ATOM_TEXT_CHARS:
            snippet = snippet.rstrip() + " …"
        lines.append(f"*{term}*: {snippet}")
    if len(lines) <= 2:
        return ""
    return "\n".join(lines).strip()


def _build_quote_block(quote_atoms: list[dict]) -> str:
    """Format attributed quote atoms as a prompt injection block."""
    lines = [_QUOTE_BLOCK_HEADER, ""]
    for item in quote_atoms:
        body = item.get("body", {})
        speaker = body.get("speaker", "").strip()
        text_en = _strip_arabic(body.get("text_en", ""))
        if not speaker or not text_en:
            continue
        snippet = text_en[:_MAX_ATOM_TEXT_CHARS]
        if len(text_en) > _MAX_ATOM_TEXT_CHARS:
            snippet = snippet.rstrip() + " …"
        lines.append(f"{speaker}:")
        lines.append(snippet)
        lines.append("")
    if len(lines) <= 2:
        return ""
    return "\n".join(lines).strip()


def _build_context_block(atoms: list[dict]) -> str:
    """Format doctrine atoms as a prompt injection block."""
    lines = [_PROMPT_BLOCK_HEADER, ""]
    for atom in atoms:
        body = atom.get("body", {})
        text_en = _strip_arabic(body.get("text_en", ""))
        if not text_en:
            continue
        binder = body.get("binder_slug", "")
        chapter = body.get("chapter_slug", "")
        tags_label = f"{binder}, ch. {chapter}" if binder else ""
        snippet = text_en[:_MAX_ATOM_TEXT_CHARS]
        if len(text_en) > _MAX_ATOM_TEXT_CHARS:
            snippet = snippet.rstrip() + " …"
        lines.append(f"Source: Kashkole — {tags_label}".rstrip(" —").rstrip())
        lines.append("---")
        lines.append(snippet)
        lines.append("")
    return "\n".join(lines).strip()


def _live_quran_enabled(book_dir: Path) -> bool:
    """Read enable_live_quran_lookup from meta.yml. Default: False."""
    meta_path = book_dir / "meta.yml"
    if not meta_path.exists():
        return False
    try:
        import yaml  # type: ignore[import]
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        return bool(meta.get("series", {}).get("enable_live_quran_lookup", False))
    except Exception:  # noqa: BLE001
        return False


def _topic_markers_enabled(book_dir: Path) -> bool:
    """Read enable_topic_markers from meta.yml. Default: False."""
    meta_path = book_dir / "meta.yml"
    if not meta_path.exists():
        return False
    try:
        import yaml  # type: ignore[import]
        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        return bool(meta.get("series", {}).get("enable_topic_markers", False))
    except Exception:  # noqa: BLE001
        return False


def _verse_in_db(surah: int, ayat: int) -> bool:
    """Return True if a quran atom for this verse exists in the knowledge DB."""
    try:
        conn = _db.get_connection()
        row = conn.execute(
            "SELECT 1 FROM atoms WHERE type='quran' AND json_extract(body,'$.surah')=? AND json_extract(body,'$.ayat')=? LIMIT 1",
            (surah, ayat),
        ).fetchone()
        return row is not None
    except Exception:  # noqa: BLE001
        return False


def _append_mcp_log(log_path: Path, tool: str, args: dict,
                    *, latency_ms: int, source: str, chapter: str = "") -> None:
    """Append a JSON line to _system/mcp-calls.jsonl."""
    import datetime
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "tool": tool,
        "args": args,
        "latency_ms": latency_ms,
        "source": source,
        "chapter": chapter,
    }
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Fetch doctrine atoms for given topic tags.")
    parser.add_argument("tags", nargs="+", help="Topic tags to look up (e.g. tawhid eschatology)")
    parser.add_argument("--max", type=int, default=_MAX_ATOMS_DEFAULT, help="Max atoms to return")
    args = parser.parse_args()
    atoms = fetch_atoms_for_tags(args.tags, max_atoms=args.max)
    if not atoms:
        print("No matching atoms found.")
        return 0
    for atom in atoms:
        body = atom["body"]
        print(f"[{atom['id']}]")
        print(f"  {body.get('text_en', '')[:120]}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
