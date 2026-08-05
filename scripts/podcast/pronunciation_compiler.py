#!/usr/bin/env python3
"""pronunciation_compiler.py — glossary.yml -> versioned ElevenLabs PLS dictionary.

Step 4 of Audio Engine v2. Deterministically compiles a book's
`_system/glossary.yml` (the Phase-0c phonetic<->Arabic overlay) into an
ElevenLabs ALIAS-RULE pronunciation dictionary (PLS lexicon format — alias
rules work on ALL models/languages; phoneme rules are legacy-English-only
and are deliberately NOT used).

Lifecycle:
    compile (pure, deterministic, sorted)  ->  upload ONCE per book  ->
    pin {dictionary_id, version_id} in BOOK_DIR/_system/pronunciation-dictionary.json
    ->  every render call passes the pinned locator.

A glossary CHANGE recompiles to a different PLS hash -> a fresh upload ->
the state file records the new pin and appends the old one to `history`
(the ledger). Renders always pin an exact version; nothing floats.

Arabic-script recitation SCAFFOLD (halt point H2): per-book flag
`elevenlabs_arabic_recitation: true` in series-config.yaml (DEFAULT OFF).
When ON, `compile_turns_for_render` substitutes glossary phonetic forms
with their native Arabic script at the script-COMPILE layer for engines that
support it. Persisted Islamic chapter sources also carry Arabic script beside
romanized terms via `inject_chapter_arabic.py`; phonetic respelling still lives
in the glossary / pronunciation dictionary, not inline chapter prose.

Usage (manual):
    python3 scripts/podcast/pronunciation_compiler.py <book-slug>            # compile + show plan
    python3 scripts/podcast/pronunciation_compiler.py <book-slug> --upload   # ensure uploaded + pinned
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))

STATE_FILENAME = "pronunciation-dictionary.json"

# Common English loanwords that must NEVER get alias rules: English speakers
# (and the v3 voices) already say them naturally, and forcing a respelling
# produces mangled audio ("Imam" -> "e-Maam", observed live 2026-06-12).
# Matches the WHOLE grapheme case-insensitively — multi-word names that merely
# contain one of these ("Abd Allah") keep their rules.
LOANWORD_SKIP = frozenset(
    {
        "imam",
        "imams",
        "allah",
        "quran",
        "koran",
        "sunnah",
        "sunna",
        "hadith",
        "ahadith",
        "islam",
        "muslim",
        "muslims",
    }
)

# Personal-name connectors: a glossary entry containing one of these as a
# standalone token is a person name (e.g. "Ja'far ibn Mansur al-Yaman"), which is
# REFERENTIAL — never recited in Arabic (the user wants teaching terms in Arabic,
# not author/transmitter names; names are pronounced fine via the alias dictionary).
_NAME_CONNECTORS = frozenset({"ibn", "bin", "ibni", "abu", "abi", "abu'l", "umm", "bint", "al-yaman"})


def _is_proper_name(phonetic: str) -> bool:
    """Deterministic: True when the glossary phonetic looks like a personal name
    (carries a name connector token). Doctrinal terms (tawhid, hujjah, zuhd) have
    none and return False, so they ARE eligible for Arabic-script recitation."""
    toks = [t.strip(".,").lower() for t in str(phonetic).split()]
    return any(t in _NAME_CONNECTORS for t in toks)


# ─── Human curation (glossary schema v2) ─────────────────────────────────────
# Optional per-entry decision set by Asif in the Astro reader before audio:
#   decision: keep | fix_phonetic | correct_arabic | replace_english
#     keep / absent      -> original fields (byte-identical to schema v1)
#     fix_phonetic       -> corrected_phonetic overrides the match key + alias grapheme
#     correct_arabic     -> corrected_arabic overrides the recited script
#     replace_english    -> term is left in English (no Arabic recited)
# The model never authors Arabic; the human curates the verified overlay, the
# render injects it. A glossary with no decisions behaves exactly as before.
_DECISION_KEEP = "keep"
_DECISION_FIX_PHONETIC = "fix_phonetic"
_DECISION_CORRECT_ARABIC = "correct_arabic"
_DECISION_REPLACE_ENGLISH = "replace_english"


def resolve_curation(entry: dict) -> dict:
    """Apply a glossary entry's human decision; return effective render fields.

    Returns {"phonetic": match-key/alias-grapheme, "arabic": script to recite,
    "drop_arabic": True when the human chose English-only}. Absent/keep decision
    yields the original phonetic + arabic_script unchanged (no behavior drift)."""
    decision = str(entry.get("decision") or _DECISION_KEEP).strip().lower()
    phonetic = str(entry.get("phonetic") or "").strip()
    arabic = str(entry.get("arabic_script") or "").strip()
    if decision == _DECISION_FIX_PHONETIC:
        corrected = str(entry.get("corrected_phonetic") or "").strip()
        if corrected:
            phonetic = corrected
    elif decision == _DECISION_CORRECT_ARABIC:
        corrected = str(entry.get("corrected_arabic") or "").strip()
        if corrected:
            arabic = corrected
    return {
        "phonetic": phonetic,
        "arabic": arabic,
        "drop_arabic": decision == _DECISION_REPLACE_ENGLISH,
    }


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_glossary_entries(book_dir: Path) -> list[dict]:
    """Entries from BOOK_DIR/_system/glossary.yml ([] when absent/empty)."""
    gpath = Path(book_dir) / "_system" / "glossary.yml"
    if not gpath.exists():
        return []
    try:
        import yaml

        data = yaml.safe_load(gpath.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    entries = data.get("entries") or []
    return [e for e in entries if isinstance(e, dict)]


def _usable_rules(entries: list[dict]) -> list[tuple[str, str]]:
    """(grapheme, alias) pairs worth shipping: the script's phonetic form ->

    the audio respelling. Skips entries with no audio_phonetic, trivial
    rules where the alias equals the grapheme (case/punct-insensitively),
    and LOANWORD_SKIP graphemes (whole-grapheme match)."""

    def _norm(s: str) -> str:
        return "".join(c for c in s.lower() if c.isalnum())

    rules: dict[str, str] = {}
    for e in entries:
        # Teaching-relevance balance: a dynasty / place / passing reference
        # (classified `incidental`) needs no pinned pronunciation — keep the PLS
        # dictionary a teaching glossary, not a historical index. Names + other
        # referential terms keep their alias so they are still said correctly.
        if str(e.get("teaching_relevance") or "").strip().lower() == "incidental":
            continue
        cur = resolve_curation(e)
        # fix_phonetic moves the grapheme to the corrected form so the alias rule
        # matches what the human says appears in the text. keep/absent -> original.
        grapheme = cur["phonetic"]
        alias = str(e.get("audio_phonetic") or "").strip()
        if not grapheme or not alias:
            continue
        if _norm(grapheme) == _norm(alias):
            continue  # trivial respelling adds nothing
        if grapheme.lower() in LOANWORD_SKIP:
            continue  # common English loanword — natural reading beats an alias
        rules.setdefault(grapheme, alias)  # first occurrence wins, like the glossary
    return sorted(rules.items())  # deterministic order


def compile_pls(entries: list[dict], *, lang: str = "en-US") -> str:
    """Deterministic PLS lexicon (alias rules only). Same entries -> same bytes."""
    rules = _usable_rules(entries)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<lexicon version="1.0"',
        '         xmlns="http://www.w3.org/2005/01/pronunciation-lexicon"',
        f'         alphabet="ipa" xml:lang="{lang}">',
    ]
    for grapheme, alias in rules:
        lines.append("  <lexeme>")
        lines.append(f"    <grapheme>{escape(grapheme)}</grapheme>")
        lines.append(f"    <alias>{escape(alias)}</alias>")
        lines.append("  </lexeme>")
    lines.append("</lexicon>")
    return "\n".join(lines) + "\n"


def pls_sha256(pls_text: str) -> str:
    return hashlib.sha256(pls_text.encode("utf-8")).hexdigest()


# ─── State (the per-book pin + history ledger) ───────────────────────────────


def state_path(book_dir: Path) -> Path:
    return Path(book_dir) / "_system" / STATE_FILENAME


def read_dictionary_state(book_dir: Path) -> dict:
    p = state_path(book_dir)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write_dictionary_state(book_dir: Path, state: dict) -> None:
    p = state_path(book_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def dictionary_locator(book_dir: Path) -> dict | None:
    """The pinned locator for render calls, or None when no dictionary exists.

    Shape matches the API: {"pronunciation_dictionary_id": ..., "version_id": ...}.
    """
    st = read_dictionary_state(book_dir)
    if st.get("dictionary_id") and st.get("version_id"):
        return {
            "pronunciation_dictionary_id": st["dictionary_id"],
            "version_id": st["version_id"],
        }
    return None


def ensure_dictionary(book_dir: Path, client=None, *, log=print) -> dict | None:
    """Compile the glossary; upload IF the compiled PLS is new; return the

    pinned locator (or None when the book has no usable glossary rules).

    Render-once discipline: an unchanged glossary never re-uploads — the
    existing pin is returned as-is. A changed glossary uploads a fresh
    dictionary and the previous pin moves to `history` (never deleted, so
    every past render's ledger entry stays resolvable)."""
    entries = load_glossary_entries(book_dir)
    pls = compile_pls(entries)
    digest = pls_sha256(pls)
    n_rules = pls.count("<lexeme>")

    if n_rules == 0:
        log("  [pronunciation] no usable glossary rules — rendering without a dictionary")
        return None

    st = read_dictionary_state(book_dir)
    if st.get("pls_sha256") == digest and st.get("dictionary_id") and st.get("version_id"):
        log(
            f"  [pronunciation] glossary unchanged — pinned dictionary "
            f"{st['dictionary_id']} v{st['version_id']} ({n_rules} rules)"
        )
        return dictionary_locator(book_dir)

    if client is None:
        from _elevenlabs import ElevenLabsClient

        client = ElevenLabsClient()

    name = f"{Path(book_dir).name}-glossary"
    log(f"  [pronunciation] uploading {n_rules}-rule PLS dictionary {name!r} ...")
    dict_id, version_id = client.create_pronunciation_dictionary(
        name=name, pls_text=pls, description=f"podcast-factory glossary compile {digest[:12]}"
    )

    history = list(st.get("history") or [])
    if st.get("dictionary_id"):
        history.append(
            {
                "dictionary_id": st.get("dictionary_id"),
                "version_id": st.get("version_id"),
                "pls_sha256": st.get("pls_sha256"),
                "compiled_at": st.get("compiled_at"),
                "entry_count": st.get("entry_count"),
            }
        )
    _write_dictionary_state(
        book_dir,
        {
            "engine": "elevenlabs",
            "dictionary_id": dict_id,
            "version_id": version_id,
            "pls_sha256": digest,
            "compiled_at": _utc_now(),
            "entry_count": n_rules,
            "history": history,
        },
    )
    log(f"  [pronunciation] pinned dictionary {dict_id} v{version_id}")
    return dictionary_locator(book_dir)


# ─── Arabic-script recitation scaffold (H2 — default OFF) ────────────────────


def arabic_recitation_enabled(book_dir: Path) -> bool:
    """Per-book flag `elevenlabs_arabic_recitation` (default False), GATED to
    Arabic-capable engines.

    The NotebookLM dialogue-render route does not receive this extra render-time
    Arabic substitution; persisted Islamic chapter sources already carry visible
    Arabic via inject_chapter_arabic.py. The flag only controls extra audio-render
    substitution on Arabic-capable engines. Flips only after Asif approves the H2
    two-variant audible sample."""
    cfg = Path(book_dir) / "_system" / "series-config.yaml"
    if not cfg.exists():
        return False
    try:
        import yaml

        data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
        if not bool(data.get("elevenlabs_arabic_recitation")):
            return False
    except Exception:
        return False
    # Engine gate: Arabic reaches the audio only on an Arabic-capable engine.
    try:
        from _audio_engines import audio_engine_for_book

        return bool(audio_engine_for_book(book_dir).supports_arabic_script)
    except Exception:
        return True  # flag set but engine unresolvable — honor the flag


def _glossary_term_subs(book_dir: Path) -> list[tuple[str, str]]:
    """(phonetic, arabic_script) pairs to recite, longest-first. EXCLUDES
    loanwords (natural English reading beats a substitution) and personal names
    (referential — pronounced via the alias dictionary, never recited).

    Teaching-relevance balance: once the glossary carries `teaching_relevance`
    (set by teaching_relevance_classifier.py), ONLY `teaching`-classified terms
    are recited in Arabic — the doctrine is spoken in Arabic, while dynasties,
    places, transmitter names, and other referential noise stay in plain speech.
    A glossary with NO classification recites every non-name / non-loanword term
    exactly as before (backward compatible)."""
    entries = load_glossary_entries(book_dir)
    classified = any(str(e.get("teaching_relevance") or "").strip() for e in entries)
    subs = []
    for e in entries:
        if classified and str(e.get("teaching_relevance") or "").strip().lower() != "teaching":
            continue  # recite teaching terms only — leave referential noise unrecited
        cur = resolve_curation(e)
        if cur["drop_arabic"]:
            continue  # human chose replace-with-English — no Arabic recited
        phonetic = cur["phonetic"]
        arabic = cur["arabic"]
        if not phonetic or not arabic:
            continue
        if phonetic.lower() in LOANWORD_SKIP or _is_proper_name(phonetic):
            continue
        subs.append((phonetic, arabic))
    subs.sort(key=lambda kv: len(kv[0]), reverse=True)
    return subs


def compile_turns_for_render(book_dir: Path, turns: list, *, log=None) -> list:
    """Script-COMPILE-layer transform applied just before chunking/synthesis.

    Flag OFF (default): identity — romanized text + the pronunciation dictionary
    carry pronunciation. Flag ON: the ElevenLabs render gains VERIFIED Arabic
    from two deterministic sources, never from the model:
      1. Quran VERSES — every resolvable citation gets the verbatim KQur Arabic
         spliced in after it (scripts/podcast/_quran_recitation.py).
      2. Key TERMS — glossary phonetic forms carrying an `arabic_script` value
         are replaced with the native script (loanwords + personal names skipped).
    eleven_v3 handles mixed-language text. Persisted chapters are handled by
    inject_chapter_arabic.py; this transform exists only in the render path and
    never writes chapter or script artifacts."""
    if not arabic_recitation_enabled(book_dir):
        return list(turns)
    from _dialogue_script import Turn
    from _quran_recitation import inject_recitations

    term_subs = _glossary_term_subs(book_dir)
    out = []
    for t in turns:
        # 1. Verbatim Quran recitation after each resolvable citation (verified
        #    source; unresolved citations are left in English).
        text = inject_recitations(t.text, log=log)
        # 2. Key-term native script (longest-first; names/loanwords already skipped).
        # Use letter-boundary lookahead/lookbehind so short phonetics (e.g. "itra")
        # cannot match inside English words ("arb[itra]ry" -> "arbعترةry" was the bug).
        for phonetic, arabic in term_subs:
            pattern = r"(?<![a-zA-Z])" + re.escape(phonetic) + r"(?![a-zA-Z])"
            text = re.sub(pattern, arabic, text)
        out.append(Turn(speaker=t.speaker, text=text))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Compile (and optionally upload+pin) a book's pronunciation dictionary.")
    ap.add_argument("slug", help="book slug (any bucket)")
    ap.add_argument("--upload", action="store_true", help="ensure the compiled dictionary is uploaded + pinned")
    args = ap.parse_args()

    from _paths import find_content

    found = find_content(args.slug)
    if not found:
        print(f"ERROR: no content directory matches slug {args.slug!r}", file=sys.stderr)
        return 2
    book_dir = found[2]

    entries = load_glossary_entries(book_dir)
    pls = compile_pls(entries)
    n_rules = pls.count("<lexeme>")
    print(f"glossary entries: {len(entries)}  usable alias rules: {n_rules}")
    print(f"compiled PLS sha256: {pls_sha256(pls)[:16]}...")
    st = read_dictionary_state(book_dir)
    if st:
        print(f"pinned: {st.get('dictionary_id')} v{st.get('version_id')} (hash {str(st.get('pls_sha256'))[:16]}...)")
    if args.upload:
        loc = ensure_dictionary(book_dir)
        print(f"locator: {loc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
