# Pronunciation — Degrees of Excellence (book-specific overrides)

Per-book phonetic overrides. Read by `build_episode_txt.py` (via `_rules`) and
`podcast-challenger`. **May ADD terms; MUST NOT contradict** the per-book
glossary at `_system/glossary.yml` (the shared `content/_shared/arabic/` manifest was
retired in the 2026-05-23 restructure).

Format: pipe table.

Filled 2026-08-01 after the post-production review of the first audio run. The table
was empty, and five of the six episode framings carried an English *gloss* in the
phonetic position (`arkan: the pillars`) rather than a phonetic. The framing block
instructs the hosts to "say each term ONCE using its phonetic form", so they were told
to use a phonetic and handed a translation — which is how *arkan* was spoken as
"Archon", *mafdul* as "Mathdul", and *masbuq* as "Mazbuck".

Stress is marked by CAPITALS on the stressed syllable. `ee` is a long i (machine),
`oo` a long u (boot). `kh` is the ch of Scottish *loch*; `gh` is a voiced back r;
`q` is a k made far back in the throat.

**Two symbols for long A, and the difference is real.** Arabic long *alif* has two
values depending on what sits next to it:

- `aa` — the default, a long front-to-central [aa] as in *father*: **imam**, **zakat**,
  **al-Naysaburi**, **walaya**, **Yasin**, **bayt al-mal**.
- `AH` — the *backed* value, as in the o of *hot* or *mom*. Long alif retracts toward
  the back of the mouth when it touches one of the emphatic (velarized) consonants
  — ط ظ ص ض ق, and to a lesser degree غ خ ر. In that environment an English speaker
  genuinely hears something closer to "o": **Taha**, **ahl al-zahir**, **ahl al-batil**,
  **tiryaq**.

The letter `o` is deliberately NOT used for either. English orthography reads a bare
`o` as the /oh/ of *go, toe, no*, so a respelling like "TOH-haa" would be spoken
"toe-ha" — further from the Arabic than the spelling it replaced. `AH` gets the backed
vowel without inviting the diphthong.

| Term | Phonetic | Notes |
|---|---|---|
| imamate | IM-uh-mayt | English word, three syllables. The book's central term (74 uses). Garbled in 33 of 34 utterances on the first run — as *imit*, *emma*, *emmet*, *emit*, *imana*, and once as "Emirah", a different office entirely. |
| imam | i-MAAM | Resolved cleanly on the first run; listed so it is never re-derived from *imamate*. |
| vicegerent | vice-JEER-uhnt | English word. Garbled 8 times against 4 clean, including the closing sentence of the final episode as "vice labyrinth". |
| al-Naysaburi | an-nay-saa-BOO-ree | The author. Spoken three different ways across three episodes. Matches `glossary.yml`. |
| qutb | KOOTB | The pole. One syllable. |
| asas al-din | ah-SAAS ad-DEEN | Foundation of religion. |
| tawhid | tow-HEED | Divine unity. |
| ta'wil | taa-WEEL | Inner interpretation. |
| tashbih | tash-BEEH | Anthropomorphism. |
| arkan | ar-KAAN | The pillars/elements. Spoken as "Archon" on the first run, wrapped in a fabricated attribution. |
| tiryaq | tir-YAHQ | The antidote. |
| ya'sub | yaa-SOOB | The chief (of bees). |
| ahl al-zahir | AHL az-ZAH-hir | The literalists. |
| Maghrib | MAGH-rib | The west / North Africa. |
| fay | FIE | Rhymes with "eye". The return/bestowal. |
| nutq | NOOTQ | Articulate reason. One syllable. |
| taslim | tas-LEEM | Trusting submission. |
| raiya | ra-EE-ya | The flock, the subjects. |
| sais | SAA-is | The steersman. |
| mafdul | maf-DOOL | The one surpassed. Spoken as "Mathdul". |
| masbuq | mas-BOOQ | The one preceded. Spoken as "Mazbuck". |
| qibla | QIB-lah | Direction of prayer. |
| khutba | KHUT-bah | The sermon. |
| zakat | za-KAAH | The alms. |
| khums | KHOOMS | The fifth. One syllable. |
| hudud | hu-DOOD | The prescribed penalties. |
| walaya | wa-LAA-ya | Bond of allegiance. |
| bayt al-mal | BAYT al-MAAL | The public treasury. |
| da'irat al-din | DAA-i-rat ad-DEEN | The circle of religion. |
| Taha | TAH-haa | Quranic name, ch. 20. |
| Yasin | YAA-seen | Quranic name, ch. 36. |
| nass | NAHSS | Designation by explicit naming. |
| sunna | SOON-nah | God's established way. |
| nur al-imama | NOOR al-i-MAA-ma | The light of the imamate. |
| falta | FAL-tah | A hasty slip. |
| Ghadir Khumm | gha-DEER KHOOM | The designation event. Spoken as "Qadir Kum". Present in `chapters/ch05e`, not in any framing — added to the EP05 block so it is covered wherever it is read from. |
| mutimm | moo-TIMM | The perfector. |
| ghulat | goo-LAAT | The exaggerators. |
| ahl al-haqq | AHL al-HAQQ | The people of truth. |
| ahl al-batil | AHL al-BAH-til | The people of falsehood. |
