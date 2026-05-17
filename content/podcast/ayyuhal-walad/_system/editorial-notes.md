# Editorial Notes — Ayyuhal Walad (v3.5 re-run)

## Source

*Ayyuhal Walad — My Dear Beloved Son (or Daughter)* by Imam Abu Hamid Muhammad al-Ghazali. English translation by Irfan Hasan, from the Urdu rendering of the Arabic original (compiled within *Majmu'a Rasail Imam Ghazali*). 30-page PDF at `_system/source/Ayyuhal-Walad.pdf`.

## Translator decisions

- **Quranic translations** in chapter prose are attributed to **Yusuf Ali** on first per-chapter use. The Irfan Hasan source uses Muhammad Asad ("The Message of the Qur'an") for several but not all — we name Yusuf Ali for consistency and ease of cross-reference, and use translations that closely match Asad's where he is the closer rendering. Choice was made in the prior workspace and preserved.
- **Hadith translations** are Irfan Hasan's; cited by collection where known, or simply attributed to the Prophet (or Sufi master / Companion) with note.

## Phonetic architecture (v3.5)

Phonetics live ONLY in each episode's customize prompt `## Pronunciation` block (per R-PRONUNCIATION-IMPERATIVE). Chapters carry transliteration only — no inline `(PHO-ne-tic)` parens, no post-transliteration phonetic lines in blockquotes. The build script enforces this.

## Substitution decisions (per `04-common-term-substitutions.md` §2)

The default substitution policy is applied: *nafs* → **lower soul** (default) or **soul** (when contrasted), *shaytan* → **Satan**, *ruh* → **spirit**, *qalb* → **heart**, *aql* → **intellect**, *hawa* → **lower desire** or **passion**, *dunya* → **this world**, *akhirah* → **the Hereafter**, *jannah* → **paradise**, *jahannam* → **hell**, *qiyamah* → **the Day of Judgment**, *ilm* → **knowledge**, *hikmah* → **wisdom**, *sabr* → **patience**, *shukr* → **gratitude**, *malak/malaa'ika* → **angel(s)**, *niyyah* → **intention**, *zuhd* → **detachment from the world**, *wara'* → **scrupulousness**.

**Kept in Arabic (per §3):** *tawakkul*, *ikhlas*, *ihsan*, *taqwa*, *taqleed* (not used), *tasawwuf*, *bid'a*, *fard al-ayn*, *fard kifaya*, *halal*, *haram*, *ma'rifah*, *mujahadah*, *du'a*, *riya*, *iman* (mostly substituted to "faith"; kept once on first mention as gloss).

**Kept by exception:**
- *nafs* in ch01 at the one moment where the source explicitly defines it as the technical Sufi term ("Intelligent is the one who subdued his/her *nafs*"). Glossed inline.
- *nafs* in ch02 at the inline-gloss line introducing the Sufi tripartite-soul vocabulary ("In Sufi technical vocabulary, the nafs is the part of you that pulls toward base appetite…") which is the load-bearing beat of Benefit Two, plus the two surrounding verbatim Haatim blockquotes that the gloss anchors (acceptable under §3 verbatim-quote exception).
- *hadith qudsi* in ch05 — `qudsi` is kept as a hadith-classification term per §3 (technical vocabulary, no clean English equivalent). Phonetic added to shared manifest §4 (2026-05-17).
- Elsewhere always substituted.

## Honorific application (R-HONORIFIC-ONCE)

Each chapter expands the honorific at most once per figure:
- Prophet Muhammad — *peace and blessings be upon him* on first mention; *the Prophet* thereafter.
- Companions (RA) — *may Allah be pleased with him/her* on first mention; bare name thereafter.
- Imams (AS) — *peace be upon him* on first mention; bare alias thereafter.
- Sufi masters (RA, departed) — *may Allah have mercy upon him* on first mention; alias thereafter.

## Name alias application (per `05-name-alias-policy.md`)

First mention uses the full name; subsequent uses use the alias:
- Imam Abu Hamid Muhammad al-Ghazali → **Ghazali**
- Junaid al-Baghdadi → **Junaid**
- Sufyan al-Thawri → **Sufyan**
- Shaqiq al-Balkhi → **Shaqeeq**
- Hatim bin Ism al-Asamm → **Haatim**
- Dhu'l-Nun al-Misri → **Dhu'l-Nun**
- Imam Ali ibn Abi Talib → **Imam Ali**

## Carry-over from prior workspace

The 5-chapter segmentation was preserved from the archived prior workspace. The prior workspace's challenger converged to SHIP-READY with one residual P0 (Yusuf Ali attribution at ch01) and a set of pre-v3.5 transcript artifacts. This re-run authors every chapter file fresh under v3.5 — no chapter prose is copied from the archive.

## Open questions / flags

None at this time. The treatise is short and Ghazali's argument is unmistakable. Any future flags surface as `[CONTEXT NEEDED]` in chapter scratchpads.
