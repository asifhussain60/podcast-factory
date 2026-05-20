# Operator Review — Asaas al-Taʾwīl English Transcript

**Halt point:** After Phase 0b (English refinement, chunked across 5 windows), before Phase 0c (Arabic phonetic pass). Halted manually 2026-05-20 at 15:30Z by the orchestrator-aware Claude session on `mac-studio-primary`, following the KaR precedent (commits `f4e7970` halt + `09899d9` approval, 2026-05-19).

**Source artifact:** `_system/source/text/refined-english.md` (10,329 lines, ~759 KB — Phase 0b output)
**Top-level mirror for review:** `english-transcript.md` (same content, easier path; safe to edit inline)
**Companion:** `_system/source/text/chapters-rationale.md` (operator-authored episode plan, 67 lines)

When done, type **"resume asaas"** in chat — I'll integrate decisions and run `--resume asaas-al-taveel`.

---

## How to use this file

Three ways to give feedback:

1. **Inline edits** — edit `english-transcript.md` directly. Your edits flow into Phase 0c's input on resume.
2. **Marginal comments here** — add bullets in §§1–5; I'll integrate them.
3. **Free-form chat** — tell me in chat; I'll patch before resume.

P22.impl code is **NOT** shipped (per acceptance rows 202–211). This workflow is manual — feedback flows through Claude, not directly into the orchestrator's prompt context. Once P22.impl lands, the operator-review block auto-injects into Phase 0c+ prompts.

---

## 1. Translation issues (page-anchored)

If a passage reads wrong in English, note the PDF page number (`<!-- page N -->` marker in the transcript) + brief description:

- Page __ — (issue)
- Page __ — (issue)

## 2. Missing or scrambled passages

> ⚠️ **Pre-filled defect — Claude flagged on scaffold (2026-05-20):**
>
> **Pages 21–27 are MISSING from `refined-english.md`.** They exist in `_system/source/text/raw-extract.md` (the Phase 0a output) but were dropped during Phase 0b chunked refinement.
>
> The 7-page gap covers the **author's introduction**: al-Nuʿmān's own preamble, including his cross-reference to his earlier *Pillars of Islam* and his framing of why this book matters. `raw-extract.md` line 451+ has the heading "Author's Introduction / In the name of God, the Most Gracious…" — none of this made it into `refined-english.md`, which jumps from `<!-- page 18 -->` (editor's intro tail) straight to `<!-- page 28 -->` (mid-author-introduction, "The Messenger of Allah… every Qur'anic verse has an outer and an inner").
>
> **Why this matters:** the author's introduction is the only place al-Nuʿmān explicitly states his project — that this book is the foundational Ismaili treatment of *taʾwīl*. EP01's framing ("the hidden code") leans on this voice. Without pp. 21–27, the listener loses the author's own opening declaration.
>
> **Three options:**
>
> - [ ] **(A) Re-refine pages 21–27 from raw-extract before Phase 0c** (Recommended) — splice them into refined-english.md at line 320, between `<!-- page 18 -->` and `<!-- page 28 -->`. ~30 min of focused `claude -p` work.
> - [ ] **(B) Accept the gap; flag for Phase 0g** — let EP01's framing rely on PDF pp. 3–18 (editor's intro) for author voice; document the gap in registry.md.
> - [ ] **(C) Operator splices manually** — read raw-extract pp. 21–27 and paste a polished English version into `english-transcript.md` at the right slot; I'll mirror into refined-english.md on resume.

Other passages you spot during review:

- Page __ — (description)
- Page __ — (description)

## 3. Glossary additions

Arabic terms that should be in `_system/concept-glossary.md` and/or `_system/pronunciation.md` with operator-approved glosses. Asaas's recursive-scaffold pattern means EP01 carries the highest glossary load (8–10 terms) and EP02–06 lean on it. Pre-seeded list — confirm or amend:

