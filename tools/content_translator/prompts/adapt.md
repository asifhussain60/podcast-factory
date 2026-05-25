# Adaptation Conventions — KAHSKOLE English Layer

## Goal
Transform the literal Azure translation (`raw-extract.en.md`) into polished scholarly
English that reads beautifully while faithfully conveying every doctrinal point.
Output goes to `adapted-extract.en.md` + `adaptation-citations.jsonl`.

## Style targets
- **Tone:** scholarly, calm, reverent. Mirror IIS publications (Daftary, Walker, Hunzai).
  Not preachy, not academic-cold.
- **Sentence rhythm:** vary — short declarative sentences interleaved with longer subordinate
  clauses. Avoid run-ons and choppy strings.
- **Paragraph flow within sections:** each section reads as a continuous argument;
  paragraphs connect with topic + transition sentences.
- **Cross-section structure:** section markers are inviolable. Do NOT merge sections.

## Structure rules
- Every `<!-- section N (id=X, raw_sort=Y): label -->` marker must appear verbatim.
- Under each section marker, use the R2 English topic title as a `##` heading.
  If no R2 title exists, translate the Urdu label literally.
- Section body: one or more paragraphs of polished prose.
- Blockquotes (`>`), tables, image description blocks — preserve exactly from the source.

## Terminology — preserve and gloss
First occurrence of any technical term: transliterate + English gloss in parens.
Thereafter: transliteration alone (no repeated glosses).

| Urdu/Arabic | Transliteration | English gloss |
|---|---|---|
| عقل اول | al-ʿAql al-Awwal | the First Intellect |
| منبعثین / منبعث | al-Munbaʿithūn / al-Munbaʿith | the Emanators / the Emanator |
| مبدع تعالی | Mubdiʿ Taʿālā | the Originator, Most High |
| تاویل | taʾwīl | esoteric exegesis |
| دعوت | daʿwa | the summons / the invitation |
| داعی / دعات | dāʿī / duʿāt | Summoner / the Summoners |
| کمال اول | kamāl awwal | primary perfection |
| کمال ثانی | kamāl thānī | secondary perfection |
| حد عالی | ḥadd ʿālī | the upper limit |
| حد دانی | ḥadd dānī | the lower limit |

## Augmentation — what counts
Add **0–3 augmentations per section** where they add genuine value:
- Cross-reference to a parallel passage in a named Fatimid-era work
- Disambiguate a term with different Ismaili sub-tradition usages
- A one-line attestation from a Fatimid source that strengthens the argument
- Explain Quranic context the original assumed the reader already knew

Do NOT add augmentations for:
- Background already in the source text
- "As is well known…" statements (the original didn't need help with those)
- Modern scholarly commentary (Daftary, Halm, Walker) — cite primary sources first
- Anything you cannot pin to a specific named work with high confidence

Each augmentation gets a `[^cite-N]` inline footnote marker and a corresponding
JSONL entry in `adaptation-citations.jsonl`.

## adaptation-citations.jsonl schema
One JSON object per line:
```jsonl
{"cite_id":"cite-1","section_id":1093,"section_position":1,"excerpt":"As Kirmani writes in Rahat al-ʿAql…","source_work":"Rahat al-ʿAql","source_author":"Hamid al-Din al-Kirmani","source_authority":"Fatimid Dāʿī, d. ~1020 CE","source_location_hint":"opening cosmological section","confidence":"high","training_grounded":true}
```
- `confidence`: `"high"` only — drop medium/low rather than include
- `training_grounded`: always `true` (no WebFetch used)

## Hard rules
- NEVER modify `raw-extract.md`
- NO WebFetch / WebSearch — all augmentation from Claude's training only
- Every augmentation needs high-confidence attribution to a specific named work
- Preserve ALL `⟪ar:…⟫` and `⟪quran S:A⟫` markers exactly as in the source
- Do not invent ayat numbers. Do not fabricate hadith chains.
