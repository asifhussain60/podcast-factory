# F27 — Tier 2.5 validator drafts (paste-in source)

**Status**: drafts only. Do NOT paste into `scripts/podcast/build_episode_txt.py` while orchestrator is mid-flight on KaR (would FAIL the 4 chapters shipping under v3 doctrine).

**When to land**: after orchestrator quiesce on KaR (all 4 chapters shipped or halted) AND before any new book's Phase 0g run.

**Pattern**: each validator follows the existing `assert_*` shape from Tier 2 (assert_framing_has_name_discipline_section, assert_framing_dramatic_arc_structure, etc.). Soft-flag mode via `_flag_p1()` for non-blocking; hard-raise for doctrine violations.

---

## Validator #1 — `assert_no_arabic_transliteration_in_chapter`

**Catches**: F20 + F29 leaks. Arabic person-names, book-titles, surah-names, concept-words in chapter prose.

```python
ARABIC_PHONETIC_PATTERNS = [
    # Common Arabic prefixes/suffixes (case-insensitive)
    r"\bal-[A-Za-z]+",          # al-Kirmani, al-Sijistani, al-Shams, al-Ahzab
    r"\babu\s+[A-Za-z]+",       # Abu Hatim, Abu Ya'qub
    r"\bibn\s+[A-Za-z]+",       # Ibn Mas'ud
    r"\bbint\s+[A-Za-z]+",      # bint X
    r"[a-z]'[a-z]",             # apostrophe in middle (al-Mu'izz, Da'i, ma'lul, Ta'wil)
    r"\b[A-Za-z]+iyy[ah]\b",    # -iyyah suffix (al-Sajjadiyya, taqiyyah)
    r"\b[A-Za-z]+aani\b",       # -ani suffix (al-Kirmaani)
    r"\b[A-Za-z]+oosh\b",       # -ush/-oosh suffix
]

ALLOWED_ARABIC_ORIGIN = {
    "quran", "imam", "medina", "ismaili", "fatimid", "fatimi",
    "yusuf ali",  # translator credit
    "muhammad",   # the Prophet's name (acceptable per stable label)
}

KNOWN_SURAH_NAMES = {
    "al-fatiha", "al-baqarah", "al-imran", "al-nisa", "al-maidah",
    "al-anam", "al-araf", "al-anfal", "al-tawbah", "yunus", "hud",
    "yusuf", "al-rad", "ibrahim", "al-hijr", "al-nahl", "al-isra",
    "al-kahf", "maryam", "ta-ha", "al-anbiya", "al-hajj", "al-muminun",
    "al-nur", "al-furqan", "al-shuara", "al-naml", "al-qasas",
    "al-ankabut", "al-rum", "luqman", "al-sajdah", "al-ahzab", "saba",
    "fatir", "ya-sin", "al-saffat", "sad", "al-zumar", "ghafir",
    "fussilat", "al-shura", "al-zukhruf", "al-dukhan", "al-jathiyah",
    "al-ahqaf", "muhammad", "al-fath", "al-hujurat", "qaf",
    "al-dhariyat", "al-tur", "al-najm", "al-qamar", "al-rahman",
    "al-waqiah", "al-hadid", "al-mujadilah", "al-hashr", "al-mumtahanah",
    "al-saff", "al-jumuah", "al-munafiqun", "al-taghabun", "al-talaq",
    "al-tahrim", "al-mulk", "al-qalam", "al-haqqah", "al-maarij",
    "nuh", "al-jinn", "al-muzzammil", "al-muddaththir", "al-qiyamah",
    "al-insan", "al-mursalat", "al-naba", "al-naziat", "abasa",
    "al-takwir", "al-infitar", "al-mutaffifin", "al-inshiqaq",
    "al-buruj", "al-tariq", "al-ala", "al-ghashiyah", "al-fajr",
    "al-balad", "al-shams", "al-layl", "al-duha", "al-sharh",
    "al-tin", "al-alaq", "al-qadr", "al-bayyinah", "al-zalzalah",
    "al-adiyat", "al-qariah", "al-takathur", "al-asr", "al-humazah",
    "al-fil", "quraysh", "al-maun", "al-kawthar", "al-kafirun",
    "al-nasr", "al-masad", "al-ikhlas", "al-falaq", "al-nas",
}

def assert_no_arabic_transliteration_in_chapter(chapter_text: str, chapter_slug: str) -> None:
    """Block any Arabic transliteration in chapter prose.

    Catches F20 + F29: person-names, book-titles, surah-names, concept-words.
    """
    import re
    text_lower = chapter_text.lower()
    violations = []

    # Pattern-based detection
    for pattern in ARABIC_PHONETIC_PATTERNS:
        matches = re.findall(pattern, chapter_text, re.IGNORECASE)
        for match in matches:
            normalized = match.lower().strip()
            if normalized in ALLOWED_ARABIC_ORIGIN:
                continue
            if any(allowed in normalized for allowed in ALLOWED_ARABIC_ORIGIN):
                continue
            violations.append(f"pattern={pattern!r} match={match!r}")

    # Surah-name detection
    for surah in KNOWN_SURAH_NAMES:
        if surah in text_lower:
            # Allow when wrapped as "the chapter Qaf" etc. but flag for review
            violations.append(f"surah_name={surah!r}")

    if violations:
        _raise(
            f"R-NO-ARABIC-TRANSLITERATION in chapter {chapter_slug}: "
            f"{len(violations)} violations. Sample: {violations[:5]}"
        )
```

