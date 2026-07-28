"""_morphology_parse.py — pure parser for the Quranic Arabic Corpus morphology file.

Reads ``quranic-corpus-morphology-0.4.txt`` (GPL, Kais Dukes / corpus.quran.com)
and yields one structured record per morphological segment. Pure and strict by
design: no I/O beyond the lines it is handed, no LLM, and a malformed line
RAISES with its line number rather than being skipped — the corpus is a fixed
artifact, so any parse surprise means the file or the parser is wrong, and a
silent skip would make every downstream count a lie.

File shape (verified against the corpus documentation, asserted at build time):
comment/metadata header lines, a blank line, a ``LOCATION FORM TAG FEATURES``
header row, then one TAB-separated row per segment. LOCATION is
``(chapter:verse:word:segment)``, 1-indexed. FORM/LEM/ROOT are Buckwalter ASCII
(``{ } ~ ` < > & ' * $`` are DATA, never delimiters — see ``_buckwalter``).
FEATURES is ``|``-delimited with NO fixed order: the first token is the segment
type (``STEM``/``PREFIX``/``SUFFIX``); everything else is extracted BY KEY
(``POS:``, ``LEM:``, ``ROOT:``) or kept as a bare flag. Root and lemma are
nullable — particles, pronouns and many proper nouns carry neither.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Iterator

_LOCATION_RE = re.compile(r"^\((\d+):(\d+):(\d+):(\d+)\)$")
_SEGMENT_TYPES = ("STEM", "PREFIX", "SUFFIX")
_HEADER_TOKEN = "LOCATION"


class MorphologyParseError(ValueError):
    """A line the parser refuses to guess about. Carries the 1-based line number."""


def parse_segments(lines: Iterable[str]) -> Iterator[dict[str, Any]]:
    """Yield one record per segment row.

    Record shape::

        {"location": {"chapter", "verse", "word", "segment"},   # 4 ints, 1-indexed
         "form": str,            # Buckwalter surface form
         "tag": str,             # POS tag column
         "segment_type": str,    # STEM | PREFIX | SUFFIX
         "pos": str | None,      # POS:x from FEATURES (stems)
         "lemma": str | None,    # LEM:x (Buckwalter), nullable
         "root": str | None,     # ROOT:x (Buckwalter), nullable
         "features": dict}       # every remaining KEY:VALUE, plus bare flags -> True

    Header/comment lines before the table and the column-header row are skipped;
    once the table starts, every line must parse or ``MorphologyParseError`` is
    raised with the offending line number.
    """
    in_table = False
    for lineno, raw in enumerate(lines, start=1):
        line = raw.rstrip("\n")
        if not in_table:
            # The table begins at the first row whose LOCATION column parses.
            # Everything before it (copyright header, blank line, the
            # LOCATION/FORM/TAG/FEATURES header row) is skipped structurally —
            # not by comment-prefix guessing, which the file does not promise.
            if line.startswith("("):
                in_table = True
            else:
                continue
        if not line.strip():
            continue
        cols = line.split("\t")
        if len(cols) != 4:
            raise MorphologyParseError(f"line {lineno}: expected 4 TAB columns, got {len(cols)}: {line!r}")
        loc_raw, form, tag, features_raw = cols
        m = _LOCATION_RE.match(loc_raw.strip())
        if not m:
            raise MorphologyParseError(f"line {lineno}: bad LOCATION {loc_raw!r}")
        chapter, verse, word, segment = (int(g) for g in m.groups())
        seg_type, pos, lemma, root, features = _parse_features(features_raw, lineno)
        yield {
            "location": {"chapter": chapter, "verse": verse, "word": word, "segment": segment},
            "form": form,
            "tag": tag,
            "segment_type": seg_type,
            "pos": pos,
            "lemma": lemma,
            "root": root,
            "features": features,
        }


def _parse_features(features_raw: str, lineno: int) -> tuple[str, str | None, str | None, str | None, dict[str, Any]]:
    """FEATURES parsed BY KEY — the corpus fixes no attribute order."""
    tokens = [t for t in features_raw.split("|") if t]
    if not tokens or tokens[0] not in _SEGMENT_TYPES:
        raise MorphologyParseError(
            f"line {lineno}: FEATURES must open with one of {_SEGMENT_TYPES}, got {features_raw!r}"
        )
    seg_type = tokens[0]
    pos: str | None = None
    lemma: str | None = None
    root: str | None = None
    features: dict[str, Any] = {}
    for token in tokens[1:]:
        # Split on the FIRST colon only: LEM/ROOT values are Buckwalter and may
        # themselves carry any ASCII punctuation except the delimiters.
        key, sep, value = token.partition(":")
        if not sep:
            features[token] = True  # bare flag: M, 3MS, GEN, (IV), Al+, ...
        elif key == "POS":
            pos = value
        elif key == "LEM":
            lemma = value
        elif key == "ROOT":
            root = value
        else:
            features[key] = value  # MOOD:, PRON:, SP:, ...
    return seg_type, pos, lemma, root, features


def group_words(segments: Iterable[dict[str, Any]]) -> Iterator[list[dict[str, Any]]]:
    """Group consecutive segments sharing ``(chapter, verse, word)`` into words.

    The corpus lists a word's segments consecutively, so simple run-grouping is
    exact — no sorting, no buffering beyond one word.
    """
    current: list[dict[str, Any]] = []
    current_key: tuple[int, int, int] | None = None
    for seg in segments:
        loc = seg["location"]
        key = (loc["chapter"], loc["verse"], loc["word"])
        if key != current_key and current:
            yield current
            current = []
        current_key = key
        current.append(seg)
    if current:
        yield current
