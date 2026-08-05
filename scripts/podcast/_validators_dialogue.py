"""_validators_dialogue.py — deterministic pre-synthesis gate for dialogue scripts.

The quality core of the autonomous audio path (Audio Engine v2, Step 3).
NOTHING renders before this gate passes: the renderer refuses any script
without a passing gate report, so paid synthesis can never run on unvetted
content.

Extends the deterministic rule system (scripts/podcast/_rules.py +
_validator_constants.py) to the dialogue-script artifact:

    deny lists (MODERNIZE / SURPRISE / AI-cliche)     P0
    meta-prose tells                                  P0
    doctrinal checks (content/_shared/<tradition>)    P0/P1 per finding
    coverage: every contract tension + concept        P0  (no-teaching-lost analog)
    host-role parity (both voices present, A leads)   P0/P1
    Arabic Unicode (ENGINE-AWARE via the registry)    P0 when unsupported
    audio tags (ENGINE-AWARE)                         P0 unsupported / P1 not sparse
    honorifics-once                                   P1
    abbreviated work titles                           P1
    doubled phrases (copy-paste corruption)           P1
    Quran citation format (Islamic profile only)      P1
    SOFT character band                               P2  (pacing advisory ONLY —
                                                          content is NEVER cut)

All checks return findings instead of sys.exit-ing (unlike the chapter
validators) because this gate runs inside a convergence loop. The gate
report carries the EXACT credit estimate (chars x registry rate) so the H1
spend halt can surface it.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _audio_engines import audio_engine_for_book, credit_estimate
from _dialogue_script import (
    AUDIO_TAG_RE,
    DialogueScriptError,
    Turn,
    audio_tag_count,
    estimated_minutes,
    parse_dialogue_script,
    script_char_count,
    script_path_for,
    soft_char_band,
)
from _rules import (
    AI_CLICHE_DENY,
    MODERNIZE_DENY,
    R_AUGMENT_ARABIC_RANGES,
    SURPRISE_DENY,
)
from _validator_constants import (
    FORBIDDEN_ABBREVIATIONS,
    HONORIFIC_PHRASES,
    META_PROSE_REGEX_TELLS,
    META_PROSE_TELLS,
    QURAN_CITATION_BAD_PATTERNS,
)

DIALOGUE_GATE_VERSION = "1.0"

# Tag sparseness ceiling: more than one [tag] per this many turns is a P1.
TAG_SPARSE_TURNS_PER_TAG = 6

# Coverage: fraction of a tension/concept's significant tokens that must
# appear in the spoken text for the item to count as surfaced.
COVERAGE_TOKEN_FRACTION = 0.6

_COVERAGE_STOPWORDS = frozenset(
    "the a an and or of to in on for with as at by is are was were be this "
    "that it its from into not no but how what why when who which between "
    "their there them they he she his her him you your we our us".split()
)


@dataclass(frozen=True)
class Finding:
    check_id: str
    severity: str  # "P0" | "P1" | "P2"
    message: str
    excerpt: str = ""


@dataclass
class DialogueGateReport:
    episode_id: str
    engine_name: str
    char_count: int = 0
    credit_estimate: int = 0
    n_turns: int = 0
    findings: list[Finding] = field(default_factory=list)

    def count(self, severity: str) -> int:
        return sum(1 for f in self.findings if f.severity == severity)

    @property
    def p0(self) -> int:
        return self.count("P0")

    @property
    def p1(self) -> int:
        return self.count("P1")

    @property
    def p2(self) -> int:
        return self.count("P2")

    @property
    def render_blocked(self) -> bool:
        """P0s block synthesis unconditionally. P1s block until the
        convergence loop accepts SHIP-WITH-CAUTION. P2s never block."""
        return self.p0 > 0


def _significant_tokens(text: str) -> set[str]:
    words = re.split(r"[^a-z0-9']+", text.lower())
    return {w for w in words if len(w) > 3 and w not in _COVERAGE_STOPWORDS}


def _spoken_text(turns: list[Turn]) -> str:
    """The text the listener hears — turn text only, one line per turn,

    space-padded so deny entries with boundary spaces (' right? ') match at
    line edges too."""
    return "\n".join(f" {t.text} " for t in turns)


def _doubled_phrases(turns: list[Turn]) -> list[str]:
    """Back-to-back repeated 4-8 word phrases inside any single turn

    (copy-paste corruption — the B6 class of finding)."""
    _PUNCT = str.maketrans("", "", ".,;:!?\"'()")
    hits: list[str] = []
    seen: set[str] = set()
    for t in turns:
        raw = t.text.split()
        norm = [w.translate(_PUNCT).lower() for w in raw]
        n = len(norm)
        for window in range(4, 9):
            if window * 2 > n:
                break
            for i in range(n - window * 2 + 1):
                a = " ".join(norm[i : i + window])
                b = " ".join(norm[i + window : i + window * 2])
                if a == b and len(a) >= 16 and a not in seen:
                    seen.add(a)
                    hits.append(" ".join(raw[i : i + window])[:80])
    return hits


def _contract_coverage_items(contract: dict) -> list[str]:
    """Every tension + concept the contract declares (the coverage contract)."""
    items: list[str] = []
    for key in ("key_tensions", "concepts"):
        val = contract.get(key) or []
        if isinstance(val, list):
            items.extend(str(v) for v in val if str(v).strip())
    return items


def gate_dialogue_script(
    book_dir: Path,
    episode_id: str,
    *,
    contract: dict | None = None,
) -> DialogueGateReport:
    """Run every deterministic check against the episode's script artifact.

    *contract* may be supplied pre-parsed; otherwise it is loaded from
    BOOK_DIR/chapter-contracts/<chapter-slug>.yml (chapter slug = the part of
    the episode id after 'EP##-').
    """
    engine = audio_engine_for_book(book_dir)
    report = DialogueGateReport(episode_id=episode_id, engine_name=engine.name)
    path = script_path_for(book_dir, episode_id)

    if not path.exists():
        report.findings.append(Finding("DLG-MISSING", "P0", f"script artifact missing: {path}"))
        return report

    try:
        turns = parse_dialogue_script(path.read_text(encoding="utf-8"))
    except DialogueScriptError as e:
        report.findings.append(Finding("DLG-PARSE", "P0", f"script does not parse: {e}"))
        return report

    report.n_turns = len(turns)
    report.char_count = script_char_count(turns)
    report.credit_estimate = credit_estimate(engine, report.char_count)
    spoken = _spoken_text(turns)
    spoken_lower = spoken.lower()

    # ── Deny lists (P0 — these reach the listener verbatim) ──────────────────
    for deny, check_id in (
        (MODERNIZE_DENY, "DLG-DENY-MODERNIZE"),
        (SURPRISE_DENY, "DLG-DENY-SURPRISE"),
        (AI_CLICHE_DENY, "DLG-AI-CLICHE"),
    ):
        hits = sorted({p.strip() for p in deny if p in spoken})
        if hits:
            report.findings.append(
                Finding(check_id, "P0", f"{len(hits)} deny-list phrase(s) in spoken text: {hits[:6]}")
            )

    # ── Meta-prose tells (P0 — a script describing itself) ───────────────────
    meta_hits = sorted({t for t in META_PROSE_TELLS if t in spoken_lower})
    for pat in META_PROSE_REGEX_TELLS:
        m = re.search(pat, spoken, flags=re.IGNORECASE)
        if m:
            meta_hits.append(m.group(0)[:40])
    if meta_hits:
        report.findings.append(Finding("DLG-META-PROSE", "P0", f"meta-prose tells in spoken text: {meta_hits[:6]}"))

    # ── Honorifics once (P1) ─────────────────────────────────────────────────
    over = [(p.pattern, len(p.findall(spoken))) for p in HONORIFIC_PHRASES if len(p.findall(spoken)) > 1]
    if over:
        report.findings.append(
            Finding(
                "DLG-HONORIFIC-ONCE",
                "P1",
                "honorific expansions repeated (allowed once per form): "
                + "; ".join(f"{pat!r} x{n}" for pat, n in over[:4]),
            )
        )

    # ── Abbreviated work titles (P1) ─────────────────────────────────────────
    abbrev_hits = [label for pat, label in FORBIDDEN_ABBREVIATIONS.items() if re.search(pat, spoken)]
    if abbrev_hits:
        report.findings.append(Finding("DLG-ABBREVIATION", "P1", f"abbreviated work titles: {abbrev_hits[:4]}"))

    # ── Doubled phrases (P1) ─────────────────────────────────────────────────
    doubled = _doubled_phrases(turns)
    if doubled:
        report.findings.append(
            Finding("DLG-DOUBLED-PHRASE", "P1", f"{len(doubled)} back-to-back doubled phrase(s): {doubled[:3]}")
        )

    # ── Islamic-profile checks (doctrine + citation format) ──────────────────
    from _content_profile import is_islamic_scholarly

    if is_islamic_scholarly(book_dir):
        quran_hits = sorted({m.group(0) for pat in QURAN_CITATION_BAD_PATTERNS for m in pat.finditer(spoken)})
        if quran_hits:
            report.findings.append(
                Finding(
                    "DLG-QURAN-CITATION",
                    "P1",
                    f"terse Quran citation(s) — use '(chapter N, verse M)': {quran_hits[:5]}",
                )
            )
        try:
            from _doctrinal import run_doctrinal_checks, tradition_pack_dir
            from _validators import _resolve_book_tradition

            tradition = _resolve_book_tradition(path)
            if tradition_pack_dir(tradition).is_dir():
                for f in run_doctrinal_checks(spoken):
                    sev = "P0" if f.severity == "P0" else "P1"
                    report.findings.append(
                        Finding(
                            f"DLG-{f.check_id}",
                            sev,
                            f"doctrinal: {f.signature}" + (f" — use {f.replacement!r}" if f.replacement else ""),
                            excerpt=f.context_excerpt[:120],
                        )
                    )
        except Exception as e:
            report.findings.append(Finding("DLG-DOCTRINE-UNAVAILABLE", "P1", f"doctrinal checks could not run: {e}"))

    # ── Host-role parity ─────────────────────────────────────────────────────
    speakers = {t.speaker for t in turns}
    if speakers != {"HOST_A", "HOST_B"}:
        report.findings.append(
            Finding("DLG-HOST-PARITY", "P0", f"both hosts must speak; found speakers: {sorted(speakers)}")
        )
    else:
        a_chars = sum(len(t.text) for t in turns if t.speaker == "HOST_A")
        a_share = a_chars / max(report.char_count, 1)
        if not (0.35 <= a_share <= 0.90):
            report.findings.append(
                Finding(
                    "DLG-HOST-BALANCE",
                    "P1",
                    f"Host A (scholar) speaks {a_share:.0%} of characters — expected "
                    f"35-90% (scholar leads, seeker is present).",
                )
            )

    # ── Arabic Unicode (ENGINE-AWARE via the registry) ───────────────────────
    if not engine.supports_arabic_script:
        arabic = [ch for ch in spoken if any(lo <= ord(ch) <= hi for lo, hi in R_AUGMENT_ARABIC_RANGES)]
        if arabic:
            report.findings.append(
                Finding(
                    "DLG-ARABIC-SCRIPT",
                    "P0",
                    f"{len(arabic)} Arabic-script character(s) but engine "
                    f"{engine.name!r} does not support Arabic script.",
                )
            )

    # ── Audio tags (ENGINE-AWARE) ────────────────────────────────────────────
    n_tags = audio_tag_count(turns)
    # Registry-driven sparseness budget (v3 wants reaction tags; the old flat
    # 1-per-6 cap produced flat audio — the engine card carries its own ceiling).
    budget = getattr(engine, "tag_budget_per_turns", TAG_SPARSE_TURNS_PER_TAG) or TAG_SPARSE_TURNS_PER_TAG
    if n_tags and not engine.supports_audio_tags:
        report.findings.append(
            Finding(
                "DLG-TAGS-UNSUPPORTED", "P0", f"{n_tags} [tag] cue(s) but engine {engine.name!r} does not support them."
            )
        )
    elif n_tags and n_tags > max(1, report.n_turns // budget):
        report.findings.append(
            Finding(
                "DLG-TAGS-NOT-SPARSE",
                "P1",
                f"{n_tags} [tag] cues across {report.n_turns} turns — keep at most "
                f"one per {budget} turns (tags are billed as characters).",
            )
        )
    # Ear-locked lesson (2026-06-12): TONAL tags on the scholar (HOST_A) recolor
    # his approved timbre. Only a bare [pause] is allowed on HOST_A; any other
    # tag on a HOST_A turn is a P1 (reaction tags belong to the seeker, HOST_B).
    if engine.supports_audio_tags:
        host_a_tonal: list[str] = []
        for t in turns:
            if t.speaker != "HOST_A":
                continue
            for tag in AUDIO_TAG_RE.findall(t.text):
                if tag.strip("[]").strip().lower() != "pause":
                    host_a_tonal.append(tag)
        if host_a_tonal:
            report.findings.append(
                Finding(
                    "DLG-TAGS-HOST-A-TONAL",
                    "P1",
                    f"{len(host_a_tonal)} tonal tag(s) on the scholar (HOST_A): "
                    f"{sorted(set(host_a_tonal))[:5]} — only [pause] is allowed on "
                    f"HOST_A; put reaction tags ([curious], [thoughtful], ...) on HOST_B.",
                )
            )

    # ── COVERAGE: every contract tension + concept surfaced (P0) ─────────────
    if contract is None:
        m = re.match(r"^EP\d+[a-z]?-(.+)$", episode_id)
        chapter_slug = m.group(1) if m else episode_id
        cpath = Path(book_dir) / "chapter-contracts" / f"{chapter_slug}.yml"
        if cpath.exists():
            try:
                import yaml

                contract = yaml.safe_load(cpath.read_text(encoding="utf-8")) or {}
            except Exception:
                contract = {}
        else:
            contract = {}
    missing: list[str] = []
    for item in _contract_coverage_items(contract):
        toks = _significant_tokens(item)
        if not toks:
            continue
        present = sum(1 for t in toks if t in spoken_lower)
        if present / len(toks) < COVERAGE_TOKEN_FRACTION:
            missing.append(item[:80])
    if missing:
        report.findings.append(
            Finding(
                "DLG-COVERAGE",
                "P0",
                f"{len(missing)} contracted tension(s)/concept(s) not surfaced in the "
                f"script (no-teaching-lost): {missing[:3]}",
            )
        )

    # ── NotebookLM interactive-style nudges (P2 — advisory; the semantic
    #    challenger carries the real seven-moves enforcement, these are cheap
    #    mechanical hints so the fixer never thrashes on regex false positives) ─
    if turns:

        def _wc(s: str) -> int:
            return len(re.sub(r"\[[^\]]+\]", " ", s).split())

        # Cold-open hook: the opening should pose a question to the listener.
        opener = " ".join(t.text for t in turns[:2])
        if "?" not in opener:
            report.findings.append(
                Finding(
                    "DLG-STYLE-COLD-OPEN",
                    "P2",
                    "opening turns pose no question — the NotebookLM style opens on "
                    "the chapter's question to the listener, not a statement.",
                )
            )
        # Short reactive beats: at least a few <=5-word turns at the peaks.
        short_turns = sum(1 for t in turns if 1 <= _wc(t.text) <= 5)
        if report.n_turns >= 20 and short_turns < 2:
            report.findings.append(
                Finding(
                    "DLG-STYLE-REACTIVE-BEATS",
                    "P2",
                    f"only {short_turns} short reactive turn(s) — the interactive "
                    f"style scatters 1-5 word beats ('And?' / 'Just sand.') at peaks.",
                )
            )
        # Tidy-summary close: the final turn should land on an open image.
        last = turns[-1].text.lower()
        if re.search(
            r"\b(in summary|to summari[sz]e|in conclusion|to sum up|"
            r"so,? to recap)\b",
            last,
        ):
            report.findings.append(
                Finding(
                    "DLG-STYLE-TIDY-CLOSE",
                    "P2",
                    "closing turn reads as a tidy summary — the style closes on the "
                    "chapter's unresolved image / a question to the listener.",
                )
            )

    # ── SOFT character band (P2 — pacing advisory; content is NEVER cut) ─────
    tier = _read_length_tier(book_dir)
    lo, hi = soft_char_band(tier)
    if report.char_count < lo or report.char_count > hi:
        direction = "under" if report.char_count < lo else "over"
        report.findings.append(
            Finding(
                "DLG-SOFT-BAND",
                "P2",
                f"script is {report.char_count:,} chars (~{estimated_minutes(report.char_count)} min) — "
                f"{direction} the {tier} soft band {lo:,}-{hi:,}. PACING ADVISORY ONLY: "
                f"never cut a teaching to fit; expand only if the chapter genuinely "
                f"needs more development.",
            )
        )

    return report


def _read_length_tier(book_dir: Path) -> str:
    cfg = Path(book_dir) / "_system" / "series-config.yaml"
    if cfg.exists():
        try:
            import yaml

            data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
            tier = str(data.get("length_tier") or "").strip()
            if tier:
                return tier
        except Exception:
            pass
    return "default_deep_dive"


def render_gate_report(report: DialogueGateReport) -> str:
    """Markdown gate report — includes the EXACT credit estimate (H1 input)."""
    lines = [
        f"# Dialogue gate report — {report.episode_id}",
        "",
        f"- gate version: {DIALOGUE_GATE_VERSION}",
        f"- engine: {report.engine_name}",
        f"- turns: {report.n_turns}",
        f"- characters (billable): {report.char_count:,}",
        f"- estimated audio: ~{estimated_minutes(report.char_count)} min",
        f"- **credit estimate: {report.credit_estimate:,} credits**",
        f"- findings: P0={report.p0} P1={report.p1} P2={report.p2}",
        "",
    ]
    if report.findings:
        lines.append("## Findings")
        lines.append("")
        for f in report.findings:
            lines.append(f"- [{f.severity}] {f.check_id}: {f.message}")
            if f.excerpt:
                lines.append(f"  - context: ...{f.excerpt}...")
    else:
        lines.append("No findings — script is render-eligible.")
    lines.append("")
    return "\n".join(lines)