**Edge cases:**
- "Medina" (allowed geographic name) — must whitelist
- "Imam" (allowed loanword) — must whitelist via `ALLOWED_ARABIC_ORIGIN`
- "Quran" (allowed) — whitelisted
- "Muhammad" (the Prophet's name) — allowed
- "Ismaili" / "Fatimid" / "Fatimi" — allowed

**Test fixtures:**
- v4-revised chapter.txt should FAIL on al-Ahzab, al-Shams, Qaf (we know this from audit)
- v4-revised chapter.txt should PASS once F29 chapter rewrite lands

---

## Validator #2 — `assert_no_arabic_transliteration_in_framing`

Same regex set, applied to framing.md content. The framing has a `## Pronunciation` section that legitimately mentions Arabic-origin allowed-list terms; this section should be excluded from the scan via a marker (e.g., scan everything OUTSIDE `<!--TTS-SAFE-CONFIG-->` blocks).

```python
def assert_no_arabic_transliteration_in_framing(framing_text: str, episode_slug: str) -> None:
    """Block Arabic transliterations in framing.md (excluding pronunciation block)."""
    # Strip pronunciation block before scanning
    import re
    framing_scrubbed = re.sub(
        r"## 14\. Pronunciation.*?(?=\n## )",
        "",
        framing_text,
        flags=re.DOTALL,
    )
    # ... reuse Validator #1's pattern logic ...
```

---

## Validator #3 — `assert_framing_analogy_cap_strict`

**Catches**: v3 mid-episode invention; v4 wax-seal + costume + vault + cups + campfire + parent-child variants.

```python
FORBIDDEN_ANALOGY_KEYWORDS = {
    "sealed room", "two rooms", "two sealed",
    "mail carrier", "mailman", "postal", "envelope",
    "television", "screen", "monitor", "tv ",
    "broadcast", "data stream", "streaming", "server",
    "4k", "hd", "sd", "pixels", "resolution",
    "teacup", "tea cup", "ocean",
    "battery", "terminal",
    "signet", "wax seal", "wax-seal", "wax stamped", "royal seal",
    "crystal pitcher", "silver cup",
    "cosmic ruler",
    "venn diagram",
    "radio tower", "antenna",
    "cosplay", "costume", "dress-up", "dress up",
    "campfire", "camp fire",
    "waterfall", "down a mountain", "down the mountain",
    "solar panel",
    "cathedral",
    "ladder", "valley",
    "fulcrum",
    "pie chart",
    "political map", "border", "firewall",
    "tape measure",
    "podcast", "streaming",
    "vault", "vault holding",
    "cup", "cups are small", "cups that are small",
    "frankenstein",
    "parent", "child", "parents and children",  # "I-am-a-teacher" relation variant
}

def assert_framing_analogy_cap_strict(framing_text: str, episode_slug: str) -> None:
    """Detect forbidden analogies in framing.md.

    Allows: mirror (Beat 2), messenger (Beat 4), light-on-glass-stone (Beat 5),
    source-images (seven seas, speaker-and-foundation, male-female counterparts).
    """
    text_lower = framing_text.lower()
    violations = []
    for keyword in FORBIDDEN_ANALOGY_KEYWORDS:
        if keyword in text_lower:
            violations.append(keyword)

    if violations:
        _flag_p1(
            episode_slug,
            f"R-ANALOGY-CAP-STRICT framing leak: forbidden patterns found = {violations}"
        )
```

**Note**: this is also applied to TRANSCRIPT after audio-overview ships, not just framing. But framing-pre-gen is the first checkpoint.

---

## Validator #4 — `assert_framing_no_modern_artifacts`

```python
FORBIDDEN_MODERN_KEYWORDS = {
    # Electronics
    "television", "screen", "monitor", "phone", "tablet", "computer", "laptop",
    # Streaming
    "broadcast", "server", "data stream", "internet", "app", "software",
    "streaming", "casting media", "video",
    # Resolution
    "sd", "hd", "4k", "8k", "pixels",
    # Social media
    "twitter", " x ", "tiktok", "instagram", "youtube", "social media",
    "algorithm", "content creator", "internet troll", "reply guy",
    # Modern psychology / wellness
    "cognitive behavioral therapy", "productivity framework", "life hack",
    "self-help", "mindfulness app", "dopamine hit", "attention economy",
    # Modern consumer products
    "car ", "plane ", "refrigerator", "lightbulb", "coffee maker",
    # Modern roles
    "influencer", "podcaster", "blogger", "vlogger", "marketer",
    # Modern timestamps
    "21st century", "in our modern world", "modern listener",
    "in today's world", "in the 1990s", "modern-day",
    # Modern slang
    "cosplay", "hot take", "doomscroll", "deep dive", "screen time", "notification",
    # Geopolitics
    "nation-state", "democracy", "election", "parliament",
    # Anachronistic cultural references
    "frankenstein", "popularity contest", "synthetic chemistry",
}

def assert_framing_no_modern_artifacts(framing_text: str, episode_slug: str) -> None:
    """Detect modern-vocabulary contamination in framing.md."""
    text_lower = framing_text.lower()
    violations = [k for k in FORBIDDEN_MODERN_KEYWORDS if k in text_lower]
    if violations:
        _flag_p1(
            episode_slug,
            f"R-NOMODERNIZE framing leak: {violations}"
        )
```

---

## Validator #5 — `assert_framing_honorific_bounded_both_sides`

**Catches**: v3 honorific dropping to ZERO; v4-revised honorific misplacement.

```python
def assert_framing_honorific_bounded_both_sides(framing_text: str, episode_slug: str) -> None:
    """Each honorific appears EXACTLY ONCE (not zero, not twice)."""
    import re

    # "peace be upon him" — for Commander of the Faithful first mention
    pbuh_count = len(re.findall(
        r"\bpeace be upon him\b",
        framing_text,
        re.IGNORECASE,
    ))

    # "peace and blessings of Allah be upon him and his family" — for Prophet
    pbuhf_count = len(re.findall(
        r"peace and blessings of allah be upon him and his family",
        framing_text,
        re.IGNORECASE,
    ))

    violations = []
    if pbuh_count != 1:
        violations.append(f"'peace be upon him' count={pbuh_count} (expected exactly 1)")
    if pbuhf_count != 1:
        violations.append(f"'peace and blessings...' count={pbuhf_count} (expected exactly 1)")

    if violations:
        _flag_p1(
            episode_slug,
            f"R-HONORIFIC-ONCE bound failure: {violations}"
        )
```

---

## Validator #6 — `assert_no_arabic_surah_names_in_chapter_or_framing`

**Catches**: F29 — al-Shams, al-Ahzab, Qaf, al-Isra spoken in audio.

```python
def assert_no_arabic_surah_names_in_chapter_or_framing(
    chapter_text: str,
    framing_text: str,
    episode_slug: str,
) -> None:
    """Block Arabic surah-name leaks. Surahs must be referenced by English meaning."""
    combined = (chapter_text + "\n\n" + framing_text).lower()
    violations = []
    for surah in KNOWN_SURAH_NAMES:
        # Allow "the chapter X" English-meaning patterns that include the surah-name in instruction blocks only
        # Strict: any occurrence in chapter or non-instruction parts of framing is a violation
        if surah in combined:
            violations.append(surah)

    if violations:
        _flag_p1(
            episode_slug,
            f"R-SURAH-ENGLISH-ONLY: Arabic surah names leaked: {violations[:5]}"
        )
```

**Note**: this is a STRICT validator. If chapter prose contains "the chapter al-Shams," it fails. Phase 0e prompt patch (F29) must rewrite chapter prose to use English meanings BEFORE this validator can pass.

**Migration path**: KaR Ch07-Ch15 chapters already shipped under v3 doctrine carry Arabic surah names. Either (a) re-write affected chapters as part of F28 re-emit batch, or (b) accept v3-quality on those + apply F29 doctrine to new chapters only.

---

## Validator #7 — `assert_alqaab_only_established_or_paraphrased`

**Catches**: F24 — novel alqaab translated literally ("the Striker" anti-pattern).

```python
ESTABLISHED_ENGLISH_ALQAAB = {
    "commander of the faithful",  # Amir al-Mu'minin
    "lion of god",                 # Asadullah
    # Add more established renderings as encountered
}

FORBIDDEN_LITERAL_ALQAAB_TRANSLATIONS = {
    "the striker",
    "the puller",
    "the returner",
    "the lion",  # alone, without "of god"
    # Add more anti-patterns as encountered
}

def assert_alqaab_only_established_or_paraphrased(
    chapter_text: str,
    framing_text: str,
    episode_slug: str,
) -> None:
    """Block awkward literal alqaab translations."""
    combined_lower = (chapter_text + "\n\n" + framing_text).lower()
    violations = [k for k in FORBIDDEN_LITERAL_ALQAAB_TRANSLATIONS if k in combined_lower]
    if violations:
        _flag_p1(
            episode_slug,
            f"R-ALQAAB-FUNCTIONAL-PARAPHRASE: {violations} — use functional paraphrase or drop"
        )
```

---

## Validator #8 — `assert_show_notes_has_apparatus_table`

**Catches**: F25 — show-notes lack scholarly apparatus table.

```python
def assert_show_notes_has_apparatus_table(
    show_notes_text: str,
    episode_slug: str,
) -> None:
    """Show-notes (99-show-notes.md) must contain a structured apparatus table."""
    required_headers = [
        "Original / Transliteration",
        "Category",
        "Written Form",
        "Audio Label",
        "First Audio Use",
    ]

    if "## Name and Title Preservation Table" not in show_notes_text:
        _flag_p1(
            episode_slug,
            "F25 apparatus-table missing: '## Name and Title Preservation Table' header not found"
        )
        return

    missing_headers = [h for h in required_headers if h not in show_notes_text]
    if missing_headers:
        _flag_p1(
            episode_slug,
            f"F25 apparatus-table incomplete columns: {missing_headers}"
        )
```

---

## Integration plan (after orchestrator quiesce)

1. Read `scripts/podcast/build_episode_txt.py` head — find existing `_raise()` / `_flag_p1()` helpers + the validator-registry pattern
2. Append `ARABIC_PHONETIC_PATTERNS`, `ALLOWED_ARABIC_ORIGIN`, `KNOWN_SURAH_NAMES`, `FORBIDDEN_ANALOGY_KEYWORDS`, `FORBIDDEN_MODERN_KEYWORDS`, `ESTABLISHED_ENGLISH_ALQAAB`, `FORBIDDEN_LITERAL_ALQAAB_TRANSLATIONS` to the module-level constants section
3. Paste the 8 `assert_*` functions after the existing Tier 2 validators (around the `assert_framing_recurring_thesis_present` function)
4. Wire them into the existing validator-call site (likely in `validate_bundle()` or equivalent)
5. Run against KaR Ch07 v4-revised lab files to confirm expected failures (al-Shams, al-Ahzab, Qaf, wax-seal, costume, etc.)
6. Run against newly-shipped KaR EP03 (under v3 doctrine) to measure backward-compat surface — these would all flag P1 (soft) until F29 chapter rewrite lands

## Test plan

| Test fixture | Validator | Expected result |
|---|---|---|
| v4-revised chapter.txt | #1 (arabic-translit-chapter) | FAIL on al-Shams, al-Ahzab, Qaf (surah names) |
| v4-revised framing.md | #2 (arabic-translit-framing) | PASS (pronunciation block excluded) |
| v4-revised framing.md | #3 (analogy-cap-strict) | PASS (mirror/messenger/light approved; forbidden list intact) |
| v4-revised framing.md | #4 (no-modern-artifacts) | PASS (no Frankenstein in framing) |
| v4-revised framing.md | #5 (honorific-bounded) | PASS (exactly-1 of each in framing) |
| v4-revised lab files | #6 (surah-names) | FAIL on al-Shams, al-Ahzab, Qaf in chapter |
| v4-revised framing.md | #7 (alqaab-paraphrase) | PASS (no novel alqaab) |
| Any episode's 99-show-notes.md | #8 (apparatus-table) | FAIL (no apparatus table exists in any current episode) |

After F29 chapter rewrite + apparatus-table-addition, all validators should pass.
