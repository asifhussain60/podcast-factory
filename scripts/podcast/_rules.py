from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

"""Canonical rule data shared across the podcast scripts.

This file IS the source of truth for the rule lists. An earlier version of
this docstring named `content/podcast/.skill/handbook/notebooklm-customize-
prompt-rules.md` as the normative human-readable counterpart; that handbook
tree was removed in the 2026-05-23 restructure and has not been restored.
Until it is, this file (plus content/_shared/islam/*.yml for doctrinal data)
holds the contract for both humans and code. See infra/claude-agents/
podcast-challenger.md Section 0 for the current authority list.

Consumers:
  - scripts/podcast/build_episode_txt.py — uses ABBREVIATIONS_MAP + HONORIFICS to
    enforce R-NO-ABBREVIATION and R-HONORIFIC-ONCE as hard gates on chapter +
    framing content at build time.
  - scripts/podcast/audit_transcript.py — uses all six lists for post-hoc
    transcript scans against the actual NotebookLM audio output.
  - scripts/podcast/learn_aggregate.py / learn_propose.py / test_challenger.py
    read CHALLENGER_VERSION + LEARNING_DIR to locate the substrate.
  - .github/agents/podcast-challenger.agent.md stamps CHALLENGER_VERSION into
    every challenger-report.md.

Each consumer transforms the raw data into its own preferred shape (regex dict
vs. substring list); the canonical data itself is plain Python literals.
"""

# ─── Challenger self-version (stamped into every challenger-report.md and every
# findings.jsonl record). Single source of truth — agent reads from here so
# the spec frontmatter version, the report header version, and the ledger
# `source_version` field never drift.
#
# 2.1 (2026-05-24): added R-HOST-ROLE-PARITY as a P0 — Host A (male voice) is
# always scholar/teacher; Host B (female voice) is always seeker/student/
# debater. Roles never rotate across episodes within a single book. Also
# added R-EPISODE-FORMAT-RECOMMENDED P1 — every chapter-contract must declare
# `episode_format: deep_dive | debate` with a one-paragraph rationale.
#
# 2.2 (2026-05-25): scholarly-conversation rubric landed — adds four new
# deterministic rules (R-NO-AI-CLICHE, R-NO-FAUX-PROFUNDITY-OPENING,
# R-NO-PREMATURE-CLOSURE, R-NO-DEEP-DIVE-SELF-REFERENCE) plus the
# tradition-conditional R-NO-ESSENTIALISM-EXTERNAL (active only when
# series-config.yaml.source_tradition != the episode's subject tradition).
# The LLM-grade rubric extension (§3 religious literacy, §4 philosophical
# rigor, §6 interfaith) lives in _workspace/prompts/gemini-bundle-auditor.md so both
# auditors see it. See F30 / scholarly-rubric integration trail on develop.
# 2.5 (2026-06-10): chapter-density + citation + sermon wave — adds
# R-MAX-CONCEPTS (≤3 concept H2 sections per episode, frame headings
# excluded; deterministic gate in Phase 0d post-write + preflight),
# R-QURAN-CITATION-FORMAT (canonical plain-English `(chapter N, verse M)`
# form; terse `(Q N:M)` / `(Quran N:M)` / bare `(N:M)` flagged),
# R-NO-TRANSLIT-FORMULA (no `*Arabic translit* — *translation*` formula
# pairs in chapter prose; English translation only), and
# R-SERMON-VERBATIM (sermon/khutba passages render whole as their own
# concept section, contract carries `sermon:` block, framing carries a
# `## Verbatim Recitation` instruction). Chapter-set checks CS7–CS10
# (coverage, overlap/dedup, sermon integrity, set density) land in
# check_chapter_set.py. Standard: docs/standards/chapter-density.md.
# 2.6 (2026-06-24): promotes Arabic-in-chapters from display-layer preference
# to P0 rule for islamic_scholarly books. R-ARABIC-IN-CHAPTERS requires every
# Islamic chapter source to persist glossary-backed Arabic script while keeping
# phonetic respelling in the glossary / Customize prompt only.
CHALLENGER_VERSION = "2.6"

R_MAX_CONCEPTS: str = "R-MAX-CONCEPTS"
R_QURAN_CITATION_FORMAT: str = "R-QURAN-CITATION-FORMAT"
R_NO_TRANSLIT_FORMULA: str = "R-NO-TRANSLIT-FORMULA"
R_SERMON_VERBATIM: str = "R-SERMON-VERBATIM"
R_ARABIC_IN_CHAPTERS: str = "R-ARABIC-IN-CHAPTERS"

# ─── Upstream precheck sources (Wave N — adversarial validation, Phase A–C) ──
# These are the `source` values written into _learning/findings.jsonl by the
# shift-left deterministic + LLM discriminator pre-checks in
# scripts/podcast/_authoring/_artifact_convergence.py.  Distinct from the
# per-chapter challenger (source="podcast-challenger") — upstream checks fire
# at generation time (Phase 0b/0e), before any chapter is drafted.
#
# Registered here so learn_aggregate.py + learn_propose.py can route proposals
# to the correct human-resolution targets (generator prompt edits in
# _authoring/_refine.py / _authoring/_enrichment.py).
UPSTREAM_PRECHECK_SOURCES: frozenset[str] = frozenset({
    "precheck-0b",   # refined-english.md — deterministic + Phase-B LLM fidelity
    "precheck-0e",   # per-chapter enrichment — deterministic + Phase-C LLM faithfulness
})

# Upstream check IDs and their human-resolution targets (the same mapping as
# CHECK_ID_TO_TARGET in learn_propose.py; duplicated here for runtime look-up
# without importing learn_propose.py from pipeline scripts).
UPSTREAM_CHECK_ID_TO_TARGET: dict[str, str] = {
    # Phase A — deterministic
    "U0B-EMPTY":              "author: re-run Phase 0b; the refinement produced empty output",
    "U0B-LENGTH-DRIFT":       "author: review _authoring/_refine.py window prompts — length-ratio constraint",
    "U0B-STRUCTURE-COLLAPSE": "author: review _authoring/_refine.py window prompts — paragraph-preservation rule",
    "U0E-SHRANK":             "author: review _authoring/_enrichment.py prompt — DO NOT drop source content",
    "U0E-BALLOON":            "author: review _authoring/_enrichment.py prompt — cap total word growth",
    # Phase B — LLM fidelity (0b)
    "U0B-MEANING-DRIFT":        "author: review 0b window prompt — strengthen DO NOT change meaning instruction",
    "U0B-DROPPED-TEACHING":     "author: review 0b window prompt — preserve ALL teachings, examples, and illustrations",
    "U0B-HALLUCINATED-ADDITION": "HUMAN REVIEW REQUIRED — fabricated content in refined-english.md (P0)",
    "U0B-REGISTER-SHIFT":       "author: review 0b window prompt — preserve scholarly register",
    # Phase C — LLM faithfulness (0e)
    "U0E-HALLUCINATED-CITATION": "HUMAN REVIEW REQUIRED — fabricated citation in enriched chapter (P0)",
    "U0E-SOURCE-ALTERED":        "author: review 0e enrichment prompt — DO NOT alter source text, only enrich",
    "U0E-DOCTRINE-DRIFT":        "author: review 0e enrichment prompt — tradition-coherence guard",
}

