"""The deterministic gates that run on a correction before any model does.

Split out of `_correction_packets` (DR-005: one module, one job). The gates are the cheap, certain
half of the workflow. They reuse what the repo already enforces on every other prose route
(`_vowelling`, `_mushaf`, `_book_voice_gates`, `_book_edits`) instead of restating any of it, so a
correction cannot get past a check a Composer edit would have failed. A gate failure is a verdict
with NO model call: a correction that cannot be resolved to one place cannot be reviewed by anyone.

A Qur'anic letter change is never sent to a model and never applied by a script -- it goes to a
person, because a "typo fix" on scripture is not a typo fix.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher

SPOKEN_RETENTION_FLOOR = 0.90


@dataclass
class Gate:
    id: str
    result: str  # ok | warn | no
    note: str = ""

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def _arabic_runs(text: str) -> list[str]:
    """Arabic-script runs in order, repeats kept. Only whitespace continues a run."""
    from _vowelling import ARABIC_RE

    cls = ARABIC_RE.pattern
    return [m.group(0).strip() for m in re.finditer(rf"(?:{cls})+(?:\s+(?:{cls})+)*", text or "")]


def has_arabic(text: str) -> bool:
    from _vowelling import ARABIC_RE

    return bool(ARABIC_RE.search(text or ""))


def _arabic_letters(text: str) -> str:
    """The Arabic-script content of `text` alone, joined with single spaces."""
    return " ".join(_arabic_runs(text))


def arabic_gate(quote: str, proposed: str, kind: str) -> Gate | None:
    """Is an Arabic change marks-only? None when the correction involves no Arabic.

    Applied whenever the quote carries Arabic script or the kind says `arabic`,
    because a moderator can put the wrong kind on a correction and the script is
    what has to be protected. Runs are compared pairwise and English words around
    them are free to change: only the script itself is guarded.
    """
    from _vowelling import rejection_reason

    q_runs, p_runs = _arabic_runs(quote), _arabic_runs(proposed)
    if not q_runs and not p_runs:
        if kind == "arabic":
            return Gate("arabic-marks-only", "warn", "kind is 'arabic' but neither text contains Arabic script")
        return None
    if not q_runs:
        return Gate(
            "arabic-marks-only",
            "warn",
            "the proposal introduces Arabic script the passage did not have; no gate can check it against the source",
        )
    if len(q_runs) != len(p_runs):
        return Gate("arabic-marks-only", "no", f"number of Arabic runs changed ({len(q_runs)} -> {len(p_runs)})")
    for old, new in zip(q_runs, p_runs):
        if old == new:
            continue
        reason = rejection_reason(old, new)
        if reason:
            return Gate("arabic-marks-only", "no", reason)
    return Gate("arabic-marks-only", "ok", "Arabic script changes only vowel marks")


def quran_gate(quote: str, proposed: str) -> Gate | None:
    """A change of LETTERS inside a mushaf-resolved run is never machine-handled.

    Letters, not marks: `_vowelling.skeleton` strips marks and nothing else, so an
    Uthmani respelling counts as a change here (it is a change -- to scripture).
    """
    from _mushaf import is_quranic_sequence
    from _vowelling import skeleton

    q_ar = _arabic_letters(quote)
    if not q_ar:
        return None
    if not is_quranic_sequence(q_ar) and not any(is_quranic_sequence(r) for r in _arabic_runs(quote)):
        return None
    if skeleton(q_ar) != skeleton(_arabic_letters(proposed)):
        return Gate(
            "quran-letters",
            "no",
            "the quote is Qur'anic text and the proposal changes its letters -- this needs a person, never a script or a model",
        )
    return Gate("quran-letters", "ok", "Qur'anic text; only marks (or nothing) change")


def is_quranic_quote(quote: str) -> bool:
    from _mushaf import is_quranic_sequence

    ar = _arabic_letters(quote)
    return bool(ar) and (is_quranic_sequence(ar) or any(is_quranic_sequence(r) for r in _arabic_runs(quote)))


def frame_gate(old_para: str, new_para: str, *, frame: str | None, narrator_subject: str) -> Gate:
    """Narrative-frame integrity on the paragraph, before vs after -- the same
    `revoice_gates` every prose-rewriting route must pass."""
    try:
        from _book_voice_gates import revoice_gates

        findings = revoice_gates(
            old_para, new_para, check_opening=False, frame=frame or None, narrator_subject=narrator_subject or ""
        )
    except Exception as exc:  # a gate that cannot run must say so, not pass silently
        return Gate("narrative-frame", "warn", f"gate could not run: {exc}")
    if findings:
        return Gate("narrative-frame", "no", "; ".join(findings[:3]))
    return Gate("narrative-frame", "ok", "grammatical person, speech tags, script retention and enumerations intact")


def word_retention(old: str, new: str) -> float:
    """Share of `old`'s words that survive in `new`, paragraph by paragraph.

    A correction substitutes text inside a paragraph and never adds or removes a
    paragraph break, so pairing paragraphs by position and diffing each pair is
    exact and cheap. If the counts differ (a caller passed unrelated texts) it
    falls back to one diff over the whole word stream.
    """
    old_paras = re.split(r"\n\s*\n", old.strip())
    new_paras = re.split(r"\n\s*\n", new.strip())
    total = sum(len(p.split()) for p in old_paras)
    if total == 0:
        return 1.0
    if len(old_paras) != len(new_paras):
        a, b = old.split(), new.split()
        matched = sum(bl.size for bl in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
        return matched / max(len(a), 1)
    kept = 0
    for o, n in zip(old_paras, new_paras):
        if o == n:
            kept += len(o.split())
            continue
        a, b = o.split(), n.split()
        kept += sum(bl.size for bl in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    return kept / total


def retention_gate(old_body: str, new_body: str) -> Gate:
    r = word_retention(old_body, new_body)
    if r < SPOKEN_RETENTION_FLOOR:
        return Gate(
            "word-retention",
            "no",
            f"only {r:.0%} of the chapter's words survive; a spoken book must keep at least {SPOKEN_RETENTION_FLOOR:.0%}",
        )
    return Gate("word-retention", "ok", f"{r:.0%} of the chapter's words survive")


def substitution_gates(
    *,
    old_para: str,
    new_para: str,
    quote: str,
    proposed: str,
    kind: str,
    frame: str | None,
    narrator_subject: str,
) -> list[Gate]:
    """The gates that depend only on the change itself -- shared verbatim by the
    packet builder and by `pull_corrections`, so a correction passes or fails the
    same way at review time and at apply time."""
    gates: list[Gate] = []
    q = quran_gate(quote, proposed)
    if q:
        gates.append(q)
    a = arabic_gate(quote, proposed, kind)
    if a:
        gates.append(a)
    gates.append(frame_gate(old_para, new_para, frame=frame, narrator_subject=narrator_subject))
    return gates


def verdict_from_gates(gates: list[Gate]) -> str | None:
    """The verdict the gates decide on their own, or None ("ask the AI").

    `quran-letters` outranks everything: it is `needs_human`, not `reject`,
    because the moderator may be right and only a person can say so.
    """
    if any(g.id == "quran-letters" and g.result == "no" for g in gates):
        return "needs_human"
    if any(g.result == "no" for g in gates):
        return "reject"
    return None


def gate_summary(gates: list[Gate], verdict: str) -> str:
    failing = [g for g in gates if g.result == "no"]
    if verdict == "needs_human":
        return (
            "This changes the letters of a Qur'anic passage, so it was not sent to the AI reviewer. "
            "A person has to decide."
        )
    detail = " ".join(f"{g.note.rstrip('.')}." for g in failing[:2])
    return f"Rejected by an automatic check before review. {detail}".strip()
