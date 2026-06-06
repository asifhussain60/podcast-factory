# The Shaykh and the Disciple's Rule of Life

**Episode format:** `deep_dive` (two-host walkthrough). If this should be a debate instead, set `contract.episode_format: debate`. See [infra/claude-agents/podcast-challenger.md](../../../infra/claude-agents/podcast-challenger.md) Categories F + P for the format-specific constraints.

## Opening directive

In the first ten seconds, the hosts should name the work and the question this episode is asking. Do not open with "today we'll discuss". Start in the middle of the question.

## Audience

Thoughtful adult readers continuing through Imam al-Ghazali's letter *Ayyuha al-Walad* (ay-YU-hal WA-lad — "O My Beloved Son"). The previous two episodes carried the diagnosis (knowledge unaccompanied by righteous action does not save the scholar) and the cure in outline (the dawn watch, the rule that worship is obedience to the Prophetic *Shari'ah* — sha-REE-ah — under inner *mujahadah*, and the first four conditions of the sincere seeker). This episode walks the working rule of life the disciple is now handed. It has three braided strands. First, the eight benefits Hatim ibn Ism — disciple of the Khurasanian master Shaykh Shafeeq al-Balkhi — brought back from long inward observation of the people of the world: the only beloved who descends into the grave (righteous deeds); the discipline against the *Nafs* (NAFS — lower self) anchored in Quran 79:40–41; the practice of sending wealth ahead by spending in the Way of Allah anchored in Quran 16:96; *Taqwa* (TAQ-wa — God-conscious reverence) as the only true nobility anchored in Quran 49:13; contentment with the assigned portion anchored in Quran 43:32; recognizing *Shaytan* (shay-TAAN) alone as the enemy anchored in Quran 35:6; the certitude that sustenance is the responsibility of Allah anchored in Quran 11:6; and *Tawakkul* (ta-WAK-kul — reliance) on the One who suffices anchored in Quran 65:3. Shaykh Shafeeq's verdict is that whoever acts on these eight has acted on all four sacred Books — the *Tawrat* (taw-RAAT), the *Injil* (in-JEEL), the *Zabur* (za-BOOR), and the Quran. Second, the figure at the center of the seeker's life — the *Shaykh al-Kamil* (shaykh al-KAA-mil — perfected spiritual guide), the *Murshid al-Kamil* (mur-SHID al-KAA-mil) — Ghazali's farmer-tending-the-crop figure, the full catalog of qualifications a true Shaykh must possess, the rule that the Shaykh's *Bay'a* (bay-AH — solemn covenant) must chain unbroken back to the Messenger of Allah ﷺ, the outer etiquette (no argument, no over-praying in his presence, obedience to whatever he commands within the *Shari'ah*) and the inner etiquette (no doubt of him in the heart — if doubt arises, the disciple withdraws until the inward and outward come back into harmony), and the bright line that a true Shaykh cannot and will not command anything forbidden by the *Shari'ah* (the diagnostic that separates the master from the impostor). Third, the inner vocabulary of the Path itself — Ghazali gives one verbatim definition each for *Tasawwuf* (ta-SAW-wuf — the inner science of purifying the soul), servitude, *Tawakkul*, and *Ikhlas* (ikh-LAAS — sincerity), and tells the disciple to stop asking the rest of his questions for now and put what he has into practice. The closing register is the threshold of the parting admonitions, where the rule of life turns into its final counsel.

## Angle

`faithful_exposition` — the chosen lens. Faithful exposition = follow source authorial voice; comparative = bring in cross-tradition context; etc. The framing's other sections (Central tensions, Tone constraints) lock the lens into per-episode specifics.

## Length

Target ~22–40 min Audio Overview. Multi-thematic; let the conversation breathe.

## Host dynamic

`curious_mind + scholar_companion`. NotebookLM's default English voice pair is John (male) for Host A and Hannah (female) for Host B. The CANONICAL pairing this skill enforces (per R-HOST-ROLE-PARITY in scripts/podcast/_rules.py, challenger Category Q): Host A (male) is the scholar / teacher / master / shaykh / guide role; Host B (female) is the seeker / student / debater / questioner / novice role. This pairing does NOT rotate across episodes within a book. If the contract's `host_dynamic` reverses this (e.g. `advocate_b + scholar_companion` putting Host B in the scholar role), the framing author MUST flip the host_a / host_b assignment so the male voice stays in the scholar pool.

## Central tensions to reach

The hosts MUST surface every one of these tensions, by name, in the conversation:

  - >

## Tone constraints

The hosts must NOT do the following:

  - >

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