# ─── Category W (Wave L) — augmentation-quality checks. Guards that knowledge
# augmentation enriches genuine gaps naturally (never forced), respects the book's
# content level, draws only real atoms, weaves etymology in spoken form (≤3/chapter,
# never spelling Arabic letters), and never repeats an atom across chapters.
# Implemented deterministically in _augmentation.py (W3–W6 mechanical; W1–W2 light
# heuristic + agent judgment). Severities:
#   W1 forced/no-gap augmentation     P1  (auto-revert the block)
#   W2 unnatural / bolted-on phrasing P1  (auto-revert the block)
#   W3 etymology cap/spoken-form      P1
#   W4 doctrine atom above book level P0  (wrong-level leak — hard block)
#   W5 fabricated atom (not in DB)    P0  (integrity — hard block)
#   W6 atom repeated across chapters  P1
R_AUGMENT_ETYMOLOGY_MAX_PER_CHAPTER = 3
# Arabic Unicode ranges that must NEVER appear in an etymology spoken-form aside.
R_AUGMENT_ARABIC_RANGES = (
    (0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF), (0xFE70, 0xFEFF),
)
# Block-header substrings the challenger scans for in augmented episode text.
R_AUGMENT_BLOCK_HEADERS = {
    "doctrine": "[PRIOR DOCTRINAL CONTEXT",
    "term": "[TERM GLOSSARY",
    "quote": "[ATTRIBUTED SAYINGS",
    "etymology": "[ETYMOLOGY",
}

# ─── R-ARABIC-INTEGRITY (P0 2026-06-16) — Arabic spans (Quran verses, hadith,
# named terms) are BYTE-STABLE across every LLM pass. The pipeline snapshots a
# content-addressed (NFC-normalized) fingerprint of every Arabic span BEFORE the
# first LLM mutation (0a-synthesize), then re-verifies after 0a/0b/0e. The ONLY
# sanctioned mutators are (1) canonical injection by restore_arabic.py
# (quran_ayat_lookup + verified atoms) and (2) human glossary schema-v2 curation
# (pronunciation_compiler.resolve_curation, surfaced by the Astro phonetic-view).
# Any other change — a silent LLM mutation, drop, or invention — FAILS the phase.
# Implemented in scripts/podcast/arabic_integrity.py; composed as blocking finalize
# gate G13 for islamic_scholarly books.
R_ARABIC_INTEGRITY: str = "R-ARABIC-INTEGRITY"
ARABIC_FINGERPRINT_VERSION: str = "1.0"
# Bidi/joiner control codepoints stripped before hashing so a pass that only
# re-inserts directional marks is not flagged as a mutation (RTL-ligature stability).
R_ARABIC_BIDI_STRIP: tuple[int, ...] = (
    0x200C, 0x200D, 0x200E, 0x200F,
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
    0x2066, 0x2067, 0x2068, 0x2069,
)
# Combining tashkeel (harakat) ranges used to derive the vowel-stripped skeleton.
# A near-match that differs ONLY in this range is classified AI-VOWEL-DRIFT.
R_ARABIC_TASHKEEL: tuple[tuple[int, int], ...] = (
    (0x064B, 0x0652), (0x0653, 0x065F), (0x0670, 0x0670),
)

# ─── R-HOST-ROLE-PARITY (P0 2026-05-24) — host roles are locked book-wide.
# Host A is always the scholar/teacher. Host B is always the seeker/student/
# debater. The role assignments do not rotate, swap, or blur across episodes.
# Detection: scan framing.host_a.role and framing.host_b.role against the
# canonical role pools below. Any framing where the assignments disagree with
# the pools — or where roles swap between episodes of the same book — is a
# P0 finding (code: HOST-ROLE-PARITY).
HOST_A_ROLES_SCHOLAR = (
    "scholar", "teacher", "master", "alim", "aalim", "shaykh", "sheikh",
    "guide", "expert", "mentor", "professor",
)
HOST_B_ROLES_SEEKER = (
    "seeker", "student", "debater", "questioner", "novice", "disciple",
    "ghulam", "ghulaam", "apprentice", "interlocutor", "challenger",
)
# Voice → gender pairing (single source of truth; cross-references the
# NotebookLM Audio Overview default English voices). When the
# `notebooklm_voices` audit reads which voice spoke which line, this map
# gates the alignment check.
HOST_VOICE_GENDER = {"host_a": "male", "host_b": "female"}

# ─── R-EPISODE-FORMAT-RECOMMENDED (P1 2026-05-24) — every chapter-contract
# declares `episode_format` plus a one-paragraph rationale. For debate-mode
# contracts, the `debate` block is fully populated (proposition + host_a/
# host_b positions + source_moves + resolution). The challenger refuses (P1)
# any contract where the format is missing or `debate` blocks are partial.
#
# F32 (2026-05-25): extended from the original two-valued enum (deep_dive,
# debate) to seven values. The new values (walkthrough, monologue, interview,
# recap, narrative) are needed for non-book categories per _branching.py
# (letters, articles, lectures, interviews). Phase 0d author picks per
# chapter from this list; downstream framing-author + R-HOST-ROLE-PARITY
# rules need parallel extensions (deferred — current rules assume
# deep_dive/debate). When a chapter declares a not-yet-wired format,
# build_episode_txt.py emits a P1 warning "format X not yet fully wired
# downstream; expect best-effort author behavior" rather than blocking.
EPISODE_FORMAT_ALLOWED = (
    "deep_dive",      # one position unfolded layer-by-layer (most book chapters)
    "debate",         # two named voices in extended back-and-forth (concession arcs OK)
    "walkthrough",    # step-by-step exposition (articles, technical chapters)
    "monologue",      # single-host explanatory; secondary host as ambient interlocutor
    "interview",      # Q&A structured (rare in primary sources; common in lecture-of-X)
    "recap",          # mid-book summary episode (every Nth chapter for long books)
    "narrative",      # pure historical/biographical exposition, no doctrinal dispute
)

