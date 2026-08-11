"""Read KSessions.sql — the offline dump of KSESSIONS_DEV.

The dump is a SQL Server script, UTF-16LE, ~29 MB, and the only offline copy of
Asif's delivered sessions. It is read rather than queried because the live server
(192.168.1.158) is not reachable from every machine this pipeline runs on, and a
book must ingest the same way whether it is or not.

Parsing is done by hand rather than with a SQL library for one reason: the values
carry authored HTML full of quotes, apostrophes and parentheses, and every
off-the-shelf splitter tested on it broke on `it''s` inside a transcript. The
scanner below tracks the string state explicitly, which is the only thing that
distinguishes a `)` closing the row from a `)` inside a sentence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from _paths import REPO_ROOT

# Anchored to the repo root, not the working directory — the lane is run from the
# repo root, from scripts/podcast/, and from tests, and a relative path resolves
# differently in all three.
DUMP_PATH = REPO_ROOT / "content/_shared/source-library/KSessions.sql"

# Sessions the lane may ingest, by KSESSIONS GroupID. An explicit list, never
# "every group with transcripts": G5 MABDA MA'AD belongs in the al-anwaar
# reading edition, and G7/G12/G18 already shipped as books. Selecting by
# availability would drag all four back in.
INGESTABLE_GROUPS: dict[int, str] = {
    1: "is-quran-a-miracle",
    2: "islam-vs-iman",  # no Groups row survives; identified by its session names
    3: "wise-reminder",
    8: "quran-comprehension",
    11: "surah-al-fateha",
    13: "mindful-prayers",
    14: "love-of-the-prophet",
}

# A transcript column holding the literal SQL NULL. Not an empty string — the row
# exists and claims to be a transcript, which is why it has to be recognised
# rather than merely falsy.
_SQL_NULL = "ULL"


@dataclass(frozen=True)
class Session:
    session_id: int
    group_id: int
    sequence: int
    name: str
    description: str
    date: datetime | None
    media_guid: str | None  # names the session's image folder, never an audio file
    transcript_html: str  # "" when the row is NULL or absent

    @property
    def has_transcript(self) -> bool:
        """True when there is enough text to be a chapter rather than a stub.

        500 plain-text characters, measured with the markup stripped. Every row
        in the dump is either under 60 characters (a stub) or over 4,000 (real
        teaching), so the threshold sits in an empty gap and no book's fate turns
        on where exactly it falls.
        """
        return len(strip_markup(self.transcript_html)) >= 500


def strip_markup(html: str) -> str:
    """Plain text length of authored HTML, for measurement only — never for output."""
    if not html or html == _SQL_NULL:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _rows(dump: str, table: str) -> list[str]:
    """Every INSERT's argument list for one table, as raw un-split text."""
    out: list[str] = []
    for match in re.finditer(rf"INSERT \[dbo\]\.\[{table}\] \([^)]*\) VALUES \(", dump):
        i, depth, buf, in_string = match.end(), 1, [], False
        while i < len(dump) and depth > 0:
            char = dump[i]
            if in_string:
                if char == "'":
                    if i + 1 < len(dump) and dump[i + 1] == "'":
                        buf.append("''")
                        i += 2
                        continue
                    in_string = False
                buf.append(char)
            elif char == "'":
                in_string = True
                buf.append(char)
            elif char == "(":
                depth += 1
                buf.append(char)
            elif char == ")":
                depth -= 1
                if depth == 0:
                    break
                buf.append(char)
            else:
                buf.append(char)
            i += 1
        out.append("".join(buf))
    return out


def _split(row: str) -> list[str]:
    """Split one row on top-level commas, unescaping SQL's doubled apostrophes."""
    parts: list[str] = []
    cur: list[str] = []
    depth, in_string, i = 0, False, 0
    while i < len(row):
        char = row[i]
        if in_string:
            if char == "'":
                if i + 1 < len(row) and row[i + 1] == "'":
                    cur.append("'")
                    i += 2
                    continue
                in_string = False
            else:
                cur.append(char)
        elif char == "'":
            in_string = True
        elif char == "(":
            depth += 1
            cur.append(char)
        elif char == ")":
            depth -= 1
            cur.append(char)
        elif char == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
            i += 1
            continue
        else:
            cur.append(char)
        i += 1
    parts.append("".join(cur).strip())
    return parts


def _date(field: str) -> datetime | None:
    found = re.search(r"N([\d\-]{10}T[\d:.]+)", field)
    return datetime.fromisoformat(found.group(1)) if found else None


def _guid(field: str) -> str | None:
    value = field.lstrip("N").strip()
    return value if re.fullmatch(r"[0-9a-f-]{36}", value) else None


def load_sessions(group_id: int, dump_path: Path | None = None) -> list[Session]:
    """Every session in one group, in delivery order, with its transcript attached.

    Refuses a group outside INGESTABLE_GROUPS rather than returning it, so the
    exclusions are enforced at the only place that reads the dump instead of
    being a rule each caller has to remember.
    """
    if group_id not in INGESTABLE_GROUPS:
        raise ValueError(
            f"group {group_id} is not ingestable by this lane. "
            f"Allowed: {sorted(INGESTABLE_GROUPS)}. "
            "G5 belongs in al-anwaar; G7/G12/G18 already shipped as books."
        )

    path = dump_path or DUMP_PATH
    dump = path.read_text(encoding="utf-16-le", errors="replace")

    transcripts: dict[int, str] = {}
    for row in _rows(dump, "SessionTranscripts"):
        cols = _split(row)
        html = cols[2].lstrip("N").strip()
        transcripts[int(cols[1])] = "" if html == _SQL_NULL else html

    sessions: list[Session] = []
    for row in _rows(dump, "Sessions"):
        cols = _split(row)
        if int(cols[1]) != group_id:
            continue
        session_id = int(cols[0])
        sessions.append(
            Session(
                session_id=session_id,
                group_id=group_id,
                sequence=int(cols[2] or 0),
                name=cols[4].lstrip("N").strip(),
                description=cols[5].lstrip("N").strip(),
                date=_date(cols[6]),
                media_guid=_guid(cols[7]),
                transcript_html=transcripts.get(session_id, ""),
            )
        )
    return sorted(sessions, key=lambda s: s.sequence)


def duplicate_transcripts(sessions: list[Session]) -> list[tuple[int, int]]:
    """Sessions whose transcripts are near-identical — a copy-paste in the source.

    Reported rather than repaired. Session 211 ("Love Based Religion") holds a
    99.96% copy of session 215 ("A Model For Success"), so publishing it verbatim
    would put a different lecture under its title. The lane's answer is to prefer
    the recording's own transcription for such a chapter, which it can only do if
    something names the pairs.
    """
    import difflib

    texts = {s.session_id: strip_markup(s.transcript_html) for s in sessions}
    substantial = [sid for sid, text in texts.items() if len(text) >= 500]
    found: list[tuple[int, int]] = []
    for i, left in enumerate(substantial):
        for right in substantial[i + 1 :]:
            if difflib.SequenceMatcher(None, texts[left], texts[right]).ratio() > 0.98:
                found.append((left, right))
    return found
