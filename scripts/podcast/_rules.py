"""Canonical rule data shared across the podcast scripts.

These lists are mirrored from `content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md`
(the NORMATIVE contract). When a rule changes, edit BOTH this file and the handbook
normative copy together. The handbook is the source of truth for humans; this file
is the source of truth for code.

Consumers:
  - scripts/podcast/build_episode_txt.py — uses ABBREVIATIONS_MAP + HONORIFICS to
    enforce R-NO-ABBREVIATION and R-HONORIFIC-ONCE as hard gates on chapter +
    framing content at build time.
  - scripts/podcast/audit_transcript.py — uses all six lists for post-hoc
    transcript scans against the actual NotebookLM audio output.

Each consumer transforms the raw data into its own preferred shape (regex dict
vs. substring list); the canonical data itself is plain Python literals.
"""

# ─── R-NO-MODERNIZE (chapter + framing must not pull in 21st-century social-media idioms)
# Substring scans — phrase as-it-would-appear in transcript text.
MODERNIZE_DENY = [
    "Twitter", "twitter", "X.com", " X ", "social media",
    "algorithm", "algorithmic", "content creator", "internet troll",
    "reply guy", "YouTube comment", "youtube comment", "TikTok", "tiktok",
    "Instagram", "instagram", "livestream", "screen time", "notification",
    "attention economy", "21st century", "quote-tweet", "quote tweet",
    "quote tweeting", "hashtag", "follower count", "doomscroll",
    "hot take", "cognitive behavioral therapy",
    "productivity framework", "life hack", "self-help", "wellness",
    "mindfulness app", "dopamine hit", "deep dive",
    "in our modern world", "modern digital lives", "platforms like",
]

# ─── R-NOSURPRISE (NotebookLM hosts must not perform shock/awe reactions)
SURPRISE_DENY = [
    "wow", "Wow",
    "that's so interesting", "that is so interesting",
    "it's chilling", "It's chilling",
    "it's devastating", "It's devastating",
    "it's terrifying", "It's terrifying",
    "it's profound", "It's profound",
    "it's fascinating", "It's fascinating",
    "it's amazing", "It's amazing",
    "oh my god", "Oh my god",
    " right? ", " right?\n", "Right?",
    " exactly", "Exactly",
    "no way", "No way",
]

# ─── R-WELCOME (chapter opening must not begin with a cold "today we'll discuss" frame)
WELCOME_COLD = [
    "today we'll discuss", "today we will discuss",
    "in this episode", "in our final deep dive",
    "Welcome to our", "Welcome to today", "Welcome back",
]

# ─── R-NO-ABBREVIATION
# Canonical structure: full title → list of forbidden short forms that should be
# replaced. The audit script flattens to substring scans; the build script wraps
# each in word-boundary regex (with two negative-lookahead exceptions for
# "the Ihya" / "the Nahj" so it doesn't false-positive on the full title itself).
ABBREVIATIONS_MAP = {
    "Ihya Ulum al-Din":              ["the Ihya", "EI", "IUD"],
    "Nahj al-Balagha":               ["the Nahj", "NJB"],
    "Sahih Bukhari and Sahih Muslim": ["Sahihayn"],
}

# ─── R-HONORIFIC-ONCE
# Honorific phrase forms — each is one allowed-once-per-figure-per-chapter form.
# Stored as regex pattern strings so consumers can compile with their own flags
# (the build script uses IGNORECASE; audit treats them as case-sensitive regex).
HONORIFICS = [
    r"\(peace and blessings be upon him\)",
    r"\(peace be upon him\)",
    r"\(peace be upon them\)",
    r"\(peace be upon her\)",
    r"\(may Allah be pleased with him\)",
    r"\(may Allah be pleased with her\)",
    r"\(PBUH\)",
    r"\(SAW\)",
    r"\(AS\)",
    r"\(RA\)",
    "peace and blessings of Allah be upon him",
    "peace and blessings be upon him",
    "peace be upon him",
    "ﷺ",
]

# ─── Filler-interjection scrub (host TTS prosody artifacts)
FILLER_INTERJECTIONS = [
    " yeah ", " Yeah ", " yeah, ", " Yeah,",
    " right, ", " Right, ", " right. ", " Right. ",
    " exactly, ", " Exactly, ",
]


# ───────────────────────────────────────────────────────────────────────────────
# Derivation helpers — keep transformations next to the canonical data so they
# can be reviewed together when the rules change.
# ───────────────────────────────────────────────────────────────────────────────


def abbreviations_for_audit() -> list[tuple[str, str]]:
    """Audit shape: (substring, full_title). Substring is what to scan for via
    str.count. Returned in dictionary-iteration order, deterministic across runs."""
    out: list[tuple[str, str]] = []
    for full, abbrevs in ABBREVIATIONS_MAP.items():
        for a in abbrevs:
            if a == "EI":
                # Audit historically scanned ' EI ' and ' EI.' separately to
                # avoid matching mid-word. Preserve that behavior.
                out.append((" EI ", full))
                out.append((" EI.", full))
            else:
                out.append((a, full))
    return out


def abbreviations_for_build() -> dict[str, str]:
    """Build shape: regex_pattern → user-facing message. The build script
    enforces these as hard gates with re.search.

    Two patterns get negative-lookahead because they're prefixes of the full
    title: 'the Ihya' must not match 'the Ihya Ulum al-Din'; same for 'the Nahj'.
    """
    out: dict[str, str] = {}
    for full, abbrevs in ABBREVIATIONS_MAP.items():
        for a in abbrevs:
            if a == "the Ihya":
                pat = r"\bthe Ihya\b(?! Ulum)"
            elif a == "the Nahj":
                pat = r"\bthe Nahj\b(?! al-Balagha)"
            else:
                pat = rf"\b{a}\b"
            out[pat] = f"{a} (use full title '{full}')"
    return out
