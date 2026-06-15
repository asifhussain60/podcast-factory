# Podcast Challenger Report

**Book:** kunooz-al-hikmah
**Run:** 2026-06-15 7:14 PM EST (challenger v2.5)
**Scope:** per-chapter lectures-six-seven-eight-continued
**Iterations:** 1 (of 5 max — early break: zero auto-fixes available, (P0,P1) identical to prior converged state)
**Verdict:** SHIP-WITH-CAUTION
**Content profile:** islamic_scholarly (detected from meta.yml)
**Pipeline context:** invoked from within `orchestrate_book.py` parent process — Category S1 async-safety gate bypassed for this in-pipeline call.

## Auto-fixes applied (iteration-by-iteration)

| Iter | Check | File | Action |
|---|---|---|---|
| — | — | — | None this run. Prior converged state holds: 7 legacy `(Quran N:M)` → `(chapter N, verse M)` reformats from the 2026-06-15 7:12 PM EST run are still in place. |

## Findings requiring author resolution

### P0 (blocks ship)

None. Re-validation summary:
- Doctrinal pack T1–T5 (chapter + framing): 0 findings.
- Inline phonetic parens (N1): 0 in chapter.
- Honorific discipline (O1): `(peace and blessings be upon him)` 1×, `(peace be upon him)` 1× — each at first mention only.
- Meta-prose tells (B1), file-length self-references (B3), translator-apparatus prefixes (B4): clean.
- `[VERIFY CITATION]` / `[CONTEXT NEEDED]` markers (A2, D5): 0.
- Quran citation format R-QURAN-CITATION-FORMAT: all 7 citations in canonical `(chapter N, verse M)` form.
- Legacy `(Quran N:M)` forms: 0.
- Q1–Q4 host-role parity: Host A scholar (male) / Host B seeker (female) — consistent with sibling EP07 / EP09 framings.

### P1 (ship-with-caution)

#### F20 / R-NO-ARABIC-TRANSLITERATION: `al-Taslim` survives in a book-title citation

- **File:** `chapters/ch08a-lectures-six-seven-eight-continued.txt:47`
- **Context:** "(the same author's *Rawdat al-Taslim*, paragraph one, rendered into English by S. J. Badakhchani, I. B. Tauris, 2005, page 3)"
- **Doctrine:** F20 forbids Arabic transliterations in chapter prose to keep the audio TTS-safe.
- **Assessment:** appears inside a scholarly book-title citation, where the policy normally permits the original-language title in italics (parallel to the prior episode's `Tabaqat` citation). The framing already maps `Rawdat al-Taslim → the corrective treatise` under `## Pronunciation`, so NotebookLM pronounces the bibliographic title once but the surrounding prose uses the English label.
- **Suggested fix:** acceptable as a one-off bibliographic citation, OR rewrite as "(the same author's corrective treatise, paragraph one, rendered into English by S. J. Badakhchani…)" if the author prefers a fully English-only chapter body.
- **Auto-fix:** not applied — bibliographic-citation policy is an authoring judgment call.

#### F25-APPARATUS-TABLE: `99-show-notes.md` missing the Name and Title Preservation Table

- **File:** `_system/episode-drafts/EP08-lectures-six-seven-eight-continued/99-show-notes.md`
- **Doctrine:** F25 requires every episode's 99-show-notes to carry the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk) the TTS-safe audio omits.
- **Suggested fix:** append a `## Name and Title Preservation Table` section listing audio labels paired with preserved spellings (the Persian companion ↔ Salman al-Farsi; the philosopher-jurist of our line ↔ Nasir al-Din al-Tusi; the corrective treatise ↔ Rawdat al-Taslim; one of the canonical hadith collections ↔ Sahih Muslim, Kitab al-Fadail; the early biographer's *Tabaqat* ↔ Ibn Sa'd, *Kitab al-Tabaqat al-Kubra*).
- **Auto-fix:** not applied — apparatus table content requires authoring decisions about which preserved spellings to surface.

### P2 (advisory)

#### B5: 48 em-dashes in chapter prose

- **File:** `chapters/ch08a-lectures-six-seven-eight-continued.txt`
- **Doctrine:** B5 discourages em-dashes because they can confuse NotebookLM's prosody.
- **Assessment:** sibling episodes (EP07, EP09) carry comparable counts; this is a book-level voice choice already in effect. Not auto-stripped this run, consistent with prior run's judgment.
- **Auto-fix:** withheld pending book-level decision.

## Health metrics

| File | Words | Notes |
|---|---|---|
| ch08a-lectures-six-seven-eight-continued.txt | 6,082 | Just above the 5,500 chapter band; consistent with extended-tier sibling episodes (EP07: ~6,400; EP09: ~6,700). |
| EP08 framing (00-framing.md) | 759 | Within 200–3,500 framing soft band; R-RECURRING-THESIS spine x3 present. |
| Quran citations | 7 | All in canonical `(chapter N, verse M)` form. |
| Honorifics | 2 | Each form at first mention only — O1 clean. |
| Em-dashes (B5) | 48 | Advisory; not auto-stripped. |
| Doctrinal findings | 0 | T1–T5 clean across chapter and framing. |

## Verdict rationale

Re-run converges on the prior state in one iteration: no new auto-fixes are deterministically available, and the (P0=0, P1=2) tally is identical to the prior converged report. The two remaining P1 findings (`al-Taslim` in a bibliographic citation; missing apparatus table in `99-show-notes.md`) match the established book-level pattern (see EP07 and EP09 reports) and are author-decision items. No P0 findings; episode is **SHIP-WITH-CAUTION**.
