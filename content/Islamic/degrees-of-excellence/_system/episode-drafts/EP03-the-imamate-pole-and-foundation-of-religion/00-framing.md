# The Imamate, Pole of Religion

**Episode format:** `deep_dive` (two-host walkthrough). If this should be a debate instead, set `contract.episode_format: debate`. See [infra/claude-agents/podcast-challenger.md](../../../infra/claude-agents/podcast-challenger.md) Categories F + P for the format-specific constraints.

## Opening directive

In the first ten seconds, the hosts should name the work and the question this episode is asking. Do not open with "today we'll discuss". Start in the middle of the question.

## Audience

'Listeners who have the introduction''s context and are ready to enter al-Naysaburi''s treatise itself. They want his opening move: why he places the imamate, not prophecy, at the center of religion; why he treats it as a rational necessity that even its deniers confirm; and how he sets up nature and sacred law as two standing witnesses to the office. This is where the argument stops being previewed and starts being made, in the author''s own voice and order.

## Angle

`faithful_exposition` — the chosen lens. Faithful exposition = follow source authorial voice; comparative = bring in cross-tradition context; etc. The framing's other sections (Central tensions, Tone constraints) lock the lens into per-episode specifics.

## Length

Target ~50-60 min Audio Overview. Dense doctrinal material — let the hosts unfold layer by layer without rushing.

## Host dynamic

`curious_mind + scholar_companion`. NotebookLM's default English voice pair is John (male) for Host A and Hannah (female) for Host B. The CANONICAL pairing this skill enforces (per R-HOST-ROLE-PARITY in scripts/podcast/_rules.py, challenger Category Q): Host A (male) is the scholar / teacher / master / shaykh / guide role; Host B (female) is the seeker / student / debater / questioner / novice role. This pairing does NOT rotate across episodes within a book. If the contract's `host_dynamic` reverses this (e.g. `advocate_b + scholar_companion` putting Host B in the scholar role), the framing author MUST flip the host_a / host_b assignment so the male voice stays in the scholar pool.

## Central tensions to reach

The hosts MUST surface every one of these tensions, by name, in the conversation:

  - 'The imam before the messenger. Al-Naysaburi''s most startling move is to refuse precedence to prophecy: affirming the imamate, he argues, already affirms the messengership, because whoever knows the imam knows the messenger, but not the reverse. The hosts should let this inversion land as the deliberate provocation it is, not smooth it over.

## Tone constraints

The hosts must NOT do the following:

  - 'Follow al-Naysaburi''s own order: the pole of religion and the priority of the imam first, then the necessity grounded in nature and intellect, then the mirroring of the two creations and the two witnesses. Do not import the concrete ladder of excellence here; it is out of scope here.

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
