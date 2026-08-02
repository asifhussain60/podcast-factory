"""_book_companion.py — PROPOSE the reader's per-chapter Companion cards.

The Companion is the PRIVATE reading layer: per-chapter cards a reader surfaces
while reading aloud to someone — an analogy that makes a passage click, a plain
unpacking, a term's root, a question to pose. It is not part of the book. Cards
never enter ``book/book.md`` and never enter the PDF; they live in
``_system/companion-notes/<chapter-key>.json``, the same on-disk shape the Studio
UI writes (mirror of ``plan-dashboard/src/lib/reader/companion/types.ts``).

WHAT THIS MODULE DOES NOT DO, since 2026-08-02: write. It used to run
automatically at the end of every ``0book-render`` and author ten to fifteen
cards for every chapter of the book, so an edition came off the pipeline carrying
a hundred-odd explanations no human had read — and the chapter lane stamped them
``provider: "manual"``, which the site renders as "You", so the machine's cards
wore the reader's name. Asif asked for the opposite arrangement: propose on
demand, per chapter, after the prose is final, and file only what he keeps.

So what survives here is the candidate half, and nothing in it opens a file for
writing. The Composer drives it through ``propose_companion.py``; the kept cards
are filed by the web apply step through the same append-only ``upsertNote`` a
human's own note goes through. See ``propose_chapter_cards`` for why that is a
structural property rather than a flag.

The contract on a candidate is unchanged, and it is the part worth keeping:

  * THREE candidate lanes, so a chapter is seen from three directions — its own
    composed prose, the podcast episodes that cover the same passage, and the
    knowledge base's grounded atoms. One lane alone produces one flavour of card.
  * DETERMINISTIC guardrails before a card is ever shown. A card's ``quote`` must
    be a real substring of the chapter, its Arabic must be copied from a source,
    an etymology card must name a root the corpus actually carries. A card that
    cannot prove itself is dropped — never softened, never filled in.
  * A RANKED pool. Every lane over-produces; a judgment pass ranks the pooled
    candidates, and the balance rule marks what it would have picked. It advises
    now rather than deciding, because the human doing the choosing is in the room.

MIRROR NOTE (2026-07-26): the note type carries an optional ``etymology:
string[]`` — the Studio's Scholar cards keep etymology as discrete, individually
deletable items rather than as prose inside ``body``. This module does not
produce the field; a card without it is valid, and the reader treats absence as
"no items". If cards proposed here ever carry etymology of their own, write it as
that array rather than appending an "Etymology" paragraph to ``body``.

Engine: ``claude -p`` on the flat-rate subscription, as with the rest of the book
lane. The gates and the selection are pure Python — no model is trusted to
enforce its own constraints.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from _arabic_coverage import arabic_run_spans, arabic_span_is_grounded, normalize_arabic
from _authoring._core import AuthoringError, _run_claude_p_with_retry
from _book_companion_prompts import (
    chapter_lane_prompt,
    corpus_lane_prompt,
    corpus_line,
    judge_prompt,
    parse_cards,
    podcast_lane_prompt,
    rank_order,
)
from _book_edits import anchor_key
from _book_fences import span_re
from _buckwalter import arabic_fold
from _corpus_retrieval import RetrievalIndex, atom_searchable_text
from _doctrinal import run_doctrinal_checks
from _narrator_policy import atom_narrator, disallowed_narrator

# ─── Card vocabulary — MIRROR of companion/registry.ts KIND_DEFS ─────────────
# Both sides must change in the same commit (the TS<->Python mirror rule). The
# renderer degrades gracefully for an unknown kind, but a kind absent here can
# never be generated, so this list is the generator's whole vocabulary.
KIND_ANALOGY = "analogy"
KIND_EXPLANATION = "explanation"
KIND_QUESTION = "question"
KIND_NOTE = "note"
KIND_ETYMOLOGY = "etymology"
KIND_VOCAB = (KIND_ANALOGY, KIND_EXPLANATION, KIND_QUESTION, KIND_NOTE, KIND_ETYMOLOGY)

# ─── The balance contract ────────────────────────────────────────────────────
TARGET_MIN = 10
TARGET_MAX = 15
# No single kind may take more than a third of a chapter's cards. This is the rule
# that stops the drift the hand-authored set fell into (19 of 35 analogies).
KIND_CEILING_FRACTION = 1 / 3
# A kind the chapter's material can genuinely support should appear at least once.
# "Can support" is decided by the gates, not by a quota: if no etymology candidate
# survives grounding, the chapter simply has no etymology card.
KIND_FLOOR = 1

# ─── Card body bounds ────────────────────────────────────────────────────────
# A card is something you say out loud in a few sentences. Below the floor it is a
# fragment; above the ceiling the reader stops reading and starts reciting.
_MIN_BODY_WORDS = 20
_MAX_BODY_WORDS = 130

_COMPANION_TIMEOUT = 900
_ATOMS_PER_CHAPTER = 12
_RELEVANCE_THRESHOLD = 0.06
# Transcript assignment floor: below this a transcript is not about this chapter.
_TRANSCRIPT_MATCH_FLOOR = 0.02
_MAX_TRANSCRIPTS_PER_CHAPTER = 3

_CHAPTER_HEADING_RE = re.compile(r"(?m)^##\s+(.+?)\s*$")
_EDITORIAL_SPAN_RE = span_re("editorial")
_META_RE = re.compile(r"\b(as an ai|i cannot|here is the|the chapter says|this card)\b", re.I)
_EP_STEM_RE = re.compile(r"^ch(\d+)")


"""``safe_chapter_key`` lived here and is DELETED (Asif, 2026-08-02).

