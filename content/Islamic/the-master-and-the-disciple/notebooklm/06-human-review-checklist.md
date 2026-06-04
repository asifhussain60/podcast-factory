# Human Review Checklist — *The Master and the Disciple*

**Purpose.** This is the pre-publication gate. Every episode generated from this source set passes through these checks **before** the audio leaves the operator's machine. No NotebookLM AI can satisfy these on its own — a human with theological literacy must sign off.

This file is read together with `03-source-integrity-notes.md`. The integrity-notes file says *what status each claim has*; this file says *what the human must verify before publishing*.

---

## A. Quotation and attribution review

For each episode, the reviewer confirms:

- [ ] Every direct quotation from the Quran is delivered in English translation; the transliteration is not spoken aloud as the primary delivery.
- [ ] Every hadith mentioned uses the phrase "in the tradition…" or "is remembered as…" unless a verified critical-edition citation is available.
- [ ] The "I am the city of knowledge and Ali is its gate" attribution is framed as a traditional teaching, not a fully-footnoted academic claim — unless the operator's chosen edition resolves the chain.
- [ ] Every quotation from Ali, peace be upon him, that draws from *Nahj al-Balagha* is phrased as "Ali is remembered in the tradition collected as *Nahj al-Balagha* as having taught…" rather than as a verbatim critical-edition quote.
- [ ] Sayings attributed to Imaam Ja'far as-Saadiq use the same tradition-association framing.
- [ ] No quotation is presented without honorific on first mention (see `01-pronunciation-guide.md` §"Honorific protocol").

## B. Theological framing review