# F32 (2026-05-25): map of which formats are currently fully wired downstream.
# Formats outside this set still validate at contract-write time but emit a
# P1 warning at build time noting they may exhibit best-effort author behavior.
EPISODE_FORMAT_FULLY_WIRED = ("deep_dive", "debate")

# ─── Slide Deck Challenger self-version (stamped into every slide-challenger-report.md
# and every findings.jsonl record with source="slide-deck-challenger"). Independent
# of the audio CHALLENGER_VERSION above so the two challengers can evolve separately.
SLIDE_DECK_CHALLENGER_VERSION = "1.0"

# ─── Canonical book-category enum. Single source of truth — previously duplicated
# (with inconsistent type: tuple vs set vs list) across orchestrate_book.py,
# scaffold_book.py, ingest_source.py, audit_page_markers.py per AU-X1-001 in
# audit report 2026-05-23-204940. Consumers now `from _rules import ALLOWED_CATEGORIES`.
# Tuple chosen for immutability + argparse `choices=` compatibility.
ALLOWED_CATEGORIES = ("books", "articles", "documents", "lectures", "interviews", "letters", "asbaaq", "sites", "explainers")
# `explainers` — professional / consumer explainer content: employee onboarding, product docs,
# system walkthroughs, consumer guides. `sites` continues to work for existing content;
# `explainers` is the preferred category for new content of this type.

# Categories that skip the phonetic pass (0c) and the doctrinal enrichment pass (0e).
# Consumer/explainer content has no Arabic transliteration requirements and no
# tradition-specific doctrinal context to inject.
CONSUMER_CATEGORIES: frozenset[str] = frozenset({"sites", "explainers"})

# ─── Content-profile system (Wave CP) — declares how a book moves through the pipeline.
# Every book declares `content_profile` in its series-config.yaml; missing field defaults
# to `islamic_scholarly` so all existing books are unaffected. Profiles drive:
#   - assertion gating in build_episode_txt.py (Arabic checks skipped for non-Islamic)
#   - phase 0c phonetics (no-op for non-islamic_scholarly, already handled via CONSUMER_CATEGORIES)
#   - challenger rule selection (only islamic_scholarly gets Arabic name/citation checks)
# ─── Content-type registry (2026-06-04, Wave: content/ type-first layout) ──────
# SINGLE SOURCE OF TRUTH for what a content type is: its canonical profile key
# (stored as `content_profile` in series-config.yaml), the top-level `bucket`
# folder it lives under (content/<bucket>/<slug>/), which pipeline phases it
# skips, and its literary (revoice) voice defaults. Adding a content type = one
# entry here. Two ORTHOGONAL axes used to be conflated:
#   • the legacy `category` (books/lectures/sites/…) — still used for the optional
#     book-vs-lecture metadata tag, and retained in ALLOWED_CATEGORIES for intake.
#   • the content TYPE / profile — what actually drives routing + voice + bucket.
# This registry is the profile axis. _paths.py maps profile→bucket via bucket_for_profile().
@dataclass(frozen=True)
class ContentType:
    profile: str          # canonical content_profile key (series-config.yaml)
    bucket: str           # top-level folder under content/ (type-first layout)
    skip_phonetics: bool  # skip Phase 0c (Arabic phonetic pass)
    skip_enrichment: bool # skip Phase 0e (doctrinal enrichment)
    skip_ocr: bool        # skip Phase 0a Azure OCR (source already digital English/text)
    literary_voice: dict  # revoice defaults consumed by _literary.py
    # Default audio engine for a NEW book of this profile, stamped into
    # series-config.yaml at intake (intake_launch._write_series_config). NEW-book
    # default ONLY — never applied retroactively, so existing books with no
    # `audio_engine` field keep the notebooklm default and never move off the
    # path their already-rendered audio came from.
    audio_engine: str = "notebooklm"
    # Default ElevenLabs cast (host key -> voice-library name) stamped at intake
    # when the chosen engine is elevenlabs and the operator picked no voices.
    default_voice_cast: dict = field(default_factory=dict)


CONTENT_TYPE_REGISTRY: dict[str, "ContentType"] = {
    "islamic_scholarly": ContentType(
        profile="islamic_scholarly", bucket="Islamic",
        skip_phonetics=False, skip_enrichment=False, skip_ocr=False,
        literary_voice={
            "narrator_voice": "author_first_person",
            "narrator_subject": "the author",
            "addressee": "the reader",
            "scene_source": "text_only",
        },
        # All Islamic books use NotebookLM (Google conversational AI — approved
        # fingerprint from the-master-and-the-disciple, confirmed 2026-06-13).
        # ElevenLabs scripted dialogue was tried for Vol 1 and rejected.
        audio_engine="notebooklm",
        default_voice_cast={"host_a": "Eric", "host_b": "Lily"},
    ),
    "technical": ContentType(
        profile="technical", bucket="Technical",
        skip_phonetics=True, skip_enrichment=True, skip_ocr=True,
        literary_voice={
            "narrator_voice": "peer_expert",
            "narrator_subject": "a senior practitioner",
            "addressee": "a fellow developer",
            "scene_source": "text_only",
        },
    ),
    "fiction": ContentType(
        profile="fiction", bucket="Fiction",
        skip_phonetics=True, skip_enrichment=True, skip_ocr=False,
        literary_voice={
            "narrator_voice": "narrative_voice",
            "narrator_subject": "the narrator",
            "addressee": "the reader",
            "scene_source": "text_only",
        },
    ),
    "consumer_explainer": ContentType(
        profile="consumer_explainer", bucket="Guides",
        skip_phonetics=True, skip_enrichment=True, skip_ocr=True,
        literary_voice={
            "narrator_voice": "contemporary_narrator",
            "narrator_subject": "a guide",
            "addressee": "you",
            "scene_source": "text_only",
        },
    ),
    "general_nonfiction": ContentType(
        profile="general_nonfiction", bucket="Guides",
        skip_phonetics=True, skip_enrichment=False, skip_ocr=False,
        literary_voice={
            "narrator_voice": "scholarly_essayist",
            "narrator_subject": "the author",
            "addressee": "the reader",
            "scene_source": "text_only",
        },
    ),
}

# Ordered top-level bucket folders under content/ (type-first layout, 2026-06-04).
BUCKETS: tuple[str, ...] = ("Islamic", "Technical", "Fiction", "Guides")

# CONTENT_PROFILES is now DERIVED from the registry (was a hand-maintained tuple
# of 3; technical + fiction are now first-class). Order: registry insertion order.
CONTENT_PROFILES: tuple[str, ...] = tuple(CONTENT_TYPE_REGISTRY)
ISLAMIC_SCHOLARLY_PROFILE = "islamic_scholarly"