- **nāṭiq** (ناطق) — "speaker-prophet"; each cycle's bearer of revelation (Ādam, Nūḥ, Ibrāhīm, Mūsā, ʿĪsā, Muḥammad, Qāʾim). EP01 introduces.
- **asās** (أساس) — "foundation"; the immediate inheritor of a nāṭiq who guards the *taʾwīl* (e.g., ʿAlī as asās of Muḥammad). EP01 introduces.
- **ḥujja** (حجة) — "proof, evidence"; the chain of 12 imāms who continue the asās line under each nāṭiq. EP01 introduces.
- **taʾwīl** (تأويل) — "esoteric interpretation"; the book's title-concept. EP01 introduces (contrast with *tafsīr*).
- **ẓāhir** (ظاهر) — "outer, apparent"; the literal/legal surface. EP01 introduces.
- **bāṭin** (باطن) — "inner, hidden"; the esoteric meaning *taʾwīl* unlocks. EP01 introduces.
- **mubdaʿ** (مُبدَع) — "originated being"; first emanation from the divine. EP01 introduces if quoted.
- **ʿaql awwal** (عقل أوّل) — "First Intellect"; Neoplatonic-influenced cosmology layer. EP01 introduces if quoted.
- **nafs kulliyya** (نفس كلية) — "Universal Soul"; second cosmology layer. EP01 introduces if quoted.
- **qāʾim** (قائم) — "the riser"; the awaited seventh nāṭiq. EP06 introduces.
- **ghayba** (غيبة) — "occultation"; the qāʾim's hidden state. EP06 introduces.
- **intiẓār** (انتظار) — "expectation, waiting"; the doctrine of awaiting the qāʾim. EP06 introduces.

Additional terms you want added:

- **term** — (gloss / pronunciation correction)

## 4. Pronunciation corrections

Names/terms NotebookLM is likely to mangle; add to `_system/mangle-map.md`. Pre-seeded from chapters-rationale.md "Numeric/symbolic surface" and the nāṭiq cycle:

