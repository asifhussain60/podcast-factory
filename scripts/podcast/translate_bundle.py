#!/usr/bin/env python3
"""translate_bundle.py — bridges Phase 0a-translate for source_extractor bundles.

A bundle intaken via `intake_book.py --from-bundle` lands at
phase=0a-translate when source_language != "en". This script does the
translation half so the book can advance to Phase 0b refine.

What it does:

1. Validates state: source_kind=bundle, phase=0a-translate, source_language!=en.
2. Reads _system/source/text/raw-extract.md.
3. Tokenizes ⟪…⟫ markers as HTML void elements so Translator preserves them
   (the inline Arabic + Quran citation markers must not be translated —
   they're the actual Arabic verses + structural citation anchors).
4. Calls Azure Translator (existing _azure.translate_text helper) with
   text_type="html" so the placeholders survive the round-trip.
5. Restores markers in the translated text.
6. Backs up the source-language version to raw-extract.<lang>.md.
7. Writes the English version to raw-extract.md (the canonical name
   downstream phases expect).
8. Updates orchestrator-state.json: phase=0b, last_completed_phase=0a,
   adds phases.0a.translated_at + translation_provider="azure".
9. Appends translator details to _system/source/text/_provenance.json.

Usage:
  python3 scripts/podcast/translate_bundle.py --slug <book-slug>
  python3 scripts/podcast/translate_bundle.py --slug <book-slug> --dry-run

Known limitations:
- Bold/italic markdown emphasis (`**bold**`, `*italic*`) may be reformatted
  by Translator. Acceptable for Phase 0b refine to clean up.
- The Urdu translations inside `⟪ar-quote:…⟫` companion lines are translated
  (which is the goal); inline Arabic in `⟪ar:…⟫` is preserved.
- Azure Translator quality on Urdu→English is good but not perfect. Phase 0b
  refine + per-chapter authoring add the polish.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from _paths import REPO_ROOT

WORKSPACE_BOOKS = REPO_ROOT / "content" / "drafts"


def _die(msg: str) -> int:
    print(f"translate_bundle: {msg}", file=sys.stderr)
    return 2


def _info(msg: str) -> None:
    print(msg)


# Inline marker pattern: matches ⟪…⟫ in any of the three known shapes
# (ar:, ar-quote:, quran). Non-greedy inside; ⟫ is the close bracket.
_MARKER_RE = re.compile(r"⟪[^⟪⟫]*⟫")


def _protect_markers(text: str) -> tuple[str, list[str]]:
    """Replace every ⟪…⟫ with `<m id="N"/>` and return (rewritten_text, markers).

    `<m id="N"/>` is an HTML self-closing void element. Azure Translator with
    text_type="html" preserves it across the round-trip; inside Arabic content
    cannot be confused for translatable prose."""
    markers: list[str] = []

    def _sub(m: re.Match) -> str:
        markers.append(m.group(0))
        return f'<m id="{len(markers) - 1}"/>'

    rewritten = _MARKER_RE.sub(_sub, text)
    return rewritten, markers


_PLACEHOLDER_RE = re.compile(r'<m\s+id="(\d+)"\s*/>')


def _restore_markers(text: str, markers: list[str]) -> str:
    """Reverse of _protect_markers."""
    def _sub(m: re.Match) -> str:
        idx = int(m.group(1))
        if 0 <= idx < len(markers):
            return markers[idx]
        return m.group(0)  # leave alone if out of range
    return _PLACEHOLDER_RE.sub(_sub, text)


def translate_bundle(slug: str, *, dry_run: bool = False) -> int:
    book_dir = WORKSPACE_BOOKS / slug
    if not book_dir.is_dir():
        return _die(f"book workspace not found: {book_dir}")

    state_path = book_dir / "_system" / "orchestrator-state.json"
    if not state_path.exists():
        return _die(f"orchestrator-state.json missing at {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))

    if state.get("source_kind") != "bundle":
        return _die(
            f"source_kind is {state.get('source_kind')!r}, not 'bundle'. "
            f"This script is only for source_extractor bundles."
        )
    if state.get("phase") != "0a-translate":
        return _die(
            f"phase is {state.get('phase')!r}, not '0a-translate'. "
            f"Bundle either does not need translation (source_language=en) "
            f"or has already advanced past Phase 0a-translate."
        )

    source_language = state.get("source_language", "")
    if source_language == "en":
        return _die("source_language is 'en' — nothing to translate.")
    if not source_language:
        return _die("state.source_language is missing.")

    raw_extract = book_dir / "_system" / "source" / "text" / "raw-extract.md"
    if not raw_extract.exists():
        return _die(f"raw-extract.md missing at {raw_extract}")

    backup = (
        book_dir / "_system" / "source" / "text"
        / f"raw-extract.{source_language}.md"
    )
    if backup.exists() and not dry_run:
        _info(f"==> Existing backup at {backup.relative_to(REPO_ROOT)}; "
              f"will overwrite raw-extract.md but leave backup intact.")

    src_text = raw_extract.read_text(encoding="utf-8")
    _info(f"==> Translating {raw_extract.relative_to(REPO_ROOT)}")
    _info(f"    source_language: {source_language} → en")
    _info(f"    source chars:    {len(src_text):,}")

    # Marker protection
    protected, markers = _protect_markers(src_text)
    _info(f"    markers protected: {len(markers)}")

    if dry_run:
        _info("==> --dry-run: skipping Azure Translator call + writes.")
        return 0

    # Lazy import of _azure so --dry-run works without Azure creds
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import _azure  # noqa: E402

    try:
        creds = _azure.load_translator_creds()
    except _azure.AzureCredsError as e:
        return _die(f"Azure Translator creds: {e}")

    t0 = time.monotonic()
    translated_protected = _azure.translate_text(
        creds, protected,
        src_lang=source_language, tgt_lang="en",
        text_type="html",
    )
    elapsed = time.monotonic() - t0
    _info(f"    translation done: {len(translated_protected):,} chars, {elapsed:.1f}s")
    # F36 (2026-05-25): record Azure Translator spend in cost-ledger.jsonl.
    try:
        from _cost_ledger import append_azure_translator_cost
        cost_row = append_azure_translator_cost(
            book_dir=book_dir, phase="0b", step="translate-bundle/translator",
            char_count=len(protected),
        )
        _info(f"    Azure cost (translator): ${cost_row.cost_usd:.4f} for {len(protected):,} input chars")
    except Exception as _e:
        _info(f"    WARN: cost-ledger append failed: {_e}")

    translated = _restore_markers(translated_protected, markers)
    restored_count = len(_PLACEHOLDER_RE.findall(translated_protected)) - \
                     len(_PLACEHOLDER_RE.findall(translated))
    _info(f"    markers restored: {restored_count}/{len(markers)}")

    # Backup source-language version (only on first run)
    if not backup.exists():
        backup.write_text(src_text, encoding="utf-8")
        _info(f"    backup written:  {backup.relative_to(REPO_ROOT)}")

    raw_extract.write_text(translated, encoding="utf-8")
    _info(f"    English written: {raw_extract.relative_to(REPO_ROOT)}")

    # Update orchestrator-state.json
    now = datetime.now(timezone.utc).isoformat()
    state["phase"] = "0b"
    state["phase_status"] = "pending"
    state["last_completed_phase"] = "0a"
    state["last_error"] = None
    state["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    state.setdefault("phases", {}).setdefault("0a", {}).update({
        "translated_at": now,
        "translation_provider": "azure",
        "translation_src_lang": source_language,
        "translation_tgt_lang": "en",
        "translation_chars_in": len(src_text),
        "translation_chars_out": len(translated),
    })
    state_path.write_text(json.dumps(state, indent=2) + "\n")
    _info(f"    state.json:      phase=0b, last_completed_phase=0a, last_error=null")

    # Append translator info to _provenance.json
    prov_path = book_dir / "_system" / "source" / "text" / "_provenance.json"
    if prov_path.exists():
        try:
            prov = json.loads(prov_path.read_text(encoding="utf-8"))
            prov["translator"] = {
                "provider": "azure",
                "api_version": _azure.TRANSLATOR_API_VERSION,
                "src_lang": source_language,
                "tgt_lang": "en",
                "region": creds.region,
                "input_char_count": len(src_text),
                "output_char_count": len(translated),
                "elapsed_seconds": round(elapsed, 2),
                "marker_count": len(markers),
                "marker_restoration": restored_count == len(markers),
            }
            prov_path.write_text(
                json.dumps(prov, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            _info(f"    provenance:      appended translator block")
        except Exception as e:
            _info(f"    WARN: could not update provenance.json — {e}")

    _info("")
    _info("==> DONE. Next:")
    _info(f"    python3 scripts/podcast/orchestrate_book.py --resume {slug}")
    _info(f"    Pipeline picks up at Phase 0b (refine).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--slug", required=True, help="Book slug under content/drafts/")
    ap.add_argument("--dry-run", action="store_true",
                    help="Validate state + count markers; skip Azure call + writes.")
    args = ap.parse_args()
    return translate_bundle(args.slug, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
