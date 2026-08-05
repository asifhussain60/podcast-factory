"""_autonomy.py — how far a started run drives before it stops for a human.

Split out of ``_rules.py`` rather than added to it: that module is at its
line-count ceiling, and autonomy is not a content rule. It is a policy about the
RUN, which is a different thing from a policy about the book — and keeping the
two apart is why this file can grow a level without touching the rules every
book's prose is judged against.

See ``phases/autonomy_gate`` for the gates themselves and why only some of them
are a run's to clear.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Autonomy level — how far a started run drives before it stops for a human.
#
# The pipeline's stops were never a single policy. Some exist because a human has
# to APPROVE something (the series plan), some because money is about to be spent
# (the audio-render gate), some because a human has to physically DO something
# (generate audio in NotebookLM and drop the files), and one because the next step
# is irreversible and audience-facing (publish). Collapsing them into one
# "interactive/autonomous" switch would either strand a run that only needed an
# approval, or drive one straight through the gate that makes a draft public.
#
# So the level names how far the run may go, and each stop declares which level
# clears it. Approvals and spend gates the level can clear are cleared and
# RECORDED in the decision ledger, never skipped silently. Two stops no level
# clears, for different reasons: the NotebookLM audio drop is physically
# impossible for the pipeline to perform, and publish is a Tier-2 action whose
# standing permission is the author's to grant in CLAUDE.md, not a config field's.
AUTONOMY_LEVELS: dict[str, dict[str, object]] = {
    "manual": {
        "label": "stop at every gate",
        "clears_series_plan": False,
        "clears_audio_render": False,
        "description": "Every halt waits for --resume. The behaviour before autonomy levels existed.",
    },
    "to_finalize": {
        "label": "drive to the finalize halt",
        "clears_series_plan": True,
        "clears_audio_render": False,
        "description": (
            "Auto-approves the series plan, records it in the decision ledger, and drives every "
            "phase it can reach. Deliberately does NOT clear the audio-render gate: that halt is "
            "not only a spend gate, it is the one place a human reads the book BEFORE irreversible "
            "ElevenLabs credits are spent on it, and an autonomous run that skipped it would be "
            "buying audio for a book nobody had read. Also stops at the NotebookLM audio drop, "
            "which no level can clear because the pipeline cannot perform it."
        ),
    },
}
DEFAULT_AUTONOMY: str = "manual"


def autonomy_level_for(declared: str | None = None) -> str:
    """Resolve a book's autonomy level. Unknown values fall back to manual.

    Falling back to the CAUTIOUS end is the whole point: a typo in one book's
    config must never be the reason a gate went unwatched. The opposite default
    would make a misspelling indistinguishable from consent.
    """
    return declared if declared in AUTONOMY_LEVELS else DEFAULT_AUTONOMY


def autonomy_clears(level: str, gate: str) -> bool:
    """True when ``level`` is allowed to clear ``gate`` on the author's behalf.

    ``gate`` is ``series_plan`` or ``spend_gates``. An unknown gate is never
    cleared — a stop added later is manual until someone decides otherwise here,
    which is the safe direction for a list that will grow.
    """
    spec = AUTONOMY_LEVELS.get(level) or AUTONOMY_LEVELS[DEFAULT_AUTONOMY]
    return bool(spec.get(f"clears_{gate}", False))
