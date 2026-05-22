# Triage notes — Kunooz Al-Hikmah

**Target book**: `lectures/kunooz-al-hikmah/`
**Source language**: Urdu (with extensive Arabic citations + scholar names)
**Speaker**: lectures by a member of the Dawoodi Bohra clergy
**Content type**: Four-part lecture series introducing the Risala
*Kunooz al-Hikmah al-Mazboora li-Arbab al-Isma* by Sayyidina Ali bin Hibatullah.

## Inputs

- `audio/01-04 GH - Kunooz Al-Hikmah.mp3` — original recordings (~46MB total).
- `audio/01 GH - Kunooz Al-Hikmah-proj.llc` — LosslessCut project file (incidental).
- `turboscribe/01-04 GH - Kunooz Al-Hikmah.txt` — TurboScribe transcripts
  (timestamped, English-paraphrased where Urdu/Arabic was rendered).
- `turboscribe/TurboScribe Export 1623213481.zip` — original export archive.

## Processing hints

- **Source of truth: TurboScribe txts**, not Azure Speech. They were
  human-curated externally. The MP3s are reference for spot-checking only.
- Strip timestamps (`(MM:SS - MM:SS)` lines) when importing to
  `transcripts/EP##-slug.transcript.txt`.
- Phonetic/transliteration coverage will need a pronunciation pass —
  many Arabic names paraphrased by ASR (e.g. "Qunool-ul-Hikmah" should be
  "Kunooz al-Hikmah"). Add corrections to
  `_system/pronunciation.md` during chapter authoring.

## Triage policy

| Asset | Action | Reason |
|-------|--------|--------|
| MP3 files | KEEP at `_source/audio/` (gitignored) | Reference for human spot-check |
| `.llc` file | KEEP at `_source/audio/` (gitignored) | Editing project provenance |
| TurboScribe `.txt` | KEEP at `_source/turboscribe/` (tracked) | Training-valuable, small |
| TurboScribe `.zip` | KEEP at `_source/turboscribe/` (gitignored) | Original-export provenance |
