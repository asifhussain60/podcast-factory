#!/usr/bin/env python3
"""audit_transcript.py — Empirical NotebookLM transcript audit.

PURPOSE

  Closes the empirical-feedback loop the pipeline previously lacked. Given a
  NotebookLM-generated transcript (audio overview transcribed to text), measure
  drift against the framing's directives and produce a per-episode audit report.

  This is the sensor end of the architecture:

    chapter + customize prompt  →  NotebookLM  →  transcript
                                                       ↓
                                              audit_transcript.py
                                                       ↓
                                  per-episode markdown report with:
                                    - phonetic-doubling count (R-PHONETICS-OUT)
                                    - mangled-name detector
                                    - modernization-injection count (R-NOMODERNIZE)
                                    - surprise-noise loop count (R-NOSURPRISE)
                                    - welcome-cold violations (R-WELCOME)
                                    - honorific repetition count (R-HONORIFIC-ONCE)
                                    - abbreviation injections (R-NO-ABBREVIATION)
                                    - filler-injection density (R-NOINTERRUPT)

USAGE

  python3 scripts/podcast/audit_transcript.py <BOOK_DIR> <EP##-slug> [<transcript-file>]

  When the transcript file argument is omitted, the script auto-resolves to
    <BOOK_DIR>/turboscribe/EP##-<slug>.transcript.txt

OUTPUT

  Writes  <BOOK_DIR>/_system/audit-EP##-<slug>.md  — markdown report. Stable
  format so successive runs are diffable.

DOES NOT MODIFY anything else. Read-only against chapter, framing, and
transcript; writes only the audit report.
"""

import re
import sys
from pathlib import Path
from collections import Counter

# Canonical rule lists live in _rules.py (mirrored from the handbook normative
# copy at content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md).
sys.path.insert(0, str(Path(__file__).parent))
from _rules import (
    MODERNIZE_DENY,
    SURPRISE_DENY,
    WELCOME_COLD,
    HONORIFICS as HONORIFIC_EXPANSIONS,
    FILLER_INTERJECTIONS,
    abbreviations_for_audit,
)

FORBIDDEN_ABBREVIATIONS = abbreviations_for_audit()


# Names commonly mangled by NotebookLM TTS (observed empirically).
# Maps canonical spelling → list of likely mangled forms to detect.
NAME_MANGLING_MAP = {
    "Ayyuhal Walad": [
        "a yuhal wallad", "i you hall wall odd", "ayyuhallwalaad",
        "ayuhol walad", "ayyuhaw walad", "ayyuhal wallad",
    ],
    "Tasawwuf": ["tassel wolf", "tasso wolf", "tasa wolf", "tassel woolf"],
    "Ikhlas": ["aclus", "iclas", "ick las"],
    "Nahj al-Balagha": ["najah balala", "najah balaga", "nahjal balaga"],
    "Dhul-Nun al-Misri": ["shakestone noon mystery", "shake stone noon"],
    "Hatim bin Ism": ["hatim vanism", "hatim of nism", "hatim vanism"],
    "Shaqiq al-Balkhi": ["shaikik al-balki", "shafeeq balkhi"],
    "Bay'a": ["bhaya", "bayaa"],
    "Riyazat": ["rizat", "riyzat"],
    "Mujahadah": ["mujahada", "moo jahada"],
    "Nasir-i Khusraw": ["nasiri khusra", "nasir kushra"],
    "Riya": [" rhea ", " rhea,", " rhea."],  # spelled like the ostrich
    "Ihya Ulum al-Din": [" EI ", " EI."],
    "Sahih Bukhari": ["sahail bukhari"],
    "Sahih Muslim": ["sahi muslim"],
    "Sahih Sitta": ["sahasita", "sa ha sita"],
    "Azwaj al-Mutahharat": ["aswaja al-mutaharat"],
    "Aisha Siddiqa": ["aisha siddhika"],
    "Fard al-ayn": ["fard al-an"],
    "Fard Kifaya": ["fard ki efaya"],
    "Hadith Qudsi": [],  # detected by adjacent repetition instead
}


