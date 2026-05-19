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

**Operator preference (choose one or write your own):**
- [ ] **Bāb N · §M** within-bāb numbering (more honest to the source)
- [ ] **Book N · Section M** plain-English alternative
- [ ] (your preferred convention)

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

**Confirm or override:**
- [ ] Defaults above look right — emit `content-range.md` as-is
- [ ] Override → `body_starts_at_page: ___`, `body_ends_at_page: ___`
- [ ] No content-range for this run — process whole transcript (backward-compat)

## 8. Approval

When ready to resume:

- [ ] I approve this transcript — proceed with Phase 0c

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
