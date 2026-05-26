## Inventory

- **Bundle:** `EP06 — Justice, Monotheism, and the Guardians of Allah` (the-master-and-the-disciple, chapter 6)
- **Files present (5):** `00-framing.md`, `02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`, `99-show-notes.md`
- **Files missing (1):** `01-source.md` (or `01-chapter.md`) — primary source document is not in the bundle, so NotebookLM has no retrievable chapter prose
- **Artifact-coverage status:**
  - framing → present, dense, mostly well-formed
  - primary source → **MISSING** (P0 in this context — the entire retrieval substrate)
  - key passages → **present-but-empty placeholder** (`> >` plus `[LLM-FILL]`)
  - context pack → **present-but-empty** (every field is `[LLM-FILL]`)
  - discussion spine → **present-but-empty** (every one of 8 beats is `[LLM-FILL]`; also a structural beat-count mismatch with framing's 6-beat arc)
  - show notes → present, but heavily transliterated, italics-laden, and contradicts framing's name-discipline

Net: this is a stub bundle dressed up by one rich framing file. NotebookLM would have nothing to ground on, no verbatim quotes to retrieve, no built spine to follow.

---

## Chapter Findings

### Chapter 6: Justice, Monotheism, and the Guardians of Allah

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | (missing) `01-source.md` | bundle root | No primary source / chapter prose file exists in the bundle, so NotebookLM has no retrievable text underneath the framing prompt. Hosts will improvise the chapter from the framing alone. | Generate `01-source.md` containing the full chapter prose in the project's articulation style (paragraph prose, Arabic in script with English first, no italics/bold, Q\|Surah:Verse citations on their own lines if any). Source it from the chapter contract or the canonical chapter file on the `book/the-master-and-the-disciple` branch. |
| P0 | `02-key-passages.md` | `### Passage 1` | File contains only a literal `> >` blockquote shell and an `[LLM-FILL]` "Why this matters" line — zero passages. The discussion spine's anchor instructions ("reference passage N from `02-key-passages.md`") therefore point at nothing. | Populate at least 8 verbatim passages drawn from the chapter, one per spine beat plus one for the recurring thesis. Required minimum set: the fire-is-hot figure, the four-letters exchange, the *causes between Him and His creation* derivation, the four-nations indictment, the three-qualities argument, the prophets-count sequence (Abraham→Moses, Moses→Jesus), the *Moses fleeing to Shu'ayb* paradigm, *Had you supported the friends of Allah…* thesis (verbatim), *were it not for the narrations of the jurists…*, the closing doxology + *no power and no strength except by Allah the Almighty*. Each passage: blockquoted prose + one sentence on why it matters. |
| P1 | `03-context-pack.md` | `## Author / narrator` … `## Related works` | Every field is an `[LLM-FILL]` placeholder. Hosts have no author identification, no chapter-position context, no tradition framing, no prior-chapter handoff (the chapter 5 zero-point seam-question). | Fill in: author = the tenth-century Yemeni author (use the stable label from framing, do NOT voice his Arabic name); "What this chapter is responding to" = chapter 5's collapse of the senior scholar's Sharia-equals-religion identification and her seam-question *the attribute is preferable to him; so how is it described?*; "Tradition / lineage" = a single sentence locating the chapter inside its tradition; "Related works" = leave deliberately empty per the anti-noise / self-contained-episode rule. |
| P0 | `04-discussion-spine.md` | every `### Beat N` block | The hidden steering layer is entirely unbuilt — 8 beats, every key-question / tension / anchor-passage / landing is `[LLM-FILL]`. Without a real spine, the framing's six-beat dramatic arc has nothing to steer the hosts through. | Rebuild the spine from scratch to **match framing's six-beat arc** (not the template's eight). Beats: 1 The crisis, 2 The first failed answer (creed-without-meaning, fire-is-hot, four-letters), 3 The second failed answer (no-prophet-after, four-nations, three-qualities), 4 The pivot (causes-between-Him-and-creation, prophet-count, recurring thesis spoken verbatim for the second time), 5 The non-bodily correction (speaker-prophet + successor as one chain, Moses-fleeing-Pharaoh, jurists-shield-the-killer indictment, *were it not for the narrations of the jurists…*), 6 Human stakes + close (recurring thesis verbatim for third time, doxology, closing formula). Each beat: one-sentence key question, one-sentence tension grounded in a specific chapter passage (NOT the literal token `>`), explicit pointer to a numbered passage in `02-key-passages.md`, one-sentence landing/residue. Delete beats 7 and 8 from the template. |
| P1 | `04-discussion-spine.md` | template header `8 beats. The hidden steering layer…` | Spine template's 8-beat shape conflicts with framing's "Six beats, in this order" arc, inviting NotebookLM to invent two extra beats that have no chapter material. | After populating the six real beats, either delete the surplus beat headers or replace the template's "8 beats" preamble with "6 beats" to match framing. |
| P0 | `99-show-notes.md` | `**Blurb:**` paragraph | Single unbroken ~1000-word paragraph for the blurb. Even if the blurb is "show-notes only," any host that browses notes-style prose will lose its breath line; well past the 400-word audio-breath threshold. | Split the blurb into 5–7 short paragraphs corresponding to the six-beat arc, with a one-line lead and a one-line landing. Strip the blurb to ~250–350 words; the show-notes blurb is not a chapter summary and should not retell the chapter. |
| P0 | `99-show-notes.md` | `**Blurb:**` — `Abu Malik (a-BOO MAA-lik)…Salih (SAA-lih)…Al-Bakhtari (al-bakh-tah-REE)` | Show notes voices the very Arabic personal names that framing's `## Stable role-labels` and `## Name discipline` blocks forbid ("Do not voice the Arabic personal names of figures. Use the English labels … every time"). The transliteration ALSO violates the articulation rule "Arabic terms in Arabic script only. Never transliterated." Directly cross-contaminates the framing's name discipline if hosts retrieve from notes. | Rewrite the blurb using only the stable English labels: "the senior scholar of the old creed" / "the senior scholar"; "the young teacher"; "the scholar-father"; "the tenth-century author". Strip every `(a-BOO MAA-lik)`-style inline phonetic from the blurb (phonetics live in the framing's `## Pronunciation` block, not in narrative prose). |
| P0 | `99-show-notes.md` | `*the use of God's names…*` …pervasive `*…*` italics | Asterisk italics used as the default emphasis device throughout the blurb. Articulation house style explicitly forbids italics. NotebookLM also treats asterisk-wrapped fragments unevenly when surfaced in retrieval. | Remove all `*…*` italic markers from the blurb. If quotation is needed, use double-quoted prose or block-quote a sentence on its own line. Re-flow the prose so emphasis comes from sentence shape, not typography. |
| P0 | `99-show-notes.md` | `(*waṣī*, /waˈsˤiː/)` … `(*ta'wīl*, /taʔˈwiːl/)` … `(*awliyāʾ*, /ʔawliˈjaːʔ/)` | Inline IPA notation will be voiced literally as a glitch (slash characters and IPA glyphs are not pronounceable). Same problem with the bracketed Arabic-script tokens mixed into English prose without the framing's "English first, Arabic in parentheses" pattern. | Delete every IPA bracket from the show notes. Where the term must appear, follow the articulation rule: English meaning first, then Arabic in Arabic script in parentheses, e.g., "the successor (وصي)". Move all phonetic guidance to `00-framing.md` `## Pronunciation` only. |
| P1 | `99-show-notes.md` | `Sharia (sha-REE-ah)` …`Sunnah` …`Qur'an` …`Taqiyya (ta-KEE-yah)` …`ta'zir (tah-ZEER)` | Transliterated Arabic technical terms embedded in English prose. Articulation rule: Arabic terms in Arabic script only, never transliterated. The parenthetical phonetic in narrative prose is also a NotebookLM glitch source. | Convert each transliterated term to the English-first / Arabic-in-parentheses form: "sacred law (شريعة)", "the Prophetic practice (سنة)", "the Qur'an (قرآن)", "protective concealment (تقية)", "discretionary chastisement (تعزير)". |
| P1 | `99-show-notes.md` | `## Related episodes` list of five chapters | Lists the five prior episodes by slug — directly contradicts framing's `## Anti-noise rules` "Treat this chapter as a self-contained episode. The hosts must NOT cross-reference other chapters of the book." If NotebookLM ingests show notes for retrieval, the list invites the very cross-reference the framing forbids. | Delete the `## Related episodes` section from `99-show-notes.md` for episodes intended to read as self-contained. If a reader-facing series-index is wanted, move it to a separate `_system/series-index.md` outside the NotebookLM upload set. |
| P2 | `99-show-notes.md` | `## References` — `> >` | References section contains only a literal `> >` blockquote shell — no references actually listed. | Either remove the `## References` heading or populate it with the one canonical reference (chapter source citation) and nothing else. |
| P2 | `99-show-notes.md` | `**Length estimate:** see contract.length_target (extended)` | Length estimate punted to a contract file, but the framing explicitly says "Target a 50 to 60 minute in-depth conversation." The show notes can carry that number directly. | Replace with "**Length estimate:** 50–60 minutes." |
| clean | `00-framing.md` | `## Opening directive` …`## Three-part focus` | Six-beat arc, opening directive, recurring thesis discipline (three verbatim placements), name discipline, banter suppression, anti-noise, three governing analogies — all explicitly stipulated. | clean |
| clean | `00-framing.md` | `## Pronunciation` | Pronunciation block lives in the steering layer, never inline in chapter prose; correct placement for an appendix-style guidance. | clean |

---

## Episode Findings

### Episode EP06 — Justice, Monotheism, and the Guardians of Allah

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `04-discussion-spine.md` | every beat | Discussion spine is entirely placeholder. There is no built spine for the hosts to follow, no required beats, no bridging tension, no anchor passages — the framing's six-beat arc has no scaffolding underneath it. | (Same fix as Chapter Findings row above — rebuild the spine to match framing's six-beat arc with real key-questions, tensions, anchor-passage references, and landings.) |
| P0 | `02-key-passages.md` | `### Passage 1` | Zero verbatim passages exist for hosts to retrieve. Framing names ~10 verbatim quotations the hosts are stipulated to voice (fire-is-hot, four-letters, four-nations indictment, prophet count, recurring thesis, *no power and no strength…*, etc.), but none are in the bundle. Hallucination risk on every quoted line is maximal. | (Same fix — populate `02-key-passages.md` with the framing-stipulated verbatim quotations.) |
| P1 | `00-framing.md` | `## Roles + positions` | Host-role assignment names Host A (male) as "the young teacher" (scholar-role) and Host B (female) as "the senior scholar of the old creed" — both hosts are scholars. Default rubric assumes male = scholar / female = student. This is an intentional debate-with-concession format, but the inversion of the student/learner default should be acknowledged so it isn't auto-corrected back by NotebookLM's voice patterns. | Add one sentence to `## Roles + positions`: "Both voices are scholar voices in this episode; the asymmetry is doctrine-held, not expertise-held. Host B carries the inherited classical creed and concedes by the close; do not soften her into a student or learner — she is a senior teacher being argued into ground she did not see." |
| clean | `00-framing.md` | `## Opening directive` last sentence | "Do not open with 'today we'll discuss' or 'welcome back'." — the skip-the-intro instruction is present. | clean |
| clean | `00-framing.md` | `## Length` | Target 50–60 minutes stated. | clean |
| clean | `00-framing.md` | `## Pronunciation` block | Pronunciation appendix present in framing, covering every Arabic term that actually appears in the chapter; framing explicitly tells hosts not to voice Arabic personal names and to refer to surahs by English meaning. | clean |
| P1 | `00-framing.md` | `## Resolution` + `## Landing` | Framing closes on a settled concession ("Host B concedes the main proposition") and the chapter's doxology — no genuine open question is left hanging. Scholarly-conversation rubric §4(e) "premature closure" applies: a closed-loop ending discourages the kind of "live disagreement still sits here" close that real scholarly conversations carry. The chapter is internal to its tradition, so this is P1 not P0. | After the doxology, add one steering line to `## Landing`: "Both hosts may, just before silence, briefly acknowledge that the concession is doctrinal — the historical question of how guardians become visible in any given age remains genuinely open, and the close does not pretend otherwise." Do not extend the audio; keep the doxology as final voiced content. |
| P2 | `00-framing.md` | `## Three-part focus` header | The section header reads "Three-part focus" but the content is a six-beat arc. The mismatch invites NotebookLM to compress to three larger beats. | Rename the heading to `## Six-beat arc` (or `## Dramatic arc — six beats`) so the structural unit matches the named focus. |
| P2 | `00-framing.md` | `## Central tensions` last paragraph | Three pushback turns for Host B are scripted verbatim. This is excellent for asymmetric engagement, but all three pushback lines come from Host B with Host A responding — Host A never genuinely concedes ANYTHING. Scholarly-conversation rubric §4(e) "no host ever concedes" applies to Host A specifically. | Add one steering line: "Engineer ONE moment where Host A concedes something to Host B — a sentence, not a beat — e.g., that the senior scholar's no-prophet-after objection is the strongest internal-case version of the inherited creed before the pivot dissolves it. The concession is rhetorical respect, not doctrinal retreat." |

---

## Cross-Bundle Patterns

The dominant pattern is **scaffold-without-substrate**: one richly built framing prompt sitting on top of three empty placeholder files and a missing primary source. The framing references the chapter file as "the entire source NotebookLM sees," but no chapter file is in the bundle's virtual filesystem, and the three retrieval-side artifacts (key passages, context pack, discussion spine) are template stubs. If NotebookLM were given only the files in the manifest, the hosts would have nothing to ground on except the framing's own quoted fragments — every doctrinal claim becomes a hallucination risk.

A secondary pattern is **name-discipline collision between framing and show notes**. The framing locks every figure to a single English label and explicitly forbids voicing Arabic personal names, transliterations, and IPA. The show notes blurb does all three repeatedly — proper names ("Abu Malik", "Salih"), transliterated technical terms ("Sharia", "Sunnah", "Taqiyya"), inline phonetic hints (`(a-BOO MAA-lik)`), and bracketed IPA (`/waˈsˤiː/`). If NotebookLM is configured to ingest show notes alongside the framing prompt, the show notes will override the framing's discipline in retrieval and the hosts will voice exactly what the framing forbids. Treat the show notes as a reader-facing artifact only and keep it out of NotebookLM's source set, or rewrite it to honor the framing.

A tertiary pattern is **structural drift inside the spine template** — its 8-beat shape doesn't match the framing's 6-beat arc, and the surplus beats are an invitation for NotebookLM to invent two extra beats. The fix is collapsing the template to 6 beats during the spine-fill, not adding two more chapter beats to fit the template.

There is **no AI-cliché smell in the framing prompt itself** — the deny-list is explicit and comprehensive (deep-dive self-reference, faux-profundity, reflexive validation, modernization terms, formal-essay transitions all forbidden), and the three governing analogies are bounded. Likewise no orientalism or essentialism issue arises because the episode is internal to its source tradition. The §4 scholarly-rubric issues that DO apply are the §4(e) premature-closure note on the Resolution block and the §4(e) "no host ever concedes" note on Host A.

---

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "01-source.md",
    "anchor": "(file does not exist — create at bundle root)",
    "severity": "P0",
    "problem": "Primary source / chapter prose file is missing from the bundle, so NotebookLM has no retrievable chapter text underneath the framing prompt.",
    "fix": "Create 01-source.md at the bundle root containing the full chapter prose for EP06 in the project's articulation style: paragraph prose only; Arabic terms in Arabic script with English-first parenthetical pairing; no italics, bold, footnotes, or postscripts; Q|Surah:Verse citations on their own line immediately after the quoted verse; stable English labels (the young teacher, the senior scholar of the old creed, the scholar-father, the tenth-century author, the Commander of the Faithful, the fourth Imam) used consistently; source content from the canonical chapter file on the book/the-master-and-the-disciple branch (content/drafts/the-master-and-the-disciple/chapters/ or the equivalent contracted path).",
    "category": "notebooklm"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "### Passage 1",
    "severity": "P0",
    "problem": "File contains only a placeholder '> >' blockquote and an [LLM-FILL] note; zero verbatim passages exist for hosts to retrieve, so every quotation the framing stipulates becomes a hallucination risk.",
    "fix": "Populate with ten verbatim passages drawn from the chapter, one per the framing's required quoted moments: (1) the fire-is-hot figure, (2) the four-letters-of-Allah exchange, (3) the 'causes between Him and His creation' derivation, (4) the four-nations indictment, (5) the three-qualities argument, (6) the six-prophets-between-Abraham-and-Moses sequence, (7) the seven-prophets-between-Moses-and-Jesus sequence, (8) the Moses-fleeing-to-Shu'ayb paradigm, (9) 'were it not for the narrations of the jurists, no tyrannical king could ever be established', (10) the recurring thesis verbatim 'Had you supported the friends of Allah, they would have appeared; had you failed His enemies, they would not have prevailed' followed by the closing formula 'there is no power and no strength except by Allah the Almighty'. Each passage: numbered heading, the verbatim quote in a blockquote, one sentence under 'Why this matters' grounding it to its discussion-spine beat.",
    "category": "citation"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "## Author / narrator",
    "severity": "P1",
    "problem": "Every field is an [LLM-FILL] placeholder; hosts have no author identification, no chapter-position context, no tradition framing, no chapter-5 handoff (the senior scholar's zero-point seam-question).",
    "fix": "Fill the four sections: 'Author / narrator' = the tenth-century Yemeni author of the dialogue book (do NOT voice his Arabic name — use 'the tenth-century author' label as in framing); 'What this chapter is responding to' = chapter 5's collapse of the senior scholar's identification of religion with the sacred law of her age, ending on her seam-question 'the attribute is preferable to him; so how is it described?' which chapter 6 answers by pulling the argument into justice and monotheism; 'Tradition / lineage' = one sentence locating the chapter inside its tradition without naming personal names of figures; 'Related works' = leave deliberately empty per the framing's self-contained-episode rule, with one prose sentence explaining the deliberate emptiness.",
    "category": "cohesion"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 1: Opening hook",
    "severity": "P0",
    "problem": "Spine is entirely placeholder — all eight beats are [LLM-FILL] and the eight-beat template shape conflicts with the framing's locked six-beat arc; without a built spine the framing's beat instructions are orphaned and NotebookLM will improvise.",
    "fix": "Rebuild the spine from scratch to match the framing's six-beat arc and delete beats 7 and 8 from the template entirely. The six beats: 1 The crisis (open inside the senior scholar's zero-point and the seam-question); 2 The first failed answer (creed-without-meaning, fire-is-hot, four-letters); 3 The second failed answer (no-prophet-after objection, four-nations indictment, three-qualities); 4 The pivot (causes-between-Him-and-creation derivation, prophet-count exactness, recurring thesis spoken verbatim for the second time); 5 The non-bodily correction (speaker-prophet + successor as one chain, Moses-fleeing-Pharaoh paradigm, jurists-shield-the-killer indictment, 'were it not for the narrations of the jurists…'); 6 The human stakes + the unresolved question (recurring thesis verbatim for the third time, then doxology, then closing formula). For each beat: one-sentence key question grounded in the chapter, one-sentence tension that quotes or names a specific chapter passage (NEVER the literal token '>'), an explicit pointer like 'reference Passage N from 02-key-passages.md' tied to the numbered passages created in the 02-key-passages fix, and one-sentence landing/residue. Also change the file's preamble line '8 beats. The hidden steering layer…' to '6 beats. The hidden steering layer…'.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P0",
    "problem": "The blurb is a single unbroken ~1000-word paragraph, well past the 400-word audio-breath threshold and also far too long for a show-notes blurb — it re-tells the chapter rather than introducing it.",
    "fix": "Cut the blurb to ~250–350 words and split into 5–7 short paragraphs corresponding to the six-beat arc. Each paragraph: one lead sentence + at most two follow-on sentences. The blurb introduces the episode for a reader scanning notes; it does not retell the chapter and does not quote verbatim passages.",
    "category": "length"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Chapter five ended on Abu Malik (a-BOO MAA-lik)",
    "severity": "P0",
    "problem": "The blurb voices the very Arabic personal names that 00-framing.md's Stable role-labels block forbids ('Abu Malik', 'Salih', 'Al-Bakhtari'), with inline phonetic hints like '(a-BOO MAA-lik)' embedded in narrative prose; this directly cross-contaminates the framing's name discipline if hosts retrieve from notes.",
    "fix": "Rewrite the blurb using only the stable English labels from 00-framing.md: 'the senior scholar of the old creed' (then 'the senior scholar'), 'the young teacher', 'the scholar-father', 'the tenth-century author', 'the Commander of the Faithful' (with the honorific spoken once at first mention only, never paired with the personal name of the Father of Imams), 'the fourth Imam'. Strip every parenthetical phonetic hint of the form '(a-BOO MAA-lik)' from the blurb — phonetics live in 00-framing.md ## Pronunciation only.",
    "category": "host-role"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "*the use of God's names without knowing His Oneness*",
    "severity": "P0",
    "problem": "Asterisk italics are used as the default emphasis device throughout the blurb (dozens of *…* fragments); articulation house style explicitly forbids italics and NotebookLM retrieval handles asterisk-wrapped fragments unevenly.",
    "fix": "Remove every '*…*' italic marker from the blurb. Where a quoted phrase is needed, use double-quoted prose inline or pull the phrase onto its own line as a short blockquote. Re-flow the prose so emphasis comes from sentence shape, not typography.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "(*waṣī*, /waˈsˤiː/, the successor",
    "severity": "P0",
    "problem": "Inline IPA notation '/waˈsˤiː/', '/taʔˈwiːl/', '/ʔawliˈjaːʔ/' will be voiced literally by NotebookLM as audible glitches (slash characters and IPA glyphs are not pronounceable as speech).",
    "fix": "Delete every IPA-bracket fragment from 99-show-notes.md. Where the term must appear in the blurb, follow the articulation rule: English meaning first, then the Arabic term in Arabic script in parentheses, e.g., 'the successor (وصي)', 'the esoteric interpretation (تأويل)', 'the guardians of Allah (أولياء)'. All phonetic guidance lives in 00-framing.md ## Pronunciation only.",
    "category": "pronunciation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Sharia (sha-REE-ah)",
    "severity": "P1",
    "problem": "Transliterated Arabic technical terms ('Sharia', 'Sunnah', 'Qur'an', 'Taqiyya', 'ta'zir', 'da'wa', 'nāṭiq', 'ḥawl', 'quwwa', 'ḥujja', 'bāb') are embedded in English prose throughout the blurb; the articulation rule requires Arabic in Arabic script only, never transliterated.",
    "fix": "Convert each transliterated term to English-first / Arabic-in-parentheses form: 'sacred law (شريعة)', 'Prophetic practice (سنة)', 'the Qur'an (قرآن)', 'protective concealment (تقية)', 'discretionary chastisement (تعزير)', 'the call (دعوة)', 'the speaker-prophet (ناطق)', 'the turning (حول)', 'the strength (قوة)', 'the proof (حجة)', 'the gate (باب)'. Strip the parenthetical phonetic spellings ('(sha-REE-ah)', '(ta-KEE-yah)', '(tah-ZEER)', '(DAH-wah)', '(NAA-tiq)') — they belong in 00-framing.md ## Pronunciation only.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "## Related episodes",
    "severity": "P1",
    "problem": "Show notes lists five prior episodes by slug, directly contradicting 00-framing.md ## Anti-noise rules 'Treat this chapter as a self-contained episode. The hosts must NOT cross-reference other chapters of the book.' If NotebookLM ingests show notes, the cross-reference list invites the very cross-reference the framing forbids.",
    "fix": "Delete the entire '## Related episodes' section from 99-show-notes.md. If a series-index is wanted for reader navigation, move it to a separate file under content/drafts/the-master-and-the-disciple/_system/series-index.md that is NOT part of the NotebookLM upload bundle.",
    "category": "duplication"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "## References",
    "severity": "P2",
    "problem": "References section contains only a literal '> >' blockquote shell with no references actually listed.",
    "fix": "Either remove the '## References' heading entirely, or populate it with the single canonical reference — the chapter source citation on the book/the-master-and-the-disciple branch — and nothing else.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Length estimate:** see contract.length_target (extended)",
    "severity": "P2",
    "problem": "Length estimate punts to a contract file, but 00-framing.md states 'Target a 50 to 60 minute in-depth conversation' directly.",
    "fix": "Replace the line with '**Length estimate:** 50–60 minutes.'",
    "category": "length"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Roles + positions",
    "severity": "P1",
    "problem": "Both Host A and Host B are scholar voices in this episode (young teacher vs senior scholar of the old creed); the inversion of the default male-teacher / female-learner pattern is intentional but not made explicit, so NotebookLM's voice patterns may auto-soften Host B into a student/learner register.",
    "fix": "Append one sentence to the end of ## Roles + positions: 'Both voices are scholar voices in this episode; the asymmetry is doctrine-held, not expertise-held. Host B carries the inherited classical creed and concedes by the close — do not soften her into a student or learner. She is a senior teacher being argued into ground she did not see.'",
    "category": "host-role"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Resolution",
    "severity": "P1",
    "problem": "Episode closes on a settled doctrinal concession plus the chapter's doxology — no genuine open question is left hanging. Scholarly-conversation premature-closure smell: real scholarly conversations carry a 'live disagreement still sits here' note even when one position concedes.",
    "fix": "Add one steering line to ## Landing immediately before 'Both hosts then go silent.' that reads: 'Just before silence, both hosts may briefly acknowledge that the concession is doctrinal — the historical question of how guardians become visible in any given age remains genuinely open, and the close does not pretend otherwise.' Do not extend the audio time budget; the doxology remains the final voiced content.",
    "category": "spine"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Three-part focus",
    "severity": "P2",
    "problem": "The section header reads '## Three-part focus' but the content is a six-beat arc; the heading-content mismatch invites NotebookLM to compress the arc to three larger beats.",
    "fix": "Rename the heading from '## Three-part focus' to '## Six-beat arc' (or '## Dramatic arc — six beats') so the structural unit named in the heading matches the six beats actually stipulated underneath.",
    "category": "spine"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Central tensions",
    "severity": "P2",
    "problem": "Three pushback turns are scripted verbatim for Host B with Host A always responding; Host A never genuinely concedes anything. Scholarly-conversation 'no host ever concedes' smell applies asymmetrically to Host A.",
    "fix": "Append one steering line to ## Central tensions: 'Engineer ONE moment where Host A concedes something to Host B — a sentence, not a beat — naming, for instance, that the senior scholar's no-prophet-after objection is the strongest internal-case version of the inherited creed before the pivot dissolves it. The concession is rhetorical respect, not doctrinal retreat.'",
    "category": "spine"
  }
]
```
