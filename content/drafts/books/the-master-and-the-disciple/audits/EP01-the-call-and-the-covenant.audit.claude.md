## Inventory

- **Bundle:** `EP01-the-call-and-the-covenant` (one chapter, one episode, single-bundle audit).
- **Chapter / Episode 1:** "The Master's Call and the Disciple's Covenant" — opening of *The Master and the Disciple*.
- **Artifacts present:** framing (`00-framing.md`), key passages stub (`02-key-passages.md`), context pack stub (`03-context-pack.md`), discussion spine stub (`04-discussion-spine.md`), show notes (`99-show-notes.md`).
- **Artifacts missing:** primary source (`01-source.md`) — the chapter text itself is absent from the bundle, so NotebookLM has nothing to retrieve verbatim from.
- **Maturity:** framing is mature and rule-saturated; everything else is template scaffold awaiting authorship.

## Chapter Findings

### Chapter 1: The Master's Call and the Disciple's Covenant

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `02-key-passages.md` | `# Key passages` / `### Passage 1` | The file contains a single `>` placeholder and an `[LLM-FILL]` rationale — no verbatim passages exist for the framing's eight quote-anchor directives (law of thanks, Persian wanderer, sermon, brothers parable, work-not-flattery, five conditions, the key, the rope of God). Hosts have nothing to retrieve and will improvise. Compounded by the absence of `01-source.md`, which the manifest does not list — the source chapter is not in the bundle at all. | Generate `01-source.md` from `chapter-contracts/the-call-and-the-covenant.yml` (the canonical chapter prose), then author 6–8 verbatim passages in `02-key-passages.md` covering exactly the eight quotation targets the framing's "Anti-noise rules" enumerates, each with a one-sentence "why this matters" beat-anchor note. |
| P0 | `03-context-pack.md` | `## Author / narrator` | Every section (`Author / narrator`, `What this chapter is responding to`, `Tradition / lineage`, `Related works`) is `[LLM-FILL]`. Hosts have no grounded background and will either fabricate or repeat the framing's `## Background` paragraph verbatim. | Populate each section with material consistent with framing's `## Background`: tenth-century Fatimid-Yemeni author and dialogue-treatise tradition; the crisis-of-thanks question the chapter answers; the early Ismaili tariqah lineage with internal qualification (per scholarly-rubric §4c); related dialogue treatises and the other five episodes named in `99-show-notes.md`. |
| P1 | `99-show-notes.md` | `**Blurb:**` | Transliterated Arabic (`Kitab al-'Alim wa-l-Ghulam`, `da'wa`, *Party of God*, *covenant of God*, *law of thanks*) violates the articulation rule "Arabic terms in Arabic script only, never transliterated." Even if show notes are reader-only, downstream surfaces (podcast-reader, future viewer) render them. | Replace transliterations with the framing's stable English labels — *the book "The Master and the Disciple"*, *the call*, *the Party of God* — and, where the Arabic must appear, put it in Arabic script with the English meaning leading: e.g., *the call (الدعوة)*. |
| P1 | `99-show-notes.md` | `**Blurb:**` | Italics used throughout (e.g., *the calamity of ignorance*, *the rope of God upon His earth*, *stand with him with outward agreement*) violate "no bold, no italics." Show notes diverge stylistically from framing's voiced-prose discipline. | Convert all `*...*` runs to plain prose; preserve emphasis through sentence structure, not glyphs. |
| P1 | `99-show-notes.md` | `## References` | References section contains a single `>` character — no citations populated. The framing's narrative draws on Quran verses and a quoted line from *The Peak of Eloquence*, none of which are surfaced. | List every verse the chapter cites in `Q|Surah:Verse` form, plus the *Peak of Eloquence* reference for the Father of Imams quote, exactly as they appear in the source chapter. |
| clean | — | — | Cohesion (within framing) — single thesis, six narrative beats, three constrained verbatim restatements, clean opening-to-binding arc. | — |
| clean | — | — | Duplication — none in framing (recurring thesis is intentional and quota-bounded at three). | — |
| clean | — | — | NotebookLM audio-readability of framing — no bulleted prose blocks, no tables, no code, no emoji, no bracket-stacking; one-fluent-unit pronunciation directives given. | — |

