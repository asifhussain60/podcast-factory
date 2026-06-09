# What Ismaili Interpretation Is

**Episode format:** `deep_dive` (two-host walkthrough). If this should be a debate instead, set `contract.episode_format: debate`. See [infra/claude-agents/podcast-challenger.md](../../../infra/claude-agents/podcast-challenger.md) Categories F + P for the format-specific constraints.

## Opening directive

In the first ten seconds, the hosts should name the work and the question this episode is asking. Do not open with "today we'll discuss". Start in the middle of the question.

## Audience

Thoughtful adult readers approaching the Ismaili science of inner interpretation (ta'wil) for the first time through al-Nu'man ibn Hayyun's Asas al-Ta'wil — listening for the basic vocabulary they will need to walk into the six Speaker-Prophet chapters that follow, and for the editor Arif Tamir's own framing of why this 10th-century Fatimid manuscript was held in private custody for a thousand years before its 1960 Beirut printing.

## Angle

`faithful_exposition` — the chosen lens. Faithful exposition = follow source authorial voice; comparative = bring in cross-tradition context; etc. The framing's other sections (Central tensions, Tone constraints) lock the lens into per-episode specifics.

## Length

Target ~50-60 min Audio Overview. Dense doctrinal material — let the hosts unfold layer by layer without rushing.

## Host dynamic

`curious_mind + scholar_companion`. NotebookLM's default English voice pair is John (male) for Host A and Hannah (female) for Host B. The CANONICAL pairing this skill enforces (per R-HOST-ROLE-PARITY in scripts/podcast/_rules.py, challenger Category Q): Host A (male) is the scholar / teacher / master / shaykh / guide role; Host B (female) is the seeker / student / debater / questioner / novice role. This pairing does NOT rotate across episodes within a book. If the contract's `host_dynamic` reverses this (e.g. `advocate_b + scholar_companion` putting Host B in the scholar role), the framing author MUST flip the host_a / host_b assignment so the male voice stays in the scholar pool.

## Central tensions to reach

The hosts MUST surface every one of these tensions, by name, in the conversation:

  - >

## Tone constraints

The hosts must NOT do the following:

  - Walk the introduction in the order Arif Tamir actually walks it. He opens with

## Pronunciation hooks

[LLM-FILL — list every non-English term, transliteration, or name appearing in the source, with respelling and brief gloss. Or set contract.phonetic_overrides.]

## Anti-noise rules

- Quote directly from the source when discussing a beat. Do not paraphrase the source's voice.
- Treat this as a standalone Audio Overview. Do not reference other Audio Overviews — they are not in NotebookLM's context.
- Do not abbreviate honorifics; speak them in full.
- End on a question, not a conclusion.
- NO cross-chapter references. This episode's chapter file is the entire source NotebookLM sees. The hosts must NOT say "the previous chapter showed", "as we'll see later", "the next chapter answers", "earlier in the book", etc. Treat the chapter as a self-contained episode.

## Do not (forbidden vocabulary and framings)

The hosts must NOT use any of the following — these are the canonical DENY lists per `scripts/podcast/_rules.py::MODERNIZE_DENY` + `SURPRISE_DENY`. The substring scanner in `build_episode_txt.py` refuses any framing that omits this block.

- Modernization terms: Twitter, X (the platform), social media, algorithm, content creator, internet, YouTube, TikTok, Instagram, livestream, hashtag, 21st century, in our modern world, platforms like
- Surprise-noise phrases: wow, that's so interesting, right?, it's chilling, it's devastating, it's terrifying, it's profound, it's fascinating, it's amazing
- Imitation-of-authority: rephrasings of the work's original arguments in casual / commercial / self-help register

---

Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.
