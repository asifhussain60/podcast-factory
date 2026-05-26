"""translate.py — Azure-based literal Urdu→English translation of a bundle.

Reads raw-extract.md, splits by section markers, translates each section's
content via Azure Translator, reassembles with original markers intact, and
writes raw-extract.en.md.

NEVER modifies raw-extract.md. (Source of truth stays byte-faithful.)
Stage transition: reviewed → translated.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "podcast"))
import _azure  # noqa: E402

COST_LEDGER = REPO_ROOT / "_workspace" / "plan" / "kashkole-translation-cost-ledger.jsonl"

# Azure Translator S1: $10 / 1M characters
COST_PER_CHAR_USD = 10.0 / 1_000_000

# Markers we protect from translation by substituting with placeholders
_AR_MARKER_RE = re.compile(r"⟪(ar(?:-quote)?:[^⟫]*)⟫")
_QURAN_MARKER_RE = re.compile(r"⟪(quran \d+:\d+)⟫")
_SECTION_MARKER_RE = re.compile(
    r"^(<!-- section \d+ \(id=\d+, raw_sort=\d+\): .+? -->)$",
    re.MULTILINE,
)
_IMG_BLOCK_RE = re.compile(
    r"(\[diagram:.*?\]\n\s+\(see \.\./images/\d+\.\w+\)\n(?:  \*Arabic labels.*?\n)?(?:  \*Note:.*?\n)?)",
    re.DOTALL,
)


def _protect_markers(text: str) -> tuple[str, dict[str, str]]:
    """Replace ⟪…⟫ markers and image blocks with stable XML-safe placeholders.

    Azure Translator preserves XML void elements (<x id="N"/>), so we use
    those as protection tokens. Returns (protected_text, placeholder_map).
    """
    placeholders: dict[str, str] = {}
    counter = [0]

    def _sub(match: re.Match) -> str:
        pid = f"MKRP{counter[0]:04d}"
        counter[0] += 1
        placeholders[pid] = match.group(0)
        return f'<x id="{pid}"/>'

    text = _AR_MARKER_RE.sub(_sub, text)
    text = _QURAN_MARKER_RE.sub(_sub, text)
    text = _IMG_BLOCK_RE.sub(_sub, text)
    return text, placeholders


def _restore_markers(text: str, placeholders: dict[str, str]) -> str:
    # Restore in reverse insertion order: outer placeholders (higher ID, created last)
    # are replaced first, exposing inner placeholders embedded in their content.
    for pid in reversed(list(placeholders.keys())):
        text = text.replace(f'<x id="{pid}"/>', placeholders[pid])
    return text


def _split_by_sections(source: str) -> list[tuple[str, str]]:
    """Split source into [(marker_or_header, content), ...].

    The first element is always the file header (title + source line),
    with an empty string as marker. Subsequent elements have the section
    comment as marker and the section body as content.
    """
    parts: list[tuple[str, str]] = []
    last_end = 0
    header_done = False

    for m in _SECTION_MARKER_RE.finditer(source):
        chunk = source[last_end : m.start()]
        if not header_done:
            parts.append(("", chunk))
            header_done = True
        else:
            # content belonging to the previous section marker
            if parts:
                prev_marker, _ = parts[-1]
                parts[-1] = (prev_marker, chunk)
            else:
                parts.append(("", chunk))
        parts.append((m.group(1), ""))
        last_end = m.end()

    # trailing content after last section marker
    tail = source[last_end:]
    if parts:
        prev_marker, _ = parts[-1]
        parts[-1] = (prev_marker, tail)
    else:
        parts.append(("", tail))

    return parts


def _is_english_content(text: str) -> bool:
    """Return True if >80% of non-whitespace chars are ASCII — already English."""
    non_ws = [c for c in text if not c.isspace()]
    if not non_ws:
        return False
    ascii_count = sum(1 for c in non_ws if ord(c) < 128)
    return ascii_count / len(non_ws) > 0.80


def translate_bundle(
    bundle_root: Path,
    creds: Optional[_azure.TranslatorCreds] = None,
    *,
    binder_id: Optional[int] = None,
    chapter_id: Optional[int] = None,
    dry_run: bool = False,
) -> dict:
    """Translate a bundle's raw-extract.md → raw-extract.en.md.

    Returns a summary dict with cost_usd, sections_translated, char_count.
    Stage transition: reviewed → translated.
    Idempotent: if stage is already 'translated' (or further), skips.
    """
    bundle_yml = bundle_root / "bundle.yml"
    text_dir = bundle_root / "_system" / "source" / "text"
    raw_extract = text_dir / "raw-extract.md"
    raw_extract_en = text_dir / "raw-extract.en.md"

    if not bundle_yml.exists():
        raise FileNotFoundError(f"bundle.yml not found: {bundle_yml}")
    if not raw_extract.exists():
        raise FileNotFoundError(f"raw-extract.md not found: {raw_extract}")

    stage = _read_stage(bundle_yml)
    if stage not in ("reviewed",):
        if stage in ("translated", "adapted", "challenged"):
            print(f"SKIPPED (already {stage}): {bundle_root}")
            return {"skipped": True, "stage": stage}
        raise RuntimeError(
            f"Unexpected stage '{stage}' — expected 'reviewed'. "
            "Re-run review/seal first."
        )

    source_text = raw_extract.read_text(encoding="utf-8")

    # English passthrough: if content is >80% ASCII, it's already English — no Azure call.
    # Write the source as-is to raw-extract.en.md and stamp stage.
    if _is_english_content(source_text):
        completed_at = datetime.now(timezone.utc).isoformat()
        if not dry_run:
            raw_extract_en.write_text(source_text, encoding="utf-8")
            _append_translation_block(bundle_yml, 0, 0, 0.0, completed_at,
                                      engine="passthrough-english")
            _update_stage(bundle_yml, "translated")
            _append_cost_ledger(binder_id, chapter_id, "passthrough", 0.0, completed_at)
        return {
            "skipped": False,
            "passthrough": True,
            "sections_translated": 0,
            "char_count": 0,
            "cost_usd": 0.0,
            "completed_at": completed_at,
            "output_path": str(raw_extract_en),
        }

    if creds is None:
        creds = _azure.load_translator_creds()

    parts = _split_by_sections(source_text)

    translated_parts: list[tuple[str, str]] = []
    total_chars = 0
    sections_translated = 0

    for marker, content in parts:
        if not content.strip():
            translated_parts.append((marker, content))
            continue

        protected, placeholders = _protect_markers(content)
        char_count = len(protected)
        total_chars += char_count

        if dry_run:
            translated_content = f"[DRY RUN — {char_count} chars would be translated]\n"
        else:
            raw_translated = _azure.translate_text(
                creds,
                protected,
                src_lang="ur",
                tgt_lang="en",
                text_type="html",
            )
            translated_content = _restore_markers(raw_translated, placeholders)

        translated_parts.append((marker, translated_content))
        if marker:  # don't count header as a section
            sections_translated += 1

    # Reassemble
    out_lines: list[str] = []
    for marker, content in translated_parts:
        if marker:
            out_lines.append(marker)
        out_lines.append(content)
    output = "".join(out_lines)

    cost_usd = total_chars * COST_PER_CHAR_USD
    completed_at = datetime.now(timezone.utc).isoformat()

    if not dry_run:
        raw_extract_en.write_text(output, encoding="utf-8")
        _append_translation_block(bundle_yml, sections_translated, total_chars, cost_usd, completed_at)
        _update_stage(bundle_yml, "translated")
        _append_cost_ledger(binder_id, chapter_id, "translate", cost_usd, completed_at)

    return {
        "skipped": False,
        "sections_translated": sections_translated,
        "char_count": total_chars,
        "cost_usd": cost_usd,
        "completed_at": completed_at,
        "output_path": str(raw_extract_en),
    }


# ── bundle.yml helpers ────────────────────────────────────────────────────────

def _read_stage(bundle_yml: Path) -> str:
    for line in bundle_yml.read_text(encoding="utf-8").splitlines():
        if line.startswith("stage:"):
            return line.split(":", 1)[1].strip()
    return ""


def _update_stage(bundle_yml: Path, new_stage: str) -> None:
    text = bundle_yml.read_text(encoding="utf-8")
    lines = [
        f"stage: {new_stage}" if l.startswith("stage:") else l
        for l in text.splitlines()
    ]
    bundle_yml.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _strip_existing_block(text: str, key: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    skipping = False
    for line in lines:
        if line.startswith(f"{key}:"):
            skipping = True
            continue
        if skipping:
            if not line or line[0] in (" ", "\t"):
                continue
            skipping = False
        out.append(line)
    return "\n".join(out).rstrip() + "\n"


def _append_translation_block(
    bundle_yml: Path,
    sections: int,
    chars: int,
    cost: float,
    completed_at: str,
    engine: str = "azure-translator-v3",
) -> None:
    text = _strip_existing_block(bundle_yml.read_text(encoding="utf-8"), "translation")
    block = (
        f"\ntranslation:\n"
        f"  engine: {engine}\n"
        f"  completed_at: {completed_at}\n"
        f"  sections_translated: {sections}\n"
        f"  char_count: {chars}\n"
        f"  azure_cost_usd: {cost:.6f}\n"
    )
    bundle_yml.write_text(text.rstrip() + block, encoding="utf-8")


def _append_cost_ledger(
    binder_id: Optional[int],
    chapter_id: Optional[int],
    phase: str,
    cost_usd: float,
    completed_at: str,
) -> None:
    COST_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "binder_id": binder_id,
        "chapter_id": chapter_id,
        "phase": phase,
        "cost_usd": round(cost_usd, 6),
        "completed_at": completed_at,
    }
    with COST_LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
