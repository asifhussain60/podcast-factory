#!/usr/bin/env python3
"""Canonical NotebookLM upload table — the ONE place its format is defined.

Standing rule (locked per feedback_notebooklm_instructions_format.md): whenever
the pipeline is ready to upload chapters/episodes to NotebookLM, it presents a
markdown table with EXACTLY these columns:

    | Chapters | Episodes | Deep dive or debate | Length |

- Chapters            chapter number + title (e.g. "1. Knowledge Without Action")
- Episodes            "EP01 — <title>" so the file to upload is identifiable
- Deep dive or debate the NotebookLM conversation style (Deep Dive | Debate)
- Length              the NotebookLM length setting — DEFAULT is "Long"

Every emitter (chapter_driver finalize halt, assemble_bundle, probe bundle)
renders through this module so the format can never drift again. To change the
format, change it HERE — not in each caller.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from _paths import REPO_ROOT

# The standing default length setting. Change here to retune globally.
DEFAULT_LENGTH = "Long"

# Recognized per-episode overrides from the density plan (density_planner.py).
_VALID_LENGTHS = ("Default", "Long")


def load_density_lengths(book_dir) -> dict[int, str]:
    """Per-episode NotebookLM Length overrides from _system/density-plan.json.

    The density planner (scripts/podcast/density_planner.py) assigns each
    episode group a length setting; its plan artifact's presence IS the
    opt-in. Returns {} when no plan exists or it is unreadable, so every
    caller falls back to DEFAULT_LENGTH and books without a plan render
    byte-identically to before.
    """
    import json
    p = Path(book_dir) / "_system" / "density-plan.json"
    if not p.exists():
        return {}
    try:
        plan = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    out: dict[int, str] = {}
    for g in plan.get("groups", []):
        length = g.get("notebooklm_length")
        if length not in _VALID_LENGTHS:
            continue
        for ep in g.get("episode_numbers", []):
            if isinstance(ep, int):
                out[ep] = length
    return out


def length_for_episode(book_dir, ep_num: int,
                       lengths: dict[int, str] | None = None) -> str:
    """The Length cell for one episode: density-plan override or the default.

    Pass a pre-loaded *lengths* dict (from load_density_lengths) when
    rendering many rows to avoid re-reading the plan per row.
    """
    if lengths is None:
        lengths = load_density_lengths(book_dir)
    return lengths.get(ep_num, DEFAULT_LENGTH)

COLUMNS = ("Chapters", "Episodes", "Deep dive or debate", "Length")


def repo_rel_href(path, book_dir) -> str | None:
    """Repo-root-relative href for a file, for clickable markdown links.

    Uses the canonical ``REPO_ROOT`` from ``_paths`` rather than counting levels
    above ``book_dir`` — the level count is wrong for nested volumes
    (``content/<Bucket>/<container>/<vol>/``). ``book_dir`` is retained in the
    signature for back-compat but no longer drives the computation. Returns None
    for a missing path; falls back to the raw string if outside the repo root.
    """
    if path is None:
        return None
    try:
        return str(Path(path).resolve().relative_to(REPO_ROOT))
    except (ValueError, IndexError):
        return str(path)


def conversation_style(episode_format: str | None) -> str:
    """The 'Deep dive or debate' column value for an episode_format.

    NotebookLM offers Deep Dive / Brief / Critique / Debate; this pipeline uses
    Deep Dive for everything except an explicit debate episode.
    """
    return "Debate" if (episode_format or "").strip().lower() == "debate" else "Deep Dive"


@dataclass
class UploadRow:
    n: int                            # episode / chapter number
    chapter_title: str                # chapter display title
    episode_title: str                # episode display title
    episode_format: str = "deep_dive"
    length: str = DEFAULT_LENGTH
    chapter_href: str | None = None   # link target for the Chapters cell (chapter SOURCE file)
    episode_href: str | None = None   # link target for the Episodes cell (episode FRAMING file)
    session_index: int | None = None  # Session grouping (chapter-density standard) — None = flat
    session_title: str | None = None
    chapter_stem: str | None = None   # canonical chapter stem (ch19c-...) — drives the
                                      # worklist drop-target checklist; NOT rendered in cells()

    def chapters_text(self) -> str:
        title = self.chapter_title.strip() if self.chapter_title else f"Chapter {self.n}"
        return f"{self.n}. {title}"

    def episodes_text(self) -> str:
        return f"EP{self.n:02d} — {self.episode_title}"

    @staticmethod
    def _link(text: str, href: str | None) -> str:
        """Markdown link when an href is known; plain text otherwise.

        Chapters/Episodes are ALWAYS clickable links when the file is known
        (standing rule) — Chapters -> chapter SOURCE, Episodes -> episode FRAMING.
        """
        return f"[{text}]({href})" if href else text

    def cells(self) -> list[str]:
        return [
            self._link(self.chapters_text(), self.chapter_href),
            self._link(self.episodes_text(), self.episode_href),
            conversation_style(self.episode_format),
            self.length,
        ]


def render_upload_table(rows: list[UploadRow]) -> str:
    """Render the canonical markdown pipe table. Returns a multi-line string.

    Session grouping (presence-gated): when rows carry session metadata, a
    full-width banner row introduces each Session. Columns stay EXACTLY the
    locked four — the banner is a normal row with empty trailing cells, so
    flat books render byte-identically to before.
    """
    body = [f"| {' | '.join(COLUMNS)} |", "|" + "---|" * len(COLUMNS)]
    current_session: int | None = None
    for r in rows:
        if r.session_index is not None and r.session_index != current_session:
            current_session = r.session_index
            label = r.session_title or f"Session {r.session_index}"
            body.append(
                f"| **Session {r.session_index} — {label}** | | | |")
        body.append("| " + " | ".join(r.cells()) + " |")
    return "\n".join(body)


def render_upload_table_lines(rows: list[UploadRow]) -> list[str]:
    """Same table as a list of lines, for line-by-line loggers."""
    return render_upload_table(rows).splitlines()


# ── Slide-deck generation card (2026-06-10) ──────────────────────────────────
# SIBLING of the locked episode upload table (which is untouched above): the
# instruction card printed at the finalize halt for the NotebookLM "Slide deck"
# tool, one row per chapter that has a converged deck pair in slide-decks/.
# Centralized HERE for the same reason as the episode table — emitters
# (chapter_driver finalize halt, _slide_import missing-PDF halt) must render
# through this module so the format cannot drift.

import re as _re

DEFAULT_SLIDE_FORMAT = "Detailed deck"
DEFAULT_SLIDE_LENGTH = "Default"

SLIDE_COLUMNS = ("Chapter", "Upload source", "Describe-box paste", "Format",
                 "Length", "Save exported PDF as")

_FRAMING_RE = _re.compile(r"^(ch\d{2}[a-z]?)-framing-(.+)\.md$")


def discover_slide_framings(book_dir: Path) -> list[tuple[str, str, Path, Path | None]]:
    """(ch, slug, framing_path, deck_txt_path|None) per converged deck pair.

    Framing-driven (NEVER PDF-glob-driven): a chapter participates in the slide
    round iff its chNN-framing-<slug>.md exists — density-skipped chapters never
    get one. Tolerates letter-suffix chapter ids (ch14b).
    """
    deck_dir = Path(book_dir) / "slide-decks"
    out: list[tuple[str, str, Path, Path | None]] = []
    if not deck_dir.is_dir():
        return out
    for f in sorted(deck_dir.glob("ch*-framing-*.md")):
        m = _FRAMING_RE.match(f.name)
        if not m:
            continue
        ch, slug = m.group(1), m.group(2)
        deck_txt = deck_dir / f"{ch}-deck-{slug}.txt"
        out.append((ch, slug, f, deck_txt if deck_txt.exists() else None))
    return out


def expected_deck_pdf(book_dir: Path, ch: str, slug: str) -> Path:
    """Canonical drop path for a chapter's NotebookLM-exported deck PDF."""
    return Path(book_dir) / "slide-decks" / f"{ch}-{slug}.pdf"


