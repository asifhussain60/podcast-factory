# kitab-al-riyad — published podcast assets

Published from `_workspace/books/kitab-al-riyad/` to this directory on **2026-05-23T09:02:49Z**.

- **Source git ref:** `develop@4e26c46355d1`
- **Episode count:** 15
- **NotebookLM mode:** 2-voice Extended Deep Dive

## NotebookLM upload (per episode)

For each EP## row below:

1. Create a new NotebookLM notebook (or open an existing one).
2. Upload `chapters/ch##-<slug>.txt` as the single source.
3. Open the Customize prompt box and paste the contents of `episodes/EP##-<slug>.txt`.
4. Click **Generate**.

The chapter file is the SOURCE (uploaded as-is); the episode file is the CUSTOMIZE PROMPT (pasted into the prompt box). Do not concatenate them — NotebookLM treats them as different inputs.

## Episode list

| EP | Chapter file (SOURCE) | Episode file (CUSTOMIZE PROMPT) | Topic |
|---|---|---|---|
| EP01 | `chapters/ch01-the-perfect-and-the-perfection-of-the-soul.txt` | `episodes/EP01-the-perfect-and-the-perfection-of-the-soul.txt` | the perfect and the perfection of the soul |
| EP02 | `chapters/ch02-soul-intellect-and-the-power-of-emanation.txt` | `episodes/EP02-soul-intellect-and-the-power-of-emanation.txt` | soul intellect and the power of emanation |
| EP03 | `chapters/ch03-the-soul-in-time-and-the-rejoinder-to-al-nusra.txt` | `episodes/EP03-the-soul-in-time-and-the-rejoinder-to-al-nusra.txt` | the soul in time and the rejoinder to al nusra |
| EP04 | `chapters/ch04-summary-perfection-of-the-soul.txt` | `episodes/EP04-summary-perfection-of-the-soul.txt` | summary perfection of the soul |
| EP05 | `chapters/ch05-the-intellect-as-the-first-creation.txt` | `episodes/EP05-the-intellect-as-the-first-creation.txt` | the intellect as the first creation |
| EP06 | `chapters/ch06-soul-and-spirit-one-substance-or-two.txt` | `episodes/EP06-soul-and-spirit-one-substance-or-two.txt` | soul and spirit one substance or two |
| EP07 | `chapters/ch07-souls-as-parts-or-traces.txt` | `episodes/EP07-souls-as-parts-or-traces.txt` | souls as parts or traces |
| EP08 | `chapters/ch08-the-human-as-fruit-of-the-worlds.txt` | `episodes/EP08-the-human-as-fruit-of-the-worlds.txt` | the human as fruit of the worlds |
| EP09 | `chapters/ch09-motion-stillness-hyle-and-form.txt` | `episodes/EP09-motion-stillness-hyle-and-form.txt` | motion stillness hyle and form |
| EP10 | `chapters/ch10-the-sections-of-the-world.txt` | `episodes/EP10-the-sections-of-the-world.txt` | the sections of the world |
| EP11 | `chapters/ch11-qada-and-qadar-fate-and-destiny.txt` | `episodes/EP11-qada-and-qadar-fate-and-destiny.txt` | qada and qadar fate and destiny |
| EP12 | `chapters/ch12-the-shariah-of-adam-and-the-first-speaker.txt` | `episodes/EP12-the-shariah-of-adam-and-the-first-speaker.txt` | the shariah of adam and the first speaker |
| EP13 | `chapters/ch13-prophets-as-teachers-monotheism-and-the-ranks.txt` | `episodes/EP13-prophets-as-teachers-monotheism-and-the-ranks.txt` | prophets as teachers monotheism and the ranks |
| EP14 | `chapters/ch14-tawhid-and-the-critique-of-al-mahsul.txt` | `episodes/EP14-tawhid-and-the-critique-of-al-mahsul.txt` | tawhid and the critique of al mahsul |
| EP15 | `chapters/ch15-book-summary.txt` | `episodes/EP15-book-summary.txt` | book summary |

## Republishing

This directory is **filesystem-only** and **not git-tracked**. It can be deleted and regenerated at any time by re-running:

```
scripts/podcast/publish_to_library.py kitab-al-riyad
```

from any worktree on the `podcast-factory` repo (the script resolves `library/` from `<repo-parent>/library/`).
