"""Intelligence layer — phase 0h step 3: DB-backed Augmenter.

Enriches episode text with relevant doctrine atoms from the Kashkole corpus
stored in the knowledge-base DB.  This is the Wave B upgrade of the JSONL-based
`knowledge/augmenter.py`, which was deleted 2026-07-18 (it was never wired as a
runtime fallback); this module is the only augment path.

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
from _rules import (
    CONTENT_LEVEL_LADDER,
    R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED,
    allowed_content_levels,
)

from intelligence._local_server_client import quran_verse as _live_verse
from intelligence._local_server_client import topic_search as _live_topic_search

# Maximum doctrine atoms injected per augmentation call
_MAX_ATOMS_DEFAULT = 5
# Maximum etymology insights woven per chapter (Wave L-4). Hard cap — etymology is
# rationed so each root-insight lands; the challenger (Category W) enforces this.
_MAX_ETYMOLOGY_DEFAULT = 3
# Trim atom text_en to this many chars — Kashkole atoms are full doctrinal chapters and
# can exceed 6K chars each.  ~600 chars ≈ 90–100 words: enough to convey the central
# teaching without flooding the NotebookLM customize-prompt.
_MAX_ATOM_TEXT_CHARS = 600
# Strip Arabic Unicode range (U+0600–U+06FF and extended)
_ARABIC_RE = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]+")
# Strip Kashkole markup wrappers: ⟪ar:...⟫, ⟪quran N:N⟫, ⟪ar-quote:...⟫
_WRAPPER_RE = re.compile(r"⟪[^⟫]*⟫")

# Canonical Q-citation pattern: Q2:255 or unicode quran marker
_QURAN_CITE_RE = re.compile(r"Q(\d+):(\d+)", re.IGNORECASE)
# Topic marker template emitted when enable_topic_markers is true
_TOPIC_MARKER_TMPL = '<span class="ref-topic" data-topic-id="{id}">{text}</span>'

_PROMPT_BLOCK_HEADER = "[PRIOR DOCTRINAL CONTEXT — Kashkole corpus]"
_TERM_BLOCK_HEADER = "[TERM GLOSSARY — Kashkole corpus]"
_QUOTE_BLOCK_HEADER = "[ATTRIBUTED SAYINGS — Kashkole corpus]"
# Minimum term-name length for keyword match — avoids false hits on very short roots
_MIN_TERM_MATCH_LEN = 4
# Common English words to skip in term keyword matching — they appear italicised in
# Kashkole source but carry no Islamic technical meaning.
_COMMON_ENGLISH_SKIP = frozenset(
    {
        "complete",
        "perfect",
        "defective",
        "content",
        "without",
        "observe",
        "observation",
        "knowledge",
        "power",
        "life",
        "faith",
        "truth",
        "light",
        "prayer",
        "fasting",
        "pilgrimage",
        "alms",
        "witness",
        "first",
        "second",
        "third",
        "good",
        "evil",
        "right",
        "wrong",
        "great",
        "small",
        "high",
        "low",
        "able",
        "above",
        "below",
        "before",
        "after",
        "indeed",
        "thus",
        "divine",
        "sacred",
        "holy",
        "inner",
        "outer",
        "true",
        "false",
        "special",
        "general",
        "natural",
        "spiritual",
        "physical",
        "moral",
        "pure",
        "perfect",
        "blessed",
    }
)


# ─── public API ───────────────────────────────────────────────────────────────


def augment_episode_text(
    episode_text: str,
    book_dir: Path,
    topic_tags: Sequence[str] | None = None,
    *,
    max_atoms: int = _MAX_ATOMS_DEFAULT,
    tradition: str | None = None,
    episode_slug: str = "",
    record: bool = True,
) -> str:
    """Prepend doctrine, term, quote, and etymology context blocks to episode text.

    Four parallel lookups (all gated on enable_knowledge_augmenter in meta.yml):
      1. Doctrine atoms  — tag-based query against the book's knowledge_tags.
      2. Term atoms      — keyword match: term names that appear in the episode text.
      3. Quote atoms     — speaker keyword match: quotes whose speaker is named in the text.
      4. Etymology atoms — root-insight match (universal; ≤3/chapter; spoken form).

    Cross-chapter anti-repetition (Wave L-5): atoms injected into OTHER episodes of
    this book (tracked in episode-augment-ledger.json) are excluded, so no atom
    repeats across chapters in the same book/binder. After selection, the atoms
    used by THIS episode are recorded to the ledger (unless record=False, used by
    tests). Re-running one episode is idempotent (its own prior atoms aren't
    excluded from itself).

    Returns original text unchanged if the gate is off or all four lookups return empty.

    Args:
        episode_text: The framing/episode text to augment.
        book_dir:     `content/drafts/<slug>/` — used to read meta.yml + ledger.
        topic_tags:   Tags to filter doctrine atoms by.  If None, falls back to
                      book-level knowledge_tags from meta.yml.
        max_atoms:    Cap applied per lookup bucket (default 5 each).
        episode_slug: Identifies this episode in the anti-repetition ledger.
        record:       When True (default) persist this episode's atoms to the ledger.
    """
    if not _augmentation_enabled(book_dir):
        return episode_text

    book_tradition = tradition or _book_tradition(book_dir)
    # Content-level gate (Wave L-2): None for non-Islamic / unclassified books,
    # which preserves pre-Wave-L behavior (no level filter applied).
    book_content_level = _book_content_level(book_dir)
    # Anti-repetition (Wave L-5): atoms already used by OTHER episodes of this book.
    ledger = _load_episode_ledger(book_dir)
    already_used = _atoms_used_in_other_episodes(ledger, episode_slug)

    injected_ids: list[str] = []

    # 1. Doctrine atoms (tag-based)
    tags = list(topic_tags or []) or _book_tags(book_dir)
    doctrine_block = ""
    if tags:
        # episode_slug-derived offset so each episode gets a different window into the
        # matched atom pool — prevents all episodes in one book seeing identical passages.
        ep_offset = _episode_offset(episode_slug, max_atoms)
        doc_atoms = _fetch_doctrine_atoms(
            tags,
            max_atoms=max_atoms,
            tradition=book_tradition,
            offset=ep_offset,
            content_level=book_content_level,
            exclude_atom_ids=already_used,
        )
        if doc_atoms:
            doctrine_block = _build_context_block(doc_atoms)
            injected_ids += [a["id"] for a in doc_atoms]

    # 2. Term atoms (keyword match in episode text)
    term_block = ""
    term_atoms = _fetch_matching_terms(episode_text, book_tradition, max_terms=max_atoms, exclude_atom_ids=already_used)
    if term_atoms:
        term_block = _build_term_block(term_atoms)
        injected_ids += [a["id"] for a in term_atoms]

    # 3. Quote atoms (speaker keyword match)
    quote_block = ""
    quote_atoms = _fetch_matching_quotes(
        episode_text, book_tradition, max_quotes=max_atoms, exclude_atom_ids=already_used
    )
    if quote_atoms:
        quote_block = _build_quote_block(quote_atoms)
        injected_ids += [a["id"] for a in quote_atoms]

    # 4. Etymology atoms (Wave L-4) — universal resource, never content-level-gated.
    #    Conservative term match; capped at 3/chapter; spoken-form guidance only.
    etym_block = ""
    etym_atoms = _fetch_matching_etymology(
        episode_text, max_etymology=_MAX_ETYMOLOGY_DEFAULT, exclude_atom_ids=already_used
    )
    if etym_atoms:
        etym_block = _build_etymology_block(etym_atoms)
        injected_ids += [a["id"] for a in etym_atoms]

    parts = [p for p in (doctrine_block, term_block, quote_block, etym_block) if p]
    if not parts:
        return episode_text

    if record and injected_ids:
        _record_episode_atoms(book_dir, episode_slug, injected_ids)
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
                _append_mcp_log(
                    mcp_log,
                    "quran_verse",
                    {"surah": surah, "ayat": ayat},
                    latency_ms=latency_ms,
                    source="live",
                    chapter=chapter_slug,
                )
        else:
            if mcp_log:
                _append_mcp_log(
                    mcp_log,
                    "quran_verse",
                    {"surah": surah, "ayat": ayat},
                    latency_ms=latency_ms,
                    source="miss",
                    chapter=chapter_slug,
                )

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
        return bool(meta.get("series", {}).get("enable_knowledge_augmenter", R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED))
    except Exception:
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
    except Exception:
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
    except Exception:
        return []


# ─── Cross-chapter anti-repetition ledger (Wave L-5) ────────────────────────
# A dedicated episode-augmentation ledger, kept SEPARATE from the book-level
# augmentation-ledger.json that augment_book.py fully overwrites with its own
# schema. Sharing one file across the two augmentation paths would be fragile;
# this file is owned solely by the per-episode augmenter.
_EPISODE_LEDGER_NAME = "episode-augment-ledger.json"


def _episode_ledger_path(book_dir: Path) -> Path:
    return book_dir / "_system" / _EPISODE_LEDGER_NAME


def _load_episode_ledger(book_dir: Path) -> dict:
    """Load the per-episode augmentation ledger ({episodes: {slug: {...}}})."""
    p = _episode_ledger_path(book_dir)
    if not p.exists():
        return {"episodes": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("episodes"), dict):
            return data
    except Exception:
        pass
    return {"episodes": {}}


def _atoms_used_in_other_episodes(ledger: dict, current_slug: str) -> set[str]:
    """Union of atom IDs injected into every episode EXCEPT current_slug.

    Excluding the current episode keeps re-runs idempotent: re-augmenting EP02
    does not exclude EP02's own prior atoms (which would drift the result), only
    atoms claimed by EP01, EP03, … so nothing repeats across chapters.
    """
    used: set[str] = set()
    for slug, entry in (ledger.get("episodes") or {}).items():
        if slug == current_slug:
            continue
        used.update(entry.get("atoms_injected", []) or [])
    return used


def _record_episode_atoms(book_dir: Path, episode_slug: str, atom_ids: list[str]) -> None:
    """Write/overwrite this episode's injected-atom list in the ledger."""
    if not episode_slug:
        return
    ledger = _load_episode_ledger(book_dir)
    ledger.setdefault("episodes", {})[episode_slug] = {
        "atoms_injected": sorted(set(atom_ids)),
    }
    p = _episode_ledger_path(book_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(ledger, indent=2, ensure_ascii=False), encoding="utf-8")