It claimed to mirror ``companion/keys.ts::safeChapterKey`` and did not. On
``## 9. God's Vicegerent in His Time`` this side produced
``9-god-s-vicegerent-in-his-time`` (apostrophe → separator) and the TypeScript
produced ``9-gods-vicegerent-in-his-time`` (apostrophe deleted). Because Python
named the file and TypeScript asked for it, chapter 9's fourteen cards were
invisible in the reader for as long as they existed — an unpinned mirror, of the
class CLAUDE.md now fixture-pins four of.

Nothing here computes an on-disk note key any more. This module PROPOSES; the
key under which a kept card is filed is supplied by the surface that is already
reading that chapter's notes, so the two can no longer disagree. Chapters are
addressed by ``_book_edits.anchor_key`` — the Composer's own chapter key, which
IS fixture-pinned to its JavaScript twin."""


# ─── Chapters ────────────────────────────────────────────────────────────────
def book_chapters(book_md: str) -> list[dict[str, str]]:
    """``book.md`` as the reader sees it: one entry per ``##`` heading.

    Editorial asides are stripped from the prose a card may quote — an aside is
    companion material itself, and a card quoting one would anchor to text the
    reader meets as an aside rather than as the chapter.
    """
    matches = list(_CHAPTER_HEADING_RE.finditer(book_md))
    out: list[dict[str, str]] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(book_md)
        title = m.group(1).strip()
        prose = _EDITORIAL_SPAN_RE.sub("", book_md[m.end() : end]).strip()
        out.append({"key": anchor_key(title), "title": title, "prose": prose})
    return out


# ─── Lane 2: the podcast ─────────────────────────────────────────────────────
def map_transcripts_to_chapters(
    chapters: list[dict[str, str]], transcripts: dict[str, str]
) -> dict[str, list[tuple[str, float]]]:
    """Assign each episode transcript to the book chapter(s) it actually covers.

    The book's chapters and the podcast's episodes are two different cuts of the
    same source, so no stored mapping relates them. Rather than invent one, this
    scores each transcript against each chapter's prose with the same lexical
    index the augmentation uses, and assigns a transcript to a chapter only when
    the overlap clears a floor. A transcript may serve two adjacent chapters; a
    chapter with no matching episode simply loses that lane.
    """
    if not transcripts:
        return {c["key"]: [] for c in chapters}
    pool = [{"id": stem, "type": "transcript", "body": {"text_en": text}} for stem, text in transcripts.items()]
    index = RetrievalIndex(pool)
    out: dict[str, list[tuple[str, float]]] = {}
    for ch in chapters:
        scored = index.select(ch["prose"], k=_MAX_TRANSCRIPTS_PER_CHAPTER, threshold=_TRANSCRIPT_MATCH_FLOOR)
        out[ch["key"]] = [(s.id, round(s.score, 4)) for s in scored]
    return out


def load_transcripts(book_dir: Path) -> dict[str, str]:
    """Every episode transcript, keyed by canonical stem (the source-of-truth copy)."""
    root = Path(book_dir) / "m4a" / "transcripts"
    if not root.exists():
        return {}
    out: dict[str, str] = {}
    for p in sorted(root.glob("*.transcript.txt")):
        try:
            out[p.name.replace(".transcript.txt", "")] = p.read_text(encoding="utf-8")
        except Exception:
            continue
    return out


def episode_ref(stem: str) -> str:
    """``ch07d-air-and-…`` -> ``EP07`` — the ref shape the card source pill shows."""
    m = _EP_STEM_RE.match(stem)
    return f"EP{int(m.group(1)):02d}" if m else stem[:12]


# ─── Guardrails ──────────────────────────────────────────────────────────────
def gate_card(
    card: dict[str, Any],
    *,
    prose: str,
    arabic_src: str = "",
    etymology_terms: frozenset[str] = frozenset(),
    morphology_ref: dict[str, set[str]] | None = None,
) -> tuple[bool, list[str]]:
    """Deterministic accept/reject for ONE card. Returns (accepted, reasons).

    Every rule here answers "can this card prove itself?". None of them is about
    taste — taste is the judgment pass's job, and it runs on cards that already
    passed this.
    """
    reasons: list[str] = []
    kind = str(card.get("kind") or "").strip().lower()
    body = " ".join(str(card.get("body") or "").split())
    words = body.split()

    if kind not in KIND_VOCAB:
        reasons.append(f"unknown kind {kind!r}")
    if len(words) < _MIN_BODY_WORDS:
        reasons.append(f"too short to be a card ({len(words)}<{_MIN_BODY_WORDS} words)")
        return False, reasons
    if len(words) > _MAX_BODY_WORDS:
        reasons.append(f"over the card budget ({len(words)}>{_MAX_BODY_WORDS} words)")
    if _META_RE.search(body):
        reasons.append("meta-commentary or self-reference")

    # The quote is what the reader highlights — it must exist in the chapter.
    quote = " ".join(str(card.get("quote") or "").split())
    if quote and _normalize_prose(quote) not in _normalize_prose(prose):
        reasons.append(f"quote is not a verbatim passage of the chapter: {quote[:48]!r}")

    # Arabic must be copied from a source, never recalled.
    for span in arabic_run_spans(body, min_chars=2):
        if not arabic_span_is_grounded(span, arabic_src):
            reasons.append(f"Arabic not traceable to a source: {span[:32]}")
            break

    # An etymology card must name a root the corpus actually carries — either an
    # existing etymology atom OR a term the Quranic morphology corpus resolves
    # (the same root truth the site's veto enforces; parity per plan S4).
    if kind == KIND_ETYMOLOGY:
        ref = morphology_ref or {}
        arabic_terms = arabic_run_spans(body, min_chars=2)
        in_atoms = any(t in body.lower() for t in etymology_terms)
        in_morphology = False
        for span in arabic_terms:
            fold = arabic_fold(normalize_arabic(span))
            if fold in ref:
                in_morphology = True
                # A card that also CLAIMS a dashed root must not contradict the
                # corpus for that term (membership veto, under-fires on unknowns).
                m = re.search(r"[ء-ي]\s*(?:-\s*[ء-ي]\s*){1,3}", body)
                if m:
                    claimed = arabic_fold(normalize_arabic(re.sub(r"[-\s]", "", m.group())))
                    if claimed and claimed not in ref[fold]:
                        reasons.append(f"etymology root contradicts the morphology corpus for {span[:16]}")
                break
        if not etymology_terms and not ref:
            reasons.append("etymology card but the corpus carries no etymology atoms")
        elif not in_atoms and not in_morphology:
            reasons.append("etymology card names no term the corpus carries")

    p0 = [f for f in run_doctrinal_checks(body) if f.severity == "P0"]
    if p0:
        reasons.append("doctrinal P0: " + "; ".join(f"{f.check_id}:{f.signature}" for f in p0[:2]))

    return (not reasons), reasons


def _normalize_prose(text: str) -> str:
    """Whitespace- and quote-mark-insensitive form, so a curly quote never fails a match."""
    t = re.sub(r"[‘’“”]", lambda m: "'" if m.group() in "‘’" else '"', text or "")
    t = re.sub(r"[*_`]", "", t)
    return " ".join(t.split()).lower()


def dedupe_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop cards that say the same thing — three lanes will rediscover one idea."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for c in cards:
        fingerprint = " ".join(_normalize_prose(str(c.get("body", ""))).split()[:12])
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        out.append(c)
    return out


# ─── The balance rule ────────────────────────────────────────────────────────
def _kind_ceiling(target_max: int = TARGET_MAX) -> int:
    """The most cards any ONE kind may take — the rule that stops a chapter drifting."""
    return max(1, int(target_max * KIND_CEILING_FRACTION))


def select_balanced(
    cards: list[dict[str, Any]], *, target_min: int = TARGET_MIN, target_max: int = TARGET_MAX
) -> list[dict[str, Any]]:
    """Pick a balanced set from ranked candidates. Order is the ranking; ties keep it.

    Two passes. First a floor pass takes the best card of each kind that has one,
    so a kind the chapter can support is never crowded out by a strong run of
    another. Then a fill pass walks the ranking in order, admitting a card only
    while its kind is under the ceiling. The result honours the ranking wherever
    the balance rule leaves it free to.
    """
    ceiling = _kind_ceiling(target_max)
    chosen: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    taken: set[int] = set()

    for kind in KIND_VOCAB:
        for i, c in enumerate(cards):
            if i in taken or c.get("kind") != kind:
                continue
            if len(chosen) >= target_max:
                break
            chosen.append(c)
            counts[kind] = counts.get(kind, 0) + 1
            taken.add(i)
            break
        if counts.get(kind, 0) >= KIND_FLOOR:
            continue

    for i, c in enumerate(cards):
        if len(chosen) >= target_max:
            break
        if i in taken:
            continue
        kind = str(c.get("kind"))
        if counts.get(kind, 0) >= ceiling:
            continue
        chosen.append(c)
        counts[kind] = counts.get(kind, 0) + 1
        taken.add(i)

    # Last resort: the balanced pool ran dry before the floor. Rather than ship a
    # thin chapter, admit further cards past the per-kind ceiling — and let
    # ``mix_report`` record that the ceiling was breached, so a chapter that only
    # reached its count by leaning on one kind is visible rather than silent.
    if len(chosen) < target_min:
        for i, c in enumerate(cards):
            if len(chosen) >= target_min or i in taken:
                continue
            chosen.append(c)
            counts[str(c.get("kind"))] = counts.get(str(c.get("kind")), 0) + 1
            taken.add(i)

    # Restore ranking order rather than floor-pass order.
    order = {id(c): i for i, c in enumerate(cards)}
    return sorted(chosen, key=lambda c: order.get(id(c), 0))


def mix_report(cards: list[dict[str, Any]]) -> dict[str, Any]:
    """The per-chapter balance summary — what shipped, and whether it obeys the rule."""
    counts: dict[str, int] = {}
    for c in cards:
        counts[str(c.get("kind"))] = counts.get(str(c.get("kind")), 0) + 1
    total = len(cards) or 1
    ceiling = _kind_ceiling()
    return {
        "total": len(cards),
        "kinds": counts,
        "dominant_share": round(max(counts.values()) / total, 2) if counts else 0.0,
        "within_target": TARGET_MIN <= len(cards) <= TARGET_MAX,
        "within_ceiling": all(v <= ceiling for v in counts.values()),
    }


def _default_generator(prompt: str, book_dir: Path, label: str, log) -> str:
    rc, out, err = _run_claude_p_with_retry(
        prompt, timeout=_COMPANION_TIMEOUT, book_dir=book_dir, phase="0book-companion", step=label, log=log
    )
    if rc != 0:
        raise AuthoringError(
            phase="0book-companion",
            message=f"{label}: claude -p rc={rc}: {err[:200]}",
            manual_fallback="Re-run the companion phase; each chapter is regenerated independently.",
        )
    return out or ""


# ─── Proposal: the read-only half ────────────────────────────────────────────
# There is no writer in this module, and that is deliberate rather than tidy
# (Asif, 2026-08-02). The predecessor, `author_phase_book_companion`, regenerated
# every chapter and wrote every file unconditionally — and `_merge_notes` dropped
# each chapter's prior GENERATED notes on the way past. A `propose_only=True`
# flag on that function would have made one boolean the only thing standing
# between a proposal and the destruction of a curated set, which is the shape
# behind docs/rca/2026-07-28-automation-deleted-companion-notes.md.
#
# So the read-only half is EXTRACTED instead. `propose_chapter_cards` returns
# candidates; neither it nor anything it calls opens a file for writing. Propose-
# only is a structural property of the call graph, not a promise in a docstring.
# Filing a kept card is the web Composer's job, through the same append-only
# `upsertNote` a human's own note goes through.

#: Most candidates a single chapter's review list may carry. Not a quality bar —
#: the reviewer's attention is the scarce thing, and a list past this stops being
#: read. `select_balanced` still marks its own picks; see `recommended` below.
PROPOSAL_CAP = 24


def build_proposal_context(book_dir: Path) -> dict[str, Any]:
    """Everything the lanes need that does not vary by chapter.

    Built once and handed to each `propose_chapter_cards` call: the knowledge-base
    atoms and the morphology reference are hundreds of milliseconds to load and are
    identical for every chapter of a book.
    """
    book_dir = Path(book_dir).resolve()
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        raise AuthoringError(
            phase="0book-companion",
            message=f"book.md not found at {book_md}",
            manual_fallback="Compose the book before proposing Companion cards.",
        )
    chapters = book_chapters(book_md.read_text(encoding="utf-8"))
    transcripts = load_transcripts(book_dir)

    ocr = book_dir / "_system" / "source" / "ocr" / "raw-extract.md"
    arabic_src = ocr.read_text(encoding="utf-8") if ocr.exists() else ""

    kb_root = Path(__file__).resolve().parents[2] / "content" / "knowledge-base"
    atoms = _load_kb_atoms(kb_root)
    try:
        from _etymology_corpus import load_morphology_reference

        morphology_ref = load_morphology_reference()
    except Exception:
        morphology_ref = {}

    return {
        "book_dir": book_dir,
        "chapters": chapters,
        "transcripts": transcripts,
        "assignment": map_transcripts_to_chapters(chapters, transcripts),
        "atoms_index": RetrievalIndex(atoms) if atoms else None,
        "morphology_ref": morphology_ref,
        "etymology_terms": frozenset(
            str(a["body"].get("term", "")).lower()
            for a in atoms
            if a.get("type") == "etymology" and isinstance(a.get("body"), dict) and a["body"].get("term")
        ),
        "arabic_allowed": arabic_src
        + "\n"
        + "\n".join(
            str(a["body"].get(k, "")) for a in atoms if isinstance(a.get("body"), dict) for k in ("arabic", "root")
        ),
    }


def propose_chapter_cards(
    ctx: dict[str, Any],
    chapter_key: str,
    *,
    generator: Callable[[str, Path, str, Any], str] | None = None,
    log=print,
) -> dict[str, Any]:
    """Candidate cards for ONE chapter, ranked, gated, and written nowhere.

    `chapter_key` is a `_book_edits.anchor_key` — the Composer's own chapter key.
    An unknown key raises rather than silently proposing for the first chapter,
    because a reviewer cannot tell a mis-anchored list from a bad one.
    """
    book_dir: Path = ctx["book_dir"]
    gen = generator or _default_generator
    ch = next((c for c in ctx["chapters"] if c["key"] == chapter_key), None)
    if ch is None:
        raise AuthoringError(
            phase="0book-companion",
            message=f"no chapter keyed {chapter_key!r} in book.md (have: {[c['key'] for c in ctx['chapters']]})",
            manual_fallback="Re-open the chapter in the Composer; the heading may have been edited.",
        )
    key, title, prose = ch["key"], ch["title"], ch["prose"]
    candidates: list[dict[str, Any]] = []
    dropped: list[str] = []

    def harvest(raw: str, source: dict[str, str] | None) -> None:
        for card in parse_cards(raw):
            card["kind"] = str(card.get("kind") or "").strip().lower()
            ok, reasons = gate_card(
                card,
                prose=prose,
                arabic_src=ctx["arabic_allowed"],
                etymology_terms=ctx["etymology_terms"],
                morphology_ref=ctx["morphology_ref"],
            )
            if not ok:
                dropped.append(f"{card.get('kind')}: {reasons[0]}")
                continue
            if source:
                card["source"] = source
            candidates.append(card)

    # `chapter`, not `manual`. The lane authors from the chapter's own prose; it was
    # stamped `manual` and the site renders that as "You", so every machine card in
    # the reader wore the human's name (90 of them, on one book).
    harvest(gen(chapter_lane_prompt(title, prose), book_dir, f"comp-chapter-{key[:24]}", log), {"provider": "chapter"})

    for stem, _score in ctx["assignment"].get(key, []):
        ref = episode_ref(stem)
        harvest(
            gen(
                podcast_lane_prompt(title, prose, ctx["transcripts"][stem], ref),
                book_dir,
                f"comp-podcast-{ref}-{key[:18]}",
                log,
            ),
            {"provider": "notebooklm", "ref": ref},
        )

    index = ctx["atoms_index"]
    if index is not None:
        selected = index.select(prose, k=_ATOMS_PER_CHAPTER, threshold=_RELEVANCE_THRESHOLD)
        corpus = "\n".join(f"- {corpus_line(s.atom, atom_searchable_text(s.atom)[:260])}" for s in selected)
        if corpus:
            harvest(
                gen(corpus_lane_prompt(title, prose, corpus), book_dir, f"comp-corpus-{key[:24]}", log),
                {"provider": "corpus"},
            )

    candidates = dedupe_cards(candidates)
    if candidates:
        order = rank_order(
            gen(
                judge_prompt(title, candidates, target_max=TARGET_MAX, ceiling=_kind_ceiling()),
                book_dir,
                f"comp-judge-{key[:24]}",
                log,
            ),
            len(candidates),
        )
        candidates = [candidates[i] for i in order]

    # The balance rule ADVISES now; it does not decide. It exists because a model
    # left to itself hands back ten analogies, and its back-stop even breaches its
    # own kind ceiling to reach the minimum — correct when a model has the last
    # word, wrong when a human does. So mark what it would have chosen and show the
    # mix; never withhold a candidate from the person doing the choosing.
    chosen = select_balanced(candidates)
    picked = {id(c) for c in chosen}
    for card in candidates:
        card["recommended"] = id(card) in picked

    candidates = candidates[:PROPOSAL_CAP]
    mix = mix_report(chosen)
    log(
        f"      companion: {title[:44]:46s} {len(candidates):2d} candidates "
        f"({len(chosen)} recommended, {len(dropped)} dropped) · {mix['kinds']}"
    )
    return {
        "chapter": key,
        "title": title,
        "candidates": candidates,
        "dropped": dropped,
        "episodes": [episode_ref(s) for s, _ in ctx["assignment"].get(key, [])],
        "mix": mix,
        "target": {"min": TARGET_MIN, "max": TARGET_MAX, "kind_ceiling_fraction": KIND_CEILING_FRACTION},
    }


def _load_kb_atoms(kb_root: Path) -> list[dict[str, Any]]:
    atoms: list[dict[str, Any]] = []
    for name in ("etymology.jsonl", "quran.jsonl", "hadith.jsonl", "doctrine.jsonl", "quote.jsonl"):
        path = kb_root / name
        if not path.exists():
            continue
        try:
            for raw in path.read_text(encoding="utf-8").splitlines():
                if not raw.strip():
                    continue
                atom = json.loads(raw)
                if disallowed_narrator(atom_narrator(atom)):
                    continue
                atoms.append(atom)
        except Exception:
            continue
    return atoms


# `_merge_notes` and `_as_note` lived here and are DELETED (Asif, 2026-08-02).
#
# They were the write path: `_as_note` minted a note id and stamped
# `generated: true`, and `_merge_notes` kept the human's notes while replacing
# every prior generated one. That ownership dance existed only because two
# writers shared one file. There is now ONE writer — the Composer's apply step,
# through the same append-only `upsertNote` a human's own note goes through — so
# the flag has nothing left to discriminate and the replace has nothing to
# replace. Notes already on disk keep their `generated: true`; nothing reads it
# to decide what to destroy any more.
#
# The whole-book CLI went with them. Keeping it "so the module has a caller"
# would have preserved exactly the second unattended producer this change exists
# to remove; `propose_companion.py` is the caller now.
