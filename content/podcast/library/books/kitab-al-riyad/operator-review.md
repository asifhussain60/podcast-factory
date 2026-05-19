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

## 6. Approval

When ready to resume:

- [ ] I approve this transcript — proceed with Phase 0c

---

## What happens on resume

When you signal "resume KaR":
1. I patch `refined-english.md` with any inline edits from `english-transcript.md` (if you edited the top-level mirror)
2. I integrate your bullets above into a one-page operator brief
3. I run `python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad` — the orchestrator picks up at Phase 0c (window 10/13 in progress will be the first window it touches)
4. The remaining Phase 0c → 0d → 0e → 0f-halt path executes (~30-40 more minutes to the next operator gate at Phase 0f)

If you find no issues, just say "resume KaR, transcript LGTM" and I'll skip the patch step.
