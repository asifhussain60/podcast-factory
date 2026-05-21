# Operator Review — Kitab al-Riyad English Transcript

**Halt point:** After Phase 0b (English refinement), before Phase 0c (Arabic phonetic pass). Halted by manual SIGINT on 2026-05-19 at 15:34 PT.

**Source artifact:** `_system/source/text/refined-english.md` (3,709 lines, ~486 KB)
**Top-level mirror for review:** `english-transcript.md` (same content, easier path)

Mark issues below. When done, type "halt KaR resume" in the chat — I'll patch the transcript per your notes and resume Phase 0c.

---

## How to use this file

You have **three** ways to give feedback:

1. **Inline edits** — edit `english-transcript.md` directly. Your changes flow into Phase 0c's input on resume.
2. **Marginal comments here** — add bullets below; I'll integrate them when resuming.
3. **Free-form chat** — just tell me in chat what you found; I'll patch the file before resume.

The pipeline does NOT have P22 code wired up yet (that's a separate W2 implementation task). So your feedback flows through me, not through the orchestrator's prompt context directly. Once P22 lands, this workflow becomes automatic.

---

## 1. Translation issues (page-anchored)

If a passage reads wrong in English, note the page number + brief description:

- Page __ — (issue)
- Page __ — (issue)

## 2. Missing or scrambled passages

If you spot a page that's clearly missing or the OCR went sideways:

- Page __ — (description)

## 3. Glossary additions

Arabic terms that should be added to `_system/concept-glossary.md` (or `_system/pronunciation.md`) with operator-approved glosses:

- **term** — (gloss / pronunciation correction)

## 4. Pronunciation corrections

Names/terms NotebookLM is likely to mangle; add to `_system/mangle-map.md`:

- (term) → (correct pronunciation hint)

## 5. Free-form comments

Anything else — voice notes for the framing, chapters that should be split/merged, factual concerns, sensitive material to flag:

(your notes here)

## 6. Translation collision: *abwāb* vs *fusūl* both rendered "Chapter"

Phase 0b's refinement translated both al-Kirmani's *abwāb* (10 "books" / parts) AND his *fusūl* (157 "sections" within those books) as "Chapter." You'll see passages like:

- Line 514: **"Chapters of the Book"** = al-Kirmani's TOC of the 10 *abwāb*
- Line 516: **"Chapter One"** (in the TOC) = Bāb 1 of 10
- Line 558: **"Chapter One"** (start of body) = Fasl 1 of Bāb 1
- Line 849: **"Chapter Sixteen of Chapter One"** = Fasl 16 of Bāb 1

I'll normalize this before Phase 0d runs:
- *Abwāb* → "Bāb 1" through "Bāb 10" (or "Book 1"–"Book 10")
- *Fusūl* → "§1" through "§157" globally, OR "Bāb N · §M" within-bāb numbering

**Operator preference (chosen 2026-05-19):**
- [x] **Bāb N · §M** within-bāb numbering (more honest to the source)
- [ ] ~~Book N · Section M~~
- [ ] ~~Part N · Chapter M~~

Chapter file slugs will be: `ch01-bab-1-perfection-of-the-soul.txt` … `ch10-bab-10-eschatology.txt` (final titles per Phase 0d). Cross-references: "as we saw in §3 above" within-bāb; "recall Bāb 8 · §22 on motion and rest" across-bāb. Hosts naturally explain *bāb* the first time it appears in Ep1; the concept-glossary will gain `bāb` and `fasl` as entries during Phase 0e.

## 7. Content range — skip editor's apparatus + back-matter indexes

The file is 3,709 lines, 254 PDF pages. The actual al-Kirmani body content is **PDF pages 52–232 (lines 498–3,127)**. Front matter (editor's intro by Arif Tamir, 1960) is pages 1–51 (~13% of the file); back matter (six indexes) is pages 233–254 (~16%). Skipping these saves ~29% of LLM token spend on Phases 0c (phonetic), 0e (enrichment), and 11 (per-chapter framing) — meaningful real money on this book.

Per the new content-range convention (handbook: `content/podcast/.skill/handbook/book-dir-layout.md` §"Per-book content range"; plan: P4.10), I'll emit `_system/source/text/content-range.md` from your decisions below before Phase 0c resumes.

**Heuristic-suggested defaults (pre-filled from my structural analysis):**

```yaml
body_starts_at_page: 52      # al-Kirmani's own preface opens here (line 498)
body_ends_at_page: 232       # Bāb 10's last section ends here (line 3,127)
include_author_preface: true # al-Kirmani's own preface (page 52) IS content
include_author_toc: false    # al-Kirmani's TOC of 10 abwāb (page 53) is structural-only
```

Front matter being skipped (pages 1–51):
- p. 1–6: cover + half-titles
- p. 7–32: editor's Introduction — bios of al-Razi / al-Sijistani / al-Kirmani
- p. 33–39: editor's bibliographic list of al-Kirmani's 25 works + structural overview
- p. 40–43: editor's editing notes (manuscripts A and B, Ivanow)
- p. 44–51: editor's TOC summary in their own words

Back matter being skipped (pages 233–254):
- p. 233–237: Subject Index
- p. 239–241: Index of Qurʾānic Verses
- p. 243–245: Index of manuscripts and printed books
- p. 245–247: Index "Message — 21" (likely footnote index)
- p. 247–249: Index of Names
- p. 251–254: Index of cities and countries

**Confirmed 2026-05-19:**
- [x] Defaults above look right — emit `content-range.md` with body 52–232 (preface in, TOC out)
- [ ] ~~Override range~~
- [ ] ~~No content-range~~

`_system/source/text/content-range.md` emitted alongside this approval commit.

## 8. Approval

- [x] **I approve this transcript — proceed with Phase 0c** (2026-05-19)

### Caveat: P4.10 + P22 enforcement code not yet shipped

The content-range convention (P4.10) and operator-review prompt-injection (P22) are documented in the plan but the orchestrator code that READS `content-range.md` and the `<operator-review>` XML block is in W2 (P22) + a future commit (P4.10). For THIS resume:

- `content-range.md` is committed as a record of operator intent — **honored by future runs** once P4.10 ships
- The current orchestrator will process the **whole 254-page transcript** at Phase 0c/0d/0e (Loop N may spuriously flag the editor's 25-work bibliography; ~$3-5 extra LLM cost)
- The Bāb N · §M naming preference is captured here — **not auto-injected into Phase 0d's prompt** until P22 ships; Phase 0d's LLM will choose chapter naming heuristically

Two options for actually resuming:

**Option A — Resume now, accept the gap.** Live with whole-transcript processing + heuristic chapter naming for this single run. Future runs honor preferences once P22 + P4.10 land. Net cost: ~$3-5 extra on Phase 0c-0e for this book.

**Option B — Ship P22 + P4.10 minimal code first, then resume.** ~1-2 hours of focused work to wire content-range.md reading into Phase 0d and operator-review.md injection into Phase 0c+ prompts. Then resume honors all operator decisions.

Operator's call. Either way, this commit captures the decisions so they're durable.

---

## What happens on resume

When you signal "resume KaR":
1. I patch `refined-english.md` with any inline edits from `english-transcript.md` (if you edited the top-level mirror)
2. I integrate your bullets above into a one-page operator brief
3. **§6 abwāb/fusūl decision**: I normalize the translation collision per your choice before Phase 0d
4. **§7 content range**: if confirmed, I emit `_system/source/text/content-range.md` with `body_starts_at_page: 52`, `body_ends_at_page: 232`. Phase 0d, 0e, 11 honor it (per P4.10). If "no content-range" is chosen, the whole transcript flows through as today.
5. I run `python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad` — the orchestrator picks up at Phase 0c
6. Phase 0c → 0d → 0e → 0f-halt executes (~30-40 more minutes to the next operator gate at Phase 0f), or less if content-range skips the editor's apparatus + indexes

If you find no issues, just say "resume KaR, transcript LGTM" and I'll use the content-range defaults from §7.
