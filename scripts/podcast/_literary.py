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


# ── Gemini API ───────────────────────────────────────────────────────────────

_GEMINI_MODEL = "gemini-2.5-pro"
_GEMINI_TIMEOUT = 300  # seconds; literary rewrites are longer than analysis tasks


def _load_gemini_key() -> str:
    env = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if env:
        return env.strip()
    r = subprocess.run(
        ["security", "find-generic-password", "-s", "gemini_api_key",
         "-a", os.environ.get("USER", ""), "-w"],
        capture_output=True, text=True, timeout=10,
    )
    if r.returncode != 0:
        raise RuntimeError("gemini_api_key not found in keychain")
    return r.stdout.strip()


def _call_gemini(prompt: str) -> str:
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
        log(f"  {stem}: {word_count} words → building literary version …")

        prompt = _build_prompt(chapter_text, config)

        if dry_run:
            log(f"  [dry-run] prompt length: {len(prompt)} chars — no API call made")
            continue

        literary_text = _call_gemini(prompt)

        # Ensure the chapter title heading is preserved if the model strips it
        if not literary_text.strip().startswith("#"):
            title_match = re.match(r"^(#[^\n]+)", chapter_text)
            if title_match:
                literary_text = title_match.group(1) + "\n\n" + literary_text.strip()

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
