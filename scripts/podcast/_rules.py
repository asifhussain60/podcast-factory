from __future__ import annotations

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
# rigor, §6 interfaith) lives in prompts/gemini-bundle-auditor.md so both
# auditors see it. See F30 / scholarly-rubric integration trail on develop.
CHALLENGER_VERSION = "2.2"

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
ALLOWED_CATEGORIES = ("books", "articles", "documents", "lectures", "interviews", "letters", "asbaaq")

# ─── Learning substrate root (relative to repo root). Used by all four
# learning scripts (aggregate, propose, test, health writer) and by the
# challenger agent's report-writer to locate findings.jsonl + health/.
LEARNING_DIR = "content/podcast/.skill/_learning"

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

    The ledger lives at `<repo_root>/content/podcast/.skill/_learning/
    findings.jsonl` and is append-only. Callers MUST NOT emit duplicates
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