## Episode Findings

### Episode EP01: The Master's Call and the Disciple's Covenant

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `04-discussion-spine.md` | `### Beat 1: Opening hook` | Every one of the eight beats is `[LLM-FILL]` — no key question, no tension, no anchor passage, no landing populated anywhere. NotebookLM has no steering layer and will follow `00-framing.md` cold, losing the beat-level retrieval anchors. | Author all beats with concrete key-question, tension (drawn from the chapter), anchor-passage reference back to `02-key-passages.md`, and a landing residue. |
| P0 | `04-discussion-spine.md` | `# Discussion spine` | Spine declares **eight beats**; framing `00-framing.md` `## Three-part focus` prescribes **six beats** that "land once and only once." The structural count mismatch will produce drift — either two phantom beats authored from scratch, or two collapsed and re-cut. | Reconcile to the framing's six beats and rename them exactly: (1) Preachers' question and crisis of thanks, (2) Law of thanks, (3) Persian wanderer and calamity of ignorance, (4) Master's arrival, assembly, sermon, (5) Dialogue and the chapter's pivot, (6) Five conditions, long absence, binding. Delete the two surplus beat blocks. |
| P1 | `00-framing.md` | `## Pronunciation` | Pronunciation appendix covers only `Quran` and `Sinai`. The chapter narrative names additional Arabic-origin terms (the call, the covenant, the Party of God, the chamber from the great river, the figure of the key) that NotebookLM may attempt phonetically. The appendix also forward-references "Persian wanderer" without phonetic guidance for any place- or person-derived term in the source. | Once `01-source.md` is authored, sweep it for every Arabic-origin token and add a one-fluent-unit phonetic for each (e.g., `tariqah` → `ta-REE-qah`, `da'wa` → `DAH-wah`) — appendix only, never inline in prose. |
| P2 | `00-framing.md` | `# The Master's Call and the Disciple's Covenant` / `**Episode format:**` | NotebookLM Audio Overview format is described in editorial language ("in-depth walkthrough") but never named as one of the platform's four format settings (Deep Dive / Brief / Critique / Debate). Downstream upload-instruction generation requires the named setting. | Add an explicit line under `**Episode format:**`: `NotebookLM format: Deep Dive. Length: Long.` — Deep Dive is the right fit (single-source exposition with two-host friction; debate is wrong because the dynamic is master/disciple, not adversarial). |
| clean | `00-framing.md` | `## Host dynamic` | Host roles assigned per book-wide convention: Host A male = scholar / teacher / Master's voice; Host B female = disciple / challenger. Roles locked, not rotated. Three pushback turns seeded at Beats 4, 5, 6 with forbidden-first-word guard. | — |
| clean | `00-framing.md` | `## Length` | 50–60 minute target declared; six dense beats support the length without padding. | — |
| clean | `00-framing.md` | `## Opening directive` / `## Anti-noise rules` (R-WELCOME) | Skip-the-intro guard explicit; "today we'll discuss" and "welcome back" forbidden by name. | — |
| clean | `00-framing.md` | `## Anti-noise rules` (R-NOREPEAT) + `## Do not` | Banter suppression, surprise-noise phrases, formal-essay transitions, and forbidden-first-words for Host B's pushback all explicitly enumerated. | — |
| clean | `00-framing.md` | `## Opening directive` (recurring thesis) | Single thesis declared, voiced exactly three times verbatim at fixed positions (open, pivot in Beat 5, close in Beat 6). | — |
| clean | `00-framing.md` | `## Stable role-labels` + `## Name discipline` | TTS-safe label discipline strict: no Arabic personal names voiced; the forbidden pairing of the leadership-title with the personal name of the Father of Imams guarded by name; surah names replaced with English meaning. | — |
| clean | `00-framing.md` | `## Landing` | No cliffhanger — framing explicitly forbids `and that's the chapter` / `until next time` / pre-announcing the next chapter. Hosts go silent. | — |
| clean | `00-framing.md` | `## Central tensions` | Steelman-before-critique posture (the disciple-who-agrees-yet-stands-outside move is engineered to land hard, not as cheap dramatic tension); concession structure honest. No premature closure. | — |
| clean | `00-framing.md` | `## Background` | Internal-Ismaili episode (per scholarly-rubric §4 tradition-precedence) with proper internal qualification — "the early Ismaili teaching positioned itself relative to the wider Muslim community" — no essentialism, no orientalism, no leader-equals-tradition conflation. | — |

