#!/usr/bin/env python3
"""_doctrinal.py — Category T (doctrinal accuracy) checks for the challenger.

Implements T1 through T5 from the podcast-challenger spec. Backed by three
YAML data files under content/_shared/islam/:

    imam-lineage-ismaili.yml   (T2 lineage, T3 forbidden_imam_titles)
    naming-conventions.yml     (T3 naming, P0 phrase scrub)
    canonical-attributions.yml (T1 attribution, T5 weak hadith)

T4 (Farman date/location plausibility) is a stub — needs a Farman dataset
that does not exist yet. Stubbed so the rule-id taxonomy is complete and the
data file path is reserved for future population.

Consumers:
  - scripts/podcast/build_episode_txt.py wires `check_t3_forbidden_phrases`
    as a hard build-time gate (catches "Imam Ali" before any chapter ships).
  - podcast-challenger agent runs `run_doctrinal_checks` on every chapter
    during convergence and emits findings to _learning/findings.jsonl.
  - test_challenger.py exercises each check_* function against fixtures
    in content/podcast/.skill/_learning/fixtures/doctrinal/.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from _paths import REPO_ROOT

# F31 (2026-05-25): tradition-pack registry. The original pipeline pinned
# `ISLAM_DATA = content/_shared/islam/`; that single hardcoded path silently
# no-ops the doctrinal gates for non-Islamic books and risks false-positives
# when a Twelver-Shia or Sufi book uses Ismaili-specific lineage data. The
# new pattern: each tradition gets its own subdirectory under content/_shared/
# with the same YAML schema. `load_doctrinal_pack(tradition)` returns the
# data dict for the named tradition; if the directory doesn't exist, it
# returns an empty pack so callers can emit a T-NO-PACK info finding
# (silence isn't mistaken for cleanliness).
ISLAM_DATA = REPO_ROOT / "content" / "_shared" / "islam"   # legacy alias kept for back-compat
TRADITION_DATA_ROOT = REPO_ROOT / "content" / "_shared"


def tradition_pack_dir(tradition: str) -> Path:
    """F31: resolve the data directory for a named tradition slug.

    `tradition` is the lowercase slug declared in series-config.yaml
    `source_tradition` (e.g. 'islam', 'ismaili', 'mahayana', 'catholic').
    Returns the path even if it doesn't exist — callers use .exists().
    Aliases like 'ismaili'/'shia'/'sunni'/'twelver'/'sufi' resolve to
    'islam' since the data files under content/_shared/islam/ cover the
    broader Islamic tradition.
    """
    alias = {"ismaili": "islam", "shia": "islam", "sunni": "islam",
             "twelver": "islam", "sufi": "islam"}.get(tradition.lower(), tradition.lower())
    return TRADITION_DATA_ROOT / alias


def load_doctrinal_pack(tradition: str) -> dict:
    """F31: load the YAML data pack for `tradition`; return empty pack if absent.

    Loads imam-lineage-*.yml, naming-conventions.yml, canonical-attributions.yml
    from the tradition's directory. Returns:
      {'_pack_missing': bool, 'tradition': str,
       'lineage': {sub_key: dict, ...}, 'naming': dict, 'attributions': dict}

    When the tradition dir doesn't exist, `_pack_missing=True` so callers
    (build_episode_txt.py, podcast-challenger) can emit a T-NO-PACK info
    finding rather than silently passing all doctrinal checks.
    """
    pack_dir = tradition_pack_dir(tradition)
    if not pack_dir.is_dir():
        return {"_pack_missing": True, "tradition": tradition,
                "lineage": {}, "naming": {}, "attributions": {}}
    out: dict = {"_pack_missing": False, "tradition": tradition,
                 "lineage": {}, "naming": {}, "attributions": {}}
    for lineage_path in sorted(pack_dir.glob("imam-lineage-*.yml")):
        out["lineage"][lineage_path.stem.replace("imam-lineage-", "")] = _load_yaml(lineage_path)
    naming_path = pack_dir / "naming-conventions.yml"
    if naming_path.exists():
        out["naming"] = _load_yaml(naming_path)
    attr_path = pack_dir / "canonical-attributions.yml"
    if attr_path.exists():
        out["attributions"] = _load_yaml(attr_path)
    return out


@dataclass
class DoctrinalFinding:
    """One Category-T finding. Mirrors the shape emit_finding() expects."""
    check_id: str           # "T1" | "T2" | "T3" | "T4" | "T5"
    severity: str           # "P0" | "P1"
    signature: str          # short machine-readable id
    context_excerpt: str    # the offending substring, up to 300 chars
    line: int | None = None
    replacement: str = ""   # optional canonical alternative
    reason: str = ""        # human-readable why-this-fired


# ─── YAML loading (no PyYAML dep — minimal parse of these flat files) ───────


def _load_yaml(path: Path) -> dict:
    """Tiny YAML reader sufficient for the three data files we ship. The data
    is intentionally flat-ish; no anchors, no complex nesting beyond list-of-
    dicts. Falls back to PyYAML if available, otherwise hand-parses the
    minimal subset the data uses.
    """
    text = path.read_text(encoding="utf-8")
    try:
        import yaml   # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        # Hand-parse: keys at indent 0, list items at indent 2 with `- key:`.
        # This is intentionally narrow — DO NOT extend without adding tests.
        # The fallback exists so the challenger keeps working in stripped-
        # down environments (CI shells without PyYAML).
        return _yaml_fallback(text)


def _yaml_fallback(text: str) -> dict:
    """Last-resort parse for the data files in content/_shared/islam/.
    Supports: top-level keys, scalar values, list-of-dicts under a key.
    Strips comments and blank lines."""
    out: dict = {}
    lines = [
        ln.rstrip()
        for ln in text.splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]
    i = 0
    while i < len(lines):
        ln = lines[i]
        m = re.match(r"^(\w[\w_-]*):\s*(.*)$", ln)
        if m and not ln.startswith(" "):
            key, val = m.group(1), m.group(2).strip()
            if val:
                out[key] = _yaml_scalar(val)
                i += 1
            else:
                # Collect either a list-of-dicts or list-of-scalars
                items, i = _yaml_collect_list(lines, i + 1)
                out[key] = items
        else:
            i += 1
    return out


def _yaml_collect_list(lines: list[str], i: int) -> tuple[list, int]:
    items: list = []
    while i < len(lines) and lines[i].startswith("  - "):
        first = lines[i][4:].strip()
        m = re.match(r"^(\w[\w_-]*):\s*(.*)$", first)
        if m:
            # list-of-dicts: collect this and following indented kv pairs
            item: dict = {m.group(1): _yaml_scalar(m.group(2).strip())} if m.group(2).strip() else {m.group(1): []}
            i += 1
            while i < len(lines) and lines[i].startswith("    "):
                sub = lines[i][4:]
                sm = re.match(r"^(\w[\w_-]*):\s*(.*)$", sub)
                if sm:
                    item[sm.group(1)] = _yaml_scalar(sm.group(2).strip()) if sm.group(2).strip() else []
                i += 1
            items.append(item)
        else:
            items.append(_yaml_scalar(first))
            i += 1
    return items, i


def _yaml_scalar(v: str):
    """Parse a YAML scalar: bool, int, quoted string, or inline list."""
    if v in ("true", "True"):
        return True
    if v in ("false", "False"):
        return False
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        if not inner:
            return []
        return [_yaml_scalar(x.strip().strip('"').strip("'")) for x in inner.split(",")]
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1]
    if v.startswith("|"):
        return ""   # block scalars are reason text; we don't need to parse
    if v.isdigit():
        return int(v)
    return v


# ─── Public data accessors ──────────────────────────────────────────────────


def load_imam_lineage() -> dict:
    return _load_yaml(ISLAM_DATA / "imam-lineage-ismaili.yml")


def load_naming_conventions() -> dict:
    return _load_yaml(ISLAM_DATA / "naming-conventions.yml")


def load_canonical_attributions() -> dict:
    return _load_yaml(ISLAM_DATA / "canonical-attributions.yml")


# ─── T1: Canonical attribution check ────────────────────────────────────────


def check_t1_canonical_attribution(text: str) -> list[DoctrinalFinding]:
    """For each entry in canonical-attributions.yml, search the text for the
    signature fragment. If found, scan the same paragraph for any forbidden
    attribution string. If a forbidden attribution co-occurs with the signature,
    emit P0 finding."""
    findings: list[DoctrinalFinding] = []
    data = load_canonical_attributions()
    for entry in data.get("attributions", []) or []:
        sig = entry.get("signature", "") if isinstance(entry, dict) else ""
        if not sig:
            continue
        # Use first 40 chars of signature as a stable lookup fragment
        needle = sig[:40].lower()
        for paragraph in re.split(r"\n\s*\n", text):
            if needle not in paragraph.lower():
                continue
            for forbidden in entry.get("forbidden_attributions", []) or []:
                f = forbidden.split(" (")[0].strip()   # strip trailing reason
                if f and f.lower() in paragraph.lower():
                    findings.append(DoctrinalFinding(
                        check_id="T1",
                        severity="P0",
                        signature=f"t1.{sig[:30].replace(' ', '_')}",
                        context_excerpt=paragraph[:300],
                        replacement=entry.get("canonical_attribution", ""),
                        reason=entry.get("reason", "").strip(),
                    ))
    return findings


# ─── T2: Imam lineage check ─────────────────────────────────────────────────


_ORDINAL_RE = re.compile(
    r"\b(?:the\s+)?(?:(\d+)(?:st|nd|rd|th)?|(first|second|third|fourth|fifth|sixth|seventh))\s+imam\b",
    re.IGNORECASE,
)
_WORD_TO_ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4,
                "fifth": 5, "sixth": 6, "seventh": 7}


def check_t2_imam_lineage(text: str) -> list[DoctrinalFinding]:
    """When the text names "the Nth Imam" (or "the Nth Imam, <Name>"), verify
    N matches the canonical lineage. The check looks for the canonical_name
    or any alias in a 60-char window after the ordinal phrase; if a different
    Imam's name appears, emit P0.

    Also flags any reference to "the Nth Imam" where N exceeds the known
    lineage length, since that signals a typo or unknown extension."""
    findings: list[DoctrinalFinding] = []
    data = load_imam_lineage()
    imams = data.get("imams", []) or []
    by_ord = {(i.get("ordinal") if isinstance(i, dict) else None): i for i in imams}

    for m in _ORDINAL_RE.finditer(text):
        num_str, word = m.group(1), m.group(2)
        if num_str:
            ordinal = int(num_str)
        else:
            ordinal = _WORD_TO_ORD.get(word.lower(), 0)
        if not ordinal:
            continue

        if ordinal not in by_ord:
            findings.append(DoctrinalFinding(
                check_id="T2",
                severity="P0",
                signature=f"t2.unknown_ordinal_{ordinal}",
                context_excerpt=text[max(0, m.start() - 40):m.end() + 60],
                reason=(f"Reference to 'the {ordinal}th Imam' but lineage "
                        f"only has {len(by_ord)} entries — likely typo or "
                        f"missing data."),
            ))
            continue

        # Look at the 80-char window after the match for a name token
        window = text[m.end():m.end() + 120]
        canonical = by_ord[ordinal]
        if not isinstance(canonical, dict):
            continue
        canonical_name = canonical.get("canonical_name", "")
        aliases = canonical.get("aliases", []) or []
        all_canonical_strs = [canonical_name] + list(aliases)

        # Did the writer place a DIFFERENT Imam's canonical_name in the window?
        for other_ord, other in by_ord.items():
            if other_ord == ordinal or not isinstance(other, dict):
                continue
            other_name = other.get("canonical_name", "")
            if other_name and other_name in window:
                # Crosscheck — was the correct Imam's name ALSO in the window?
                if not any(s and s in window for s in all_canonical_strs):
                    findings.append(DoctrinalFinding(
                        check_id="T2",
                        severity="P0",
                        signature=f"t2.lineage_swap_{ordinal}_{other_ord}",
                        context_excerpt=text[max(0, m.start() - 40):m.end() + 120],
                        replacement=canonical_name,
                        reason=(f"Text says 'the {ordinal}th Imam' but pairs "
                                f"it with {other_name} (who is #{other_ord} "
                                f"in the canonical lineage)."),
                    ))
                    break
    return findings


# ─── T3: Forbidden naming-convention violations ─────────────────────────────


def check_t3_forbidden_phrases(text: str) -> list[DoctrinalFinding]:
    """Substring scan for every entry in naming-conventions.yml::forbidden_phrases.

    This is the highest-volume check — "Imam Ali" appears in many third-party
    sources and needs to be aggressively scrubbed before a chapter ships.
    Build-script integration: build_episode_txt.py calls this as a HARD gate.

    Dedup invariant: each (start_offset, match_text) emits at most one finding,
    even when the same forbidden phrase appears in multiple data files
    (e.g., "Imam Ali" lives in both naming-conventions.yml and
    imam-lineage-ismaili.yml::forbidden_imam_titles).
    """
    findings: list[DoctrinalFinding] = []
    seen_positions: set[tuple[int, str]] = set()
    data = load_naming_conventions()
    for entry in data.get("forbidden_phrases", []) or []:
        if not isinstance(entry, dict):
            continue
        match = entry.get("match", "")
        if not match:
            continue
        # Word-boundary check so "Imam Ali" matches but "Imam Ali Zayn..." does NOT
        # (the multi-word names of valid Imams must not false-positive).
        pattern = r"\b" + re.escape(match) + r"\b(?!\s+(?:Zayn|al-Sajjad|ibn))"
        for m in re.finditer(pattern, text):
            key = (m.start(), m.group(0))
            if key in seen_positions:
                continue
            seen_positions.add(key)
            findings.append(DoctrinalFinding(
                check_id="T3",
                severity=entry.get("severity", "P0"),
                signature=f"t3.{match.replace(' ', '_').lower()}",
                context_excerpt=text[max(0, m.start() - 40):m.end() + 60],
                replacement=entry.get("replacement", ""),
                reason=entry.get("reason", "").strip(),
                line=text[:m.start()].count("\n") + 1,
            ))

    # Also scrub forbidden_imam_titles from imam-lineage-ismaili.yml — those
    # are P0 violations of the lineage policy itself (Imam Fatima, etc.)
    lineage = load_imam_lineage()
    for entry in lineage.get("forbidden_imam_titles", []) or []:
        if not isinstance(entry, dict):
            continue
        for alias in entry.get("aliases_that_signal_violation", []) or []:
            if not alias:
                continue
            pattern = r"\b" + re.escape(alias) + r"\b"
            for m in re.finditer(pattern, text):
                key = (m.start(), m.group(0))
                if key in seen_positions:
                    continue
                seen_positions.add(key)
                findings.append(DoctrinalFinding(
                    check_id="T3",
                    severity=entry.get("severity", "P0"),
                    signature=f"t3.lineage_forbidden.{alias.replace(' ', '_').lower()}",
                    context_excerpt=text[max(0, m.start() - 40):m.end() + 60],
                    replacement=", ".join(entry.get("canonical_titles", []) or []),
                    reason=entry.get("reason", "").strip(),
                    line=text[:m.start()].count("\n") + 1,
                ))

    return findings


# ─── T4: Farman date/location plausibility (STUB) ───────────────────────────


def check_t4_farman_plausibility(text: str) -> list[DoctrinalFinding]:
    """STUB — needs a Farman dataset (date, issuing Imam, location). Once
    populated under content/_shared/islam/farmans.yml, this check should
    cross-reference any Farman attribution in the text against the dataset
    and flag impossible Imam+date pairings (e.g., a Farman dated before the
    Imam's accession or after his death).

    Currently returns no findings — the rule-id is reserved.
    """
    return []


# ─── T5: Weak/fabricated hadith (STUB until dataset populated) ─────────────


def check_t5_weak_hadith(text: str) -> list[DoctrinalFinding]:
    """Scan for matn fragments of known-weak or known-fabricated hadith. The
    list under canonical-attributions.yml::weak_or_fabricated_hadith is empty
    on first commit — populate via the trainer skill as patterns emerge."""
    findings: list[DoctrinalFinding] = []
    data = load_canonical_attributions()
    for entry in data.get("weak_or_fabricated_hadith", []) or []:
        if not isinstance(entry, dict):
            continue
        sig = entry.get("signature", "")
        if not sig:
            continue
        if sig.lower() in text.lower():
            findings.append(DoctrinalFinding(
                check_id="T5",
                severity=entry.get("severity", "P1"),
                signature=f"t5.{sig[:30].replace(' ', '_').lower()}",
                context_excerpt=sig[:300],
                reason=entry.get("reason", "").strip(),
            ))
    return findings


# ─── Aggregator ─────────────────────────────────────────────────────────────


def run_doctrinal_checks(text: str) -> list[DoctrinalFinding]:
    """Run T1–T5 in order. Returns aggregated findings, severity-sorted (P0
    first) so the caller can stop on first P0 if desired."""
    findings: list[DoctrinalFinding] = []
    findings.extend(check_t1_canonical_attribution(text))
    findings.extend(check_t2_imam_lineage(text))
    findings.extend(check_t3_forbidden_phrases(text))
    findings.extend(check_t4_farman_plausibility(text))
    findings.extend(check_t5_weak_hadith(text))
    findings.sort(key=lambda f: (f.severity != "P0", f.check_id))
    return findings


# ─── CLI for ad-hoc scans ───────────────────────────────────────────────────


def _cli():
    import argparse
    ap = argparse.ArgumentParser(
        description="Run Category T (doctrinal accuracy) checks against a file."
    )
    ap.add_argument("path", help="Path to chapter/framing/episode .md or .txt")
    args = ap.parse_args()
    text = Path(args.path).read_text(encoding="utf-8")
    findings = run_doctrinal_checks(text)
    if not findings:
        print(f"OK — no doctrinal findings in {args.path}")
        return 0
    for f in findings:
        print(f"{f.severity} {f.check_id} ({f.signature})")
        print(f"  reason: {f.reason[:200]}")
        print(f"  context: …{f.context_excerpt[:200]}…")
        if f.replacement:
            print(f"  replacement: {f.replacement}")
        print()
    return 1 if any(f.severity == "P0" for f in findings) else 0


if __name__ == "__main__":
    import sys
    sys.exit(_cli())
