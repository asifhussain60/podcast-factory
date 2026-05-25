## Inventory

- **EP03 — World, Hereafter, and the Right of Wealth** (Chapter 3 of *The Master and the Disciple*)
  - `00-framing.md` — present, complete (22.5 KB, six-beat walk, host roles, pronunciation, tone, anti-noise, forbidden vocabulary)
  - `01-source.md` — **MISSING** (primary source artifact not in bundle)
  - `02-key-passages.md` — present but **stub-only** (185 bytes, no actual passages, single `[LLM-FILL]`)
  - `03-context-pack.md` — present but **stub-only** (all five sections are `[LLM-FILL]`)
  - `04-discussion-spine.md` — present but **stub-only** (all 8 beat scaffolds are `[LLM-FILL]`)
  - `99-show-notes.md` — present, complete blurb + related-episode list

## Chapter Findings

### Chapter 3: World, Hereafter, and the Right of Wealth

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | 01-source.md | (file absent) | The primary source artifact for this chapter is missing from the bundle. NotebookLM has nothing to summarize; the entire chapter walk cannot anchor to verbatim source text. | Create `01-source.md` containing the full chapter text in the house articulation style (prose, Arabic in parentheses next to English equivalents, Quran citations as `Q|Surah:Verse`). Without it, the bundle is unusable. |
| P0 | 02-key-passages.md | `### Passage 1` | The key-passages file is a single empty `>` blockquote with one `[LLM-FILL]` rationale. Every beat in the framing demands verbatim quotes (pair-question, three-houses, sower-and-plant, rope exchange, dropped inner interpretation, inward of Pharaoh's dream, two verdicts, two-eyes aphorism, archer-figure, Quranic warrant, golden rule, wealth-rule, fifth, five-share enactment, refusal, description-of-the-generous-one, deferral) and there is nothing for hosts to retrieve. | Populate at least 17 passages corresponding to the framing's verbatim list. Each passage = blockquote of the source text + a one-line "Why this matters" pointing to the beat number. |
| P0 | 03-context-pack.md | `## Author / narrator` | Every section is `[LLM-FILL]`. Hosts have zero grounding for author identity, dialogue tradition, tenth-century Yemeni Ismaili setting, or related works. Grounding-blindness will push hosts toward generic "Islamic mysticism" hallucination. | Fill `## Author / narrator` with the tenth-century Yemeni Ismaili attribution; `## What this chapter is responding to` with the cosmology-to-ethics bridge function; `## Tradition / lineage` with the early Fatimid Ismaili da'wa context (Ismaili tradition, internally-qualified); `## Related works` with the chapter's place in the book and the apparatus figures (Walker, Halm, Daftary, Hollenberg, Corbin); leave `## Why this lands now` as the framing already notes ("[Not required for this adaptation mode]"). |
| P0 | 04-discussion-spine.md | `### Beat 1: Opening hook` | Every beat is `[LLM-FILL]`. The framing declares SIX beats; the spine scaffolds EIGHT. The steering layer is non-existent and structurally misaligned with the framing. | Rewrite the spine as a six-beat walkthrough matching the framing exactly: (1) Pairs that point; (2) Three houses, three knowledges, limit of teaching; (3) The rope and the two dropped inner interpretations; (4) Two eyes, two verdicts, Master's tears; (5) One creation, many passions, body and wealth; (6) Five shares, Imam first named, deferral at the door. Fill every Key question / Tension / Anchor passage / Landing. Drop Beats 7–8. |
| P1 | 99-show-notes.md | `**Blurb:**` | Blurb voices Arabic concept words extensively (nāṭiqs, ta'wīl, hawl, hujja, bāb, ʿuṣba, batin, zakat, awliyāʾ, al-Khidr) and an Arabic book title (*Kitab al-'Alim wa-l-Ghulam*) and an Arabic formula (*la hawla wa la quwwata illa billah*). The framing's concept-word and naming discipline says these convert to English equivalents (speakers, inner interpretation, year-turning figure, argument, door, band, inward, purification-due, guardians, immortal green-clad guide). If show notes are displayed or read aloud, the discipline is broken on the listener-facing surface. | Replace each Arabic term with its house English equivalent: nāṭiqs → speaker-prophets; ta'wīl → inner interpretation; hawl/quwwa → year-turning figure / power; hujja → argument; bāb → door; ʿuṣba → band; batin → inward; zakat → purification-due; awliyāʾ → guardians; al-Khidr → the immortal green-clad guide; *la hawla wa la quwwata illa billah* → the formula every believer utters (*there is no power except in Allah*). Drop the romanized book title; use *the book "The Master and the Disciple"*. |
| P1 | 99-show-notes.md | `**Blurb:**` | Blurb uses "God" several times ("causes of God", "between God and", "the rope of Allah" once but "God" elsewhere). Articulation rule mandates "Allah". | Replace every "God" with "Allah" in the blurb. |
| P1 | 99-show-notes.md | `Q 4:69` | Citation appears as `Q 4:69` (space form), not the locked `Q|Surah:Verse` form on a new line immediately following the verse. | Reformat as `Q|4:69` on a line of its own immediately after the quoted warrant ("whoever obeys Allah and His Messenger…"). |
| P1 | 99-show-notes.md | `**Blurb:**` | One-paragraph blurb runs ~900 words without any segmentation. For show-notes prose (reader-facing) this is dense; if NotebookLM ingests it as context, the lack of natural breath points encourages summarization. | Segment into 3–4 prose paragraphs at natural seams: pair-question → three houses, rope → two dropped inner interpretations, two-eyes → ethics → wealth, five-share enactment → deferral. No headings inside the blurb; paragraph breaks only. |
| P2 | 00-framing.md | `**Episode format:**` | Framing describes the episode as "in-depth walkthrough" but does NOT declare which NotebookLM Audio Overview format (Deep Dive / Brief / Critique / Debate) the bundle targets. | Add an explicit line under `**Episode format:**`: "NotebookLM Audio Overview format: **Deep Dive**, Length: **Long**." Justification: six-beat 50–60-minute walkthrough with exposition + friction maps cleanly to Deep Dive at Long. |
| P2 | 00-framing.md | `## Pronunciation` | The pronunciation block is well-built for terms in the framing, but show notes voices additional Arabic terms (al-Khidr, ʿuṣba, batin) that have no pronunciation entry. Once show notes Arabic is converted to English (per the P1 fix above), this collapses; flagging defensively in case any Arabic survives. | After the show-notes Arabic→English conversion, audit the pronunciation appendix once more to confirm no Arabic remains anywhere in voiced or ingested artifacts. |
| - | 00-framing.md | (cohesion, articulation, NotebookLM-readability) | clean — single thesis, six-beat narrative spine, host roles fixed, recurring formula gated to three verbatim utterances, anti-noise + forbidden vocabulary lists present, pronunciation appendix complete for in-framing terms, banter suppression and anti-cliché doctrine present. | clean |

## Episode Findings

### Episode 3: World, Hereafter, and the Right of Wealth

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | 04-discussion-spine.md | `### Beat 1: Opening hook` | Host-role consistency cannot be seeded: spine is empty. The framing names Host A = Master/scholar (male, John), Host B = Boy/seeker (female, Hannah) and forbids rotation, but the spine never instantiates the assignment with example exchanges per beat. | When rewriting the spine, attach to each beat at least one example exchange that demonstrates the locked roles — Host A delivers the doctrinal settlement; Host B presses with the three required pushback turns at the Beat 2→3, Beat 3, and Beat 5 sites named in the framing. |
| P0 | 04-discussion-spine.md | `### Beat 8: Landing` | Spine beat count (8) contradicts framing beat count (6). NotebookLM's hosts cannot reconcile two competing structural plans; if both are ingested, the audio will drift. | Collapse the spine to six beats matching the framing's six narrative movements exactly. Renumber the closing beat as Beat 6 (Five shares, Imam first named, deferral at the door). |
| P0 | 02-key-passages.md | `### Passage 1` | Pronunciation appendix in `00-framing.md` is referenced from the framing, but every passage that needs to be voiced verbatim is missing. Hosts cannot quote what isn't there; they will paraphrase and lose the chapter's signature moves. | Populate verbatim passages first (see Chapter row above); then add a one-line note at the top of `02-key-passages.md` pointing hosts to the pronunciation appendix in `00-framing.md`. |
| P1 | 00-framing.md | `## Pronunciation` | A spoken-form citation appendix is not present even though Quran citations exist (Q|4:69 in show notes; "the chapter on the family of Imran", "the chapter on iron", "the chapter on the heights", "the chapter on women", "the chapter on the spoils of war" in framing). If `Q|4:69` is voiced literally, audio breaks. | Add a `## Citations — spoken form` block to `00-framing.md`: "Q|4:69 → 'Quran, chapter four, verse sixty-nine.'" Add a one-line note to surah-references: "Speak surah references in the chapter's English-meaning form already used in the framing; never voice the citation token." |
| P1 | 00-framing.md | `## Opening directive` | Framing forbids "today we'll discuss" / "welcome back" but does not contain an explicit "Skip the intro" instruction that NotebookLM hosts recognize. Without it the default voices typically burn 60–90 seconds on context-setting. | Add a sentence under `## Opening directive`: "Skip the intro. Open inside the chapter's first beat — the Boy's pair-question — within the first ten seconds." |
| P1 | (cross-artifact) | (length calibration) | Framing targets 50–60 minutes (Deep Dive Long) but `01-source.md` is absent and `02-key-passages.md` is empty, so source volume cannot be verified against the target. Risk: hosts oversimplify (source too thin) or summarize (source too dense). | After source + key-passages are populated, word-count the source. Target 7,500–10,000 source words for a 50–60-minute Deep Dive Long episode; flag and resegment if outside that band. |
| P2 | 00-framing.md | `## Tone constraints` | Banter suppression is partially handled via the forbidden-first-words and forbidden-vocabulary lists, but no explicit instruction that hosts "minimize filler and avoid recap loops." | Add one sentence to `## Tone constraints`: "Hosts avoid filler interjections, do not recap what just landed, and never restate a passage after it has been named back by reference." |
| - | 00-framing.md | (single-thesis discipline, cliffhangers, host roles, role-labels, anti-noise, forbidden vocabulary, anti-repetition, surprise discipline, landing discipline, governing images) | clean — single thesis named in one sentence, no cliffhangers, locked role-labels with stable English forms, three governing images with a closed-set rule, anti-repetition and surprise-discipline rules present, landing explicitly ends on the deferral with no pre-announcement. | clean |

## Cross-Bundle Patterns

Only one bundle is in scope, but two patterns warrant flagging for the series-level operator. First, the EP03 bundle ships a fully authored `00-framing.md` paired with three placeholder artifacts (`02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`) and a missing `01-source.md`. This is a Phase 0e/0f drift signature — the framing was authored or refreshed without re-running the source + key-passages + spine + context-pack generators on the same revision. Second, `99-show-notes.md` voices Arabic concept-words and book titles that the framing has explicitly converted to English everywhere else; the show-notes file appears to have been generated against an earlier articulation policy. Both patterns will repeat across the other five episode bundles unless the regenerator is re-run.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "01-source.md",
    "anchor": "(file creation)",
    "severity": "P0",
    "problem": "Primary source artifact is missing from the bundle; NotebookLM has no source text to anchor the chapter walk.",
    "fix": "Create content/drafts/the-master-and-the-disciple/_system/episode-drafts/EP03-world-hereafter-and-the-right-of-wealth/01-source.md containing the full Chapter 3 source text in house articulation style: prose paragraphs only, Arabic terms in parentheses next to English equivalents (Prayer (صلاة) form), no bold/italics/footnotes, Quran citations as Q|Surah:Verse on their own line, 'Allah' not 'God', concept-words converted to English (speaker-prophets, inner interpretation, argument, door, year-turning figure, band, inward, guardians, immortal green-clad guide, purification-due).",
    "category": "cohesion"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "### Passage 1",
    "severity": "P0",
    "problem": "Key-passages file is a single empty blockquote with one [LLM-FILL] rationale; the framing demands 17+ verbatim passages and none are present.",
    "fix": "Replace the entire body of 02-key-passages.md with 17 numbered passages corresponding to the framing's verbatim list (pair-question, three-houses, sower-and-plant, rope exchange, dropped inner interpretation of la-hawla, inward of Pharaoh's dream, two verdicts, two-eyes aphorism, archer-figure, Quranic warrant Q|4:69, golden rule, wealth-rule, fifth-of-the-best, five-share enactment, Master's refusal, description-of-the-generous-one, deferral at the door). Each passage = source-text blockquote + one-line 'Why this matters' pointing to the beat number.",
    "category": "cohesion"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "## Author / narrator",
    "severity": "P0",
    "problem": "Every section of the context pack is [LLM-FILL]; hosts have no grounding for author, tradition, or related works, inviting generic Islamic-mysticism hallucination.",
    "fix": "Fill each section: Author/narrator = tenth-century Yemeni author, attributed by long tradition to a son of one of the great Yemeni callers. What this chapter is responding to = the cosmology-to-ethics bridge, with the Boy turning from the seven principles and the parable of the egg to the application in body, knowledge, work, and wealth. Tradition/lineage = early Fatimid Ismaili da'wa, internally-qualified (the classical Ismaili reading; not generalized to 'Islam'). Related works = the book's own surrounding chapters (call-and-covenant, will-command-and-the-seven, greater-shaykh-and-the-naming, father-revealed, justice-monotheism-and-the-guardians) plus apparatus figures Walker, Halm, Daftary, Hollenberg, Corbin. Leave 'Why this lands now' as 'Not required for this adaptation mode.'",
    "category": "cohesion"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 1: Opening hook",
    "severity": "P0",
    "problem": "All eight beats are [LLM-FILL] placeholders and the beat count (8) contradicts the framing's six-beat narrative spine.",
    "fix": "Rewrite 04-discussion-spine.md as a six-beat spine matching the framing exactly: Beat 1 Pairs that point; Beat 2 Three houses, three knowledges, limit of teaching; Beat 3 The rope and the two dropped inner interpretations; Beat 4 Two eyes, two verdicts, Master's tears; Beat 5 One creation, many passions, body and wealth; Beat 6 Five shares, Imam first named, deferral at the door. For each beat fill Key question, Tension (drawn from a real source passage in 02-key-passages.md, not the literal '>' string), Anchor passage (reference Passage N from the populated 02-key-passages.md), and Landing. Attach to each beat one example exchange that locks Host A = Master/scholar and Host B = Boy/seeker, including the three required Host B pushback turns at Beat 2→3, Beat 3, and Beat 5.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "Blurb voices Arabic concept-words (nāṭiqs, ta'wīl, hawl, hujja, bāb, ʿuṣba, batin, zakat, awliyāʾ, al-Khidr), an Arabic book title (Kitab al-'Alim wa-l-Ghulam), and the formula la-hawla-wa-la-quwwata-illa-billah; the framing converts every one of these to English.",
    "fix": "In 99-show-notes.md replace each Arabic term with its house English equivalent throughout the blurb: nāṭiqs → speaker-prophets; ta'wīl → inner interpretation; hawl → year-turning figure; quwwa → power; hujja → argument; bāb → door; ʿuṣba → band; batin → inward; zakat → purification-due; awliyāʾ → guardians; al-Khidr → the immortal green-clad guide; 'la hawla wa la quwwata illa billah' → the formula every believer utters ('there is no power except in Allah'); 'Kitab al-'Alim wa-l-Ghulam' → the book 'The Master and the Disciple'. Drop all Arabic transliteration from the blurb.",
    "category": "pronunciation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "Blurb uses 'God' multiple times ('causes of God', 'between God and the awliyāʾ'); articulation rule mandates 'Allah'.",
    "fix": "In 99-show-notes.md replace every standalone 'God' with 'Allah' in the blurb. Keep 'Allah' where it already appears.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Q 4:69",
    "severity": "P1",
    "problem": "Quran citation appears as 'Q 4:69' (space form) inline; locked citation form is 'Q|Surah:Verse' on a new line immediately following the verse.",
    "fix": "In 99-show-notes.md replace the inline 'Q 4:69' with the verse text on one line followed by 'Q|4:69' on the next line, both inside the blurb's prose flow.",
    "category": "citation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "Blurb is a single ~900-word paragraph with no natural breath points; if ingested as context this density pushes NotebookLM toward summarization.",
    "fix": "In 99-show-notes.md split the blurb into four prose paragraphs at the seams: (1) pair-question + three houses + limit of teaching, (2) rope + two dropped inner interpretations, (3) two eyes + two verdicts + ethics of body + wealth-rule, (4) five-share enactment + Imam first named + deferral at the door. Use paragraph breaks only; no headings inside the blurb.",
    "category": "notebooklm"
  },
  {
    "file": "00-framing.md",
    "anchor": "**Episode format:**",
    "severity": "P2",
    "problem": "Framing describes the episode as 'in-depth walkthrough' but does not declare the NotebookLM Audio Overview format and length setting.",
    "fix": "In 00-framing.md add a line immediately after the '**Episode format:**' paragraph: 'NotebookLM Audio Overview format: **Deep Dive**, Length setting: **Long**.' Justification line below it: six-beat 50–60-minute walkthrough with exposition + structured friction.",
    "category": "format"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Opening directive",
    "severity": "P1",
    "problem": "Framing forbids 'today we'll discuss' / 'welcome back' but lacks an explicit 'Skip the intro' instruction that NotebookLM hosts pick up; default voices typically burn 60–90 seconds on context-setting.",
    "fix": "In 00-framing.md append one sentence at the end of the '## Opening directive' paragraph: 'Skip the intro. Open inside the chapter's first beat — the Boy's pair-question — within the first ten seconds of audio.'",
    "category": "spine"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P1",
    "problem": "No spoken-form citation appendix is present even though the chapter contains Quran citations (Q|4:69) and surah references; literal voicing of 'Q|4:69' breaks audio.",
    "fix": "In 00-framing.md add a new subsection '## Citations — spoken form' immediately after '## Pronunciation' with: 'Q|4:69 → Quran, chapter four, verse sixty-nine.' Plus one sentence: 'Speak surah references in the English-meaning forms already used in the framing (the chapter on the family of Imran, the chapter on iron, the chapter on the heights, the chapter on women, the chapter on the spoils of war); never voice the citation token aloud.'",
    "category": "citation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Tone constraints",
    "severity": "P2",
    "problem": "Banter suppression is implicit via the forbidden-first-words and forbidden-vocabulary lists but lacks an explicit instruction against filler and recap loops.",
    "fix": "In 00-framing.md append to the '## Tone constraints' section one sentence: 'Hosts avoid filler interjections, do not recap what just landed, and never restate a passage after it has been named back by its short reference (the pairs, the three houses, the sower, the dropped inner interpretation, the two verdicts, the two eyes, the archers, the fifth of the best, the five shares, the deferral at the door).'",
    "category": "tone"
  }
]
```
