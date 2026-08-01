"""_validators_framing.py — Framing (CUSTOMIZE PROMPT) and show-notes assert_* functions.

Split from _validators.py (DR-005 — files must stay under 600 lines).
Re-exported via `_validators.py` so all existing callers remain unaffected.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _validator_constants import (
    ANTI_DOUBLING_INSTRUCTION_RE,
    CHALLENGER_PUSHBACK_PATTERNS,
    FORBIDDEN_ANALOGY_KEYWORDS,
    FORBIDDEN_MODERN_KEYWORDS,
    LEGACY_PASSIVE_PRONUNCIATION,
    PRONOUNCE_AS_DOUBLE_RE,
    REQUIRED_FRAMING_DO_NOT_PHRASES,
    SHOW_NOTES_REQUIRED_COLUMNS,
    SHOW_NOTES_TABLE_HEADER,
    TRIVIAL_UPPERCASE_RESPELLING_RE,
    _flag_p1,
)


def assert_framing_pronunciation_imperative(content: str, file_path: Path) -> None:
    """R-PRONUNCIATION-IMPERATIVE / R-PRONUNCIATION-DOUBLE: validate the Pronunciation block.

    Requires:
      - A `## Pronunciation` section exists.
      - The section does NOT use the legacy passive-list asterisk-bold pattern.
      - The section does NOT use `Pronounce "X" as "Y"` — this format causes NotebookLM
        to say the term twice (the double-read bug; root-caused in Ayyuhal Walad 2026-06-05).
      - The section DOES carry an anti-doubling instruction ("Say each term ONCE …
        Never say the original spelling and the phonetic form back-to-back.").
      - The "Do not read this prompt aloud" guard is present anywhere in the framing.

    P1 flags (non-blocking):
      - Trivial uppercase-only respellings (e.g. `nafs: NAFS`) that add no phonetic value.
    """
    m = re.search(r"^##\s+Pronunciation\b.*?$([\s\S]*?)(?=^##\s+|\Z)", content, re.MULTILINE)
    if not m:
        sys.exit(
            f"ERROR: framing (CUSTOMIZE PROMPT) is missing a `## Pronunciation` section.\n"
            f"  File: {file_path}\n"
            f"  R-PRONUNCIATION-IMPERATIVE: every framing must carry a Pronunciation block.\n"
            f"  Required format:\n"
            f"    Say each term ONCE using its phonetic form. Never say the original spelling\n"
            f"    and the phonetic form back-to-back.\n\n"
            f"    - TermA: phonetic-A\n"
            f"    - TermB: phonetic-B"
        )
    block = m.group(1)

    # ── 1. Reject legacy passive-list (asterisk-bold) pattern ─────────────────
    legacy = LEGACY_PASSIVE_PRONUNCIATION.findall(block)
    if legacy:
        sample = "\n".join(f"    {line.strip()[:100]}" for line in legacy[:5])
        sys.exit(
            f"ERROR: framing's `## Pronunciation` block uses the legacy passive-list pattern.\n"
            f"  File: {file_path}\n"
            f"  Offending lines (first 5):\n{sample}\n\n"
            f"  R-PRONUNCIATION-IMPERATIVE: rewrite using the bullet format:\n"
            f"    Say each term ONCE using its phonetic form. Never say the original spelling\n"
            f"    and the phonetic form back-to-back.\n\n"
            f"    - TermA: phonetic-A\n"
            f"  The passive list does not change NotebookLM voice-model behavior — empirically\n"
            f"  hosts said 'tassel wolf' for *Tasawwuf* across three episodes."
        )

    # ── 2. Reject "Pronounce X as Y" format — causes TTS double-read ──────────
    bad_lines = PRONOUNCE_AS_DOUBLE_RE.findall(block)
    if bad_lines:
        sample = "\n".join(f"    {ln.strip()[:120]}" for ln in bad_lines[:5])
        sys.exit(
            f'ERROR: framing\'s `## Pronunciation` block uses the `Pronounce "X" as "Y"` format.\n'
            f"  File: {file_path}\n"
            f"  Offending lines (first 5):\n{sample}\n\n"
            f"  R-PRONUNCIATION-DOUBLE: this format causes NotebookLM to say the term AND its\n"
            f'  respelling back-to-back (e.g. "tahajjud, Tahajjud"). Replace with:\n\n'
            f"    Say each term ONCE using its phonetic form. Never say the original spelling\n"
            f"    and the phonetic form back-to-back.\n\n"
            f"    - TermA: phonetic-A\n"
            f"    - TermB: phonetic-B  (or: substitute *English gloss*)\n\n"
            f"  For substitute-only terms (no phonetic guidance needed), write:\n"
            f"    - nafs: substitute *the lower self*"
        )

    # ── 3. Require anti-doubling instruction ──────────────────────────────────
    if not ANTI_DOUBLING_INSTRUCTION_RE.search(block):
        sys.exit(
            f"ERROR: framing's `## Pronunciation` block is missing the anti-doubling instruction.\n"
            f"  File: {file_path}\n"
            f"  R-PRONUNCIATION-IMPERATIVE: the block must open with:\n"
            f"    Say each term ONCE using its phonetic form. Never say the original spelling\n"
            f"    and the phonetic form back-to-back.\n"
            f"  This instruction prevents NotebookLM from reading the term twice."
        )

    # ── 3b. Require at least one bullet-list entry (- term: phonetic) ───────────
    # The anti-doubling instruction alone is not enough — the block must also
    # carry at least one bullet entry so there is actual pronunciation guidance.
    # A block with only the instruction line and no entries passes the instruction
    # check but gives NotebookLM nothing to work with.
    _has_bullet = re.search(r"^\s*-\s+\S", block, re.MULTILINE)
    _has_do_not_voice = re.search(r"(?i)do\s+not\s+voice", block)
    if not _has_bullet and not _has_do_not_voice:
        sys.exit(
            f"ERROR: framing's `## Pronunciation` block has the anti-doubling instruction\n"
            f"  but no pronunciation entries or 'Do not voice' directive.\n"
            f"  File: {file_path}\n"
            f"  R-PRONUNCIATION-IMPERATIVE: add at least one bullet entry:\n"
            f"    - TermA: phonetic-A\n"
            f"    - TermB: substitute *English gloss*"
        )

    # ── 4. P1 flag: trivial uppercase-only respellings ────────────────────────
    for lm in TRIVIAL_UPPERCASE_RESPELLING_RE.finditer(block):
        term = lm.group(1).strip()
        phon = lm.group(2).strip()
        if term.lower().replace("-", "").replace(" ", "").replace("'", "") == phon.lower().replace("-", "").replace(
            " ", ""
        ).replace("'", ""):
            _flag_p1(
                "R-PRONUNCIATION-TRIVIAL",
                file_path,
                f"`{term}: {phon}` is a trivial uppercase respelling — it adds no phonetic value. "
                f"Either provide a genuine respelling (e.g. `{term}: {term.lower()}-STRESSED`) "
                f"or drop the entry entirely.",
            )

    # ── 5. No-read-aloud guard ────────────────────────────────────────────────
    if "Do not read this guidance aloud" not in content and "Do not read this prompt aloud" not in content:
        sys.exit(
            f"ERROR: framing missing the no-read-aloud guard.\n"
            f"  File: {file_path}\n"
            f"  R-NO-READ-PROMPT: framing must end with:\n"
            f"  `Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.`"
        )


_PRONUNCIATION_ENTRY_RE = re.compile(r"^\s*-\s+([^:\n]{1,60}?)\s*:\s*(.+?)\s*$", re.MULTILINE)
# An English translation, not a spoken form. Every instance that shipped in the
# 2026-08-01 run led with a determiner — "the pillars", "the one surpassed",
# "the one preceded" — and no Arabic transliteration or respelling ever does.
_GLOSS_SHAPED_VALUE = re.compile(r"^(?:the|an?)\s+\S", re.IGNORECASE)
# A row the human deliberately marked as a substitution is not a defect.
_EXPLICIT_SUBSTITUTE = re.compile(r"^substitute\b", re.IGNORECASE)


def assert_framing_pronunciation_render(
    content: str,
    file_path: Path,
    book_dir: Path | None = None,
    chapter_text: str | None = None,
) -> None:
    """R-PRONUNCIATION-RENDER: no English translation in the value slot.

    Companion to ``_pronunciation_block.apply_to_framing``. On the normal path
    the compiler has already replaced every value, so this passes by
    construction; it earns its place on the degrade path, where a book with
    nothing settled keeps its authored block and this is the only thing standing
    between `- arkan: the pillars` and the audio.

    An English substitute is allowed when the LADDER produces it — a ledger
    gloss, an exonym, an explicit ``substitute`` row. So a gloss-shaped value is
    only an error when it DISAGREES with what the ladder independently resolves
    for that term. Skipped entirely without a book dir or chapter text, since
    there is then nothing to resolve against.
    """
    if book_dir is None or chapter_text is None:
        return
    m = re.search(r"^##\s+Pronunciation\b.*?$([\s\S]*?)(?=^##\s+|\Z)", content, re.MULTILINE)
    if not m:
        return  # absence is the imperative gate's error to report, not this one
    try:
        import sys as _sys

        _sys.path.insert(0, str(Path(__file__).resolve().parent))
        from _pronunciation_block import compile_entries
    except ImportError:
        return  # the compiler is the authority; without it there is nothing to check

    resolved = {t.strip().lower(): v for t, v in compile_entries(book_dir, chapter_text, m.group(1))[0]}

    offenders: list[str] = []
    for em in _PRONUNCIATION_ENTRY_RE.finditer(m.group(1)):
        term, value = em.group(1).strip(), em.group(2).strip()
        if _EXPLICIT_SUBSTITUTE.match(value):
            continue
        if not _GLOSS_SHAPED_VALUE.match(value):
            continue
        if resolved.get(term.lower(), "").strip().lower() == value.lower():
            continue  # the ladder chose this English itself
        offenders.append(f"- {term}: {value}")

    if offenders:
        sample = "\n".join(f"    {o}" for o in offenders[:6])
        sys.exit(
            f"ERROR: framing's `## Pronunciation` block puts an English translation in the\n"
            f"  value slot — the slot the block's own instruction calls a phonetic.\n"
            f"  File: {file_path}\n"
            f"  Offending entries (first 6):\n{sample}\n\n"
            f"  R-PRONUNCIATION-RENDER: the hosts are told to say each term ONCE using the\n"
            f"  form given here. Hand them a translation and they try to pronounce it —\n"
            f"  this is how *arkan* was spoken as 'Archon' and *masbuq* as 'Mazbuck'.\n\n"
            f"  Fix by giving the term a settled spoken form, in order of preference:\n"
            f"    1. Add a row to {book_dir}/_system/pronunciation.md — the build then\n"
            f"       compiles the value and the authored text stops mattering.\n"
            f"    2. Settle it by ear:\n"
            f"       python3 scripts/podcast/run_pronunciation_probe.py <book-slug>\n"
            f"    3. If the term genuinely should be spoken in English, mark it as a\n"
            f"       substitution so the intent is explicit:\n"
            f"         - {offenders[0].split(':')[0].lstrip('- ')}: substitute *{offenders[0].split(':', 1)[1].strip()}*"
        )


def assert_framing_analogy_cap_strict(content: str, file_path: Path) -> None:
    """F27 #3: detect forbidden analogies in framing.md."""
    scan_text = content.lower()
    scan_text_scrubbed = re.sub(
        r"###?\s+(?:explicitly\s+)?forbidden\s+analogies.*?(?=\n##\s|\n###\s|\Z)",
        "",
        scan_text,
        flags=re.DOTALL,
    )
    violations = [k for k in FORBIDDEN_ANALOGY_KEYWORDS if k in scan_text_scrubbed]
    if violations:
        _flag_p1(
            "R-ANALOGY-CAP-STRICT",
            file_path,
            f"framing: forbidden analogy patterns detected: {violations[:8]}. "
            f"Allowed: mirror, messenger, light-on-glass-stone, source-images only.",
        )


def assert_framing_no_modern_artifacts(content: str, file_path: Path) -> None:
    """F27 #4: detect modern-vocabulary contamination in framing.md."""
    scan_text = content.lower()
    scan_text_scrubbed = re.sub(
        r"##\s+\d*\.?\s*R-NOMODERNIZE.*?(?=\n##\s|\Z)",
        "",
        scan_text,
        flags=re.DOTALL,
    )
    scan_text_scrubbed = re.sub(
        r"##\s+do not\s*\(forbidden vocabulary.*?(?=\n##\s|\Z)",
        "",
        scan_text_scrubbed,
        flags=re.DOTALL,
    )
    violations = [k for k in FORBIDDEN_MODERN_KEYWORDS if k in scan_text_scrubbed]
    if violations:
        _flag_p1(
            "R-NOMODERNIZE-STRICT",
            file_path,
            f"framing: modern artifacts detected: {violations[:8]}. "
            f"R-NOMODERNIZE: tenth-century metaphysics — no modern vocabulary.",
        )


def assert_framing_honorific_bounded_both_sides(content: str, file_path: Path) -> None:
    """F27 #5: each honorific appears EXACTLY ONCE."""
    scan_text_lower = content.lower()
    scan_text_lower = re.sub(
        r"##?\s*\d*\.?\s*R-HONORIFIC-ONCE.*?(?=\n##\s|\Z)",
        "",
        scan_text_lower,
        flags=re.DOTALL,
    )
    scan_text_lower = re.sub(
        r"##?\s*\d*\.?\s*Honorific\s+(?:1|2|discipline).*?(?=\n##\s|\Z)",
        "",
        scan_text_lower,
        flags=re.DOTALL,
    )

    pbuh_count = scan_text_lower.count("peace be upon him")
    pbuhf_count = scan_text_lower.count("peace and blessings of allah be upon him and his family")

    issues: list[str] = []
    if pbuh_count != 1:
        issues.append(
            f"'peace be upon him' occurs {pbuh_count}× (must equal 1; first mention of Commander of the Faithful)"
        )
    if pbuhf_count != 1:
        issues.append(
            f"'peace and blessings of Allah...' occurs {pbuhf_count}× (must equal 1; first mention of the Prophet)"
        )

    if issues:
        _flag_p1("R-HONORIFIC-BOTH-BOUNDS", file_path, "framing: " + "; ".join(issues))


def assert_show_notes_has_apparatus_table(content: str, file_path: Path) -> None:
    """F27 #8 / F25: 99-show-notes.md must contain a structured apparatus table."""
    if SHOW_NOTES_TABLE_HEADER not in content:
        _flag_p1(
            "F25-APPARATUS-TABLE",
            file_path,
            f"no '{SHOW_NOTES_TABLE_HEADER}' section header found. "
            f"F25 doctrine: every episode's 99-show-notes.md carries the "
            f"written-layer apparatus (preserved Arabic / transliterations + "
            f"audio-label crosswalk) the TTS-safe audio omits.",
        )
        return
    missing = [col for col in SHOW_NOTES_REQUIRED_COLUMNS if col not in content]
    if missing:
        _flag_p1(
            "F25-APPARATUS-TABLE",
            file_path,
            f"apparatus table missing required columns: {missing}. Required: {list(SHOW_NOTES_REQUIRED_COLUMNS)}.",
        )


def assert_framing_has_name_discipline_section(content: str, file_path: Path) -> None:
    """R-NAMEDISCIPLINE: framing has a Name discipline section with rotation sets."""
    has_section = bool(re.search(r"^##\s+Name\s+discipline\b", content, re.MULTILINE | re.IGNORECASE)) or bool(
        re.search(r"^Name\s+discipline\b", content, re.MULTILINE | re.IGNORECASE)
    )
    if not has_section:
        _flag_p1(
            "R-NAMEDISCIPLINE",
            file_path,
            "no `## Name discipline` section found. Add a Name discipline "
            "section listing each figure's full Arabic name (once on first "
            "mention) + 3-4 English alias rotation set. See handbook: "
            "notebooklm-customize-prompt-rules.md R-NAMEDISCIPLINE.",
        )
        return
    has_rotation = bool(
        re.search(
            r"(Rotation:|→)\s*[A-Za-z][^\n]*?[/,][^\n]*?[/,]",
            content,
        )
    )
    if not has_rotation:
        _flag_p1(
            "R-NAMEDISCIPLINE",
            file_path,
            "Name discipline section found but no rotation set with 3+ aliases "
            "(`Rotation: a / b / c` or `→ a / b / c`). See handbook.",
        )


def assert_framing_dramatic_arc_structure(content: str, file_path: Path) -> None:
    """R-DRAMATIC-ARC: debate-format framings declare a multi-beat arc."""
    beat_markers = re.findall(r"\bBeat\s+\d+\b", content)
    distinct_beats = set(beat_markers)
    has_six_beats = len(distinct_beats) >= 6

    structure_tells = ["crisis", "failed answer", "pivot", "stakes"]
    lower = content.lower()
    structure_hits = sum(1 for t in structure_tells if t in lower)
    has_structure_declaration = structure_hits >= 3

    if not (has_six_beats or has_structure_declaration):
        _flag_p1(
            "R-DRAMATIC-ARC",
            file_path,
            f"no 6-beat dramatic arc detected — found {len(distinct_beats)} "
            f"distinct Beat markers AND only {structure_hits}/4 structure "
            f"tells (crisis / failed answer / pivot / stakes). Restructure "
            f"`## Three-part focus` as a 6-beat arc. See handbook: "
            f"notebooklm-customize-prompt-rules.md R-DRAMATIC-ARC.",
        )


def assert_framing_challenger_friction_lists_patterns(content: str, file_path: Path) -> None:
    """R-CHALLENGER-FRICTION: framing names challenger role + ≥2 pushback patterns."""
    has_host_dynamic = bool(re.search(r"^##\s+Host\s+dynamic\b", content, re.MULTILINE | re.IGNORECASE))
    has_central_tensions = bool(re.search(r"^##\s+Central\s+tensions\b", content, re.MULTILINE | re.IGNORECASE))
    if not (has_host_dynamic or has_central_tensions):
        _flag_p1(
            "R-CHALLENGER-FRICTION",
            file_path,
            "no `## Host dynamic` or `## Central tensions` section found — the "
            "challenger-friction clause cannot be placed. See handbook: "
            "notebooklm-customize-prompt-rules.md R-CHALLENGER-FRICTION.",
        )
        return
    lower = content.lower()
    has_challenger_role = any(t in lower for t in ("challenger", "pushback", "friction"))
    seen_bases = set()
    for p in CHALLENGER_PUSHBACK_PATTERNS:
        if p in content:
            base = p.replace("’", "'")
            seen_bases.add(base)
    distinct_patterns = len(seen_bases)

    if not has_challenger_role or distinct_patterns < 2:
        missing = []
        if not has_challenger_role:
            missing.append("no `challenger` / `pushback` / `friction` language in Host dynamic or Central tensions")
        if distinct_patterns < 2:
            missing.append(
                f"only {distinct_patterns} of the required pushback patterns found (need ≥2): "
                f"I don't buy that yet… / That sounds like wordplay… / Isn't this just replacing… / "
                f"How is this different…"
            )
        _flag_p1(
            "R-CHALLENGER-FRICTION",
            file_path,
            "; ".join(missing) + ". See handbook: notebooklm-customize-prompt-rules.md R-CHALLENGER-FRICTION.",
        )


def assert_framing_analogy_cap_declared(content: str, file_path: Path) -> None:
    """R-ANALOGY-CAP: framing's Tone constraints declares 3-5 governing analogies."""
    m = re.search(
        r"^##\s+Tone(?:\s+constraints)?\b.*?$([\s\S]*?)(?=^##\s+|\Z)",
        content,
        re.MULTILINE | re.IGNORECASE,
    )
    if not m:
        _flag_p1(
            "R-ANALOGY-CAP",
            file_path,
            "no `## Tone constraints` section found — cannot validate analogy "
            "enumeration. See handbook: notebooklm-customize-prompt-rules.md "
            "R-ANALOGY-CAP.",
        )
        return
    tone_block = m.group(1)
    analogy_lines = re.findall(
        r"(?:^|\n)\s*[-*]?\s*\*{0,2}Analogy\s+\d+\b",
        tone_block,
        re.IGNORECASE,
    )
    n_analogies = len(analogy_lines)
    if n_analogies == 0:
        _flag_p1(
            "R-ANALOGY-CAP",
            file_path,
            "no governing-analogy enumeration found in `## Tone constraints`. "
            "Enumerate 3-5 analogies, each tied to a beat. See handbook: "
            "notebooklm-customize-prompt-rules.md R-ANALOGY-CAP.",
        )
        return
    if n_analogies < 3 or n_analogies > 5:
        _flag_p1(
            "R-ANALOGY-CAP",
            file_path,
            f"found {n_analogies} governing analogies in `## Tone constraints`; "
            f"required range is 3-5 inclusive. See handbook: "
            f"notebooklm-customize-prompt-rules.md R-ANALOGY-CAP.",
        )


def assert_framing_recurring_thesis_present(content: str, file_path: Path, contract_anchor: str | None = None) -> None:
    """R-RECURRING-THESIS: framing references the chapter's central thesis 3×."""
    if contract_anchor:
        count = content.count(contract_anchor)
        if count < 3:
            _flag_p1(
                "R-RECURRING-THESIS",
                file_path,
                f"contract anchor thesis found {count}× in framing; "
                f"R-RECURRING-THESIS requires VERBATIM appearance ≥3× "
                f"(open + pivot + close). Thesis (first 80 chars): "
                f"{contract_anchor[:80]!r}. See handbook: "
                f"notebooklm-customize-prompt-rules.md R-RECURRING-THESIS.",
            )
            return
        return
    has_rule_ref = "R-RECURRING-THESIS" in content
    has_three_times = bool(
        re.search(
            r"\b(three|3)\s+times\b.*?\b(verbatim|verbatim,)",
            content,
            re.IGNORECASE | re.DOTALL,
        )
    ) or bool(
        re.search(
            r"\bverbatim\b.*?\b(three|3)\s+times\b",
            content,
            re.IGNORECASE | re.DOTALL,
        )
    )
    if not (has_rule_ref and has_three_times):
        _flag_p1(
            "R-RECURRING-THESIS",
            file_path,
            "no contract anchor was provided AND framing lacks both an "
            "R-RECURRING-THESIS rule reference and a 'verbatim … three times' "
            "instruction. Add the rule clause to `## Anti-noise rules`. "
            "See handbook: notebooklm-customize-prompt-rules.md "
            "R-RECURRING-THESIS.",
        )


def assert_framing_deny_block(content: str, file_path: Path) -> None:
    """R-NOMODERNIZE + R-NOSURPRISE + R-NO-READ-PROMPT: framing carries a `## Do not` block."""
    if not re.search(r"^##\s+Do not\b", content, re.MULTILINE):
        sys.exit(
            f"ERROR: framing missing the `## Do not (forbidden vocabulary and framings)` section.\n"
            f"  File: {file_path}\n"
            f"  R-NOMODERNIZE + R-NOSURPRISE: every framing must include a DENY block\n"
            f"  listing modernization terms (Twitter, X, social media, algorithm, ...) and\n"
            f"  surprise-noise phrases ('wow', 'right?', 'it's chilling', ...). The block\n"
            f"  is the structural fix for empirically-observed host drift away from\n"
            f"  faithful exposition into modern analogies and surprise loops.\n"
            f"  See scripts/podcast/_rules.py (rules R-PRONUNCIATION-IMPERATIVE, R-NOMODERNIZE, etc.)."
        )
    missing = [p for p in REQUIRED_FRAMING_DO_NOT_PHRASES if p not in content]
    if missing:
        sys.exit(
            f"ERROR: framing's DENY block is missing required entries: {missing}\n"
            f"  File: {file_path}\n"
            f"  See R-NOMODERNIZE / R-NOSURPRISE / R-NO-READ-PROMPT for the canonical list."
        )
