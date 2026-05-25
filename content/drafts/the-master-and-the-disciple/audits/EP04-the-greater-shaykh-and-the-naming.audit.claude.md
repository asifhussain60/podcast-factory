## Inventory

- **EP04 — The Greater Shaykh and the Seventh-Day Naming** (bundle root `EP04-the-greater-shaykh-and-the-naming/`)
  - Framing (`00-framing.md`): present, substantive
  - Primary source (`01-source.md`): **MISSING**
  - Key passages (`02-key-passages.md`): stub only — body is `> >` and `*Why this matters:* [LLM-FILL]`
  - Context pack (`03-context-pack.md`): present but ALL fields are `[LLM-FILL]` placeholders
  - Discussion spine (`04-discussion-spine.md`): present but ALL 8 beats are `[LLM-FILL]` placeholders
  - Show notes (`99-show-notes.md`): present, substantive

## Chapter Findings

### Chapter EP04: The Greater Shaykh and the Seventh-Day Naming

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `00-framing.md` | `## Background` | Framing asserts "the chapter file is the entire source," but no `01-source.md` exists in the bundle — NotebookLM will hallucinate the entire chapter from framing alone. | Author `01-source.md` containing the full verbatim chapter text (the re-birth chapter from *Kitab al-ʿAlim wa-l-Ghulam*) before NotebookLM ingestion. |
| P0 | `02-key-passages.md` | `### Passage 1` | File contains only `> >` and `*Why this matters:* [LLM-FILL]`. The retrieval layer is empty; hosts will paraphrase or invent every quoted passage. | Populate verbatim quotes the framing explicitly demands: the announcement, the brotherly recognition, the doxology on justice-as-middle, the chain-of-rights, the full naming dialogue, the veiled-transmission disclosure, the Hajj-by-the-great-sign figure, the eight-clause blessing, the five negatives, the six qualities, the interpretation key, and the closing line *then his father came to him, angry*. Each with a `*Why this matters:*` line tying it to a specific beat. |
| P0 | `03-context-pack.md` | `## Author / narrator` | All four populated headings remain `[LLM-FILL]` — hosts have no grounding for tradition, author, or related works and will fabricate. | Fill all four headings using the framing's own `## Background` paragraph plus the source-tradition (Ismaili, tenth-century Fatimid Yemen) and lineage placement. |
| P0 | `04-discussion-spine.md` | `### Beat 1: Opening hook` | The entire steering layer is `[LLM-FILL]` placeholders — NotebookLM has no beat structure, no anchor passages, no landings. The episode WILL drift. | Author all beats with explicit key-question / tension / anchor-passage / landing fields, drawn directly from framing's `## Three-part focus`. |
| P0 | `04-discussion-spine.md` | Beat count | Spine declares **8 beats** but framing's `## Three-part focus` declares **6 beats** ("Six beats walking the chapter in narrative order. Each beat lands once and only once. Do not double back; do not jump forward."). Direct contradiction — whichever NotebookLM follows, the other is violated. | Rewrite spine to exactly **6 beats** matching framing: (1) Yellowing and announcement, (2) Council and brotherly recognition, (3) Two opening discourses, (4) Seventh-day naming dialogue (pivot), (5) Seventh day, veiled transmission, inner pilgrimage, (6) Farewell, interpretation key, unresolved close. Remove Beats 7 and 8. |
| P0 | `99-show-notes.md` | `**Blurb:**` | Show-notes blurb voices the forbidden full Arabic personal name *Ubayd Allah, son of Abd Allah* OUTSIDE the framing's permitted window (framing locks this name to the Beat-4 verbatim quote ONLY; before and after, "refer to the figure as the seeker"). If NotebookLM is given this blurb, the name leaks. | Replace the two instances of *Ubayd Allah, son of Abd Allah* in the blurb with *the seeker* (or *the youth*). The name appears once only, inside the quoted naming-dialogue exchange. |
| P1 | `99-show-notes.md` | `**Blurb:**` | Pervasive transliterated Arabic — *Kitab al-ʿAlim wa-l-Ghulam*, *da'wa*, *batin*, *ihram*, *Shaykh*, *Hajj*, *Sa'd*, *Ubayd Allah*, *Abd Allah*. Articulation rule: Arabic terms in Arabic script only, never transliterated; English first with Arabic in parentheses. | Convert all transliterated terms to either English-only (the chain, the call, the innermost inward, the consecrated state, the elder, the pilgrimage) or English-with-Arabic-script-parenthetical for the first mention of canonical terms (the inner [الباطن], pilgrimage [الحج]). |
| P1 | `99-show-notes.md` | `**Blurb:**` | Heavy italic emphasis across dozens of phrases (*yellowed*, *seventh-day naming*, *greater Shaykh*, *highest transmission*, etc.). Articulation rule: no bold, no italics. | Strip all `*...*` italic markup. Quotation marks for verbatim passages; plain prose for everything else. |
| P1 | `99-show-notes.md` | `**Blurb:**` | The blurb is a single ~1,000-word unbroken paragraph — NotebookLM will compress to summary and lose the seven-beat narrative. | Split into 3–4 paragraphs aligned to framing beats (announcement / council and discourses / naming and veiled transmission / farewell and unresolved close). |
| P1 | `00-framing.md` | `## Pronunciation` | The framing carries pronunciation directives inline in prose form, but no separate, retrievable pronunciation appendix exists in the bundle for the spoken-form citations the framing demands the hosts produce. NotebookLM will mis-voice *ihram*, *Sa'd*, *Hajj* without an explicit map. | Add a `## Pronunciation appendix` block (or `06-pronunciation.md`) mapping each term to its phonetic spelling exactly as framing already supplies: Quran → qur-AAN; Sinai → SEE-nigh; Hajj → HAJ; ihram → ih-RAAM; Sa'd → SAHD; Ubayd Allah → oo-BAYD ah-LAH; Abd Allah → AB-d ah-LAH. Reference from `00-framing.md`. |
| P1 | `99-show-notes.md` | `## References` | References field is `>` placeholder. The blurb makes many specific source claims; hosts will be unable to ground them. | Replace `>` with the actual citation list (chapter, edition, translator) for *Kitab al-ʿAlim wa-l-Ghulam* plus the secondary works framing names (*the book "The Psalms of Islam"*, *the book "The Treatise on Rights"*, *the book "The Path of Eloquence"*). |
| P2 | `00-framing.md` | `## Host dynamic` | Pushback example #3 ("That sounds like wordplay…") opens with *That sounds like wordplay* — fine — but example #2 risks reading as a quasi-rhetorical question chain that invites NotebookLM to extend the chain rather than answer. | Tighten example #2 to a single pointed sentence; remove the trailing "Aren't you just refusing every category I offer?" rhetorical extension. |
| P2 | `00-framing.md` | `## Anti-noise rules` | Framing instructs the recurring thesis is spoken three times verbatim. The articulation rule "no claim restated more than twice" must be explicitly exempted in framing so downstream auditors do not flag it. | Add one line under `## Anti-noise rules` (R-NOREPEAT): *Exception: the recurring thesis (R-RECURRING-THESIS) is spoken three times verbatim by design and is exempt from R-NOREPEAT.* |
| P2 | `99-show-notes.md` | `## Related episodes` | Related episodes list four sibling slugs but uses kebab-case slugs not titles; if NotebookLM ever surfaces this, it reads as broken metadata. | Replace slugs with display titles (or remove the list and let the audience-facing layer render related episodes from `series-config.yaml`). |