- [ ] The text is identified as *early Ismaili Shi'i* on first reference in every episode.
- [ ] The author attribution uses "**associated with** Ja'far ibn Mansoor al-Yaman," not "definitively authored by."
- [ ] Claims specific to Ismaili tradition (seven Naa-tiqs, the Imaam lineage, Wilaayah's encompassing role) are framed as the Ismaili tradition's specific teaching, not as generic Islam.
- [ ] The Wilaayah three-component structure (heart / tongue / limbs) is recognizable as the Ismaili formulation paralleled to the divine Will/Command/Word triad — and is labeled as editorial paraphrase if it appears in an `[Editorial Clarification]` paragraph.
- [ ] The first-seven-Imaams list (Ali through Ismaa-eel ibn Ja'far) is presented as the Shia/Ismaili understanding — Sunni Islam does not share this list.
- [ ] The episode does **not** flatten the work into a generic mentorship narrative, generic Sufism, or generic "old wisdom book" framing (see `04-do-not-say-guardrails.md` §1).

## C. Pronunciation review

- [ ] Every name and term spoken in the episode that has an entry in `01-pronunciation-guide.md` was pronounced according to the canonical form. Listen back specifically for: **Allaah, Saa-lih, Aboo Maa-lik, Al-Bakh-ta-ree, Sharee-ah, Taa-weel, Zaahir, Baatin, Wilaayah, Imaam, Hujjah, Daa-ee.**
- [ ] No inline phonetic parenthetical was read aloud. (The source files do not contain them; if NotebookLM hallucinated a parenthetical, fix the customize prompt.)
- [ ] No name was pronounced inconsistently across the episode. If the host varied the pronunciation of any name, this is a P0 blocker.
- [ ] Honorifics follow the protocol (full honorific first mention, name alone subsequently — see pronunciation guide §"Honorific protocol").
- [ ] For any name that appeared in the episode but is not in the guide, an entry has been added to the guide before publication.

## D. Editorial-clarification labeling review

- [ ] Listeners can hear (in the host's framing) the difference between source text and editorial clarification. The host should say "the editor adds an analogy here…" or "to make this accessible, the modern reader can think of…" before delivering an `[Editorial Clarification]` paragraph.
- [ ] No `[Editorial Clarification]` paragraph was presented as if it were from the original work.
- [ ] The technology analogies (software architecture, authorized access, deployment, GPS, virtual reality) appeared at most once per episode, each in service of the job assigned in `03-source-integrity-notes.md` §"Editorial-clarification paragraphs."

## E. Do Not Say compliance

- [ ] None of the anti-patterns in `04-do-not-say-guardrails.md` appeared in the episode.
- [ ] Specifically: the book was not reduced to "find a mentor," outward practice was not dismissed, Ismaili-specific claims were not presented as generic Islam, and no anachronistic tech analogy (algorithm, neural network, blockchain, AGI) was introduced.

## F. Episode-arc fidelity

- [ ] The episode's central question matches the one named in `05-episode-arc.md` for this chapter.
- [ ] The episode closer points forward to the next episode using (or naturally paraphrasing) the bridge content in `05-episode-arc.md` §"Episode-to-episode bridges."
- [ ] The episode honors the chapter's spoiler level — Ep 0 reveals only the broad arc; later episodes don't pre-empt their successors.

## G. Listener-fit and difficulty fidelity

- [ ] The "Who this is for" and "Who may struggle" framing from the per-chapter `chNN-scaffolding.md` Listener Fit section was acknowledged either explicitly or implicitly by the host's framing choices.
- [ ] For high-difficulty chapters (Ch 2, Ch 6): the chapter's Listener Difficulty block was honored — central question repeated, terms defined before use, one analogy at a time.

## H. Tone discipline

- [ ] The episode does not flatten into self-help.
- [ ] The episode does not flatten into a generic "ancient wisdom" review.
- [ ] The episode acknowledges difficulty (where high) rather than waving it away.
- [ ] The episode does not use casual jokes about sacred concepts or names.
- [ ] At least one host question (from the per-chapter scaffolding) was raised; the episode did not become monologic.

## I. NotebookLM-specific cleanup

- [ ] No three-consecutive-sentence repetition of the same Arabic term.
- [ ] No inline parenthetical phonetics were spoken aloud.
- [ ] No irrelevant biographical preamble ("born in the year…") about Ja'far ibn Mansoor al-Yaman or any Imaam.
- [ ] The host did not interrupt itself across a sacred name or quoted teaching.

## J. Numeric / Symbolic Disambiguation review (P4 protocol)

For Ch 2 specifically, but applicable to any chapter asserting numeric / symbolic claims:

- [ ] Every numeric/symbolic claim in the chapter has a row in `03-source-integrity-notes.md` §"Numeric/Symbolic enumeration register" (status = RESOLVED / RESOLVED-with-framing / NEEDS HUMAN REVIEW).
- [ ] No invented enumeration appears in any chapter (Loop N P0 blocker).
- [ ] The 12 jazāʾir enumeration appears in episode 2 only, not in episodes 3+ (one-time enumeration rule).
- [ ] The 7 seas enumeration uses the Yaʿqūbī list with the framing caveat, NOT the Greek/Mediterranean list.
- [ ] The cryptic sphere-letters sequence (ب ج لا د م لہ م) is flagged NEEDS HUMAN REVIEW; no decoding is offered on air.
- [ ] The fifth intermediary is flagged NEEDS HUMAN REVIEW; the Dāʿī reading is probable but not asserted as definitive.
- [ ] The anachronism register entries are honored: host labels BOTH period referent AND modernization for "seven continents" / "seven heavens" order.
- [ ] The luminary order in Ch 2 is flagged for Morris-edition cross-check post-publication.
- [ ] Any chapter using abjad letter-values cites `content/_shared/arabic/06-abjad-numerals.md` as authority.

**Failure-mode escalation:** if Loop N raises a P0 finding (invented enumeration / unsourced cipher decoding), the book is BLOCKED from shipping. Resolution paths: (1) add a tier 1-4 source to the register row, OR (2) reclassify as NEEDS HUMAN REVIEW and remove the enumeration assertion from prose (replace with "requires specialist commentary" framing). If neither path resolves it, escalate to the Morris critical edition. **Never silently advance.**

---

## Sign-off

For each episode, the reviewer records:

```yaml
episode: EP##-<slug>
review_date: YYYY-MM-DD
reviewer: <name>
verdict:
  - SHIP-READY               # All sections passed
  - SHIP-WITH-CAUTION        # One or more P2 items remain; described below
  - BLOCKED                  # One or more P0/P1 items remain; described below
notes: |
  Free-text. Specifically: which section had any P1/P2 issues, what was done about them.
flagged_for_next_episode: |
  Free-text. Anything the next episode's reviewer should re-verify (e.g., a pronunciation drift that started here).
```

## Failure-mode escalation

- **P0 (BLOCKED — do not publish):** any false attribution; Ismaili-specific claim presented as generic Islam; any sacred name mangled; any quotation presented as critical-edition without verification.
- **P1 (SHIP-WITH-CAUTION):** repeated honorific stacking; one inline-phonetic read aloud; one anachronistic tech analogy; one missing first-mention honorific.
- **P2 (note for next episode):** listener-fit framing not explicit; one bridge to next episode missed.

A SHIP-READY verdict requires zero P0 and zero P1 findings.