def bucket_for_profile(profile: str | None) -> str:
    """Map a content_profile to its top-level bucket folder. Defaults to Islamic.

    The bucket is the type-first folder (content/<bucket>/<slug>/). Unknown or
    absent profiles fall back to Islamic — the historical default that keeps every
    pre-existing book on the full scholarly pipeline.
    """
    ct = CONTENT_TYPE_REGISTRY.get(profile or "")
    return ct.bucket if ct else "Islamic"


def literary_voice_for_profile(profile: str | None) -> dict:
    """Revoice voice defaults for a profile (used by _literary.py). Islamic fallback."""
    ct = CONTENT_TYPE_REGISTRY.get(profile or "") or CONTENT_TYPE_REGISTRY[ISLAMIC_SCHOLARLY_PROFILE]
    return dict(ct.literary_voice)


def phase_capabilities(profile: str | None) -> "ContentType":
    """Return the ContentType (phase-skip capabilities) for a content_profile.

    SINGLE accessor for every phase-skip decision (0a OCR, 0c phonetics, 0e
    enrichment). Reads the CONTENT_TYPE_REGISTRY (single source of truth); unknown
    or absent profiles fall back to islamic_scholarly — the historical default that
    runs the full scholarly pipeline. Mirrors the bucket_for_profile pattern so
    routing logic lives in ONE place instead of scattered `category in {...}` checks.
    """
    return CONTENT_TYPE_REGISTRY.get(profile or "") or CONTENT_TYPE_REGISTRY[ISLAMIC_SCHOLARLY_PROFILE]


def audio_engine_default_for_profile(profile: str | None) -> str:
    """Default audio engine to stamp for a NEW book of this profile.

    NEW-book default only (consumed by intake_launch). Unknown/absent profiles
    fall back to islamic_scholarly's default. This never touches existing books.
    """
    ct = CONTENT_TYPE_REGISTRY.get(profile or "") or CONTENT_TYPE_REGISTRY[ISLAMIC_SCHOLARLY_PROFILE]
    return ct.audio_engine


def default_voice_cast_for_profile(profile: str | None) -> dict:
    """Default ElevenLabs cast (host key -> library name) for a NEW book."""
    ct = CONTENT_TYPE_REGISTRY.get(profile or "") or CONTENT_TYPE_REGISTRY[ISLAMIC_SCHOLARLY_PROFILE]
    return dict(ct.default_voice_cast)

# ─── Content-level ladder (Wave M) — ISLAMIC scholarly books only. Single source
# of truth for category-gated augmentation. A book declaring `content_level` in
# meta.yml draws doctrine atoms ONLY at or below its own level (cumulative
# downward), never above. Mirrors the Kashkole Lookup_levels spiritual hierarchy
# from most accessible (general) to most metaphysical (haqaiq).
#
# `universal` sits OUTSIDE the ladder — always eligible at every level. It is the
# permanent value for Quran/Hadith/Term/Etymology atoms (universal resources,
# never level-gated) and the eligible-everywhere marker for doctrine atoms.
# NULL (absent) = non-Islamic book OR uncategorized atom: no gate applied.
#
# CONTENT_LEVEL_LADDER is ordered low→high; index = rank. allowed_content_levels()
# returns {levels 0..rank(book_level)} for the cumulative-downward query clause.
CONTENT_LEVEL_LADDER: tuple[str, ...] = (
    "general",      # narrative / historical accounts
    "advanced",     # advanced scholarly; legal analysis; formal exoteric commentary
    "taveel",       # ta'wil: allegorical / esoteric interpretation (batin)
    "mamsool",      # parables / exemplars: teaching the esoteric through analogy
    "mabda_maad",   # origin-and-return: cosmological doctrine, cosmic intellects
    "haqaiq",       # essential realities: eternal metaphysical truths (deepest)
)
CONTENT_LEVELS: frozenset[str] = frozenset(CONTENT_LEVEL_LADDER) | {"universal"}


def allowed_content_levels(book_level: str | None) -> list[str]:
    """Return the doctrine-atom content levels a book at *book_level* may draw from.

    Cumulative downward: a book at rank N is eligible for every ladder level at
    or below N, plus 'universal'. Returns an empty list when *book_level* is None
    or unrecognized (caller then applies NO content-level gate — the non-Islamic /
    uncategorized path, preserving pre-Wave-L behavior).

    Examples:
        allowed_content_levels('taveel')    -> ['general','advanced','taveel','universal']
        allowed_content_levels('haqaiq')    -> ['general','advanced','taveel','mamsool','mabda_maad','haqaiq','universal']
        allowed_content_levels('general')   -> ['general','universal']
        allowed_content_levels(None)        -> []
    """
    if not book_level or book_level not in CONTENT_LEVEL_LADDER:
        return []
    rank = CONTENT_LEVEL_LADDER.index(book_level)
    return list(CONTENT_LEVEL_LADDER[: rank + 1]) + ["universal"]

# ─── Learning substrate root (relative to repo root). Used by all four
# learning scripts (aggregate, propose, test, health writer) and by the
# challenger agent's report-writer to locate findings.jsonl + health/.
LEARNING_DIR = "_learning"

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

# ─── R-NO-AI-CLICHE (P0 2026-05-25, v2.2 scholarly-rubric §1)
# Banned phrases that fingerprint unsupervised LLM "podcast voice." These
# are substrings to scan in chapter prose AND framing.md. Severity P0 in
# 99-show-notes.md and framing.md; downgraded to P1 if found only in
# operator-facing scaffolding files (00-source-index.md, etc.) where the
# audience is human and the term is being discussed, not voiced.
AI_CLICHE_DENY = [
    "deep dive", "deep-dive",
    "let's dive in", "let's dive into",
    "today's episode", "today we'll explore", "today, we'll explore",
    "today we'll discuss", "today, we'll discuss",
    "in this episode", "in this conversation",
    "join us as we", "buckle up",
    "without further ado", "let's get started",
    "fasten your seatbelts",
    "journey through", "journey into",
    "fascinating world of", "fascinating world",
    "mind blown", "mind-blown", "blew my mind",
    "what a journey", "what a ride",
]

# ─── R-NO-FAUX-PROFUNDITY-OPENING (P0 2026-05-25, v2.2 scholarly-rubric §1)
# Banned opening shapes — rhetorical questions that gesture at meaning without
# committing to a thesis. Applied to the FIRST 200 characters of framing.md
# `## Opening` section and to the first paragraph of any chapter file.
FAUX_PROFUNDITY_OPENING_PATTERNS = [
    r"can we find meaning",
    r"what (?:does it (?:truly )?mean|it truly means) to be human",
    r"what does this (truly )?say about",
    r"is there meaning (in|to)",
    r"in a world where",
    r"in an (?:age|era)\b",
    r"have you ever (?:wondered|stopped to)",
    r"imagine (?:a world|for a moment)",
    r"picture this[:.]",
]