def count_phrase_hits(text: str, phrases: list[str]) -> list[tuple[str, int]]:
    return [(p, text.count(p)) for p in phrases if text.count(p) > 0]


def count_regex_hits(text: str, patterns: list[str]) -> list[tuple[str, int]]:
    out = []
    for pat in patterns:
        n = len(re.findall(pat, text))
        if n > 0:
            out.append((pat, n))
    return out


def detect_phonetic_doublings(text: str) -> list[str]:
    """The 'Sahih Sitta, sahasita' pattern: a transliterated term immediately
    followed (within a few words) by a near-identical lower-case respelling.

    Heuristic: a capitalized Arabic-style token followed by a comma/space and
    then a hyphen-bearing lowercase token whose letters loosely match.
    """
    pattern = re.compile(
        r"\b([A-Z][a-zA-Z']{2,})\b[\s,]+([a-z]+(?:[\s\-][a-z]+){1,3})"
    )
    hits = []
    for m in pattern.finditer(text):
        a, b = m.group(1), m.group(2).replace("-", " ").replace(",", "")
        # If b looks like a respelled phonetic of a (loose letter overlap)
        a_l = a.lower()
        b_collapsed = b.replace(" ", "")
        if len(b_collapsed) < 4:
            continue
        # cheap "looks like a respelling" check: ≥60% of a's letters in b_collapsed,
        # and b_collapsed has at least one hyphen or multiple short syllables.
        common = sum(1 for c in set(a_l) if c in b_collapsed)
        if len(set(a_l)) and common / len(set(a_l)) >= 0.55 and "-" in m.group(2):
            hits.append(f"{a}, {m.group(2)}")
    # also detect literal duplicated tokens: "Du'a, du'a"
    dup = re.findall(r"\b([A-Za-z'`\-]{3,})\b[\s,]+\1\b", text, re.IGNORECASE)
    for d in dup:
        hits.append(f"{d}, {d.lower()}")
    return hits


def detect_mangled_names(text: str) -> list[tuple[str, str, int]]:
    out = []
    for canonical, mangled_forms in NAME_MANGLING_MAP.items():
        for m in mangled_forms:
            n = text.lower().count(m.lower())
            if n > 0:
                out.append((canonical, m, n))
    return out


def word_count(text: str) -> int:
    return len(text.split())


