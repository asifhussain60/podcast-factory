# Arabic TTS Protocol (Track A · forward state)

**Role.** This file is a tracked governance protocol, loaded as cold-start item 17 by `.github/agents/podcast-challenger.agent.md` and as item 18 by `skills-staging/podcast/SKILL.md`. Producer and challenger consult it on every chapter and every episode authoring run.

**Status.** Approved (Track A). Implementation pending — the protocol describes the **target state** of the Arabic TTS rules. The challenger does NOT yet enforce the future rules in Sections "Implementation steps" / "Acceptance criteria" because they have not landed in their named rule files. Until they do, this document serves as: (1) the design contract for the upcoming rules change; (2) advisory context for any authoring decision affecting Arabic phonetics; (3) the source of the **Conversational vs Classical** mode distinction that all framings should respect even before B1–B8 land mechanically.

**Authority interleave.** Where this protocol contradicts the current `notebooklm-customize-prompt-rules.md` or `01-tts-pronunciation-key.md`, the rule file wins **until** B1–B8 execute; after execution, this protocol's framing is canonical and the rule files are updated to match.

**Implementation trigger.** Type `implement` (or equivalent) to authorize execution of steps B1–B8. When complete, mark this document `IMPLEMENTED` at the top and migrate any residual roadmap content into `content/podcast/.skill/ROADMAP.md` Section A.

---

## Scope (approved)

**Track A — Strengthen the existing TTS engineering layer.**
No architectural change. The current NotebookLM pipeline is preserved. The addendum's intent is honored through the customize prompt's steering layer.

**Track B (NOT approved this round).** A separate direct-TTS authoring artifact (a TTS-ready script bypassing NotebookLM) is out of scope until a dedicated design pass against a chosen TTS provider. Not part of this plan.

---

## What the addendum requires (Asif's quality baseline, 2026-05-18)

1. **Conversational vs Classical mode distinction.** Anglicized smooth phonetics for casual integration (`Inshallah` → `in-shah-LAH`); hard-syllable Tajweed approximation for scripture and named figures (`Quran` → `koor-AHN`).
2. **TTS-Hacking engineering rules.** Build phonetic strings using intuitive English phonics:
   - Q → K (Quran → koor-AHN)
   - Dh → TH (Dhikr → THIK-er)
   - Kh → KH (guttural marker; Khalid → KHAH-lid)
   - Stressed syllable capitalized
   - Hyphens separate syllables / emulate glottal stops
   - No standard Romanization tokens (`q`, `dh`, `gh`, apostrophe for `ain`)
3. **Phonetic Key glossary** at the top of every user-reviewable artifact mapping standard Arabic → TTS-baked phonetic.
4. **Inline phonetic in spoken dialogue** (addendum's literal text) — *re-scoped under Track A*: implemented via NotebookLM honoring the Phonetic Key during synthesis, NOT by writing phonetics inline in the chapter. The chapter stays clean per R-PHONETICS-OUT (May 2026 audit's structural fix; reverting it re-introduces the `Sunnah, soon-nah` / `tassel wolf` failure modes).

---

## Architectural decisions (locked under Track A)

| Decision | Rationale |
|---|---|
| **R-PHONETICS-OUT stays intact.** No inline phonetic parens in the chapter file. | May 2026 transcript audit: inline parens are voiced aloud by NotebookLM as content, producing systematic doublings and mangled names. Reverting regresses 5 audited episodes. |
| **R-PRONUNCIATION-IMPERATIVE splits into two modes.** Conversational + Classical. | Honors the addendum's mode distinction without architectural change. Same imperative-line shape; different cadence per mode. |
| **`## Pronunciation` block renamed to `## Phonetic Key (TTS Pronunciation)`.** | Honors the addendum's "Phonetic Key glossary" framing. Auto-fix for legacy headers in existing framings. |
| **Per-book `pronunciation.md` gains a `Mode` column.** | One-time per-term classification; book authors don't repeat it per episode. |
| **TTS engineering rules promoted to numbered imperatives** in `content/_shared/arabic/01-tts-pronunciation-key.md`. | The Q→K / Dh→TH / Kh→KH / stress-cap / hyphen-glottal rules become a contract surface, not in-prose guidance. |

---

## Implementation steps (gated)

Each step is atomic and reversible. Numbers in order of execution.

