"""_augmentation.py — Category W (augmentation quality) checks for the challenger.

Wave L. Guards that knowledge augmentation (doctrine / term / quote / etymology
context blocks prepended to episode text by intelligence/augmenter.py) is:

  W1  used only where it fills a genuine gap — not forced. (P1, auto-revert)
  W2  natural, not bolted-on. (P1, auto-revert) — light heuristic + agent judgment.
  W3  etymology rationed (<= R_AUGMENT_ETYMOLOGY_MAX_PER_CHAPTER), spoken in romanized
      form, NEVER spelling Arabic letters / emitting Arabic script. (P1)
  W4  every doctrine atom within the book's content level (cumulative downward). (P0)
  W5  every referenced atom actually exists in knowledge.db — no fabrication. (P0)
  W6  no atom repeated across chapters of the same book. (P1)

W3 is text-only. W4/W5/W6 read the per-episode ledger (episode-augment-ledger.json)
+ knowledge.db. W1/W2 are flagged heuristically here and judged semantically by the
challenger agent (the spec in podcast-challenger.md owns the prose rubric).

Mirrors _doctrinal.py (Category T): a Finding dataclass + per-check functions +
run_all aggregator. Pure-stdlib; importable in stripped CI shells.

Authority: Wave L plan §L-6; _rules.py R_AUGMENT_* + CHALLENGER_VERSION 2.4.
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import _db  # noqa: E402
from _rules import (  # noqa: E402
    R_AUGMENT_ETYMOLOGY_MAX_PER_CHAPTER,
    R_AUGMENT_ARABIC_RANGES,
    R_AUGMENT_BLOCK_HEADERS,
    allowed_content_levels,
)

_ARABIC_RE = re.compile(
    "[" + "".join(rf"\u{lo:04x}-\u{hi:04x}" for lo, hi in R_AUGMENT_ARABIC_RANGES) + "]"
)


@dataclass
class AugmentationFinding:
    """One Category-W finding. Mirrors the shape emit_finding() expects."""
    check_id: str            # "W1".."W6"
    severity: str            # "P0" | "P1"
    signature: str           # short machine-readable id
    context_excerpt: str = ""
    reason: str = ""


# ─── block extraction ───────────────────────────────────────────────────────

def _extract_block(text: str, header_key: str) -> str:
    """Return the augmentation block whose header startswith the configured prefix.

    Augmenter blocks are prepended ahead of the episode body. A block is its
    header line plus the following content lines (bullets / glossary entries),
    tolerating a single blank line between the header and its content. The block
    ENDS at the blank line that precedes the next block header or the episode
    body — so the episode prose is never swallowed. Returns "" when absent.
    """
    prefix = R_AUGMENT_BLOCK_HEADERS[header_key]
    other_headers = [p for p in R_AUGMENT_BLOCK_HEADERS.values() if p != prefix]
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.strip().startswith(prefix)), None)
    if start is None:
        return ""
    end = start
    j = start + 1
    while j < len(lines):
        s = lines[j].strip()
        if s == "":
            # Blank line: continue only if the next non-blank line is block content
            # (a bullet). Otherwise the block has ended (episode body follows).
            k = j + 1
            while k < len(lines) and lines[k].strip() == "":
                k += 1
            if k < len(lines) and lines[k].lstrip().startswith("- "):
                j = k
                continue
            break
        if any(s.startswith(p) for p in other_headers):
            break  # next block header
        end = j
        j += 1
    return "\n".join(lines[start:end + 1]).strip()


# ─── W3 — etymology discipline (text-only) ──────────────────────────────────

def check_w3_etymology(text: str) -> list[AugmentationFinding]:
    block = _extract_block(text, "etymology")
    if not block:
        return []
    findings: list[AugmentationFinding] = []
    bullets = [ln for ln in block.splitlines() if ln.lstrip().startswith("- ")]
    if len(bullets) > R_AUGMENT_ETYMOLOGY_MAX_PER_CHAPTER:
        findings.append(AugmentationFinding(
            check_id="W3", severity="P1", signature="etymology-over-cap",
            context_excerpt=f"{len(bullets)} etymology insights",
            reason=f"More than {R_AUGMENT_ETYMOLOGY_MAX_PER_CHAPTER} etymology insights "
                   f"in one chapter ({len(bullets)}).",
        ))
    if _ARABIC_RE.search(block):
        m = _ARABIC_RE.search(block)
        findings.append(AugmentationFinding(
            check_id="W3", severity="P1", signature="etymology-arabic-script",
            context_excerpt=block[max(0, m.start() - 20): m.start() + 20],
            reason="Arabic script in an etymology aside — roots must be SPOKEN "
                   "(romanized), never written/spelled in Arabic letters.",
        ))
    # Every etymology bullet must carry a spoken form (a quoted "..." phonetic).
    for b in bullets:
        if 'spoken "' not in b and "spoken '" not in b:
            findings.append(AugmentationFinding(
                check_id="W3", severity="P1", signature="etymology-no-spoken-form",
                context_excerpt=b[:120],
                reason="Etymology aside lacks a spoken phonetic guide.",
            ))
            break
    return findings


# ─── ledger / DB backed checks (W4, W5, W6) ─────────────────────────────────

def _load_ledger(book_dir: Path) -> dict:
    p = book_dir / "_system" / "episode-augment-ledger.json"
    if not p.exists():
        return {"episodes": {}}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d.get("episodes"), dict) else {"episodes": {}}
    except Exception:  # noqa: BLE001
        return {"episodes": {}}


def _book_content_level(book_dir: Path) -> str | None:
    meta = book_dir / "meta.yml"
    if not meta.exists():
        return None
    try:
        import yaml  # type: ignore[import]
        data = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
        lvl = data.get("content_level")
        return str(lvl) if allowed_content_levels(lvl) else None
    except Exception:  # noqa: BLE001
        return None


def check_w4_w5_content_and_existence(book_dir: Path, episode_slug: str) -> list[AugmentationFinding]:
    """W4 (doctrine within level) + W5 (atom exists) for one episode's ledger entry."""
    ledger = _load_ledger(book_dir)
    entry = (ledger.get("episodes") or {}).get(episode_slug)
    if not entry:
        return []
    atom_ids = entry.get("atoms_injected", []) or []
    if not atom_ids:
        return []
    conn = _db.get_connection()
    placeholders = ",".join("?" * len(atom_ids))
    rows = {r[0]: (r[1], r[2]) for r in conn.execute(
        f"SELECT id, type, content_level FROM atoms WHERE id IN ({placeholders})", atom_ids,
    ).fetchall()}

    findings: list[AugmentationFinding] = []
    # W5 — fabrication: every injected atom id must exist.
    for aid in atom_ids:
        if aid not in rows:
            findings.append(AugmentationFinding(
                check_id="W5", severity="P0", signature="fabricated-atom",
                context_excerpt=aid,
                reason=f"Injected atom '{aid}' does not exist in knowledge.db.",
            ))
    # W4 — content-level leak: doctrine atoms must be within the book's band.
    book_level = _book_content_level(book_dir)
    allowed = set(allowed_content_levels(book_level))
    if allowed:
        for aid, (atype, clevel) in rows.items():
            if atype != "doctrine":
                continue  # only doctrine is gated
            if clevel is None:
                continue  # uncategorized passes during transition
            if clevel not in allowed:
                findings.append(AugmentationFinding(
                    check_id="W4", severity="P0", signature="content-level-leak",
                    context_excerpt=f"{aid} ({clevel})",
                    reason=f"Doctrine atom '{aid}' is level '{clevel}', above the book's "
                           f"level '{book_level}' (allowed: {sorted(allowed)}).",
                ))
    return findings


