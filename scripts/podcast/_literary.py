"""_literary.py — Literary transformation phase (08b-literary).

Reads each enriched chapter (chapters/{slug}.txt), rewrites it as
literary nonfiction in the author's modernized voice, and writes the
result to:
  - BOOK_DIR/_stages/{chapter_id}/literary.md  (Studio tab source)
  - BOOK_DIR/chapters/literary/{slug}.txt       (NotebookLM upload source)

Voice and style are configured per-book in _system/series-config.yaml
under the `literary:` key. If absent, defaults derive from content_profile.

LLM: Gemini 2.5 Pro (gemini_api_key in keychain).
NO claude -p. Standing rule: bulk LLM = Gemini.

Idempotency: BOOK_DIR/_system/literary-log.md — rows with "DONE" are
skipped on re-run.

Usage (standalone):
  python3 _literary.py <BOOK_DIR>
  python3 _literary.py <BOOK_DIR> --chapter ch01-<slug>  # single chapter
  python3 _literary.py <BOOK_DIR> --dry-run               # show prompts, no write
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

from _rules import literary_voice_for_profile
from _content_profile import resolve_content_profile

# ── Default voice config per content_profile ────────────────────────────────
# Voice DEFAULTS now live in the single content-type registry (_rules.
# CONTENT_TYPE_REGISTRY); this module reads them via literary_voice_for_profile()
# so the literary voice and the rest of the pipeline can never disagree about a
# profile again. The voice INSTRUCTION TEXT below stays here — it is prompt-internal.

_VOICE_INSTRUCTIONS: dict[str, str] = {
    "author_first_person": (
        "Write entirely in first person as {narrator_subject}, speaking directly to {addressee}. "
        "The voice is intimate, rhetorically alive, and modernized — clear contemporary English with "
        "no archaisms or formal translations. Address the reader as you would address someone you are "
        "genuinely trying to reach."
    ),
    "contemporary_narrator": (
        "Write in a warm, clear contemporary voice that guides {addressee} through the material. "
        "The narrator is knowledgeable but never condescending — think of the best explainer you have "
        "ever read. Use 'you' naturally to address the reader."
    ),
    "scholarly_essayist": (
        "Write as a scholar thinking aloud — essayistic, reflective, precise. The voice of someone "
        "who has lived with this material long enough to see what is essential and what is not. "
        "Montaigne or Joan Didion in register: personal without being confessional."
    ),
    "peer_expert": (
        "Write as a senior practitioner talking directly to a peer who is learning. Show the thinking "
        "behind decisions, not just the decisions. Make the tacit explicit. Use 'you' naturally — "
        "this is a conversation, not a lecture."
    ),
    "narrative_voice": (
        "Write in a compelling narrative voice that draws the reader forward. Scene, character, and "
        "tension are your tools. Make the abstract concrete. Each section should feel like it is going "
        "somewhere."
    ),
}

_SCENE_SOURCE_INSTRUCTIONS: dict[str, str] = {
    "text_only": (
        "Use only scenes, images, and references that appear in the source text. "
        "Do not invent historical context or details that are not in the source."
    ),
    "historical_imagination": (
        "You may reconstruct the historical world of the text — setting, atmosphere, physical detail — "
        "grounded in the period and place but using imaginative specificity."
    ),
    "contemporary_analogies": (
        "Translate the situations and characters into contemporary equivalents where appropriate. "
        "The ideas should land in the present."
    ),
}


# ── Chapter-craft guidance (reading-edition revoice) ─────────────────────────
# Distilled from the professional book-rewrite craft standard. Applies to the
# whole-book revoice (_book_compose.py) for the companion reading-edition PDF.
# Two layers: a UNIVERSAL CORE that holds for every content profile, plus one of
# two mutually exclusive overlays — NARRATIVE (scene/dialogue-bearing sources:
# islamic_scholarly, fiction) or EXPOSITORY (technical/explainer/general
# nonfiction). New profiles route through chapter_craft_block() — one place to
# extend, never a prompt rewrite. The faithfulness/Arabic-script/output contract
# stays in _book_compose.py; this is prose-craft only and adds no doctrine.

_CHAPTER_CRAFT_CORE = (
    "Write this as a chapter of a real book by a skilled author-teacher — not a study guide, a "
    "summary, an outline, or a simplified paraphrase. The prose should feel authored, not assembled: "
    "it has movement, clear ideas, and clean transitions. The teaching must live INSIDE the prose, "
    "never announced as instructional scaffolding. Do NOT write \"the teaching of this chapter,\" "
    "\"the main lesson,\" \"the key takeaway,\" \"in plain language,\" \"this matters because,\" or "
    "\"the reader should understand.\" Show the idea through the specific things the text names; let "
    "the point arrive, do not label it.\n\n"
    "Preserve the source's SEQUENCE. Keep the original order of events, claims, concepts, and "
    "arguments unless a change is genuinely necessary for readability; the chapter should unfold "
    "continuously, not be rearranged into a lecture outline. You may clarify, smooth, and explain — "
    "slow the pace, break a dense argument into steps, show why each step follows from the last, use "
    "natural repetition — but do NOT dumb the material down, flatten a technical distinction, soften "
    "a demanding or severe teaching into vagueness, or modernize the worldview away. Make difficulty "
    "teachable, not easy.\n\n"
    "Define specialized terms inside the prose, never as a glossary line — not \"Hujja means proof\" "
    "but a sentence in which the meaning lands as the term is used. Use repetition only when each "
    "return adds force or clarity, never to pad. Bridge the reader into hard ideas with transitions "
    "that teach rather than abrupt jumps from narration to doctrine. Every paragraph should move the "
    "chapter forward — advance the matter, clarify the argument, deepen the stakes, or turn toward "
    "what comes next. Cut filler.\n\n"
    "Never let the prose read like any of these failure modes: a study guide (\"This chapter teaches "
    "three lessons. First...\"), an academic abstract (\"The passage establishes a hierarchical "
    "epistemology...\"), a podcast script (\"So what's really going on here is...\"), a casual "
    "explainer (\"Basically, the student realizes...\"), decorative mysticism (\"the luminous river "
    "of inward knowing cascaded through the secret chambers...\"), or mechanical paraphrase (\"He "
    "asked a question. The teacher answered. Then he asked another.\").\n\n"
    "Sentence discipline: prefer concrete verbs over abstract nominalizations; keep most sentences "
    "under 30 words, using an occasional longer one only for rhythm or emphasis; keep paragraphs "
    "short to medium; never stack more than two abstract concepts in one sentence; use a topic "
    "sentence when entering complex material; let an important short sentence stand alone when it "
    "earns the weight."
)

_CHAPTER_CRAFT_NARRATIVE = (
    "This source carries scenes, characters, and dialogue. Open the chapter in motion — a moment of "
    "tension, a character's action, a consequence carried from the previous chapter, or a question "
    "already alive in the scene — not with an outline or an explanation. Where the source has "
    "dialogue that carries argument, character, or a turning point, keep it; you may lightly "
    "modernize its sentence structure for clarity but never its meaning, and let it sound elevated "
    "yet natural. Use the exchanges as pressure: a student's question can reveal need, confusion, "
    "resistance, partial understanding, or readiness, and the teacher's answer should feel precise, "
    "restrained, and consequential. Do not gloss every line with commentary — explain only where the "
    "reader needs help following the argument; let strong dialogue carry its own force. Where the "
    "source uses an analogy, keep it and make its force land. Let the explanation emerge from what is "
    "happening in the scene wherever possible. Close the chapter by showing what has changed and why "
    "the next chapter must follow — narrative readiness, never a summary."
)

_CHAPTER_CRAFT_EXPOSITORY = (
    "This source is expository rather than narrative. Open each chapter on the concrete problem, "
    "question, or case at hand rather than an outline, and let the explanation build outward from the "
    "specific things the text names. Where the source genuinely uses lists, tables, or numbered "
    "steps to carry meaning, you may keep them — but never manufacture bullet-point summaries, "
    "recaps, or study-guide sections where the source had flowing exposition. Close on a consequence "
    "or the next open question, not a restated summary."
)

# Profiles whose sources are scene-and-dialogue bearing get the narrative overlay;
# everything else gets the expository overlay. Extend by adding to this set.
_NARRATIVE_CRAFT_PROFILES = {"islamic_scholarly", "fiction"}


def chapter_craft_block(profile: str | None) -> str:
    """Return the universal craft core plus the profile-appropriate overlay.

    Used by the reading-edition revoice (_book_compose.py) so every book — present
    and future — inherits the craft standard, with narrative vs. expository craft
    selected by content profile.
    """
    overlay = (_CHAPTER_CRAFT_NARRATIVE
               if (profile or "islamic_scholarly") in _NARRATIVE_CRAFT_PROFILES
               else _CHAPTER_CRAFT_EXPOSITORY)
    return f"{_CHAPTER_CRAFT_CORE}\n\n{overlay}"


# ── Gemini API ───────────────────────────────────────────────────────────────

_GEMINI_MODEL = "gemini-2.5-pro"
_GEMINI_TIMEOUT = 300  # seconds; literary rewrites are longer than analysis tasks


def _load_gemini_key() -> str:
    # Central resolver: env → keychain → Azure Key Vault (llm-gemini-api-key).
    from _secrets import get_gemini_key
    return get_gemini_key()


def _call_gemini(prompt: str) -> str:
    from _engine import engine_guard, TASK_REVOICE, ENGINE_GEMINI
    engine_guard(TASK_REVOICE, ENGINE_GEMINI)
    key = _load_gemini_key()
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}"
           f":generateContent?key={key}")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.55,
            "maxOutputTokens": 16000,
        },
    }).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=_GEMINI_TIMEOUT) as r:
        d = json.loads(r.read())
    return d["candidates"][0]["content"]["parts"][0]["text"]


# ── Config loading ───────────────────────────────────────────────────────────

def _read_literary_config(book_dir: Path) -> dict[str, str]:
    # Use the validated resolver (not a raw regex) so the literary voice agrees
    # with challenger/assertion routing about this book's profile.
    profile = resolve_content_profile(book_dir)
    config = literary_voice_for_profile(profile)
    config["content_profile"] = profile

    cfg_path = book_dir / "_system" / "series-config.yaml"
    if cfg_path.exists():
        text = cfg_path.read_text(encoding="utf-8")
        # Simple key: value parser for the literary: block
        in_block = False
        for line in text.splitlines():
            if re.match(r"^literary\s*:", line):
                in_block = True
                continue
            if in_block:
                if line and not line[0].isspace():
                    break  # left the literary block
                m = re.match(r"^\s+([\w_]+)\s*:\s*(.+)$", line)
                if m:
                    config[m.group(1)] = m.group(2).strip().strip('"\'')

    # Derive narrator_subject from meta.yml author if not set explicitly
    if config.get("narrator_subject") in ("the author", None, ""):
        meta = book_dir / "meta.yml"
        if meta.exists():
            am = re.search(r"^author\s*:\s*(.+)$", meta.read_text(encoding="utf-8"), re.M)
            if am:
                config["narrator_subject"] = am.group(1).strip()

    return config


# ── Prompt building ──────────────────────────────────────────────────────────

def _build_prompt(chapter_text: str, config: dict[str, str]) -> str:
    voice_key = config.get("narrator_voice", "author_first_person")
    scene_key = config.get("scene_source", "text_only")
    narrator = config.get("narrator_subject", "the author")
    addressee = config.get("addressee", "the reader")

    voice_instr = _VOICE_INSTRUCTIONS.get(voice_key, _VOICE_INSTRUCTIONS["author_first_person"])
    voice_instr = voice_instr.format(narrator_subject=narrator, addressee=addressee)
    scene_instr = _SCENE_SOURCE_INSTRUCTIONS.get(scene_key, _SCENE_SOURCE_INSTRUCTIONS["text_only"])

    return f"""You are transforming a scholarly or translated text into contemporary literary nonfiction.