## Cross-Bundle Patterns

Single-bundle audit; no cross-bundle pattern surface. The dominant pattern is **maturity asymmetry**: the framing is rule-saturated and production-ready, while four of the five bundle files (`02`, `03`, `04`, plus the wholly-missing `01-source.md`) remain authoring stubs. This is consistent with a bundle paused immediately after framing-authorship and before per-artifact fill — Claude Code should treat the framing as the contract and author the remaining artifacts to satisfy it (six beats, six anchor-passages keyed to those beats, grounded context, populated show-notes references). The framing's beat count (6) is authoritative; the spine template's default of 8 is the drift to correct, not the other way around.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "02-key-passages.md",
    "anchor": "# Key passages",
    "severity": "P0",
    "problem": "File contains only a single '>' placeholder and one '[LLM-FILL]' rationale; no verbatim passages exist for the framing's eight required quote anchors and the primary source 01-source.md is missing from the bundle entirely.",
    "fix": "First generate 01-source.md at the bundle root by extracting the chapter prose from chapter-contracts/the-call-and-the-covenant.yml. Then author exactly eight verbatim passages in 02-key-passages.md covering: (1) the threefold law of thanks, (2) the four-part exchange on praiseworthy vs reprehensible speech, (3) the parable of the brothers and the inherited wealth, (4) the rule of work-not-flattery, (5) the five conditions, (6) the figure of the key distinguishing forbidden union from lawful marriage, (7) the covenant as the rope of God upon His earth, and (8) the closing image of the disciple falling silent while the Master begins to expound. Each passage gets a one-sentence 'why this matters' line naming which of the framing's six beats it anchors.",
    "category": "citation"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "## Author / narrator",
    "severity": "P0",
    "problem": "Every section is an '[LLM-FILL]' placeholder, leaving hosts with no grounded background and forcing them to either fabricate or repeat the framing's Background paragraph.",
    "fix": "Populate Author/narrator with the tenth-century Fatimid-Yemeni author per framing Background; populate 'What this chapter is responding to' with the crisis-of-thanks question (gap between knowing the threefold obligation and discharging it); populate 'Tradition / lineage' with the early Ismaili tariqah, internally-qualified per scholarly-rubric tradition-precedence (no essentialism, no leader-equals-tradition conflation); populate 'Related works' with the five other episodes listed in 99-show-notes.md plus The Peak of Eloquence and The Spiritual Couplets as named in the framing. Leave 'Why this lands now' empty as the template indicates.",
    "category": "cohesion"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "# Discussion spine",
    "severity": "P0",
    "problem": "Spine declares eight beats but the framing prescribes six beats that 'land once and only once'; the count mismatch will force two phantom beats or two collapsed beats and drift the structure away from the framing's contract.",
    "fix": "Delete Beat 7 and Beat 8 blocks. Rename the remaining six beats exactly: Beat 1 'Preachers' question and crisis of thanks', Beat 2 'The law of thanks', Beat 3 'The Persian wanderer and the calamity of ignorance', Beat 4 'The Master arrives, the assembly, the sermon', Beat 5 'The dialogue and the chapter's pivot', Beat 6 'The five conditions, the long absence, and the binding'. Preserve the existing Beat-1 'Opening hook' and Beat-8 'Landing' template landings only as structural reminders inside Beats 1 and 6 respectively.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "### Beat 1: Opening hook",
    "severity": "P0",
    "problem": "Every beat's Key question, Tension, Anchor passage, and Landing field is '[LLM-FILL]' — no steering layer exists, so NotebookLM hosts will follow only the framing and lose the per-beat retrieval anchors.",
    "fix": "For each of the six reconciled beats, fill: Key question (drawn from the framing's beat-by-beat prose under '## Three-part focus'); Tension (the specific friction the framing names for that beat — e.g., Beat 4 'genuine challenger friction on what the chain of transmission actually is'); Anchor passage (reference to the matching passage number in 02-key-passages.md once that file is authored); Landing (the residue the beat leaves, ending in a question, never a takeaway).",
    "category": "spine"
  },
  {
    "file": "00-framing.md",
    "anchor": "## Pronunciation",
    "severity": "P1",
    "problem": "The pronunciation appendix covers only 'Quran' and 'Sinai'; any other Arabic-origin term that appears in the source chapter (tariqah, da'wa, names of figures or places) has no phonetic guidance and NotebookLM will mispronounce.",
    "fix": "After 01-source.md is authored, scan it for every Arabic-origin token and add a one-fluent-unit phonetic to the Pronunciation section using the same 'term as one fluent word' format (e.g., tariqah → ta-REE-qah; da'wa → DAH-wah). Keep all phonetics in the appendix only, never inline in voiced prose.",
    "category": "pronunciation"
  },
  {
    "file": "00-framing.md",
    "anchor": "**Episode format:**",
    "severity": "P2",
    "problem": "The framing describes format editorially ('in-depth walkthrough') but never names one of NotebookLM's four platform settings, which the upload-instructions generator requires.",
    "fix": "Append a single line directly under the existing '**Episode format:**' line: 'NotebookLM format: Deep Dive. Length: Long.' Deep Dive is correct because the dynamic is single-source exposition with engineered friction, not adversarial Debate.",
    "category": "format"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "Blurb uses transliterated Arabic ('Kitab al-'Alim wa-l-Ghulam', 'da'wa') in violation of the articulation rule that Arabic appears in Arabic script with parenthesized English meaning, never transliterated.",
    "fix": "Replace 'Kitab al-'Alim wa-l-Ghulam (The Book of the Master and the Boy)' with 'the book \"The Master and the Disciple\"' per the framing's stable-role-labels. Replace 'da'wa' with 'the call' or, where the Arabic must surface, 'the call (الدعوة)'. Audit the rest of the blurb for any remaining transliteration and apply the same rule.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "**Blurb:**",
    "severity": "P1",
    "problem": "Italic emphasis (*the calamity of ignorance*, *the rope of God upon His earth*, *stand with him with outward agreement*, etc.) is used throughout in violation of the articulation rule forbidding bold and italics.",
    "fix": "Strip all '*...*' italic runs in the blurb and convert them to plain prose; preserve emphasis through sentence rhythm and quotation phrasing only.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "## References",
    "severity": "P1",
    "problem": "References section is a single '>' character — no Quran citations and no book references populated, despite the chapter drawing on both verse citations and the line from The Peak of Eloquence.",
    "fix": "Populate the References list with: every Quran verse cited in the chapter in 'Q|Surah:Verse' form (sourced from 01-source.md once authored); 'The Peak of Eloquence — the saying of the Father of Imams on knowledge and wealth'; and 'The Spiritual Couplets — the image of the reed cut from its bed' if that image is preserved in the source. Use plain prose entries, no italics, no transliterated Arabic.",
    "category": "citation"
  }
]
```
