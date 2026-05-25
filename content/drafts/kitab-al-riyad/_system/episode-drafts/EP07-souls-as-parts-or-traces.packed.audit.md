## Inventory

- **Chapter EP07 — "Souls As Parts Or Traces"** (bundle directory: root of consolidated input)
  - framing: PRESENT (`00-framing.md`)
  - primary source: MISSING
  - key passages: MISSING
  - context pack: MISSING
  - discussion spine: MISSING
  - show notes: MISSING

## Chapter Findings

### Chapter EP07: Souls As Parts Or Traces

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `00-framing.md` | "eceivership. The soul's continuity with what stands" | Stranded/corrupted paragraph appended after the first "Do not read this prompt aloud" closer. Begins mid-word ("eceivership"), duplicates content already covered in Beats 4–6, and is followed by a second "Do not read this prompt aloud" closer — file has two endings. | Delete the entire stranded block from "eceivership. The soul's continuity..." through "...where bodies cannot reach." and the duplicate "Do not read this prompt aloud" line. End the file at the first "Do not read this prompt aloud." sentence following Essential Teachings. |
| P1 | `00-framing.md` | "Host dynamic" | The two-sentence assignment "The female host is Advocate A (protagonist + verdict). The male host is Advocate B (challenger). Roles are locked at episode start; no swap mid-episode." appears verbatim twice — once at the tail of "Stable role-labels" and again as the opening of "Host dynamic". Intra-file verbatim repetition; NotebookLM hosts will surface it as a stutter. | Remove the duplicate role-assignment sentences from the end of "Stable role-labels". Keep them only in the "Host dynamic" section. |
| P1 | `00-framing.md` | "Pronunciation" | Arabic terms are transliterated only (walaya, sharia, nawafil, Hadith Qudsi, Ma'ad, Mawlana, Alawi, Hikam, Asrar) with no Arabic-script presence anywhere in the bundle. House style requires Arabic terms in Arabic script with English gloss preceding in parentheses; transliteration is permitted only inside a pronunciation appendix keyed off the Arabic-script form. | Add Arabic-script form alongside each pronunciation entry: e.g., "Pronounce walaya (ولاية) as 'wa-LAY-ya.'" Then audit the body of the framing and replace running-text transliterations with the format `English gloss (Arabic script)`. |
| P1 | `00-framing.md` | "Pronunciation" | Pronunciation guidance is embedded inline in the framing rather than separated as a referenced appendix; framing does not point hosts to it as an appendix lookup. | Move the pronunciation block to a clearly labeled `## Pronunciation appendix` at the end of the framing (after Landing), and add a one-line reference near the top of the framing directing hosts to consult it for any Arabic term. |
| P1 | `00-framing.md` | "Beat 6: Stakes close with thesis" | "Two bow-lengths" is invoked twice as a Quran reference (Beats 5 and 6, plus the corrupted tail) without ever being cited in the required `Q\|53:9` form. | Insert the citation immediately after the Beat 6 reference to two bow-lengths on its own line: `Q\|53:9`. Remove the duplicate occurrence in the corrupted tail when that block is deleted. |
| P1 | `00-framing.md` | "Background" | The framing references "Chapter Three settled that prime matter is the trace of the Second" — a cross-chapter dependency presented without resolution inside this single-episode bundle, inviting hosts to improvise the prior chapter's argument. | Convert to a one-sentence self-contained restatement that does not require the listener to have heard a prior episode: name the conclusion in this chapter's terms without pointing at "Chapter Three". |
| P2 | `00-framing.md` | "Pronunciation" | "Hadith Qudsi" appears in the role labels and pronunciation list but the gloss says God speaks in the first person — house style requires "Allah", not "God". | Replace "God speaks in the first person" with "Allah speaks in the first person" in the Hadith Qudsi pronunciation entry. |
| P2 | `00-framing.md` | "Stable role-labels" | "Ali ibn Abi Talib (peace be upon him)" — house style requires "Maulana Ali" rather than "Imam Ali" as the standing label; current label "Commander of the Faithful" is acceptable, but the proper-name parenthetical should align. | Change the parenthetical to "Maulana Ali ibn Abi Talib (peace be upon him)" so the proper-name reference uses the house style. |
| clean | `00-framing.md` | Cohesion | Single thesis cleanly stated, repeated verbatim at Beats 1, 4, 6 as instructed. Opening, middle, closing turns are present and resolved. | clean |
| clean | `00-framing.md` | Single-thesis discipline | Thesis is named in one sentence and locked: "The speaking souls are the second emanation: what is in the whole is found in the part by rank, not by composition." | clean |

## Episode Findings

### Episode EP07: Souls As Parts Or Traces

| Severity | File | Anchor | Problem | Fix |
|---|---|---|---|---|
| P0 | `00-framing.md` | "Host dynamic" | Host-role assignment is inverted relative to the house rule (male = scholar/teacher, female = student/learner). Here, the female host (Advocate A) holds the scholar/verdict role and the male host (Advocate B) holds the challenger role. NotebookLM will execute the framing literally and reverse the intended voice mapping. | If the inversion is deliberate, add an explicit single-sentence override at the top of "Host dynamic" stating that this episode intentionally inverts the default male=scholar / female=student pairing. Otherwise, swap: Advocate A = male (protagonist + verdict), Advocate B = female (challenger), and rewrite the seeded challenger lines accordingly. |
| P0 | (missing) | bundle root | No pronunciation appendix exists as a discrete artifact, and bundle ships only the framing — there is no source the hosts can ground in. Arabic terms are present; the framing's inline pronunciation is the only guard, and it is not referenced as an appendix. | Create `01-pronunciation.md` containing the Arabic-script + phonetic table, and reference it in the framing top-matter as the canonical lookup. Remove the inline duplicate from the framing once the appendix file exists. |
| P1 | (missing) | bundle root | Five of the six standard bundle artifacts are absent: primary source, key passages, context pack, discussion spine, show notes. NotebookLM will receive only the framing and improvise the source material. | Add the five missing artifacts: `02-primary-source.md` (chapter text), `03-key-passages.md`, `04-context-pack.md`, `05-discussion-spine.md`, `06-show-notes.md`. Until they exist, the bundle cannot ship. |
| P1 | `00-framing.md` | "Opening directive" | No "skip the intro" instruction anywhere in the framing. NotebookLM hosts will burn 60–90 seconds on default context-setting before reaching Beat 1. | Add a one-line directive at the very top of "Opening directive": "Skip the intro. Open in the middle of the dispute as instructed in Beat 1." |
| P1 | `00-framing.md` | "Three-part focus" | No target episode length is declared, and there is no calibration of source volume against length. Six beats with three tensions and multiple analogies can easily run 25+ minutes if hosts unpack at lecture pace. | Add a "Length target" line under "Opening directive": state the target (e.g., "Length target: 18–22 minutes") and note that the spine and beats are calibrated for that window. |
| P1 | `00-framing.md` | "Landing — Beat 1: Unresolved tension" | The framing closes by posing an open question — "is the chain the guarantee, or is it something the believer must actively hold?" — which is a cliffhanger in a single-episode bundle and a hallucination trigger for NotebookLM hosts to improvise a payoff. | Either resolve the question inside Beat 6 with a one-sentence answer derived from the chapter text, or strip the question from "Landing" and replace it with a closing reflection that returns to the verdict without inviting follow-up. |
| P1 | `00-framing.md` | "Citation in body" | No spoken-form citation appendix exists for the implicit Quranic reference (two bow-lengths → Q\|53:9). Read aloud, "Q\|53:9" sounds broken. | Create a citation spoken-form appendix (either as a section in framing labeled "Citation spoken-form appendix" or as `01b-citations.md`) mapping each citation to natural speech: e.g., `Q\|53:9` → "the Quran, chapter fifty-three, verse nine." Reference it from the framing. |
| P2 | `00-framing.md` | "Opening directive" | No NotebookLM Audio Overview format is declared (Deep Dive, Brief, Critique, or Debate). The framing's structure (two advocates, three tensions, six beats, locked verdict-bearer) clearly targets **Debate**, but it is not stated. | Add a "Format" line under "Opening directive": "Format: Debate. Advocate A holds the verdict, Advocate B presses the strongest opposing case." |
| P2 | `00-framing.md` | "Central tensions" | The three tensions are dense and overlap on the same author-versus-successor axis (parts vs. traces vs. second emanation; substance-partness vs. rank; Intellect-as-Word). Without explicit beat allocation, NotebookLM may collapse them into one and oversimplify. | Add a single line per tension naming which Beat it lives in (Tension 1 → Beat 2/3, Tension 2 → Beat 6, Tension 3 → Beat 5) so the host pair does not re-litigate the same axis three times. |
| clean | `00-framing.md` | Spine completeness | Opening hook (Beat 1), four discussion beats (Beats 2–5), bridging tension (Beat 5's Intellect-Word move), closing reflection returning to the hook (Beat 6). | clean |
| clean | `00-framing.md` | Banter suppression | "Anti-noise rules", "Do not", and "Tone constraints" sections explicitly suppress surprise interjections, back-channel affirmations, formal-essay transitions, recap-before-respond, and re-citation. | clean |

## Cross-Bundle Patterns

Only one bundle is present in the consolidated input, so cross-bundle patterns cannot be assessed directly. One systemic risk is visible from the single bundle: the framing carries the full weight of all six standard artifacts. If the rest of the book is shipping in this shape, every episode is one truncated paste or one corrupted closer away from a P0 audio failure, because there is no parallel primary-source or discussion-spine file to back-fill from. Recommend an audit pass at the bundle-builder level to confirm whether the other six artifacts exist on disk and were dropped during consolidation, or whether they were never produced. The end-of-file corruption ("eceivership..." stranded after the first "Do not read this prompt aloud") looks like a paste-or-template-merge artifact rather than human error, which would imply other bundles in the same book may be carrying the same trailing block — worth scanning the rest of `content/drafts/kitab-al-riyad/_system/episode-drafts/` for the same corruption signature.

## Claude Code Instruction Block

```claude-code-fixes
[
  {
    "file": "00-framing.md",
    "anchor": "eceivership. The soul's continuity with what stands",
    "severity": "P0",
    "problem": "Stranded/corrupted paragraph appended after the first closing 'Do not read this prompt aloud' line, beginning mid-word ('eceivership'), duplicating Beat 4-6 content, and followed by a second 'Do not read this prompt aloud' closer — the file has two endings.",
    "fix": "Delete the entire block beginning with 'eceivership. The soul's continuity with what stands above it is real,' through '...where bodies cannot reach.' and then delete the second 'Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.' line. The file must end at the first 'Do not read this prompt aloud.' sentence that follows the Essential Teachings paragraph.",
    "category": "duplication"
  },
  {
    "file": "00-framing.md",
    "anchor": "Host dynamic",
    "severity": "P0",
    "problem": "Host-role assignment is inverted relative to the house rule that male = scholar/teacher and female = student/learner. Female host (Advocate A) is assigned scholar+verdict; male host (Advocate B) is assigned challenger. NotebookLM will execute literally and reverse the intended voice mapping.",
    "fix": "Decide intent: if inversion is intentional for this chapter, insert at the top of 'Host dynamic' a single sentence: 'This episode intentionally inverts the default male=scholar / female=student pairing because the verdict-bearer in this adjudication is rhetorically female-coded in the source.' If unintentional, swap the assignments throughout: Advocate A = male (protagonist + verdict), Advocate B = female (challenger), and update every pronoun and seeded line accordingly.",
    "category": "host-role"
  },
  {
    "file": "00-framing.md",
    "anchor": "The female host is Advocate A (protagonist + verdict)",
    "severity": "P1",
    "problem": "The two sentences assigning Advocate A and Advocate B their roles appear verbatim twice: once at the end of 'Stable role-labels' and again as the opening of 'Host dynamic'. Intra-file verbatim repetition will surface as a stutter in NotebookLM.",
    "fix": "Delete the duplicated paragraph at the end of 'Stable role-labels' (the three sentences beginning 'The female host is Advocate A (protagonist + verdict).'). Keep the assignment only in the 'Host dynamic' section.",
    "category": "duplication"
  },
  {
    "file": "00-framing.md",
    "anchor": "Pronunciation",
    "severity": "P1",
    "problem": "All Arabic terms are transliterated only (walaya, sharia, nawafil, Hadith Qudsi, Ma'ad, Mawlana, Alawi, Hikam, Asrar) with zero Arabic-script presence anywhere in the bundle. House style requires Arabic terms in Arabic script with English gloss preceding in parentheses; transliteration belongs only inside a pronunciation appendix keyed to the Arabic-script form.",
    "fix": "Add the Arabic-script form to every pronunciation entry: e.g., 'Pronounce walaya (ولاية) as wa-LAY-ya.' Then sweep the body of the framing and replace running-text transliterations with the format 'English gloss (Arabic script)' — e.g., 'spiritual guardianship (ولاية)', 'revealed divine law (شريعة)', 'voluntary devotional works (نوافل)', 'sacred saying (حديث قدسي)'.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "Pronunciation",
    "severity": "P1",
    "problem": "Pronunciation guidance lives inline in the framing rather than as a separated appendix; the framing does not reference it as an appendix lookup, so hosts will treat it as another instruction block rather than a runtime reference.",
    "fix": "Move the entire Pronunciation block to the end of the file as a section titled '## Pronunciation appendix' placed after 'Landing'. Insert a one-line reference under 'Opening directive': 'Pronunciation appendix lives at the end of this framing — consult it for every Arabic term before speaking.'",
    "category": "pronunciation"
  },
  {
    "file": "00-framing.md",
    "anchor": "Beat 6: Stakes close with thesis",
    "severity": "P1",
    "problem": "The 'two bow-lengths' Quranic reference appears multiple times without ever being cited in the required Q|Surah:Verse form. Hosts cannot ground the reference; NotebookLM may misattribute it.",
    "fix": "On a new line immediately after the first mention of 'two bow-lengths' in 'Beat 5: Non-bodily correction', insert: 'Q|53:9'. Do the same after the 'two bow-lengths' mention in Beat 6. (The duplicate mention in the corrupted tail is removed by the P0 deletion fix.)",
    "category": "citation"
  },
  {
    "file": "00-framing.md",
    "anchor": "Background",
    "severity": "P1",
    "problem": "Framing references 'Chapter Three settled that prime matter is the trace of the Second' — a cross-chapter dependency in a single-episode bundle. Hosts will improvise the prior chapter's argument because the bundle does not include it.",
    "fix": "Rewrite the 'Background' paragraph so the prime-matter / Second relationship is stated in self-contained form without pointing at 'Chapter Three'. One self-contained sentence is enough: 'Prime matter is the trace of the universal Soul's source-Intellect; the speaking souls are the open question.' Remove the cross-chapter pointer.",
    "category": "cohesion"
  },
  {
    "file": "00-framing.md",
    "anchor": "Opening directive",
    "severity": "P1",
    "problem": "No 'skip the intro' instruction. Default NotebookLM hosts will spend 60-90 seconds on context-setting before reaching Beat 1.",
    "fix": "Add as the first line under 'Opening directive': 'Skip the intro. Open in the middle of the dispute as instructed in Beat 1.'",
    "category": "format"
  },
  {
    "file": "00-framing.md",
    "anchor": "Opening directive",
    "severity": "P1",
    "problem": "No target episode length is stated. Six beats with three dense tensions easily run 25+ minutes at lecture pace.",
    "fix": "Add a line under 'Opening directive': 'Length target: 18-22 minutes. The spine and beats are calibrated for this window — do not pad and do not over-summarize.'",
    "category": "length"
  },
  {
    "file": "00-framing.md",
    "anchor": "Landing — Beat 1: Unresolved tension",
    "severity": "P1",
    "problem": "'Landing' closes by asking 'is the chain the guarantee, or is it something the believer must actively hold?' — a cliffhanger inside a single-episode bundle. Hosts will improvise a payoff and hallucinate.",
    "fix": "Either resolve the question with a one-sentence answer grounded in the chapter ('The chain is the guarantee; the believer's obedience is the act by which the rank is reached.'), or strip the question entirely and replace 'Landing — Beat 1: Unresolved tension' with a closing reflection that returns to the verdict without opening a new thread.",
    "category": "cohesion"
  },
  {
    "file": "00-framing.md",
    "anchor": "Pronunciation — Hadith Qudsi",
    "severity": "P1",
    "problem": "The Hadith Qudsi gloss says 'in which God speaks in the first person'. House style requires 'Allah', not 'God'.",
    "fix": "In the Hadith Qudsi pronunciation entry, replace 'God speaks in the first person' with 'Allah speaks in the first person'.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "Citation spoken-form appendix",
    "severity": "P1",
    "problem": "No citation spoken-form appendix exists. When the Q|53:9 citation is added (per the citation fix), reading 'Q pipe fifty-three colon nine' aloud will sound broken.",
    "fix": "Add a section at the end of the framing titled '## Citation spoken-form appendix' containing a single mapping: 'Q|53:9 → the Quran, chapter fifty-three, verse nine.' Add a one-line reference under 'Opening directive': 'Citation spoken-form appendix lives at the end — use the spoken form, never read the Q-pipe notation aloud.'",
    "category": "citation"
  },
  {
    "file": "00-framing.md",
    "anchor": "Stable role-labels",
    "severity": "P2",
    "problem": "'Ali ibn Abi Talib (peace be upon him)' uses the bare proper-name form. House style prefers 'Maulana Ali' as the standing label.",
    "fix": "In the 'Commander of the Faithful' bullet, change 'the Father of Imams, Ali ibn Abi Talib (peace be upon him)' to 'the Father of Imams, Maulana Ali ibn Abi Talib (peace be upon him)'.",
    "category": "articulation"
  },
  {
    "file": "00-framing.md",
    "anchor": "Opening directive",
    "severity": "P2",
    "problem": "No NotebookLM Audio Overview format is declared. The framing's structure (two advocates, three tensions, locked verdict-bearer, explicit challenger-friction patterns) clearly targets Debate, but it is not stated, so NotebookLM may default to Deep Dive.",
    "fix": "Add under 'Opening directive': 'Format: Debate. Advocate A holds the verdict throughout; Advocate B presses the strongest opposing case and does not concede until Beat 6.'",
    "category": "format"
  },
  {
    "file": "00-framing.md",
    "anchor": "Central tensions",
    "severity": "P2",
    "problem": "The three tensions overlap on the same author-versus-successor axis and could collapse into one in audio without explicit beat allocation.",
    "fix": "Append one line to each tension naming the Beat that carries it: under Tension 1 add 'Carried in Beats 2-3.'; under Tension 2 add 'Carried in Beat 6.'; under Tension 3 add 'Carried in Beat 5.'",
    "category": "spine"
  }
]
```
