"""_validators.py — Chapter validators, structural helpers, and re-exports.

Three-file split (DR-005 — files must stay under 600 lines):
  _validator_constants.py  — all rule constants + P1 flags + small helpers
  _validators_framing.py   — framing (CUSTOMIZE PROMPT) assert_* functions
  _validators.py (this)    — chapter assert_* + structural helpers + re-exports

Everything is re-exported from build_episode_txt.py via `from _validators import *`
so all existing callers remain unaffected.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _validator_constants import *  # noqa: F401, F403
from _validator_constants import (
    META_PROSE_TELLS, META_PROSE_REGEX_TELLS,
    INLINE_PHONETIC_PATTERNS, FORBIDDEN_ABBREVIATIONS,
    HONORIFIC_PHRASES, ARABIC_TRANSLIT_PATTERNS,
    ALLOWED_ARABIC_ORIGIN_LOWER, KNOWN_SURAH_NAMES_LOWER,
    FORBIDDEN_LITERAL_ALQAAB, MANUSCRIPT_META_TELLS,
    MANUSCRIPT_META_HEADER_RE, CH_PATTERN,
    HOST_A_ROLES_SCHOLAR, HOST_B_ROLES_SEEKER,
    _flag_p1, _is_rule_example_line,
)
from _validators_framing import *  # noqa: F401, F403


# ─── assert_* functions — chapter (SOURCE) ────────────────────────────────────

def assert_no_meta_prose(content: str, file_path: Path, role: str,
                         extra_tells: list[str] | None = None) -> None:
    """Refuse to build if content contains meta-prose tells."""
    lower = content.lower()
    all_tells = META_PROSE_TELLS + list(extra_tells or [])
    lines = content.splitlines()

    substring_hits: list[str] = []
    for tell in all_tells:
        if tell not in lower:
            continue
        any_real_leak = False
        for line in lines:
            if tell in line.lower() and not _is_rule_example_line(line, tell):
                any_real_leak = True
                break
        if any_real_leak:
            substring_hits.append(tell)
    regex_hits = []
    for pat in META_PROSE_REGEX_TELLS:
        for m in re.finditer(pat, content, flags=re.IGNORECASE):
            regex_hits.append((pat, m.group(0)))
    if not (substring_hits or regex_hits):
        return

    offending = []
    for tell in substring_hits:
        for ln, line in enumerate(lines, 1):
            if tell in line.lower() and not _is_rule_example_line(line, tell):
                offending.append(f"  {file_path.name}:{ln}: {line.strip()[:120]}")
                break
    for pat, matched in regex_hits[:5]:
        for ln, line in enumerate(lines, 1):
            if re.search(pat, line, flags=re.IGNORECASE):
                offending.append(f"  {file_path.name}:{ln} (regex {pat!r} matched {matched!r}): {line.strip()[:120]}")
                break

    joined = "\n".join(offending[:10])
    tells_summary = ", ".join(repr(h) for h in substring_hits)
    if regex_hits:
        tells_summary += " | regex: " + ", ".join(repr(p) for p, _ in regex_hits[:5])
    sys.exit(
        f"ERROR: {role} file contains meta-prose that would reach NotebookLM.\n"
        f"  Tells found: {tells_summary}\n"
        f"  Offending lines:\n{joined}\n\n"
        f"  Chapter files are uploaded as-is to NotebookLM as the SOURCE — meta inside\n"
        f"  the file is read literally by the hosts. Authoring metadata belongs in\n"
        f"  `BOOK_DIR/_system/enrichment-log.md`, NOT inline.\n"
        f"  Framing files are pasted as-is into NotebookLM's Customize box — meta there\n"
        f"  becomes steering noise.\n"
        f"  See skills-staging/podcast/SKILL.md §6 Output Rules."
    )


def assert_no_html_comments(content: str, file_path: Path, role: str) -> None:
    if has_html_comments(content):  # type: ignore[name-defined]  # noqa: F821
        sys.exit(
            f"ERROR: {role} file contains HTML comments (`<!-- ... -->`).\n"
            f"  File: {file_path}\n"
            f"  Chapter files are uploaded as-is to NotebookLM as the SOURCE. HTML\n"
            f"  comments would be read literally by the hosts. Move authoring metadata\n"
            f"  to `BOOK_DIR/_system/enrichment-log.md` and remove the inline comment.\n"
            f"  Framing files are pasted as-is into Customize box; same constraint.\n"
            f"  (build_episode_txt.py does NOT strip — it refuses, so the chapter file\n"
            f"  is always upload-ready.)"
        )


def assert_no_inline_phonetics(content: str, file_path: Path) -> None:
    """R-PHONETICS-OUT: chapter must not carry inline phonetic guides."""
    hits: list[tuple[int, str]] = []
    for pat in INLINE_PHONETIC_PATTERNS:
        for m in pat.finditer(content):
            ln = content[: m.start()].count("\n") + 1
            line = content.splitlines()[ln - 1] if ln - 1 < len(content.splitlines()) else ""
            hits.append((ln, line.strip()[:120]))
    if not hits:
        return
    joined = "\n".join(f"  {file_path.name}:{ln}: {line}" for ln, line in hits[:10])
    sys.exit(
        f"ERROR: chapter (SOURCE) file contains inline phonetic guides.\n"
        f"  Hits ({len(hits)} found; first 10 shown):\n{joined}\n\n"
        f"  R-PHONETICS-OUT (2026-05-17): chapter files must not carry inline\n"
        f"  `*Term* (PHO-ne-tic; gloss)` parens or post-transliteration phonetic\n"
        f"  blockquote lines. NotebookLM reads them aloud as content — empirically\n"
        f"  producing 'Sahih Sitta, sahasita' doublings and mangled names like\n"
        f"  'tassel wolf' for *Tasawwuf*. Move every phonetic into the matching\n"
        f"  framing's `## Pronunciation` block as an imperative line:\n"
        f"      Pronounce \"Tasawwuf\" as \"ta-SAW-wuf\". Say it as one fluent word.\n"
        f"  See scripts/podcast/_rules.py (rules R-PHONETICS-OUT, R-NO-ABBREVIATION, etc.)\n"
        f"  R-PHONETICS-OUT and notebooklm-customize-prompt-rules.md\n"
        f"  R-PRONUNCIATION-IMPERATIVE."
    )


def assert_no_abbreviations(content: str, file_path: Path) -> None:
    """R-NO-ABBREVIATION: chapter must spell out canonical work titles."""
    hits: list[tuple[int, str, str]] = []
    for pat, label in FORBIDDEN_ABBREVIATIONS.items():
        for m in re.finditer(pat, content):
            ln = content[: m.start()].count("\n") + 1
            line = content.splitlines()[ln - 1] if ln - 1 < len(content.splitlines()) else ""
            hits.append((ln, label, line.strip()[:120]))
    if not hits:
        return
    joined = "\n".join(f"  {file_path.name}:{ln}: {label} → in: {line}" for ln, label, line in hits[:10])
    sys.exit(
        f"ERROR: chapter (SOURCE) file contains abbreviated work titles.\n"
        f"  Hits:\n{joined}\n\n"
        f"  R-NO-ABBREVIATION: listeners cannot resolve unfamiliar contractions.\n"
        f"  Use the full canonical title every time. See\n"
        f"  scripts/podcast/_rules.py (rules R-PHONETICS-OUT, R-NO-ABBREVIATION, etc.) R-NO-ABBREVIATION."
    )


def assert_honorifics_once_only(content: str, file_path: Path) -> None:
    """R-HONORIFIC-ONCE: each honorific phrase form expanded ≤1 time per chapter."""
    over: list[tuple[str, int]] = []
    for pat in HONORIFIC_PHRASES:
        n = len(pat.findall(content))
        if n > 1:
            over.append((pat.pattern, n))
    if not over:
        return
    joined = "\n".join(f"  '{pat}' appears {n} times" for pat, n in over)
    sys.exit(
        f"ERROR: chapter (SOURCE) file repeats honorific expansions.\n"
        f"  File: {file_path}\n"
        f"  Repeated honorifics (allowed once per chapter per form):\n{joined}\n\n"
        f"  R-HONORIFIC-ONCE: expand each honorific exactly once per figure on\n"
        f"  first mention; subsequent mentions use the contracted name only\n"
        f"  ('the Prophet', 'Imam Ali'). NotebookLM reads every expansion aloud\n"
        f"  — empirically: 9 expansions of '(peace and blessings be upon him)'\n"
        f"  in a single audited episode. See\n"
        f"  scripts/podcast/_rules.py (rules R-PHONETICS-OUT, R-NO-ABBREVIATION, etc.)\n"
        f"  R-HONORIFIC-ONCE."
    )


def assert_no_arabic_transliteration(content: str, file_path: Path, role: str) -> None:
    """F27 #1+#2: block Arabic transliterations in chapter prose or framing."""
    scan_text = content
    if role.startswith("framing"):
        scan_text = re.sub(
            r"##?\s*\d*\.?\s*Pronunciation.*?(?=\n##\s|\Z)",
            "",
            content,
            flags=re.DOTALL | re.IGNORECASE,
        )

    violations: list[str] = []
    for pattern in ARABIC_TRANSLIT_PATTERNS:
        for match in pattern.finditer(scan_text):
            token = match.group(0)
            if token.lower() in ALLOWED_ARABIC_ORIGIN_LOWER:
                continue
            if any(allowed in token.lower() for allowed in ALLOWED_ARABIC_ORIGIN_LOWER):
                continue
            violations.append(token)

    if violations:
        unique = sorted(set(violations))
        sample = unique[:8]
        _flag_p1(
            "R-NO-ARABIC-TRANSLITERATION",
            file_path,
            f"{role}: {len(unique)} Arabic transliterations detected. "
            f"Sample: {sample}. F20 doctrine: replace with English audio labels."
        )


