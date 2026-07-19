"""schema.py — the two documents the supplication lane owns, and their rules.

There are exactly two persisted documents:

  _system/source-record.json   IMMUTABLE after the OCR step. The ordered OCR
                               lines with page/line provenance, plus a digest.
                               Nothing downstream may rewrite it.

  units.json                   The working document. Segmentation writes unit
                               boundaries, the human review pass adjusts them,
                               translation fills in English.

THE INTEGRITY INVARIANT
-----------------------
A unit's `source` text is never authored, regenerated, or edited by a model.
Models emit only `line_ids` (segmentation) and `english` (translation). The
`source` string is DERIVED, every single time it is needed, by joining the
referenced lines out of the immutable OCR record — see `derive_source`.

This makes the verbatim guarantee structural rather than merely checked: there
is no code path by which model output can reach the source column. The gate in
gates.py is then an independent second assertion, not the only line of defence.

THE OCR LINE IS THE ATOM
------------------------
Units reference whole OCR lines. A human reviewer may MERGE freely (concatenate
id lists) and may SPLIT at any line boundary — but cannot split *within* a line,
because doing so would require someone to retype source text and would break the
invariant above. If a supplication genuinely needs a finer break, the fix is to
re-run OCR, not to hand-edit the source.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The only two scripts this lane renders. `source_language` is ALWAYS passed
# explicitly and never inferred — the existing pipeline's `ingest_source.py`
# defaults `--src-lang` to "ar" with nothing wiring series-config's
# `source_language` into it, which would silently translate Urdu as Arabic.
# This lane refuses to guess.
SOURCE_LANGUAGES: tuple[str, ...] = ("ar", "ur")

LINE_ID_RE = re.compile(r"^p(\d+)l(\d+)$")

# Metadata fields of the content model, in reading order. All optional; the
# renderer emits only the ones present.
META_FIELDS: tuple[str, ...] = (
    "type",
    "attributed_to",
    "occasion",
    "purpose",
    "place",
)


class SupplicationError(RuntimeError):
    """Any lane-level contract violation. Always fatal — never auto-repaired."""


def line_id(page: int, line: int) -> str:
    """Provenance id for an OCR line: page 3, line 12 → 'p3l12'."""
    return f"p{page}l{line}"


@dataclass(frozen=True)
class SourceLine:
    id: str
    page: int
    line: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "page": self.page, "line": self.line, "text": self.text}


@dataclass
class SourceRecord:
    """The immutable OCR record. Written once, read forever."""

    slug: str
    source_language: str
    source_pdf: str
    lines: list[SourceLine]
    ocr: dict[str, Any] = field(default_factory=dict)

    # ── digest ──────────────────────────────────────────────────────────────
    @property
    def digest(self) -> str:
        """SHA-256 over the id+text of every line, in order.

        Any reordering, edit, insertion, or deletion changes this. It is stamped
        into units.json at segmentation time, so a units.json can never be
        silently paired with a different (or re-run) OCR record.
        """
        h = hashlib.sha256()
        for ln in self.lines:
            h.update(ln.id.encode("utf-8"))
            h.update(b"\x1f")
            h.update(ln.text.encode("utf-8"))
            h.update(b"\x1e")
        return h.hexdigest()

    def by_id(self) -> dict[str, SourceLine]:
        return {ln.id: ln for ln in self.lines}

    # ── persistence ─────────────────────────────────────────────────────────
    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "source_language": self.source_language,
            "source_pdf": self.source_pdf,
            "ocr": self.ocr,
            "digest": self.digest,
            "lines": [ln.to_dict() for ln in self.lines],
        }

    def write(self, path: Path) -> None:
        if path.exists():
            raise SupplicationError(
                f"{path} already exists — the OCR record is immutable. Delete it "
                f"deliberately and re-run the OCR step if the source really changed."
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> "SourceRecord":
        if not path.is_file():
            raise SupplicationError(f"OCR record not found: {path} — run the ocr step first.")
        d = json.loads(path.read_text(encoding="utf-8"))
        rec = cls(
            slug=d["slug"],
            source_language=d["source_language"],
            source_pdf=d.get("source_pdf", ""),
            ocr=d.get("ocr", {}),
            lines=[SourceLine(id=x["id"], page=x["page"], line=x["line"], text=x["text"]) for x in d["lines"]],
        )
        stored = d.get("digest")
        if stored and stored != rec.digest:
            raise SupplicationError(
                f"{path}: digest mismatch — the OCR record has been edited since it was "
                f"written (stored {stored[:12]}…, recomputed {rec.digest[:12]}…). "
                f"The record is immutable; restore it from git."
            )
        return rec


def derive_source(unit_line_ids: list[str], index: dict[str, SourceLine]) -> str:
    """THE one function that produces a unit's source text.

    Joins the referenced OCR lines with a single space. OCR wraps mid-phrase, so
    a space is the correct join for both Arabic and Urdu; no other normalization
    is applied, because normalizing would mean altering source text.
    """
    missing = [i for i in unit_line_ids if i not in index]
    if missing:
        raise SupplicationError(f"unit references unknown OCR line id(s): {missing}")
    return " ".join(index[i].text for i in unit_line_ids)


def refrain_units(doc: "UnitsDoc", record: "SourceRecord") -> set[int]:
    """Unit numbers whose source text occurs verbatim MORE THAN ONCE.

    A refrain in a supplication is a short response line that recurs through a
    litany; marking it lets someone reciting from the page find their place
    again. That is worth showing — but ONLY when it is provably true.

    An earlier version asked the segmentation model to flag refrains. That was
    an unvalidated judgment call: a model that over-flags speckles the page with
    highlight for no reason, and nothing downstream could tell a real refrain
    from a guess. This function replaces that judgment with arithmetic — a unit
    is a refrain if and only if its exact derived source appears again elsewhere
    in the same document. It cannot over-fire, it is testable, and it updates
    automatically when a human merges or splits units during review.

    Comparison is on the SOURCE, not the English: the source is the immutable
    ground truth, and two units with identical source must render identically
    anyway.
    """
    index = record.by_id()
    sources = [derive_source(u.line_ids, index) for u in doc.units]
    counts: dict[str, int] = {}
    for src in sources:
        counts[src] = counts.get(src, 0) + 1
    return {u.n for u, src in zip(doc.units, sources) if counts[src] > 1}


@dataclass
class Unit:
    """A unit is a grouping of OCR lines plus its English rendering.

    NOTE there is no `refrain` field. Whether a unit is a refrain is DERIVED
    (see `refrain_units`), never stored and never decided by a model.
    """

    n: int
    line_ids: list[str]
    english: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"n": self.n, "line_ids": list(self.line_ids), "english": self.english}


@dataclass
class UnitsDoc:
    """The working document: unit boundaries + English + presentation metadata."""

    slug: str
    source_language: str
    source_digest: str
    units: list[Unit]
    title_en: str = ""
    title_src: str = ""
    meta: dict[str, str] = field(default_factory=dict)
    preamble_en: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "source_language": self.source_language,
            "source_digest": self.source_digest,
            "title_en": self.title_en,
            "title_src": self.title_src,
            "meta": {k: v for k, v in self.meta.items() if k in META_FIELDS and v},
            "preamble_en": self.preamble_en,
            "units": [u.to_dict() for u in self.units],
        }

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> "UnitsDoc":
        if not path.is_file():
            raise SupplicationError(f"units.json not found: {path} — run the segment step first.")
        d = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            slug=d["slug"],
            source_language=d["source_language"],
            source_digest=d.get("source_digest", ""),
            title_en=d.get("title_en", ""),
            title_src=d.get("title_src", ""),
            meta=dict(d.get("meta") or {}),
            preamble_en=d.get("preamble_en", ""),
            units=[
                Unit(
                    n=u.get("n", i + 1),
                    line_ids=list(u["line_ids"]),
                    english=u.get("english", ""),
                )
                for i, u in enumerate(d["units"])
            ],
        )


def render_payload(doc: UnitsDoc, record: SourceRecord) -> dict[str, Any]:
    """Materialize the shape render-supplication-pdf.mjs consumes.

    This is the ONLY place `source` strings enter the rendered artifact, and they
    are derived here from the immutable record — never read from units.json.
    """
    index = record.by_id()
    refrains = refrain_units(doc, record)
    return {
        "slug": doc.slug,
        "source_language": doc.source_language,
        "title_en": doc.title_en,
        "title_src": doc.title_src,
        "meta": {k: v for k, v in doc.meta.items() if k in META_FIELDS and v},
        "preamble_en": doc.preamble_en,
        "units": [
            {
                "n": u.n,
                "source": derive_source(u.line_ids, index),
                "english": u.english,
                "refrain": u.n in refrains,
            }
            for u in doc.units
        ],
    }


def validate_source_language(lang: str | None) -> str:
    if lang not in SOURCE_LANGUAGES:
        raise SupplicationError(
            f"source_language must be one of {'|'.join(SOURCE_LANGUAGES)} (got {lang!r}). "
            f"It selects the script face and the translation prompt, and is never inferred."
        )
    return lang
