# Archetype — Islamic Scholastic Text

**Version:** 1.0 (distilled from Kitab al-Riyad, 2026-05-22)
**Genre:** Islamic scholastic prose — Ismaili / Sufi / classical philosophical / hadith-and-exegesis works engaging Quran, hadith, Imam Ali sayings, and primary tradition sources.
**Empirical basis:** Kitab al-Riyad (13 chapters, ~117k words), one full pipeline cycle through Phase 0a→trainer, EP10 cleared P0 via fixer pass and returned SHIP-WITH-CAUTION with 3 P1s requiring author judgment.
**Pipeline coverage:** Phase 0d (chapter design) + Phase 0e (chapter authoring/enrichment) + Phase 0g (framing authoring).
**Validator coverage:** F20 (no Arabic names), F24 (alqaab functional paraphrase), F27 (Tier 2.5 validators), F29 (surah English-only).
**Challenger categories addressed:** A (citations), C (pronunciation), J (name aliasing), M (modernization), N (phonetic-as-content), O (honorifics), R (conversation choreography).

---

## How to use this archetype

1. **For a new Islamic scholastic book** entering the pipeline at Phase 0a:
   - Append the **Phase 0d/0e doctrine** (§3) to the system prompt of `scripts/podcast/_authoring.py` `author_phase_0e()`.
   - Append the **Phase 0g framing template** (§4) to the system prompt of `author_framing()`.
   - Pre-populate the **chapter contract template** (§9) with the genre defaults.
   - Pre-load the **forbidden patterns catalog** (§7) into the challenger's KNOWN_FORBIDDEN constants so book-1 doesn't have to discover them.

2. **For the KaR finish** (manual mode):
   - Apply §3+§4 conventions to fix EP10's 3 remaining P1s (validation pass on the archetype).
   - Apply §4 template to author the 12 remaining chapter framings (chapters 01–09, 11–13) with cheap LLM-skeleton + heavy hand-edit.
   - Run `scripts/podcast/build_episode_txt.py` per chapter to emit episode .txts.

3. **For the challenger** going forward:
   - Findings should cite the archetype rule ID (e.g., "A4-translator-mismatch per archetype §6.1") so doctrine traceability is preserved.
   - The challenger's existing 7 F27 validators already enforce the bulk of this archetype — see §8 for the validator-to-rule map.

---

## §1. Genre signature — what makes a text "Islamic scholastic"

An Islamic scholastic text is recognized by **all** of these features:

- **Source-tier diversity**: Citations weave at least four tiers — (Tier 1) primary author's own treatises; (Tier 2) Quran; (Tier 3) Sunni or Shia hadith collections; (Tier 4) Imam Ali sayings (Nahj al-Balagha, Ghurar al-Hikam) or other early-tradition sermons/letters.
- **Honorifics**: Names of the Prophet, Imams, and revered figures carry post-name honorific phrases — `(peace be upon him)`, `(peace and blessings of Allah be upon him)`, `(may Allah be pleased with him)`, etc. Never abbreviated (no PBUH, no SAW).
- **Conceptual vocabulary**: Arabic technical terms appear inline — `tawhid` (monotheism), `hudud` (limits), `da'wa` (the call), `natiq` (speaker-prophet), `hayula` (prime matter), `nafs` (soul), `ruh` (spirit), `shirk` (associating partners with God), `falsafa` (philosophy), `kun` (the divine "Be!"). These are technical, not ornamental — substitution policy applies.
- **Quranic citation discipline**: Quotes follow `(Quran chapter:verse; English surah description)` with translator named on first occurrence (Yusuf Ali, Asad, Pickthall, Sahih International, or "rendered after [translator]" for paraphrase).
- **Hadith citation discipline**: `(Collection, Book, Hadith #)` — e.g., `(Sahih al-Bukhari, Book 59, Hadith 3191)`. Collection name is always specific; no generic placeholders.
- **Primary-source citation discipline**: Work title + author or speaker + (for sermons/letters) numbered identifier. Example: `(the book *The Path of Eloquence*, Sermon 1)` for Nahj al-Balagha.

If a book hits 4 of the 6 features, treat it as Islamic scholastic and load this archetype.

---

## §2. The TTS-engineering problem this archetype solves

NotebookLM's voice model mangles Arabic. Empirically observed on KaR:
- `al-Kirmani` drifted into **12+ phonetic variants** across a single 42-minute episode.
- `al-hayuli` reads as `Allah` to the voice model — same vowel pattern, catastrophic semantic collision.
- Arabic surah names (`Surat Ya Sin`, `Surat an-Nahl`) read as unfluent syllable strings — listener confusion.

