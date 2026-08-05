#!/usr/bin/env python3
"""arabic_integrity.py — hard, deterministic Arabic-preservation gate.

The reader's promise for an audio-sourced Islamic book is that Arabic script
(Quran verses, hadith, named terms) is restored from canonical/verified sources
and then NEVER silently altered. Every LLM editorial/refine/enrich pass is a
place where a verse could be re-spelled, dropped, or hallucinated. This module
makes that promise enforceable:

  1. snapshot — BEFORE the first LLM mutation, fingerprint every Arabic span in
     the LLM-mutable artifacts (the English-refined layers + glossary
     `arabic_script` + knowledge-base atoms). Each span is NFC-normalized,
     bidi-stripped, and content-addressed (sha256). Stored as a MULTISET so a
     verse that legitimately recurs N times is conserved, not deduped — this
     survives the heavy reorganization phase 0a-synthesize performs.

  2. verify <phase> — AFTER an LLM pass, recompute the multiset and diff it
     against the baseline. Differences are FORGIVEN only when they match the
     allowlist (canonical Quran injection by restore_arabic + verified atoms, or
     a human glossary schema-v2 curation decision). Anything left over is a
     FORBIDDEN silent mutation/drop/invention → exit 3 (halt the phase).

Invariant (R-ARABIC-INTEGRITY, _rules.py): the ONLY sanctioned Arabic mutators
are canonical injection and the Astro phonetic-view curation. Zero LLM, zero
network, idempotent, book-agnostic — same posture as the other R-* gates.

CLI:
  python3 scripts/podcast/arabic_integrity.py snapshot <slug> [--force]
  python3 scripts/podcast/arabic_integrity.py verify   <slug> --phase 0a|0b|0e
  python3 scripts/podcast/arabic_integrity.py status   <slug> [--json]

Exit codes: 0 = clean / allowlisted, 3 = forbidden Arabic mutation, 2 = error.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from _paths import REPO_ROOT, content_dir, find_content
from _rules import (
    ARABIC_FINGERPRINT_VERSION,
    R_ARABIC_BIDI_STRIP,
    R_ARABIC_INTEGRITY,
    R_ARABIC_TASHKEEL,
    emit_finding,
    phase_capabilities,
)

# Single source of truth for Arabic detection — never re-declare the range.
from restore_arabic import _ARABIC_RE, _has_arabic

SNAPSHOT_NAME = "arabic-fingerprints.json"
REPORT_NAME = "arabic-integrity-report.md"
EXIT_OK = 0
EXIT_FORBIDDEN = 3
EXIT_ERROR = 2

# Arabic punctuation that may sit INSIDE a multi-word span (so a verse stays one
# span instead of fragmenting per word). Comma, semicolon, question mark, full
# stop, and the ASCII space are span-internal connective glue.
_SPAN_GLUE = set(" \t،؛؟۔")
# A PROTECTED span (Quran verse / hadith / named term) always has >= 2 Arabic
# letters. A lone isolated Arabic character (e.g. an illustrative letter `ھ`, or a
# stray glyph) can never be a protected verse/term — counting it as a span produces
# false "invented-span" flags. So spans below this many Arabic LETTERS are not
# tracked. This does NOT weaken protection of real verses/hadith/terms.
MIN_ARABIC_LETTERS = 2
_BIDI_STRIP_SET = set(R_ARABIC_BIDI_STRIP)
_TASHKEEL_SET: set[int] = set()
for _lo, _hi in R_ARABIC_TASHKEEL:
    _TASHKEEL_SET.update(range(_lo, _hi + 1))


# ─────────────────────────────────────────────────────────────────────────────
# Normalization
# ─────────────────────────────────────────────────────────────────────────────
def normalize_arabic_span(s: str) -> str:
    """Canonical comparison form: NFC, bidi/joiner controls stripped, edge-trimmed.

    Used IDENTICALLY at snapshot and verify time so comparison is apples-to-apples.
    Tashkeel (harakat) is PRESERVED here — the full vowelled form is the primary
    identity; `skeleton()` derives the vowel-stripped variant for drift reporting.
    """
    s = unicodedata.normalize("NFC", s)
    s = "".join(ch for ch in s if ord(ch) not in _BIDI_STRIP_SET)
    return s.strip()


def skeleton(s: str) -> str:
    """Vowel-stripped (tashkeel-removed) form, for AI-VOWEL-DRIFT classification."""
    s = normalize_arabic_span(s)
    return "".join(ch for ch in s if ord(ch) not in _TASHKEEL_SET)


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def extract_spans(text: str) -> list[str]:
    """Return every maximal Arabic span in ``text`` (normalized, non-empty).

    A span is a maximal run that contains at least one Arabic codepoint and is
    glued across interior spaces / Arabic punctuation, so a multi-word verse is
    one span. Runs with no Arabic letter (pure punctuation/space) are dropped.
    """
    spans: list[str] = []
    buf: list[str] = []
    has_letter = False

    def _flush() -> None:
        nonlocal has_letter
        if buf and has_letter:
            norm = normalize_arabic_span("".join(buf))
            # Require >= MIN_ARABIC_LETTERS actual Arabic letters: a lone glyph is
            # never a protected verse/hadith/term, and flagging it is a false positive.
            n_letters = sum(1 for ch in norm if _ARABIC_RE.match(ch))
            if norm and _has_arabic(norm) and n_letters >= MIN_ARABIC_LETTERS:
                spans.append(norm)
        buf.clear()
        has_letter = False

    for ch in text:
        if _ARABIC_RE.match(ch):
            buf.append(ch)
            has_letter = True
        elif buf and ch in _SPAN_GLUE:
            # interior glue — keep accumulating, but don't let trailing glue leak
            buf.append(ch)
        else:
            _flush()
    _flush()
    return spans


# ─────────────────────────────────────────────────────────────────────────────
# Book resolution + artifact scoping
# ─────────────────────────────────────────────────────────────────────────────
def _resolve_book_dir(slug: str) -> Path | None:
    hit = find_content(slug)
    if hit:
        return hit[2]
    cand = content_dir(slug)
    return cand if cand.exists() else None


def _content_profile(book_dir: Path) -> str | None:
    """Best-effort content_profile from meta.yml, else series-config.yaml, else None."""
    import yaml

    for rel in ("meta.yml", "_system/series-config.yaml"):
        p = book_dir / rel
        if p.is_file():
            try:
                data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            prof = data.get("content_profile") or data.get("profile")
            if prof:
                return str(prof)
    return None


def _is_islamic(book_dir: Path) -> bool:
    """Gate scope: only islamic_scholarly books carry restored Arabic to protect.

    Audio Islamic books frequently have no meta.yml yet at 0a-synthesize time;
    fall back to category=lectures (the audio-Islamic default) so the gate is
    active during early phases, matching the 0c/0e skip ladder.
    """
    prof = _content_profile(book_dir)
    if prof:
        return phase_capabilities(prof).bucket == "Islamic"
    state = book_dir / "_system" / "orchestrator-state.json"
    if state.is_file():
        try:
            data = json.loads(state.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        cat = (data.get("category") or "").strip().lower()
        # Islamic categories per _paths._CATEGORY_TO_BUCKET.
        return cat in {"books", "lectures", "letters", "asbaaq", "interviews", "articles", "documents"}
    return True  # historical default: run the full scholarly pipeline


# Artifacts each phase may have mutated. Glossary + atoms are checked at EVERY
# phase (an LLM pass must never touch them). Prose layers are phase-scoped.
_PHASE_PROSE: dict[str, tuple[str, ...]] = {
    "0a": ("_system/unified-book.md", "_system/source/text/refined-english.md"),
    "0b": ("_system/source/text/refined-english.md", "_system/unified-book.md"),
    "0e": (),  # chapters/* globbed dynamically below
    # SNAPSHOT scope: Arabic legitimately present before any LLM pass, so it must
    # include the SOURCE. Every book before `spiritual-ethos` got its Arabic from
    # its own OCR, making refined-english the first artifact to carry any; that
    # book's capture is English with none, and its 999 runs were woven in from
    # lecture transcripts, so 0b carrying them faithfully read as 999 inventions.
    "all": ("_system/source/text/raw-extract.md", "_system/unified-book.md", "_system/source/text/refined-english.md"),
}


def _prose_artifacts(book_dir: Path, phase: str) -> list[Path]:
    out: list[Path] = []
    for rel in _PHASE_PROSE.get(phase, ()):
        p = book_dir / rel
        if p.is_file():
            out.append(p)
    if phase in ("0e", "all"):
        out.extend(sorted((book_dir / "chapters").glob("ch*.txt")))
    return out


def _glossary_spans(book_dir: Path) -> list[dict[str, Any]]:
    """Arabic in glossary.yml `arabic_script` fields → fingerprint records."""
    import yaml

    gpath = book_dir / "_system" / "glossary.yml"
    if not gpath.is_file():
        return []
    try:
        data = yaml.safe_load(gpath.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    recs: list[dict[str, Any]] = []
    for e in data.get("entries") or []:
        if not isinstance(e, dict):
            continue
        script = (e.get("arabic_script") or "").strip()
        if not _has_arabic(script):
            continue
        norm = normalize_arabic_span(script)
        recs.append(
            _record(
                norm,
                "glossary.yml#arabic_script",
                {"entry_phonetic": e.get("phonetic") or ""},
                "glossary-curated",
                e.get("phonetic") or "",
            )
        )
    return recs


def _atom_spans() -> list[dict[str, Any]]:
    """Arabic on knowledge-base atoms (quran/hadith/quote) → fingerprint records.

    Atoms are a shared corpus, not per-book, but their Arabic is canonical/verified
    and must never be rewritten by a book's LLM pass — so they belong in the snapshot.
    """
    import sqlite3

    db = REPO_ROOT / "content" / "knowledge-base" / "knowledge.db"
    if not db.is_file():
        return []
    recs: list[dict[str, Any]] = []
    try:
        conn = sqlite3.connect(str(db))
        rows = conn.execute("SELECT id, type, body FROM atoms WHERE type IN ('quran','hadith','quote')").fetchall()
        conn.close()
    except Exception:
        return []
    for atom_id, atype, raw in rows:
        try:
            body = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            continue
        ar = (body.get("arabic") or "").strip()
        if not _has_arabic(ar):
            continue
        prov = (
            "atom-sdk-verified"
            if body.get("arabic_source") == "model-sdk-verified"
            else ("canonical-quran" if atype == "quran" else "atom-preexisting")
        )
        recs.append(
            _record(
                normalize_arabic_span(ar),
                f"atom:{atype}:{atom_id}",
                {"atom_id": atom_id, "atom_type": atype},
                prov,
                (body.get("text_en") or body.get("text") or "")[:80],
            )
        )
    return recs


def _record(norm: str, source_artifact: str, anchor: dict[str, Any], provenance: str, context: str) -> dict[str, Any]:
    return {
        "hash": _hash(norm),
        "skeleton_hash": _hash(skeleton(norm)),
        "nfc_text": norm,
        "source_artifact": source_artifact,
        "anchor": anchor,
        "provenance": provenance,
        "context_excerpt": (context or "")[:80],
    }


def _prose_records(book_dir: Path, phase: str) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    for p in _prose_artifacts(book_dir, phase):
        rel = p.relative_to(book_dir).as_posix()
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for span in extract_spans(line):
                recs.append(_record(span, rel, {"line": i}, "unknown-preexisting", line.strip()[:80]))
    return recs


def collect_records(book_dir: Path, phase: str) -> list[dict[str, Any]]:
    """All Arabic fingerprint records in scope for ``phase`` (prose + glossary + atoms)."""
    return _prose_records(book_dir, phase) + _glossary_spans(book_dir) + _atom_spans()


# ─────────────────────────────────────────────────────────────────────────────
# Snapshot
# ─────────────────────────────────────────────────────────────────────────────
def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _snapshot_path(book_dir: Path) -> Path:
    return book_dir / "_system" / SNAPSHOT_NAME


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    import os
    import tempfile

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def snapshot(slug: str, *, force: bool = False) -> int:
    book_dir = _resolve_book_dir(slug)
    if book_dir is None:
        print(f"arabic_integrity: book not found: {slug}", file=sys.stderr)
        return EXIT_ERROR
    if not _is_islamic(book_dir):
        print(f"arabic_integrity: snapshot skipped (non-Islamic profile) for {slug}")
        return EXIT_OK
    spath = _snapshot_path(book_dir)
    if spath.exists() and not force:
        print(f"arabic_integrity: snapshot already exists ({spath.name}); use --force to rebaseline")
        return EXIT_OK
    recs = collect_records(book_dir, "all")
    by_hash = Counter(r["hash"] for r in recs)
    payload = {
        "schema_version": 1,
        "book_slug": slug,
        "rule_id": R_ARABIC_INTEGRITY,
        "fingerprint_version": ARABIC_FINGERPRINT_VERSION,
        "snapshot_phase": "pre-0a",
        "ts_created": _utc(),
        "spans": recs,
        "by_hash": dict(by_hash),
    }
    _atomic_write_json(spath, payload)
    print(f"arabic_integrity: snapshot wrote {len(recs)} spans ({len(by_hash)} distinct) → _system/{SNAPSHOT_NAME}")
    return EXIT_OK


def load_snapshot(book_dir: Path) -> dict[str, Any] | None:
    p = _snapshot_path(book_dir)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Allowlist (sanctioned mutations)
# ─────────────────────────────────────────────────────────────────────────────
def build_allowlist(book_dir: Path) -> dict[str, set[str]]:
    """Return the set of normalized-Arabic hashes that MAY legitimately appear or
    disappear post-pass, keyed by sanction kind.

    - ``added``: canonical Arabic the restore path is permitted to INJECT — every
      atom `arabic` value + glossary `arabic_script` (curation-resolved). A new
      span post-pass is forgiven only if its hash is here.
    - ``dropped``: spans a human curation decision sanctioned removing — glossary
      entries marked `replace_english` / drop. Their disappearance is forgiven.
    """
    added: set[str] = set()
    dropped: set[str] = set()

    # Canonical/verified atom + glossary Arabic = sanctioned injections.
    for rec in _atom_spans() + _glossary_spans(book_dir):
        added.add(rec["hash"])

    # Curation decisions on the glossary (schema v2). resolve_curation is the
    # single source both the audio renderer and the Astro overlay read.
    try:
        import yaml
        from pronunciation_compiler import resolve_curation  # type: ignore
    except Exception:
        resolve_curation = None  # type: ignore
        yaml = None  # type: ignore
    gpath = book_dir / "_system" / "glossary.yml"
    if resolve_curation and yaml and gpath.is_file():
        try:
            data = yaml.safe_load(gpath.read_text(encoding="utf-8")) or {}
        except Exception:
            data = {}
        for e in data.get("entries") or []:
            if not isinstance(e, dict):
                continue
            try:
                resolved = resolve_curation(e)
            except Exception:
                resolved = e
            decision = (e.get("decision") or e.get("curation_decision") or "").strip()
            # A corrected Arabic value is a sanctioned ADD.
            corrected = (resolved.get("arabic_script") if isinstance(resolved, dict) else "") or ""
            if _has_arabic(corrected):
                added.add(_hash(normalize_arabic_span(corrected)))
            orig = e.get("arabic_script") or ""
            if decision in ("replace_english", "drop_arabic", "drop") and _has_arabic(orig):
                dropped.add(_hash(normalize_arabic_span(orig)))
    return {"added": added, "dropped": dropped}


# ─────────────────────────────────────────────────────────────────────────────
# Verify
# ─────────────────────────────────────────────────────────────────────────────
def _classify_drift(
    missing_hash: str, base_recs: list[dict[str, Any]], now_recs: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """If a missing span has a present near-twin (same skeleton, diff vowels),
    return a vowel-drift descriptor; else None."""
    base = next((r for r in base_recs if r["hash"] == missing_hash), None)
    if not base:
        return None
    twin = next(
        (r for r in now_recs if r["skeleton_hash"] == base["skeleton_hash"] and r["hash"] != missing_hash), None
    )
    if twin:
        return {
            "baseline": base["nfc_text"],
            "present": twin["nfc_text"],
            "artifact": base["source_artifact"],
            "anchor": base["anchor"],
        }
    return None


def verify(slug: str, phase: str) -> int:
    book_dir = _resolve_book_dir(slug)
    if book_dir is None:
        print(f"arabic_integrity: book not found: {slug}", file=sys.stderr)
        return EXIT_ERROR
    if not _is_islamic(book_dir):
        return EXIT_OK  # no-op for non-Islamic books
    snap = load_snapshot(book_dir)
    if snap is None:
        # No baseline → nothing protected yet. Snapshot opportunistically and pass.
        print(f"arabic_integrity: no baseline for {slug}; taking one now (verify is a no-op this pass)")
        snapshot(slug)
        return EXIT_OK

    base_recs: list[dict[str, Any]] = snap.get("spans", [])
    base_count = Counter(r["hash"] for r in base_recs)
    now_recs = collect_records(book_dir, phase)
    now_count = Counter(r["hash"] for r in now_recs)
    allow = build_allowlist(book_dir)

    missing = base_count - now_count  # spans that vanished (or dropped in count)
    appeared = now_count - base_count  # spans that materialized (or grew)

    forbidden_drops: list[dict[str, Any]] = []
    vowel_drifts: list[dict[str, Any]] = []
    for h, n in missing.items():
        if h in allow["dropped"]:
            continue
        drift = _classify_drift(h, base_recs, now_recs)
        rec = next((r for r in base_recs if r["hash"] == h), {})
        if drift:
            vowel_drifts.append({**drift, "count": n})
        else:
            forbidden_drops.append(
                {
                    "nfc_text": rec.get("nfc_text", ""),
                    "artifact": rec.get("source_artifact", ""),
                    "anchor": rec.get("anchor", {}),
                    "count": n,
                }
            )

    forbidden_new: list[dict[str, Any]] = []
    for h, n in appeared.items():
        if h in allow["added"]:
            continue
        # A materialized span whose skeleton twins a baseline span is the OTHER side
        # of a vowel-drift (already reported under missing) — not a separate invention.
        rec = next((r for r in now_recs if r["hash"] == h), {})
        twin_in_base = any(r["skeleton_hash"] == rec.get("skeleton_hash") for r in base_recs)
        if twin_in_base:
            continue
        forbidden_new.append(
            {
                "nfc_text": rec.get("nfc_text", ""),
                "artifact": rec.get("source_artifact", ""),
                "anchor": rec.get("anchor", {}),
                "count": n,
            }
        )

    _write_report(
        book_dir,
        slug,
        phase,
        forbidden_drops,
        forbidden_new,
        vowel_drifts,
    )
    violations = len(forbidden_drops) + len(forbidden_new) + len(vowel_drifts)
    if violations:
        for kind, items in (
            ("AI-DROP", forbidden_drops),
            ("AI-INVENT", forbidden_new),
            ("AI-VOWEL-DRIFT", vowel_drifts),
        ):
            for it in items:
                emit_finding(
                    repo_root=REPO_ROOT,
                    source="arabic-integrity",
                    source_version=ARABIC_FINGERPRINT_VERSION,
                    book=slug,
                    check_id=kind,
                    severity="P0",
                    signature=f"{kind}:{it.get('artifact', '')}:{(it.get('nfc_text') or it.get('baseline') or '')[:24]}",
                    file=str(it.get("artifact", "")),
                    context_excerpt=(it.get("nfc_text") or it.get("baseline") or "")[:300],
                    resolution="flagged",
                )
        print(
            f"arabic_integrity: ✗ {violations} forbidden Arabic change(s) in phase {phase} — see _system/{REPORT_NAME}",
            file=sys.stderr,
        )
        return EXIT_FORBIDDEN
    print(f"arabic_integrity: ✓ phase {phase} clean ({len(base_recs)} baseline spans verified)")
    return EXIT_OK


def _write_report(
    book_dir: Path,
    slug: str,
    phase: str,
    drops: list[dict[str, Any]],
    invents: list[dict[str, Any]],
    drifts: list[dict[str, Any]],
) -> Path:
    p = book_dir / "_system" / REPORT_NAME
    lines = [
        f"# Arabic Integrity Report — {slug}",
        "",
        f"- Rule: {R_ARABIC_INTEGRITY} (fingerprint v{ARABIC_FINGERPRINT_VERSION})",
        f"- Phase verified: `{phase}`",
        f"- Generated: {_utc()}",
        f"- Verdict: {'PASS' if not (drops or invents or drifts) else 'FAIL'}",
        "",
        "Forbidden = an Arabic span mutated/dropped/invented by an LLM pass with no",
        "sanctioning provenance (canonical injection or glossary curation).",
        "",
    ]

    def _tbl(title: str, items: list[dict[str, Any]], cols: list[str]) -> None:
        lines.append(f"## {title} ({len(items)})")
        if not items:
            lines.append("")
            lines.append("_None._")
            lines.append("")
            return
        lines.append("")
        lines.append("| " + " | ".join(cols) + " |")
        lines.append("|" + "|".join("---" for _ in cols) + "|")
        for it in items:
            lines.append("| " + " | ".join(str(it.get(c.lower().replace(" ", "_"), "")) for c in cols) + " |")
        lines.append("")

    _tbl("AI-DROP — spans removed without sanction", drops, ["NFC_text", "Artifact", "Anchor", "Count"])
    _tbl("AI-INVENT — spans introduced without sanction", invents, ["NFC_text", "Artifact", "Anchor", "Count"])
    _tbl("AI-VOWEL-DRIFT — tashkeel altered on a protected span", drifts, ["Baseline", "Present", "Artifact", "Anchor"])
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def gate_arabic_integrity(workspace: Path) -> tuple[bool, str]:
    """Finalize-gate entry (G13). Returns (passed, message).

    Verifies the FINAL artifacts against the baseline snapshot with the full
    allowlist. Non-Islamic books / books with no snapshot pass vacuously.
    """
    if not _is_islamic(workspace):
        return True, "n/a (non-Islamic profile)"
    if load_snapshot(workspace) is None:
        return True, "n/a (no Arabic baseline snapshot)"
    slug = workspace.name
    rc = verify(slug, "all")
    if rc == EXIT_OK:
        return True, "Arabic spans byte-stable against baseline"
    return False, f"forbidden Arabic mutation(s) — see _system/{REPORT_NAME}"


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
def _status(slug: str, as_json: bool) -> int:
    book_dir = _resolve_book_dir(slug)
    if book_dir is None:
        print(f"arabic_integrity: book not found: {slug}", file=sys.stderr)
        return EXIT_ERROR
    snap = load_snapshot(book_dir)
    info = {
        "slug": slug,
        "islamic": _is_islamic(book_dir),
        "has_snapshot": snap is not None,
        "baseline_spans": len(snap.get("spans", [])) if snap else 0,
        "distinct": len(snap.get("by_hash", {})) if snap else 0,
        "snapshot_ts": snap.get("ts_created") if snap else None,
    }
    if as_json:
        print(json.dumps(info, ensure_ascii=False, indent=2))
    else:
        for k, v in info.items():
            print(f"  {k:<16} {v}")
    return EXIT_OK


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("snapshot", help="Fingerprint Arabic spans BEFORE the first LLM pass.")
    sp.add_argument("slug")
    sp.add_argument("--force", action="store_true", help="rebaseline even if a snapshot exists")
    vp = sub.add_parser("verify", help="Verify Arabic spans unchanged after an LLM pass.")
    vp.add_argument("slug")
    vp.add_argument("--phase", required=True, choices=["0a", "0b", "0e", "all"])
    stp = sub.add_parser("status", help="Show baseline snapshot state.")
    stp.add_argument("slug")
    stp.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.cmd == "snapshot":
        return snapshot(args.slug, force=args.force)
    if args.cmd == "verify":
        return verify(args.slug, args.phase)
    if args.cmd == "status":
        return _status(args.slug, args.json)
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
