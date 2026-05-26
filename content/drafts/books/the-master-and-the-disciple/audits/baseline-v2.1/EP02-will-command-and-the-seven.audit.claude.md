## Inventory

- **Bundle: EP02 — Will, Command, and the Seven** (chapter: *The Architecture of Creation*)
  - Framing: present and fully authored (`00-framing.md`, 21,496 bytes)
  - Primary source: **absent from bundle** (no chapter prose file)
  - Key passages: **stub** (`02-key-passages.md`, 185 bytes — single `> >` placeholder)
  - Context pack: **stub** (`03-context-pack.md`, 544 bytes — every section `[LLM-FILL]`)
  - Discussion spine: **stub** (`04-discussion-spine.md`, 2,514 bytes — all 8 beats `[LLM-FILL]`)
  - Show notes: present and fully authored (`99-show-notes.md`, 2,950 bytes)
  - Pronunciation appendix: **absent**
  - Citation spoken-form appendix: **absent**

Episode count: 1 (EP02). Of the six standard artifacts, two are authored, three are unfilled templates, and one is missing entirely.

## Chapter Findings

### Chapter: The Architecture of Creation (EP02)

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | 00-framing.md | manifest (preamble) | The bundle ships no primary chapter source file; NotebookLM has nothing to ingest as the audio source. | Add `01-source.md` to the bundle containing the verbatim chapter prose in house style; update the manifest. |
| P0 | 02-key-passages.md | Passage 1 | The only passage entry is a hollow blockquote (`> >`) with a `[LLM-FILL]` justification — retrieval has nothing to ground host quotations on. | Populate with at least six verbatim passages from the chapter (three-words formula, seven-principles, great-parallel, body-and-soul, six-limits-and-a-seventh, air-as-highest-proof, the egg), each followed by a one-sentence *Why this matters*. |
| P0 | 03-context-pack.md | Author / narrator | Every section is `[LLM-FILL]`; hosts have no author, tradition, or lineage context and will fabricate. | Author all four populated sections (Author/narrator, What this chapter is responding to, Tradition/lineage, Related works) using `00-framing.md`'s `## Background` paragraph as the seed. |
| P1 | 99-show-notes.md | Blurb | Heavy transliterated Arabic (*nāṭiqs, ḥujaj, nuqabā', du'āt, zahir, batin, Kitab al-'Alim wa-l-Ghulam, Kun, fa-yakun*) violates the house rule that Arabic appears in script only, never transliterated. | Rewrite using the stable English labels from `00-framing.md`'s `## Stable role-labels`; where Arabic must appear, render it in script in parentheses after the English (e.g., *the speakers (نَاطِق)*). |
| P1 | 99-show-notes.md | Blurb | Multiple uses of *God* where house style mandates *Allah* ("God as the *First of all firsts*", "the world without knowledge of its soul, God"). | Replace every occurrence of *God* with *Allah* in the blurb, preserving any verbatim Quranic English where the quoted translation uses the word. |
| P1 | 99-show-notes.md | Blurb | Quran citation rendered as `Q 7:26` rather than the prescribed `Q|7:26` on a new line immediately after the verse. | Reformat to `Q|7:26` and move to its own line directly after the sentence about the three garments of Adam. |
| P1 | 99-show-notes.md | References | The References list contains only a `>` placeholder — no actual references. | Replace with the historians named in `00-framing.md`'s `## Background` paragraph (Daftary, Halm, Walker, Corbin, Hollenberg), or remove the section if no external references are intended. |
| P2 | 99-show-notes.md | Length estimate | Line `see contract.length_target (extended)` is a template artifact. | Replace with the explicit value `Length estimate: 50–60 minutes` taken from the framing. |
| P2 | 99-show-notes.md | Blurb | The blurb walks the chapter's six-beat arc in narrative form, duplicating the framing's beat descriptions and inflating duplication risk if both files reach NotebookLM. | Compress the blurb to one paragraph under 120 words naming the thesis (*the apparent is evidence of the hidden*) and the three governing images (body-and-soul, air-encompassing-all, the egg) without walking each beat. |
| - | 00-framing.md | Cohesion | clean — single thesis, six beats, narrative discipline, landing on the egg | clean |
| - | 00-framing.md | Single thesis discipline | clean — *the apparent is evidence of the hidden*, spoken three times verbatim by design | clean |
| - | 00-framing.md | Articulation (as directive document) | clean — bold and italics used for directive markup, not for the spoken prose | clean |

## Episode Findings

### Episode 1: EP02 — Will, Command, and the Seven

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | 04-discussion-spine.md | Beat 1 through Beat 8 | The entire hidden-steering layer is `[LLM-FILL]`. Without it NotebookLM hosts have no spine — they will drift, lose structure, and improvise the chapter's most settled moves. | Author all beats with concrete `Key question / Tension / Anchor passage / Landing` content drawn from the framing's six chapter beats; each Anchor passage must reference a numbered entry in `02-key-passages.md`. |
| P1 | 04-discussion-spine.md | beat count header | The spine template prescribes 8 beats while the framing prescribes 6 chapter beats; the structural mismatch will force authoring drift. | Reduce the spine to 6 beats (Opening hook + Beats 1–4 + Landing on the egg) and update the header, OR split framing Beat 5 into two (catechism, then air-as-highest-proof) and framing Beat 6 into two (three-layers, then egg) — pick one approach and document it in a one-line note under the spine title. |
| P0 | 00-framing.md | Pronunciation | No separate pronunciation appendix exists; the framing covers only *Quran* and *imam* inline. Every other Arabic token in the chapter source will be mangled. | Create `05-pronunciation.md` mapping every Arabic term in the chapter to a fluent-unit phonetic spelling (e.g., صلاة → *sa-LAH*); replace the inline directives with a one-line reference to it. |
| P1 | 00-framing.md | Pronunciation | No spoken-form appendix for Quran citations; `Q|7:26` read literally as text would break in audio. | Create `06-citations-spoken.md` mapping every Quran citation in the chapter to natural speech (e.g., `Q|7:26` → *Quran, chapter seven, verse twenty-six*); reference it from `## Pronunciation`. |
| P1 | 00-framing.md | Length | Target is 50–60 minutes, but with the primary source absent, source-volume sufficiency cannot be verified — too thin invites repetition, too dense forces summarization. | Once `01-source.md` is added, confirm word count supports the target (≈7,500–9,000 words); if thin, reduce target to 40–50 min; if dense, segment into two episodes. |
| P2 | 00-framing.md | Opening directive | Framing declares format as "in-depth walkthrough" — not one of NotebookLM's four formats (Deep Dive, Brief, Critique, Debate). The upload dropdown is ambiguous. | Add a single line under `## Opening directive`: `NotebookLM format: Deep Dive` (justification: single-chapter exposition with two-host friction, 50–60 min target). |
| - | 00-framing.md | Host roles (R-HOSTROLES) | clean — Host A = male/scholar, Host B = female/learner, three seeded pushback exchanges, no rotation | clean |
| - | 00-framing.md | Skip-the-intro (R-WELCOME) | clean — framing forbids *today we'll discuss* and *welcome back* | clean |
| - | 00-framing.md | Banter suppression | clean — R-NOREPEAT, R-NOBACKGROUND, forbidden-affirmation list all present | clean |
| - | 00-framing.md | Cliffhanger discipline | clean — Beat 6 explicitly ends the episode; no later-promises | clean |
| - | 00-framing.md | Source file count | clean — 5 files in bundle, well under 6 | clean |

## Cross-Bundle Patterns

The bundle is bimodal — two files are exceptionally polished (`00-framing.md`, `99-show-notes.md`) while three are unauthored template stubs (`02-key-passages.md`, `03-context-pack.md`, `04-discussion-spine.md`) and the primary chapter source is absent. This is the signature of a framing-authorship phase that completed cleanly while the downstream key-passages, context-pack, and discussion-spine generators either failed silently or were skipped. The next pipeline action should be to re-run those three generators against the chapter source before any NotebookLM upload — uploading now would surface a sophisticated framing into a void of retrieval scaffolding.

A second pattern: the framing rigorously enforces *stable English labels, no Arabic transliteration* inside the spoken episode, but the show notes blurb breaks that rule extensively with terms like *nāṭiqs, ḥujaj, nuqabā', du'āt, zahir, batin*. House style needs to apply uniformly across every bundle file that may surface to either listeners or NotebookLM ingestion. The two files appear to have been authored against different style contracts.

A third pattern: pronunciation and citation spoken-form coverage is partial — inline directives exist in the framing but no dedicated appendix files exist. For a chapter dense with Arabic tokens and at least one Quran citation, separate appendix files are required, not inline notes that risk being stripped or ignored during upload. The bundle protocol should make `05-pronunciation.md` and `06-citations-spoken.md` mandatory artifacts, not optional add-ons.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "00-framing.md",
    "anchor": "manifest (preamble)",
    "severity": "P0",
    "problem": "The bundle ships no primary chapter source file; NotebookLM has nothing to ingest as the audio source.",
    "fix": "Create 01-source.md in the bundle directory containing the verbatim chapter prose under house articulation rules (Arabic in script only, Allah not God, Q|Surah:Verse citations on their own line, no bold/italics/lists, paragraph prose); update the bundle manifest to list it.",
    "category": "cohesion"
  },
  {
    "file": "02-key-passages.md",
    "anchor": "Passage 1",
    "severity": "P0",
    "problem": "The only passage entry is a hollow blockquote (> >) with a [LLM-FILL] justification; retrieval has nothing to ground host quotations on.",
    "fix": "Replace Passage 1 with at least six verbatim passages drawn from the chapter source in narrative order — the three-words formula, the seven-principles enumeration, the great-parallel passage, the body-and-soul figure, the six-limits-and-a-seventh master-parable, the air-as-highest-proof settlement, and the parable of the egg — each followed by a single 'Why this matters' sentence.",
    "category": "spine"
  },
  {
    "file": "03-context-pack.md",
    "anchor": "Author / narrator",
    "severity": "P0",
    "problem": "Every section of the context pack is [LLM-FILL]; hosts have no author, tradition, or lineage context and will fabricate.",
    "fix": "Populate Author/narrator (the tenth-century Fatimid Yemen author of the dialogue treatise, attributed by tradition to a son of the founding generation of Yemeni callers), What this chapter is responding to (the long expounding after the binding of the covenant), Tradition/lineage (early Fatimid dialogue treatises; cite the historians named in 00-framing.md's ## Background paragraph), and Related works (other chapters of the same book listed in 99-show-notes.md's Related episodes block).",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "Beat 1: Opening hook",
    "severity": "P0",
    "problem": "All eight beats are [LLM-FILL] template placeholders; the hidden steering layer NotebookLM relies on does not exist.",
    "fix": "Author every beat with concrete Key question, Tension, Anchor passage reference, and Landing content drawn from the framing's six chapter beats; ensure each Anchor passage line references a numbered passage in 02-key-passages.md after that file is populated.",
    "category": "spine"
  },
  {
    "file": "04-discussion-spine.md",
    "anchor": "beat count header",
    "severity": "P1",
    "problem": "The spine template prescribes 8 beats while the framing prescribes 6 chapter beats walked in narrative order, creating a structural mismatch that will force authoring drift.",
    "fix": "Reduce the spine to 6 beats (Opening hook + Beats 1-4 from framing + Landing on the egg), remove Beat 7 and Beat 8 sections, and update the spine header to '6 beats. The hidden steering layer'; alternatively split framing Beat 5 into two beats (catechism, then air-as-highest-proof) and framing Beat 6 into two (three-layers, then egg) — pick one approach and document it in a one-line note under the spine title.",
    "category": "spine"
  },
  {
    "file": "00-framing.md",
    "anchor": "Pronunciation",
    "severity": "P0",
    "problem": "No separate pronunciation appendix file exists; the framing covers only Quran and imam inline, so every other Arabic token in the chapter source will be mangled by NotebookLM.",
    "fix": "Create 05-pronunciation.md in the bundle directory mapping every Arabic term appearing in the chapter source to a fluent-unit phonetic spelling (e.g., صلاة → sa-LAH); replace the existing inline pronunciation directives in 00-framing.md's ## Pronunciation block with a single sentence: 'See 05-pronunciation.md for the full token map.'",
    "category": "pronunciation"
  },
  {
    "file": "00-framing.md",
    "anchor": "Pronunciation",
    "severity": "P1",
    "problem": "No citation spoken-form appendix exists; literal pronunciation of Q|Surah:Verse strings as text would sound broken in audio.",
    "fix": "Create 06-citations-spoken.md mapping every Quran citation that appears in the chapter to natural speech form (e.g., 'Q|7:26 → Quran, chapter seven, verse twenty-six'); add a one-line reference to it under 00-framing.md's ## Pronunciation block: 'See 06-citations-spoken.md for citation spoken-forms.'",
    "category": "citation"
  },
  {
    "file": "00-framing.md",
    "anchor": "Length",
    "severity": "P1",
    "problem": "Target is 50-60 minutes but with the primary source absent from the bundle, source-volume sufficiency for this length cannot be verified.",
    "fix": "After 01-source.md is added, verify word count supports the 50-60 minute target (approximately 7,500-9,000 words at NotebookLM's typical density); if thin, reduce target to 40-50 min in the framing's ## Length block; if dense, segment into two episodes and update the framing's six-beat structure accordingly.",
    "category": "length"
  },
  {
    "file": "00-framing.md",
    "anchor": "Opening directive",
    "severity": "P2",
    "problem": "The framing declares episode format as 'in-depth walkthrough', which is not one of the four NotebookLM Audio Overview formats (Deep Dive, Brief, Critique, Debate), leaving the upload-time format selection ambiguous.",
    "fix": "Add a single line at the end of the ## Opening directive block: '**NotebookLM format:** Deep Dive — single-chapter exposition with two-host friction at the 50-60 minute length.'",
    "category": "format"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Blurb",
    "severity": "P1",
    "problem": "The blurb uses transliterated Arabic throughout (nāṭiqs, ḥujaj, nuqabā', du'āt, zahir, batin, Kitab al-'Alim wa-l-Ghulam, Kun, fa-yakun), violating the house rule that Arabic terms appear in Arabic script only, never transliterated.",
    "fix": "Rewrite the blurb using the stable English labels from 00-framing.md's ## Stable role-labels (the speakers, the arguments, the chiefs, the summoners, the apparent and the inward); where Arabic must appear, render it in script in parentheses after the English term, never as Latin-letter transliteration.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Blurb",
    "severity": "P1",
    "problem": "The blurb uses 'God' repeatedly where house style mandates 'Allah'.",
    "fix": "Replace every occurrence of 'God' with 'Allah' in the blurb, except inside any verbatim Quranic English translation where the quoted text uses the word as-is.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Blurb",
    "severity": "P1",
    "problem": "The Quran citation appears as 'Q 7:26' instead of the prescribed 'Q|Surah:Verse' form on its own line immediately following the verse.",
    "fix": "Reformat the 'Q 7:26' citation to 'Q|7:26' and move it onto its own line directly following the sentence that references the three garments of Adam.",
    "category": "citation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "References",
    "severity": "P1",
    "problem": "The References section contains only a single '>' placeholder character with no actual entries.",
    "fix": "Replace the placeholder with the historians named in 00-framing.md's ## Background paragraph (the historian Daftary, the historian Halm, the philosopher Walker, the historian Corbin, the historian Hollenberg) formatted as a bulleted list, or remove the entire References section if the chapter carries no external citations.",
    "category": "articulation"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Length estimate",
    "severity": "P2",
    "problem": "The length estimate is the template artifact 'see contract.length_target (extended)' rather than a human-readable value.",
    "fix": "Replace the line with '**Length estimate:** 50-60 minutes' to match the value declared in 00-framing.md's ## Length block.",
    "category": "length"
  },
  {
    "file": "99-show-notes.md",
    "anchor": "Blurb",
    "severity": "P2",
    "problem": "The blurb walks the chapter's six-beat arc in narrative form, duplicating the framing's beat descriptions and inflating cross-file duplication risk if both reach NotebookLM.",
    "fix": "Compress the blurb to a single paragraph under 120 words that names the thesis ('the apparent is evidence of the hidden') and the three governing images (body-and-soul, air-encompassing-all, the egg) without walking each beat in narrative order; the framing carries the beat detail, the show notes should carry the invitation.",
    "category": "duplication"
  }
]
```
