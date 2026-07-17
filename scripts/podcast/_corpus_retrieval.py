"""_corpus_retrieval.py — shared per-passage relevance + per-work non-repetition.

The augmentation surfaces (companion-PDF ``_book_augment`` and the podcast
``intelligence/augmenter``) must agree on two things: which corpus atoms are
*relevant* to a given passage, and which have *already been used* within a book
so a reader never meets the same cross-reference twice. Historically the book
path had neither — it reused a fixed head-of-file slice of 40 atoms on every
chapter. This module is the single home for both.

Two pieces:

  * ``RetrievalIndex`` — scores every atom against a passage and returns the most
    relevant, above a threshold, with the score exposed so weak matches can be
    dropped rather than injected. Scoring is **pluggable** (a scorer registry):
    the default ``lexical`` scorer needs no dependency and no network (flat-rate,
    $0), and works better as the corpus gains structure (topic tags, roots). An
    embedding scorer can register later without touching a single caller.

  * ``UsedLedger`` — a per-work record of atom ids already consumed, so an atom
    used once is not injected again *within the same book*. Non-repetition is a
    within-book rule ONLY: a strong verse or hadith is free to reappear in a
    different book, so this ledger is per-book and never consulted across books.

Atoms are plain dicts of the shape ``{"id": str, "type": str, "body": {...}}``
(the JSONL/DB currency), so both the JSONL-backed book path and the DB-backed
podcast path can feed the same code.
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

# ─── Atom text extraction (shared with _book_augment.atom_text semantics) ────
_MD_HEADER_RE = re.compile(r"(?m)^#+\s.*$")
_INLINE_MARKUP_RE = re.compile(r"⟪[^⟫]*⟫")
_TOKEN_RE = re.compile(r"[a-z][a-z'-]{2,}")
_QREF_RE = re.compile(r"\bq\s*(\d{1,3})\s*[:.]\s*(\d{1,3})\b", re.IGNORECASE)

# Very common English words carry no retrieval signal; drop them so the overlap
# score reflects meaningful shared vocabulary, not stop-word coincidence.
_STOPWORDS = frozenset("""
the a an and or but if then else of to in on at by for with without from into
onto is are was were be been being it its this that these those he she they them
his her their our your my we you i as not no nor so than too very can will would
should could may might must have has had do does did done not which who whom whose
what when where why how all any both each few more most other some such only own
same over under again further once here there when about against between through
during before after above below up down out off then them theirs itself upon
""".split())


def atom_searchable_text(atom: dict[str, Any]) -> str:
    """The English text of an atom, cleaned to clean prose for scoring/grounding.

    Mirrors ``_book_augment.atom_text``: atoms store their prose at
    ``body.text_en`` (doctrine/hadith/quran/quote share this), older shapes use a
    top-level field. Markdown headers and inline ``⟪ar:…⟫`` markup are stripped.
    """
    body = atom.get("body") if isinstance(atom.get("body"), dict) else {}
    text = (
        body.get("text_en")
        or atom.get("text")
        or atom.get("arabic")
        or atom.get("translation")
        or body.get("translation")
        or ""
    )
    text = _MD_HEADER_RE.sub("", text)
    text = _INLINE_MARKUP_RE.sub("", text)
    return " ".join(text.split())


def _atom_keywords(atom: dict[str, Any]) -> list[str]:
    """Extra high-signal keywords beyond the prose: topic tags + root/derivatives.

    These are the fields the lexical scorer weights above ordinary prose overlap,
    because a shared topic tag or Arabic root is a much stronger relevance signal
    than a shared common word. Absent fields simply contribute nothing.
    """
    body = atom.get("body") if isinstance(atom.get("body"), dict) else {}
    out: list[str] = []
    tags = body.get("topic_tags") or atom.get("topic_tags") or []
    if isinstance(tags, (list, tuple)):
        out.extend(str(t) for t in tags)
    for key in ("root_transliteration", "term"):
        v = body.get(key)
        if v:
            out.append(str(v))
    for d in (body.get("derivatives") or []):
        if isinstance(d, dict) and d.get("term"):
            out.append(str(d["term"]))
    return [w.strip().lower() for w in out if str(w).strip()]


def _atom_qrefs(atom: dict[str, Any]) -> set[tuple[int, int]]:
    """Quran (surah, ayah) references an atom carries, as a set for exact overlap."""
    body = atom.get("body") if isinstance(atom.get("body"), dict) else {}
    refs: set[tuple[int, int]] = set()
    if atom.get("type") == "quran" or ("surah" in body and "ayah" in body):
        try:
            refs.add((int(body["surah"]), int(body["ayah"])))
        except (KeyError, TypeError, ValueError):
            pass
    for r in (body.get("quran_refs") or []):
        m = _QREF_RE.search(str(r)) or re.search(r"(\d{1,3})[:.](\d{1,3})", str(r))
        if m:
            refs.add((int(m.group(1)), int(m.group(2))))
    return refs


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOPWORDS]


def _passage_qrefs(text: str) -> set[tuple[int, int]]:
    return {(int(a), int(b)) for a, b in _QREF_RE.findall(text or "")}


# ─── Scored result ──────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ScoredAtom:
    atom: dict[str, Any]
    score: float

    @property
    def id(self) -> str:
        return str(self.atom.get("id", ""))


# ─── Pluggable scorer registry (extensibility: embeddings can drop in later) ─
# A scorer is prepared once over the atom pool, then queried per passage. This is
# the abstraction an embedding scorer needs too (precompute atom vectors in
# ``prepare``, cosine in ``score``) — so swapping mechanisms never touches a caller.
_SCORERS: dict[str, Callable[[], "Scorer"]] = {}


def register_scorer(name: str) -> Callable[[Callable[[], "Scorer"]], Callable[[], "Scorer"]]:
    def _wrap(factory: Callable[[], "Scorer"]) -> Callable[[], "Scorer"]:
        _SCORERS[name] = factory
        return factory
    return _wrap


def get_scorer(name: str) -> "Scorer":
    if name not in _SCORERS:
        raise KeyError(f"unknown relevance scorer {name!r}; registered: {sorted(_SCORERS)}")
    return _SCORERS[name]()


class Scorer:
    """Interface: ``prepare`` once over the atom pool, then ``score`` per passage."""

    def prepare(self, atoms: list[dict[str, Any]]) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def score(self, passage: str) -> list[float]:  # pragma: no cover - interface
        raise NotImplementedError


class LexicalScorer(Scorer):
    """Cosine TF-IDF overlap + topic-tag and Quran-ref boosts.

    Similarity is the **cosine** of the passage and atom TF-IDF vectors, so it is
    length-invariant: a long doctrine atom no longer outscores a short verse just
    for having more words — only genuinely shared, distinctive vocabulary raises
    the score. Rare shared tokens (high IDF) count for more than common ones. On
    top of the cosine base, an exact topic-tag or verse-reference match adds a
    modest bonus (a far stronger relevance signal than prose overlap). Scores stay
    in ``[0, 1]`` so the threshold is corpus-stable.
    """

    _TAG_BONUS = 0.12
    _REF_BONUS = 0.20

    def prepare(self, atoms: list[dict[str, Any]]) -> None:
        self._atoms = atoms
        self._tokens: list[set[str]] = []
        self._keywords: list[set[str]] = []
        self._qrefs: list[set[tuple[int, int]]] = []
        df: dict[str, int] = {}
        for atom in atoms:
            toks = set(_tokenize(atom_searchable_text(atom)))
            self._tokens.append(toks)
            self._keywords.append(set(_atom_keywords(atom)))
            self._qrefs.append(_atom_qrefs(atom))
            for t in toks:
                df[t] = df.get(t, 0) + 1
        n = max(1, len(atoms))
        # Smoothed IDF: log((N+1)/(df+1)) + 1 — always positive, rewards rarity.
        self._idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
        # Precompute each atom's TF-IDF vector norm (tf=1 over the token set).
        self._norms = [
            math.sqrt(sum(self._idf.get(t, 1.0) ** 2 for t in toks)) or 1e-9
            for toks in self._tokens
        ]

    def score(self, passage: str) -> list[float]:
        p_tokens = set(_tokenize(passage))
        p_lower = (passage or "").lower()
        p_refs = _passage_qrefs(passage)
        p_norm = math.sqrt(sum(self._idf.get(t, 1.0) ** 2 for t in p_tokens)) or 1e-9
        out: list[float] = []
        for i in range(len(self._atoms)):
            shared = p_tokens & self._tokens[i]
            dot = sum(self._idf.get(t, 1.0) ** 2 for t in shared)
            cosine = dot / (p_norm * self._norms[i])
            tag_hits = sum(1 for kw in self._keywords[i] if kw and kw in p_lower)
            ref_hits = len(p_refs & self._qrefs[i])
            score = cosine + self._TAG_BONUS * min(2, tag_hits) + self._REF_BONUS * min(2, ref_hits)
            out.append(min(1.0, score))
        return out


@register_scorer("lexical")
def _make_lexical() -> Scorer:
    return LexicalScorer()


# ─── The index façade callers use ───────────────────────────────────────────
class RetrievalIndex:
    """Prepare a scorer over an atom pool once; query the top matches per passage.

    Build ONE index per run (the corpus is shared across chapters), then call
    ``select`` per chapter — far cheaper than rescoring the whole corpus from
    scratch each time via the module-level convenience.
    """

    def __init__(self, atoms: Iterable[dict[str, Any]], *, scorer: str = "lexical") -> None:
        self.atoms = [a for a in atoms if isinstance(a, dict) and a.get("id")]
        self._scorer = get_scorer(scorer)
        self._scorer.prepare(self.atoms)

    def select(
        self,
        passage: str,
        *,
        k: int,
        threshold: float,
        exclude_ids: Iterable[str] = (),
    ) -> list[ScoredAtom]:
        """The ``k`` most-relevant atoms scoring >= ``threshold``, minus ``exclude_ids``.

        Returned best-first. Below-threshold atoms are never returned, so a chapter
        with no genuinely-related atom yields an empty list (no forced injection).
        """
        exclude = {str(x) for x in exclude_ids}
        scores = self._scorer.score(passage)
        ranked = sorted(
            (
                ScoredAtom(atom, sc)
                for atom, sc in zip(self.atoms, scores)
                if sc >= threshold and str(atom.get("id")) not in exclude
            ),
            key=lambda s: s.score,
            reverse=True,
        )
        return ranked[:k]


def select_relevant(
    atoms: Iterable[dict[str, Any]],
    passage: str,
    *,
    k: int,
    threshold: float,
    exclude_ids: Iterable[str] = (),
    scorer: str = "lexical",
) -> list[ScoredAtom]:
    """One-shot convenience: build an index and query it once."""
    return RetrievalIndex(atoms, scorer=scorer).select(
        passage, k=k, threshold=threshold, exclude_ids=exclude_ids
    )


# ─── Per-work non-repetition ledger (within-book only) ──────────────────────
class UsedLedger:
    """Per-book record of consumed atom ids so nothing repeats *within* a book.

    Scope is deliberately per-book: repetition is a within-book defect only, so a
    strong atom is free to reappear in a different book and this ledger is never
    consulted across books. Multiple surfaces of ONE book (e.g. the companion PDF
    across its chapters) share one file and accumulate into it as they run.

    A single augment pass processes every chapter in one call, so it starts from a
    clean in-memory set (``reset``) and persists at the end — keeping re-runs
    idempotent (a second run is not starved by the first run's record).
    """

    SCHEMA = "podcast.augment-used-ledger/v1"
    DEFAULT_NAME = "augment-used-ledger.json"

    def __init__(self, book_dir: Path, *, name: str = DEFAULT_NAME) -> None:
        self._path = Path(book_dir) / "_system" / name
        self._used: set[str] = set()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> "UsedLedger":
        """Populate the in-memory set from disk (cross-surface accumulation)."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._used = {str(x) for x in (data.get("used") or [])}
        except (OSError, json.JSONDecodeError, AttributeError):
            self._used = set()
        return self

    def reset(self) -> "UsedLedger":
        self._used = set()
        return self

    def used(self) -> set[str]:
        return set(self._used)

    def record(self, atom_ids: Iterable[str]) -> None:
        self._used.update(str(x) for x in atom_ids if str(x))
        self._persist()

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"schema": self.SCHEMA, "used": sorted(self._used)},
                       indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )


def attribute_used(note_text: str, candidates: list[dict[str, Any]], *, min_overlap: int = 2) -> list[str]:
    """Which candidate atoms a generated note actually drew on (for the ledger).

    A note is generated from ``k`` candidate atoms but usually grounds in only a
    few. Marking only the atoms whose distinctive tokens actually surface in the
    note (>= ``min_overlap`` shared non-stopword tokens, OR a shared verse ref)
    keeps non-repetition keyed to what the reader SEES, so later chapters are not
    starved of good atoms that were shown but never used.
    """
    note_tokens = set(_tokenize(note_text))
    note_refs = _passage_qrefs(note_text)
    note_lower = (note_text or "").lower()
    used: list[str] = []
    for atom in candidates:
        aid = str(atom.get("id", ""))
        if not aid:
            continue
        shared = note_tokens & set(_tokenize(atom_searchable_text(atom)))
        kw_hit = any(kw and kw in note_lower for kw in _atom_keywords(atom))
        if len(shared) >= min_overlap or kw_hit or (note_refs & _atom_qrefs(atom)):
            used.append(aid)
    return used
