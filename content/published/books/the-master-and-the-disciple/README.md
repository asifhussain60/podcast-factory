# the-master-and-the-disciple — published podcast assets

Published from `content/drafts/the-master-and-the-disciple/` to this directory on **2026-05-25T21:39:00Z**.

- **Source git ref:** `develop@a664c7c94eef`
- **Episode count:** 6
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
| EP01 | `chapters/ch01-the-call-and-the-covenant.txt` | `episodes/EP01-the-call-and-the-covenant.txt` | the call and the covenant |
| EP02 | `chapters/ch02-will-command-and-the-seven.txt` | `episodes/EP02-will-command-and-the-seven.txt` | will command and the seven |
| EP03 | `chapters/ch03-world-hereafter-and-the-right-of-wealth.txt` | `episodes/EP03-world-hereafter-and-the-right-of-wealth.txt` | world hereafter and the right of wealth |
| EP04 | `chapters/ch04-the-greater-shaykh-and-the-naming.txt` | `episodes/EP04-the-greater-shaykh-and-the-naming.txt` | the greater shaykh and the naming |
| EP05 | `chapters/ch05-father-revealed-and-the-faces-of-seeking.txt` | `episodes/EP05-father-revealed-and-the-faces-of-seeking.txt` | father revealed and the faces of seeking |
| EP06 | `chapters/ch06-justice-monotheism-and-the-guardians.txt` | `episodes/EP06-justice-monotheism-and-the-guardians.txt` | justice monotheism and the guardians |

## Republishing

This directory is **filesystem-only** and **not git-tracked**. It can be deleted and regenerated at any time by re-running:

```
scripts/podcast/publish_to_library.py the-master-and-the-disciple
```

from any worktree on the `podcast-factory` repo (the script resolves `content/published/` from `<repo-parent>/content/published/`).
