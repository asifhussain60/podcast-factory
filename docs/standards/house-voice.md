# House Voice — global style standard for voice normalization (WC8.8 / SN-1..SN-7)

**Status:** locked 2026-05-29 (Asif). **Scope:** every book, every source, every genre in the
podcast-factory corpus. The voice-normalization pipeline stage rewrites narration toward THIS
single standard so the whole library reads as one coherent, natural voice. The learning loop
refines this guide over time; it is the one place the target voice is defined.

> This governs the **Normalized** stage (between Core and Augmented). Input-adaptive,
> output-uniform: the normalizer detects the incoming register and maps it to the voice below.

---

## 1. The voice (SN-1)

**Editorial-modern, accessible — the Stripe Press / MIT Press register.** Warm, clear,
dignified, and flowing. Written for an intelligent general reader who is *not* a specialist:
nothing is dumbed down, but nothing assumes insider vocabulary either. The reader should feel
guided by one careful, confident writer — never aware that the underlying sources were a
classical translation, a lecture transcript, and a teaching story stitched together.

Touchstones: plain strong sentences; concrete over abstract; a calm, respectful authority;
generous but invisible transitions. Avoid: ornate "translationese", academic hedging, hype,
sermon cadence, and filler.

## 2. What may change, what may not (SN-2 — moderate latitude)

**May change (narration / exposition only):**
- Reflow run-on or choppy sentences into a natural rhythm.
- Smooth transitions between ideas and paragraphs.
- Unify tense and point of view within the house voice.
- Repair translationese (literal Arabic/Urdu word-order, stilted articles, awkward idiom).
- Standardize terminology and the rendering of names already glossed.

**MUST NOT change (hard rules):**
- **Scripture, hadith, and poetry are VERBATIM.** Quran verses, prophetic sayings, and quoted
  verse/poetry are never reworded, reordered, abridged, or paraphrased — only the prose
  *around* them is normalized. (Quoted material is detected and locked before the rewrite.)
- **No meaning change.** Every claim, qualification, attribution, and nuance present in the
  Core stage is preserved. Normalization is re-voicing, not re-interpreting.
- **No new content.** The normalizer does not add facts, examples, references, or commentary
  (that is the Augment stage's job, and it is attributed).

## 2b. Terminus technicus preservation (SN-7 — hard rule, `R_TERMINUS_PRESERVE`)

The drive toward an "accessible general-reader register" must NOT erase the tradition's own
vocabulary. A *terminus technicus* — a precise doctrinal term such as *tawil*, *zuhd*, *maʿrifa*,
*ikhlas*, *farḍ ʿayn* — is a concept, not a stylistic flourish, and is **never** flattened to a
lossy English paraphrase ("*tawil*" → "esoteric interpretation" is forbidden).

- **Preserve the PHONETIC form on every occurrence.** The term carries through in its
  transliterated (phonetic) form. On the **first** occurrence within an episode you **may** add a
  brief English gloss in parentheses — "*tawil* (the inner, esoteric meaning of scripture)" — and
  thereafter the term stands alone. Reducing a term to an English gloss only is forbidden.
- **Orthogonal to R-PHONETICS-OUT.** Arabic *script* (تأویل) is still stripped from
  podcast-bound output — NotebookLM's TTS cannot read it; the *phonetic* form (*tawil*) is what
  preserves the term. SN-7 protects the term's **identity**, not its script. (The reader UI
  re-pairs script with phonetic via `glossary.yml`; that is a render-time overlay, not the
  normalized prose.)

> The protect-list is **per-book, tradition-agnostic data** loaded at run time from
> `content/drafts/books/<slug>/_system/glossary.yml` (the `phonetic`/`transliteration` fields) —
> see `gemini_refine.load_protect_terms`. A Sufi treatise, a Stoic letter, and a Vedanta
> commentary each carry their own terms; the rule is the standard, the glossary is the data. An
> empty/absent glossary degrades gracefully to the general rule with no enumerated terms.

## 3. Point of view & register mapping (SN-6)

| Incoming register | Map to the house voice by… |
|---|---|
| Classical-Arabic translationese | De-literalize word order; modern idiom; keep the dignity, drop the stiffness. |
| Third-person scholarly | Keep the third person where it carries meaning; lift dryness into clear, warm exposition. |
| Lecture / spoken transcript | Remove verbal tics, false starts, and asides; convert speech rhythms to written prose. |
| Teaching story / narrative | Preserve the narrative arc; tighten pacing; consistent past-tense storytelling. |

Default address: let the source's natural POV stand unless it fights readability; do not force
second-person counsel except where the source itself is direct address (e.g. a letter).

## 4. Application & safety (SN-3, SN-4)

- **Auto-applied** as the Normalized stage artifact; the Studio shows **Source/Core vs
  Normalized** with a diff as the spot-check surface.
- **One global voice** — this guide, not a per-book style. Consistency across the library is
  the point.
- **Meaning-drift guards:** (a) scripture verbatim (locked before rewrite); (b) the diff tab is
  always one click away; (c) the podcast-challenger runs a doctrinal-fidelity check on the
  Normalized stage; (d) the learning loop flags recurring risky rewrites for human review.

## 5. Worked micro-examples

> **Translationese →**
> *Before:* "Verily the knowledge which is not acted upon, indeed it shall be a proof against
> its possessor on the Day of Standing."
> *After:* "Knowledge you don't act on becomes evidence against you on the Day of Judgment."

> **Lecture transcript →**
> *Before:* "So, um, the point here — and this is important — is basically that, you know, the
> Prophet, peace be upon him, he told us…"
> *After:* "The point is this: the Prophet, peace be upon him, told us…"

> **Scripture (UNCHANGED) →**
> A quoted verse stays exactly as rendered in the source; only the sentence introducing it is
> normalized.

---

*Decisions of record: SN-1..SN-6 in `_workspace/prompts/improvements/10-reader-redesign-decisions.md`;
plan item WC8.8 in `_workspace/plan/refactor/plan.yaml`.*