The archetype's discipline is **English-substitution + stable English labels + Pronounce-block exception** — the chapter prose carries zero Arabic after first mention; technical terms that MUST remain in Arabic (because they encode a doctrine non-translatable into English) get explicit Pronounce directives in the framing's Pronunciation block. Everything else is replaced.

This is the single largest source of P0/P1 findings on Islamic texts. Solve it once at the archetype level and book-2 onward saves ~30% of pipeline iteration cost.

---

## §3. Phase 0d/0e doctrine — chapter-prose authoring

Apply at chapter design (0d) and chapter authoring/enrichment (0e). These rules belong in the system prompt of `author_phase_0e()`.

### §3.1 R-NO-ARABIC-NAMES (F20)

After first mention, **zero Arabic personal names, book titles, or concept words appear in chapter prose**. Allow-list of Arabic-origin words that may remain:
- `Quran`, `Imam`, `Medina`, `Mecca`, `Ismaili`, `Fatimid`, `Sunni`, `Shia` (proper nouns / standard English usage).
- Quranic verse content **inside** a blockquote (the verse itself, not the citation).

Substitution patterns (canonical for Islamic scholastic texts):
- **Personal names → stable English label** (one label per figure for the entire episode set). Examples from KaR:
  - `al-Kirmani` → `the author` (book-wide stable label)
  - `Ibn Sina` → `the earlier philosopher` or `Avicenna` if Anglicized
  - `al-Mu'ayyad fi'l-Din al-Shirazi` → `the chief missionary`
  - `Hamid al-Din Ahmad al-Kirmani` → `the author` (NOT re-introduced by full name later, including in bold headers)
- **Book titles → English wrapper** at first mention, then short form. Examples:
  - `Rahat al-Aql` → `the book *The Repose of the Intellect*` (first), then `the book` or `that book` or `*The Repose of the Intellect*`
  - `Aqwam al-Marasim` → `the book *Milestones of Religion*`
  - `al-Masabih` → `the book *With Lamps*`
- **Concept words → English equivalent** throughout. After first occurrence (where the Arabic may appear once in italics with the English gloss), use the English form:
  - `tawhid` → `monotheism` or `the affirmation of divine oneness`
  - `hudud` → `the limits` (the hierarchy of religious ranks)
  - `da'wa` → `the call` (the Ismaili mission)
  - `natiq` → `the speaker-prophet`
  - `shirk` → `associating partners with God`
  - `falsafa` → `philosophy` (the Greek-derived tradition)

### §3.2 R-SURAH-ENGLISH-ONLY (F29)

Surahs are referenced by **English meaning of the surah name**, not the Arabic name. Examples table for common surahs:

| Arabic surah name | English meaning (use this) |
|---|---|
| al-Fatihah | the chapter of the opening |
| al-Baqarah | the chapter of the cow |
| al-Ikhlas | the chapter of sincerity |
| an-Nahl | the chapter of the bee |
| Ya Sin | the chapter of the mystic letters (or: the chapter that opens with "Ya Sin") |
| ash-Shura | the chapter of consultation |
| al-Mulk | the chapter of dominion |
| al-Ahzab | the chapter of the confederates |
| al-Nur | the chapter of light |
| al-Anfal | the chapter of the spoils |
| al-Tawbah | the chapter of repentance |
| al-Isra' | the chapter of the night journey |
| al-Kahf | the chapter of the cave |
| Maryam | the chapter of Mary |
| al-Anbiya' | the chapter of the prophets |

Citation form: `(Quran 16:40; the chapter of the bee)` or `(Quran 16:40, the chapter of the bee)`. **Never** `(Surat an-Nahl)` or `Surat al-Baqarah` in chapter prose.

### §3.3 R-ALQAAB-FUNCTIONAL-PARAPHRASE (F24)

Only **established English alqaab** (titular epithets) are spoken. Established list:
- `Commander of the Faithful` (for Imam Ali)
- `Lion of God` (for Imam Ali)
- `the Prophet` (generic when context is clear)
- `the Messenger of God` (for the Prophet)
- `the Trustworthy` (al-Amin, an established epithet for the Prophet pre-prophethood)

For **novel or obscure alqaab**, use a **functional paraphrase**, NOT a literal translation. Anti-pattern: translating an epithet like `al-Daribu` literally as "the Striker" — that's the F24 violation. Right pattern: paraphrase what the epithet means in context ("the one who delivers decisive judgments").

### §3.4 Honorific discipline (R-HONORIFIC-ONCE BOUNDED BOTH SIDES)

Each honorific phrase **expanded exactly once per chapter, at first mention** — not zero, not twice. Mandatory at first mention.

- The Prophet's honorific: `(peace and blessings of Allah be upon him)` — once at first mention of Muhammad/the Prophet/the Messenger.
- Imams' honorific: `(peace be upon him)` — once at first mention of each Imam.
- Companions' honorific: `(may Allah be pleased with him/her)` — once at first mention.
- Allah's honorific: `(glorified and exalted is He)` or `(may He be glorified)` — once at first mention in chapter, optional thereafter.

