# 06 — Annotation + visual-differentiation prompt for *Ayyuhal Walad*

**Target book:** `CONTENT/drafts/books/ayyuhal-walad` (al-Ghazali, *O Beloved Son* — the book in the reader screenshot).
**Note:** you wrote "anwar/ayyuhal walad" — there is **no `anwar` book** in `CONTENT/drafts/books/` (slugs: `asaas-al-taveel`, `ayyuhal-walad`, `islr-mas-i`, `kitab-al-riyad`, `the-master-and-the-disciple`). Confirm whether "anwar" is a future book or an alias before this prompt runs against a second target.

> This prompt is the **executable spec** to hand to the implementing agent once the DISCUSS topics (03/04/05) converge. It is written so it can run unattended. It assumes Option A (canonical corpus) + sidecar markers + blackbox-backed popovers, but is written to degrade gracefully if only the blackbox exists.

---

## Goal
Produce, for each chapter of *Ayyuhal Walad*, a **sidecar annotation file** (`<chapter>.annotations.json`) whose every entry is **verified against the wisdom corpus via the MCP blackbox**, so the reader renders deterministic visual differentiation (Quran / hadith / Arabic-term / topic cross-reference) without live regex or LLM guessing.

## Inputs
- Chapter text: `CONTENT/drafts/books/ayyuhal-walad/chapters/ch{NN}-*.{txt,md}` (5 chapters).
- Glossary overlay: `.../ayyuhal-walad/_system/glossary.yml` (phonetic ↔ Arabic script).
- MCP blackbox: `source_library_server.py` (stdio for the agent; HTTP :4390 for verification). Build `mirror.db` first if Docker isn't running.

## Procedure (per chapter)
1. **Segment** the chapter into paragraphs (the reader already assigns `data-para-idx`; mirror that indexing).
2. **Detect candidates** — every Quran-shaped ref (`Q? S:A[-A]`), every hadith citation, every glossary/Arabic term, every phrase that may be a known topic.
3. **Verify each candidate through the blackbox** (do NOT trust the regex alone):
   - Quran → `quran_lookup(surah, ayat)`; keep only if it resolves. Attach canonical verse text + translation.
   - Term → `word_etymology(term)`; attach root + derivatives if found.
   - Topic phrase → `topic_search(keyword)` then `topic_get(id)`; attach topic id + linked ayats as cross-references.
   - Hadith → (corpus has KQUR `Ahadees`/`Narrators`; use the hadith query path) verify narrator/text exists.
4. **Classify**: `verified=true` only if the blackbox confirmed it. Unverified candidates are recorded with `verified=false` and `needs_review=true` (surface in the workbench, never render as authoritative).
5. **Emit** `<chapter>.annotations.json`:
   ```json
   { "book": "ayyuhal-walad", "chapter": "ch03-the-path", "generated": "<iso>",
     "markers": [
       { "para_idx": 4, "start": 112, "end": 118, "text": "2:153",
         "type": "quran", "canonical_id": "2:153", "verified": true,
         "payload": { "arabic": "...", "translation": "..." } },
       { "para_idx": 7, "start": 33, "end": 39, "text": "sabr",
         "type": "term", "canonical_id": "root:ص-ب-ر", "verified": true,
         "payload": { "root": "...", "derivatives": ["..."] } }
     ] }
   ```
6. **Do NOT mutate the chapter prose.** Markers are out-of-band (keeps `.txt` clean, survives re-authoring, matches the existing glossary-overlay pattern).

## Visual-differentiation contract (reader side)
Each `type` maps to the existing `ref-categories` treatment (`plan-dashboard/src/lib/reader/ref-categories/builtin/`): quran = amber 📖, hadith = green ✦, term = purple ʿ. The reader prefers sidecar markers over live regex when the sidecar exists. Popovers pull from `:4390`, not quran.com/Gemini.

## Acceptance
- Every chapter has a sidecar; `verified=true` ratio reported per chapter.
- Zero prose mutations (diff the `.txt` before/after = empty).
- Reader renders markers with correct per-type visual treatment and corpus-backed popovers.
- Unverified candidates appear in the workbench review lane, not as authoritative refs.

## Degradation
- If `mirror.db` and Docker are both unavailable → abort with a clear message (do not fall back to quran.com/Gemini for "verified" markers; an unverifiable marker must be `verified=false`).
- Interpretive tags (`esoteric / reality / sharia`) are **out of scope** for this automated pass — they remain human judgment in the workbench (optionally blackbox-*suggested* per doc 04, but never auto-applied).

## Dependencies (must land first)
- Corpus decision (doc 03) — at minimum the blackbox must resolve against *something* (Docker DBs or mirror).
- `verify_and_classify` tool + built `mirror.db` (doc 04).
- Reader sidecar-render path (doc 04).
These are why this prompt is **documented now but not executed** — it sits behind the three DISCUSS decisions.