## Episode Findings

### Episode EP04: The Greater Shaykh and the Seventh-Day Naming

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `04-discussion-spine.md` | All beats | Spine is unauthored — host-role consistency, beat completeness, format suitability cannot be checked because there is no content to check. | See chapter finding above — author all 6 beats with explicit host-role attribution (Host A scholar, Host B seeker) per framing's `## Host dynamic`. |
| P0 | `00-framing.md` | `## Host dynamic` | Host roles correctly assigned (male = scholar/teacher, female = seeker/student) and seeded with three explicit Host B pushback examples — but the spine, where these roles must be operationalized, is empty. The role assignment is stranded. | Once spine is authored, every beat must name which host opens, which pushes back, and where the three seeded pushbacks land (seam 3→4; Beat 4 naming; Beat 5 veiled transmission; Beat 6 closing). |
| P1 | `00-framing.md` | `## Length` | Length target is "50 to 60 minute in-depth conversation" but the bundle has no source file and empty spine — the host pair cannot sustain 50 min on framing alone and will pad with repetition. | Either ingest the full chapter as `01-source.md` AND author the spine, OR reduce length target to a range the populated source can actually support. Do not generate audio at this length without source. |
| P1 | `00-framing.md` | `## Opening directive` | "Skip the intro" instruction is present in functional form ("Do not open with *today we'll discuss* or *welcome back*. Start in the middle of the question.") — clean on this dimension. | clean |
| P2 | `00-framing.md` | `## Three-part focus` (Beat 5) | Veiled transmission is correctly framed as veil-honoring with explicit "may not invent content or speculate" — strong. The seam where Host B's third pushback lands ("How is this different from refusing to answer?") risks pulling Host A into specifics if the spine doesn't pre-stage Host A's permitted answer (name *what kind* of matters; name *why* the source veils). | When authoring spine Beat 5, pre-stage Host A's allowed responses to the veil-pushback: (a) name the register of matters (the innermost inward, what the source guards under pious dissimulation); (b) name the reason for the veil (doctrine, not omission); (c) point to the Hajj-by-the-great-sign figure as the chapter's signal. |
| P2 | `00-framing.md` | `## Anti-noise rules` (R-NOSURPRISE) | Framing requires "exactly one separate-prep illusion (R-SURPRISE-MOVE)" at the seventh-day rite. Without an authored spine, this directive has no anchor. | Spine Beat 5 must encode the separate-prep moment — Host B introduces the seventh-day rite image (bathing, purest garments, *the day of Sa'd*) BEFORE Host A leads toward it. |
| P2 | `00-framing.md` | `## Host dynamic` | Format declared: `deep_dive`. Appropriate for source density once source is populated. | clean |
| — | `00-framing.md` | `## Do not` | Forbidden vocabulary block present, comprehensive, includes the forbidden leadership-title/personal-name pairing rule. | clean |

## Cross-Bundle Patterns

The bundle is a **two-file episode**: `00-framing.md` (highly engineered, dense, articulation-disciplined) and `99-show-notes.md` (verbose, transliteration-heavy, italic-heavy, single-paragraph blob). The three middle artifacts — key passages, context pack, discussion spine — are scaffolds with `[LLM-FILL]` placeholders, and `01-source.md` is absent. This is the signature of a bundle where the framing author paused after `00-framing.md` and never returned to populate the retrieval and steering layers. NotebookLM will read the framing as instructions, find no source to ground them in, find no spine to follow, find no passages to quote, and synthesize the episode from the framing's *descriptions* of what should be quoted — guaranteeing fabrication. Show-notes prose violates the same articulation discipline the framing painstakingly enforces (transliteration, italics, monolithic paragraph) — the two files were written by different conventions and one must be brought into line with the other before any of this reaches NotebookLM.

A structural risk: the framing's 6-beat narrative spine and the discussion-spine file's 8-beat template directly disagree. This is not stylistic — it is a count mismatch that will cause one of the two documents to be ignored. Resolve by editing the spine file to exactly the 6 beats framing names.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "00-framing.md",
    "anchor": "## Background",
    "severity": "P0",
    "problem": "Bundle is missing 01-source.md; framing claims the chapter file is the entire source but no source artifact exists.",
    "fix": "Author 01-source.md in this bundle containing the full verbatim chapter text of the re-birth chapter from Kitab al-Alim wa-l-Ghulam (the chapter whose closing line is 'then his father came to him, angry'). Do not paraphrase; include every passage the framing and key-passages files reference.",
    "category": "cohesion"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "### Passage 1",
    "severity": "P0",
    "problem": "File body contains only an empty blockquote and an LLM-FILL placeholder; the retrieval layer is empty.",
    "fix": "Replace the stub with twelve verbatim passages drawn from 01-source.md, one per framing requirement: (1) the announcement (mercy cast into the heart of the one who has charge of him); (2) the brotherly recognition exchange (the boy we used to hear about / the one whose remembrance is sweet); (3) the doxology on justice as the middle between two extremes including the spread-out hands figure; (4) the chain of rights (thought, good manners, knowledge, action, obedience); (5) the full naming dialogue from name-asked through 'how can a thing know that which has no name' to 'until the completion of seven days, for the dignity of the newborn'; (6) the recurring thesis 'the name belongs to you, and you belong to the name. So it does not appear except within your limit, and it travels with your duration'; (7) the seventh-day preparation (bathing, purest garments, the day of Sa'd); (8) the veiled-transmission disclosure (matters upon which no fancy had ever descended); (9) the Hajj-by-the-great-sign figure; (10) the eight-clause blessing; (11) the five negatives on the father; (12) the interpretation key (whatever in it is praiseworthy is like the truth and its people). Each passage block must end with a *Why this matters:* line that names the framing beat it anchors.",
    "category": "cohesion"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "## Author / narrator",
    "severity": "P0",
    "problem": "All four populated headings are LLM-FILL placeholders; the hosts have no grounding context.",
    "fix": "Populate Author/narrator with the attribution from framing (tenth-century Fatimid Yemen, attributed by long tradition to a son of one of the great Yemeni callers of the founding generation), What this chapter is responding to with the chapter-three deferral on the Imam's permission and the chapter's positioning as the chapter of initiation, Tradition/lineage with the Ismaili tariqah and the early Ismaili da'wa context expressed in the framing's English vocabulary (the call, the chain, the inner interpretation), and Related works with the three companion books framing names (the book of psalms, the book of the treatise on rights, the book of the path of eloquence). Leave 'Why this lands now' as marked not-required.",
    "category": "cohesion"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 1: Opening hook",
    "severity": "P0",
    "problem": "All eight beats are LLM-FILL placeholders; the steering layer NotebookLM follows is empty.",
    "fix": "Rewrite the file as exactly 6 beats matching framing's three-part focus (delete Beat 7 and Beat 8). For each beat, populate Key question, Tension (drawn from the named passage in 02-key-passages.md), Anchor passage (reference passage N from 02-key-passages.md), and Landing. Beat 1 anchors to the announcement; Beat 2 to the brotherly recognition; Beat 3 to the chain of rights and justice-as-middle; Beat 4 (pivot) to the full naming dialogue and the recurring thesis (second VERBATIM utterance lands here); Beat 5 to the veiled transmission and the Hajj-by-the-great-sign figure with explicit veil-honoring guard; Beat 6 to the eight-clause blessing, interpretation key, recurring thesis (third VERBATIM utterance), and closing line 'then his father came to him, angry'. Each beat names which host opens and where the seeded Host B pushbacks land.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 7",
    "severity": "P0",
    "problem": "Spine declares 8 beats but framing declares exactly 6 beats; the count contradicts framing's 'each beat lands once and only once. Do not double back; do not jump forward'.",
    "fix": "Delete Beat 7 and Beat 8 entirely. Rename the existing 'Beat 8: Landing' content (closing on a question or unresolved tension) into the Beat 6 Landing field. The spine ends at Beat 6.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P0",
    "problem": "Blurb voices the full Arabic personal name 'Ubayd Allah, son of Abd Allah' outside framing's permitted Beat-4 verbatim-quote window; framing locks this name to that single moment and requires 'the seeker' before and after.",
    "fix": "Find both instances of 'Ubayd Allah, son of Abd Allah' in the blurb and replace each with 'the seeker'. The name appears nowhere in the show-notes blurb.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "Blurb is saturated with transliterated Arabic (Kitab al-Alim wa-l-Ghulam, da'wa, batin, ihram, Shaykh, Hajj, Sa'd) violating the articulation rule that Arabic appears in Arabic script only, with English translation preceding when used.",
    "fix": "Replace every transliterated Arabic term in the blurb with its English equivalent from the framing's `## Stable role-labels` and `## Tone constraints`: Kitab al-Alim wa-l-Ghulam → the book 'The Master and the Boy'; da'wa → the call or the method of the call; batin → the inner or the innermost inward; ihram → the consecrated state; Shaykh → the elder of the chain (first mention) then the elder or the master of the house; Hajj → the pilgrimage; Sa'd → leave inside the verbatim quote 'the day of Sa'd, and the guardian of Sa'd' only. Imam → the fourth Imam to whom the supplications are attributed (first mention) then the same Imam.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "Blurb uses pervasive italic emphasis (`*yellowed*`, `*seventh-day naming*`, `*greater Shaykh*`, dozens of others) violating articulation rule 'no bold, no italics'.",
    "fix": "Strip every `*...*` italic pair from the blurb. For verbatim quoted passages, use straight quotation marks. For emphasis, rely on word choice and sentence order — no markup.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "Blurb is a single unbroken ~1,000-word paragraph; NotebookLM will compress it to a summary, losing the chapter's six-beat narrative shape.",
    "fix": "Split the blurb into four paragraphs aligned to framing beats: paragraph 1 covers the yellowing and the announcement (Beats 1-2); paragraph 2 covers the two opening discourses (Beat 3); paragraph 3 covers the naming dialogue and the seventh-day deferral (Beat 4); paragraph 4 covers the veiled transmission, the inner pilgrimage, the farewell with eight-clause blessing and interpretation key, and the unresolved close on the father's anger (Beats 5-6). One blank line between paragraphs.",
    "category": "notebooklm"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P1",
    "problem": "Pronunciation directives are buried in prose inside framing; no retrievable appendix exists that NotebookLM can surface when it encounters Arabic terms in source.",
    "fix": "Add a new file 06-pronunciation.md in this bundle containing a clean map: 'Quran → qur-AAN', 'Sinai → SEE-nigh', 'Hajj → HAJ', 'ihram → ih-RAAM', 'Sa'd → SAHD', 'Ubayd Allah → oo-BAYD ah-LAH', 'Abd Allah → AB-d ah-LAH'. One term per line. Reference this file from 00-framing.md '## Pronunciation' section with a single sentence: 'See 06-pronunciation.md for the spoken-form map.'",
    "category": "pronunciation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "## References",
    "severity": "P1",
    "problem": "References field is a placeholder `>`; the blurb makes specific quoted claims that need source attribution.",
    "fix": "Replace the placeholder `>` with the actual reference list: the edition and translator of Kitab al-Alim wa-l-Ghulam used as source; the book 'The Psalms of Islam' (al-Sahifa al-Sajjadiyya) edition; the book 'The Treatise on Rights' (Risalat al-Huquq) edition; the book 'The Path of Eloquence' (Nahj al-Balagha) edition — each by title and translator only, with no transliteration of the Arabic titles in the visible field.",
    "category": "citation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Anti-noise rules",
    "severity": "P2",
    "problem": "Framing engineers three verbatim utterances of the recurring thesis but the anti-noise rule (R-NOREPEAT) elsewhere caps any claim at two restatements; downstream auditors will flag this engineered exception as a violation.",
    "fix": "Append one sentence to the `## Anti-noise rules` R-NOREPEAT line: 'Exception: the recurring thesis (R-RECURRING-THESIS) is spoken three times verbatim by design — at the open, at the Beat 4 pivot, and at the close in Landing — and is the sole exempt repetition.'",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Host dynamic",
    "severity": "P2",
    "problem": "Pushback example #2 ('That sounds like wordplay...') ends with a rhetorical-question chain ('Aren't you just refusing every category I offer?') that risks inviting NotebookLM to extend the chain rather than letting Host A answer.",
    "fix": "Trim example #2's trailing sentence. Keep: 'That sounds like wordplay. If the seeker is not the servant-name, is not free, and cannot be newborn, what is he ACTUALLY?' End there.",
    "category": "host-role"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "## Related episodes",
    "severity": "P2",
    "problem": "Related-episodes list shows kebab-case slugs (the-call-and-the-covenant, will-command-and-the-seven, etc.) rather than display titles; if surfaced verbatim by NotebookLM or by any downstream reader, reads as broken metadata.",
    "fix": "Either replace each slug with its display title (e.g., 'EP01 — The Call and the Covenant'), or remove the `## Related episodes` block entirely and rely on series-config.yaml to render related-episode links in the audience layer.",
    "category": "format"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Length",
    "severity": "P1",
    "problem": "Length target is 50-60 minutes but the bundle currently has no source, no key passages, and no spine — the hosts cannot sustain 50 minutes on framing instructions alone and will pad or hallucinate.",
    "fix": "Do not submit this bundle to NotebookLM until 01-source.md is authored, 02-key-passages.md is fully populated with the twelve passages listed above, and 04-discussion-spine.md is rewritten to the six framing-aligned beats. After those three fixes, the length target is supportable; before them, generation will fail.",
    "category": "length"
  }
]
```
