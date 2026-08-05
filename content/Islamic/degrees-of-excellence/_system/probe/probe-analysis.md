# Pronunciation probe — analysis

- **Book:** degrees-of-excellence
- `probe_analyst_version: 1.0`

## Run 2 (2026-08-01, Default length) — PRONUNCIATION-PARTIAL

- **Audio:** `m4a/The_Imam_as_a_Law_of_Physics.m4a` (18:12)
- **Transcript:** `EP00-pronunciation-probe/probe-run2.transcript.txt`

The glossary source plus Default length worked: **every one of the 39 terms was
spoken**, against 9 in run 1. The framing's structural instructions were still
ignored — it is a themed episode, it opens on a hook, and it says "deep dive"
twice despite the deny-list — so coverage comes from what the SOURCE contains,
never from telling the hosts how to read it. Worth remembering for any future
probe: put nothing in the source you do not want spoken, and expect the framing
to shape tone but not structure.

### Plain transliteration beats a respelling — the run-1 terms, re-tested

| Term | Run 1 (respelling) | Run 2 (plain) | |
|---|---|---|---|
| walaya | `wa-LAA-ya` → "wa la ya" | `walaya` → "walaya" | plain wins outright |
| khutba | `KHUT-bah` → "KHU Tiba" | `khutba` → "Chutbah" | plain better |
| sais | `SAA-is` → "a SAA, is" | `sais` → "seis" | plain better |
| nur al-imama | `NOOR al-i-MAA-ma` → "NO or Ali Masma" | `nur al-imama` → "Nur Ali Mama" | plain better, still wrong |
| al-Naysaburi | `an-nay-saa-BOO-ree` → 2 variants | `al-Naysaburi` → 13 variants | both fail |
| vicegerent | `vice-JEER-uhnt` → "vice jeer hunt" | `vicegerent` → "the vice spirit of God" | both fail |
| tawhid | `tow-HEED` → "toheed" | `tow-HEED` → "Toheed" | control held |

The two-syllable respellings held across both runs; every longer one lost to the
plain form. The withdrawal of the other 38 was the right call.

### Heard clean — 21 terms, written to the cross-book ledger

al-Kirmani · Maghrib · arkan · raiya · ya'sub · Taha · Yasin · nass · falta ·
mafdul · mutimm · fay · hudud · qibla · ghulat · walaya · Ghadir Khumm ·
asas al-din · da'irat al-din · tiryaq · tawhid

Each said the same way every time it appeared. These are `confirmed` in
`content/knowledge-base/pronunciations.jsonl` and will be skipped by every future
probe, in this book and any other.

### Heard wrong — 8 terms, needing a decision

| Term | Told to say | Came out as |
|---|---|---|
| al-Naysaburi | `al-Naysaburi` | 13 different ways: Al-Nisaburi ×3, Alnais Saburi, Ale Saburi, Ali Saburi, Al-Nay Sabari, Al-Nasaburi, Al Nasabiri, Alanesaburi, almaburi, al-Naisaburi, Al-Nasibiri |
| imamate | `imamate` | "the MFA", "the Imamat", "the Yamavat", "the image", "the Yamam" |
| vicegerent | `vicegerent` | "the vice spirit of God" |
| ahl al-haqq | `ahl al-haqq` | "the Allah Haq" |
| qutb | `qutb` | "the quad" |
| nutq | `nutq` | "the Nutka", "the Nutkue" |
| khums | `khums` | "the comes" |
| nur al-imama | `nur al-imama` | "the Nur Ali Mama" |

**ahl al-haqq is the sharpest of these.** "the Allah Haq" puts the divine name
into a phrase that does not contain it — a doctrinal error, not just a
mispronunciation, and the one item here that should not ship whatever is decided
about the rest.

**al-Naysaburi is the most consequential.** It is the author, named in every
episode, and thirteen renderings in eighteen minutes means a listener cannot
tell they are hearing one person. The framing's own `R-STABLE-ROLE-LABELS` rule
already prescribes the remedy for exactly this — one fixed English label per
figure — and "the author" is what the episodes already use elsewhere.

### Close but imperfect — 10 terms, left unsettled

Rahat al-Aql → "Rahat al-Aq" · sais → "seis" · masbuq → "Maspuk" ·
bayt al-mal → "Beit Amal" · ithbat → "ifbat" · khutba → "Chutbah" ·
tashbih → "tashbi" · ahl al-batil → "Al al-Batil" · ahl al-zahir → "Al al-Zahir" ·
taslim → "Taslim" twice, but also "chasm" and "Tasselman"

Recognisable, and a listener would follow them. Whether that is good enough is a
judgement about this edition, not something a transcript decides, so none of
them were written to the ledger either way.

---

## Run 1 (2026-08-01, Shorter length) — superseded

- **Audio:** `m4a/How_medieval_Arabic_words_defined_cosmic_order.m4a` (5:06)

The source phrased every item as a stage direction — "1. Next, say
**wa-LAA-ya** — as in: …" — so NotebookLM conversationalised the instructions and
produced a themed discussion naming **9 of 39 terms**. Shorter compounded it at
seven seconds a term. Both were fixed for run 2: the source became a glossary,
and the length guidance became Default.

Its nine terms are the respelling column of the comparison table above.
