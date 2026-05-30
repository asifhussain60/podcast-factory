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

NOTEBOOKLM UPLOAD TABLE (mandatory format per feedback_notebooklm_instructions_format.md)
    EP | Title | Format | NLM Format | Length
    Length rule: episode framing > 3,500 words → Long; ≤ 3,200 words → Default.

EXIT CODES
    0  all chapters + framings present; PEQ all WARN or PASS
    1  missing artifacts or PEQ FAIL on any chapter
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from _paths import REPO_ROOT  # noqa: E402
from _quality import PEQScore, score as peq_score  # noqa: E402

# ---------------------------------------------------------------------------
# Episode-chapter discovery
# ---------------------------------------------------------------------------

def _load_episode_map(book_dir: Path) -> list[dict]:
    """Load episode↔chapter mapping from episode-chapter-map.json."""
    p = book_dir / "_system" / "episode-chapter-map.json"
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("mapping", [])


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
    """Find the chapter source .txt file."""
    chapters_dir = book_dir / "chapters"
    # Exact match first.
    exact = chapters_dir / f"{chapter_slug}.txt"
    if exact.exists():
        return exact
    # Pattern match (chNN-<slug>.txt).
    short_slug = chapter_slug.split("-", 1)[-1] if "-" in chapter_slug else chapter_slug
    matches = list(chapters_dir.glob(f"ch*-{short_slug}.txt"))
    return matches[0] if matches else None


def _resolve_framing_file(book_dir: Path, episode_slug: str) -> Path | None:
    """Find the episode framing .txt file in episodes/."""
    p = book_dir / "episodes" / f"{episode_slug}.txt"
    return p if p.exists() else None


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
    return "Long" if wc > 3_500 else "Default"


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
    book_dir = REPO_ROOT / "content" / "drafts" / "books" / slug
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
            "chapter_words": len(chapter_path.read_text(encoding="utf-8").split()) if chapter_path else 0,
            "framing_words": len(framing_path.read_text(encoding="utf-8").split()) if framing_path else 0,
            "chapter_ok": chapter_path is not None,
            "framing_ok": framing_path is not None,
            "slide_deck_ok": deck_path is not None,
            "slide_framing_ok": slide_framing_path is not None,
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

    # NotebookLM upload table (mandatory format).
    print(f"\nNOTEBOOKLM UPLOAD TABLE — *Ayyuhal Walad* (5 episodes)")
    print(f"  Read the chapter SOURCE to NotebookLM; paste the FRAMING into Customize.")
    print()
    print(f"  {'EP':<5} {'Title':<38} {'Format':<11} {'NLM Format':<12} {'Length'}")
    print(f"  {'-'*5} {'-'*38} {'-'*11} {'-'*12} {'-'*7}")
    for r in rows:
        print(f"  EP{r['ep']:<3d} {r['title']:<38} {r['format']:<11} {r['nlm_format']:<12} {r['length']}")

    print()
    print(f"  Source files  → upload each  chapters/chNN-<slug>.txt  as the ONLY source")
    print(f"  Framing files → paste body of episodes/EPNN-<slug>.txt  into the Customize box")
    print(f"  (skip the '# Framing: …' H1 title line when pasting)")

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
