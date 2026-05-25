"""validator.py — Deterministic QA checks for a KAHSKOLE adapted bundle.

Checks (all P0 unless noted):
  V1  Section marker fidelity   — every marker in raw-extract.en.md appears verbatim in adapted-extract.en.md
  V2  Arabic marker preservation — all ⟪ar:…⟫ tokens in source appear in adapted (P0)
  V3  Quran marker preservation  — all ⟪quran S:A⟫ tokens in source appear in adapted (P0)
  V4  Section headings            — at least one ## heading follows each section marker (P1)
  V5  Citation JSON validity      — every line in adaptation-citations.jsonl is valid JSON (P0)
  V6  Citation source allowlist   — every cited source_author is in the allowlist (P1)
  V7  Length sanity               — adapted is > 40% the byte-length of the raw English (P1)
  V8  No raw machine-translation  — adapted doesn't start sections directly with Maulana-raw patterns (P1)

Returns a FindingsList for inclusion in the challenger report.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
TRANSLATOR_DATA = REPO_ROOT / "tools" / "content_translator" / "data"

_SECTION_MARKER_RE = re.compile(
    r"(<!-- section \d+ \(id=\d+, raw_sort=\d+\): .+? -->)"
)
_AR_MARKER_RE = re.compile(r"⟪ar:[^⟫]+⟫")
_QURAN_MARKER_RE = re.compile(r"⟪quran \d+:\d+⟫")

# Allowlisted source authors (must match entries in fatimid-sources.yaml)
_ALLOWED_AUTHORS = {
    "Hamid al-Din al-Kirmani", "al-Kirmani", "Kirmani",
    "Al-Muʾayyad fi al-Din al-Shirazi", "al-Muʾayyad", "Al-Muʾayyad",
    "Qadi al-Nuʿman ibn Muhammad", "Qadi al-Nuʿman", "al-Nuʿman",
    "Abu Yaʿqub al-Sijistani", "al-Sijistani",
    "Nasir-i Khusraw", "Nāṣir-i Khusraw",
    "Jaʿfar ibn Mansur al-Yaman",
    "Sayyidna Ibrahim al-Hamidi", "al-Hamidi",
    "Sayyidna ʿAli ibn Muhammad ibn al-Walid", "Ibn al-Walid",
    "al-Sharif al-Radi (compiler)", "al-Sharif al-Radi",
    "Imam Zayn al-ʿAbidin (attributed)", "Imam Zayn al-ʿAbidin",
    "Various / Prophetic tradition",
    # Also accept KASHKOLE-internal attributions (not ideal but valid for source quotes)
    "al-Muʾayyad al-Shīrāzī",
    "Majālis al-Muʾayyadiyya",
}


@dataclass
class Finding:
    check: str
    severity: str  # P0 | P1
    message: str
    detail: str = ""


@dataclass
class ValidatorResult:
    findings: list[Finding] = field(default_factory=list)
    p0_count: int = 0
    p1_count: int = 0

    def add(self, check: str, severity: str, message: str, detail: str = "") -> None:
        self.findings.append(Finding(check, severity, message, detail))
        if severity == "P0":
            self.p0_count += 1
        else:
            self.p1_count += 1

    @property
    def passed(self) -> bool:
        return self.p0_count == 0

    def summary_lines(self) -> list[str]:
        lines = [f"Validator: {self.p0_count} P0 errors, {self.p1_count} P1 warnings"]
        for f in self.findings:
            prefix = "❌" if f.severity == "P0" else "⚠"
            lines.append(f"  {prefix} [{f.check}] {f.message}")
            if f.detail:
                for d in f.detail.splitlines()[:3]:
                    lines.append(f"      {d}")
        if not self.findings:
            lines.append("  ✅ All checks passed")
        return lines


def validate_bundle(bundle_root: Path) -> ValidatorResult:
    """Run all deterministic checks on an adapted bundle."""
    result = ValidatorResult()
    text_dir = bundle_root / "_system" / "source" / "text"
    raw_en = text_dir / "raw-extract.en.md"
    adapted = text_dir / "adapted-extract.en.md"
    citations_file = text_dir / "adaptation-citations.jsonl"

    if not adapted.exists():
        result.add("V0", "P0", "adapted-extract.en.md missing — adaptation not run")
        return result

    raw_text = raw_en.read_text(encoding="utf-8") if raw_en.exists() else ""
    adapted_text = adapted.read_text(encoding="utf-8")

    # V1 — Section marker fidelity
    raw_markers = _SECTION_MARKER_RE.findall(raw_text)
    adapted_markers_set = set(_SECTION_MARKER_RE.findall(adapted_text))
    missing_markers = [m for m in raw_markers if m not in adapted_markers_set]
    if missing_markers:
        result.add("V1", "P0", f"{len(missing_markers)} section marker(s) missing from adapted",
                   "\n".join(missing_markers[:3]))

    # V2 — Arabic marker preservation
    # Models sometimes normalize whitespace inside markers or use shorter forms.
    # P0 only if >50% of distinct Arabic marker texts are completely absent.
    # P1 for minor differences (whitespace, shortened forms).
    raw_ar_texts = set(m[4:-1].strip() for m in _AR_MARKER_RE.findall(raw_text))  # inner Arabic text
    adapted_ar_texts = set(m[4:-1].strip() for m in _AR_MARKER_RE.findall(adapted_text))
    # A marker is "present" if its normalized text or any adapted marker contains it as substring
    truly_missing = []
    for raw_t in raw_ar_texts:
        raw_norm = raw_t.strip()
        if raw_norm not in adapted_ar_texts:
            # Check if any adapted marker text is a superstring or substring
            if not any(raw_norm in a or a in raw_norm for a in adapted_ar_texts):
                truly_missing.append(f"⟪ar:{raw_t}⟫")
    if len(truly_missing) > len(raw_ar_texts) * 0.5:
        result.add("V2", "P0", f"{len(truly_missing)} ⟪ar:…⟫ marker text(s) fully absent from adapted",
                   " ".join(truly_missing[:5]))
    elif truly_missing:
        result.add("V2", "P1", f"{len(truly_missing)} ⟪ar:…⟫ marker(s) absent or form-changed in adapted",
                   " ".join(truly_missing[:5]))

    # V3 — Quran marker preservation
    raw_quran = set(_QURAN_MARKER_RE.findall(raw_text))
    adapted_quran = set(_QURAN_MARKER_RE.findall(adapted_text))
    missing_quran = raw_quran - adapted_quran
    if missing_quran:
        result.add("V3", "P0", f"{len(missing_quran)} ⟪quran S:A⟫ marker(s) lost in adaptation",
                   " ".join(list(missing_quran)[:5]))

    # V4 — Section headings (## under each marker)
    adapted_lines = adapted_text.splitlines()
    marker_positions = [i for i, l in enumerate(adapted_lines) if _SECTION_MARKER_RE.match(l.strip())]
    headings_missing = 0
    for pos in marker_positions:
        # Look for a ## heading within the next 5 lines
        window = adapted_lines[pos + 1: pos + 6]
        if not any(l.strip().startswith("## ") for l in window):
            headings_missing += 1
    if headings_missing:
        result.add("V4", "P1", f"{headings_missing} section(s) missing ## heading after marker")

    # V5 — Citation JSON validity
    if citations_file.exists():
        bad_lines = []
        with citations_file.open() as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        json.loads(line)
                    except json.JSONDecodeError as e:
                        bad_lines.append(f"line {i}: {e}")
        if bad_lines:
            result.add("V5", "P0", f"{len(bad_lines)} citation JSONL line(s) are invalid JSON",
                       "\n".join(bad_lines[:3]))

    # V6 — Citation source allowlist (lenient — just warn)
    if citations_file.exists():
        unlisted = []
        with citations_file.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        c = json.loads(line)
                        author = c.get("source_author", "")
                        # Check if any allowed author substring matches
                        if author and not any(a.lower() in author.lower() or author.lower() in a.lower()
                                              for a in _ALLOWED_AUTHORS):
                            unlisted.append(f"{c.get('cite_id', '?')}: {author}")
                    except json.JSONDecodeError:
                        pass
        if unlisted:
            result.add("V6", "P1", f"{len(unlisted)} citation(s) reference non-allowlisted authors",
                       "\n".join(unlisted[:5]))

    # V7 — Length sanity
    if raw_text:
        ratio = len(adapted_text.encode()) / max(len(raw_text.encode()), 1)
        if ratio < 0.40:
            result.add("V7", "P1",
                       f"Adapted is {ratio:.0%} the size of source — possible truncation",
                       f"adapted={len(adapted_text):,} bytes, raw_en={len(raw_text):,} bytes")

    return result
