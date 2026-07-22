# Articulation-recovery punchlist — the-master-and-the-disciple

Extracted 2026-07-22 (RCA-001). Each item is a human/editorial change that was
applied on top of the FROZEN (pre-articulation) chapter bodies and must
survive the re-articulation. Column "How it comes back" says whether a
deterministic pipeline pass restores it on its own or it must be re-applied /
re-verified by hand against the new prose.

| Chapter | Change | How it comes back |
|---|---|---|
| Three Layers of Knowledge | **Green ears are "causes", NOT al-Khidr** (doctrinal fix, challenger-confirmed) | **RE-APPLY BY HAND — exists nowhere else; the base chunk still carries the error** |
| Three Layers of Knowledge | hawl gains Arabic script gloss; (ع) spelled out | inline-arabic pass + honorifics pass |
| How to Read a Conversation... (preface) | Salih glossed 'the righteous'; Shaykh/Abu Malik gloss placement; term-list style (al-Imam al-Natiq, bab, wasi, duat); "abridgement"→"abridgment"; stray "(الله)" after Allah removed | glossary/annotation-policy + spelling pass; **verify placement by hand** |
| The Persian Who Was Dead and Revived | "scholars of the Mount (Tur, الطور)" + "Frequented House (Bayt al-Mamur, البيت المعمور)" glosses (Asif-approved wording — NOT "House of Light"); comma style; stray "slide-N" lines removed | glossary carries the terms; **verify approved English wording by hand** |
| Homecoming, the Father... | "Kab al-Ahbar" spelling + quote placement; Abu Salih ('father of Salih') and Abu al-Khair ('father of the good') name glosses | **RE-APPLY BY HAND (name-gloss composer edits)** |
| The Five Shares... | Reader bridge (three senses of "father"); Ubayd Allah / Abd Allah name-riddle glosses | bridge: comprehension-bridges sidecar (auto); **name glosses by hand** |
| The World, the Hereafter... | Annotation-policy styling: nuqaba/tawil/hujaj carry script; duat/bab/wasi italic-only | glossary/annotation-policy pass; verify |
| The Boy at the Door... | "Party of God (*Hizb Allah*)" italic transliteration form | annotation-policy pass; verify |
| A Stranger in the City | (no delta — frozen body was untouched) | n/a |

Full diffs: `delta-*.diff` in this directory (baseline = the 2026-07-20
snapshots as replayed by commit 748c126). Stale sidecar archived as
`composer-edits-stale-2026-07-22.json`.

## Recovery sequence

1. Archive + clear `_system/composer-edits.json` (done in the same commit as
   this file).
2. `compose_book_v2` — base rebuilt from integrity-gated chunk cache,
   articulation pass re-voices all 9 chapters, deterministic tail passes
   (translit, annotation policy, inline Arabic, spelling, introduction,
   bridges, honorifics) re-run.
3. Re-apply the BY-HAND rows above onto the articulated prose; save through
   the Composer path so fresh durable edits protect ARTICULATED text.
4. book-challenger convergence; verify every row of this table; update
   RCA-001 action items.