@dataclass
class SlideDeckCardRow:
    ch: str                          # "ch01"
    slug: str
    framing_href: str | None = None  # paste into the Describe box (below its H1)
    deck_href: str | None = None     # upload source (.txt)
    expected_pdf: str = ""           # repo-relative drop path
    fmt: str = DEFAULT_SLIDE_FORMAT
    length: str = DEFAULT_SLIDE_LENGTH

    def cells(self) -> list[str]:
        link = UploadRow._link
        if self.ch == "book":
            # Book-level single deck (slide_deck_mode: book) — fixed filenames.
            deck_label, framing_label = "book-deck-source.txt", "book-framing.md"
        else:
            deck_label = f"{self.ch}-deck-{self.slug}.txt"
            framing_label = f"{self.ch}-framing-{self.slug}.md"
        return [
            self.ch,
            link(deck_label, self.deck_href),
            link(framing_label, self.framing_href),
            self.fmt,
            self.length,
            f"`{self.expected_pdf}`",
        ]


def render_slide_deck_card_lines(rows: list[SlideDeckCardRow]) -> list[str]:
    """The slide-deck generation card: header + per-chapter table + drop notes."""
    if not rows:
        return []
    lines = [
        "SLIDE DECK GENERATION (NotebookLM → Slide deck tool):",
        "  For each chapter: open the slide notebook, choose the Slide deck tool,",
        "  paste the framing file's contents BELOW its H1 into the Describe box,",
        "  pick the Format + Length below, Generate, then download the PDF export",
        "  and save it at the exact path in the last column.",
        "",
        f"| {' | '.join(SLIDE_COLUMNS)} |",
        "|" + "---|" * len(SLIDE_COLUMNS),
    ]
    for r in rows:
        lines.append("| " + " | ".join(r.cells()) + " |")
    lines += [
        "",
        "  Decks dropped before `--resume` are imported automatically into the",
        "  reading edition (0book-slide-import) — no further action needed.",
        "  To exempt a chapter from the reading-edition weave, create an empty",
        "  marker file: slide-decks/<ch>-<slug>.SKIP",
    ]
    return lines


