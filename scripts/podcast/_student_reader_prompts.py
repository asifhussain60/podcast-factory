"""_student_reader_prompts.py — the model-facing half of the student-reader lane.

Everything a model reads for the FINDING pass lives here: the orientation
material pulled from the repo's corpora, and the prompt that asks a first-time
reader what stopped them. The sibling ``student_reader_notes`` keeps the half no
model is trusted with — the gate, the selection, the Scholar, and the write.

Split out of that module (2026-08-06) to keep it under the DR-005 line cap, the
same way ``_book_companion_prompts`` was split out of ``_book_companion``. The
dependency runs one way (driver -> prompts), so prompt wording can change without
touching a gate.

WHAT THIS EVIDENCE IS FOR, and what it is NOT for. It orients the student: it
helps tell a genuine difficulty from a merely unfamiliar one. It is NOT the card's
evidence — the Ismaili Scholar does its own retrieval afterwards and is the only
thing that cites anything. The prompt says so explicitly, because a student
reader who starts answering from this material stops being a student reader.
"""

from __future__ import annotations

import json
import sqlite3

from _paths import REPO_ROOT
from _student_reader import DEFECT_KINDS

_KB = REPO_ROOT / "content" / "knowledge-base"


# ─── evidence ────────────────────────────────────────────────────────────────
def fts_sessions(terms: str, limit: int = 4) -> list[dict[str, str]]:
    """Session transcripts that mention the chapter's own vocabulary."""
    db = _KB / "mirror.db"
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = conn.execute(
            "SELECT session_name, snippet(fts_sessions, 1, '', '', '…', 40) "
            "FROM fts_sessions WHERE fts_sessions MATCH ? LIMIT ?",
            (terms, limit),
        ).fetchall()
        conn.close()
    except Exception:
        # An unusable corpus must leave the pass grounded in the chapter alone,
        # never stop it: a missing session index is not a reason to skip a book.
        return []
    return [{"corpus": "ksessions", "ref": r[0], "text": r[1]} for r in rows]


def doctrine_atoms(limit: int = 40) -> list[dict[str, str]]:
    db = _KB / "knowledge.db"
    if not db.exists():
        return []
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = conn.execute(
            "SELECT id, body FROM atoms WHERE type='doctrine' AND tradition='fatimid-ismaili' LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
    except Exception:
        return []
    out = []
    for aid, body in rows:
        try:
            parsed = json.loads(body) if isinstance(body, str) else body
            text = parsed.get("statement") or parsed.get("text") or str(parsed)
        except Exception:
            text = str(body)
        out.append({"corpus": "doctrine", "ref": str(aid), "text": str(text)[:400]})
    return out


def evidence_block(title: str, prose: str) -> str:
    """What the model is allowed to cite, and nothing else."""
    # Chapter vocabulary as the retrieval query: the longest words the chapter
    # actually uses. Deterministic — same chapter, same query, same rows.
    words = sorted({w.strip(".,;:—\"'()").lower() for w in prose.split() if len(w) > 7})[:8]
    query = " OR ".join(w for w in words if w.isalpha()) or title
    rows = fts_sessions(query) + doctrine_atoms()
    if not rows:
        return "(no corroborating material was located — say so rather than supplying any)"
    return "\n".join(f"[{r['corpus']}:{r['ref']}] {r['text']}" for r in rows)


# ─── the prompt ──────────────────────────────────────────────────────────────
def build_prompt(title: str, prose: str, evidence: str, budget: int, already: list[str] | None = None) -> str:
    kinds = "\n".join(f"  - {k}" for k in DEFECT_KINDS)
    # Passages a previous run already noted. Told to the model rather than only
    # filtered afterwards: identical passages would be caught by the id anyway,
    # but a NEAR-miss — the next sentence, the same difficulty — would not, and
    # would arrive as a second note saying the same thing in a different place.
    seen = ""
    if already:
        listed = "\n".join(f"  - {q}" for q in already)
        seen = (
            "\nALREADY NOTED. These passages of this chapter have been marked before. Do "
            "not report them again, and do not report a neighbouring sentence that raises "
            "the SAME difficulty — find what is still unmarked, or return fewer.\n"
            f"{listed}\n"
        )
    return f"""You are reading one chapter of a translated Ismaili teaching text as a STUDENT
meeting it for the first time — not as a teacher explaining it. You are an
intelligent, careful reader: you can tell a passage that is genuinely hard to
resolve from one that is merely unfamiliar, and you do NOT flag the second.

Find ONLY the places a careful first-time reader is actually stopped. Two kinds
of stop, and nothing else:
  (a) you cannot tell what is meant — the sentence admits more than one reading
      and the chapter never resolves it, or a term or referent is used as if
      already known;
  (b) the chapter asserts something and offers nothing behind it.

For each one, write the QUESTION you would ask a scholar. That question is your
whole output for the passage — you are not explaining anything and you are not
answering it. An Ismaili scholar will answer it and the answer, not your
question, is what the reader will see.

A good question is specific to THIS passage and answerable: name the term, the
referent or the step that is missing, so the scholar knows exactly what is being
asked. "What does this mean?" is useless. "What are the seven kingdoms that
witness the twelve constellations, and why are there seven in the sky but
seventeen seas on the earth when the signs are twelve in both?" is the job.
Never pass judgement on the teaching, and never ask whether it is true — you are
recording where the chapter left you, not ruling on the tradition.

Report at most {budget} findings for this chapter. Fewer is correct when fewer
are real — an empty list is a valid answer and is better than a padded one.
{seen}

Classify each into EXACTLY one of these, using no other word:
{kinds}

BACKGROUND, for orientation only. This is material from the library that touches
the chapter's subject; it may help you tell a real difficulty from an unfamiliar
one. Do not quote it, do not cite it, and do not answer your own question from
it — the scholar does its own research.

{evidence}

Return ONLY a JSON array, no preamble and no code fence. Each element:
{{"defect": "<one of the kinds above>",
  "quote": "<a VERBATIM span of at least 4 words copied exactly from the chapter — this is where the note attaches>",
  "question": "<6-60 words, ending in a question mark: what you would ask a scholar about this passage>"}}

CHAPTER — {title}

{prose}
"""