- **al-Nuʿmān** → al-noo-MAAN (NOT "al-NEW-man"; the ʿayn before the alif is held)
- **al-Qāḍī al-Nuʿmān** → al-KAA-dee al-noo-MAAN (NOT "al-QUAD-ee")
- **ʿĀrif Tāmir** → AA-rif TAA-mir (editor's name; long alifs both syllables)
- **Hābīl & Qābīl** → haa-BEEL and KAA-beel (Abel and Cain)
- **Shīth** → SHEETH (Seth)
- **Yūshaʿ bin Nūn** → YOO-shaʿ bin NOON (Joshua son of Nun)
- **Ghadīr Khumm** → gha-DEER khoom (the pond/oasis, NOT "Khum")
- **Baḥīrā** → ba-HEE-raa (the Christian monk who recognized young Muḥammad)
- **ʿAql awwal** → AKL AW-wal (NOT "akkle"; the ʿayn is a glottal-pharyngeal stop)
- **Nafs kulliyya** → NAFS kul-LEE-ya
- **abjad** → AB-jad (the numerical-alphabet system; needed for §5 below)

Add as needed:

- (term) → (correct pronunciation hint)

## 5. Free-form comments

Anything else — voice notes for the framing, chapter mood, factual concerns, sensitive material to flag, sub-arcs that should be foregrounded:

(your notes here)

> **Claude's heads-up on what's coming downstream:** Loop N (numeric-disambiguation) will fire heavily on this book — 7 nāṭiqs, 12 ḥujjas, abjad ciphers, and al-Nuʿmān's tendency to read Fatimid doctrine back into Qurʾānic narratives (anachronism risk per chapters-rationale.md §5). If you spot any place in the transcript where you DON'T want Loop N to enforce strict factuality (e.g., al-Nuʿmān's symbolic reading of Adam's clay as the *nafs kulliyya*), flag it here — those go into the per-chapter `<allowed_symbolic_readings>` block at Phase 0g.

## 6. Source-chapter naming + episode mapping confirmation

Asaas does **not** have the abwāb/fusūl translation collision that KaR did. The source is cleanly six chapters, one per nāṭiq. `chapters-rationale.md` (operator-authored) already declares the 6-chapter → 6-episode mapping. Just confirming the slug convention:

**Proposed chapter slugs (Phase 0d output):**

| EP | Slug | Source chapters | Title |
|---|---|---|---|
| EP01 | `ch01-natiq-1-adam-the-template` | Editor's intro + Ch 1 (pp. 33–75) | The Hidden Code |
| EP02 | `ch02-natiq-2-3-nuh-ibrahim` | Ch 2 + Ch 3 (pp. 76–178) | Floods and Fathers |
| EP03 | `ch03-natiq-4-musa-part-1` | Ch 4 part 1 (pp. 179–245) | Moses and the Pharaoh's Court |
| EP04 | `ch04-natiq-4-musa-part-2` | Ch 4 part 2 (pp. 246–298) | The Davidic Kings and the Whale |
| EP05 | `ch05-natiq-5-6-isa-muhammad` | Ch 5 + Ch 6 (pp. 299–368) | Christ Without a Father, Muhammad as Seal |
| EP06 | `ch06-natiq-7-qaim-silence` | Editor's note + unwritten Ch 7 | The Seventh Silence |

**Operator confirms naming (default = recommended):**
- [ ] **(Recommended)** `chNN-natiq-N-<topic>` — honors the recursive-scaffold pattern; the word "natiq" appears in every slug so the structure is legible from `ls`
- [ ] `chNN-<topic>` — shorter, drops the natiq prefix
- [ ] override with custom slugs (write below)

Hosts will explain *nāṭiq* the first time it appears in EP01 (per §3 glossary plan); slug repetition reinforces the pattern.

## 7. Content range — skip front matter + back-matter indexes + French RTL tail

The refined-english.md is **10,329 lines / 416 PDF pages**. Per `chapters-rationale.md`:

| Zone | PDF pages | Refined lines (approx) | % of file | Status |
|---|---|---|---:|---|
| Front: cover + editor's intro + author's intro | 1–32 | 1–397 | ~4% | **SKIP** (mostly editor; author's intro pp. 21–27 missing per §2) |
| Body: six nāṭiq chapters | 33–368 | 398–8,091 | ~74% | **INCLUDE** |
| Back: indexes (subject, names, etc.) | 369–408 | 8,092–10,250 | ~21% | **SKIP** |
| French RTL editor's intro (re-OCR'd, re-translated) | 409–416 | 10,251–10,329 | ~1% | **SKIP** (this is the same editor's intro from pp. 5–18 but in French → English; pure noise) |

**Heuristic-suggested defaults (pre-filled from chapters-rationale.md page table):**

```yaml
schema_version: 1
body_starts_at_page: 33      # Chapter 1 (Ādam) opens here; refined line 398
body_ends_at_page: 368       # Chapter 6 (Muḥammad) closes here; refined line 8091
include_author_preface: false  # author's intro pp. 21–32 — currently broken (see §2); revisit after splice decision
include_author_toc: false      # author's own TOC at pp. 369–372 — structural-only
front_matter_summary: |
  Pages 1-32: cover (1-4), editor's intro by Arif Tāmir (5-20), author's
  introduction (21-32 — partially missing from refined-english.md; see §2).
  If §2 option A or C is taken, body_starts_at_page may move to 21
  (operator decision).
back_matter_summary: |
  Pages 369-408: indexes — names of prophets/figures clusters at pp. 402-408
  (cross-reference for EP01's glossary). Pages 409-416: French editor's
  intro re-OCR'd as if body content (Phase 0a artifact; pure duplication).
```

**Special consideration — editor's note on the unwritten 7th chapter:**

`chapters-rationale.md` §7 cites "editor's note on printed p. 21: al-Nuʿmān stopped because the awaited one 'has not yet come'" as the foundation for EP06 ("The Seventh Silence"). On scan, this note appears to be **inside the editor's intro (refined pp. 3–18, NOT at p. 21**, because in the OCR p. 21 is the start of author's intro, not editor's). Either:

- The cite in chapters-rationale.md is using PDF page numbers from a multimodal pass (the author wrote chapters-rationale on the Air with a fresh PDF read), which may differ from OCR page markers; OR
- The "editor's note on p. 21" is embedded *within* a section of refined-english pp. 3–18 and we need to locate it there.

EP06 framing should be unblocked either way — the unwritten-7th content can be drawn from §6.

**Confirmed:**
- [ ] **(Recommended)** Defaults look right — emit `_system/source/text/content-range.md` with body 33–368; revisit after §2 decision in case body_starts_at_page should drop to 21
- [ ] Override range (write below)
- [ ] No content-range — process whole transcript at Phase 0c/0d/0e (~$5-7 extra LLM cost on this larger book + Loop N noise on French RTL tail)

## 8. Approval

- [ ] **I approve this transcript — proceed with Phase 0c** (after §2 resolved + §6, §7 confirmed)

### Caveat: P22.impl + P4.10 enforcement code not yet shipped

Per acceptance-criteria.md rows 202–211 (P22.impl) and 365–370 (P4.10.{validator,phase0d,phase0e_phase11,backcompat,metric}): the orchestrator code that READS `content-range.md` and the `<operator-review>` XML block is NOT yet shipped. For THIS resume:

- `content-range.md` (if emitted on approval) is committed as a **record of operator intent** — honored by future runs once P4.10 ships
- The current orchestrator will process the **whole 416-page transcript** at Phases 0c/0d/0e (Loop N may spuriously flag the editor's bibliography and the French RTL tail; ~$5-7 extra LLM cost over a content-range-honored run)
- The chapter slug + naming preference from §6 is captured here but **NOT auto-injected into Phase 0d's prompt** until P22.impl ships; Phase 0d's LLM will choose chapter naming heuristically (likely close to §6 by virtue of `chapters-rationale.md` being readable by 0d already)
- The §2 pages-21-27 splice (if option A or C) happens **manually before resume** via Claude — not by orchestrator code

**Two paths after §8 approval:**

- **Option I — Resume now, accept the gap.** Live with whole-transcript processing + heuristic chapter naming + §2 splice done manually by Claude before resume. Future runs honor preferences once P22 + P4.10 land. Net cost over a fully-honored run: ~$5-7 extra LLM on Phases 0c/0d/0e + possible Loop N noise on French RTL.
- **Option II — Ship P22.impl + P4.10 minimal code first, then resume.** ~2-3 hours of focused work to wire `_content_range.py` + Phase 0d/0e/11 honors `content-range.md` + Phase 0c+ prompts include `<operator-review>` XML block. Then resume honors all decisions cleanly.

Operator's call. Either way, this commit captures the decisions so they're durable.

---

## What happens on resume

When you signal **"resume asaas"** in chat:

1. **§2 pages 21–27**: if option A or C, I splice the missing author's introduction into `refined-english.md` between current `<!-- page 18 -->` and `<!-- page 28 -->`. If option B, I add a `pages-21-27-gap` note to `_system/registry.md`.
2. **English-transcript inline edits**: if you edited `english-transcript.md` directly, I mirror your edits back into `refined-english.md` (one-shot diff merge).
3. **§3 glossary additions**: I extend `_system/concept-glossary.md` with any new terms.
4. **§4 pronunciation additions**: I extend `_system/mangle-map.md` and `_system/pronunciation.md` with any new entries.
5. **§5 free-form notes**: I integrate any "don't enforce factuality here" flags into the per-chapter contracts (`chapter-contracts/chNN-*.yaml`) — emitted during Phase 0d.
6. **§6 chapter naming**: captured here; will be reflected in Phase 0d's output verbatim if you chose recommended; integrated into Phase 0d prompt if custom (manual prompt injection by Claude until P22.impl ships).
7. **§7 content range**: if confirmed (with or without §2 boundary adjustment), I emit `_system/source/text/content-range.md` with `body_starts_at_page` + `body_ends_at_page`. Phase 0d/0e/11 honor it (per P4.10) once that code ships; until then, it's a forward-looking artifact.
8. **State + commit**: orchestrator-state.json moves to `phase: "0c", phase_status: "pending"`. Commit subject: `podcast(asaas-al-taveel): operator transcript review — approved with <one-line summary>` (KaR's convention per acceptance row 211).
9. **Resume**: `python3 scripts/podcast/orchestrate_book.py --resume asaas-al-taveel`. The orchestrator picks up at Phase 0c (Arabic phonetic pass, chunked `claude -p` like 0b). Expect 1–2 cycles of "chunk dies on 1200s timeout → I resume" before 0c completes, paralleling 0b's behavior on this size of book.
10. **Next gate after 0c**: Phase 0d (chapter segmentation, deterministic given chapters-rationale.md) → 0e (enrichment) → **Phase 0f operator gate** (persona / tier / series / episode plan confirmation). 0f is the next non-auto stop.

If you find no issues, just say **"resume asaas, transcript LGTM"** and I'll use defaults: §2 option A (re-refine pp. 21–27), §6 recommended (natiq slugs), §7 recommended (body 33–368), §8 approved.
