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

# The standing default length setting. Change here to retune globally.
DEFAULT_LENGTH = "Long"

COLUMNS = ("Chapters", "Episodes", "Deep dive or debate", "Length")


def conversation_style(episode_format: str | None) -> str:
    """The 'Deep dive or debate' column value for an episode_format.

    NotebookLM offers Deep Dive / Brief / Critique / Debate; this pipeline uses
    Deep Dive for everything except an explicit debate episode.
    """
    return "Debate" if (episode_format or "").strip().lower() == "debate" else "Deep Dive"


@dataclass
class UploadRow:
    n: int                       # episode / chapter number
    chapter_title: str           # chapter display title
    episode_title: str           # episode display title
    episode_format: str = "deep_dive"
    length: str = DEFAULT_LENGTH

    def chapters_cell(self) -> str:
        title = self.chapter_title.strip() if self.chapter_title else f"Chapter {self.n}"
        return f"{self.n}. {title}"

    def episodes_cell(self) -> str:
        return f"EP{self.n:02d} — {self.episode_title}"

    def cells(self) -> list[str]:
        return [
            self.chapters_cell(),
            self.episodes_cell(),
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