def assert_no_arabic_surah_names(content: str, file_path: Path, role: str) -> None:
    """F27 #6: detect Arabic surah names. F29 doctrine: use English meanings."""
    scan_text = content.lower()
    scan_text_scrubbed = re.sub(
        r"##?\s*\d*\.?\s*(?:R-SURAH|surah\s+(?:lookup|reference|names)).*?(?=\n##\s|\Z)",
        "",
        scan_text,
        flags=re.DOTALL,
    )
    violations: list[str] = []
    for surah in KNOWN_SURAH_NAMES_LOWER:
        if surah in scan_text_scrubbed:
            violations.append(surah)
    if violations:
        _flag_p1(
            "R-SURAH-ENGLISH-ONLY",
            file_path,
            f"{role}: Arabic surah names detected: {sorted(violations)[:8]}. "
            f"F29 doctrine: use English meanings ('the chapter on the sun' etc.)."
        )


def assert_alqaab_only_established_or_paraphrased(content: str, file_path: Path, role: str) -> None:
    """F27 #7: block awkward literal alqaab translations."""
    scan_text_lower = content.lower()
    violations = [k for k in FORBIDDEN_LITERAL_ALQAAB if k in scan_text_lower]
    if violations:
        _flag_p1(
            "R-ALQAAB-FUNCTIONAL-PARAPHRASE",
            file_path,
            f"{role}: literal alqaab translations detected: {violations}. "
            f"F24 doctrine: use functional paraphrase ('one of his martial honorifics')."
        )


