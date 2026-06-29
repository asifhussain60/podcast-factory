#!/usr/bin/env python3
"""density_planner.py -- NotebookLM Density Planner (2026-06-11).

Decides, per chapter source file, whether it should remain a standalone
NotebookLM generation, be combined with adjacent chapters into one Longer
generation, be flagged too thin, or be flagged too dense (split candidate) --
and assigns the NotebookLM length setting (Default vs Long) per episode.

Two modes:

  audit  (default) -- operates on the finished chapters/*.txt files. Read-only
         on content; writes ONLY _system/density-plan.json + density-plan.md.
         This is the post-authoring authority for NotebookLM upload settings
         (the upload table reads per-episode Length from the plan).

  plan   -- operates on the Phase 0d TOC plan (source-toc.json) when present.
         Advisory-only: its output feeds the Phase 0d STEP 1 prompt on re-runs
         (mirroring the deterministic concept-inventory pattern). It never
         gates or overrides the Phase 0d LLM planner's existing brakes.

Scoring is fully deterministic (no LLM calls, no randomness, no clock in the
decision path). The composite per-group score is:

    score = band_fit (content utilization vs the mode's soft word band)
          - compression_risk (concept/word/vocabulary/citation load vs caps)
          - incoherence_penalty (combining across arcs / low term overlap)
          - pairing_cost (combining must EARN its keep)
          + combine_bias * thin_relief (rescuing thin neighbours)

groups are contiguous runs in canonical chapter order (optimal adjacent
partition via dynamic programming), so the canonical chapter sequence and the
1:1 chapter<->episode pairing are always preserved -- a "combine" group lists
its member episodes; nothing on disk is renumbered.

Profiles: scripts/podcast/_density_profiles.py (pluggable registry, per-book
overrides via series-config.yaml `density_profiles:`).

CLI:
  python3 scripts/podcast/density_planner.py <slug> [--mode audit|plan]
      [--json] [--dry-run] [--max-group N]

Exit codes: 0 ok, 2 fatal (book/chapters not found).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import find_content  # noqa: E402
from chapter_density_audit import audit_chapter, TARGET_WORDS_PER_CONCEPT  # noqa: E402
from _density_profiles import (  # noqa: E402
    DensityProfile, get_profile, MODE_DEFAULT, MODE_LONGER, MODE_TO_LENGTH,
)

PLANNER_VERSION = "1.0"
SCHEMA_VERSION = 1

# Spoken-word proxy: NotebookLM hosts land around 150 wpm.
SPOKEN_WPM = 150
# Token estimate per whitespace word (English prose with transliterations).
TOKENS_PER_WORD = 1.35

# Reference densities for load normalization (per 1,000 words). A chapter at
# these rates carries a "full" terminology/citation load for its size.
VOCAB_REF_PER_1000 = 12.0   # distinct glossary terms
CITE_REF_PER_1000 = 6.0     # explicit (chapter N, verse M) citations

# Grouping discipline.
DEFAULT_MAX_GROUP = 3       # 3-way merges only rescue all-thin same-arc runs
OVERLAP_FLOOR = 0.12        # Jaccard floor for "same arc" when pairing
PAIRING_COST = 0.08         # combining must earn at least this much
W_RISK = 1.0
W_INCOHERENCE = 0.8
CROSS_SESSION_PENALTY = 0.30

CITATION_RE = re.compile(r"\(\s*chapter\s+\d{1,3}\s*,\s*verses?\s+\d{1,3}", re.I)
_TOKEN_RE = re.compile(r"[a-z'][a-z'\-]{3,}")
_STOPWORDS = frozenset("""
that this with from they them their there what when where which while these
those have has had been being will would could should about into over under
between among through because therefore thus then than against without within
upon does doing done says said also only just like very more most much many
some such each every other another itself himself herself yourself ones
""".split())


# ---------------------------------------------------------------------------
# data model
# ---------------------------------------------------------------------------

@dataclass
class ChapterMetrics:
    chapter_file: str
    slug: str
    ep_num: int
    title: str
    session_index: int | None
    session_title: str | None
    words: int
    est_tokens: int
    concepts: int
    concept_titles: list[str]
    words_per_concept: float
    read_minutes: float
    glossary_terms: int            # distinct glossary terms present
    glossary_per_1000: float
    citations: int
    citations_per_1000: float
    key_tensions: int
    overlap_prev: float            # Jaccard term overlap with previous chapter
    overlap_next: float
    compression_risk: float        # solo risk vs the default-mode profile
    underutilization: float        # 0..1 shortfall vs default-mode min band
    term_set: set[str] = field(default_factory=set, repr=False)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("term_set", None)
        return d


@dataclass
class GroupDecision:
    group_index: int
    members: list[str]             # chapter files, canonical order
    episode_numbers: list[int]
    framing_files: list[str]
    action: str                    # standalone | combine | flag_thin | flag_dense
    notebooklm_mode: str           # default_deep_dive | longer
    notebooklm_length: str         # Default | Long
    combined_words: int
    combined_concepts: int
    compression_risk: float
    score: float
    reasoning: str
    framing_impact: str
    pacing_directive: bool         # True -> Slice-2 pacing block recommended

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# metric extraction (deterministic)
# ---------------------------------------------------------------------------

def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _glossary_patterns(book_dir: Path) -> list[tuple[str, re.Pattern]]:
    gl = _load_yaml(book_dir / "_system" / "glossary.yml")
    pats: list[tuple[str, re.Pattern]] = []
    seen: set[str] = set()
    for e in gl.get("entries") or []:
        term = str(e.get("phonetic") or "").strip()
        if len(term) < 3 or term.lower() in seen:
            continue
        seen.add(term.lower())
        pats.append((term, re.compile(r"(?<![\w'])" + re.escape(term) + r"(?![\w])",
                                      re.IGNORECASE)))
    return pats


def _term_set(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def compression_risk(words: int, concepts: int, glossary_per_1000: float,
                     citations_per_1000: float, profile: DensityProfile) -> float:
    """0..1 composite load vs the profile's caps. ~0.6 when every load is at
    cap; >1 territory is clamped. Concept load dominates by design -- high
    doctrinal density matters more than raw word count."""
    concept_load = concepts / max(1, profile.max_major_concepts)
    word_load = words / max(1, profile.max_words_soft)
    vocab_load = min(1.5, glossary_per_1000 / VOCAB_REF_PER_1000)
    cite_load = min(1.5, citations_per_1000 / CITE_REF_PER_1000)
    raw = (0.40 * concept_load + 0.25 * word_load
           + 0.20 * vocab_load + 0.15 * cite_load)
    return round(_clamp01(0.6 * raw), 3)


_CH_FILE_RE = re.compile(r"^ch(\d{1,3})[a-z]?-(.+)\.txt$")


def collect_chapter_metrics(book_dir: Path, content_profile: str) -> list[ChapterMetrics]:
    """Layer A-C metrics for every chapters/*.txt, canonical order. Read-only."""
    chapters_dir = book_dir / "chapters"
    files = sorted(p for p in chapters_dir.glob("ch*.txt") if _CH_FILE_RE.match(p.name))
    if not files:
        return []
    gloss = _glossary_patterns(book_dir)
    dd = get_profile(content_profile, MODE_DEFAULT, book_dir)

    out: list[ChapterMetrics] = []
    for p in files:
        m = _CH_FILE_RE.match(p.name)
        slug = m.group(2)
        text = p.read_text(encoding="utf-8")
        density = audit_chapter(p, book_dir.name, "", max_concepts=dd.max_major_concepts)
        contract = _load_yaml(book_dir / "chapter-contracts" / f"{slug}.yml")
        try:
            ep_num = int(contract.get("episode_number"))
        except (TypeError, ValueError):
            ep_num = int(m.group(1))
        words = density.total_words
        per_1000 = 1000.0 / words if words else 0.0
        n_gloss = sum(1 for _t, pat in gloss if pat.search(text))
        n_cite = len(CITATION_RE.findall(text))
        g1000 = round(n_gloss * per_1000, 2)
        c1000 = round(n_cite * per_1000, 2)
        risk = compression_risk(words, density.concept_count, g1000, c1000, dd)
        si = contract.get("session_index")
        out.append(ChapterMetrics(
            chapter_file=p.name,
            slug=slug,
            ep_num=ep_num,
            title=str(contract.get("title") or slug).strip("\"'"),
            session_index=si if isinstance(si, int) else None,
            session_title=contract.get("session_title")
                if isinstance(contract.get("session_title"), str) else None,
            words=words,
            est_tokens=round(words * TOKENS_PER_WORD),
            concepts=density.concept_count,
            concept_titles=[s.title for s in density.concept_sections],
            words_per_concept=round(density.words_per_concept, 1),
            read_minutes=round(words / SPOKEN_WPM, 1),
            glossary_terms=n_gloss,
            glossary_per_1000=g1000,
            citations=n_cite,
            citations_per_1000=c1000,
            key_tensions=len(contract.get("key_tensions") or []),
            overlap_prev=0.0,
            overlap_next=0.0,
            compression_risk=risk,
            underutilization=round(_clamp01(
                (dd.min_words_soft - words) / dd.min_words_soft), 3),
            term_set=_term_set(text),
        ))

    out.sort(key=lambda c: c.ep_num)
    for i, c in enumerate(out):
        if i > 0:
            c.overlap_prev = round(_jaccard(c.term_set, out[i - 1].term_set), 3)
        if i < len(out) - 1:
            c.overlap_next = round(_jaccard(c.term_set, out[i + 1].term_set), 3)
    return out


# ---------------------------------------------------------------------------
# grouping (optimal adjacent partition, dynamic programming)
# ---------------------------------------------------------------------------

def _band_fit(words: int, prof: DensityProfile) -> float:
    """1.0 inside [min_soft, max_soft]; linear decay outside."""
    if words < prof.min_words_soft:
        return _clamp01(1.0 - (prof.min_words_soft - words) / prof.min_words_soft)
    if words > prof.max_words_soft:
        return _clamp01(1.0 - (words - prof.max_words_soft) / prof.max_words_soft)
    return 1.0


def _group_overlap(members: list[ChapterMetrics]) -> float:
    """Min pairwise-adjacent overlap inside the run (the weakest seam)."""
    if len(members) < 2:
        return 1.0
    return min(members[i].term_set and _jaccard(members[i].term_set,
               members[i + 1].term_set) or 0.0
               for i in range(len(members) - 1))


def _same_session(members: list[ChapterMetrics]) -> bool:
    idxs = {c.session_index for c in members}
    return len(idxs) == 1 and None not in idxs


def _combined(members: list[ChapterMetrics]) -> tuple[int, int, float, float]:
    words = sum(c.words for c in members)
    concepts = sum(c.concepts for c in members)
    g1000 = round(sum(c.glossary_terms for c in members) * 1000.0 / words, 2) if words else 0.0
    c1000 = round(sum(c.citations for c in members) * 1000.0 / words, 2) if words else 0.0
    return words, concepts, g1000, c1000


def _best_mode(words: int, concepts: int, g1000: float, c1000: float,
               content_profile: str, book_dir: Path,
               ) -> tuple[str, DensityProfile, float, float]:
    """Pick the generation mode (default vs longer) whose band fits best;
    ties break toward the focused default mode."""
    best = None
    for mode in (MODE_DEFAULT, MODE_LONGER):
        prof = get_profile(content_profile, mode, book_dir)
        fit = _band_fit(words, prof)
        risk = compression_risk(words, concepts, g1000, c1000, prof)
        cand = (fit, -risk, mode == MODE_DEFAULT, mode, prof)
        if best is None or cand[:3] > best[:3]:
            best = cand
    return best[3], best[4], best[0], compression_risk(
        words, concepts, g1000, c1000, best[4])


def _score_group(members: list[ChapterMetrics], content_profile: str,
                 book_dir: Path) -> tuple[float, dict] | None:
    """Per-member-normalized score for one candidate contiguous group, or
    None when the group is structurally disallowed."""
    k = len(members)
    words, concepts, g1000, c1000 = _combined(members)
    mode, prof, fit, risk = _best_mode(words, concepts, g1000, c1000,
                                       content_profile, book_dir)
    incoherence = 0.0
    if k >= 2:
        overlap = _group_overlap(members)
        same = _same_session(members)
        if not same:
            # Crossing a source-Part boundary needs STRONG topical continuity.
            if overlap < 2 * OVERLAP_FLOOR:
                return None
            incoherence += CROSS_SESSION_PENALTY
        elif overlap < OVERLAP_FLOOR:
            incoherence += W_INCOHERENCE * (OVERLAP_FLOOR - overlap) / OVERLAP_FLOOR * 0.5
        if k >= 3:
            dd = get_profile(content_profile, MODE_DEFAULT, book_dir)
            all_thin = all(c.words < dd.min_words_soft for c in members)
            if not (all_thin and same):
                return None  # 3-way merges only rescue all-thin same-arc runs
        thin_relief = sum(c.underutilization for c in members) / k
        per_member = (fit - W_RISK * risk - incoherence - PAIRING_COST
                      + prof.combine_bias * thin_relief)
    else:
        per_member = fit - W_RISK * risk

    return per_member * k, {
        "mode": mode, "profile": prof, "fit": round(fit, 3),
        "risk": risk, "incoherence": round(incoherence, 3),
        "words": words, "concepts": concepts,
        "g1000": g1000, "c1000": c1000,
    }


def partition(chapters: list[ChapterMetrics], content_profile: str,
              book_dir: Path, max_group: int = DEFAULT_MAX_GROUP,
              ) -> list[tuple[list[ChapterMetrics], dict, float]]:
    """Optimal adjacent partition: maximize summed per-member-normalized
    group scores. O(n * max_group). Returns [(members, info, score), ...] in
    canonical order."""
    n = len(chapters)
    NEG = float("-inf")
    best = [NEG] * (n + 1)
    best[0] = 0.0
    choice: list[tuple[int, dict, float] | None] = [None] * (n + 1)
    for i in range(1, n + 1):
        for k in range(1, min(max_group, i) + 1):
            members = chapters[i - k:i]
            scored = _score_group(members, content_profile, book_dir)
            if scored is None:
                continue
            s, info = scored
            if best[i - k] + s > best[i]:
                best[i] = best[i - k] + s
                choice[i] = (k, info, s)
    # Backtrack.
    groups: list[tuple[list[ChapterMetrics], dict, float]] = []
    i = n
    while i > 0:
        k, info, s = choice[i]
        groups.append((chapters[i - k:i], info, s))
        i -= k
    groups.reverse()
    return groups


# ---------------------------------------------------------------------------
# decisions + reasoning
# ---------------------------------------------------------------------------

def _framing_file(ep_num: int, slug: str) -> str:
    return f"episodes/EP{ep_num:02d}-{slug}.txt"


def _reason_solo(c: ChapterMetrics, info: dict, prof: DensityProfile,
                 action: str) -> str:
    bits = [f"{c.words:,} words, {c.concepts} concept section(s), "
            f"~{c.read_minutes:.0f} min spoken"]
    bits.append(f"band fit {info['fit']:.2f} vs {prof.min_words_soft:,}-"
                f"{prof.max_words_soft:,} ({info['mode']})")
    drivers = []
    if c.glossary_per_1000 >= VOCAB_REF_PER_1000:
        drivers.append(f"vocabulary-heavy ({c.glossary_terms} glossary terms, "
                       f"{c.glossary_per_1000}/1,000 words)")
    if c.citations_per_1000 >= CITE_REF_PER_1000:
        drivers.append(f"citation-heavy ({c.citations} verse citations)")
    if c.concepts >= prof.max_major_concepts:
        drivers.append("at the concept ceiling")
    risk_txt = f"compression risk {info['risk']:.2f}"
    if drivers:
        risk_txt += " (" + "; ".join(drivers) + ")"
    bits.append(risk_txt)
    if action == "flag_thin":
        bits.append("below the minimum solo band - thin; no adjacent same-arc "
                    "partner improved the score")
    elif action == "flag_dense":
        bits.append("risk exceeds the profile ceiling even standalone - "
                    "split candidate on the next authoring pass")
    return "; ".join(bits) + "."


def _reason_combine(members: list[ChapterMetrics], info: dict) -> str:
    names = " + ".join(c.chapter_file for c in members)
    overlap = _group_overlap(members)
    arc = (f"same source Part (session {members[0].session_index})"
           if _same_session(members) else "adjacent Parts with strong term continuity")
    return (f"{names}: combined {info['words']:,} words / {info['concepts']} "
            f"concepts fits the {info['mode']} band (fit {info['fit']:.2f}); "
            f"{arc}, adjacent-term overlap {overlap:.2f}; combined compression "
            f"risk {info['risk']:.2f}. One generation covers the arc without "
            f"padding two thin standalone runs.")


def _framing_impact(members: list[ChapterMetrics], action: str,
                    pacing: bool) -> str:
    if action == "combine":
        eps = ", ".join(f"EP{c.ep_num:02d}" for c in members)
        base = members[0]
        return (f"Re-author ONE merged framing covering {eps} (base: "
                f"EP{base.ep_num:02d}). Merge the focus lists so every member's "
                f"spine is named; union the pronunciation lists (each term said "
                f"once); single opening + single landing across the arc; keep "
                f"under 4,500 characters. Upload all member chapter files as "
                f"sources of ONE notebook; set Length to Long.")
    if action == "flag_dense":
        return ("Keep the existing framing; add the pacing directive block "
                "(depth over breadth, define terms once, skip minor detail) and "
                "set Length to Long to give the material more airtime.")
    if pacing:
        return ("Keep the existing framing; add the pacing directive block - "
                "the chapter sits near the compression ceiling.")
    return "No framing change needed."


def decide(chapters: list[ChapterMetrics], content_profile: str,
           book_dir: Path, max_group: int = DEFAULT_MAX_GROUP,
           ) -> list[GroupDecision]:
    decisions: list[GroupDecision] = []
    for gi, (members, info, score) in enumerate(
            partition(chapters, content_profile, book_dir, max_group), start=1):
        prof: DensityProfile = info["profile"]
        if len(members) == 1:
            c = members[0]
            if info["risk"] > prof.max_compression_risk:
                action = "flag_dense"
            elif c.words < prof.min_words_soft and info["mode"] == MODE_DEFAULT:
                action = "flag_thin"
            else:
                action = "standalone"
            pacing = (info["risk"] > prof.max_compression_risk * 0.9)
            length = ("Long" if action == "flag_dense"
                      else MODE_TO_LENGTH[info["mode"]])
            reasoning = _reason_solo(c, info, prof, action)
        else:
            action = "combine"
            pacing = info["risk"] > prof.max_compression_risk * 0.9
            length = "Long"
            reasoning = _reason_combine(members, info)
        decisions.append(GroupDecision(
            group_index=gi,
            members=[c.chapter_file for c in members],
            episode_numbers=[c.ep_num for c in members],
            framing_files=[_framing_file(c.ep_num, c.slug) for c in members],
            action=action,
            notebooklm_mode=info["mode"],
            notebooklm_length=length,
            combined_words=info["words"],
            combined_concepts=info["concepts"],
            compression_risk=info["risk"],
            score=round(score, 3),
            reasoning=reasoning,
            framing_impact=_framing_impact(members, action, pacing),
            pacing_directive=pacing or action in ("combine", "flag_dense"),
        ))
    return decisions


# ---------------------------------------------------------------------------
# plan assembly + reports
# ---------------------------------------------------------------------------

def _source_signature(book_dir: Path, chapters: list[ChapterMetrics]) -> str:
    h = hashlib.sha256()
    for c in chapters:
        h.update((book_dir / "chapters" / c.chapter_file).read_bytes())
    return h.hexdigest()


def build_plan(book_dir: Path, *, mode: str = "audit",
               max_group: int = DEFAULT_MAX_GROUP) -> dict:
    cfg = _load_yaml(book_dir / "_system" / "series-config.yaml")
    content_profile = str(cfg.get("content_profile") or "").strip()
    chapters = collect_chapter_metrics(book_dir, content_profile)
    if not chapters:
        raise FileNotFoundError(f"no chapter files under {book_dir / 'chapters'}")
    decisions = decide(chapters, content_profile, book_dir, max_group)

    n_default = sum(1 for d in decisions if d.notebooklm_length == "Default")
    n_long = sum(1 for d in decisions if d.notebooklm_length == "Long")
    summary = {
        "chapters": len(chapters),
        "episodes_before": len(chapters),
        "generations_after": len(decisions),
        "standalone": sum(1 for d in decisions if d.action == "standalone"),
        "combine_groups": sum(1 for d in decisions if d.action == "combine"),
        "flag_thin": sum(1 for d in decisions if d.action == "flag_thin"),
        "flag_dense": sum(1 for d in decisions if d.action == "flag_dense"),
        "length_default": n_default,
        "length_long": n_long,
        "pacing_directives": sum(1 for d in decisions if d.pacing_directive),
        "total_words": sum(c.words for c in chapters),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "planner_version": PLANNER_VERSION,
        "book_slug": cfg.get("slug") or book_dir.name,
        "content_profile": content_profile,
        "mode": mode,
        "source_signature": _source_signature(book_dir, chapters),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "profiles_used": {
            m: asdict(get_profile(content_profile, m, book_dir))
            for m in (MODE_DEFAULT, MODE_LONGER)
        },
        "summary": summary,
        "chapters": [c.to_dict() for c in chapters],
        "groups": [d.to_dict() for d in decisions],
    }


def render_markdown(plan: dict) -> str:
    s = plan["summary"]
    lines = [
        f"# NotebookLM density plan - {plan['book_slug']}",
        "",
        f"Planner v{plan['planner_version']} ({plan['mode']} mode) - "
        f"deterministic, no LLM calls. Source signature "
        f"`{plan['source_signature'][:12]}`.",
        "",
        "## Summary",
        "",
        f"- {s['chapters']} chapters, {s['total_words']:,} words total",
        f"- {s['generations_after']} NotebookLM generations planned "
        f"({s['standalone']} standalone, {s['combine_groups']} combined, "
        f"{s['flag_thin']} thin-flagged, {s['flag_dense']} dense-flagged)",
        f"- Length settings: {s['length_default']} Default, {s['length_long']} Long",
        f"- Pacing directives recommended: {s['pacing_directives']}",
        "",
        "## Decisions",
        "",
        "| # | Members | Episodes | Words | Concepts | Risk | Action | Length |",
        "|---|---------|----------|-------|----------|------|--------|--------|",
    ]
    for g in plan["groups"]:
        eps = ", ".join(f"EP{n:02d}" for n in g["episode_numbers"])
        members = "<br>".join(g["members"])
        lines.append(
            f"| {g['group_index']} | {members} | {eps} | "
            f"{g['combined_words']:,} | {g['combined_concepts']} | "
            f"{g['compression_risk']:.2f} | {g['action']} | "
            f"{g['notebooklm_length']} |")
    lines += ["", "## Reasoning and framing impact", ""]
    for g in plan["groups"]:
        eps = ", ".join(f"EP{n:02d}" for n in g["episode_numbers"])
        lines += [
            f"### Group {g['group_index']} ({eps}) - {g['action']}",
            "",
            f"- Why: {g['reasoning']}",
            f"- Framing: {g['framing_impact']}",
            "",
        ]
    return "\n".join(lines)


def write_plan(book_dir: Path, plan: dict) -> tuple[Path, Path]:
    sysdir = book_dir / "_system"
    sysdir.mkdir(exist_ok=True)
    jpath = sysdir / "density-plan.json"
    mpath = sysdir / "density-plan.md"
    jpath.write_text(json.dumps(plan, indent=2, ensure_ascii=True) + "\n",
                     encoding="utf-8")
    mpath.write_text(render_markdown(plan) + "\n", encoding="utf-8")
    return jpath, mpath


# ---------------------------------------------------------------------------
# Slice-2 consumers (pacing directive + Phase 0d advisory)
# ---------------------------------------------------------------------------

def load_plan(book_dir: Path) -> dict | None:
    p = Path(book_dir) / "_system" / "density-plan.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def group_for_episode(plan: dict | None, ep_num: int) -> dict | None:
    for g in (plan or {}).get("groups", []):
        if ep_num in g.get("episode_numbers", []):
            return g
    return None


def pacing_block_for_episode(book_dir: Path, ep_num: int) -> str | None:
    """The framing 'Pacing directive' block for an episode, or None.

    Returned ONLY when the density plan recommends it (pacing_directive=True
    for the episode's group). Wording avoids every framing deny-list phrase;
    callers insert it ABOVE the '## Do not' section so the no-read-aloud
    guard stays the final line.
    """
    g = group_for_episode(load_plan(book_dir), ep_num)
    if not g or not g.get("pacing_directive"):
        return None
    lines = [
        "## Pacing directive",
        "This source is conceptually dense. Go slowly and choose depth over breadth.",
        "Define each technical term at its first mention, then move on.",
        "Prioritize the main doctrinal movement; minor details may be skipped "
        "entirely rather than rushed.",
        "Pick the strongest example for each teaching and let it breathe; do not "
        "race to cover everything.",
    ]
    if g.get("action") == "combine":
        lines.append(
            "The sources uploaded together form one continuous arc; treat them "
            "as a single teaching, not a list of topics, and explain why they "
            "belong together before moving between them.")
    return "\n".join(lines)


def phase_0d_advisory_block(book_dir: Path) -> str:
    """Non-binding density advisory for the Phase 0d STEP 1 TOC prompt.

    Empty string when no plan exists. Mirrors the deterministic
    concept-inventory pattern: useful on re-runs, silent on fresh books.
    """
    plan = load_plan(book_dir)
    if not plan:
        return ""
    lines = []
    for g in plan.get("groups", []):
        eps = ", ".join(f"EP{n:02d}" for n in g.get("episode_numbers", []))
        if g.get("action") == "combine":
            lines.append(f"   - consider keeping {' + '.join(g['members'])} as ONE "
                         f"episode unit (prior plan combined {eps}: "
                         f"{g['combined_words']:,}w, arc-coherent)")
        elif g.get("action") == "flag_dense":
            lines.append(f"   - {g['members'][0]} ran over-dense last render "
                         f"(risk {g['compression_risk']:.2f}) - prefer a split "
                         f"at the strongest thematic seam")
        elif g.get("action") == "flag_thin":
            lines.append(f"   - {g['members'][0]} ran thin last render - prefer "
                         f"merging it into an adjacent same-arc unit")
    if not lines:
        return ""
    return ("3e. DENSITY PLANNER ADVISORY (non-binding, measured from the prior "
            "render by scripts/podcast/density_planner.py; deterministic gates "
            "still apply):\n" + "\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="NotebookLM density planner (deterministic, read-only on "
                    "chapters/ and episodes/; writes _system/density-plan.*).")
    ap.add_argument("slug", help="Book slug (any bucket).")
    ap.add_argument("--mode", choices=("audit", "plan"), default="audit")
    ap.add_argument("--max-group", type=int, default=DEFAULT_MAX_GROUP)
    ap.add_argument("--json", action="store_true", help="Print the plan JSON.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Compute and print; write nothing.")
    args = ap.parse_args(argv)

    found = find_content(args.slug)
    if found is None:
        print(f"ERROR: no book found for slug {args.slug!r}", file=sys.stderr)
        return 2
    book_dir = found[2]
    try:
        plan = build_plan(book_dir, mode=args.mode, max_group=args.max_group)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(plan, indent=2, ensure_ascii=True))
    else:
        print(render_markdown(plan))
    if not args.dry_run:
        jpath, mpath = write_plan(book_dir, plan)
        print(f"\nWrote {jpath}\nWrote {mpath}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