# ─── R-NO-PREMATURE-CLOSURE (P1 2026-05-25, v2.2 scholarly-rubric §5)
# Banned closing shapes that pretend hard questions got resolved. Scanned in
# the LAST 600 characters of framing.md `## Closing` section and in beat
# landings of 04-discussion-spine.md. Permitted closing: "we didn't settle
# this — here's where the live disagreement sits".
PREMATURE_CLOSURE_PATTERNS = [
    r"and that(?:,\s*ultimately,\s*is\s+|(?:'s| is)(?:,| )?\s*ultimately(?:,)?\s*)what",
    r"what (?:the soul|the self|truth|reality|god|allah|the divine) (?:really|truly) is",
    r"the (?:answer|key) (?:turns out to be|is|lies in)",
    r"so (?:in the end|ultimately|at last),?\s*we (?:see|find|understand)",
    r"and that(?:'s| is) (?:the|how) (?:the )?(?:whole )?(?:story|point|truth)",
]

# ─── R-NO-DEEP-DIVE-SELF-REFERENCE (P0 2026-05-25, v2.2 scholarly-rubric §1)
# Forbid the conversation describing itself as a "deep dive", "journey", or
# "exploration" — get into the material instead. Stricter sibling of
# R-NO-AI-CLICHE that targets only self-referential framings.
DEEP_DIVE_SELF_REFERENCE_PATTERNS = [
    r"(?:our|this|today's) (?:deep dive|journey|exploration|conversation)",
    r"we(?:'re| are) (?:going to|gonna) (?:dive|explore|unpack|dig)",
    r"let(?:'s| us) (?:dive|explore|unpack|dig) into",
    r"we(?:'ll| will) (?:dive|explore|unpack|dig) into",
]

# ─── R-NO-ESSENTIALISM-EXTERNAL (P0 2026-05-25, v2.2 scholarly-rubric §3)
# Blanket-tradition claims ("Muslims believe X", "Hindus think Y", "Buddhists
# hold Z") are FORBIDDEN when the episode discusses a tradition that is NOT
# the book's own source_tradition. They are PERMITTED (with internal
# qualification) when the episode is internal to one tradition.
# Detection: scan chapter prose + framing.md for these stem patterns. The
# series-config.yaml.source_tradition gates whether to flag — internal episodes
# get a P2 nudge to qualify ("classical Twelver Shia tradition emphasizes..."),
# external episodes get P0.
ESSENTIALISM_STEM_PATTERNS = [
    r"\bMuslims (?:believe|think|hold|teach|say)\b",
    r"\bHindus (?:believe|think|hold|teach|say)\b",
    r"\bBuddhists (?:believe|think|hold|teach|say)\b",
    r"\bChristians (?:believe|think|hold|teach|say)\b",
    r"\bJews (?:believe|think|hold|teach|say)\b",
    r"\bSikhs (?:believe|think|hold|teach|say)\b",
    r"\b(?:In|For) (?:Islam|Hinduism|Buddhism|Christianity|Judaism|Sikhism),\s+",
    r"\bthe (?:Islamic|Hindu|Buddhist|Christian|Jewish|Sikh) (?:view|position|teaching|tradition) (?:is|holds|states)\b",
    r"\b(?:real|true) (?:Muslims|Hindus|Buddhists|Christians|Jews|Sikhs) (?:would|don't|do not|never)\b",  # No-True-Scotsman
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


def emit_finding(
    *,
    repo_root: Path,
    source: str,
    source_version: str,
    book: str,
    episode: str = "",
    chapter: str = "",
    check_id: str,
    severity: str,
    signature: str,
    file: str = "",
    line: int | None = None,
    context_excerpt: str = "",
    resolution: str = "flagged",
    bypassed_gate: str = "",
) -> None:
    """Append one JSONL record to the learning-substrate findings ledger.

    Multi-book concurrency safety (added 2026-05-25 per F31 forward-looking
    audit): wraps the append in an fcntl LOCK_EX critical section. On macOS
    + Linux, single-line writes under PIPE_BUF (4 KiB) are atomic at the
    syscall level, BUT our line_out can exceed PIPE_BUF when context_excerpt
    is near its 300-char cap with multi-byte UTF-8. Without the lock,
    concurrent N-book orchestrators emitting findings at the same instant
    could interleave bytes within a single record. The lock costs ~1 ms per
    emit, negligible vs the LLM-call latencies that produced the finding.

    The ledger lives at `<repo_root>/_learning/findings.jsonl` and is append-only. Callers MUST NOT emit duplicates
    within a single run.
    """
    import fcntl as _fcntl
    import json as _json
    from datetime import datetime, timezone

    ledger = repo_root / LEARNING_DIR / "findings.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": source,
        "source_version": source_version,
        "book": book,
        "episode": episode,
        "chapter": chapter,
        "check_id": check_id,
        "severity": severity,
        "signature": signature,
        "file": file,
        "line": line,
        "context_excerpt": context_excerpt[:300],
        "resolution": resolution,
        # F33 (2026-05-25): post-publish findings that should have been caught
        # earlier in the pipeline carry the gate name they bypassed (e.g.
        # "G3-sequential-numbering", "Tier-2.5-build-validator"). Empty for
        # in-pipeline findings. The trainer computes per-gate false-negative
        # rate by grouping findings on this field.
        "bypassed_gate": bypassed_gate,
    }
    line_out = _json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    with ledger.open("a", encoding="utf-8") as f:
        _fcntl.flock(f.fileno(), _fcntl.LOCK_EX)
        try:
            f.write(line_out)
            f.flush()
        finally:
            _fcntl.flock(f.fileno(), _fcntl.LOCK_UN)


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


# ─── Wave I — Noise routing constants ────────────────────────────────────
# Protected categories: paragraphs matching these are NEVER offered to either
# noise-routing pass. They are exempt from deletion candidates entirely.
R_NOISE_PROTECTED_CATEGORIES: frozenset[str] = frozenset({
    "esoteric", "reality", "quran", "hadith", "poetry", "sharia",
    "ta_wil", "haqaiq", "daqaiq",
})