def _book_content_level(book_dir: Path) -> str | None:
    """Read `content_level` from meta.yml. Default: None (no gate).

    None means the book is non-Islamic or unclassified — the augmenter applies
    NO content-level filter and behaves exactly as pre-Wave-L. A returned value
    is one of CONTENT_LEVEL_LADDER (general/advanced/taveel/mamsool/mabda_maad/haqaiq);
    anything else is normalized to None so a typo never silently over-restricts.
    """
    meta_path = book_dir / "meta.yml"
    if not meta_path.exists():
        return None
    try:
        import yaml  # type: ignore[import]

        meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        level = meta.get("content_level")
        if level in CONTENT_LEVEL_LADDER:
            return str(level)
        return None
    except Exception:
        return None


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


def _content_level_clause(content_level: str | None) -> tuple[str, list[str]]:
    """Build the cumulative-downward content-level SQL fragment + params (Wave L-2).

    Returns ``("", [])`` when *content_level* is None/unknown — the caller then
    applies NO content-level gate (non-Islamic / unclassified path, identical to
    pre-Wave-L behavior).

    When a level is given, returns a clause restricting doctrine atoms to the
    book's level and everything below it, plus 'universal', plus NULL (so
    uncategorized atoms still pass during the L-3 categorization transition):

        AND (a.content_level IN (?, ?, ...) OR a.content_level IS NULL)

    The params are the allowed ladder levels from `allowed_content_levels()`,
    which already includes 'universal'.
    """
    allowed = allowed_content_levels(content_level)
    if not allowed:
        return "", []
    placeholders = ",".join("?" * len(allowed))
    clause = f"AND (a.content_level IN ({placeholders}) OR a.content_level IS NULL)"
    return clause, list(allowed)


