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
    """Render the canonical markdown pipe table. Returns a multi-line string."""
    body = [f"| {' | '.join(COLUMNS)} |", "|" + "---|" * len(COLUMNS)]
    for r in rows:
        body.append("| " + " | ".join(r.cells()) + " |")
    return "\n".join(body)


def render_upload_table_lines(rows: list[UploadRow]) -> list[str]:
    """Same table as a list of lines, for line-by-line loggers."""
    return render_upload_table(rows).splitlines()
