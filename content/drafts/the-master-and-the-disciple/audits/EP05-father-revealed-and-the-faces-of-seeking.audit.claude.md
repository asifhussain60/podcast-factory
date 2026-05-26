## Inventory

- **EP05 — The Father Revealed and the Three Faces of Seeking** (single chapter / single episode bundle)
  - Present: `00-framing.md` (22 KB, fully authored), `02-key-passages.md` (185 B, stub only), `03-context-pack.md` (544 B, all `[LLM-FILL]`), `04-discussion-spine.md` (2.5 KB, all `[LLM-FILL]`), `99-show-notes.md` (7.2 KB, fully authored)
  - **Missing: `01-source.md`** (the primary chapter source — declared dropped=0 in manifest, so it was never created)
  - **Effectively missing** (stub-only): `02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`
  - Pronunciation guidance: present inline inside `00-framing.md ## Pronunciation` (no separate appendix file)
  - Citation spoken-form guidance: handled by surah-name English-only directive inside `00-framing.md`; no separate citation appendix

## Chapter Findings

### Chapter 5: The Father Revealed and the Three Faces of Seeking

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `01-source.md` | (file missing) | Primary chapter source is absent from the bundle. NotebookLM has no document to retrieve from; hosts will hallucinate every passage stipulated as verbatim. The framing quotes `act on whichever of the two you wish`, `is this the reward of sons to their fathers?`, `I do not see that anything is left with me`, the three-states reasoning, the breach-in-medicine figure, and the recurring thesis — none of these have a source for NotebookLM to ground on. | Generate `01-source.md` from the corresponding chapter of the tenth-century dialogue book (the chapter answering the father's anger from Chapter 4, widening into Salih ↔ Abu Malik) as a single prose document. Keep all the verbatim lines the framing names. |
| P0 | `02-key-passages.md` | `### Passage 1` | Only one stub passage exists, with quote body `> >` (empty) and `*Why this matters:* [LLM-FILL]`. NotebookLM has no anchor quotes for the discussion spine to retrieve against. | Author 6–8 verbatim passages drawn from the chapter source, each as a block quote with a one-sentence `Why this matters` line, covering: the father's reproach, the boy's bind, the divorce-oath ruling `act on whichever of the two you wish`, the breach-in-medicine figure, the three-states reasoning, the senior scholar's confession `I do not see that anything is left with me`, the recurring thesis (`the cause that connects heaven to earth, unbroken …`), and the closing seam-question. |
| P0 | `03-context-pack.md` | `## Author / narrator` (and every other heading) | Every heading body is `[LLM-FILL]`. No author, no tradition, no what-this-answers, no related-works. Hosts have no grounding context, increasing hallucination of dates, names, and tradition claims. | Fill each section: author = the tenth-century Yemeni author of the dialogue book; tradition = classical Ismaili dialogue genre; what this chapter is responding to = the father's anger at the boy's initiation in Chapter 4, then the wider question of whether inherited fiqh alone constitutes religion; related works = Chapters 1–4 of the same book (already referenced in show-notes). Leave `Why this lands now` empty as marked. |
| P0 | `04-discussion-spine.md` | every `### Beat N` | All eight beats are `[LLM-FILL]`. The hidden steering layer NotebookLM follows is empty; the hosts will improvise an arc rather than walk the chapter's six-beat structure spelled out in `00-framing.md ## Three-part focus`. | Replace the 8-beat template with the 6-beat structure the framing prescribes (crisis → first answer → historical-temporal objection → pivot/recurring-thesis-2 → non-bodily correction / three faces → human stakes + unresolved question). For each beat, fill Key question, Tension (from the matching verbatim passage), Anchor passage (reference its number in `02-key-passages.md` once that file is authored), and Landing. Force the recurring thesis to appear in Beats 1, 4, and 6 word-for-word. |
| P1 | `00-framing.md` | `## Opening directive` | Articulation rule says no bold and no italics. The framing uses asterisk-bold for header labels (`**Episode format:**`, `**Host A …**`, `**Audience**`) and asterisk-italics for every verbatim quotation and inline directive. NotebookLM does not voice markdown emphasis but downstream linting and the house style both reject it. | Convert all `**…**` and `*…*` to plain text. Where italics carry verbatim-quote weight, wrap in double quotes instead. Where bold carries section-label weight, drop and rely on heading hierarchy. |
| P1 | `99-show-notes.md` | `**Blurb:**` | Same articulation deviation as framing: heavy italics (asterisks) on every Arabic term, every verbatim quote, and every doctrinal phrase. The entire blurb is one paragraph of roughly 1,200 words — far past the 400-word breath ceiling — and is dense with parenthetical stacking and em-dash chains, both flagged as voice-glitch risks if any portion is ingested by NotebookLM. | Rewrite the blurb as three to four short prose paragraphs (≤ 200 words each), drop all italic emphasis, and split em-dash chains into separate sentences. |
| P1 | `99-show-notes.md` | `**Blurb:**` ("the boy's name was Salih") | Show notes voice Arabic personal names with phonetics — `Salih (SAA-lih)`, `al-Bakhtari (al-bakh-tah-REE)`, `Abu Malik (a-BOO MAA-lik)`, `Ka'b al-Ahbar (KAB al-AH-bar)`, `Abu Salih (a-BOO SAA-lih)`, `Maqrub (mak-ROOB)` — directly contradicting the framing's R-NO-ARABIC-NAMES doctrine which mandates the boy, the father, the senior scholar, the petitioner, the early figure of report-without-witness. If NotebookLM ingests show-notes alongside framing the hosts will receive conflicting naming instructions. | Replace every Arabic personal name in the blurb with the framing's English stable label. Keep the meaning-of-name aside (`a name meaning the righteous one`) as the only naming moment, exactly as the framing prescribes. |
| P1 | `99-show-notes.md` | `**Blurb:**` ("Through them, God revived many of His creation") | Show notes paraphrases material the framing tells the hosts NOT to cross-reference — Chapters 1–4 are recapped at length, and the chapter's positive doctrine is summarized rather than reserved for in-episode landing. Pre-stating the recurring thesis here drains its three-times-in-episode pacing weight. | Cut the recap of prior chapters down to one sentence ("Chapter 4 ended on the father's anger; this chapter answers it and then widens"). Do not quote the recurring thesis in the blurb — let it land only inside the episode. |
| P2 | `99-show-notes.md` | `## References` | `References` lists only the literal placeholder `>`. No real reference is present. | Replace with a single line citing the dialogue book (author and chapter), or remove the section. |
| P2 | `00-framing.md` | `## Pronunciation` | The pronunciation block is inline inside the framing rather than a separate appendix as the bundle pattern requires. Functional for NotebookLM but inconsistent with the architecture. | Either accept as-designed (single-file framing carries the pronunciation map) and document the choice, or factor out into `05-pronunciation.md` and reference from framing. |

## Episode Findings

### EP05 — The Father Revealed and the Three Faces of Seeking

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `04-discussion-spine.md` | `### Beat 1` through `### Beat 8` | Spine is the hidden steering layer; with every beat empty, NotebookLM will follow the framing prose loosely and is likely to skip the recurring-thesis pacing (open/pivot/close), the Beat 5 testing-forge parable, and the closing seam-question — the very beats the framing depends on. | Author the spine with 6 beats matching the framing's `## Three-part focus`, not 8. Replace the existing 8-beat skeleton with: 1 Crisis, 2 First answer (breach + three-states), 3 Historical-temporal objection, 4 Pivot (recurring thesis #2), 5 Non-bodily correction + three faces, 6 Human stakes + unresolved question. |
| P0 | `02-key-passages.md` | `### Passage 1` | Discussion spine cannot reference passages that do not exist; the testing-forge parable, the divorce-oath case, the senior scholar's confession, and the recurring thesis all need anchor quotes. Without them the hosts will reword the verbatim lines the framing stipulates as verbatim. | (See chapter-finding above; same fix.) |
| P1 | `00-framing.md` | `## Stable role-labels` ("→ **the senior scholar of the old creed**") | The framing locks Host A male = scholar / teacher and Host B female = student / learner, but `## Roles + positions` casts Host B as **the senior scholar of the old creed** — a teacher role. The female voice is simultaneously labeled the senior scholar (teacher) and assigned the learner concession arc. NotebookLM will be unsure which register to voice. | Reconcile by explicit framing: Host B carries the senior-scholar's voice as a position she defends but ends by conceding it, returning to learner register at Beat 5–6. Add one sentence to `## Roles + positions` clarifying that the female voice carries the old-creed argument from inside the chapter, not as her own teaching authority. |
| P1 | `00-framing.md` | `## Length` | Target is 50–60 minutes; primary source (`01-source.md`) is missing so the length cannot be calibrated against actual source volume. A 50–60 minute target with a thin source forces padding; with a dense source forces summarization. | Once `01-source.md` is authored, verify word count supports 50–60 minutes (rule of thumb ~6,500–8,500 source words for a debate-with-concession at NotebookLM Long pacing). Adjust target if mismatched. |
| P2 | `00-framing.md` | (file root) | No explicit NotebookLM Length-setting directive (`Default` vs `Long`). The framing's 50–60 minute target implies Long but does not state it for the upload table the operator builds. | Add a one-line `NotebookLM Length: Long` to the top of the framing. |
| — | `00-framing.md` | `## Audience` | Skip-the-intro discipline present (framing instructs no `today we'll discuss` / `welcome back`). | clean |
| — | `00-framing.md` | `## Tone constraints` | Banter suppression present (R-NOINTERRUPT, forbidden-first-words list, banned modernizations, banned surprise-noise phrases). | clean |
| — | `00-framing.md` | `## Anti-noise rules` | Cliffhanger handling is engineered: the chapter's closing seam-question is preserved as an end-on-unresolved beat by design. | clean |
| — | `00-framing.md` | `## Proposition under debate` | Single-thesis discipline holds: one thesis in one sentence, Host B argues it, Host A argues against, concession at Beat 6. | clean |
| — | `00-framing.md` | `## Pronunciation` | Pronunciation appendix present and referenced; covers every Arabic term the chapter uses. | clean |
| — | `00-framing.md` | `## Roles + positions` | Steelman discipline present: framing tells Host B to argue "GENUINELY", not as a foil; has the chapter's strongest internal-case lines; defends with senior-teacher weight. Engineered concession at Beat 6 satisfies the §4(g)(7) positive-practice rule. | clean |

## Cross-Bundle Patterns

The single bundle audited shows a sharp split between authoring effort and pipeline mechanics. `00-framing.md` and `99-show-notes.md` are densely authored; the three middle artifacts that NotebookLM actually retrieves against — source, key passages, context pack, discussion spine — are either missing or pure `[LLM-FILL]`. The pattern suggests an authoring pass that prioritized the high-touch framing and the human-facing show notes but skipped the machine-facing retrieval layer entirely. Because NotebookLM grounds primarily on the source document and uses the spine as a hidden retrieval ladder, the bundle in its current state will produce a heavily improvised episode no matter how well-engineered the framing is.

A second pattern is the doctrinal conflict between framing and show-notes on Arabic personal names. The framing carries the locked R-NO-ARABIC-NAMES doctrine and assigns English stable labels; the show-notes blurb voices every Arabic personal name with phonetics, treating the show-notes as if NotebookLM will not see it. If show-notes is uploaded with framing, the hosts will receive contradictory naming guidance. Either the show-notes must conform to the framing's English-labels-only discipline, or the bundle architecture must explicitly mark show-notes as operator-facing and never uploaded.

A third pattern, smaller: the discussion-spine template ships with 8 beats while the framing's `## Three-part focus` specifies 6 beats. The template skeleton in this repo appears to predate the content-aware-format work; spine-template length should be driven by `episode-plan` per chapter, not hard-coded at 8.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "01-source.md",
    "anchor": "(file missing)",
    "severity": "P0",
    "problem": "Primary chapter source is absent from the bundle. NotebookLM has no document to ground retrieval on; every verbatim line the framing stipulates as quoted (the divorce-oath ruling, the breach figure, the three-states reasoning, the recurring thesis, the closing seam-question) will be hallucinated.",
    "fix": "Create 01-source.md as a prose document containing the full chapter text the framing references: the father's confrontation at the door, the boy's two-strands offer, the father's rejection of taqiyya and choice of debate, the boy's bind, the weeping concession, the naming of Salih and al-Bakhtari, the community's approach to the senior scholar, the breach-in-medicine figure, the three-states reasoning, the long Salih-Abu Malik dialogue including the Maqrub divorce case, the senior scholar's confession, the recurring thesis, and the chapter's closing seam-question.",
    "category": "notebooklm"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "### Passage 1",
    "severity": "P0",
    "problem": "Only one stub passage exists with empty quote body and [LLM-FILL] rationale. The discussion spine has no verbatim anchor quotes to retrieve against, and the framing's stipulated verbatim moments have no source binding.",
    "fix": "Replace with 6 to 8 verbatim passages drawn from 01-source.md once authored. Required passages: the father's reproach 'is this the reward of sons to their fathers?', the boy's bind 'either you are a scholar … or you are ignorant', the divorce-oath ruling 'act on whichever of the two you wish', the breach-in-medicine figure, the three-states reasoning, the senior scholar's confession 'the inherited code of my age has been lost, corrupted, and disrupted', the zero-point line 'I do not see that anything is left with me', the recurring thesis 'the cause that connects heaven to earth, unbroken — the loop of the firm handhold, the rope of those who hold fast, the ark of tranquility and the ship of life and the light of life', and the closing seam-question 'the attribute is preferable to him — so how is it described?'. Each passage gets a one-sentence Why this matters line.",
    "category": "notebooklm"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "## Author / narrator",
    "severity": "P0",
    "problem": "Every heading body is [LLM-FILL]. Hosts have no grounding for author identity, tradition, or what the chapter is responding to, increasing hallucination of dates and tradition claims.",
    "fix": "Fill ## Author / narrator with the tenth-century Yemeni author of the dialogue book; ## What this chapter is responding to with the father's anger at the boy's initiation in Chapter 4 widening into the inherited-fiqh-versus-living-chain debate; ## Tradition / lineage with classical Ismaili dialogue genre, internally qualified per the source-tradition precedence rule; ## Related works with Chapters 1–4 of the same book (slugs already listed in 99-show-notes.md ## Related episodes); leave ## Why this lands now as marked 'Not required for this adaptation mode'.",
    "category": "notebooklm"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 1: Opening hook",
    "severity": "P0",
    "problem": "All eight beats are [LLM-FILL]. The hidden steering layer is empty, so NotebookLM has no enforced arc — the recurring-thesis triple-landing, the testing-forge parable, the three faces of seeking, and the closing seam-question are unanchored.",
    "fix": "Rewrite 04-discussion-spine.md to carry exactly 6 beats, replacing the 8-beat template. Beat 1: Crisis — open on the divorce-oath case; Host A speaks the recurring thesis for the first time. Beat 2: First answer — Host B unfolds the breach-in-medicine figure and the three-states reasoning. Beat 3: Second answer — Host B presses the historical-temporal objection that revelation was cut off by the books. Beat 4: Pivot — Host A speaks the recurring thesis for the second time, word-for-word; argues that a religion grounded only on narration is not religion. Beat 5: Non-bodily correction — Host A unfolds the testing-forge parable and the three faces of seeking; Host B places herself in the third face. Beat 6: Human stakes — Host A speaks the recurring thesis for the third time, word-for-word; Host B voices the chapter's closing seam-question 'how is it described?'. For each beat, fill Key question, Tension drawn from the matching passage in 02-key-passages.md, Anchor passage reference, and Landing.",
    "category": "spine"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "Blurb voices Arabic personal names with phonetics — Salih, al-Bakhtari, Abu Malik, Ka'b al-Ahbar, Abu Salih, Maqrub — directly contradicting the framing's locked R-NO-ARABIC-NAMES doctrine which mandates the boy, the father, the senior scholar, the petitioner, the early figure of report-without-witness. If NotebookLM ingests show-notes with framing the hosts receive conflicting naming guidance.",
    "fix": "Replace every Arabic personal name in the blurb with the framing's English stable label. Preserve only the naming-moment aside ('a name meaning the righteous one', no Arabic) exactly as the framing prescribes. Remove the phonetic parenthetical for every personal name; keep phonetic parentheticals only for technical Arabic terms that already appear in the pronunciation map.",
    "category": "pronunciation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "The blurb is one paragraph of roughly 1,200 words containing dense parenthetical stacking and em-dash chains. It exceeds the 400-word breath ceiling and the framing's no-bold-no-italics articulation rule (asterisk italics on every quote and term).",
    "fix": "Rewrite the blurb as three to four short prose paragraphs of no more than 200 words each. Drop every asterisk-italic and asterisk-bold. Split em-dash chains into separate sentences. Cut the Chapters 1–4 recap down to one sentence ('Chapter 4 ended on the father's anger; this chapter answers it and then widens to a senior scholar sent to judge the boy'). Do not pre-state the recurring thesis in the blurb — let it land only inside the episode.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "## References",
    "severity": "P2",
    "problem": "References section contains only the literal placeholder character '>'.",
    "fix": "Replace with a single reference line citing the tenth-century dialogue book by author and chapter, or remove the ## References section entirely if no canonical citation is available.",
    "category": "citation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Opening directive",
    "severity": "P1",
    "problem": "Framing uses asterisk-bold for section labels (**Episode format:**, **Host A …**, **Audience**, **Length**) and asterisk-italics for every verbatim quotation and inline directive, violating the house articulation rule of no bold and no italics.",
    "fix": "Convert every **…** to plain text (rely on heading hierarchy for emphasis). Convert every *…* to double-quoted text when the asterisks carry verbatim-quote weight. Leave heading markup intact.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Roles + positions",
    "severity": "P1",
    "problem": "Host B is simultaneously framed as the female voice in the male-scholar / female-learner role pairing AND as 'the senior scholar of the old creed' who carries doctrinal teaching authority. The two assignments conflict on which register the female voice should hold.",
    "fix": "Add one paragraph to ## Roles + positions clarifying that the female voice carries the senior-scholar's argument from inside the chapter as a position she defends and ends by conceding, not as her own teaching authority. The learner register returns at Beats 5 and 6 once she concedes and asks 'so how is it described?'.",
    "category": "host-role"
  },
  {
    "file": "00-framing.md",
    "anchor": "(top of file, before ## Opening directive)",
    "severity": "P2",
    "problem": "No explicit NotebookLM Length-setting directive. The framing's 50–60 minute target implies Long pacing but does not state it for the operator's upload table.",
    "fix": "Add a one-line directive at the top of the framing: 'NotebookLM Length: Long.' Place it immediately after the title heading.",
    "category": "format"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Length",
    "severity": "P2",
    "problem": "Length target of 50–60 minutes cannot be calibrated against source volume because 01-source.md is missing.",
    "fix": "After 01-source.md is authored, verify its word count supports 50–60 minutes at NotebookLM Long pacing (~6,500–8,500 source words). If the source is thinner, drop the target to 40–50 minutes; if denser, raise to 60–70 minutes.",
    "category": "length"
  }
]
```