**Forbidden**: PBUH, SAW, AS, RA, SWT, JJ abbreviations. Always spelled out. Never repeated.

### §3.5 Citation discipline

**Quranic citations** — verbatim quote OR clearly attributed paraphrase:
- Format: `> *quoted text* (Quran chapter:verse; English surah description; translator)`.
- Example: `> *We have created man into toil and struggle.* (Quran 90:4; the chapter of the city; Yusuf Ali)`.
- First Quranic occurrence in a chapter **MUST** name the translator. Subsequent occurrences inherit unless they switch translators.
- If the rendering is the author's own paraphrase, attribute as `(... ; rendered by the author)` or `(... ; literal rendering)` — NOT a translator's name the rendering doesn't actually match.
- **Verify before attributing.** Pickthall's Q16:40 is "But Our commandment is but one, as the twinkling of an eye." If your text reads "Our only word for a thing, when We will it, is that We say to it, 'Be,' and it is" — that's Yusuf Ali, not Pickthall. Attribute correctly or label as paraphrase.

**Hadith citations**:
- Format: `(Collection, Book #, Hadith #)` — e.g., `(Sahih al-Bukhari, Book 59, Hadith 3191)`.
- For Shia hadith: `(al-Kafi, Volume #, Book of X, Hadith #)`.
- **Never** use placeholder strings like `the canonical hadith compiler`, `the major collection`, `the Sunni compiler`. Always specific. (This is the empirically observed Phase 0e template variable bug — corrupted hadith citations in KaR ch10.)

**Imam Ali / Nahj al-Balagha citations**:
- Format: `(the book *The Path of Eloquence*, Sermon N)` or `(*The Path of Eloquence*, Letter N)` or `(*The Path of Eloquence*, Aphorism N)`.
- Alternative if speaking aloud: `(*The Path of Eloquence*, Sermon 1)` — sermon number always present.
- Honorific `(peace be upon him)` on first mention of Imam Ali in the chapter.

**Ismaili primary-source citations**:
- Format: `(*Work Title*, author or attributed speaker; for Farmans add date and location)`.
- Example: `(*Aqwam al-Marasim*, the author, c. 411 AH)` or for the English-wrapped form: `(the book *Milestones of Religion*, the author)`.

### §3.6 Biographical context discipline (I2)

Biographical context appears **at most once per chapter**, only when directly necessary to interpret the argument. Forbidden patterns:
- "Born in [city] in [year]..."
- "Studied under..."
- "Wrote his most famous work..."
- "Lived during the reign of..."

If biography is needed (e.g., to explain why the author is engaging a specific predecessor), use ONE sentence, not a paragraph: "The author was a Fatimid-era philosopher writing against the kalam tradition" — done. No further biography in the chapter.

### §3.7 TTS-prosody discipline (B5)

- **Em-dashes** corrupt TTS pacing — voice model reads as long pause. **Replace all em-dashes with commas or semicolons.**
- Empirically observed: 77 em-dashes in KaR ch10 (motion-stillness) before cleanup. Phase 5 TTS-cleanup removes these; if you're authoring chapters manually, do it as you go.
- Acceptable punctuation: comma, semicolon, colon, period, question mark, parentheses (for citations and one-shot role-epithets only).

---

## §4. Phase 0g doctrine — framing authoring

Apply at framing authoring (0g). The framing template below mirrors EP10's clean structure (~3,500 words for an extended-length chapter).

### §4.1 Framing structure (14 sections, in order)

