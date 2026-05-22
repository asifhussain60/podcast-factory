#!/usr/bin/env python3
"""Manual library handoff proposal writer (P1.2).

Writes a schema-valid `proposed-library-entries.md` under
    <book_dir>/_system/episode-drafts/EP##-<slug>/

The file is the canonical, schema-versioned channel through which the
podcast skill PROPOSES additions to memoir libraries (quotes, clinical
anecdotes). The journal skill — and ONLY the journal skill — promotes
proposed entries to their final memoir homes. The podcast skill NEVER
writes directly to `content/babu-memoir/**`.

See:
  • _workspace/plan/podcast-plan.yaml P1.2 acceptance
  • docs/podcast/manual-library-handoff.md (operator guide)
  • principle P-7 in podcast-plan.yaml (Manual handoff for cross-skill
    content, never automatic)
"""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Literal

SCHEMA_VERSION = 1


@dataclass
class QuoteProposal:
    text: str
    attribution: str
    source_ref: str
    episode_context: str
    confidence: Literal["high", "medium", "low"] = "medium"


@dataclass
class ClinicalProposal:
    title: str
    summary: str
    source_ref: str
    episode_context: str


@dataclass
class ProposalBundle:
    book_slug: str
    episode_id: str
    quotes: list[QuoteProposal] = field(default_factory=list)
    clinical: list[ClinicalProposal] = field(default_factory=list)


def _now_iso() -> str:
    # _dt.UTC is Python 3.11+. Use _dt.timezone.utc for 3.9 compatibility.
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _yaml_escape(s: str) -> str:
    """Escape a string for safe inclusion in a single-quoted YAML scalar."""
    return s.replace("'", "''")


def render_proposal(bundle: ProposalBundle, *, generated_at: str | None = None) -> str:
    """Render a ProposalBundle as the canonical proposed-library-entries.md file content.

    Format (the journal-side promotion script consumes this):
        ---
        schema_version: 1
        book_slug: <slug>
        episode_id: EP##-<slug>
        generated_by: scripts/podcast/_proposal_writer.py
        generated_at: <ISO-8601 UTC>
        ---
        ## Quotes proposed for content/babu-memoir/_system/quotes-library.txt
        - text: '...'
          attribution: '...'
          source_ref: '...'
          episode_context: '...'
          confidence: high|medium|low

        ## Clinical anecdotes proposed for content/babu-memoir/_system/clinic-library.txt
        - title: '...'
          summary: '...'
          source_ref: '...'
          episode_context: '...'

        ## Promotion ledger (journal side writes here when promoted)
        (intentionally empty on emit; journal-side promotion appends rows)
    """
    ts = generated_at or _now_iso()
    out: list[str] = []
    out.append("---")
    out.append(f"schema_version: {SCHEMA_VERSION}")
    out.append(f"book_slug: {bundle.book_slug}")
    out.append(f"episode_id: {bundle.episode_id}")
    out.append("generated_by: scripts/podcast/_proposal_writer.py")
    out.append(f"generated_at: {ts}")
    out.append("---")
    out.append("")
    out.append("## Quotes proposed for content/babu-memoir/_system/quotes-library.txt")
    if not bundle.quotes:
        out.append("(none in this episode)")
    else:
        for q in bundle.quotes:
            out.append(f"- text: '{_yaml_escape(q.text)}'")
            out.append(f"  attribution: '{_yaml_escape(q.attribution)}'")
            out.append(f"  source_ref: '{_yaml_escape(q.source_ref)}'")
            out.append(f"  episode_context: '{_yaml_escape(q.episode_context)}'")
            out.append(f"  confidence: {q.confidence}")
    out.append("")
    out.append("## Clinical anecdotes proposed for content/babu-memoir/_system/clinic-library.txt")
    if not bundle.clinical:
        out.append("(none in this episode)")
    else:
        for c in bundle.clinical:
            out.append(f"- title: '{_yaml_escape(c.title)}'")
            out.append(f"  summary: '{_yaml_escape(c.summary)}'")
            out.append(f"  source_ref: '{_yaml_escape(c.source_ref)}'")
            out.append(f"  episode_context: '{_yaml_escape(c.episode_context)}'")
    out.append("")
    out.append("## Promotion ledger (journal side writes here when promoted)")
    out.append("(empty — journal-side promotion appends rows here when content is moved into")
    out.append("content/babu-memoir/_system/{quotes-library,clinic-library}.txt)")
    out.append("")
    return "\n".join(out)


def write_proposal(
    book_dir: Path,
    bundle: ProposalBundle,
    *,
    generated_at: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Write the proposal file to:
        <book_dir>/_system/episode-drafts/<episode_id>/proposed-library-entries.md

    Returns the path written. Refuses to overwrite an existing file unless
    `overwrite=True` — promotion has a journal-side ledger and silently
    rewriting would erase audit history.
    """
    out_dir = book_dir / "_system" / "episode-drafts" / bundle.episode_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "proposed-library-entries.md"
    if out_path.exists() and not overwrite:
        raise FileExistsError(
            f"{out_path} already exists. Promotion is journal-side; do not "
            f"overwrite without explicit operator authorization (pass overwrite=True)."
        )
    out_path.write_text(render_proposal(bundle, generated_at=generated_at))
    return out_path
