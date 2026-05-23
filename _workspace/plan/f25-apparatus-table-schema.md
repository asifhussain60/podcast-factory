# F25 — Apparatus-table schema for 99-show-notes.md

**Status**: Validator #8 landed 2026-05-23 (defensive — silent skip if file absent). Generation infrastructure still pending; depends on F26 name-aliases.yml schema v2.

## Why this exists

The podcast pipeline's empirically-validated doctrine is **TTS-safe audio**: Arabic person/book/concept names are removed from the chapter prose and framing (F20 + F29). This is correct for what the audience HEARS — NotebookLM's TTS mangles unfamiliar Arabic ("Qaf" → "cough", "al-Shams" → various) and the listener carries the meaning forward better with English labels.

But the SCHOLARLY apparatus still belongs somewhere. A specialist reading the show-notes needs to know:

- What the original Arabic transliteration was
- Which category that figure belongs to (person / book / concept / doctrine / place)
- Its written form (the proper scholarly spelling, often with diacritics)
- The audio label the listener actually heard (so the specialist can match audio ↔ written)
- The chapter line where that label first appears (so the specialist can locate the discussion)

`99-show-notes.md` is the canonical home for this written-layer apparatus. The audio layer stays clean; the written-layer carries the apparatus that scholarly readers expect.

## Required schema

Every episode's `99-show-notes.md` must contain a section with this exact header:

```
## Name and Title Preservation Table
```

The table under that header must have these five columns (in any order, but each label present):

| Column | Description |
|---|---|
| `Original / Transliteration` | Arabic name as printed in source (e.g. "al-Qāḍī al-Nuʿmān", "Nahj al-Balāgha") |
| `Category` | One of: `person` / `book` / `concept` / `doctrine` / `place` / `surah` |
| `Written Form` | Scholarly written form with diacritics where standard (e.g. "Hamīd al-Dīn al-Kirmānī") |
| `Audio Label` | The English label the listener heard ("the Fatimid philosopher", "the author") |
| `First Audio Use` | The chapter section/line where that label first appears (e.g. "ch07 §3 Beat 1") |

## Example

```markdown
## Name and Title Preservation Table

| Original / Transliteration | Category | Written Form | Audio Label | First Audio Use |
|---|---|---|---|---|
| Ḥamīd al-Dīn al-Kirmānī | person | Hamīd al-Dīn al-Kirmānī | the author | ch07 §1 Beat 1 |
| Nahj al-Balāgha | book | Nahj al-Balāgha | *The Path of Eloquence* | ch07 §2 Beat 3 |
| al-Naṭiq | concept | al-Nāṭiq | the speaker-prophet | ch07 §3 Beat 2 |
| Sūrat al-Shams | surah | Sūrat al-Shams | the chapter on the sun | ch07 §4 Beat 5 |
```

## Validator behavior (Validator #8, [build_episode_txt.py](../../scripts/podcast/build_episode_txt.py))

`assert_show_notes_has_apparatus_table(content, file_path)` runs from `build()` after building the episode `.txt`. It:

1. **Silent skip** if `99-show-notes.md` does not exist for the episode (current state of all KaR episodes — F25 generation is still pending).
2. **P1 flag** ("F25-APPARATUS-TABLE") if the file exists but lacks the `## Name and Title Preservation Table` section header.
3. **P1 flag** if the file exists with the section header but missing one or more required column labels.

The validator does NOT fail-hard. It uses `_flag_p1`, surfacing the issue in the challenger sidecar without blocking ship.

## Generation infrastructure (pending — F26 dependency)

The apparatus table cannot be auto-generated from chapter prose alone — it needs the figure → audio_label mapping that `name-aliases.yml v2` (F26) is designed to provide:

- Phase 0d emits `name-aliases.yml v2` with each figure's category, written form, audio label, and first-use anchor (from Phase 0e enrichment metadata).
- Phase 0g's `author_framing()` produces the framing.md AND `99-show-notes.md`, populating the apparatus table by joining the chapter prose's labels against `name-aliases.yml v2`.

Until F26 lands, `99-show-notes.md` is either absent (silent — current state) or human-authored. Both are acceptable; the validator catches drift only when a file exists.

## Migration path

- **KaR (shipped)**: no show-notes files exist. Validator silent. No action.
- **asaas-al-taveel (in flight)**: when F26 lands before Phase 0g, asaas's episodes inherit auto-generated show-notes.
- **Future books**: F26 + apparatus-table generation are pipeline default.

## See also

- [f27-validator-drafts.md](f27-validator-drafts.md) §"Validator #8" — original draft
- [pipeline-debt.md](pipeline-debt.md) §"True remaining P0 framework debt" — F25 status
- [cohesion-audit-2026-05-23.md](cohesion-audit-2026-05-23.md) — broader cohesion picture
