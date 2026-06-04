## Inventory

- **EP01 — The Master's Call and the Disciple's Covenant** (bundle root: `EP01-the-call-and-the-covenant/`)
  - `00-framing.md` — present, authored, ~21KB (the only fully authored artifact)
  - `01-primary-source.md` — **MISSING** (no chapter prose file packaged; NotebookLM has no canonical source to retrieve)
  - `02-key-passages.md` — present but **STUB** (single empty blockquote `> >` + one `[LLM-FILL]`)
  - `03-context-pack.md` — present but **STUB** (5 of 6 sections are `[LLM-FILL]` placeholders)
  - `04-discussion-spine.md` — present but **STUB** (8 beats, every field `[LLM-FILL]`; also beat-count mismatches framing's 6 beats)
  - `99-show-notes.md` — present, blurb authored; References block broken; Length-estimate is a placeholder string

## Chapter Findings

### Chapter EP01: The Master's Call and the Disciple's Covenant

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | (bundle root) | missing `01-primary-source.md` | The chapter prose itself is not packaged. NotebookLM will improvise from framing instructions alone, with no canonical text to ground retrieval. | Add `01-primary-source.md` containing the full chapter text in house-style paragraph prose (Arabic in script with English-first parenthetical form, `Q\|S:V` citations on their own line, no headings inside the prose). |
| P0 | `02-key-passages.md` | `### Passage 1` | The file contains a single empty blockquote (`> >`) and one `[LLM-FILL]`. NotebookLM will read the placeholder text as canonical retrieval material. | Author 6–10 verbatim passages from the chapter (law of thanks; praiseworthy vs. reprehensible speech; brothers and the inherited wealth; rule of work-not-flattery; five conditions; figure of the key; rope-of-God covenant; closing silence), each followed by a one-sentence `*Why this matters:*` gloss in house style. |
| P0 | `03-context-pack.md` | `## Author / narrator`, `## What this chapter is responding to`, `## Tradition / lineage`, `## Related works` | All four sections are `[LLM-FILL]` placeholders; NotebookLM ingests literal `[LLM-FILL]` strings as context. | Fill each section with one short prose paragraph in house style; use the tenth-century author label and "the early Ismaili tradition" framing already settled in `00-framing.md` so the two artifacts agree. |
| P0 | `04-discussion-spine.md` | every `### Beat N` | All 8 beats are `[LLM-FILL]` for Key question, Tension, Anchor passage, and Landing. The hidden steering layer is empty; hosts have nothing to follow. | Author the spine, reconciled to the framing's SIX beats (not 8). Each beat gets a one-sentence Key question, a Tension drawn from the chapter (not a generic frame), an Anchor passage referenced by passage number in `02-key-passages.md`, and a one-sentence Landing. |
| P1 | `04-discussion-spine.md` | template header (`8 beats`) | The spine template prescribes 8 beats while `00-framing.md` prescribes 6 (Beat 1 through Beat 6, with the R-RECURRING-THESIS landing in Beats 1, 5, 6). The structural drift will either pad the episode or duplicate beats. | Cut the spine template to 6 beats, mirroring `00-framing.md`'s `## Three-part focus` headings exactly: Beat 1 preachers' question, Beat 2 law of thanks, Beat 3 Persian wanderer, Beat 4 arrival/sermon, Beat 5 dialogue/pivot, Beat 6 five conditions/binding. |
| P1 | `99-show-notes.md` | `## References` | The References block is just `  - >`, a broken YAML/markdown fragment. NotebookLM and downstream readers see nothing useful. | Replace with a clean list of the source citations actually quoted in the chapter (the chapter file path; the cited line from *The Peak of Eloquence*; the Quran chapters by English meaning referenced in framing). |
| P1 | `99-show-notes.md` | `**Length estimate:**` line | Length-estimate is a placeholder string (`see contract.length_target (extended)`) rather than the actual minute value. | Replace with the framing's target: `**Length estimate:** 50–60 minutes`. |
| P1 | `99-show-notes.md` | `**Blurb:**` (first sentence) | Blurb uses transliterated Arabic — `Kitab al-'Alim wa-l-Ghulam`, `da'wa` — in violation of the house articulation rule (Arabic in Arabic script only, English-first with Arabic in parentheses on first mention). | Rewrite as: *The opening chapter of the book "The Master and the Disciple" (كتاب العالم والغلام) — the call (الدعوة)'s foundational dialogue …* — Arabic in script, English label first, parenthetical Arabic; never bare transliteration. |
| P1 | `99-show-notes.md` | `**Blurb:**` (recurring "the boy") | Blurb uses "Boy" and "Master-Boy dialogue" as labels for the disciple, contradicting `00-framing.md` `## Stable role-labels` which fixes the English label as "the disciple" (or, where the chapter says it, "the youth"). NotebookLM will hear label drift between framing and show-notes. | Replace every "Boy" / "the boy" / "Master-Boy" in the blurb with "disciple" / "the disciple" / "Master-disciple". One label per figure, used every time. |
| P1 | `00-framing.md` | `**Beat 3 — The Persian wanderer**`, `**Beat 4 — The Master arrives…**`, `**Beat 6 — The five conditions…**`, and quoted lines throughout | The framing uses "God" wherever the house style requires "Allah" (e.g., *God was waiting at the mirage*, *the rope of God upon His earth*, *praiseworthy speech is from God and calls to God*). Hosts will speak "God" verbatim. | Replace "God" with "Allah" throughout the framing's prose and quoted lines, EXCEPT where doing so would falsify a verbatim quote from the chapter file; in that case keep the quote as-is and document the exception in a one-line note at the top of `01-primary-source.md`. |
| P2 | `00-framing.md` | `## Background` | The chapter is treated as self-contained but the Background paragraph references "early Fatimid Yemen", "a son of one of the great Yemeni callers", and "fourteen sections of dialogue" — biographical/historical apparatus the host pair will be tempted to expand. R-NOBACKGROUND already says it appears once and never returns; consider tightening to two sentences. | Trim `## Background` to two sentences: one naming the book/century/form, one naming the chapter's role as the door. Delete the "fourteen sections" architecture detail; it invites cross-chapter narration. |
| P2 | `00-framing.md` | `## Pronunciation` | Only `Quran` and `Sinai` are listed. Hosts may still encounter terms like "Party of God", "deposit", or the *Peak of Eloquence* title in spoken context. | Expand pronunciation to cover any English phrase the hosts must say with specific stress (*"deposit" — say "de-POS-it"*, *"Peak of Eloquence" — say it as one fluent title*), and append a one-line note that no Arabic personal names or surah names are voiced. |

## Episode Findings

### Episode EP01: The Master's Call and the Disciple's Covenant

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `04-discussion-spine.md` | every `### Beat N` | Spine is entirely placeholder; no opening hook, no discussion beats, no bridging tension, no closing reflection authored. Without a populated spine, NotebookLM's hosts will not follow the framing's six-beat walk. | See chapter-findings spine-authoring fix; in addition, ensure Beat 1's Anchor passage is the law-of-thanks quote, Beat 5's Anchor passage is the recurring-thesis line, and Beat 6's Landing returns explicitly to the opening hook (recurring thesis spoken for the third time before the recitation). |
| P0 | `00-framing.md` | `## Pronunciation` (cross-cuts to the missing source) | Framing's pronunciation appendix is referenced from the framing itself, but the rule requires the appendix to live in the bundle and be referenced from the framing. Since the chapter quotes Arabic-script terms in verbatim passages (per `02-key-passages.md` once authored), an in-bundle pronunciation file is needed. | Move pronunciation entries to a new file `05-pronunciation.md` listing every Arabic-script token that will appear in `01-primary-source.md` and `02-key-passages.md` paired with a phonetic gloss (e.g., صلاة → "sa-LAH", الدعوة → "ad-DAH-wah"); reference it from `00-framing.md` `## Pronunciation` with a single line. |
| P1 | `00-framing.md` | `## Episode format` opening sentence | The framing declares "in-depth walkthrough" and "exposition with friction, not formal debate" but never names a NotebookLM Audio Overview format (Deep Dive, Brief, Critique, Debate). Generator will default-pick. | Add an explicit line at the top of `## Episode format`: `**NotebookLM format:** Deep Dive — narrative chapter walk with three scripted disciple-voice pushback turns; not Debate, because the disciple's friction resolves into the covenant rather than into a stalemate.` |
| P1 | `00-framing.md` | `## Background` (no citation-appendix reference) | No spoken-form citation appendix exists. The framing names "the chapter on Abraham", "the chapter on Livestock", "the chapter on the family of Imran" and references a line from *The Peak of Eloquence*; if any of these surface as `Q\|S:V` strings in `01-primary-source.md`, hosts will read them literally. | Create `06-citations-spoken.md` mapping every `Q\|S:V` that appears in `01-primary-source.md` and `02-key-passages.md` to its spoken form (e.g., `Q\|2:172` → "Quran, chapter two, verse one hundred seventy-two"), and reference it from `00-framing.md` `## Pronunciation` with one line. |
| P1 | `99-show-notes.md` | `## Related episodes` | Five other episodes are listed (`will-command-and-the-seven`, `world-hereafter-and-the-right-of-wealth`, etc.). `00-framing.md`'s R-NOREPEAT/R-NOBACKGROUND treats the chapter as self-contained and forbids cross-chapter narration; the related-episodes list in show-notes is fine as METADATA but must not bleed into framing context. Today the show-notes file is bundled alongside framing and NotebookLM may read it as a source. | Confirm `99-show-notes.md` is excluded from the NotebookLM source upload set (it is publish-layer metadata, not retrieval material). If it cannot be excluded, move `## Related episodes` to a separate file outside the upload bundle. |
| P2 | `00-framing.md` | `## Three-part focus` (Beat 3) | "Cite here, briefly, the line preserved in *The Peak of Eloquence* from the Father of Imams" gestures at an external citation without an `01-primary-source.md` anchor. R-NOSURPRISE will still hold, but the hosts may hallucinate the surrounding context. | After `01-primary-source.md` is authored, ensure the Father-of-Imams line is quoted there verbatim under a clearly-anchored passage, and update Beat 3 to say "Cite here, briefly, the line at *Peak of Eloquence* passage N as quoted in `02-key-passages.md`." |
| P2 | `00-framing.md` | `## Anti-noise rules` (R-WELCOME) | "Skip the intro" is enforced via R-WELCOME ("start in the middle of the question"), but the rule does not state the 60–90 second concern explicitly. Hosts may still begin with throat-clearing if the spine's Beat 1 does not open inside a quoted passage. | Add one sentence to R-WELCOME: "Open by stating Beat 1's Key question directly; do not narrate scope, do not say 'in this episode', do not preview the format." |
| clean | `00-framing.md` | `## Host dynamic` | Host-role assignment is unambiguous (male = scholar/teacher, female = disciple/learner-proxy), three pushback turns are scripted with full first-words DENY list, roles do not rotate. | clean |
| clean | `00-framing.md` | `## Central tensions` & `## Landing` | Single thesis is named once and only once, episode ends on a threshold (no preview, no recap), R-NOREPEAT is bounded to exactly three verbatim recurrences of the recurring thesis. | clean |

## Cross-Bundle Patterns

Only one bundle is in scope, so no cross-bundle pattern can be confirmed here. What is visible inside this single bundle is a sharp asymmetry between the framing (extensively authored, structurally disciplined, 21 KB of prose with stable role-labels, six-beat walk, three-pushback friction script, recurring-thesis discipline) and the four other artifacts (one stub, two near-empty, one with broken References and label drift). The risk is that NotebookLM is uploaded the entire bundle and reads `[LLM-FILL]` placeholders as canonical text — producing hallucinated content where the spine is empty and labels diverge where show-notes uses "Boy" against framing's "disciple". The corrective pattern is: author the missing primary-source file first (it grounds everything downstream), then author key-passages from it, then author the spine against those passages, then reconcile show-notes labels to the framing's stable-role-labels block, then reduce the spine from 8 beats to 6 to match `## Three-part focus`. The framing already specifies the chapter walk in narrative order at paragraph fidelity; the other artifacts must be derived from it, not authored independently.

A second pattern worth noting: the show-notes blurb is the only file that transliterates Arabic (`Kitab al-'Alim wa-l-Ghulam`, `da'wa`), against the house articulation rule of Arabic-in-script-only with English-first parenthetical. If show-notes is treated strictly as publish metadata (audience-facing on the reader app, not uploaded to NotebookLM), this is a low-severity copy fix; if it is part of the NotebookLM source upload, hosts will speak the transliteration aloud and the articulation rule fails. The boundary between bundle-for-upload and bundle-for-publish needs to be explicit in the pipeline and reflected in `framework.md`.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "01-primary-source.md",
    "anchor": "(file does not yet exist — create at bundle root)",
    "severity": "P0",
    "problem": "The chapter prose itself is not packaged in the bundle, leaving NotebookLM with no canonical source to retrieve.",
    "fix": "Create 01-primary-source.md at the bundle root containing the full chapter text in house-style paragraph prose: Arabic terms in Arabic script with English-first parenthetical form, Q|Surah:Verse citations on their own line immediately after each verse, no inline headings inside the prose, no bold or italics, no bullets.",
    "category": "cohesion"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "### Passage 1",
    "severity": "P0",
    "problem": "The file contains a single empty blockquote and one [LLM-FILL] placeholder; NotebookLM will ingest the placeholder text as retrieval material.",
    "fix": "Replace with 6 to 10 verbatim passages drawn from 01-primary-source.md, in chapter order: (1) law of thanks, (2) praiseworthy vs reprehensible speech, (3) brothers and the inherited wealth, (4) rule of work-not-flattery, (5) five conditions, (6) figure of the key, (7) rope-of-God covenant, (8) closing silence. Each passage gets a single-sentence *Why this matters:* gloss in house style.",
    "category": "cohesion"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "## Author / narrator",
    "severity": "P0",
    "problem": "Four of five sections are [LLM-FILL] placeholders; NotebookLM ingests literal [LLM-FILL] strings.",
    "fix": "Fill the Author/narrator, What this chapter is responding to, Tradition/lineage, and Related works sections with one short prose paragraph each, using the labels already settled in 00-framing.md (the tenth-century author, the early Ismaili tradition, the book 'The Master and the Disciple'). Leave 'Why this lands now' as 'Not required for this adaptation mode.'",
    "category": "cohesion"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 1: Opening hook",
    "severity": "P0",
    "problem": "All 8 beats are [LLM-FILL] for Key question, Tension, Anchor passage, and Landing — the hidden steering layer is empty and hosts have nothing to follow.",
    "fix": "Author the spine and reconcile it to the framing's SIX beats, not 8: Beat 1 preachers' question, Beat 2 law of thanks, Beat 3 Persian wanderer, Beat 4 arrival/sermon, Beat 5 dialogue/pivot, Beat 6 five conditions/binding. Each beat gets one-sentence Key question, Tension drawn from the chapter, Anchor passage referenced by number from 02-key-passages.md, and one-sentence Landing. Beat 5 must anchor the recurring thesis; Beat 6 must end on the threshold of the recitation.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "template header (currently '8 beats')",
    "severity": "P1",
    "problem": "Spine template prescribes 8 beats while 00-framing.md prescribes 6, causing structural drift that will either pad the episode or duplicate beats.",
    "fix": "Edit the template header from '8 beats' to '6 beats' and delete the placeholder Beat 7 and Beat 8 stubs entirely, so the spine matches 00-framing.md's ## Three-part focus exactly.",
    "category": "spine"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Episode format",
    "severity": "P1",
    "problem": "Framing declares 'in-depth walkthrough' but never names a NotebookLM Audio Overview format (Deep Dive, Brief, Critique, Debate), so the generator will default-pick.",
    "fix": "Add a single line at the top of ## Episode format: '**NotebookLM format:** Deep Dive — narrative chapter walk with three scripted disciple-voice pushback turns; not Debate, because the disciple's friction resolves into the covenant rather than a stalemate.'",
    "category": "format"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P0",
    "problem": "No in-bundle pronunciation appendix file exists; pronunciation lives inline in framing only. Once 01-primary-source.md and 02-key-passages.md contain Arabic-script tokens, the rule requires a dedicated appendix referenced from framing.",
    "fix": "Create 05-pronunciation.md at the bundle root listing every Arabic-script token that appears in 01-primary-source.md and 02-key-passages.md, paired with a phonetic gloss (e.g., صلاة → 'sa-LAH', الدعوة → 'ad-DAH-wah'). Replace 00-framing.md's ## Pronunciation body with a one-line reference: 'Pronunciation appendix lives in 05-pronunciation.md; consult it for every Arabic-script token before speaking.'",
    "category": "pronunciation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P1",
    "problem": "No spoken-form citation appendix exists. If Q|Surah:Verse strings appear in 01-primary-source.md or 02-key-passages.md, hosts will read them literally and the audio will sound broken.",
    "fix": "Create 06-citations-spoken.md mapping every Q|S:V citation that appears in 01-primary-source.md and 02-key-passages.md to its spoken form (e.g., 'Q|2:172' → 'Quran, chapter two, verse one hundred seventy-two'). Add a single line to 00-framing.md ## Pronunciation: 'Citation spoken-form appendix lives in 06-citations-spoken.md; consult it before voicing any Quran citation.'",
    "category": "citation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "## References",
    "severity": "P1",
    "problem": "The References block is a broken YAML/markdown fragment ('  - >'), surfacing nothing useful to the audience or to downstream parsers.",
    "fix": "Replace the References section with a clean bulleted list of the source citations actually quoted in the chapter: the chapter file path inside the book directory; the cited line from the book 'The Peak of Eloquence'; the Quran chapters by English meaning that appear in the framing (the chapter on Abraham, the chapter on Livestock, the chapter on the family of Imran).",
    "category": "cohesion"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Length estimate:**",
    "severity": "P1",
    "problem": "Length estimate is a placeholder string ('see contract.length_target (extended)') rather than the actual minute value declared in framing.",
    "fix": "Replace the line with '**Length estimate:** 50–60 minutes', matching 00-framing.md ## Length.",
    "category": "length"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:** (first sentence)",
    "severity": "P1",
    "problem": "Blurb uses transliterated Arabic ('Kitab al-'Alim wa-l-Ghulam', 'da'wa') in violation of the house articulation rule that requires Arabic in Arabic script only, English-first with Arabic in parentheses on first mention.",
    "fix": "Rewrite the opening of the blurb so every Arabic token is in script with English first: 'The opening chapter of the book \"The Master and the Disciple\" (كتاب العالم والغلام) — the call (الدعوة)'s foundational dialogue …'. Apply the same rule to every other Arabic transliteration in the blurb; do not leave bare transliterations anywhere.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:** (recurring 'the boy')",
    "severity": "P1",
    "problem": "Blurb uses 'Boy', 'the boy', and 'Master-Boy' for the disciple, contradicting 00-framing.md ## Stable role-labels which fixes the English label as 'the disciple'.",
    "fix": "Replace every occurrence of 'Boy' / 'the boy' / 'Master-Boy' in the blurb with 'disciple' / 'the disciple' / 'Master-disciple'. One label per figure, used every time.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Three-part focus",
    "severity": "P1",
    "problem": "Framing uses 'God' wherever house style requires 'Allah' (e.g., 'God was waiting at the mirage', 'the rope of God upon His earth', 'praiseworthy speech is from God and calls to God'). Hosts will speak 'God' verbatim, breaking the articulation rule.",
    "fix": "Replace 'God' with 'Allah' throughout 00-framing.md prose and quoted lines, EXCEPT where doing so would falsify a verbatim quote from 01-primary-source.md. For each exception, keep the quote as-is and document the exception in a one-line note at the top of 01-primary-source.md under a new heading '## Verbatim-quote exceptions to the Allah substitution rule'.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Background",
    "severity": "P2",
    "problem": "Background paragraph references early Fatimid Yemen, a son of one of the great Yemeni callers, and 'fourteen sections of dialogue' — biographical apparatus that invites cross-chapter narration despite R-NOBACKGROUND.",
    "fix": "Trim ## Background to two sentences: one naming the book/century/dialogue form, one naming the chapter's role as the door. Delete the 'fourteen sections of dialogue ending in the testament of the dying Master' detail; it primes the hosts to anticipate later chapters.",
    "category": "notebooklm"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Anti-noise rules (R-WELCOME)",
    "severity": "P2",
    "problem": "R-WELCOME forbids 'today we'll discuss' and 'welcome back' but does not name the 60-to-90-second default-host throat-clearing problem, leaving room for scope-narration openings.",
    "fix": "Add one sentence to R-WELCOME: 'Open by speaking Beat 1's Key question directly; do not narrate scope, do not say in this episode, do not preview the format, do not introduce yourselves.'",
    "category": "notebooklm"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "## Related episodes",
    "severity": "P2",
    "problem": "Five other episodes are listed in show-notes. If 99-show-notes.md is part of the NotebookLM source upload set, the host pair will read the related-episode slugs as canonical and break R-NOREPEAT and the self-contained-chapter rule.",
    "fix": "Confirm in the bundle's build script (scripts/podcast/extract_chapter.py or its successor) that 99-show-notes.md is EXCLUDED from the NotebookLM source upload set and lives only as publish-layer metadata. If exclusion is not possible, move ## Related episodes into a separate file outside the bundle.",
    "category": "notebooklm"
  }
]
```