def assert_chapter_no_manuscript_meta(content: str, file_path: Path) -> None:
    """R-NO-MANUSCRIPT-META: chapter source carries no manuscript-history meta."""
    hits: list[tuple[int, str, str]] = []
    lines = content.splitlines()
    lower_lines = [ln.lower() for ln in lines]
    for tell in MANUSCRIPT_META_TELLS:
        tell_lower = tell.lower()
        for ln_idx, ln_lower in enumerate(lower_lines):
            if tell_lower in ln_lower:
                hits.append((ln_idx + 1, tell, lines[ln_idx].strip()[:120]))
                break
    for m in MANUSCRIPT_META_HEADER_RE.finditer(content):
        ln_idx = content[: m.start()].count("\n")
        hits.append((ln_idx + 1, m.group(0).strip()[:80], lines[ln_idx].strip()[:120]))
    if not hits:
        return
    joined = "\n    ".join(f"{file_path.name}:{ln}: '{phrase}' in: {context}"
                          for ln, phrase, context in hits[:10])
    _flag_p1(
        "R-NO-MANUSCRIPT-META", file_path,
        f"chapter contains {len(hits)} manuscript-history meta-prose hit(s). "
        f"NotebookLM would voice these as content. Move manuscript-state "
        f"context to `BOOK_DIR/_system/manuscript-history.md`.\n    {joined}\n"
        f"  See handbook: notebooklm-source-chapter-rules.md "
        f"R-NO-MANUSCRIPT-META."
    )


# ─── Structural helpers ───────────────────────────────────────────────────────

def validate_host_role_parity(contract: dict) -> list[str]:
    """R-HOST-ROLE-PARITY (Q4) — deterministic host-pairing gate."""
    findings: list[str] = []
    debate = (contract or {}).get("debate") or {}
    if not isinstance(debate, dict) or not debate:
        return findings
    host_a = (debate.get("host_a") or {}).get("role", "")
    host_b = (debate.get("host_b") or {}).get("role", "")
    if host_a and host_a.lower() not in {r.lower() for r in HOST_A_ROLES_SCHOLAR}:
        findings.append(
            f"R-HOST-ROLE-PARITY (Q4): contract.debate.host_a.role={host_a!r} not in "
            f"scholar pool {HOST_A_ROLES_SCHOLAR}. Host A (male voice) must be in the "
            f"scholar/teacher pool. If contract assigns the scholar role to Host B, "
            f"swap the assignments so the male voice carries the scholar role."
        )
    if host_b and host_b.lower() not in {r.lower() for r in HOST_B_ROLES_SEEKER}:
        findings.append(
            f"R-HOST-ROLE-PARITY (Q4): contract.debate.host_b.role={host_b!r} not in "
            f"seeker pool {HOST_B_ROLES_SEEKER}. Host B (female voice) must be in the "
            f"seeker/student/debater pool."
        )
    return findings


