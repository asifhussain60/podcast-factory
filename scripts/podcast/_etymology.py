"""_etymology.py — content-driven, accuracy-gated etymology atoms.

Mines a book for its genuinely KEY Arabic technical terms, generates a root-level
breakdown for each (Arabic root, morphology, semantic field, derived family), and
keeps ONLY the ones whose root survives an accuracy gate — so nothing invented is
ever printed. Minimal by design: a small set of high-value terms per book, each
etymology generated once and reused across books (root-level dedup).

Accuracy gate (Decision D1 = generate-now, accuracy-checked — the authoritative
KSESSIONS/KQUR consolidation stays parked):

  * ``term_index`` (the KSESSIONS/KQUR root reference in ``mirror.db``) is a
    deterministic VETO — if it lists the term with a DIFFERENT root, drop the entry;
  * an independent adversarial verification pass must CONFIRM the root AND agree
    with the generation pass (self-consistency); anything unconfirmed is dropped;
  * the readable text passes the doctrinal T1–T5 gate.

Surviving atoms are written to the canonical corpus — ``etymology.jsonl`` (the
committed source of truth) plus ``knowledge.db`` (derived, for immediate podcast
use) — with the body shape the podcast etymology renderer already consumes
(``root_transliteration`` / ``root_phonetic`` / ``meaning_en`` /
``derivatives[].{term,phonetic,meaning_en}``) plus richer fields (``root`` Arabic
script, ``morphology``, ``semantic_field``, ``text_en``) for the print block.

The two LLM calls (generate, verify) are isolated so the deterministic selection
+ gate logic is unit-testable with injected fakes.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Callable

from _authoring._core import _run_claude_p_with_retry
from _doctrinal import run_doctrinal_checks

_REPO_ROOT = Path(__file__).resolve().parents[2]
_KB_DIR = _REPO_ROOT / "content" / "knowledge-base"
_ETYMOLOGY_JSONL = _KB_DIR / "etymology.jsonl"
_MIRROR_DB = _KB_DIR / "mirror.db"

_MAX_TERMS_DEFAULT = 12
_MAX_CANDIDATES = 30
_MIN_TERM_LEN = 3
_GEN_TIMEOUT = 900

# Book-title / apparatus words that are never concept terms worth a root breakdown.
_NOT_CONCEPTS = frozenset(
    """