def _fetch_doctrine_atoms(
    tags: list[str],
    *,
    max_atoms: int,
    tradition: str = "universal",
    offset: int = 0,
    content_level: str | None = None,
    exclude_atom_ids: set[str] | None = None,
) -> list[dict]:
    """Query DB for doctrine atoms tagged with any of the given tags.

    Filters by tradition: returns atoms where tradition = <tradition> OR
    tradition = 'universal'.  This prevents cross-tradition injection.

    Filters by content_level (Wave L-2): when the book declares a content_level,
    only doctrine atoms at or below that level (cumulative downward) plus
    'universal' plus NULL are eligible. None => no content-level gate.

    Excludes exclude_atom_ids (Wave L-5): atoms already injected into OTHER
    episodes of the same book, so no doctrine atom repeats across chapters.

    offset: skip this many rows so different episodes get different passages.
    """
    if not tags:
        return []
    conn = _db.get_connection()
    placeholders = ",".join("?" * len(tags))
    level_clause, level_params = _content_level_clause(content_level)
    exclude = sorted(exclude_atom_ids or [])
    exclude_clause = f"AND a.id NOT IN ({','.join('?' * len(exclude))})" if exclude else ""
    rows = conn.execute(
        f"""
        SELECT DISTINCT a.id, a.body
        FROM atoms a
        JOIN atom_topic_tags t ON t.atom_id = a.id
        WHERE a.type = 'doctrine'
          AND (a.tradition = ? OR a.tradition = 'universal')
          {level_clause}
          {exclude_clause}
          AND t.tag IN ({placeholders})
        ORDER BY a.id
        LIMIT ? OFFSET ?
        """,
        (tradition, *level_params, *exclude, *tags, max_atoms, offset),
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
    exclude_atom_ids: set[str] | None = None,
) -> list[dict]:
    """Return term atoms whose `body.term` name appears verbatim in the episode text.

    Case-insensitive; terms shorter than _MIN_TERM_MATCH_LEN chars are skipped to
    reduce false positives on short Arabic roots. Results sorted by term length
    (longest first) so more specific terms take priority over generic roots.
    Excludes exclude_atom_ids (Wave L-5): no term atom repeats across chapters.
    """
    ep_lower = episode_text.lower()
    exclude = exclude_atom_ids or set()
    conn = _db.get_connection()
    rows = conn.execute(
        "SELECT id, body FROM atoms WHERE type='term' AND (tradition=? OR tradition='universal')",
        (tradition,),
    ).fetchall()
    matched: list[dict] = []
    for atom_id, body_json in rows:
        if atom_id in exclude:
            continue
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
    exclude_atom_ids: set[str] | None = None,
) -> list[dict]:
    """Return quote atoms whose speaker name appears in the episode text.

    Only used once quote atoms exist in the DB (currently 0; wired for future runs).
    Excludes exclude_atom_ids (Wave L-5): no quote atom repeats across chapters.
    """
    ep_lower = episode_text.lower()
    exclude = exclude_atom_ids or set()
    conn = _db.get_connection()
    rows = conn.execute(
        "SELECT id, body FROM atoms WHERE type='quote' AND (tradition=? OR tradition='universal')",
        (tradition,),
    ).fetchall()
    matched: list[dict] = []
    for atom_id, body_json in rows:
        if atom_id in exclude:
            continue
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


