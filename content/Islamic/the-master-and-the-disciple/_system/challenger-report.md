# Podcast Challenger Report

**Book:** the-master-and-the-disciple
**Run:** 2026-06-11 03:25Z (challenger v2.5)
**Scope:** per-chapter rebirth-and-the-seven-day-tawaf (EP12)
**Iterations:** 1 (of 5 max — clean break: identical findings to prior pass, zero auto-fixes)
**Verdict:** SHIP-WITH-CAUTION
**content_profile:** islamic_scholarly

## Auto-fixes applied

None this run. Chapter and framing pass all P0 hard gates (build_episode_txt.py emits successfully). No deterministic auto-fix triggers fired: no inline phonetic parens (N1), no legacy passive pronunciation list (N2), no repeated honorific expansions (O1), no abbreviated work titles (O2), no cross-episode references (B2), no meta-prose tells (B1/B3/B4).

## Findings requiring author resolution

### P0 (blocks ship)

None. Doctrinal checks (T1–T5) clean on chapter and framing; T3-forbidden-pairing gate clean.

### P1 (ship-with-caution)

#### R-NO-ARABIC-TRANSLITERATION: 4 Arabic transliterations in chapter (citation apparatus)
- **File:** content/Islamic/the-master-and-the-disciple/chapters/ch12a-rebirth-and-the-seven-day-tawaf.txt
- **Context:** Bibliographic proper nouns inside parenthetical citations: `Abu Dawud`, `al-Balagha`, `al-Radi`, `al-Sharif`. These appear in parenthetical citations of *Nahj al-Balagha* (al-Sharif al-Radi) and *Sunan Abu Dawud* — the standard written bibliographic apparatus.
- **Suggested fix:** Author judgment. Accept as F20 citation-apparatus carve-out (the framing already maps audio labels to "the book *The Peak of Eloquence*" / "the hadith compiler", so TTS render is steered), or substitute. Recommend: accept as-is — citation apparatus belongs in the written chapter, not the audio.

#### F25-APPARATUS-TABLE: 99-show-notes.md missing Name and Title Preservation Table
- **File:** content/Islamic/the-master-and-the-disciple/_system/episode-drafts/EP12-rebirth-and-the-seven-day-tawaf/99-show-notes.md
- **Context:** Show-notes has `## Related episodes` and `## References` sections, but no `## Name and Title Preservation Table`. F25 doctrine requires every episode's show-notes to carry the written-layer apparatus (preserved Arabic / transliterations + audio-label crosswalk) the TTS-safe audio omits.
- **Suggested fix:** Append `## Name and Title Preservation Table` mapping audio labels → written forms (e.g. "the Father of Imams" → ʿAlī ibn Abī Ṭālib; "the book *The Peak of Eloquence*" → *Nahj al-Balāgha*; "the hadith compiler" → Abū Dāwūd al-Sijistānī; "tawaf" → ṭawāf). Written-layer only; does not affect NotebookLM audio.

### P2 (advisory)

None.

## Health metrics

| File | Words | Status |
|---|---|---|
| ch12a-rebirth-and-the-seven-day-tawaf.txt | 2,332 | Within default-deep-dive band (1,800–2,800) |
| EP12-rebirth-and-the-seven-day-tawaf/00-framing.md | 758 | Within framing band (200–2,000) |
| Tier diversity in chapter | 5 distinct tiers cited | Multi-tier (Quran, hadith collection, Nahj al-Balagha, secondary scholarship Chittick/Corbin/Daftary) |
| Phonetic gaps | 0 | Pronunciation block in framing covers tawaf, Sheikh, Imam, Kaaba, Allah, Quran, Hijra |
| Honorific expansions | 1 each (Prophet, Father of Imams) | R-HONORIFIC-ONCE compliant |

## Category coverage

All applicable categories run: A (citation discipline), B (literalness — em-dashes accepted under current build doctrine), C (phonetic coverage via framing Pronunciation block), D (enrichment depth — Tier 3/4/5 coverage), E (articulation), F (framing integrity — all four sections present), H (welcome + landing both present), I (anti-repetition + bounded background), J (name discipline block present), K (host dynamic + forbidden filler vocabulary named), M (DENY-modernize + DENY-surprise blocks present), N (no inline phonetic parens; imperative Pronunciation block), O (single-occurrence honorifics; no abbreviated titles), Q (Host A=scholar, Host B=seeker — pool-compliant; book-wide parity maintained), R (no transcript yet for empirical pass; framing-side R1–R5 in place via Host dynamic + Tone + Do-not blocks), T (doctrinal — zero findings), U (no AI-cliche, no faux-profundity opening, no premature closure, no deep-dive self-reference, no external essentialism), V (V1 curiosity hook present, V2 challenge-defeat arc present, V3 modern relevance via gravity/orbit analogy, V4 no strawman, V5 rhetorical questions present).

## Convergence trace

- Iteration 1: re-ran build_episode_txt.py → exit 0. Doctrinal checks → 0 findings. Direct scans for AI-cliche / modernization / cross-ep / meta-prose → 0 findings in chapter or framing prose (the framing's `## Do not` line containing those tokens is a forbidden-vocabulary directive to the hosts, not a violation). Findings identical to prior 2026-06-11 03:09Z pass: P0=0, P1=2, P2=0. Zero auto-fixes applicable. Intelligent break per Section 4.6b.