# Structural noise patterns for Pass 1 (zero-cost rule pre-pass).
# Each tuple: (compiled pattern, reason label).
import re as _re
R_NOISE_RULE_PATTERNS: list[tuple] = [
    (_re.compile(r"^(In the name of|Bismillah|As-salamu|Assalamu)", _re.I),     "greeting-opener"),
    (_re.compile(r"where (this|the) (chapter|session|lecture) (picks up|continues)", _re.I), "editorial-pickup"),
    (_re.compile(r"^(Dear (brothers|sisters)|Dear (brothers and sisters))", _re.I), "lecture-greeting"),
    (_re.compile(r"^(Thank you|Thanks be to (God|Allah)|We thank)", _re.I),     "boilerplate-thanks"),
    (_re.compile(r"(as we (discussed|mentioned|covered) (in the )?(previous|last))", _re.I), "recap-reference"),
    (_re.compile(r"^(To (recap|summarise|summarize)|To put it another way)", _re.I), "redundant-recap"),
    (_re.compile(r"\[Narrator.*?preamble\]|\[Editorial.*?note\]", _re.I),       "editorial-preamble"),
]

# ─── Wave N — Authorial-apparatus noise (the noise-auditor taxonomy) ──────
# A class of noise the Wave-I routing above NEVER targets: clean *authorial*
# prose that is non-teaching meta-content about the BOOK ITSELF — how it was
# recorded, authorized, transmitted, and may be circulated. The denoise/refine
# prompts (full_book_denoise.py, gemini_refine.py) only strip OCR artefacts,
# translator footnotes, and editor brackets; authorial apparatus passes every
# one of those filters because it is the author's own clean sentences. It then
# fans out into chapters/*.txt, episodes/*.txt, slide-decks/*.txt, and book.md.
# Source incident: al-Anwaar al-Lateefah vol-01 — the recorder's distribution
# warning ("do not email… do not store on your computer… punishment of cold
# iron") + ijazat/treasury chain-of-custody leaked into all four surfaces and
# built an entire EP01 out of front-matter. The `noise-auditor` agent flags
# this class with NZ-* finding IDs; the denoise prompts strip it at root.
R_NOISE_AUTHORIAL_APPARATUS: str = "R-NOISE-AUTHORIAL-APPARATUS"

# Sub-categories (NZ finding IDs map to these). Each is BOOK-PRODUCTION /
# CIRCULATION meta — NOT doctrine. The hard line: anything about how the book
# came to be recorded/transmitted/distributed is apparatus; anything the book
# TEACHES is content.
R_NOISE_APPARATUS_CATEGORIES: dict[str, str] = {
    "NZ-CIRCULATION":  "Distribution / copyright / circulation notice — do-not-email, "
                       "do-not-store-on-computer, do-not-share-online, copy-is-a-sin, and "
                       "the punishment-for-careless-circulation threat (e.g. 'cold iron').",
    "NZ-PROVENANCE":   "Provenance / chain-of-custody apparatus — ijazat/permission to RECORD, "
                       "deposit in a treasury/archive, 'recorded first for my family', the "
                       "two-fold authority-of-transmission of THIS recording.",
    "NZ-COLOPHON":     "Colophon / production meta — who transcribed/compiled/printed it, edition "
                       "and publisher notes, dedication-of-the-edition, scan/upload provenance.",
    "NZ-EDITORIAL":    "Editorial framing about the artifact rather than its subject — 'in this "
                       "lesson we will…', 'as recorded above', recording-session housekeeping.",
    "NZ-REFERENCE-TAIL": "Bibliographic tails attached to wisdom/saying blockquotes in chapter prose — "
                         "e.g. 'in Nahj al-Balagha (compiled by al-Sharif al-Radi), Hikam "
                         "(Saying) 147' or translator/source edition details. Keep the quoted "
                         "teaching and speaker; strip the reference scaffolding from chapters.",
}

# PROTECT-LIST — doctrine that LOOKS like apparatus but IS the teaching and must
# NEVER be stripped under Wave-N. In this tradition the epistemics of inherited,
# guarded knowledge and especially the DOCTRINE OF ALLEGIANCE to the Imams /
# Friends of Allah (wilayah) are core content, not provenance. The test: does the
# passage make a claim about REALITY/God/the soul/the path (keep), or only about
# the book-object's recording and circulation (strip)?
R_NOISE_APPARATUS_PROTECT: frozenset[str] = frozenset({
    "wilayah", "allegiance", "imam", "friends_of_allah", "awliya",
    "esoteric", "reality", "haqaiq", "tawhid", "soul_return", "doctrine",
})

# Heuristic Pass-1 anchors for the apparatus class (semantic judgment still
# belongs to the noise-auditor LLM / the denoise prompt; these are signals).
R_NOISE_APPARATUS_PATTERNS: list[tuple] = [
    (_re.compile(r"do not (e-?mail|share|circulate|store|upload|exchange)", _re.I), "NZ-CIRCULATION"),
    (_re.compile(r"(on|over|upon) the (internet|web)|on your computer", _re.I),     "NZ-CIRCULATION"),
    (_re.compile(r"(punishment|azab) of cold iron|to copy .* is a sin",  _re.I),    "NZ-CIRCULATION"),
    (_re.compile(r"(ghair-?mustahiqq|undeserving|indiscriminate circulation)", _re.I), "NZ-CIRCULATION"),
    (_re.compile(r"\b(ijazat|permission)\b.*\b(record|recording|set (it )?down)", _re.I), "NZ-PROVENANCE"),
    (_re.compile(r"deposited? in the treasury|treasury of the (sacred mission|Da'wat)", _re.I), "NZ-PROVENANCE"),
    (_re.compile(r"recorded (them )?(first )?for (my|his) (father|family)", _re.I),  "NZ-PROVENANCE"),
    (_re.compile(r"(transcribed|compiled|printed|scanned|typeset) by|this edition", _re.I), "NZ-COLOPHON"),
    (_re.compile(r"\b(?:in\s+)?\*?Nahj al-Balagha\*?\s*(?:\(compiled by al-Sharif al-Radi\))?,\s*(?:Hikam\s*)?\(?(?:Sermon|Saying|Letter)\)?\s*\d+", _re.I), "NZ-REFERENCE-TAIL"),
    (_re.compile(r"\b\*?(?:Nahj al-Balagha|Ghurar al-Hikam(?: wa Durar al-Kalim)?)\*?\s*(?:\(compiled by [^)]+\))?,\s*(?:Sermon|Saying|Letter|Hikam|Maxim|among the maxims)\b", _re.I), "NZ-REFERENCE-TAIL"),
]

# Version stamped into every noise-auditor report; bump on taxonomy change.
NOISE_AUDITOR_VERSION = "1.1"