NARRATOR VOICE
{voice_instr}

SCENES AND IMAGERY
{scene_instr}

STRUCTURE
Preserve every section heading exactly as it appears (## Section N — Title). Rewrite only the prose within each section. Do not add section headings that are not in the source, and do not remove any.

PRESERVE EVERYTHING INSTRUCTIVE
You have full freedom to re-voice and re-order for flow, but drop NOTHING the reader is meant to learn: every teaching, argument, example, named person, and citation (Quranic verse, hadith, line reference) in the source must survive in your rewrite. Re-voice a quotation into the narrator's voice if you wish, but do not omit its substance or its reference.

ARGUMENT
Let the argument emerge through engagement with specific things — a story Ghazali tells, a verse he cites, an image he uses — and open outward from there. Think Montaigne: the particular becomes the universal, never the other way around.

REGISTER
Contemporary literary English. Clear, precise, with rhetorical intelligence. No archaic diction. No "O such-and-such" address forms unless they arise naturally from the voice. No meta-commentary ("in this section, Ghazali argues…"). Write the thing, not about the thing.

LENGTH
Approximately the same length as the source. Do not summarize or compress.

OUTPUT
Return only the rewritten text. No preamble, no "Here is the rewrite:", no trailing commentary.

SOURCE TEXT
{chapter_text}"""


# ── Idempotency log ──────────────────────────────────────────────────────────

def _log_path(book_dir: Path) -> Path:
    return book_dir / "_system" / "literary-log.md"


def _already_done(book_dir: Path, stem: str) -> bool:
    log = _log_path(book_dir)
    if not log.exists():
        return False
    return f"- {stem}: DONE" in log.read_text(encoding="utf-8")


def _mark_done(book_dir: Path, stem: str) -> None:
    log = _log_path(book_dir)
    log.parent.mkdir(parents=True, exist_ok=True)
    if not log.exists():
        slug = book_dir.name
        log.write_text(
            f"# Literary transformation log — {slug}\n\n"
            f"Rows with `DONE` are checkpointed and skipped on re-run.\n\n",
            encoding="utf-8",
        )
    with log.open("a", encoding="utf-8") as f:
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        f.write(f"- {stem}: DONE at {ts}\n")


# ── Chapter discovery ────────────────────────────────────────────────────────

def _discover_chapters(book_dir: Path, only: str | None = None) -> list[Path]:
    chapters_dir = book_dir / "chapters"
    files = sorted(chapters_dir.glob("ch*.txt"))
    if only:
        files = [f for f in files if f.stem == only or f.name == only]
    return files


def _chapter_id_from_path(chapter_path: Path) -> str:
    """Derive the _stages/ subdirectory name from a chapter file path."""
    return chapter_path.stem  # e.g. "ch01-frame-and-the-problem-of-knowledge"


# ── No-teaching-lost guardrail ───────────────────────────────────────────────

def teaching_loss_findings(source_text: str, output_text: str) -> list[str]:
    """Deterministic check that the revoice dropped nothing instructive.

    Pure function (no LLM, no I/O). Returns a list of P1 finding strings — empty
    means clean. Three high-confidence checks: (1) every source ``## `` section
    heading survives verbatim, (2) no large word-count drop (>40%), (3) verse-style
    citation refs (e.g. ``2:255``) are not largely dropped. Conservative thresholds
    to avoid false positives on legitimate reflow.
    """
    findings: list[str] = []

    for h in dict.fromkeys(re.findall(r"^##\s+.+$", source_text, re.M)):
        if h.strip() not in output_text:
            findings.append(f"P1 missing section heading: {h.strip()[:80]!r}")

    sw, ow = len(source_text.split()), len(output_text.split())
    if sw >= 200 and ow < 0.6 * sw:
        pct = 100 * ow // max(sw, 1)
        findings.append(f"P1 large length drop: {sw}->{ow} words ({pct}% of source — possible content loss)")

    src_refs = set(re.findall(r"\b\d{1,3}:\d{1,3}\b", source_text))
    if src_refs:
        kept = sum(1 for r in src_refs if r in output_text)
        if kept < len(src_refs) * 0.5:
            findings.append(
                f"P1 citation refs dropped: only {kept}/{len(src_refs)} verse-style "
                f"references ({', '.join(sorted(src_refs)[:5])}…) survived")
    return findings


def _log_guardrail(book_dir: Path, stem: str, findings: list[str]) -> None:
    """Append guardrail findings for a chapter to literary-log.md (no silent pass)."""
    log = _log_path(book_dir)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"- {stem}: GUARDRAIL — {len(findings)} finding(s):\n")
        for fnd in findings:
            f.write(f"    - {fnd}\n")


# ── Section-chunked revoice (faithfulness over whole-chapter abridgement) ─────

def _split_chapter(text: str) -> tuple[str, str, list[tuple[str, str]]]:
    """Split a chapter into (title_line, preamble_body, [(heading, body), ...]).

    title_line  — a leading single-`#` chapter title, preserved verbatim.
    preamble    — prose before the first `## ` section.
    sections    — (verbatim `## ` heading, body) pairs.
    """
    lines = text.split("\n")
    title = ""
    start = 0
    for i, ln in enumerate(lines):
        if ln.strip():
            if re.match(r"^#\s+", ln):
                title, start = ln.strip(), i + 1
            break
    preamble: list[str] = []
    sections: list[tuple[str, str]] = []
    head: str | None = None
    body: list[str] = []
    for ln in lines[start:]:
        if re.match(r"^##\s+", ln):
            if head is not None:
                sections.append((head, "\n".join(body).strip()))
            head, body = ln.strip(), []
        elif head is None:
            preamble.append(ln)
        else:
            body.append(ln)
    if head is not None:
        sections.append((head, "\n".join(body).strip()))
    return title, "\n".join(preamble).strip(), sections


def _build_section_prompt(body: str, config: dict[str, str]) -> str:
    voice_key = config.get("narrator_voice", "author_first_person")
    scene_key = config.get("scene_source", "text_only")
    narrator = config.get("narrator_subject", "the author")
    addressee = config.get("addressee", "the reader")
    voice_instr = _VOICE_INSTRUCTIONS.get(voice_key, _VOICE_INSTRUCTIONS["author_first_person"]).format(
        narrator_subject=narrator, addressee=addressee)
    scene_instr = _SCENE_SOURCE_INSTRUCTIONS.get(scene_key, _SCENE_SOURCE_INSTRUCTIONS["text_only"])
    return f"""You are re-voicing ONE passage of a scholarly or translated text into contemporary literary nonfiction.

NARRATOR VOICE
{voice_instr}

SCENES AND IMAGERY
{scene_instr}

ABSOLUTE FAITHFULNESS
Re-voice EVERY sentence of this passage. Preserve every teaching, argument, example, named person, and citation (verse / hadith / line reference). You may improve flow and phrasing, but you must NOT summarize, condense, omit, or shorten. The output must be approximately the SAME LENGTH as the source passage — never shorter.

REGISTER
Contemporary literary English. No archaic diction. No meta-commentary ("in this passage…"). Write the thing, not about the thing.

OUTPUT
Return ONLY the re-voiced prose for this passage. Do NOT add a heading (it is supplied separately). No preamble, no fences.

SOURCE PASSAGE
{body}"""


def _revoice_chunk(body: str, config: dict[str, str], log, label: str) -> str:
    """Revoice one passage; retry once if the model abridged it (came back short)."""
    if not body.strip():
        return ""
    src_words = len(body.split())
    prompt = _build_section_prompt(body, config)
    out = _call_gemini(prompt).strip()
    if src_words >= 150 and len(out.split()) < 0.7 * src_words:
        log(f"      {label}: short ({len(out.split())}/{src_words}w) — retry (anti-abridge)")
        retry = _call_gemini(
            prompt + "\n\nYOUR PREVIOUS ATTEMPT WAS TOO SHORT — it summarized. Re-voice the FULL "
            "passage sentence by sentence; omit nothing; the output must be about the same length "
            "as the source."
        ).strip()
        if len(retry.split()) > len(out.split()):
            out = retry
    return out


def _revoice_chapter(chapter_text: str, config: dict[str, str], log, stem: str) -> str:
    """Section-by-section revoice: each source section preserved + re-voiced in
    isolation so the model cannot abridge across the chapter. Headings re-added
    verbatim. Falls back to a whole-chapter revoice (with retry) when there are
    no `## ` sections."""
    title, preamble, sections = _split_chapter(chapter_text)
    if not sections:
        whole = _revoice_chunk(chapter_text, config, log, stem)
        if title and not whole.lstrip().startswith("#"):
            whole = f"{title}\n\n{whole}"
        return whole.strip()
    log(f"    {stem}: {len(sections)} section(s) · revoicing per section")
    parts: list[str] = []
    if title:
        parts.append(title)
    if preamble:
        parts.append(_revoice_chunk(preamble, config, log, f"{stem}·intro"))
    for i, (head, body) in enumerate(sections, 1):
        parts.append(head)
        rv = _revoice_chunk(body, config, log, f"{stem}·§{i}/{len(sections)}")
        if rv:
            parts.append(rv)
    return "\n\n".join(p for p in parts if p).strip()


# ── Main transform ───────────────────────────────────────────────────────────

def author_literary_phase(
    book_dir: Path,
    *,
    only_chapter: str | None = None,
    dry_run: bool = False,
    log=print,
) -> None:
    """Transform all chapters (or one) into literary prose. Idempotent."""
    config = _read_literary_config(book_dir)
    chapters = _discover_chapters(book_dir, only=only_chapter)

    if not chapters:
        raise RuntimeError(f"No chapter files found in {book_dir / 'chapters'}")

    log(f"literary phase · {len(chapters)} chapter(s) · voice={config.get('narrator_voice')}")

    for chapter_path in chapters:
        stem = chapter_path.stem
        if _already_done(book_dir, stem):
            log(f"  {stem}: already DONE — skipping")
            continue

        chapter_text = chapter_path.read_text(encoding="utf-8").strip()
        word_count = len(chapter_text.split())
        log(f"  {stem}: {word_count} words → building literary version (section-chunked) …")

        if dry_run:
            _t, _p, _secs = _split_chapter(chapter_text)
            log(f"  [dry-run] {stem}: {len(_secs)} section(s) — no API call made")
            continue

        literary_text = _revoice_chapter(chapter_text, config, log, stem)

        chapter_id = _chapter_id_from_path(chapter_path)

        # Write Studio stage file
        stages_dir = book_dir / "_stages" / chapter_id
        stages_dir.mkdir(parents=True, exist_ok=True)
        (stages_dir / "literary.md").write_text(literary_text, encoding="utf-8")

        # Write NotebookLM source file
        literary_dir = book_dir / "chapters" / "literary"
        literary_dir.mkdir(parents=True, exist_ok=True)
        (literary_dir / f"{stem}.txt").write_text(literary_text, encoding="utf-8")

        out_words = len(literary_text.split())

        # No-teaching-lost guardrail: surface (do not silently pass) any sign the
        # rewrite dropped a section, a large chunk of text, or its citations.
        findings = teaching_loss_findings(chapter_text, literary_text)
        if findings:
            _log_guardrail(book_dir, stem, findings)
            log(f"  {stem}: ⚠ guardrail flagged {len(findings)} possible teaching-loss issue(s) "
                f"(logged to literary-log.md) — review before shipping")
            for fnd in findings:
                log(f"      · {fnd}")

        log(f"  {stem}: DONE — {out_words} words written")
        _mark_done(book_dir, stem)


# ── CLI entry point ──────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Literary transformation phase")
    p.add_argument("book_dir", type=Path, help="Path to book directory")
    p.add_argument("--chapter", help="Transform only this chapter stem (e.g. ch01-<slug>)")
    p.add_argument("--dry-run", action="store_true", help="Show prompt info without calling Gemini")
    args = p.parse_args()

    book_dir = args.book_dir.resolve()
    if not book_dir.is_dir():
        sys.exit(f"ERROR: {book_dir} is not a directory")

    try:
        author_literary_phase(
            book_dir,
            only_chapter=args.chapter,
            dry_run=args.dry_run,
        )
    except RuntimeError as e:
        sys.exit(f"ERROR: {e}")


if __name__ == "__main__":
    main()