1. **Opening directive** — Brief welcome (one sentence) + 2–3 sentence thesis naming source, central tension, landing question. Sets the conversation's stakes.
2. **Background** — ONE-time only context. Used when listener needs scaffolding to follow the argument. Limit to 3 sentences max. NO biographical detail beyond what's strictly load-bearing.
3. **Pronunciation** — Imperative-form directives for every Arabic term in the chapter prose. See §5 for exhibit format.
4. **Stable role-labels** — R-STABLE-ROLE-LABELS spec. One English label per figure for the entire episode. See §4.2.
5. **Host dynamic** — Driver = curious-mind (asks, probes, summarizes); Color = scholar-companion as **genuine challenger** (must pushback ≥3 times with literal doubt patterns from §4.3 below).
6. **Conversation choreography** — Reset clauses, separate-prep planting, cadence directives. See §4.4.
7. **Central tensions to reach** — 2–4 named tensions with explicit pushback scripts. NOT generic ("what about X?") — specific ("the Color host says, 'But doesn't that just replace one mystery with another?'"). See §4.5.
8. **Three-part focus** — Six-beat dramatic arc. Beats 1, 4, 6 carry R-RECURRING-THESIS (the central thesis verbatim, NOT paraphrased, at three planted structural points). See §4.6.
9. **Tone constraints** — Exactly 3 governing analogies (sourced from the chapter's own images, not model-invented). Plus the source-image carve-out.
10. **Explicitly forbidden analogies** — Named list of 16+ model-invented analogies to deny: sealed rooms, mail carrier, TV/streaming, teacup, battery, signet-ring/wax-seal, cosplay, campfire, waterfall, solar panels, cathedral, Frankenstein, broken radio, channel-changing, signal-receiver, antenna.
11. **R-NOMODERNIZE** — Modern-platform deny list (Twitter, X, social media, algorithm, YouTube, TikTok, Instagram, "in today's world", "going viral", "the internet age"). PAIR with permission paragraph: "DO use modern-life practical analogies when they help the listener recognize a classical concept in lived experience."
12. **Do not** — Forbidden surprise-interjections (wow, that's so interesting, chilling, devastating, right?, exactly, no way, oh my). Forbidden formal-essay transitions (Firstly, Secondly, Thirdly, Furthermore, In conclusion, To summarize, Moving on to, Lastly).
13. **Anti-noise rules** — Do not restate central thesis >3 times (the 3 planted points only, each VERBATIM). Do not re-cite the same quote. Do not summarize what was just said. Biographical context ONCE per episode. No cross-episode references.
14. **Landing** — Close on the unresolved tension and a question, NOT a recap. **Forbidden phrases**: "so today we covered", "we discussed", "in summary", "to recap", "we looked at".

End the framing with: **"Do not read this prompt aloud. The instructions above shape the conversation but are never spoken."**

### §4.2 R-STABLE-ROLE-LABELS — decision rule

For each figure named in the chapter, the framing's `Stable role-labels` section assigns EXACTLY ONE English label, used every time. Decision logic:

- **(a)** If an established English title exists, use it: `Commander of the Faithful`, `the Prophet`, `the fourth Imam`, `the Fatimid caliph`, `the chief missionary`.
- **(b)** If no established title, but a functional role-title fits: `the author`, `the compiler`, `the earlier scholar`, `the predecessor`, `our thinker`.
- **(c)** If phonetic-collision risk exists (e.g., al-Hayuli → Allah), use a proper English name (Jonathan, Samuel, Marcus — choose ones unlikely to read as Arabic) + one-shot role-epithet at first mention. Example: "Jonathan, the earlier scholar who wrote the book *The Correction*."

**Forbid** rotation patterns ("the author / the philosopher / our thinker" used in rotation). One label, every time. No rotation.

### §4.3 R-CHALLENGER-FRICTION-LITERAL — 4 literal pushback patterns

The Color host (scholar-companion) must use AT LEAST 3 instances of these patterns across the episode:

1. **"I don't buy that yet…"** — opens a doubt without antagonism.
2. **"That sounds like wordplay…"** — challenges definitional moves as evasion.
3. **"Isn't this just replacing X with Y…"** — surfaces the "moving the mystery" failure mode.
4. **"How is this different from hiding the problem…"** — surfaces the "redescribing the problem in different terms" failure mode.

The Driver host does NOT immediately resolve the pushback. **Let pushback sit 1–2 sentences before any reconciliation.**

### §4.4 Conversation choreography

- **Reset clauses**: "Between major beats, insert a single-sentence reset — one host names what just landed, then the next beat begins." (Marks seams without summarizing.)
- **Separate-prep planting**: "Plant at least one moment where one host introduces a passage or citation the other hasn't led toward." (Breaks the alternating Q-A rhythm.)
- **Cadence**: "Short-to-medium sentences with varied rhythm. Pace is conversation, not lecture. Hosts are thinking out loud."
- **Interruption avoidance (K1)**: "Each host completes a thought before the other responds. No interjections inside the other host's sentence. No talking over."

### §4.5 Central tensions — concrete spec

Each tension is named specifically and carries an explicit pushback script. Template:

```
**Tension 1: [Specific name of the doctrinal conflict]**
The argument: [author's position in 2 sentences]
The pushback: [The Color host says, "[exact pushback line]"]
The pivot: [How the conversation moves forward — NOT how the Driver "resolves" the pushback, but how the dialogue reaches the author's pivot]
```

For an Islamic scholastic chapter, common tension shapes:
- **Substantialist vs. relational ontology** — "Is X a thing or a relation?"
- **Apophatic vs. cataphatic theology** — "Can we speak of God's attributes positively or only by negation?"
- **Hierarchical emanation vs. direct creation** — "How does the One produce the many?"
- **Universal vs. particular prophetic guidance** — "Why does each cycle need a new speaker-prophet?"

### §4.6 Six-beat dramatic arc — R-RECURRING-THESIS

The Three-part focus section walks 6 beats:

- **Beat 1: Crisis open with thesis #1 (VERBATIM)** — The central thesis stated word-for-word.
- **Beat 2: Failed answer A** — A predecessor's solution and why it fails.
- **Beat 3: Failed answer B** — Another predecessor's solution and why it fails.
- **Beat 4: Author's pivot with thesis #2 (VERBATIM)** — Same central thesis, restated word-for-word.
- **Beat 5: Non-bodily correction** (or equivalent — the author's positive contribution).
- **Beat 6: Stakes close with thesis #3 (VERBATIM)** — Same central thesis a third time, word-for-word.

The thesis must be **the same string** in all 3 occurrences. Example from KaR EP10: "The Creative IS the creativity." Not "the Creator is the creating", not "creativity defines the Creator" — the exact same words at all 3 anchor points.

---

## §5. Pronunciation exhibit conventions

### §5.1 Format

Every Arabic term that appears in chapter prose (italicized or not) MUST have a Pronounce directive in the framing's `## Pronunciation` block. Format:

```
Pronounce "X" as "phonetic-rendering". Say it as N fluent syllables, accent on the Nth; this is the Arabic for English-meaning. Do not spell it.
```

**Required elements** in each directive:
- **Imperative opener** — "Pronounce" (not "X is pronounced" — passive forms forbidden).
- **Phonetic rendering** — uppercase syllable for accent, hyphens between syllables. Examples: `al-ha-YOO-laa` (al-hayula), `al-NAFS` (al-nafs), `taw-HEED` (tawhid), `KOON` (kun).
- **Syllable count + accent position** — "Say it as four fluent syllables, accent on the third."
- **English meaning gloss** — "this is the Arabic for prime matter."
- **"Do not spell it" guard** — for terms that might be misread letter-by-letter.

### §5.2 Coverage requirement (N3)

**Every transliterated Arabic term in the chapter must have a matching Pronounce directive.** This is the most-frequent P1 finding for Islamic texts (16 N3 findings in KaR's findings.jsonl).

For chapter-prose terms italicized as Arabic technical terms (`*al-hayula*`, `*al-nafs*`, `*mawhumiya*`, `*takhayyuliya*`), the choice is binary:
- **Option A**: Add a Pronounce directive in the framing.
- **Option B**: Replace the term with an English equivalent in the chapter prose (per §3.1 substitution policy).

**Default to Option B** unless the Arabic term is doctrinally non-translatable (e.g., `tawhid` keeps its Arabic identity in scholarly contexts; `al-hayula` is the Aristotelian Greek `hyle` Arabized and the chapter is making a specific etymological point).

### §5.3 Common terms to pre-load for Islamic scholastic texts

These should be in every Pronunciation block (if the chapter uses them):

| Term | Pronounce as | Syllables | Meaning gloss |
|---|---|---|---|
| Quran | qoor-AAN | 2 | the Quran (no spelling needed) |
| Imam | ee-MAAM | 2 | religious leader |
| Allah | al-LAH | 2 | God |
| tawhid | taw-HEED | 2 | monotheism / divine oneness |
| hudud | hu-DOOD | 2 | the limits / hierarchy of ranks |
| da'wa | DAW-wah | 2 | the call / the mission |
| natiq | NAA-tiq | 2 | speaker-prophet |
| hayula | ha-YOO-laa | 3 | prime matter |
| al-hayula | al-ha-YOO-laa | 4 | the prime matter (definite form) |
| nafs | NAFS | 1 | soul |
| al-nafs | al-NAFS | 2 | the soul (definite form) |
| ruh | ROOH | 1 | spirit |
| al-ruh | ar-ROOH | 2 | the spirit |
| shirk | SHIRK | 1 | associating partners with God |
| falsafa | FAL-sa-fah | 3 | philosophy (Greek-derived tradition) |
| kun | KOON | 1 | the divine "Be!" |
| kaf | KAAF | 1 | the Arabic letter K |
| nun | NOON | 1 | the Arabic letter N |
| sura | SOO-rah | 2 | a Quranic chapter |
| Nahj al-Balagha | NAHJ al-ba-LAA-ghah | 5 | the book *The Path of Eloquence* |

### §5.4 No-read-aloud guard

Framing ends with:
> Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.

This is the N4 requirement. Always present.

---

## §6. Common P0/P1 trap catalog (empirically validated from KaR)

These are the failure modes that appear most often. The challenger catches them post-hoc; this archetype prevents them at authoring time.

### §6.1 Phase 0e template variable corruption (P0)

**Symptom**: Strings like `Imam the canonical hadith compiler`, `Sahih the canonical hadith compiler`, `the major Sunni collection` appear in the chapter prose verbatim.
**Cause**: Phase 0e's prompt template has unresolved variable substitution — when the model can't resolve, it leaves the literal placeholder string in the output.
**Fix**: Hardcode hadith citations in the Phase 0e prompt with the specific collection name. NEVER use generic placeholders. If a hadith citation is uncertain, leave a `[CITATION NEEDED: hadith on X]` marker — challenger catches that as D5/P0 and it's a clean halt.
**Pre-empt at authoring**: After Phase 0e runs, grep the output for literal strings `the canonical`, `the major`, `the prominent compiler` — if any survive, fix before challenger sees it.

### §6.2 Scholarly transliteration not covered in Pronunciation block (P1, N3)

**Symptom**: Chapter uses `*al-hayula*` 5 times in italics; framing's Pronunciation block has `hayle` (English vernacular) but not `Al-hayula`.
**Cause**: Phase 0e leaves scholarly transliterations italicized, but Phase 0g writes Pronounce directives only for the English vernacular forms or the most-common terms.
**Fix**: When Phase 0g authors the Pronunciation block, scan the chapter prose for every italicized Arabic term and emit a matching Pronounce directive.
**Pre-empt**: Pass a `--phonetic-coverage-scan` flag to Phase 0g that lints chapter prose against the Pronunciation block before emitting framing.

### §6.3 Surah-naming inconsistency (P1, N3)

**Symptom**: Chapter mixes `*Surat Ya Sin*` (Arabic) with `*Surat the chapter on sincerity*` (English) inconsistently.
**Cause**: Phase 0e applies F29 substitution unevenly across surah references.
**Fix**: Phase 0e's F29 rule must be applied to ALL surah references in a single pass. Build a surah-substitution table once per chapter, apply throughout.
**Pre-empt**: F27 validator #5 (`assert_no_arabic_surah_names`) catches this — confirm it runs on every chapter.

### §6.4 Meta-artifact insertion (P1, B1)

**Symptom**: Garbled italic markers fused into prose — `by origination at *dar an earlier work on origination'*`. Broken markdown + editorial remnant.
**Cause**: Phase 0e's enrichment-merging step occasionally fuses an editorial note with the next prose token.
**Fix**: Phase 0e should emit clean markdown — no `*` characters except as italic delimiters, no apostrophes inside italics.
**Pre-empt**: F27 validator runs B1 META_PROSE_TELLS scan; manual grep for `*dar`, `'*`, `**` (triple) before challenger.

### §6.5 Full-name reintroduction after alias (P1, J2)

**Symptom**: Framing uses `the author` everywhere; chapter has a section header `## Hamid al-Din Ahmad al-Kirmani` at line 200 that reintroduces the full Arabic name.
**Cause**: Phase 0e leaves chapter section headers untouched even after applying R-STABLE-ROLE-LABELS to chapter prose.
**Fix**: Phase 0e must apply R-STABLE-ROLE-LABELS to **all** chapter content, including section headers.
**Pre-empt**: F27 validator #1 (`assert_no_arabic_transliteration`) — confirm it scans headers as well as prose.

### §6.6 Technical-term exemption without C4 justification (P2)

**Symptom**: Chapter retains `*al-nafs*` and `*al-ruh*` in Arabic; framing has no note explaining the exemption.
**Cause**: Some technical terms (al-nafs/al-ruh) carry doctrinal weight that the English ("soul"/"spirit") doesn't capture in scholarly context. They're legitimately retained — but the framing must justify.
**Fix**: When retaining an Arabic technical term, add a C4 justification line in the framing's Tone constraints: "We keep the Arabic *al-nafs* and *al-ruh* because the soul/spirit distinction in English collapses the tripartite vocabulary."
**Pre-empt**: Add a `## Substitution-policy notes` subsection to Tone constraints listing every retained Arabic term + its justification.

### §6.7 Em-dash density (P1, B5)

**Symptom**: 77 em-dashes in chapter prose (ch10 before cleanup).
**Cause**: Phase 0e's prose style favors em-dashes; voice model reads them as long pauses.
**Fix**: Phase 0e's prompt must include: "Use commas, semicolons, or colons — never em-dashes (—)."
**Pre-empt**: Phase 5 TTS-cleanup `kar_chapter_cleanup.py` replaces em-dashes with commas/semicolons. Run on every chapter.

### §6.8 Quranic translator attribution mismatch (P1, A4)

**Symptom**: Chapter cites `(Quran 16:40; translation rendered after Pickthall)` but the actual quoted text matches Yusuf Ali, not Pickthall.
**Cause**: Phase 0e's citation discipline names a translator without verifying the rendering matches.
**Fix**: When Phase 0e emits a Quranic quote, it must either (a) verbatim match a named translator's published text, OR (b) be labeled `(... ; rendered by the author)` or `(... ; literal rendering)`.
**Pre-empt**: Phase 0e gains a Quranic-quote verification step against a corpus of canonical translations (Yusuf Ali, Asad, Pickthall, Sahih International).

---

## §7. Forbidden patterns catalog

### §7.1 Forbidden analogies (16+)

For framing's `## Explicitly forbidden analogies` section:
- sealed rooms
- mail carrier / mailman / postal service
- TV channels / streaming / 4K / Netflix
- teacup / teapot / pouring water
- battery / charging / power outlet
- signet-ring / wax-seal
- cosplay / costume / dress-up
- campfire / bonfire
- waterfall / river-flow
- solar panels / solar power
- cathedral / mosque interior / architecture
- Frankenstein / monster / patchwork creature
- broken radio / static
- channel-changing / remote control
- signal-receiver / antenna
- iceberg (visible/hidden)

### §7.2 Forbidden surprise-interjections (R-NOSURPRISE)

For framing's `## Do not` section:
- wow
- that's so interesting
- it's chilling
- it's devastating
- right?
- exactly
- no way
- oh my
- huh!
- whoa
- crazy
- mind-blown / mind-blowing

### §7.3 Forbidden formal transitions (R-FORMAL-TRANSITION-DENY)

For framing's `## Do not` section:
- Firstly / First of all
- Secondly / Second of all
- Thirdly
- Fourthly / Finally
- Furthermore
- Moreover
- In conclusion / To conclude
- To summarize / In summary
- Moving on to / Turning to
- Lastly
- On the one hand / On the other hand (when used as formal connectors)

### §7.4 Forbidden modern artifacts (R-NOMODERNIZE)

For framing's `## R-NOMODERNIZE` section:
- Twitter / X (the platform)
- social media
- algorithm / algorithmic feed
- YouTube
- TikTok
- Instagram
- Facebook / Meta
- the internet (when used as a setting)
- "in today's world"
- "in our modern era"
- "going viral"
- "cancel culture"
- AI / artificial intelligence (when not the chapter's subject)
- iPhone / smartphone
- podcast (self-reference — never)

**Permission paragraph (PAIR with the deny list):**
> DO use modern-life practical analogies when they help the listener recognize a classical concept in lived experience — a chef adjusting recipes, a carpenter judging joints, a parent teaching a child. The deny list above blocks named platforms and "in today's world" phraseology; it does NOT block lived-experience analogies grounded in classical human practices.

### §7.5 Forbidden punctuation

- **em-dash (—)** — replace with comma, semicolon, or colon.
- **ellipsis (…)** — replace with period or comma.
- **emoji** — never.
- **HTML tags** — never (B1 violation).

---

## §8. Validator-to-rule map (F27 Tier 2.5)

How the 7 F27 validators in `scripts/podcast/build_episode_txt.py` enforce this archetype:

| Validator | Archetype rule | Severity |
|---|---|---|
| `assert_no_arabic_transliteration()` | §3.1 R-NO-ARABIC-NAMES (F20+F29) | P1 |
| `assert_framing_analogy_cap_strict()` | §4.1 (Tone constraints) + §7.1 (forbidden analogies) | P1 |
| `assert_framing_no_modern_artifacts()` | §4.1 (R-NOMODERNIZE) + §7.4 | P1 |
| `assert_framing_honorific_bounded_both_sides()` | §3.4 R-HONORIFIC-ONCE | P1 |
| `assert_no_arabic_surah_names()` | §3.2 R-SURAH-ENGLISH-ONLY (F29) | P1 |
| `assert_alqaab_only_established_or_paraphrased()` | §3.3 R-ALQAAB-FUNCTIONAL-PARAPHRASE (F24) | P1 |
| (constants library) | Defines patterns used by validators above | — |

**Gaps not covered by F27** (challenger catches but no static validator):
- §6.1 Phase 0e template variable corruption — challenger A2 (semantic, P0).
- §6.4 Meta-artifact insertion — challenger B1 (semantic, P1).
- §6.8 Quranic translator attribution mismatch — challenger A4 (requires translation corpus, P1).

**Future validator candidates** (worth building if the archetype propagates to 3+ books):
- `assert_no_phase_0e_template_variables()` — grep for known unresolved placeholders.
- `assert_quranic_quote_matches_named_translator()` — corpus-checked validation.
- `assert_chapter_headers_apply_stable_role_labels()` — extends §3.1 to headers.

---

## §9. Chapter contract template (Phase 0d output)

For Islamic scholastic chapters, the contract YAML should follow this template with genre defaults:

```yaml
chapter_ref: chNN-<slug>
slug: <slug>
source_type: book-chapter
book_slug: <book-slug>
source_chapter_ref: <ref-in-source-book>
episode_number: <NN>

title: <concise title, ≤6 words, may include 1 italicized Arabic technical term if doctrinally load-bearing>

audience: |
  Thoughtful adult readers who have followed [scaffolding chapters], familiar with [prerequisite concepts],
  and prepared to track an argument across [philosophical / theological / exegetical] territory.
  Not theologians; not specialists. Reading-level: serious general nonfiction.

angle: faithful_exposition  # enum: faithful_exposition | comparative | polemical | reconstructed

episode_format: deep_dive  # enum: deep_dive | debate

host_dynamic: curious_mind + scholar_companion  # for deep_dive
host_dynamic_custom: null

debate: null  # populated only when episode_format = debate

length_target: extended  # enum: brief | default | extended | ultra
# extended soft band: 5,500-9,500 words; hard cap: 10,500 words

key_tensions:
  - |
    [Specific doctrinal conflict #1 named, not generic. 2-3 sentence narrative block describing what's at stake.]
  - |
    [Specific doctrinal conflict #2 named.]
  - |
    [2-5 tensions per chapter; more for argumentative density, fewer for simple exposition.]

tone_constraints:
  - |
    [Walk the chapter's structural movements in order — do not rearrange.]
  - |
    [When the author sides with X, name the move; do not abstract.]
  - |
    [Substitution-policy note: we keep Arabic technical term *X* because [doctrinal reason].]
  - |
    [3-7 tone directives, each narrative.]

anchor_passages:
  - |
    [Key quote #1 verbatim from source, 1-3 sentences, the kind a host would reach for.]
  - |
    [6-11 anchor passages per chapter.]

adaptation_mode: faithful  # enum: faithful | adapted | simplified

phonetic_overrides:
  # Map of Arabic term -> phonetic override (used by Phase 0g Pronunciation block)
  # Pre-populate with terms in this chapter from the §5.3 common-terms table.
  al-hayula: al-ha-YOO-laa
  al-nafs: al-NAFS
  # Add chapter-specific terms as encountered.

show_notes:
  blurb: |
    [Show-notes narrative summary, 3-5 sentences. The "what this episode is about" prose.]
  related_episodes:
    - <other-slug-in-series-1>
    - <other-slug-in-series-2>
  references:
    - |
      [Reference description with full citation. For Islamic texts: include Quran translator if quoted,
       hadith collection if cited, primary source if drawn from author's other works.]
```

---

## §10. Drift watch — what to add when book-2 ships

This archetype is v1.0, distilled from KaR alone (a Ismaili philosophical text). When the second Islamic scholastic book ships:

1. **Compare phonetic-override needs** — Sufi texts will likely add terms (`fana`, `baqa`, `dhikr`, `tariqa`, `wali`, `qutb`); kalam-tradition texts will add (`jawhar`, `arad`, `sifa`, `mahiyya`). Update §5.3.
2. **Compare honorific forms** — different traditions invoke different honorifics. Update §3.4.
3. **Compare citation discipline** — Shia hadith uses `al-Kafi`, `Bihar al-Anwar`; Sufi texts cite `Fusus al-Hikam`, `Futuhat al-Makkiyya`. Update §3.5.
4. **Compare forbidden-analogy drift** — if book-2 throws a model-invented analogy not in §7.1, add it.
5. **Compare new F27 validators** — if new patterns emerge, document them in §8 and (if static-checkable) propose them as F27 additions.

**Archetype review trigger**: Every third Islamic scholastic book through the pipeline, OR when a SHIP-WITH-CAUTION verdict surfaces a P1 pattern not covered here.

---

## §11. Provenance and authority

- **Distilled from**: Kitab al-Riyad (KaR) — 13 chapters, ~117k words, full pipeline cycle 2026-05-18 through 2026-05-22. EP10 (motion-stillness-hyle-and-form) cleared P0 via fixer pass; 3 P1s deferred to author judgment.
- **Doctrine sources**: Phase 4 v4-revised commits (`23009eb`), Phase 5 TTS-safe cleanup (`f54c657`), F27 Tier 2.5 validators (`3631bc0`).
- **Validator authority**: F27 validators in [`scripts/podcast/build_episode_txt.py`](../../../../scripts/podcast/build_episode_txt.py) enforce sections §3.1, §3.2, §3.3, §3.4, §7.1, §7.4 statically; sections §6.1, §6.4, §6.8 require challenger semantic checks.
- **Challenger spec**: [`.github/agents/podcast-challenger.agent.md`](../../../../.github/agents/podcast-challenger.agent.md) — categories A, C, J, M, N, O, R map to this archetype's enforcement areas.
- **Replaces / supersedes**: nothing prior — this is the first formal archetype in `content/podcast/library/archetypes/`. Future archetypes (e.g., Sufi-specific, Shia-specific, Sunni-kalam-specific) may inherit from this base and override genre-specific sections.

**End of archetype v1.0.**
