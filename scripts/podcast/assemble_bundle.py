#!/usr/bin/env python3
"""assemble_bundle.py — WC8 Phase 8: podcast bundle validation + NotebookLM upload table.

Validates the per-book podcast bundle (chapter sources + episode framings + slide decks),
runs the 5-axis PEQ scoring on each chapter, and emits the mandatory NotebookLM upload
table so Asif can start podcast generation immediately.

USAGE
    # Full validation + upload table + PEQ summary:
    python3 scripts/podcast/assemble_bundle.py --slug ayyuhal-walad

    # JSON output (for API callers):
    python3 scripts/podcast/assemble_bundle.py --slug ayyuhal-walad --json

    # Refresh PEQ scores and rewrite challenger-report sections:
    python3 scripts/podcast/assemble_bundle.py --slug ayyuhal-walad --score

WHAT IT VALIDATES
    chapters/chNN-<slug>.txt        → source uploaded to NotebookLM (audio notebook)
    episodes/EPNN-<slug>.txt        → customize prompt pasted into NotebookLM (audio)
    slide-decks/chNN-deck-<slug>.txt       → source uploaded to NotebookLM (slide notebook)
    slide-decks/chNN-framing-<slug>.md     → customize prompt pasted into NotebookLM (slides)

PEQ SCORING (5-axis, K6)
    Runs _quality.score() deterministically on each chapter source text.
    No API calls. Uses the same formula as the challenger's inner loop.

NOTEBOOKLM UPLOAD TABLE (mandatory canonical format — defined in _notebooklm_table.py,
per feedback_notebooklm_instructions_format.md)
    | Chapters | Episodes | Deep dive or debate | Length |
    Length default: Long (standing rule). Episodes cell carries "EP## — <title>".
    Chapters/Episodes cells are ALWAYS clickable links: Chapters -> chapter SOURCE,
    Episodes -> episode FRAMING.

EXIT CODES
    0  all chapters + framings present; PEQ all WARN or PASS
    1  missing artifacts or PEQ FAIL on any chapter
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _paths import REPO_ROOT, resolve_content  # noqa: E402
from _quality import PEQScore, score as peq_score  # noqa: E402

# ---------------------------------------------------------------------------
# Episode-chapter discovery
# ---------------------------------------------------------------------------

def _derive_episode_map_from_chapters(book_dir: Path) -> list[dict]:
    """Fallback: build mapping from chapters/ when episode-chapter-map.json is absent."""
    import re as _re
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.exists():
        return []
    pattern = _re.compile(r"^(ch(\d+)[a-z]?)-(.+)\.txt$")
    entries = []
    for f in sorted(chapters_dir.glob("ch*.txt")):
        m = pattern.match(f.name)
        if m:
            # Carry the `episode` slug too — consumers (incl. the finalize
            # NotebookLM table) read entry["episode"]; the JSON-load path
            # backfills it but this derive path previously did not (KeyError).
            entries.append({"chapter": m.group(1) + "-" + m.group(3),
                            "episode": f"EP{int(m.group(2)):02d}-{m.group(3)}",
                            "n": int(m.group(2))})
    if entries:
        p = book_dir / "_system" / "episode-chapter-map.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"mapping": entries}, indent=2) + "\n",
                     encoding="utf-8")
    return entries


def _load_episode_map(book_dir: Path) -> list[dict]:
    """Load episode↔chapter mapping from episode-chapter-map.json.

    Falls back to auto-derivation from chapters/ when the JSON is missing
    (common for books that were partially processed outside the orchestrator).
    """
    p = book_dir / "_system" / "episode-chapter-map.json"
    if not p.exists():
        return _derive_episode_map_from_chapters(book_dir)
    data = json.loads(p.read_text(encoding="utf-8"))
    mapping = data.get("mapping", [])
    # Backfill the `episode` slug when the on-disk map carries only chapter + n
    # (a real schema seen in shipped books). Without this, every consumer that
    # reads entry["episode"] KeyErrors — including the finalize upload table.
    for entry in mapping:
        if "episode" not in entry and entry.get("chapter") and entry.get("n") is not None:
            m = re.match(r"^ch\d+[a-z]?-(.*)$", str(entry["chapter"]))
            tail = m.group(1) if m else str(entry["chapter"])
            entry["episode"] = f"EP{int(entry['n']):02d}-{tail}"
    return mapping


def _load_contract(book_dir: Path, chapter_slug: str) -> dict:
    """Load chapter-contract.yml and return a dict (best-effort YAML parse)."""
    contracts_dir = book_dir / "chapter-contracts"
    # Contracts may be named by short slug (without chNN- prefix).
    short_slug = chapter_slug.split("-", 1)[-1] if "-" in chapter_slug else chapter_slug
    for candidate in [f"{chapter_slug}.yml", f"{short_slug}.yml"]:
        p = contracts_dir / candidate
        if p.exists():
            # Minimal YAML parser: read key: value lines.
            result: dict = {}
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.startswith("#") or ":" not in line:
                    continue
                k, _, v = line.partition(":")
                result[k.strip()] = v.strip()
            return result
    return {}


def _resolve_chapter_file(book_dir: Path, chapter_slug: str) -> Path | None:
    """Find the chapter source .txt file. Prefers chapters-wc8/ (holistic pipeline) over chapters/."""
    short_slug = chapter_slug.split("-", 1)[-1] if "-" in chapter_slug else chapter_slug

    # Holistic pipeline output takes priority when it exists.
    wc8_dir = book_dir / "chapters-wc8"
    if wc8_dir.exists() and any(wc8_dir.glob("ch*.txt")):
        exact = wc8_dir / f"{chapter_slug}.txt"
        if exact.exists():
            return exact
        matches = list(wc8_dir.glob(f"ch*-{short_slug}.txt"))
        if matches:
            return matches[0]

    chapters_dir = book_dir / "chapters"
    # Exact match first.
    exact = chapters_dir / f"{chapter_slug}.txt"
    if exact.exists():
        return exact
    # Pattern match (chNN-<slug>.txt).
    matches = list(chapters_dir.glob(f"ch*-{short_slug}.txt"))
    return matches[0] if matches else None


def _resolve_framing_file(book_dir: Path, episode_slug: str) -> Path | None:
    """Find the episode framing .txt file in episodes/."""
    p = book_dir / "episodes" / f"{episode_slug}.txt"
    return p if p.exists() else None


def build_upload_rows(book_dir: Path, mapping: list[dict],
                      filter_episode_ids=None) -> list:
    """Build the NotebookLM UploadRow list for a book from a given episode mapping.

    SINGLE constructor for the upload-table rows, shared by the finalize-halt
    stdout table (chapter_driver._print_notebooklm_table) and the durable
    worklist file so they render from identical data — no duplicated row logic.

    *mapping* is the episode↔chapter list, passed in by the caller (from its own
    discovery) so the table and the worklist see the SAME episode set.
    *filter_episode_ids*: None lists ALL episodes (byte-identical to the
    pre-override behavior — the golden-table latch); a set lists only those
    episode ids (mixed-engine books).

    Row construction is preserved verbatim from the prior inline loop, including
    the `isinstance(session_index, int)` guard — the minimal contract YAML parser
    yields strings, so session banners stay suppressed exactly as before; do not
    "fix" this without re-baselining the golden table.
    """
    from _notebooklm_table import (  # noqa: PLC0415
        UploadRow, repo_rel_href, load_density_lengths, length_for_episode,
    )
    density_lengths = load_density_lengths(book_dir)
    rows: list = []
    for entry in mapping:
        episode_slug = entry["episode"]
        if filter_episode_ids is not None and episode_slug not in filter_episode_ids:
            continue
        chapter_slug = entry["chapter"]
        ep_num = entry["n"]
        contract = _load_contract(book_dir, chapter_slug)
        episode_format = contract.get("episode_format", "deep_dive")
        title = contract.get("title", episode_slug).strip("\"'")
        chapter_path = _resolve_chapter_file(book_dir, chapter_slug)
        framing_path = _resolve_framing_file(book_dir, episode_slug)
        _si = contract.get("session_index")
        rows.append(UploadRow(
            n=ep_num,
            chapter_title=title,
            episode_title=title,
            episode_format=episode_format,
            length=length_for_episode(book_dir, ep_num, density_lengths),
            chapter_href=repo_rel_href(chapter_path, book_dir),
            episode_href=repo_rel_href(framing_path, book_dir),
            chapter_stem=chapter_slug,
            session_index=_si if isinstance(_si, int) else None,
            session_title=contract.get("session_title")
                if isinstance(contract.get("session_title"), str) else None,
        ))
    return rows


def _resolve_slide_deck(book_dir: Path, chapter_slug: str) -> tuple[Path | None, Path | None]:
    """Return (deck_source, framing) paths for the slide deck, or None if missing."""
    sd = book_dir / "slide-decks"
    # chNN-deck-<slug>.txt and chNN-framing-<slug>.md
    short = chapter_slug.split("-", 1)[-1] if "-" in chapter_slug else chapter_slug
    deck: Path | None = None
    framing: Path | None = None
    for f in sd.glob(f"ch*-deck-{short}.txt"):
        deck = f
    for f in sd.glob(f"ch*-framing-{short}.md"):
        framing = f
    return deck, framing


# ---------------------------------------------------------------------------
# PEQ scoring helpers
# ---------------------------------------------------------------------------

def _score_chapter(chapter_text: str, contract: dict) -> PEQScore:
    """Run 5-axis PEQ scoring on a chapter source text."""
    import re

    # Fidelity: Quran citation IDs from contract key_tensions (crude — no contract citations).
    citation_ids_source: list[str] = []

    # Arc labels from text.
    arc_rules = ["open_hook", "three_points", "close"]
    arc_found: list[str] = []

    text_lower = chapter_text.lower()
    if any(re.search(p, text_lower) for p in [
        r"(let us begin|where this chapter picks up|this chapter covers"
        r"|established the doctrine|settled the architecture)",
    ]):
        arc_found.append("open_hook")
    if re.search(r"(\bfirst\b|\bsecond\b|\bthird\b|\bthe first|\bthe second|\bthe third)", text_lower):
        arc_found.append("three_points")
    if re.search(
        r"(in closing|to close|what comes next|we ask god|may god|allāh"
        r"|##\s*(what comes next|closing|conclusion)|leaves the reader|has earned)",
        text_lower,
    ):
        arc_found.append("close")

    # Enrichment signals: domain terms + Quran refs.
    italics = re.findall(r"\*([^*]+)\*", chapter_text)
    bare_glosses = [
        m.group(1)
        for m in re.finditer(r"\b([A-Za-zāīūḍṭẓḥṣʿʾ]{4,})\s*\([^)]{5,80}\)", chapter_text)
        if m.group(1).lower() not in {
            "that", "this", "with", "from", "into", "also", "such", "when",
            "then", "than", "what", "which", "some", "have", "been", "were",
        }
    ]
    term_count = len(set(italics)) + len(set(bare_glosses) - set(italics))
    glossed = len(re.findall(r"\*[^*]+\*\s*\([^)]+\)", chapter_text)) + len(set(bare_glosses))
    qrefs = len(re.findall(r"\bQ?\d+:\d+\b", chapter_text))

    words = len(chapter_text.split())

    return peq_score(
        adapted_text=chapter_text,
        citation_ids_source=citation_ids_source,
        citation_ids_found=[],
        arc_rules=arc_rules,
        arc_labels_found=arc_found,
        term_count=term_count,
        glossed_count=min(glossed, term_count),
        quran_ref_count=qrefs,
        word_count=words,
        voice_exemplar_vector=None,
    )


# ---------------------------------------------------------------------------
# NotebookLM table helpers
# ---------------------------------------------------------------------------

def _nlm_format(episode_format: str) -> str:
    """Map episode_format to NotebookLM format setting label."""
    return "Debate" if episode_format == "debate" else "Deep dive"


def _nlm_length(framing_path: Path | None) -> str:
    """Default vs Long based on framing word count."""
    if framing_path is None or not framing_path.exists():
        return "Default"
    wc = len(framing_path.read_text(encoding="utf-8").split())
    return "Long" if wc > 3_300 else "Default"


def _friendly_format(episode_format: str) -> str:
    if episode_format == "debate":
        return "Debate"
    if episode_format == "recap":
        return "Recap"
    return "Deep Dive"


# ---------------------------------------------------------------------------
# Main assembly
# ---------------------------------------------------------------------------

def assemble_bundle(slug: str, *, run_score: bool = False, as_json: bool = False) -> int:
    """Validate bundle and emit the NotebookLM upload table."""
    book_dir = resolve_content(slug)
    if not book_dir.exists():
        print(f"ERROR: book directory not found: {book_dir}", file=sys.stderr)
        return 1

    mapping = _load_episode_map(book_dir)
    if not mapping:
        print("ERROR: episode-chapter-map.json missing or empty.", file=sys.stderr)
        return 1

    rows: list[dict] = []
    peq_results: list[dict] = []
    missing: list[str] = []
    any_fail = False

    for entry in mapping:
        episode_slug = entry["episode"]   # e.g. EP01-frame-and-first-counsel
        chapter_slug = entry["chapter"]   # e.g. ch01-frame-and-first-counsel
        ep_num = entry["n"]

        contract = _load_contract(book_dir, chapter_slug)
        episode_format = contract.get("episode_format", "deep_dive")
        title = contract.get("title", episode_slug)

        chapter_path = _resolve_chapter_file(book_dir, chapter_slug)
        framing_path = _resolve_framing_file(book_dir, episode_slug)
        deck_path, slide_framing_path = _resolve_slide_deck(book_dir, chapter_slug)

        row: dict = {
            "ep": ep_num,
            "episode": episode_slug,
            "chapter": chapter_slug,
            "title": title,
            "format": _friendly_format(episode_format),
            "nlm_format": _nlm_format(episode_format),
            "length": _nlm_length(framing_path),
            "chapter_path": chapter_path,
            "framing_path": framing_path,
            "chapter_words": len(chapter_path.read_text(encoding="utf-8").split()) if chapter_path else 0,
            "framing_words": len(framing_path.read_text(encoding="utf-8").split()) if framing_path else 0,
            "chapter_ok": chapter_path is not None,
            "framing_ok": framing_path is not None,
            "slide_deck_ok": deck_path is not None,
            "slide_framing_ok": slide_framing_path is not None,
            "session_index": contract.get("session_index")
                if isinstance(contract.get("session_index"), int) else None,
            "session_title": contract.get("session_title")
                if isinstance(contract.get("session_title"), str) else None,
        }

        if not chapter_path:
            missing.append(f"chapter source: chapters/{chapter_slug}.txt")
        if not framing_path:
            missing.append(f"episode framing: episodes/{episode_slug}.txt")

        # PEQ scoring.
        if chapter_path and (run_score or not as_json):
            chapter_text = chapter_path.read_text(encoding="utf-8")
            peq = _score_chapter(chapter_text, contract)
            row["peq"] = peq.as_dict()
            peq_results.append({
                "ep": ep_num, "title": title, "chapter": chapter_slug,
                **peq.as_dict(),
            })
            if peq.verdict == "FAIL":
                any_fail = True

        rows.append(row)

    if as_json:
        print(json.dumps({"slug": slug, "episodes": rows, "missing": missing, "peq": peq_results}, indent=2))
        return 1 if missing or any_fail else 0

    # ── Human-readable output ──────────────────────────────────────────────

    print(f"\n{'='*72}")
    print(f" Podcast bundle: {slug}")
    print(f"{'='*72}\n")

    # Artifact status table.
    print("ARTIFACT STATUS")
    print(f"  {'EP':<6} {'Chapter':<38} {'Source':>7} {'Framing':>8} {'Slides':>7}")
    print(f"  {'-'*6} {'-'*38} {'-'*7} {'-'*8} {'-'*7}")
    for r in rows:
        src = "✅" if r["chapter_ok"] else "❌"
        frm = "✅" if r["framing_ok"] else "❌"
        sld = "✅" if r["slide_deck_ok"] else "⬜"
        print(f"  EP{r['ep']:<4d} {r['chapter']:<38} {src:>7} {frm:>8} {sld:>7}")

    if missing:
        print(f"\n⚠  MISSING ARTIFACTS:")
        for m in missing:
            print(f"   • {m}")

    # PEQ table.
    if peq_results:
        print(f"\nPEQ SCORES (5-axis: Fidelity 30% / Voice 20% / Structure 18% / Enrichment 17% / Interest 15%)")
        print(f"  {'EP':<5} {'Title':<38} {'Fid':>5} {'Str':>5} {'Enr':>5} {'Int':>5} {'Total':>6} {'Verdict'}")
        print(f"  {'-'*5} {'-'*38} {'-'*5} {'-'*5} {'-'*5} {'-'*5} {'-'*6} {'-'*7}")
        for p in peq_results:
            v_icon = "✅" if p["verdict"] == "PASS" else ("⚠️" if p["verdict"] == "WARN" else "❌")
            print(f"  EP{p['ep']:<3d} {p['title']:<38} "
                  f"{p['fidelity']:>5.1f} {p['structure']:>5.1f} {p['enrichment']:>5.1f} "
                  f"{p['interest']:>5.1f} {p['total']:>6.1f} {v_icon} {p['verdict']}")

    # NotebookLM upload table (mandatory canonical format — see _notebooklm_table.py).
    from _notebooklm_table import (  # noqa: PLC0415
        UploadRow, render_upload_table_lines, repo_rel_href,
        load_density_lengths, length_for_episode,
    )
    # Per-episode engine routing: when a book carries episode_engine_overrides,
    # the upload table lists ONLY the episodes routed to NotebookLM (the rest are
    # auto-rendered by ElevenLabs). With NO overrides the table is unchanged —
    # byte-identical to before (the golden-test latch).
    from _audio_engines import (  # noqa: PLC0415
        engine_for_episode, episode_engine_overrides, ENGINE_NOTEBOOKLM,
    )
    _overrides = episode_engine_overrides(book_dir)
    _table_rows = ([r for r in rows
                    if engine_for_episode(book_dir, r["episode"]) == ENGINE_NOTEBOOKLM]
                   if _overrides else rows)
    _suffix = " — NotebookLM-routed only" if _overrides else ""
    print(f"\nNOTEBOOKLM UPLOAD TABLE — {slug} ({len(_table_rows)} episodes){_suffix}")
    print(f"  Click the CHAPTER cell to open the SOURCE to upload; the EPISODE cell")
    print(f"  to open the FRAMING to paste into NotebookLM's Customize box.")
    print(f"  (skip the '# Framing: …' H1 title line when pasting)")
    print()
    _density_lengths = load_density_lengths(book_dir)
    upload_rows = [
        UploadRow(
            n=r["ep"],
            chapter_title=str(r["title"]).strip("\"'"),
            episode_title=str(r["title"]).strip("\"'"),
            episode_format="debate" if r["nlm_format"].strip().lower() == "debate" else "deep_dive",
            length=length_for_episode(book_dir, r["ep"], _density_lengths),
            chapter_href=repo_rel_href(r.get("chapter_path"), book_dir),
            episode_href=repo_rel_href(r.get("framing_path"), book_dir),
            session_index=r.get("session_index"),
            session_title=r.get("session_title"),
        )
        for r in _table_rows
    ]
    for line in render_upload_table_lines(upload_rows):
        print(f"  {line}")

    # Slide deck status.
    slides_done = sum(1 for r in rows if r["slide_deck_ok"])
    if slides_done == 0:
        print(f"\n⬜  SLIDE DECKS: none yet — run generate_slide_decks.py to produce all 5.")
    elif slides_done < len(rows):
        print(f"\n🔄  SLIDE DECKS: {slides_done}/{len(rows)} done — run generate_slide_decks.py for the rest.")
    else:
        print(f"\n✅  SLIDE DECKS: all {slides_done} present.")

    print(f"\n{'='*72}\n")

    return 1 if missing or any_fail else 0


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="WC8 Phase 8 — bundle validation + NotebookLM table.")
    ap.add_argument("--slug", required=True)
    ap.add_argument("--score", action="store_true", help="Re-run PEQ scoring")
    ap.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON")
    args = ap.parse_args()
    sys.exit(assemble_bundle(args.slug, run_score=args.score, as_json=args.as_json))


if __name__ == "__main__":
    main()