def build_slide_deck_card(book_dir: Path) -> list[str]:
    """Discover framings and render the card; [] when no deck participates.

    Includes the book-level row (slide_deck_mode: book) when
    slide-decks/book-framing.md exists: ONE deck for the whole book, dropped
    at slide-decks/book-deck.pdf.
    """
    rows = []
    for ch, slug, framing, deck_txt in discover_slide_framings(book_dir):
        pdf = expected_deck_pdf(book_dir, ch, slug)
        rows.append(SlideDeckCardRow(
            ch=ch, slug=slug,
            framing_href=repo_rel_href(framing, book_dir),
            deck_href=repo_rel_href(deck_txt, book_dir) if deck_txt else None,
            expected_pdf=str(Path(pdf).resolve().relative_to(REPO_ROOT))
            if Path(pdf).resolve().is_relative_to(REPO_ROOT) else str(pdf),
        ))
    deck_dir = Path(book_dir) / "slide-decks"
    book_framing = deck_dir / "book-framing.md"
    if book_framing.exists():
        book_deck_txt = deck_dir / "book-deck-source.txt"
        book_pdf = deck_dir / "book-deck.pdf"
        rows.append(SlideDeckCardRow(
            ch="book", slug=Path(book_dir).name,
            framing_href=repo_rel_href(book_framing, book_dir),
            deck_href=repo_rel_href(book_deck_txt, book_dir) if book_deck_txt.exists() else None,
            expected_pdf=str(book_pdf.resolve().relative_to(REPO_ROOT))
            if book_pdf.resolve().is_relative_to(REPO_ROOT) else str(book_pdf),
        ))
    return render_slide_deck_card_lines(rows)


# ── Durable NotebookLM worklist (2026-06-14) ─────────────────────────────────
# The ONE artifact the operator works through for the manual NotebookLM round-
# trips. Written to BOOK_DIR/_system/notebooklm-worklist.md at the finalize halt
# (chapter_driver) so the upload table + slide card survive across sessions
# instead of scrolling off the terminal. This is a COMPOSITION of the renderers
# above (upload table + slide card) plus a live drop-target checklist — it never
# re-implements a table, so the locked formats stay single-sourced.

def build_worklist_lines(book_dir, *, upload_rows, resume_cmd: str) -> list[str]:
    """Compose the durable worklist: upload table + slide-deck card + drop checklist.

    *upload_rows* are pre-built UploadRow objects (already filtered to the
    NotebookLM episode set by the caller via build_upload_rows). *resume_cmd* is
    the exact command to run once every drop-target is satisfied. Checkboxes are
    live: ``[x]`` when the canonical ``m4a/<stem>.m4a`` already exists on disk.
    """
    m4a_dir = Path(book_dir) / "m4a"
    tx_dir = m4a_dir / "transcripts"
    lines: list[str] = [
        "# NotebookLM worklist",
        "",
        "Single source for the manual NotebookLM round-trips. Work top to bottom.",
        "The pipeline auto-normalizes + transcribes dropped audio and auto-imports",
        "dropped slide PDFs the moment you re-run the resume command at the bottom —",
        "no separate CLI steps, no filename fixing.",
        "",
        "## 1 - Audio (NotebookLM -> Audio Overview)",
        "",
        "Per row: click the CHAPTER cell to open the SOURCE to upload, and the EPISODE",
        "cell to open the FRAMING to paste into NotebookLM's Customize box. Download each",
        "generated .m4a and drop it anywhere under `m4a/` — filenames do not matter.",
        "",
    ]
    lines += render_upload_table_lines(upload_rows)

    card = build_slide_deck_card(book_dir)
    if card:
        lines += ["", "## 2 - Slide decks (NotebookLM -> Slide deck tool)", ""]
        lines += card

    lines += ["", "## 3 - Drop-target checklist", ""]
    for r in sorted(upload_rows, key=lambda x: x.n):
        stem = r.chapter_stem or f"ch{r.n:02d}"
        audio = m4a_dir / f"{stem}.m4a"
        box = "x" if audio.exists() else " "
        lines.append(f"- [{box}] EP{r.n:02d} — {r.episode_title}")
        lines.append(f"      audio      -> m4a/{stem}.m4a")
        lines.append(f"      transcript -> m4a/transcripts/{stem}.transcript.txt  (auto on --resume)")

    lines += [
        "",
        "## When every box above is checked",
        "",
        f"    {resume_cmd}",
        "",
        "The orchestrator normalizes filenames, transcribes via Azure Speech, imports",
        "any dropped slide PDFs, then publishes. If audio is still missing it re-halts",
        "cleanly and rewrites this file — nothing is lost.",
    ]
    return lines