| # | Step | File(s) | Auto-fixable? |
|---|---|---|---|
| 1 | Rewrite TTS engineering rules as numbered imperatives | `content/_shared/arabic/01-tts-pronunciation-key.md` | n/a |
| 2 | Split R-PRONUNCIATION-IMPERATIVE into Conversational + Classical modes | `content/podcast/.skill/handbook/notebooklm-customize-prompt-rules.md` | n/a |
| 3 | Rename `## Pronunciation` → `## Phonetic Key (TTS Pronunciation)`; update auto-detect to accept both for one cycle; add auto-fix | same as #2 + `scripts/podcast/build_episode_txt.py` | yes (legacy framings via challenger) |
| 4 | Add `Mode` column to `BOOK_DIR/_system/pronunciation.md` template | `scripts/podcast/scaffold_book.py` template body | n/a |
| 5 | Backfill ayyuhal-walad's `pronunciation.md` with Mode classifications | `content/podcast/library/books/ayyuhal-walad/_system/pronunciation.md` | n/a |
| 6 | Update `worked-examples.md` §4 with one Conversational + one Classical example | `content/podcast/.skill/handbook/worked-examples.md` | n/a |
| 7 | Challenger Loop C5 gains sub-check: scripture-citation term marked Conversational → flag (authoring decision; not auto-fixed) | `.github/agents/podcast-challenger.agent.md` | flag-only |
| 8 | Re-render EP02 with auto-fixed section name; confirm clean build | `content/podcast/library/books/ayyuhal-walad/_system/episode-drafts/EP02-hatim-eight-benefits/00-framing.md` | yes |
| 9 | Commit | — | n/a |

---

## Acceptance criteria

- `content/_shared/arabic/01-tts-pronunciation-key.md` carries numbered engineering rules (Q→K, Dh→TH, Kh→KH guttural, stress-cap, hyphen-glottal). Each rule has at least one worked example.
- `R-PRONUNCIATION-IMPERATIVE` documents two canonical line templates: Conversational (smooth) and Classical (Tajweed-approximating).
- Every framing's pronunciation surface is titled `## Phonetic Key (TTS Pronunciation)`. The build script and challenger accept both `## Pronunciation` and `## Phonetic Key` during a one-cycle migration; auto-fix renames legacy headers.
- `BOOK_DIR/_system/pronunciation.md` carries a `Mode` column. ayyuhal-walad's entries are backfilled.
- `EP02-hatim-eight-benefits` rebuilds clean after the section rename auto-fix.
- `R-PHONETICS-OUT` unchanged. Chapter files stay free of inline phonetics.
- Final literal scan: zero hits outside `worked-examples.md`.
- podcast-challenger Loop C5 sub-check fires when a scripture-citation term is misclassified as Conversational.

---

## Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Section-name rename breaks build script's `R-PRONUNCIATION-IMPERATIVE` regex | High | Update regex to accept both names; auto-fix legacy headers within one cycle. |
| Conversational/Classical misclassification weakens scripture delivery | Med | Challenger Loop C5 sub-check flags scripture-citation context. Manifest defaults to Classical; per-book pronunciation.md overrides. |
| Backfilled ayyuhal-walad entries get an inconsistent Mode | Low | Default classification rule: term-in-shared-manifest → inherit; term newly added → Classical by default. |
| Existing per-book `pronunciation.md` files without Mode column trip new lint | Low | Mode column is OPTIONAL on parse; absence defaults to Classical. |

---

## Out of scope (recorded; not implemented this round)

- **Track B-DirectTTS.** Separate `_system/episode-drafts/EP##-<slug>/05-tts-script.md` authoring artifact with phonetics baked inline, for direct-TTS audio generation. Needs its own design pass with a chosen TTS provider and validation against a real render.
- **Signposting rule** (R-NAMECALL). Rejected in the prior review pass; remains rejected here.
- **Recap-tease-CTA outro.** Conflicts with R-SUMMARYTAIL; remains rejected.

---

## Status (this plan)

**Plan drafted, approved by Asif. Implementation gated on explicit `implement` (or equivalent).** No handbook files modified yet. When implementation begins, single commit titled `podcast(skill): Arabic TTS protocol — mode split + engineering rules + Phonetic Key naming`. Estimated diff size: ~6 files, ~150 lines.

**Next action on Asif:** type `implement` (or `proceed`) to authorize execution. Type `pause` if you want to review specific implementation steps line-by-line before approval.