def _fetch_matching_etymology(
    episode_text: str,
    max_etymology: int = _MAX_ETYMOLOGY_DEFAULT,
    exclude_atom_ids: set[str] | None = None,
) -> list[dict]:
    """Return etymology atoms whose transliterated term/root appears in the text.

    Conservative whole-word match (length >= _MIN_TERM_MATCH_LEN): an etymology
    insight only fires when the actual Arabic term or root is genuinely present —
    so augmentation enriches an EXISTING reference rather than being forced in.
    Etymology atoms are universal (never content-level-gated). Capped at
    *max_etymology* (default 3 per chapter), longest-term-first so the most
    specific derivative wins. Atoms without a baked root_phonetic are skipped
    (a spoken form is required — see fill_etymology_phonetics.py).
    Excludes exclude_atom_ids (Wave L-5): no etymology repeats across chapters.
    """
    import re as _re

    ep_lower = episode_text.lower()
    exclude = exclude_atom_ids or set()
    conn = _db.get_connection()
    rows = conn.execute("SELECT id, body FROM atoms WHERE type='etymology'").fetchall()
    matched: list[tuple[int, dict]] = []
    for atom_id, body_json in rows:
        if atom_id in exclude:
            continue
        try:
            body = json.loads(body_json)
        except json.JSONDecodeError:
            continue
        if not body.get("root_phonetic"):
            continue  # no spoken form yet — cannot weave correctly
        # Candidate spoken terms: the primary term (the surface word the book
        # actually uses), the root, and every derivative transliteration.
        terms = [body.get("term", ""), body.get("root_transliteration", "")]
        terms += [d.get("term", "") for d in body.get("derivatives", [])]
        best_len = 0
        for term in terms:
            t = term.strip().lower()
            if len(t) < _MIN_TERM_MATCH_LEN or t in _COMMON_ENGLISH_SKIP:
                continue
            if _re.search(rf"\b{_re.escape(t)}\b", ep_lower):
                best_len = max(best_len, len(t))
        if best_len:
            matched.append((best_len, {"id": atom_id, "body": body}))
    matched.sort(key=lambda x: -x[0])
    return [m[1] for m in matched[:max_etymology]]