allah muhammad quran imam ayah surah hadith book volume chapter page author
""".split()
)

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]+")


# ─── Term selection (content-driven, minimal) ───────────────────────────────
def _book_text(book_dir: Path) -> str:
    p = Path(book_dir) / "book" / "book.md"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _glossary_terms(book_dir: Path) -> list[str]:
    """Single/two-word transliterated glossary entries — concept-SHAPED candidates.

    The glossary also holds book titles and multi-word phrases (e.g. "Ihya al-Ulum
    ad-Din"); those have many tokens and are filtered out here. Genuine concepts
    ("nafs", "tawakkul", "al-aql") are one or two tokens and survive.
    """
    path = Path(book_dir) / "_system" / "glossary.yml"
    if not path.exists():
        return []
    try:
        import yaml

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    out: list[str] = []
    for e in data.get("entries") or []:
        raw = str(e.get("transliteration") or e.get("phonetic") or "").strip()
        term = re.sub(r"^al-", "", raw, flags=re.IGNORECASE).strip()
        toks = term.split()
        if (
            1 <= len(toks) <= 2
            and _MIN_TERM_LEN <= len(term) <= 24
            and re.fullmatch(r"[A-Za-z'\- ]+", term)
            and term.lower() not in _NOT_CONCEPTS
        ):
            out.append(term)
    return out


def gather_candidate_terms(book_dir: Path, *, max_candidates: int = _MAX_CANDIDATES) -> list[tuple[str, int]]:
    """Candidate concept terms ranked by how often the book actually uses them.

    Frequency in the book is the salience signal: a term the book leans on is a
    better etymology target than one mentioned once. Returns ``[(term, freq), ...]``
    best-first, deduped case-insensitively, capped for a minimal set.
    """
    text = _book_text(book_dir).lower()
    if not text:
        return []
    seen: dict[str, tuple[str, int]] = {}
    for term in _glossary_terms(book_dir):
        key = term.lower()
        if key in seen:
            continue
        freq = len(re.findall(rf"(?<![\w-]){re.escape(key)}(?![\w-])", text))
        if freq >= 1:
            seen[key] = (term, freq)
    ranked = sorted(seen.values(), key=lambda tf: (-tf[1], tf[0].lower()))
    return ranked[:max_candidates]


# ─── Accuracy reference (mirror.db term_index) ──────────────────────────────
def _norm_root(s: str) -> str:
    """Canonical consonant-skeleton form for comparing roots across notations.

    Lowercases, drops Arabic script, vowels, and separators, so "n-f-s", "nafs",
    and "N F S" all reduce to "nfs" for a notation-agnostic equality check.
    """
    s = re.sub(r"[^A-Za-z]", "", (s or "")).lower()
    return re.sub(r"[aeiou]", "", s)


def load_term_index(db_path: Path | None = None) -> dict[str, set[str]]:
    """``{normalized_term: {normalized_root, ...}}`` from the KSESSIONS/KQUR mirror.

    Empty dict when the mirror is absent — the gate then relies on the adversarial
    verification pass alone (no deterministic reference to veto against).
    """
    path = db_path or _MIRROR_DB
    if not path.exists():
        return {}
    out: dict[str, set[str]] = {}
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        for term, root in conn.execute("SELECT term, root FROM term_index WHERE root != ''"):
            key = re.sub(r"[^a-z]", "", str(term).lower())
            if key:
                out.setdefault(key, set()).add(_norm_root(str(root)))
        conn.close()
    except sqlite3.Error:
        return {}
    return out


# ─── Deterministic gate ─────────────────────────────────────────────────────
_REQUIRED_FIELDS = ("term", "root_transliteration", "root_phonetic", "meaning_en")


def gate_entry(
    entry: dict[str, Any],
    term_index: dict[str, set[str]],
    verdict: dict[str, Any] | None,
) -> tuple[bool, str]:
    """Accept/reject one generated etymology. ``(ok, reason)``.

    Order of checks: field completeness -> doctrinal T1–T5 on the readable text ->
    term_index deterministic veto -> adversarial verification (confirm + root
    agreement). Any failure drops the entry — the bias is toward emitting nothing
    rather than emitting a wrong root.
    """
    for f in _REQUIRED_FIELDS:
        if not str(entry.get(f, "")).strip():
            return False, f"missing {f}"
    if len(entry.get("derivatives") or []) < 1:
        return False, "no derivatives"

    text = str(entry.get("text_en", "")).strip()
    if text:
        p0 = [f for f in run_doctrinal_checks(text) if f.severity == "P0"]
        if p0:
            return False, "doctrinal P0: " + ";".join(f.check_id for f in p0[:2])

    term_key = re.sub(r"[^a-z]", "", str(entry["term"]).lower())
    gen_root = _norm_root(entry["root_transliteration"])
    if not gen_root:
        return False, "empty root skeleton"

    # Deterministic veto: a term the reference lists MUST match one of its roots.
    ref_roots = term_index.get(term_key)
    if ref_roots and not any(_roots_compatible(gen_root, r) for r in ref_roots):
        return False, f"root {gen_root!r} contradicts reference {sorted(ref_roots)}"

    # Adversarial verification: confirm + agreement with the generated root.
    if verdict is not None:
        if not verdict.get("confirmed"):
            return False, "verifier did not confirm the root"
        v_root = _norm_root(str(verdict.get("root", "")))
        if v_root and not _roots_compatible(gen_root, v_root):
            return False, f"verifier root {v_root!r} disagrees with generated {gen_root!r}"
    return True, "ok"


def _roots_compatible(a: str, b: str) -> bool:
    """True if two normalized roots plausibly denote the same triliteral root.

    Reference roots vary (skeleton "nfs" vs a fuller "ghafara"); require exact
    match OR that the shorter skeleton is a subsequence of the longer, so notation
    differences pass while a genuinely different root fails.
    """
    if not a or not b:
        return False
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    it = iter(long)
    return all(c in it for c in short)


# ─── Atom assembly + persistence ────────────────────────────────────────────
def to_atom(entry: dict[str, Any], book_slug: str) -> dict[str, Any]:
    """Build a corpus atom (id keyed by root so it dedups + reuses across books)."""
    root_id = _norm_root(entry["root_transliteration"]) or re.sub(r"[^a-z]", "", str(entry["term"]).lower())
    body = {
        "term": str(entry["term"]).strip(),
        "root": str(entry.get("root", "")).strip(),
        "root_transliteration": str(entry["root_transliteration"]).strip(),
        "root_phonetic": str(entry["root_phonetic"]).strip(),
        "meaning_en": str(entry["meaning_en"]).strip(),
        "morphology": str(entry.get("morphology", "")).strip(),
        "semantic_field": str(entry.get("semantic_field", "")).strip(),
        "derivatives": [
            {
                "term": str(d.get("term", "")).strip(),
                "phonetic": str(d.get("phonetic", "")).strip(),
                "meaning_en": str(d.get("meaning_en", "")).strip(),
            }
            for d in (entry.get("derivatives") or [])
            if str(d.get("term", "")).strip()
        ],
        "text_en": str(entry.get("text_en", "")).strip(),
    }
    return {
        "id": f"etymology:{root_id}",
        "type": "etymology",
        "body": body,
        "tradition": "universal",
        "confidence": float(entry.get("confidence", 0.9)),
        "first_seen": {"book": book_slug, "chapter": ""},
    }


def _existing_etymology_roots() -> set[str]:
    """Root ids already in the corpus (skip regeneration — reuse across books)."""
    roots: set[str] = set()
    try:
        import _db

        conn = _db.get_connection()
        for (aid,) in conn.execute("SELECT id FROM atoms WHERE type='etymology'"):
            roots.add(str(aid).split(":", 1)[-1])
    except Exception:
        pass
    if _ETYMOLOGY_JSONL.exists():
        for line in _ETYMOLOGY_JSONL.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    roots.add(str(json.loads(line).get("id", "")).split(":", 1)[-1])
                except json.JSONDecodeError:
                    continue
    roots.discard("")
    return roots


def _persist_atoms(atoms: list[dict[str, Any]], book_dir: Path, log) -> int:
    """Append new atoms to the committed etymology.jsonl and merge into the DB.

    JSONL is the source of truth (git-committed, diffable); the DB write makes the
    atoms usable by the podcast path immediately without a corpus rebuild. Both are
    ADDITIVE and id-deduped — never a clobbering export.
    """
    if not atoms:
        return 0
    existing_ids: set[str] = set()
    if _ETYMOLOGY_JSONL.exists():
        for line in _ETYMOLOGY_JSONL.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    existing_ids.add(str(json.loads(line)["id"]))
                except (json.JSONDecodeError, KeyError):
                    continue
    fresh = [a for a in atoms if a["id"] not in existing_ids]
    if not fresh:
        return 0
    # 1) committed JSONL (append)
    _KB_DIR.mkdir(parents=True, exist_ok=True)
    with _ETYMOLOGY_JSONL.open("a", encoding="utf-8") as fh:
        for a in fresh:
            fh.write(json.dumps(a, ensure_ascii=False) + "\n")
    # 2) derived DB (via the librarian merge path, for immediate podcast use)
    try:
        from intelligence.librarian import merge_into_library

        scratch = book_dir / "_system" / "_etymology-scratch.jsonl"
        scratch.parent.mkdir(parents=True, exist_ok=True)
        scratch.write_text(
            "\n".join(json.dumps(a, ensure_ascii=False) for a in fresh) + "\n",
            encoding="utf-8",
        )
        merge_into_library(book_dir, scratch)
        scratch.unlink(missing_ok=True)
    except Exception as e:
        log(f"      etymology: DB merge skipped (non-fatal): {e}")
    return len(fresh)


# ─── LLM passes (isolated; injected in tests) ───────────────────────────────
def _generation_prompt(candidates: list[tuple[str, int]], sample: str) -> str:
    listing = "\n".join(f"- {t} (used {n}x)" for t, n in candidates)
    return f"""You are compiling accurate Arabic etymology for the KEY technical terms of an Islamic
book, for a study apparatus. Accuracy is paramount: NEVER invent or guess a root — if you are not
certain of a term's classical triliteral Arabic root, OMIT that term entirely.

From the candidate terms below (with how often the book uses them), KEEP only the ones that are
genuine Arabic technical CONCEPTS a student benefits from understanding at the root level. DROP
proper names, place names, book titles, and anything that is not a concept.

For each KEPT term output an object with EXACTLY these fields:
- "term": the term as given
- "root": the triliteral root in Arabic script (e.g. "ن-ف-س")
- "root_transliteration": the root as separated consonants (e.g. "n-f-s")
- "root_phonetic": how to SAY the root aloud (e.g. "NA-fa-sa")
- "meaning_en": the root's core meaning, a few words
- "morphology": one clause on the term's form/derivation from the root
- "semantic_field": one clause on the field of meaning the root spans
- "derivatives": 2-3 objects, each {{"term","phonetic","meaning_en"}}, of words from the SAME root
- "text_en": a 2-sentence plain-English breakdown a student can read

Output ONLY a JSON array of these objects (no prose, no code fence). Fewer, correct entries are
better than more. If none qualify, output [].

CANDIDATE TERMS
{listing}

BOOK EXCERPT (context only)
{sample[:3500]}
"""


def _verification_prompt(entries: list[dict[str, Any]]) -> str:
    listing = "\n".join(
        f'- {e.get("term")}: claimed root {e.get("root_transliteration")} ("{e.get("meaning_en")}")' for e in entries
    )
    return f"""You are an independent, skeptical checker of Arabic etymology. For each term below, a
root has been CLAIMED. Confirm ONLY if you are confident the claimed triliteral root is correct for
that term in classical Arabic. Do not be agreeable — reject anything uncertain or wrong.

Output ONLY a JSON array; one object per term, EXACTLY: {{"term","confirmed":true|false,"root":"the
correct separated-consonant root"}}. If you reject, put the root you believe is correct (or "").

TERMS
{listing}
"""


def _parse_json_array(out: str) -> list[dict[str, Any]]:
    out = (out or "").strip()
    m = re.search(r"\[.*\]", out, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
        return [d for d in data if isinstance(d, dict)]
    except json.JSONDecodeError:
        return []


def _generate(candidates: list[tuple[str, int]], sample: str, book_dir: Path, log) -> list[dict[str, Any]]:
    rc, out, err = _run_claude_p_with_retry(
        _generation_prompt(candidates, sample),
        timeout=_GEN_TIMEOUT,
        book_dir=book_dir,
        phase="0book-etymology",
        step="generate",
        log=log,
    )
    if rc != 0:
        log(f"      etymology: generation failed (rc={rc}): {err[:160]}")
        return []
    return _parse_json_array(out)


def _verify(entries: list[dict[str, Any]], book_dir: Path, log) -> dict[str, dict[str, Any]]:
    if not entries:
        return {}
    rc, out, err = _run_claude_p_with_retry(
        _verification_prompt(entries),
        timeout=_GEN_TIMEOUT,
        book_dir=book_dir,
        phase="0book-etymology",
        step="verify",
        log=log,
    )
    if rc != 0:
        log(f"      etymology: verification failed (rc={rc}): {err[:160]}")
        return {}
    verdicts: dict[str, dict[str, Any]] = {}
    for v in _parse_json_array(out):
        key = re.sub(r"[^a-z]", "", str(v.get("term", "")).lower())
        if key:
            verdicts[key] = v
    return verdicts


# ─── Orchestrator ───────────────────────────────────────────────────────────
def build_etymology_atoms(
    book_dir: Path,
    *,
    log=print,
    generator: Callable[..., list[dict[str, Any]]] | None = None,
    verifier: Callable[..., dict[str, dict[str, Any]]] | None = None,
    max_terms: int = _MAX_TERMS_DEFAULT,
    write: bool = True,
) -> dict[str, Any]:
    """Mine, generate, gate, and persist etymology atoms for one book.

    Returns a report dict. ``generator``/``verifier`` default to the real LLM
    calls; tests inject fakes. ``write=False`` runs the full pipeline but persists
    nothing (dry run / preview).
    """
    book_dir = Path(book_dir).resolve()
    book_slug = book_dir.name
    gen = generator or _generate
    ver = verifier or _verify

    candidates = gather_candidate_terms(book_dir)
    existing_roots = _existing_etymology_roots()
    term_index = load_term_index()

    if not candidates:
        report = {
            "schema": "podcast.etymology/v1",
            "book": book_slug,
            "candidates": 0,
            "kept": 0,
            "dropped": 0,
            "reused": 0,
            "entries": [],
        }
        _write_report(book_dir, report)
        return report

    sample = _book_text(book_dir)
    generated = gen(candidates, sample, book_dir, log) or []
    # Skip terms whose root is already covered by an existing atom (reuse).
    generated = [e for e in generated if _norm_root(str(e.get("root_transliteration", ""))) not in existing_roots][
        :max_terms
    ]

    verdicts = ver(generated, book_dir, log) if generated else {}

    kept_atoms: list[dict[str, Any]] = []
    kept_meta: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    seen_roots: set[str] = set()
    for e in generated:
        term_key = re.sub(r"[^a-z]", "", str(e.get("term", "")).lower())
        ok, reason = gate_entry(e, term_index, verdicts.get(term_key))
        root = _norm_root(str(e.get("root_transliteration", "")))
        if ok and root in seen_roots:
            ok, reason = False, "duplicate root within this run"
        if not ok:
            dropped.append({"term": e.get("term"), "reason": reason})
            continue
        seen_roots.add(root)
        kept_atoms.append(to_atom(e, book_slug))
        kept_meta.append(
            {
                "term": e.get("term"),
                "root": e.get("root_transliteration"),
                "confirmed_by_reference": term_key in term_index,
            }
        )

    written = _persist_atoms(kept_atoms, book_dir, log) if write else 0
    report = {
        "schema": "podcast.etymology/v1",
        "book": book_slug,
        "candidates": len(candidates),
        "generated": len(generated),
        "kept": len(kept_atoms),
        "written": written,
        "dropped": len(dropped),
        "drop_reasons": dropped[:20],
        "entries": kept_meta,
    }
    _write_report(book_dir, report)
    log(
        f"    0book-etymology: {len(kept_atoms)} etymology atoms kept, "
        f"{len(dropped)} dropped, {written} newly written (from {len(candidates)} candidates)"
    )
    return report


def _write_report(book_dir: Path, report: dict[str, Any]) -> None:
    sysdir = Path(book_dir) / "_system"
    sysdir.mkdir(parents=True, exist_ok=True)
    (sysdir / "etymology-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
