"""intelligence/_anti_cliche.py — Denial lists for the augmenter and challenger.

These lists are the machine-readable half of the authoring doctrine that
forbids clichéd, self-help, and contextually inappropriate language from
appearing in podcast scripts. The challenger imports them directly; the
augmenter uses them as a prior-treatment filter.

LISTS

    CAPSTONE_DENY
        Phrases that must never appear in capstone episodes (the final
        summary episode in any archetype). They flatten a scholarly
        synthesis into motivational-poster territory.

    SELF_HELP_DENY
        Phrases that turn a scholarly Arabic source into self-help content.
        The audience is intellectually engaged; they do not need coaching.

    TIER_2_DENY
        Phrases that are acceptable in Tier-1 (general-audience) episodes
        but forbidden in Tier-2 (scholarly-register) episodes, because
        they signal casual approximation rather than scholarly precision.

    AUGMENTER_PRIOR_TREATMENT_DENY
        Phrases the augmenter must not use when generating contextual
        enrichment paragraphs. They introduce irrelevant biographical
        background, pseudo-academic hedging, or patronising explanation.

All entries are lowercase; matching is case-insensitive. Entries may
contain spaces (phrase-level matches). The challenger uses ``in`` membership
after calling ``.lower()`` on the target text; partial phrase matching is
intentional (e.g. "life lessons" catches "practical life lessons").
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# CAPSTONE_DENY
# Blocks phrases that deflate the final-episode synthesis into platitude.
# ---------------------------------------------------------------------------

CAPSTONE_DENY: frozenset[str] = frozenset({
    "key takeaways",
    "takeaway",
    "in summary",
    "to summarise",
    "to summarize",
    "wrapping up",
    "wrap up",
    "final thoughts",
    "closing thoughts",
    "lessons learned",
    "lessons we can draw",
    "what we've learned",
    "what we have learned",
    "the big picture",
    "bottom line",
    "at the end of the day",
    "the moral of the story",
    "in conclusion",
    "to conclude",
    "so to speak",
})

# ---------------------------------------------------------------------------
# SELF_HELP_DENY
# Blocks phrases that reframe a classical Islamic source as self-improvement.
# ---------------------------------------------------------------------------

SELF_HELP_DENY: frozenset[str] = frozenset({
    "applicable to our lives",
    "apply this today",
    "apply to your life",
    "relevant to modern life",
    "relevant to our lives",
    "practical wisdom",
    "practical advice",
    "actionable",
    "empowers us",
    "empowers you",
    "take charge",
    "unlock your potential",
    "personal growth",
    "self-improvement",
    "life hack",
    "life lesson",
    "life lessons",
    "mindfulness",
    "wellbeing journey",
    "journey of self",
    "better version of yourself",
    "best self",
    "thrive",
    "flourish",
    "achieve your goals",
    "growth mindset",
    "positive mindset",
    "manifest",
    "manifestation",
    "abundance mindset",
})

# ---------------------------------------------------------------------------
# TIER_2_DENY
# Blocks casual approximation in scholarly-register (Tier-2) episodes.
# ---------------------------------------------------------------------------

TIER_2_DENY: frozenset[str] = frozenset({
    "basically",
    "essentially",
    "kind of",
    "sort of",
    "a bit like",
    "you know",
    "right?",
    "so yeah",
    "i guess",
    "i suppose",
    "honestly",
    "literally",
    "actually",    # only denied in Tier-2; conversational register is fine in Tier-1
    "obviously",
    "clearly",     # overused; replace with a cited claim
    "needless to say",
    "goes without saying",
    "it's worth noting",
    "it's interesting to note",
    "interestingly",
    "fascinatingly",
    "amazingly",
    "incredibly",
    "it's fascinating",
    "believe it or not",
})

# ---------------------------------------------------------------------------
# AUGMENTER_PRIOR_TREATMENT_DENY
# Blocks phrases the augmenter must never use in enrichment paragraphs.
# ---------------------------------------------------------------------------

AUGMENTER_PRIOR_TREATMENT_DENY: frozenset[str] = frozenset({
    "born in",
    "died in",
    "was born",
    "who was born",
    "his early life",
    "her early life",
    "grew up in",
    "studied under",          # biographical; enrichment must be doctrinal, not biographical
    "is widely regarded as",
    "is considered one of",
    "it is important to note",
    "it should be noted",
    "it is worth mentioning",
    "as mentioned earlier",
    "as noted above",
    "as discussed previously",
    "the reader should be aware",
    "the listener should know",
    "for context",
    "for background",
    "by way of background",
    "historically speaking",
    "from a historical perspective",
    "scholars debate",         # vague hedge — cite specific scholars or omit
    "scholars argue",
    "some scholars believe",
    "many scholars think",
    "there is debate about",
    "it is disputed",
    "this is a complex topic",
    "this is a nuanced topic",
    "nuanced",                # almost always a hedge; replace with a specific claim
    "complex",                # same
})
