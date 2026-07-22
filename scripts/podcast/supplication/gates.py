"""gates.py — the supplication lane's own integrity gate.

WHY THE LANE SHIPS ITS OWN GATE INSTEAD OF WIDENING A SHARED ONE
----------------------------------------------------------------
`arabic_integrity.py` gates on `bucket == "Islamic"`. A new bucket therefore
SILENTLY loses Arabic-integrity protection. The safe move is not to widen that
shared gate — every existing Islamic book depends on its current behaviour and
loosening its scope is exactly the kind of change that regresses them — but to
give this lane an equivalent guarantee of its own, scoped to its own documents.

WHAT THIS GATE PROVES
---------------------
G-SUP-1  digest      units.json is paired with the exact OCR record it was
                     segmented from (no silent re-OCR underneath it).
G-SUP-2  resolvable  every referenced line id exists in the record.
G-SUP-3  coverage    every OCR line is used EXACTLY once — nothing dropped,
                     nothing duplicated. This is what catches a model quietly
                     skipping a hard-to-read line.
G-SUP-4  order       units follow the record's reading order, and the lines
                     inside a unit are contiguous. A supplication is an ordered
                     recitation; reordering it is a correctness bug, not a
                     stylistic one.
G-SUP-5  verbatim    the derived source is byte-identical to the record's line
                     text. Independent of the derivation path in schema.py, so
                     it still fires if that path is ever compromised.
G-SUP-6  translated  every unit has non-empty English (render-readiness only —
                     skipped before the translate step via require_english=False).

Every failure is fatal and reported in full. Nothing here auto-repairs.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .schema import SourceRecord, SupplicationError, UnitsDoc, derive_source


@dataclass
class GateReport:
    passed: bool
    checks: dict[str, bool] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"{'PASS' if ok else 'FAIL'}  {name}" for name, ok in self.checks.items()]
        if self.failures:
            lines.append("")
            lines.extend(f"  - {f}" for f in self.failures)
        return "\n".join(lines)


# Cap on how many individual failures are listed per check, so a wholly
# mis-segmented document reports a readable diagnosis instead of thousands of
# lines. The count is always reported in full.
_MAX_LISTED = 8


def _trunc(items: list[str], label: str) -> list[str]:
    if len(items) <= _MAX_LISTED:
        return items
    return items[:_MAX_LISTED] + [f"… and {len(items) - _MAX_LISTED} more {label}"]


def verify(doc: UnitsDoc, record: SourceRecord, *, require_english: bool = True) -> GateReport:
    """Run every gate. Returns a report; never raises for content failures."""
    rep = GateReport(passed=True)
    failures: list[str] = []

    def check(name: str, ok: bool, msgs: list[str] | None = None) -> None:
        rep.checks[name] = ok
        if not ok:
            rep.passed = False
            failures.extend(msgs or [])

    # G-SUP-1 — digest pairing
    check(
        "G-SUP-1 digest",
        bool(doc.source_digest) and doc.source_digest == record.digest,
        [
            f"units.json source_digest {doc.source_digest[:12] or '(absent)'}… does not match the "
            f"OCR record digest {record.digest[:12]}… — units.json was segmented from a different "
            f"OCR run. Re-segment, or restore the matching record."
        ],
    )

    index = record.by_id()
    order = {ln.id: i for i, ln in enumerate(record.lines)}

    # G-SUP-2 — resolvable ids
    unknown = [i for u in doc.units for i in u.line_ids if i not in index]
    check("G-SUP-2 resolvable", not unknown, _trunc([f"unknown line id: {i}" for i in unknown], "unknown ids"))

    # G-SUP-3 — exact coverage
    used: dict[str, int] = {}
    for u in doc.units:
        for i in u.line_ids:
            used[i] = used.get(i, 0) + 1
    dropped = [ln.id for ln in record.lines if ln.id not in used]
    dupes = [i for i, c in used.items() if c > 1]
    check(
        "G-SUP-3 coverage",
        not dropped and not dupes,
        _trunc([f"OCR line never used: {i} ({index[i].text[:40]!r})" for i in dropped], "dropped lines")
        + _trunc([f"OCR line used {used[i]}×: {i}" for i in dupes], "duplicated lines"),
    )

    # G-SUP-4 — reading order (only meaningful once ids resolve)
    order_msgs: list[str] = []
    if not unknown:
        prev = -1
        for u in doc.units:
            idxs = [order[i] for i in u.line_ids]
            if idxs != list(range(idxs[0], idxs[0] + len(idxs))):
                order_msgs.append(f"unit {u.n}: line_ids are not contiguous in the source ({u.line_ids})")
            if idxs and idxs[0] <= prev:
                order_msgs.append(f"unit {u.n}: starts at or before the previous unit — reading order broken")
            if idxs:
                prev = idxs[-1]
    check("G-SUP-4 order", not order_msgs, _trunc(order_msgs, "ordering problems"))

    # G-SUP-5 — verbatim source
    verbatim_msgs: list[str] = []
    if not unknown:
        for u in doc.units:
            derived = derive_source(u.line_ids, index)
            expected = " ".join(index[i].text for i in u.line_ids)
            if derived != expected:
                verbatim_msgs.append(f"unit {u.n}: derived source differs from the OCR record text")
    check("G-SUP-5 verbatim", not verbatim_msgs, _trunc(verbatim_msgs, "verbatim failures"))

    # G-SUP-6 — translation completeness
    if require_english:
        untranslated = [u.n for u in doc.units if not (u.english or "").strip()]
        check(
            "G-SUP-6 translated",
            not untranslated,
            _trunc([f"unit {n}: english is empty" for n in untranslated], "untranslated units"),
        )

    rep.failures = failures
    return rep


def assert_ok(doc: UnitsDoc, record: SourceRecord, *, require_english: bool = True) -> GateReport:
    """verify(), but raise SupplicationError on failure. Use at step boundaries."""
    rep = verify(doc, record, require_english=require_english)
    if not rep.passed:
        raise SupplicationError("supplication integrity gate FAILED\n\n" + rep.summary())
    return rep
