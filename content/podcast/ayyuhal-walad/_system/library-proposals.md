# Library Proposals — Staging File for Journal Cross-Pollination

**Source:** *Ayyuhal Walad* by Imam Al-Ghazali (trans. Irfan Hasan).
**Status:** staged from dry-run; covers only 3 of 22 sections. Full proposals will follow once all sections are refined.
**To apply:** run `/podcast apply ayyuhal-walad` *after* the full run completes and you have reviewed this file.

This file is the **only** path by which the podcast skill proposes additions to the journal's live libraries. The skill never writes to those files directly — every change goes through this staging file and through your explicit approval at the apply step.

---

## Tier 1.1 — Proposals for `content/babu-memoir/_system/translations-glossary.md`

These are pronunciation entries — phonetic transcriptions of Arabic/Sufi terms encountered in this source. Format matches the existing glossary.

| Term | Phonetic | Gloss | Confidence |
|---|---|---|---|
| Tasawwuf | Ta-saw-wuf | The Islamic spiritual path; inner purification. | high |
| Tawakkul | Ta-wak-kul | Reliance on God after right action. | high |
| Ikhlas | Ikh-laas | Sincerity; pure motive in worship. | high |
| Ihsan | Ih-saan | Spiritual excellence; worshipping God as if seeing Him. | high |
| Fard al-'ayn | Fard al-Ayn | A personal obligation on every individual. | high |
| Fard Kifaya | Fard Ki-faa-ya | A communal obligation discharged by some on behalf of all. | high |
| Sharee'ah | Sha-ree-ah | The revealed law. | high |
| Ahkamul Hakimeen | Ah-kaa-mul Haa-ki-meen | The Supreme Ruler; an epithet for God. | high |
| Ayyuhal Walad | Ay-yu-hal Wa-lad | "O Beloved Son" — Ghazali's letter to a disciple. | high |
| Ihya al-Uloom ad-Deen | Ih-yaa al-U-loom ad-Deen | "Revival of the Religious Sciences" — Ghazali's magnum opus. | high |
| Majmu'a Rasail | Maj-moo-a Ra-saa-il | "Collection of Treatises." | high |
| Shaykh al-Kamil | Shaykh al-Kaa-mil | The perfected scholar; one who can cure diseases of the heart. | high |
| Sirat al-Mustaqeem | Si-raat al-Mus-ta-qeem | The straight path. | high |
| Wajib | Waa-jib | Obligatory (a juristic category). | high |
| Nafs | Nafs | The lower self; the appetitive ego. | high |
| Riya | Ri-yaa | Showing off; ostentation. | high |
| Hasad | Ha-sad | Jealousy; envy. | high |

## Tier 1.2 — Proposals for `quotes-library.txt`

Candidate aphoristic lines from Ghazali for the journal's quotes library. Each is faithful to the source's English wording with light articulation adjustment per the new Stage 12 rule. Source line numbers reference `_meta/normalized.md`.

> "I seek refuge in Allah from knowledge that is of no benefit."
> — Prophet Muhammad, peace and blessings be upon him, quoted by Ghazali in *Ayyuhal Walad*, Introduction.

> "Tasawwuf rests on two qualities: obedience to Allah, and mercy toward Allah's creation. Either quality without the other is not Tasawwuf."
> — Imam Al-Ghazali, *Ayyuhal Walad*, Reality of Tasawwuf.

> "Every kind of animosity can be corrected, except the animosity born of jealousy. That one cannot be rectified."
> — Arabic poetry quoted by Ghazali, *Ayyuhal Walad*, Admonition One.

> "Spend your attention where it can do good."
> — Imam Al-Ghazali (paraphrased closing line), *Ayyuhal Walad*, Admonition One.

> "We the company of prophets have been ordered by Allah to address people according to the measure of their intellects."
> — Prophet Muhammad, peace and blessings be upon him, hadith quoted by Ghazali in *Ayyuhal Walad*, Admonition One.

## Tier 1.3 — Proposals for `clinic-library.txt`

The journal's `clinic-library` contains pastoral / counseling vignettes. Three candidates from this run:

> **The student's question.** A student spends years acquiring knowledge and then realizes he does not know which of his learnings will matter in the end. The recognition is itself the beginning of wisdom.
> — *Ayyuhal Walad*, Introduction.

> **Two qualities, not one.** Outer discipline without inner mercy produces legalism. Inner mercy without outer discipline produces sentimentality. Tasawwuf requires both held together.
> — *Ayyuhal Walad*, Reality of Tasawwuf.

> **The fourfold patient.** Of the four kinds of person who asks a religious question — the jealous, the foolish, the impatient self-interpreter, and the genuine seeker — only the fourth can be helped. The pastor's first task is discernment.
> — *Ayyuhal Walad*, Admonition One.

---

## Borderline candidates (Tier 1.x — held for review)

See `06b-borderline.md` when this dry-run extends to all 22 sections. None for this sample.

---

## Apply notes

When `/podcast apply ayyuhal-walad` runs, the apply gates per Stage 16 will:
1. Verify each target library has no uncommitted git changes.
2. Generate a unified diff per proposal.
3. Present diffs for user acceptance (all / some / none).
4. Apply accepted entries with dedup against existing rows.
5. Commit with message `podcast(ayyuhal-walad): library proposals merged`.
6. Re-run journal quality gates.

No changes happen until you run the apply command.