def assert_chapters_populated(book_dir: Path) -> list[Path]:
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.is_dir():
        sys.exit(
            f"ERROR: missing chapters/ directory: {chapters_dir}\n"
            f"  Episodes cannot exist without source-book chapters. "
            f"Run Phase 0 (SKILL.md §1.5) to design and enrich chapters first."
        )
    txt_files = sorted(chapters_dir.glob("*.txt"))
    if not txt_files:
        sys.exit(
            f"ERROR: chapters/ is empty: {chapters_dir}\n"
            f"  Episodes cannot exist without source-book chapters. "
            f"Run Phase 0 (SKILL.md §1.5) to design and enrich chapters first."
        )
    return txt_files


def find_chapter_by_slug(chapters_dir: Path, episode_slug: str, required: bool = True) -> "Path | None":
    candidates = []
    if chapters_dir.is_dir():
        for f in sorted(chapters_dir.glob("*.txt")):
            m = CH_PATTERN.match(f.name)
            if m and m.group(2) == episode_slug:
                candidates.append(f)
    if not candidates:
        if not required:
            return None
        existing = ", ".join(f.name for f in sorted(chapters_dir.glob("*.txt")))
        sys.exit(
            f"ERROR: no chapter file matches slug '{episode_slug}' in {chapters_dir}\n"
            f"  Expected: ch??-{episode_slug}.txt\n"
            f"  Existing chapters: {existing}\n"
            f"  Under the 1:1 chapter ↔ episode mapping (SKILL.md §0), the episode "
            f"slug after 'EP##-' must match the chapter slug after 'ch##-' exactly."
        )
    if len(candidates) > 1:
        sys.exit(
            f"ERROR: multiple chapter files match slug '{episode_slug}': "
            f"{[c.name for c in candidates]}. Resolve the duplicate before building."
        )
    return candidates[0]


def _resolve_book_tradition(file_path: Path) -> str:
    """F34 (2026-05-25): walk up from `file_path` to find series-config.yaml."""
    resolved = file_path.resolve()
    cursor = resolved if resolved.is_dir() else resolved.parent
    for _ in range(8):
        cfg = cursor / "series-config.yaml"
        if cfg.exists():
            try:
                text = cfg.read_text(encoding="utf-8")
                for line in text.splitlines():
                    line = line.strip()
                    if line.startswith("source_tradition:"):
                        return line.split(":", 1)[1].strip().strip("'\"").lower() or "islam"
            except OSError:
                pass
            break
        if cursor == cursor.parent:
            break
        cursor = cursor.parent
    return "islam"


def assert_doctrinal_clean(text: str, file_path: Path) -> None:
    """Category T hard gate. Runs T3 forbidden-phrase checks plus T1/T2/T5 advisory checks."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _doctrinal import run_doctrinal_checks, tradition_pack_dir  # noqa: E402

    tradition = _resolve_book_tradition(file_path)
    pack_dir = tradition_pack_dir(tradition)
    if not pack_dir.is_dir():
        print(
            f"INFO: T-NO-PACK — book's source_tradition={tradition!r} has no doctrinal "
            f"data pack at {pack_dir}. "
            f"Skipping Category T checks. Add a tradition pack under "
            f"content/_shared/<tradition>/ to enable doctrinal gating for this book.",
            file=sys.stderr,
        )
        return

    findings = run_doctrinal_checks(text)
    p0_findings = [f for f in findings if f.severity == "P0"]
    p1_findings = [f for f in findings if f.severity == "P1"]

    for f in p1_findings:
        _flag_p1(
            f.check_id,
            file_path,
            f"{f.signature} — {f.reason[:140]} "
            f"(context: …{f.context_excerpt[:80]}…)"
            + (f" — use: {f.replacement}" if f.replacement else ""),
        )

    if p0_findings:
        lines = ["ERROR: doctrinal-accuracy P0 violations in chapter:"]
        for f in p0_findings:
            lines.append(
                f"  [{f.check_id}] {f.signature}"
                + (f" → use '{f.replacement}'" if f.replacement else "")
            )
            lines.append(f"    context: …{f.context_excerpt[:200]}…")
            if f.reason:
                lines.append(f"    reason: {f.reason[:200]}")
        lines.append(
            f"  See content/_shared/islam/ for the canonical data and "
            f"scripts/podcast/_doctrinal.py for the rule logic."
        )
        sys.exit("\n".join(lines))