_ETYMOLOGY_BLOCK_HEADER = (
    "[ETYMOLOGY — OPTIONAL ROOT-INSIGHTS — weave AT MOST 3, only where one "
    "genuinely deepens the concept being discussed; skip any that would feel "
    "forced. Speak the root using the SPOKEN form given; NEVER spell out Arabic "
    "letters and NEVER read Arabic script. VARY your phrasing each time — do not "
    "repeat a template.]"
)


def _build_etymology_block(etymology_atoms: list[dict]) -> str:
    """Format etymology atoms as spoken-root-insight guidance for NotebookLM.

    Each line gives the derived word, its spoken form, the root + spoken form, the
    root meaning, and a one-line conceptual bridge — everything a host needs to
    say a natural "the root of X is Y, which means Z, so…" aside WITHOUT ever
    spelling Arabic letters. Arabic script is stripped (DR-012 / spoken-only).
    """
    lines = [_ETYMOLOGY_BLOCK_HEADER, ""]
    for item in etymology_atoms:
        body = item.get("body", {})
        root = _strip_arabic(body.get("root_transliteration", "")).strip()
        root_phon = body.get("root_phonetic", "").strip()
        root_meaning = _strip_arabic(body.get("meaning_en", "")).strip()
        derivs = body.get("derivatives", []) or []
        if not root or not root_phon or not root_meaning:
            continue
        # Pick the most specific derivative as the "surface word" the host links from.
        surface = ""
        for d in sorted(derivs, key=lambda d: -len(d.get("term", ""))):
            term = _strip_arabic(d.get("term", "")).strip()
            phon = d.get("phonetic", "").strip()
            gloss = _strip_arabic(d.get("meaning_en", "")).strip()
            if term and gloss:
                surface = f'the word "{gloss}" ({term}, spoken "{phon}")' if phon else f'the word "{gloss}" ({term})'
                break
        lead = surface or f'the term "{root}"'
        lines.append(
            f'- When {lead} arises, its root is {root} (spoken "{root_phon}"), '
            f'meaning "{root_meaning}". Draw the link only if it illuminates the '
            f'point — e.g. how "{root_meaning}" shades the meaning of the concept.'
        )
    if len(lines) <= 2:
        return ""
    return "\n".join(lines).strip()


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
    except Exception:
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
    except Exception:
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
    except Exception:
        return False


def _append_mcp_log(log_path: Path, tool: str, args: dict, *, latency_ms: int, source: str, chapter: str = "") -> None:
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
