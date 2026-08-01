> Template from: Betsy Beyer, Chris Jones, Jennifer Petoff, and Niall Richard Murphy. ["Site Reliability Engineering."](https://landing.google.com/sre/book/chapters/postmortem.html).

# The hosts were handed translations instead of phonetics (RCA-007)

### Date

2026-08-01 (incident window: 09:36 AM – 02:16 PM EST; the latent defects date to
the beginning of the book pipeline and to 2026-06-08)

### Authors

Claude (investigation + fix), reviewed by Asif

### Status

RESOLVED 2026-08-01. All four root causes fixed at source and committed. Eight
terms were escalated to Asif and settled by his ruling rather than by the
pipeline. Open corrective actions: AI-3, AI-4.

### Summary

The first audio run of *Degrees of Excellence* came back with mangled Arabic:
the hosts said "Archon" for `arkan`, "Mathdul" for `mafdul`, "Mazbuck" for
`ya'sub`. The obvious reading was model drift in NotebookLM. It was not. The
framing prompt had literally instructed the model to write an English
translation where a phonetic form belonged, and a downstream compression pass
had been told to strip "diacritics or hyphen-CAPS" to save characters. The
hosts were told to say each term "using its phonetic form" and then handed a
translation. They complied.

Underneath that sat three further defects, each independently sufficient to
break pronunciation on its own, and none of which any gate could see:

- `_system/pronunciation.md`, documented as the per-book override authority
  since the books began, **was read by no code at all**. Its 41 rows reached
  the audio only because a human had pasted them into six framings by hand.
- The cross-book pronunciation library was **two-thirds unreachable**. 145 of
  211 rows carried an Arabic-script key while every consumer looked up by
  romanisation; those rows had never been found by anything.
- The probe built to settle pronunciations **could not settle them**. Its
  source was phrased as stage directions, so NotebookLM discussed a glossary
  instead of reading one: 9 of 39 terms were spoken in run 1.

### Impact

Six published episodes of *Degrees of Excellence* carried mispronounced Arabic
and had to be re-authored and regenerated. One probe run (5:06 of audio, $0.03
Azure transcription, plus a NotebookLM generation and a human listen) was spent
discovering that the probe's own source shape was wrong rather than learning
anything about the terms. Two further probe cycles and roughly four and a half
hours of session time were spent reaching a settled term ladder.

No reader-facing print deliverable was affected — this is an audio-lane defect
throughout. No content was lost. The corpus-scale near-miss is recorded under
"Where we got lucky".

### Root Causes

**1. The prompt asked for the defect.** `_authoring/_framing.py` instructed the
model to emit `- TermA: English-name-or-plain-translit`. The compression
re-author, which fires on nearly every framing, then added "without diacritics
or hyphen-CAPS". Between them, the two prompts specified exactly the output that
was observed. This was never drift; it was the system working as written.

**2. A documented authority was never wired to a consumer.**
`_system/pronunciation.md` was referenced by `scaffold_book.py` (which writes
the empty stub) and by prose in `SKILL.md`. Nothing read it. A file can be
canonical in documentation and inert in code, and nothing in the repo made that
contradiction visible.

**3. A key that silently changed meaning.** `record()` keyed on
`normalize_key(term)`, which does not transliterate. June's callers passed
Arabic script as `term`; later callers passed the romanisation. Both were
"correct" against the function signature, and the library quietly split into two
namespaces, one of which no consumer could reach.

**4. Instructions inside a NotebookLM source are discussed, not obeyed.** The
probe's source numbered its terms as imperatives ("1. Next, say **wa-LAA-ya**").
NotebookLM conversationalises any source it is given, so it produced a themed
episode *about* the glossary. Coverage is determined by what the source
*contains*, never by what it *asks for* — a property of the tool that the probe's
design had not internalised.

### Trigger

Asif listened to the first generated episodes of *Degrees of Excellence* and
heard the mangled terms.

### Resolution

`_pronunciation_block.py` now compiles the framing's pronunciation block at build
time. The model still chooses *which* terms need help — that judgement is
per-episode and requires reading the chapter — but every *value* now comes from
`knowledge/term_render.py`, the same ladder the probe and the ElevenLabs
dictionary already share. The ladder gained rung 0 (the per-book override table,
where a human who has heard the audio outranks every heuristic) and rung 3 (a
`confirmed` ledger phonetic), which is what finally makes `_system/pronunciation.md`
load-bearing.

`entry_key()` now prefers the romanisation whenever the term is script and a
usable romanisation exists, so a new row cannot repeat defect 3; `lookup()`
gained a secondary index on the script, because both call patterns are real and
re-keying must not lose either.

The probe's source was rebuilt as a genuine glossary — one numbered entry per
term carrying its spoken form and a sentence, with no imperative anywhere in it —
and the instructions moved to the framing, which now states the exact term count,
requires entries in order, forbids theming, and carries the forbidden-vocabulary
block the probe framing had been the only framing in the repo to lack.

Two probe runs then settled the terms empirically: 21 confirmed and written to
the cross-book ledger, 38 unproven respellings withdrawn in favour of plain
transliterations that measurably outperformed them, and 8 terms that no
respelling could rescue escalated to Asif, who ruled they become English glosses
(`walaya` → "Spiritual Guardianship").

### Detection

Human ear, on finished audio — the latest and most expensive detection point
available. Every automated gate passed: `podcast-challenger` validates the upload
bundle's structure and cannot hear anything, and the framing validator checked
the pronunciation block's *shape* (`- term: value`) while having no way to
ask whether the value was a phonetic form or a translation.

The three latent defects were found only because the first fix prompted a read of
the surrounding code rather than a hand-correction of the six affected files.

### Action Items

| # | Action | Type | Owner | Status |
|---|---|---|---|---|
| AI-1 | Compile the framing pronunciation block from the ladder; stop asking the model for values | fix | Claude | DONE (`8f21a36`) |
| AI-2 | Re-key the pronunciation library on romanisation; add a script secondary index | fix | Claude | DONE (`7247646`) |
| AI-3 | Probe the 92 unheard `confirmed` respellings from 2026-06-08 before any of them can reach a framing | mitigate | Asif + Claude | OPEN — they are inert today; promotion without a probe would inject 92 unheard respellings at corpus scale |
| AI-4 | Add a probe that fails when a documented authority file has no code reader | prevent | Claude | OPEN — this is the generalisable half of root cause 2 |
| AI-5 | Rebuild the probe source as a glossary; move instructions to the framing | fix | Claude | DONE (`500fd2e`) |

### Lessons Learned

#### What went well

The fix went to the prompt rather than to the six files the prompt had produced.
An earlier pass the same morning (`ea53024`, `4b7dd99`) had hand-corrected the
output and left both prompts intact — which is precisely why the defect was
still live at 11:35 AM. Fixing the generator is what turned a six-file patch
into a repo-wide correction.

Withdrawing the 38 respellings *without deleting them* was the right shape: the
probe builds its term inventory from that table, so a deleted row would have
dropped the term from the very run meant to settle it. A `plain` row names a
term and asserts nothing about its sound.

Refusing to promote all 145 unreachable rows — deviating from what had already
been approved, on the grounds that 92 of them were plainly generator output
carrying a `confirmed` status no human had ever earned — prevented the single
largest potential harm in this incident.

#### What went wrong

Three defects had been latent for months behind documentation that described a
system nobody had verified existed. "Documented as the authority" was treated as
equivalent to "read by the code" in every conversation about pronunciation until
someone grepped for the readers.

The same class of mistake appeared twice in one morning: hand-correcting
generated output instead of fixing the generator (09:36 AM), then doing it
properly two hours later. That repetition is what makes this RCA mandatory
rather than optional.

#### Where we got lucky

The 92 unheard `confirmed` respellings were unreachable *because of* a separate
bug. Had the key defect not existed, `i-blis`, `ku-ran` and `AA-dam` would have
been sitting in the rung that decides what hosts say, across every book in the
corpus, for two months. The two defects cancelled — one bug held the other
harmless until both were found on the same afternoon.

### Timeline

All times EST, 2026-08-01.

| Time | Event |
|---|---|
| 09:36 AM | `ea53024` — six framings hand-corrected: real phonetics replace English glosses. **Prompts left intact.** |
| 09:43 AM | `4b7dd99` — audible scaffolding stripped, length cue settled |
| 11:35 AM | `8f21a36` — root cause found. The framing's block becomes compiled, not authored. `_system/pronunciation.md` becomes load-bearing as rung 0 |
| 11:41 AM | `500fd2e` — probe bundle rebuilt as a glossary before anyone listens to it |
| 01:13 PM | `2b621f9` — probe run 1 returns. 9 of 39 terms spoken; the probe's own shape is the second finding |
| 01:26 PM | `5a1632a` — 38 unproven respellings withdrawn on Asif's call; 2 proven values kept as control |
| 01:46 PM | `dde1de4` — probe run 2: all 39 terms spoken, 21 settled, plain transliteration beats respelling on every term longer than two syllables |
| 02:01 PM | `d97d9e3` — the 8 unsayable terms become English, per Asif's ruling |
| 02:08 PM | `7247646` — library key defect found and fixed; 66 reachable rows become 102 |
| 02:14 PM | `63e9dd8` — six ledger collisions and the `ta'wil` gloss settled |
| 02:16 PM | `7027027` — `walaya` becomes "Spiritual Guardianship" |

### Supporting information

- Ladder and rung definitions: [scripts/podcast/knowledge/term_render.py](../../scripts/podcast/knowledge/term_render.py)
- Compiled framing block: [scripts/podcast/_pronunciation_block.py](../../scripts/podcast/_pronunciation_block.py)
- Cross-book library: `content/knowledge-base/pronunciations.jsonl`
- Probe driver: [scripts/podcast/run_pronunciation_probe.py](../../scripts/podcast/run_pronunciation_probe.py)
- Closing agent: `pronunciation-probe-analyst`