# Chapter-prose reference-tail cleanup. The quote and speaker are content; the
# bibliography after the speaker is chapter noise. This intentionally targets
# wisdom/saying blockquotes, not Quranic or hadith references whose verse/book
# numbers are needed for source clarity.
R_NOISE_REFERENCE_TAIL_RES: tuple[_re.Pattern[str], ...] = (
    _re.compile(
        r"(?P<speaker>—\s*[^.\n]{1,140}?)(?:,\s*(?:in\s+)?)"
        r"\*?(?:Nahj al-Balagha|Ghurar al-Hikam(?: wa Durar al-Kalim)?)\*?\s*"
        r"(?:\(compiled by [^)]+\))?,\s*"
        r"(?:(?:Hikam\s*)?\(?(?:Sermon|Saying|Letter|Maxim)\)?\s*\d+"
        r"(?:\s*\([^)]+\))?|among the maxims on [^.]+)"
        r"(?:,\s*trans\.\s*[^.]+)?"
        r"(?:,\s*\*?Peak of Eloquence\*?)?\.",
        _re.I,
    ),
)


def strip_noise_reference_attributions(text: str) -> tuple[str, int]:
    """Strip bibliographic source tails from chapter prose, preserving speaker.

    Example:
      quote — Ali ibn Abi Talib, the Father of Imams, in *Nahj al-Balagha*
      (compiled by al-Sharif al-Radi), Hikam (Saying) 147.

    becomes:
      quote — Ali ibn Abi Talib, the Father of Imams.
    """
    count = 0

    def _replace(match: _re.Match[str]) -> str:
        nonlocal count
        count += 1
        return match.group("speaker").rstrip(" ,") + "."

    out_lines: list[str] = []
    for line in text.splitlines():
        if line.lstrip().startswith(">"):
            for pattern in R_NOISE_REFERENCE_TAIL_RES:
                line = pattern.sub(_replace, line)
        out_lines.append(line)

    trailing_newline = "\n" if text.endswith("\n") else ""
    return "\n".join(out_lines) + trailing_newline, count

# Ready-to-inject denoise directive — appended to the denoise system prompts
# (gemini_refine.DENOISE_SYS, full_book_denoise.build_system_prompts) so the apparatus
# class is stripped at the ROOT, book-agnostically, before it can fan out. The
# PROTECT brake is stated inline so doctrine (wilayah/allegiance/epistemics) is
# never cut. Book-agnostic: names no book — keys off content type, not title.
R_NOISE_APPARATUS_DIRECTIVE: str = (
    "AUTHORIAL-APPARATUS STRIP (R-NOISE-AUTHORIAL-APPARATUS, mandatory): in addition to "
    "OCR/translator/editor apparatus, REMOVE the author's own NON-TEACHING meta-content about "
    "the book-object itself — (a) CIRCULATION/COPYRIGHT notices: do-not-email / do-not-share / "
    "do-not-store-online, 'to copy this is a sin', threats of punishment for careless circulation "
    "(e.g. 'cold iron'), 'not for indiscriminate circulation', the 'undeserving'/ghair-mustahiqqeen "
    "framing; (b) PROVENANCE / chain-of-custody: permission/ijazat to RECORD or transmit THIS "
    "recording, 'I recorded it first for my family', deposit in a treasury/archive, the 'twofold "
    "authority' of this recording; (c) COLOPHON: who transcribed/compiled/printed/scanned it, "
    "edition and publisher notes; (d) REFERENCE TAILS in chapter prose: bibliographic scaffolding "
    "after a quoted saying, such as 'in Nahj al-Balagha (compiled by al-Sharif al-Radi), Hikam "
    "(Saying) 147' or translator/source-edition details. Keep the quoted teaching and the speaker; "
    "strip the reference tail from the chapter. PROTECT (NEVER strip — this is TEACHING, not apparatus): any "
    "claim about reality/God/the soul/the path/the law, the doctrine of allegiance to the Imams / "
    "Friends of Allah (wilayah), and the epistemic claim that the knowledge is INHERITED from the "
    "prophets and saints. The test: a passage about how the book was recorded/authorized/circulated "
    "is apparatus (strip); a passage about what the book TEACHES is content (keep)."
)

# ─── Wave B — Intelligence layer budget constants ─────────────────────────
# These are read by intelligence/extractor.py and intelligence/augmenter.py.
# Max per-chapter cost for the atom extractor (Claude Sonnet structured call).
R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD_PER_CHAPTER: float = 0.10
# Max per-book total cost for the atom extractor.
R_KNOWLEDGE_EXTRACTOR_COST_CAP_USD_PER_BOOK: float = 10.00
# Confidence threshold below which an extracted atom goes to manual review.
R_KNOWLEDGE_EXTRACTOR_CONFIDENCE_THRESHOLD: float = 0.70
# Whether augmentation is enabled by default (must be explicitly turned on per book).
R_KNOWLEDGE_AUGMENTER_DEFAULT_ENABLED: bool = False

# ─── SN-7 — Terminus-technicus preservation (Slice 2-fix / K6-pre) ─────────
# A terminus technicus (precise doctrinal term: tawil, zuhd, farḍ ʿayn, …) is preserved in
# PHONETIC form on every occurrence, with a brief English gloss permitted on first use only;
# it is NEVER reduced to an English paraphrase. Orthogonal to R-PHONETICS-OUT: Arabic SCRIPT is
# still stripped (TTS can't read it); the phonetic form carries the term. Enforced in the
# denoise+normalize Gemini prompts (gemini_refine.sn7_guard, protect-list from per-book
# glossary.yml) and audited by podcast-challenger Category D check D6. Standard: house-voice.md §2b.
R_TERMINUS_PRESERVE: bool = True

# ─── Slice 5c — HOST_ROLE_CONTRACT (host dynamics guardrail) ─────────────────
# The framing prompt injects this block verbatim to lock host dynamics for the
# book. Three tiers: teacher/student (default), teacher/questioner (active probe),
# scholar/debater (K1 Debater carve-out — Host B holds and defends a position).
# Source: editorial.ts card `host_roles`; the framing builder reads the card
# value and inserts HOST_ROLE_CONTRACT[preset] into the framing's Host dynamic
# section. Challenger Category Q validates compliance (Q1–Q5).
HOST_ROLE_CONTRACT: dict = {
    "teacher_student": (
        "HOST ROLES (locked book-wide — R-HOST-ROLE-PARITY): "
        "Host A (male voice) is the SCHOLAR / TEACHER — explains, contextualises, illuminates. "
        "Host B (female voice) is the STUDENT / SEEKER — receives, asks, reflects. "
        "Host B never lectures or corrects Host A. Roles do not rotate across episodes."
    ),
    "teacher_questioner": (
        "HOST ROLES (locked book-wide — R-HOST-ROLE-PARITY): "
        "Host A (male voice) is the SCHOLAR / TEACHER — explains, contextualises, illuminates. "
        "Host B (female voice) is the QUESTIONER — actively probes, presses for clarity, "
        "surfaces tension in the argument. Host B may push back but does not hold an independent "
        "position. Roles do not rotate across episodes."
    ),
    "scholar_debater": (
        "HOST ROLES (locked book-wide — R-HOST-ROLE-PARITY): "
        "Host A (male voice) is the SCHOLAR — defends the text's position with evidence. "
        "Host B (female voice) is the DEBATER — holds and defends a contrary or sceptical "
        "position drawn from the source. This is DEBATE format (K1 Debater carve-out): "
        "Host B's position is source-grounded, not invented; she concedes only when Host A "
        "produces a stronger textual argument. Roles do not rotate across episodes."
    ),
}
# Default when no editorial card is set for this book.
HOST_ROLE_CONTRACT_DEFAULT = "teacher_student"