def check_w6_no_cross_chapter_repeat(book_dir: Path) -> list[AugmentationFinding]:
    """W6 — book-wide: no atom may appear in more than one episode's ledger entry."""
    ledger = _load_ledger(book_dir)
    seen: dict[str, str] = {}
    findings: list[AugmentationFinding] = []
    for slug, entry in (ledger.get("episodes") or {}).items():
        for aid in entry.get("atoms_injected", []) or []:
            if aid in seen and seen[aid] != slug:
                findings.append(AugmentationFinding(
                    check_id="W6", severity="P1", signature="cross-chapter-repeat",
                    context_excerpt=f"{aid}: {seen[aid]} + {slug}",
                    reason=f"Atom '{aid}' injected into both '{seen[aid]}' and '{slug}'.",
                ))
            else:
                seen[aid] = slug
    return findings


# ─── auto-revert helper (W1/W2 remediation) ─────────────────────────────────

def revert_block(text: str, header_key: str) -> str:
    """Strip one augmentation block (W1/W2 auto-revert). Returns text unchanged
    when the block is absent. Used by the convergence fixer to remove a block the
    challenger judged forced/unnatural; the augmenter then re-runs with that atom
    excluded via the ledger.
    """
    block = _extract_block(text, header_key)
    if not block:
        return text
    return text.replace(block, "").replace("\n\n\n", "\n\n").strip() + "\n"


# ─── aggregator ─────────────────────────────────────────────────────────────

def run_all(text: str, book_dir: Path | None = None, episode_slug: str = "") -> list[AugmentationFinding]:
    """Run W3 (text) + W4/W5/W6 (ledger+DB when book_dir given). Severity-sorted."""
    findings = list(check_w3_etymology(text))
    if book_dir is not None:
        if episode_slug:
            findings += check_w4_w5_content_and_existence(book_dir, episode_slug)
        findings += check_w6_no_cross_chapter_repeat(book_dir)
    findings.sort(key=lambda f: (f.severity != "P0", f.check_id))
    return findings