def audit(book_dir: Path, episode_id: str, transcript_path: Path) -> Path:
    if not transcript_path.exists():
        sys.exit(
            f"ERROR: transcript not found: {transcript_path}\n"
            f"  Expected location: <BOOK_DIR>/turboscribe/<EP##-slug>.transcript.txt\n"
            f"  Or pass the path explicitly as the third argument."
        )
    text = transcript_path.read_text(encoding="utf-8")
    wc = word_count(text)

    # Compute every metric
    modernize_hits = count_phrase_hits(text, MODERNIZE_DENY)
    surprise_hits = count_phrase_hits(text, SURPRISE_DENY)
    welcome_hits = count_phrase_hits(text, WELCOME_COLD)
    abbreviation_hits = [(b, text.count(b)) for b, _ in FORBIDDEN_ABBREVIATIONS if text.count(b) > 0]
    honorific_hits = count_regex_hits(text, HONORIFIC_EXPANSIONS)
    filler_hits = count_phrase_hits(text, FILLER_INTERJECTIONS)
    phonetic_doublings = detect_phonetic_doublings(text)
    mangled = detect_mangled_names(text)

    # Densities (per 1,000 words)
    per_kw = lambda n: f"{(n * 1000) / wc:.1f}" if wc else "0.0"

    # Report
    lines: list[str] = []
    lines.append(f"# Transcript Audit · {episode_id}")
    lines.append("")
    lines.append(f"**Transcript:** `{transcript_path.relative_to(book_dir.parent.parent) if book_dir.parent.parent in transcript_path.parents else transcript_path}`")
    lines.append(f"**Word count:** {wc}")
    lines.append(f"**Audit tool:** `scripts/podcast/audit_transcript.py` v1.0 (2026-05-17)")
    lines.append("")

    # Headline verdict
    total_p0 = (
        len(phonetic_doublings) +
        sum(n for _, _, n in mangled) +
        sum(n for _, n in welcome_hits)
    )
    total_p1 = (
        sum(n for _, n in modernize_hits) +
        sum(n for _, n in surprise_hits) +
        sum(n for _, n in honorific_hits) +
        sum(n for _, n in abbreviation_hits)
    )
    if total_p0 == 0 and total_p1 == 0:
        verdict = "CLEAN"
    elif total_p0 == 0:
        verdict = "DRIFT-NOTED"
    else:
        verdict = "REGRESSION"

    lines.append(f"## Verdict: **{verdict}**")
    lines.append("")
    lines.append(f"- P0 hits (architecture failures): **{total_p0}**")
    lines.append(f"- P1 hits (drift signals): **{total_p1}**")
    lines.append("")

    # Section 1 — Phonetic doublings (R-PHONETICS-OUT)
    lines.append("## Phonetic doublings · R-PHONETICS-OUT (P0)")
    lines.append("")
    lines.append("Pattern: `Term, term-phonetic` — the hosts read the transliteration AND its respelled phonetic. Indicates either inline phonetics survived in the chapter file or the framing's `## Pronunciation` block was not in imperative form.")
    lines.append("")
    if phonetic_doublings:
        lines.append(f"**Count:** {len(phonetic_doublings)}")
        lines.append("")
        for d in phonetic_doublings[:20]:
            lines.append(f"- `{d}`")
        if len(phonetic_doublings) > 20:
            lines.append(f"- … {len(phonetic_doublings) - 20} more")
    else:
        lines.append("**Count:** 0 — no doublings detected.")
    lines.append("")

    # Section 2 — Mangled names
    lines.append("## Mangled names (P0)")
    lines.append("")
    lines.append("Known-mangling lookup: each canonical name is scanned against its empirically-observed mangled forms.")
    lines.append("")
    if mangled:
        lines.append("| Canonical | Mangled form | Count |")
        lines.append("|---|---|---|")
        for canonical, mangled_form, n in mangled:
            lines.append(f"| `{canonical}` | `{mangled_form}` | {n} |")
    else:
        lines.append("**No mangled names detected.**")
    lines.append("")

    # Section 3 — Welcome opening violations
    lines.append("## Welcome-opening violations · R-WELCOME (P0)")
    lines.append("")
    if welcome_hits:
        lines.append("| Phrase | Count |")
        lines.append("|---|---|")
        for p, n in welcome_hits:
            lines.append(f"| `{p}` | {n} |")
    else:
        lines.append("**None detected.**")
    lines.append("")

    # Section 4 — Modernization injections
    lines.append(f"## Modernization injections · R-NOMODERNIZE (P1) · density {per_kw(sum(n for _, n in modernize_hits))} per 1k words")
    lines.append("")
    if modernize_hits:
        lines.append("| Phrase | Count |")
        lines.append("|---|---|")
        for p, n in sorted(modernize_hits, key=lambda x: -x[1]):
            lines.append(f"| `{p.strip()}` | {n} |")
    else:
        lines.append("**None detected.**")
    lines.append("")

    # Section 5 — Surprise noise
    lines.append(f"## Surprise-noise loops · R-NOSURPRISE (P1) · density {per_kw(sum(n for _, n in surprise_hits))} per 1k words")
    lines.append("")
    if surprise_hits:
        lines.append("| Phrase | Count |")
        lines.append("|---|---|")
        for p, n in sorted(surprise_hits, key=lambda x: -x[1]):
            lines.append(f"| `{p.strip()}` | {n} |")
    else:
        lines.append("**None detected.**")
    lines.append("")

    # Section 6 — Honorific repetition
    lines.append("## Honorific repetitions · R-HONORIFIC-ONCE (P1)")
    lines.append("")
    lines.append("Each form allowed exactly once per chapter; the transcript should reflect ≤1 expansion per honorific phrase form.")
    lines.append("")
    if honorific_hits:
        lines.append("| Honorific form | Count |")
        lines.append("|---|---|")
        for p, n in sorted(honorific_hits, key=lambda x: -x[1]):
            lines.append(f"| `{p}` | {n} |")
    else:
        lines.append("**None detected.**")
    lines.append("")

    # Section 7 — Abbreviations
    lines.append("## Abbreviated work titles · R-NO-ABBREVIATION (P1)")
    lines.append("")
    if abbreviation_hits:
        lines.append("| Abbreviation | Count |")
        lines.append("|---|---|")
        for p, n in abbreviation_hits:
            lines.append(f"| `{p.strip()}` | {n} |")
    else:
        lines.append("**None detected.**")
    lines.append("")

    # Section 8 — Filler interjections
    lines.append(f"## Filler interjections · R-NOINTERRUPT (P2) · density {per_kw(sum(n for _, n in filler_hits))} per 1k words")
    lines.append("")
    if filler_hits:
        lines.append("| Phrase | Count |")
        lines.append("|---|---|")
        for p, n in sorted(filler_hits, key=lambda x: -x[1]):
            lines.append(f"| `{p.strip()}` | {n} |")
    else:
        lines.append("**None detected.**")
    lines.append("")

    # Section 9 — How to act on this report
    lines.append("## Remediation cheat sheet")
    lines.append("")
    lines.append("| Finding | Action |")
    lines.append("|---|---|")
    lines.append("| Phonetic doublings | Inspect chapter for surviving inline `(PHO-ne-tic)` parens; verify framing's `## Pronunciation` block uses imperative form per R-PRONUNCIATION-IMPERATIVE. |")
    lines.append("| Mangled names | Add explicit `Pronounce \"<canonical>\" as \"<phonetic>\". Say it as one fluent word.` line to the framing's Pronunciation block. Check `content/_shared/arabic/03-arabic-english-manifest.md` for canonical spelling. |")
    lines.append("| Welcome opening violations | Verify framing carries the R-WELCOME directive; tighten the Opening section to forbid the specific phrase. |")
    lines.append("| Modernization injections | Extend the framing's `## Do not` block with the specific phrase; confirm R-NOMODERNIZE canonical list is present. |")
    lines.append("| Surprise loops | Extend `## Do not` with the specific phrase; confirm R-NOSURPRISE canonical list is present. |")
    lines.append("| Honorific repetition | Audit chapter file with `assert_honorifics_once_only` in `build_episode_txt.py`; strip 2nd+ expansions. |")
    lines.append("| Abbreviated titles | Search-and-replace per the `FORBIDDEN_ABBREVIATIONS` map in `build_episode_txt.py`. |")
    lines.append("")

    report_dir = book_dir / "_system"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"audit-{episode_id}.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def main() -> None:
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        sys.exit(
            "Usage: audit_transcript.py <BOOK_DIR> <EP##-slug> [<transcript-file>]\n"
            "  When transcript-file is omitted, the default is\n"
            "  <BOOK_DIR>/turboscribe/<EP##-slug>.transcript.txt"
        )
    book_dir = Path(sys.argv[1]).resolve()
    episode_id = sys.argv[2]
    if not book_dir.is_dir():
        sys.exit(f"ERROR: BOOK_DIR is not a directory: {book_dir}")

    if len(sys.argv) == 4:
        transcript_path = Path(sys.argv[3]).resolve()
    else:
        transcript_path = book_dir / "turboscribe" / f"{episode_id}.transcript.txt"

    report_path = audit(book_dir, episode_id, transcript_path)
    print(f"Wrote audit report: {report_path}")


if __name__ == "__main__":
    main()