# ─── K6 — Interest axis (5th PEQ axis, weight 0.15) ─────────────────────────
# Curiosity-building, challenge-defeat arcs, modern relevance, and fair framing
# of opposing views. Deterministic signal detection (pattern matching); no live
# API calls. Audited by podcast-challenger Category V (V1–V5).
R_INTEREST_WEIGHT: float = 0.15   # Interest axis weight in PEQ formula

# Phrases that signal a curiosity-building opening hook.
R_INTEREST_HOOK_PATTERNS: list = [
    r"what (does|would|if|happens|kind of|makes|drives|compels)",
    r"why (does|would|did|should|is|are|do|must)",
    r"how (does|can|should|is|are|do|did)",
    r"imagine (if|a world|that|for a moment)",
    r"consider (this|the|what|a|that)",
    r"the question (is|was|becomes|facing|at the heart)",
    r"here'?s (the|a|what|why|how|something)",
    r"(let'?s|let us) (begin|start|open|ask|explore|consider)",
]

# Challenge-defeat arc: problem-raising phrases (first half of the arc).
R_INTEREST_CHALLENGE_RAISE_PATTERNS: list = [
    r"\b(objection|challenge|difficulty|problem|paradox|tension|puzzle|obstacle)\b",
    r"\b(one might (argue|say|object|think|wonder))\b",
    r"\b(it (might|may|could) seem)\b",
    r"\b(but (how|why|what|is this|does this|can))\b",
]

# Challenge-defeat arc: resolution phrases (second half of the arc).
R_INTEREST_CHALLENGE_RESOLVE_PATTERNS: list = [
    r"\b(the answer (is|lies|comes|emerges))\b",
    r"\b(in fact|actually|rather|instead|on the contrary)\b",
    r"\b(resolves?|dissolves?|overcomes?|addresses?|answers? (this|that|the))\b",
]

# Combined list for callers that only need presence of any challenge pattern.
R_INTEREST_CHALLENGE_PATTERNS: list = (
    R_INTEREST_CHALLENGE_RAISE_PATTERNS + R_INTEREST_CHALLENGE_RESOLVE_PATTERNS
)

# Phrases that signal modern relevance (connecting doctrine to contemporary life).
R_INTEREST_RELEVANCE_PATTERNS: list = [
    r"\b(today|modern|contemporary|our (time|age|era|world|lives?))\b",
    r"\b(we (find|see|live|face|encounter|grapple))\b",
    r"\b(still (holds?|rings? true|matters?|applies?|speaks?))\b",
    r"\b(resonates?|relevant|speaks? to|timeless)\b",
    r"\b(in (our|this|any|every) (age|era|time|generation|society|context))\b",
]

# Strawman markers — phrases suggesting the opposing view was oversimplified.
# Uses precise anchored patterns to avoid false positives (e.g. "obviously right").
R_INTEREST_STRAWMAN_DENY: list = [
    r"\bobviously (wrong|false|absurd|incorrect|mistaken)\b",
    r"\bclearly (wrong|mistaken|misguided)\b",
    r"\babsurdly\b",
    r"\b(silly (argument|idea|notion|objection))\b",
    r"\b(no (sane|reasonable|serious) person)\b",
]

# ─── Technical content challenger rules (category: explainers) ───────────────
# Single source of truth for challenger rules specific to technical developer
# content (explainers category). These parallel the Islamic challenger rules but
# enforce technical accuracy rather than doctrinal fidelity.
# NOTE: CHALLENGER_VERSION bump required when these are actively consumed by
# the challenger scoring path (currently declared, not yet wired).

# Code blocks must reproduce source exactly — no paraphrasing of code.
R_TECH_CODE_VERBATIM: str = "R-TECH-CODE-VERBATIM"

# CLI commands must match the source document exactly (no shorthand variants).
# Wrong: `npm i -g claude`  Correct: `npm install -g @anthropic-ai/claude-code`
R_TECH_CLI_EXACT: str = "R-TECH-CLI-EXACT"

# Version numbers must be literal — no "the latest version" or "approximately".
R_TECH_VERSION_LITERAL: str = "R-TECH-VERSION-LITERAL"

# Acronyms must be expanded on first use within each episode.
# Wrong: "Use MCP"  Correct: "Use MCP (Model Context Protocol)"
R_TECH_ACRONYM_FIRST_USE: str = "R-TECH-ACRONYM-FIRST-USE"

# No Islamic/doctrinal terminology in technical episodes (leakage detection).
R_TECH_NO_DOCTRINAL: str = "R-TECH-NO-DOCTRINAL"

# ≥4 consecutive explanatory sentences with no CLI command, code block, or
# "type/see/run" pattern — theory density is too high for an explainer.
R_TECH_THEORY_CAP: str = "R-TECH-THEORY-CAP"

# H2 section with ≥2 named features but zero hands-on sequence (CLI / diff /
# session-step) — explainers must anchor every concept in a concrete action.
R_TECH_WALKTHROUGH_PRESENT: str = "R-TECH-WALKTHROUGH-PRESENT"

# Passage explaining internal mechanics, release history, pricing tiers, or
# benchmark stats of a tool that is NOT the subject of the chapter.
R_TECH_NO_COMP_INTERNALS: str = "R-TECH-NO-COMP-INTERNALS"

# Chapter addresses a migration audience but has zero "old habit → new habit"
# mapping. P2 (advisory) — does not block shipping.
R_TECH_HABIT_MAP: str = "R-TECH-HABIT-MAP"

# Canonical rule set for the technical challenger.
TECHNICAL_RULE_SET: frozenset = frozenset({
    R_TECH_CODE_VERBATIM,
    R_TECH_CLI_EXACT,
    R_TECH_VERSION_LITERAL,
    R_TECH_ACRONYM_FIRST_USE,
    R_TECH_NO_DOCTRINAL,
    R_TECH_THEORY_CAP,
    R_TECH_WALKTHROUGH_PRESENT,
    R_TECH_NO_COMP_INTERNALS,
    R_TECH_HABIT_MAP,
})
