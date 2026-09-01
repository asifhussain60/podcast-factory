"""_book_brief.py — "The Book in Brief": the whole book condensed into one section.

WHAT IT IS
----------
A standalone piece of prose, placed above the introduction, that carries the
substance of the entire book at roughly a thirtieth of its length. Not a set of
chapter summaries joined together — the drafting call never sees a chapter, only a
ranked plan of material, which is what makes that structurally true rather than a
thing the prompt asks for.

It is APPARATUS and says so, on the same terms as the introduction beneath it:
honestly titled so no reader can mistake it for the author's own words, unnumbered
because it has no source lines and every entry in `book-toc.json` is defined by the
lines it was translated from, and written in the book's own articulated register so
it does not read as a second hand.

THE ORDER IS THE POINT
----------------------
  1. ANALYSE   one call per section, the only stage that reads the book's prose,
               producing structured points with a weight, a kind and dependencies.
  2. RANK      no model at all — `_book_brief_rank` scores, tiers, retains and
               allocates a word budget by importance rather than by source length.
  3. DRAFT     one call, from the plan alone.
  4. CHECK     a lexical sweep shortlists essential points the draft may have lost;
               one model call adjudicates only the shortlist, because lexical
               search cannot see paraphrase and a model asked about everything
               would be asked to grade its own work.
  5. REPAIR    one call, and only if something was actually missing.
  6. GATE      the hard word cap, the shapes a brief may never take, and the
               mid-sentence cut a compressor produces when it trims by counting.

WHY THE CAP IS A GATE AND NOT A TRIM
------------------------------------
Every other length rule in this repo runs the other way: `_book_completeness` HALTS
a compose when a chapter came back shorter than its source, because an edition that
quietly drops text is the defect that pipeline exists to prevent. A brief inverts
that contract, so it gets its own gate rather than a flag on the existing one — and
the gate refuses rather than truncates, because cutting to a word count is how a
brief ends mid-sentence.

COST
----
One call per section plus two to four, once per book, cached. The cache is the
idempotency marker: a re-compose does not re-buy any of it, and `force` is the only
way to spend again. Section analyses are keyed by a CONTENT fingerprint, the rule
`_window_cache` argues for at length — an mtime rule would discard the whole
analysis on a `git checkout`.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from _book_brief_gate import gate_brief, lexical_shortlist
from _book_brief_prompts import adjudicate_prompt, analyse_prompt, draft_prompt, repair_prompt
from _book_brief_rank import DEFAULT_PRESET, PRESETS
from _book_brief_rank import plan as build_plan

#: The section's title, everywhere. Parallel in form to `## Introduction to the
#: Book` — both name the book rather than pretending to be part of it — and plain
#: ASCII, per the house rule on output.
BRIEF_HEADING = "## The Book in Brief"

CACHE_DIR = "brief"
BRIEF_NAME = "brief.md"
PLAN_NAME = "plan.json"
REPORT_NAME = "report.json"

_HEADING_RE = re.compile(r"(?m)^(##\s+.+)$")
_BRIEF_SECTION_RE = re.compile(
    r"(?ms)^##\s+The Book in Brief\s*$.*?(?=^##\s+|\Z)",
)
#: Headings that are a plate rather than the book — the brief sits AFTER these and
#: before everything else. Anything not matched here is treated as the book proper,
#: so a source-authored `## Introduction` (which on most nonfiction carries the
#: thesis) is analysed like any other section rather than skipped.
_CREDITS_RE = re.compile(r"^\s*(opening|closing|end)?\s*credits\s*$|^\s*front\s*matter\s*$", re.I)

_ANALYSE_TIMEOUT = 900
_DRAFT_TIMEOUT = 1200


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------


def _heading_text(line: str) -> str:
    return line.strip()[3:].strip()


def strip_brief(book_md: str) -> str:
    """Remove a previously injected brief, whitespace normalized. Idempotent."""
    return re.sub(r"\n{3,}", "\n\n", _BRIEF_SECTION_RE.sub("", book_md))


def sections_for_brief(book_md: str, *, exclude: list[str] | None = None) -> list[dict[str, str]]:
    """The book proper, split on `## `, with apparatus removed.

    Apparatus is the brief itself and the credits plate. The pipeline's own
    `## Introduction to the Book` is excluded too — it is a description of the
    edition, and a brief built partly from it would be condensing this repo's prose
    rather than the book's.

    `exclude` carries `brief_exclude_sections` from the book's config, by heading
    title. It exists for a section that is ABOUT the book rather than part of it and
    cannot be recognised as such: a publisher's foreword or an editor's
    introduction. White Nights ships with one — a modern essay that recounts the
    whole novella, including its ending, before Dostoyevsky's text begins. Analysed
    like a chapter it contributed ten "essential" points, every one a restatement of
    a chapter that had not been read yet, and the brief would have been built from
    somebody else's summary rather than from the story.

    DECLARED per book, never sniffed. The distinction between an author's own
    introduction — which on most nonfiction carries the thesis and must be
    condensed — and a publisher's foreword is not visible in the prose, and a rule
    that guessed would silently drop the thesis of the next expository book.
    """
    skip = {s.strip().lower() for s in (exclude or [])} | {"introduction to the book"}
    parts = _HEADING_RE.split(strip_brief(book_md))
    out: list[dict[str, str]] = []
    for i in range(1, len(parts), 2):
        title = _heading_text(parts[i])
        body = (parts[i + 1] if i + 1 < len(parts) else "").strip()
        if _CREDITS_RE.match(title) or title.strip().lower() in skip:
            continue
        if not body:
            continue
        out.append({"title": title, "body": body})
    return out


def excluded_sections(book_dir: Path, cfg: dict[str, Any] | None = None) -> list[str]:
    """Heading titles this book keeps out of its own condensation."""
    cfg = _series_config(book_dir) if cfg is None else cfg
    raw = cfg.get("brief_exclude_sections") or []
    return [str(x) for x in raw] if isinstance(raw, list) else [str(raw)]


def inject_brief(book_md: str, text: str) -> str:
    """Place the brief immediately above the introduction, below any credits plate.

    Anchored on the first heading that is neither the brief nor a credits plate —
    which is the introduction where one exists and the first chapter where one does
    not. Deliberately NOT anchored on the introduction's own heading: three routes
    in this repo produce a different introduction heading (the pipeline's own, a
    source-authored `## Introduction`, and none at all), and an anchor that has to
    recognise all three is an anchor that silently no-ops on the fourth. That is
    the exact failure `inject_introduction` documents having shipped.

    ORDER AGAINST THE INTRODUCTION IS LOAD-BEARING, and the apparatus sequence
    depends on this docstring for the reason. `apply_introduction` runs at step 5e
    and anchors on the first heading that is not ITSELF; run the brief first and
    that anchor finds the brief, so the introduction is injected above it and the
    two print in the wrong order. Run second, as step 5f does, and this anchor
    finds the introduction and the pair converges — every compose, however often —
    to credits, brief, introduction, chapter one.

    Idempotent: strips its own previous output first, so a convergence loop that
    re-enters compose many times never stacks briefs.
    """
    stripped = strip_brief(book_md)
    if not (text or "").strip():
        return stripped
    match = next(
        (m for m in _HEADING_RE.finditer(stripped) if not _CREDITS_RE.match(_heading_text(m.group(1)))),
        None,
    )
    block = f"{BRIEF_HEADING}\n\n{text.strip()}"
    if match is None:
        return (stripped.rstrip() + "\n\n" + block + "\n") if stripped.strip() else block + "\n"
    head, tail = stripped[: match.start()].rstrip(), stripped[match.start() :]
    return (head + "\n\n" if head else "") + block + "\n\n" + tail


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------


def _series_config(book_dir: Path) -> dict[str, Any]:
    path = Path(book_dir) / "_system" / "series-config.yaml"
    if not path.exists():
        return {}
    try:
        import yaml

        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


#: Content profile -> condensation strategy. Declared config always wins; this is
#: the fallback, and a profile absent from it falls through to the narrative frame
#: rather than to a guess about the prose.
_PROFILE_STRATEGY = {
    "islamic_scholarly": "doctrinal",
    "technical": "technical",
    "fiction": "narrative",
    "memoir": "biographical",
    "biography": "biographical",
    "guides": "expository",
    "business": "expository",
}
_FRAME_STRATEGY = {
    "external_narrator": "narrative",
    "participant_narrator": "narrative",
    "transmitted_report": "doctrinal",
    "first_person_author": "biographical",
}


def strategy_for(book_dir: Path, cfg: dict[str, Any] | None = None) -> str:
    """Which condensation strategy this book gets. DECLARED first, never sniffed.

    `brief_strategy` in series-config.yaml is authoritative, for the same reason
    `narrative_frame` is: what kind of book this is is a property of the source,
    and a pipeline that infers it from the prose in front of it will eventually
    infer it differently after a rewrite.
    """
    cfg = _series_config(book_dir) if cfg is None else cfg
    declared = str(cfg.get("brief_strategy") or "").strip().lower()
    if declared:
        return declared
    profile = str(cfg.get("content_profile") or "").strip().lower()
    if profile in _PROFILE_STRATEGY:
        return _PROFILE_STRATEGY[profile]
    frame = str(cfg.get("narrative_frame") or "").strip().lower()
    return _FRAME_STRATEGY.get(frame, "expository")


def target_words(book_dir: Path, cfg: dict[str, Any] | None = None, *, override: int | None = None) -> int:
    """The hard maximum for this book's brief.

    `brief_words` in series-config.yaml wins over `brief_mode`, which names a
    preset. A book that declares neither gets `standard` — 3,500 words — which is
    the default for every route.
    """
    if override:
        return int(override)
    cfg = _series_config(book_dir) if cfg is None else cfg
    explicit = cfg.get("brief_words")
    if explicit:
        try:
            return max(400, int(explicit))
        except (TypeError, ValueError):
            pass
    mode = str(cfg.get("brief_mode") or DEFAULT_PRESET).strip().lower()
    return PRESETS.get(mode, PRESETS[DEFAULT_PRESET])


def _facts(book_dir: Path) -> dict[str, Any]:
    meta = Path(book_dir) / "meta.yml"
    out: dict[str, Any] = {}
    if meta.exists():
        try:
            import yaml

            data = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
            out["title"] = data.get("title")
            out["author"] = data.get("author")
        except Exception:
            pass
    return out


# ---------------------------------------------------------------------------
# the lane
# ---------------------------------------------------------------------------


def _fingerprint(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(" ".join((p or "").split()).encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:16]


def _outline(plan: dict[str, Any]) -> str:
    """The plan, rendered for the drafting call. Grouped by section, ordered as the
    book runs, each group carrying the budget it earned and each point its tier."""
    by_section: dict[int, list[dict[str, Any]]] = {}
    for p in plan["retained"]:
        by_section.setdefault(p["section_index"], []).append(p)
    lines: list[str] = []
    for idx in sorted(by_section):
        pts = sorted(by_section[idx], key=lambda p: -p["score"])
        words = plan["section_words"].get(idx, 0)
        lines.append(f"\n### {pts[0]['section_title']}  [budget: about {words} words]")
        for p in pts:
            note = " (prerequisite)" if p.get("retained_as_prerequisite") else ""
            lines.append(f"  [{p['id']}] {p['tier'].upper()}{note} ({p['kind']}): {p['text']}")
    dropped_heavy = [p for p in plan["dropped"] if p["tier"] in ("supporting", "important")]
    if dropped_heavy:
        lines.append(
            "\nDELIBERATELY EXCLUDED — do not restore, and do not gesture at them:\n"
            + "\n".join(f"  - {p['text']}" for p in dropped_heavy[:12])
        )
    return "\n".join(lines)


def _ask(book_dir: Path, prompt: str, *, step: str, timeout: int, log, author, json_mode: bool = False) -> str:
    if author is not None:
        return (author(prompt) or "").strip()
    try:
        from _authoring._claude_runtime import pure_json_call_options, pure_text_call_options
        from _authoring._core import _run_claude_p_with_retry

        opts = pure_json_call_options() if json_mode else pure_text_call_options()
        rc, out, err = _run_claude_p_with_retry(
            prompt, timeout=timeout, book_dir=book_dir, phase="0book-brief", step=step, log=log, **opts
        )
        if rc != 0:
            log(f"    brief: {step} failed (claude -p rc={rc}): {str(err)[:120]}")
            return ""
        return (out or "").strip()
    except Exception as e:
        log(f"    brief: {step} skipped (non-fatal): {e}")
        return ""


def _json(raw: str) -> dict[str, Any]:
    s = (raw or "").strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", s, re.S)
    if m:
        s = m.group(1)
    else:
        i, j = s.find("{"), s.rfind("}")
        if i != -1 and j != -1:
            s = s[i : j + 1]
    return json.loads(s)


def analyse_sections(book_dir: Path, *, log=print, force: bool = False, author=None) -> list[dict[str, Any]]:
    """One structured record per section. Cached by content fingerprint.

    A section whose analysis fails is recorded as an EMPTY point list rather than
    dropped, so the section indices the point ids are built from stay stable across
    a partial run — a resumed analysis must not renumber the dependency graph.
    """
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    sections = sections_for_brief(book_md.read_text(encoding="utf-8"), exclude=excluded_sections(book_dir))
    cache_dir = book_dir / "_system" / CACHE_DIR / "analysis"
    cache_dir.mkdir(parents=True, exist_ok=True)
    strategy = strategy_for(book_dir)

    analyses: list[dict[str, Any]] = []
    prior_ids: list[str] = []
    for i, sec in enumerate(sections, start=1):
        path = cache_dir / f"S{i:02d}.json"
        fp = _fingerprint(sec["title"], sec["body"], strategy)
        if not force and path.exists():
            try:
                cached = json.loads(path.read_text(encoding="utf-8"))
                if cached.get("fingerprint") == fp:
                    analyses.append(cached)
                    prior_ids += [f"S{i:02d}-P{j:02d}" for j in range(1, len(cached.get("points") or []) + 1)]
                    continue
            except Exception:
                pass
        log(f"    brief: analysing section {i}/{len(sections)} — {sec['title']}")
        raw = _ask(
            book_dir,
            analyse_prompt(
                strategy=strategy,
                index=i,
                total=len(sections),
                title=sec["title"],
                body=sec["body"],
                prior="\n".join(f"  {pid}" for pid in prior_ids[-40:]),
            ),
            step=f"analyse-S{i:02d}",
            timeout=_ANALYSE_TIMEOUT,
            log=log,
            author=author,
            json_mode=True,
        )
        try:
            data = _json(raw)
            data["points"] = [p for p in (data.get("points") or []) if str(p.get("text") or "").strip()]
        except Exception as e:
            log(f"    brief: section {i} analysis unreadable ({e}) — recorded empty")
            data = {"title": sec["title"], "purpose": "", "points": []}
        data["title"] = sec["title"]
        data["fingerprint"] = fp
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        analyses.append(data)
        prior_ids += [f"S{i:02d}-P{j:02d}" for j in range(1, len(data["points"]) + 1)]

    # Prune analyses of sections that no longer exist. Excluding one section
    # renumbers every section after it, so the tail of the previous run is left
    # behind as a file whose name now belongs to nothing — harmless today, because
    # each file carries the fingerprint of the prose it describes and a mismatch
    # forces a re-read, but it is debris that reads like current state to anyone
    # opening the folder. White Nights left an `S07.json` holding an analysis of
    # the producer's introduction the moment that introduction was excluded.
    for stale in cache_dir.glob("S*.json"):
        if int(stale.stem[1:]) > len(sections):
            stale.unlink()
            log(f"    brief: pruned stale analysis {stale.name} — the book now has {len(sections)} sections")
    return analyses


def author_brief(
    book_dir: Path,
    *,
    log=print,
    force: bool = False,
    reanalyse: bool = False,
    author=None,
    words: int | None = None,
) -> dict[str, Any]:
    """Analyse, rank, draft, check, repair, gate. Returns a report; never raises.

    ``force`` re-drafts; ``reanalyse`` also re-reads the book. They are separate
    knobs because the analysis is both the expensive half and the half that
    invalidates itself correctly: every section is cached under a fingerprint of
    its own prose, so changed text is re-read without being asked and a re-draft
    for prompt-tuning must not re-buy the reading.
    """
    book_dir = Path(book_dir)
    out_dir = book_dir / "_system" / CACHE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = out_dir / BRIEF_NAME
    total = target_words(book_dir, override=words)

    if not force and cache.exists():
        cached = cache.read_text(encoding="utf-8").strip()
        if cached and gate_brief(cached, total_words=total)[0]:
            return {"text": cached, "cached": True, "words": len(cached.split())}

    analyses = analyse_sections(book_dir, log=log, force=reanalyse, author=author)
    if not any(a.get("points") for a in analyses):
        return {"text": "", "reason": "no analysable sections"}

    plan = build_plan(analyses, total_words=total)
    (out_dir / PLAN_NAME).write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
    log(
        f"    brief: {len(plan['points'])} points ranked, {len(plan['retained'])} retained "
        f"({len(plan['essential_ids'])} essential) into a {total}-word budget"
    )

    from _book_frontmatter import style_exemplar

    try:
        from _book_voice_prompts import ARTICULATION_REGISTER

        register = f"REGISTER (the same contract every chapter of this book was written under)\n{ARTICULATION_REGISTER}"
    except Exception:
        register = "REGISTER: clear, precise, unhurried expository prose for an educated general reader."
    exemplar = style_exemplar(book_dir)
    if exemplar:
        register += f"\n\nA REAL PASSAGE OF THIS BOOK'S PROSE, to match the voice against:\n{exemplar}"

    text = _ask(
        book_dir,
        draft_prompt(
            facts=_facts(book_dir),
            strategy=strategy_for(book_dir),
            register=register,
            plan=plan,
            outline=_outline(plan),
        ),
        step="draft",
        timeout=_DRAFT_TIMEOUT,
        log=log,
        author=author,
    )
    if not text:
        return {"text": "", "reason": "draft failed"}

    report: dict[str, Any] = {
        "total_words": total,
        "strategy": strategy_for(book_dir),
        "points": len(plan["points"]),
        "retained": len(plan["retained"]),
        "essential": len(plan["essential_ids"]),
        "draft_words": len(text.split()),
    }

    essential = [p for p in plan["retained"] if p["tier"] == "essential"]
    shortlist = lexical_shortlist(text, essential)
    missing: list[dict[str, Any]] = []
    if shortlist:
        raw = _ask(
            book_dir,
            adjudicate_prompt(draft=text, points="\n".join(f"  [{p['id']}] {p['text']}" for p in shortlist)),
            step="coverage",
            timeout=_ANALYSE_TIMEOUT,
            log=log,
            author=author,
            json_mode=True,
        )
        try:
            ids = set(_json(raw).get("missing") or [])
            missing = [p for p in shortlist if p["id"] in ids]
        except Exception as e:
            log(f"    brief: coverage adjudication unreadable ({e}) — treating shortlist as covered")
    report["coverage"] = {
        "essential": len(essential),
        "shortlisted": len(shortlist),
        "missing": [p["id"] for p in missing],
        "percent": round(100.0 * (len(essential) - len(missing)) / max(1, len(essential)), 1),
    }

    ok, reasons = gate_brief(text, total_words=total)
    if missing or not ok:
        log(f"    brief: repairing — {len(missing)} omission(s); {'; '.join(reasons) or 'shape ok'}")
        repaired = _ask(
            book_dir,
            repair_prompt(
                draft=text,
                register=register,
                findings="\n".join(f"  - {r}" for r in reasons),
                missing="\n".join(f"  - {p['text']}" for p in missing),
                total=total,
            ),
            step="repair",
            timeout=_DRAFT_TIMEOUT,
            log=log,
            author=author,
        )
        if repaired and gate_brief(repaired, total_words=total)[0]:
            text = repaired
            report["repaired"] = True
        elif repaired:
            report["repair_rejected"] = gate_brief(repaired, total_words=total)[1]

    ok, reasons = gate_brief(text, total_words=total)
    report["accepted"] = ok
    report["reasons"] = reasons
    report["words"] = len(text.split())
    (out_dir / REPORT_NAME).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if not ok:
        log(f"    brief: rejected — {'; '.join(reasons)}")
        return {"text": "", "reason": "; ".join(reasons), "report": report}
    cache.write_text(text + "\n", encoding="utf-8")
    return {"text": text, "words": len(text.split()), "report": report}


def apply_brief(
    book_dir: Path,
    *,
    log=print,
    force: bool = False,
    reanalyse: bool = False,
    author=None,
    words: int | None = None,
) -> dict[str, Any]:
    """Author and inject in one step. Report-shaped, like the other compose steps.

    THE HUMAN'S BRIEF WINS. The Composer is the singular path for anything bound
    for the PDF and this is a section a reader can open there, so a saved Composer
    edit is injected as written and no model is asked. Ungated, for the reason
    `apply_introduction` gives: a cap exists to hold a MODEL to a brief, and
    refusing a person's own words would be the pipeline overruling its author.
    """
    book_dir = Path(book_dir)
    book_md = book_dir / "book" / "book.md"
    if not book_md.exists():
        return {"applied": False, "reason": "no book.md"}

    from _book_edits import anchor_key, edited_body

    authored = edited_body(book_dir, anchor_key(BRIEF_HEADING))
    if authored:
        before = book_md.read_text(encoding="utf-8")
        after = inject_brief(before, authored)
        if after != before:
            book_md.write_text(after, encoding="utf-8")
        log(f"    brief: the author's own ({len(authored.split())} words), not re-written")
        return {"applied": True, "words": len(authored.split()), "authored": True}

    result = author_brief(book_dir, log=log, force=force, reanalyse=reanalyse, author=author, words=words)
    text = result.get("text") or ""
    if not text:
        return {"applied": False, "reason": result.get("reason") or "no brief"}
    before = book_md.read_text(encoding="utf-8")
    after = inject_brief(before, text)
    if after != before:
        book_md.write_text(after, encoding="utf-8")
    # A cached brief carries no report — it was accepted on a previous run and the
    # coverage number belongs to that run, not this one. Saying so beats printing
    # "?%", which reads as a check that failed rather than one that did not re-run.
    coverage = (result.get("report") or {}).get("coverage") or {}
    detail = f"{coverage['percent']}% essential coverage" if coverage else "reused from cache"
    log(f"    brief: {len(text.split())} words, {detail}")
    return {"applied": True, "words": len(text.split()), "report": result.get("report")}
