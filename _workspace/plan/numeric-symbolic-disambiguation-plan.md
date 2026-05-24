# Numeric / Symbolic Disambiguation — Plan for All Future Podcast Work

> **Canonical home (since v3 of the plan, 2026-05-19):** this work is now folded into `_workspace/plan/podcast-plan.yaml` as **Phase P4** (Wave 1). This document remains the authoritative design reference; execution traceability lives in [`acceptance-criteria.md`](./acceptance-criteria.md) rows **P4.1 – P4.8**, and the visual summary is in [`view/index.html`](./view/index.html) §8.
>
> When you change anything in this document, also update P4 in `podcast-plan.yaml` and the P4.x rows in `acceptance-criteria.md`. Pass 5 L10 will flag drift.

**Status:** PLAN ONLY. Not executed. Awaits explicit go-ahead per file.
**Date:** 2026-05-19 (created); folded into canonical plan as P4 on 2026-05-19.
**Concrete example used throughout:** *The Master and the Disciple* / *Kitāb al-ʿĀlim wa'l-Ghulām*, Chapter 2 — Oath and Cosmic Origins (`content/drafts/the-master-and-the-disciple/Ch-02-Oath and Cosmic Origins - Refined.md` and the iCloud original at `~/Library/Mobile Documents/com~apple~CloudDocs/Books/Kitaab_Al-aalim_wal_Ghulam_Chapters/Ch-02-Oath and Cosmic Origins.txt`).

---

## 0. Why this plan exists

Classical Islamic / Ismaili source material is saturated with **symbolic numeric structures** — 7 heavens, 7 earths, 7 principles, 12 mansions, 12 regions, 7 seas, 12 hujjas, the 28 Arabic letters, abjad-encoded passages, the "seven oft-repeated," the "five intermediaries," and so on. NotebookLM and the current podcast pipeline handle these poorly in three predictable ways:

1. **It asserts the number without enumerating the items.** "There are twelve regions" — but the chapter never says which twelve. Listener leaves with a count, not content.
2. **It modernizes anachronistically.** "Seven earths" gets glossed as "seven continents (Asia, Africa, N-America, S-America, Antarctica, Europe, Australia)" — a list that could not have existed when the text was written.
3. **It leaves abjad-encoded cipher sequences untranslated.** `(ب ج لا د م لہ م)` appears in the text as a coded reference to seven spheres; nothing in the pipeline knows what to do with it.

The pipeline needs a **systematic protocol** to detect, research, and disambiguate these — once per book, per number — without inventing content. This plan defines that protocol, uses Ch-02 of *The Master and the Disciple* as the worked example, and lists every file that would change.

---

## 1. The Ch-02 ambiguity register (LIVE audit — the concrete example)

These are the actual ambiguities found in the iCloud source of Ch-02. Each row is the kind of finding the proposed pipeline check would flag automatically.

### 1.1 Numeric structures asserted but not enumerated

| # | Claim in chapter | Status | Authoritative answer | Source |
|---|---|---|---|---|
| A1 | **12 regions on earth** (outward sign of the 12 Hujjahs of each Imam, "one hujja assigned to each region") | RESOLVED | Fatimid Ismaili enumeration of the world into **twelve jazāʾir** ("islands"): al-ʿArab, al-Rūm, al-Ṣaqāliba, al-Nūba, al-Khazar, al-Hind, al-Sind, al-Zanj, al-Ḥabash, al-Ṣīn, al-Daylam (sometimes paired with Khurāsān), al-Barbar. Each headed by a chief dāʿī bearing the title **ḥujja**. | Encyclopedia Iranica §"Dāʿī"; al-Naysabūrī; Ibn Ḥawqal; Nāṣir-i Khusraw's own writings (he held the jazīra of Khurāsān). |
| A2 | **7 seas** as "intermediaries between Allah and the Imams following the Natiq" | RESOLVED — with framing caveat | The classical Arab-geographic Seven Seas per **9th-century Yaʿqūbī** (period-contemporary with Ja'far): Sea of Fars (Persian Gulf), Sea of Larwi (Arabian Sea), Sea of Harkand (Bay of Bengal), Sea of Kalāh-bār (Strait of Malacca), Sea of Ṣalāhiṭ (Singapore Strait), Sea of Kardanj (Gulf of Thailand / lower South China Sea), Sea of Ṣanjī (South China Sea). | Wikipedia "Seven Seas" §"Medieval Arab geographers"; Yaʿqūbī. Reframe required: the host says "the seven seas of classical Arab geography known at the time the book was written." Do NOT substitute the Greek list (Aegean, Adriatic, Mediterranean, Black, Red, Caspian, Persian) — that is not the Ismaili reference frame. |
| A3 | **Cryptic letter sequence `(ب ج لا د م لہ م)`** — described as the seven heavenly spheres | **UNRESOLVED — flag for human review** | Seven items, matching the 7 spheres. Three candidate interpretations (none verified): (i) abjad-encoded initials of seven Cherubim / karūbiyya per classical Ismaili cosmogony; (ii) OCR / transcription artifact garbling an original sequence; (iii) abbreviated planet names. **Decision per user (2026-05-19): flag for human/editorial review; do NOT decode; host signals "the text encodes the seven spheres in a letter-sequence that requires the tradition's specialist commentary to fully decode."** | Encyclopedia Iranica §"Cosmogony vi. In Ismāʿīlism" references seven karūbiyya with esoteric names but does not enumerate them. Critical edition (James W. Morris, I.B. Tauris) must be consulted. |
| A4 | **12 Naqibs** (chiefs of each Natiq) | RESOLVED | Two valid framings: (1) historical — the 12 men (10 Khazraj + 2 Aws) of the Second Pledge of Aqaba (621 CE) chosen by the Prophet Muhammad; (2) cosmological / symbolic — 12 men assisting each Naṭiq, mirroring the 12 mansions of the Zodiac. Ja'far's text uses sense (2). The Aqaba 12 is the exemplar of the type for Muhammad's cycle. | wikishia §"Pledge of al-Aqaba"; Bukhari (Merits of the Helpers in Madinah); Ismaili cosmological literature. |
| A5 | **12 Hujjahs** of each Imam | RESOLVED (structural; not exhaustively named) | For each Imam, twelve visible diurnal ḥujjas and twelve concealed nocturnal ḥujjas; each ḥujja heads one jazīra. The Iranica article quotes Dāʿī Abū ʿAbdallāh al-Shīʿī directly. Specific names of the 12 ḥujjas for any given Imam are tradition-internal and not always public. | Encyclopedia Iranica §"Cosmogony vi"; ismailignosis.com guardians-of-esoteric-knowledge series. |
| A6 | **"The seven oft-repeated"** (السبع المثاني) — Monday's symbol | RESOLVED | Refers to **Sūrat al-Fātiḥah** (its 7 verses), recited in every unit of prayer. Confirmed across majority Sunni and Shia tafsīr (al-Baghawī, al-Shinqīṭī, Majlisī's *Ḥayāt al-Qulūb* vol. 3 part 27). | Multiple tafsīr; quran.com Surah al-Fātiḥah tafsirs. |
| A7 | **"The fifth of God's intermediaries"** — Thursday's symbol | **UNRESOLVED — flag for human review** | Probable inference: the fifth rank in the Ismaili da'wa hierarchy (Nāṭiq, Asāas/Wasi, Imām, Ḥujja, **Dāʿī**) = the Dāʿī. The chapter itself names the same five-rank structure, so this reading is internally consistent — but it must be verified against the Morris critical edition before locking. | Iranica §"Cosmogony vi" confirms the five-rank hierarchy. Verification needed against the printed edition. |
| A8 | **The Asāas of the Natiq** — referenced for "his lifetime" then "designated Wasi after his death" | RESOLVED | Each Natiq (cycle-prophet) has an Asāas (foundation) who becomes the Wasi after the Natiq's death. For Muhammad's cycle: **Asāas = Imam Ali, peace be upon him**. Implicit in the chapter; explicit in Ismaili foundational doctrine. | Iranica §"Cosmogony vi"; Ismaili catechetical literature. |

### 1.2 Anachronism flags (already present in the iCloud source)

| # | Claim | Issue | Proposed handling |
|---|---|---|---|
| A9 | "**seven continents (Asia, Africa, N-America, S-America, Antarctica, Europe, Australia)**" | Anachronistic — the Americas and Antarctica were unknown to the period. The classical equivalent is **al-aqālīm al-sabʿa** (the seven climes / Ptolemaic latitudinal bands) per Suhrāb's *ʿAjāʾib al-aqālīm al-sabʿah* (902–945 CE) and the Ikhwān al-Ṣafāʾ Epistle 4 ("On Geography"). | Scaffolding records both: the original-period referent (seven climes) and the modernization. Host names which they are using and labels it accordingly. |
| A10 | "**seven heavens (Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon)**" | This is the **classical Ptolemaic luminaries** model — period-appropriate. Order in the chapter is non-standard. | Mark as period-appropriate; flag the non-standard order for verification against the Morris edition. |

### 1.3 Validated numeric claims (no action needed)

| # | Claim | Verification |
|---|---|---|
| A11 | "7 letters" of `kun fayakun` (كن فيكون) — 2 + 5 = 7 | ✓ Validated: ك+ن = 2 letters; ف+ي+ك+و+ن = 5 letters. |
| A12 | "12 letters" of `iradah amr bi-qawl` (ارادۃ أمر بقول) | ✓ Validated: 5 + 3 + 4 = 12 letters. |
| A13 | "7 days × 12 hours each = 168 hours/week" | ✓ Validated. |

---

## 2. The Abjad numerals synthesis (added per user request 2026-05-19)

The full **Eastern (Mashriqi) Abjad** table — the variant the chapter uses. Mnemonic phrases: أَبْجَدْ هَوَّزْ حُطِّيْ كَلِمَنْ سَعْفَصْ قَرَشَتْ ثَخَذْ ضَظَغْ.

### 2.1 Complete Mashriqi table

| Letter | Name | Value | Letter | Name | Value | Letter | Name | Value |
|---|---|---:|---|---|---:|---|---|---:|
| ا | ʾalif | **1** | ي | yāʾ | **10** | ق | qāf | **100** |
| ب | bāʾ | **2** | ك | kāf | **20** | ر | rāʾ | **200** |
| ج | jīm | **3** | ل | lām | **30** | ش | shīn | **300** |
| د | dāl | **4** | م | mīm | **40** | ت | tāʾ | **400** |
| ه | hāʾ | **5** | ن | nūn | **50** | ث | thāʾ | **500** |
| و | wāw | **6** | س | sīn | **60** | خ | khāʾ | **600** |
| ز | zāy | **7** | ع | ʿayn | **70** | ذ | dhāl | **700** |
| ح | ḥāʾ | **8** | ف | fāʾ | **80** | ض | ḍād | **800** |
| ط | ṭāʾ | **9** | ص | ṣād | **90** | ظ | ẓāʾ | **900** |
| | | | | | | غ | ghayn | **1000** |

**Hisab al-Jummal** (حساب الجُمَّل, "calculation of total"): sum letter-by-letter. ة (tāʾ marbūṭa) typically counts as ه = 5.

### 2.2 Reference calculations

| Phrase | Calculation | Sum |
|---|---|---:|
| الله (Allāh) | 1+30+30+5 | **66** |
| بسم الله الرحمن الرحيم (basmala) | (per Wikipedia) | **786** |
| محمد (Muḥammad) | 40+8+40+4 | **92** |
| علي (ʿAlī) | 70+30+10 | **110** |

### 2.3 Calculations relevant to Ch-02

| Phrase | Letter-by-letter | Sum | Use in chapter |
|---|---|---:|---|
| كن (kun) | 20+50 | **70** | "Be!" — the divine command |
| فيكون (fa-yakun) | 80+10+20+6+50 | **166** | "so it came to be" |
| كن فيكون | 70+166 | **236** | The two-word creative utterance |
| الإرادة (will) | 1+30+1+200+1+4+5 | **242** | First creative word |
| الأمر (command) | 1+30+1+40+200 | **272** | Second |
| القول (speech) | 1+30+100+6+30 | **167** | Third |
| Sum of the triad | 242+272+167 | **681** | The triadic creative principle |

*Note:* These are Abjad **values**. The chapter's "7 letters" and "12 letters" claims refer to letter **counts**, which are different — both have been verified separately in §1.3.

---

## 3. Phase 2 plan — Per-book scaffolding fills (the worked example)

These are the **specific changes** that would be made to *The Master and the Disciple* scaffolding to resolve the Ch-02 ambiguity register. Each change is concrete, file-scoped, and would be made in a single commit if approved.

### 3.1 UPDATE `_notebooklm/02-glossary.md`

Add these entries (insertion-ordered alphabetically with existing entries; show only the new content here):

```md
### The Twelve Jazāʾir (al-jazāʾir al-ithnāʿashar)
- Plain-English meaning: The twelve "islands" or regions into which the
  classical Fatimid Ismaili da'wa divided the inhabited world. Each region
  was headed by a chief dā'ī bearing the title ḥujja. In the symbolic
  cosmology of Ch 2, the twelve regions on earth point to the twelve hujjas
  who assist each Imam.
- Why it matters in this series: The chapter asserts "twelve regions" but
  does not enumerate them. The historically attested enumeration is:
  al-ʿArab, al-Rūm, al-Ṣaqāliba, al-Nūba, al-Khazar, al-Hind, al-Sind,
  al-Zanj, al-Ḥabash, al-Ṣīn, al-Daylam, al-Barbar. (Sources: Iranica
  §"Dāʿī"; Ibn Ḥawqal; Nāṣir-i Khusraw on Khurāsān as a jazīra.)
- Host enumeration policy: deliver the list ONCE, in Episode 2.
  Do not repeat in later episodes.

### The Seven Seas (al-biḥār al-sabʿa) — Yaʿqūbī enumeration
- Plain-English meaning: The seven maritime regions known to 9th-century
  Arab geographers — period-contemporary with Ja'far ibn Mansūr al-Yaman.
- Why it matters in this series: Ch 2 calls the seven seas "intermediaries
  between Allah and the Imams following the Natiq." The Yaʿqūbī list:
  Sea of Fars (Persian Gulf), Sea of Larwi (Arabian Sea), Sea of Harkand
  (Bay of Bengal), Sea of Kalāh-bār (Strait of Malacca), Sea of Ṣalāhiṭ
  (Singapore Strait), Sea of Kardanj (Gulf of Thailand / lower South
  China Sea), Sea of Ṣanjī (South China Sea).
- Host framing: "the seven seas of classical Arab geography known at the
  time the book was written." Do NOT substitute the Greek/Mediterranean
  list (Aegean, Adriatic, etc.) — that is not the Ismaili reference frame.
- Host enumeration policy: deliver the list ONCE, in Episode 2.

### The Seven Oft-Repeated (al-sabʿ al-mathānī)
- Plain-English meaning: Sūrat al-Fātiḥah — the seven-verse opening surah
  of the Qurʾān, recited in every unit of prayer. The chapter assigns it
  as Monday's symbol.
- Why it matters: Ch 2 names "the seven doubled ones" as Monday's symbol
  without identifying it. Without this fill, listeners hear an opaque
  reference. The cross-tradition consensus (Sunni and Shia tafsīr) is
  al-Fātiḥah.

### The Asāas
- Plain-English meaning: "Foundation" — in Ismaili tradition, the figure
  who functions as the Naṭiq's living interpreter during his lifetime and
  becomes the Wasi (trustee) after his death.
- Why it matters: Ch 2 references the Asāas without naming whose Asāas.
  For Muhammad's cycle, the Asāas is Imam Ali, peace be upon him.
  Implicit in the chapter; explicit in foundational doctrine.

### Hisab al-Jummal (Abjad numerals)
- Plain-English meaning: The traditional Arabic-letter numerology system
  in which each letter has a numerical value. See
  `content/_shared/arabic/06-abjad-numerals.md` for the full table.
- Why it matters: Ch 2 contains explicit letter-count claims (the 7
  letters of "kun fayakun"; the 12 letters of "iradah amr bi-qawl") and
  one cryptic abjad-encoded sphere sequence (B3). The reader / host needs
  the Abjad table to verify the claims and to handle the cipher.
```

### 3.2 UPDATE `_notebooklm/03-source-integrity-notes.md`

Add a new top-level section after the existing "Transliteration consistency":

```md
## Numeric / symbolic enumeration register

Every numeric or symbolic claim in the chapter set that asserts a count
without enumerating its members. Each item is classified by resolution
status and given a podcast-handling instruction.

| Item | Chapter | Status | Authoritative source | Podcast instruction |
|---|---|---|---|---|
| 12 jazāʾir / regions | Ch 2 | RESOLVED | Iranica §"Dāʿī" + Ibn Ḥawqal + Nāṣir-i Khusraw | Enumerate ONCE in Ep 2 using glossary list. Do not repeat. |
| 7 seas | Ch 2 | RESOLVED (framing caveat) | Yaʿqūbī (9th c.) per Wikipedia "Seven Seas" §"Medieval Arab geographers" | Enumerate ONCE in Ep 2 with framing "the seven seas of classical Arab geography known at the time the book was written." |
| Cryptic letter sequence (ب ج لا د م لہ م) | Ch 2 | NEEDS HUMAN REVIEW | Iranica §"Cosmogony vi" mentions seven karūbiyya without enumerating; Morris critical edition must be consulted | Host signals: "the text encodes the seven spheres in a letter-sequence that requires the tradition's specialist commentary to fully decode." Do not invent a decoding. |
| 12 Naqibs | Ch 2 | RESOLVED (two framings) | wikishia §"Pledge of al-Aqaba"; Bukhari | Sense (1): historical Aqaba 12 — exemplar for Muhammad's cycle. Sense (2): cosmological 12 per Naṭiq. Use sense (2) for Ch 2's symbolic register; mention sense (1) once as the Muhammad-cycle exemplar. |
| 12 Hujjahs of each Imam | Ch 2, Ch 6 | RESOLVED (structural) | Iranica §"Cosmogony vi"; Dā'ī Abū ʿAbdallāh al-Shīʿī | Frame as a tradition-internal structure: "for each Imam there are twelve diurnal and twelve nocturnal ḥujjas." Do not name them. |
| The seven oft-repeated (al-sabʿ al-mathānī) | Ch 2 | RESOLVED | Cross-tradition tafsīr consensus | Identify as Sūrat al-Fātiḥah on first mention. |
| The fifth intermediary | Ch 2 | NEEDS HUMAN REVIEW | Iranica §"Cosmogony vi" confirms the five-rank hierarchy | Probable reading: Thursday's symbol = the Dāʿī rank. Verify against Morris edition before locking. |
| The Asāas (cycle-specific) | Ch 2 | RESOLVED | Foundational Ismaili doctrine | For Muhammad's cycle: Asāas = Ali, peace be upon him. Make explicit on first mention. |

## Anachronism register

| Claim | Chapter | Issue | Podcast instruction |
|---|---|---|---|
| "seven continents (Asia, Africa, N-America, S-America, Antarctica, Europe, Australia)" | Ch 2 | Anachronistic — period referent is al-aqālīm al-sabʿa (seven climes / Ptolemaic latitudinal bands) | Host labels both: "the modern reader thinks of seven continents; the period text refers to the seven climes — the Greek-Ptolemaic latitudinal bands also used by the Ikhwān al-Ṣafāʾ." |
| "seven heavens (Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon)" | Ch 2 | Period-appropriate (classical Ptolemaic luminaries) but non-standard order | Use as given; flag the order for verification against the Morris edition. |
```

### 3.3 UPDATE `_notebooklm/ch02-scaffolding.md`

Insert a new section **"Numeric Disambiguation"** between the existing **Podcast Segment Map** and **Recurring Refrain for Host**, and add a corresponding NotebookLM Instruction at the end of the existing block:

```md
## Numeric Disambiguation (per `03-source-integrity-notes.md`)

This chapter contains seven numeric / symbolic structures the listener
will hear. The host enumerates each ONCE, here, then refers back to the
ideas without repeating the lists.

### The 12 jazāʾir (regions of the earth, sign of the 12 ḥujjas)
**Symbolic meaning first:** the number twelve points to the twelve
mansions of the Zodiac — the heavenly correspondence to the earthly
twelve. Each Imam's twelve ḥujjas symbolically dwell in twelve regions.

**Historical enumeration** (Fatimid-period attestation, ONE-TIME only):
al-ʿArab, al-Rūm, al-Ṣaqāliba, al-Nūba, al-Khazar, al-Hind, al-Sind,
al-Zanj, al-Ḥabash, al-Ṣīn, al-Daylam, al-Barbar — each headed by a
chief dāʿī bearing the title ḥujja. (Per user decision 2026-05-19:
"Both — symbolic + historical" framing.)

### The 7 seas
**Symbolic meaning first:** in the chapter the seven seas are
"intermediaries between Allah and the Imams following the Natiq." The
seven correspondingly points to the seven principles of creation
established earlier in the chapter.

**Historical enumeration (Yaʿqūbī, 9th c.):** Sea of Fars, Sea of Larwi,
Sea of Harkand, Sea of Kalāh-bār, Sea of Ṣalāhiṭ, Sea of Kardanj,
Sea of Ṣanjī. Frame as "the seven seas of classical Arab geography
known at the time the book was written."

### The 7 heavenly spheres (ب ج لا د م لہ م)
**NEEDS HUMAN REVIEW.** The text encodes the seven spheres in a
letter-sequence that requires the tradition's specialist commentary to
fully decode. Host signal: "the text gestures here at a coded sequence
of seven letters; the full decoding requires the tradition's specialist
commentary." Do NOT invent a reading.

### The 12 Naqibs (chiefs of each Naṭiq)
**Symbolic:** twelve assistants per Naṭiq, mirroring the twelve mansions.
**For Muhammad's cycle:** the historical exemplar is the twelve men
(ten from the Khazraj, two from the Aws) who took the Second Pledge of
al-ʿAqaba in 621 CE. Mention once as the period instance.

### The Asāas (cycle-specific)
For Muhammad's cycle, the Asāas is **Imam Ali, peace be upon him**, who
becomes the Wasi (trustee) after the Naṭiq's death. The chapter implies
this; make it explicit on first mention.

### The seven oft-repeated (al-sabʿ al-mathānī, Monday's symbol)
**= Sūrat al-Fātiḥah**, the seven-verse opening surah recited in every
unit of prayer.

### The fifth intermediary (Thursday's symbol)
**NEEDS HUMAN REVIEW.** Probable reading: the fifth rank in the da'wa
hierarchy (Nāṭiq → Asāas → Imām → Ḥujja → Dāʿī) — i.e., the Dāʿī rank.
Verify against the Morris critical edition before locking.
```

And **append** this to the existing **NotebookLM Instruction** block:

```md
- **One-time enumeration rule.** In this episode (and ONLY in this
  episode), enumerate the 12 jazāʾir, the 7 seas, and the 12 Naqibs once
  each, using the per-item lists in the Numeric Disambiguation block
  above. Do NOT enumerate these lists again in any later episode — refer
  to them as concepts only.
- **Coded sphere-letters.** The sequence `(ب ج لا د م لہ م)` is flagged
  for human review. Do not decode it. Host says: "the text gestures
  here at a coded sequence of seven letters; the full decoding requires
  the tradition's specialist commentary."
- **Anachronism handling.** When the source text says "seven continents,"
  the host adds a one-sentence period frame: "the original tradition
  framed this as the seven climes — the Greek-Ptolemaic latitudinal
  bands." Do not pretend the modern continents list is the period text.
- **Abjad reference.** When the chapter cites letter counts (the 7
  letters of `kun fayakun`, the 12 letters of `iradah amr bi-qawl`), the
  host may briefly note "in the Abjad system these letters also carry
  numerical values" but does NOT perform the calculation aloud unless
  asked. The full Abjad table lives at
  `content/_shared/arabic/06-abjad-numerals.md`.
```

### 3.4 UPDATE `_notebooklm/06-human-review-checklist.md`

Add new section after **§I NotebookLM-specific cleanup**:

```md
## J. Numeric / Symbolic Enumeration Review

- [ ] The 12 jazāʾir were enumerated ONCE in Episode 2, using the
      historically-attested Fatimid list. Not repeated in any later episode.
- [ ] The 7 seas were enumerated ONCE in Episode 2, using the Yaʿqūbī
      9th-century list, with the framing "the seven seas of classical
      Arab geography known at the time the book was written." Not
      repeated.
- [ ] The 12 Naqibs received the symbolic + historical-exemplar (Aqaba
      Pledge) framing ONCE in Episode 2. Not repeated.
- [ ] The Asāas was identified explicitly for Muhammad's cycle (Ali,
      peace be upon him) on first mention in Episode 2.
- [ ] The seven oft-repeated (al-sabʿ al-mathānī) was identified as
      Sūrat al-Fātiḥah on first mention.
- [ ] The cryptic letter sequence (ب ج لا د م لہ م) was flagged on-air
      as needing tradition-specialist commentary; NOT decoded with an
      invented reading.
- [ ] The fifth intermediary reading (Thursday) was either confirmed
      against the Morris critical edition or explicitly flagged for the
      listener as "the text leaves this open; the most consistent reading
      with the chapter's own hierarchy is the Dāʿī rank, but verification
      is pending."
- [ ] No anachronistic gloss (e.g., modern continents, modern political
      regions) was delivered without the period-text reframe alongside it.
- [ ] Any Abjad letter-count or value claim in the chapter was either
      verified against `content/_shared/arabic/06-abjad-numerals.md` or
      flagged for human review.

**Failure-mode escalation for §J:**
- **P0 (BLOCKED):** any *invented* enumeration (e.g., host guesses at the
  decoded seven-letter sphere sequence and presents a reading).
- **P1 (SHIP-WITH-CAUTION):** enumeration repeated across episodes
  (anti-repetition violation); period-vs-modern reframe missing.
- **P2 (note for next episode):** "the fifth intermediary" or other
  marked items still awaiting Morris-edition verification.
```

---

## 4. Phase 3 plan — Pipeline fixes (the recurring protocol)

These changes generalize the Ch-02 worked example into a **standing protocol** for every future book. The user's intent: "use this as a concrete example for all future work."

### 4.1 CREATE `content/_shared/arabic/06-abjad-numerals.md`

Cross-skill canonical Abjad numerals reference. Mirrors the structure of the existing 01–05 shared files. Contents:

1. Full Mashriqi (Eastern) and Maghribi (Western) variants of the Abjad table.
2. Hisab al-Jummal practice — how to sum, how ة and final letters are counted.
3. Worked examples (the §2 table above, plus a half-dozen common phrases).
4. **When to use it in the pipeline:** any chapter that cites letter-counts; any abjad-encoded passage; any numerological claim requiring verification.
5. **Lookup behavior:** any new term added to a book's pronunciation guide that includes a letter-count or numeric claim is verified against this table before publication.

Mandatory pre-read addition: SKILL.md's pre-read list extends to seven SHARED_ARABIC files (00 through 06 — currently 00 through 05).

### 4.2 CREATE `content/podcast/.skill/handbook/numeric-symbolic-disambiguation.md`

General protocol for **any** book containing symbolic / numeric structures. Outline:

```md
# Numeric / Symbolic Disambiguation Protocol

## 1. When this protocol activates
Any chapter that asserts a count without enumerating its members
("twelve X," "seven Y"); any chapter containing a cipher / abjad-encoded
sequence; any chapter applying a modern gloss (continents, planets,
political regions) to a pre-modern text.

## 2. Workflow per ambiguity
1. **Identify** — flag the claim with the ambiguity register format
   (item / chapter / claim text / candidate resolution).
2. **Research** — consult authoritative sources in this preference order:
   - Critical editions (e.g., IIS Shi'i Heritage Series, I.B. Tauris)
   - Encyclopedia Iranica / IIS publications / Brill journals
   - Peer-reviewed academic (Cambridge, Brill, university presses)
   - General reference (Wikipedia, Encyclopaedia of Islam)
   - General web (lowest weight; only for cross-checking)
3. **Record** in the book's `_notebooklm/03-source-integrity-notes.md`
   numeric/symbolic enumeration register, with: status (RESOLVED /
   NEEDS HUMAN REVIEW), source, podcast instruction.
4. **Add to the per-chapter scaffolding** a "Numeric Disambiguation"
   block containing the symbolic meaning + (if resolved) the period-
   attested enumeration, with explicit ONE-TIME enumeration policy.
5. **Add to the human-review checklist** a §J row per claim.

## 3. The "enumerate once" rule
NotebookLM tends to repeat memorable lists across episodes. To prevent
this anti-pattern, every enumeration is delivered in ONE episode (the
chapter where it first appears), referenced in later episodes only as a
concept. The challenger Loop N enforces this (see §4.4).

## 4. Anachronism handling
When a translated source modernizes a period referent (e.g., "seven
continents" for "seven climes"), the scaffolding records BOTH the
period referent and the modernization. The host names which they are
using on-air. Failure to label is a P1 finding.

## 5. Invented content is P0
If the scaffolding asserts an enumeration that cannot be sourced, that
is a P0 BLOCKED finding regardless of how plausible the guess is. The
correct handling is: flag for human review, signal to the listener
that the item requires tradition-specialist commentary, do not invent.

## 6. Authoritative-source register
Maintained per-book in `_notebooklm/03-source-integrity-notes.md`.
Every resolved item carries its source citation. Every NEEDS HUMAN
REVIEW item carries (a) which critical edition or specialist should be
consulted, (b) the candidate interpretations the researcher considered
but did not commit to.
```

### 4.3 EXTEND `content/podcast/.skill/handbook/pre-refined-source-mode.md`

Add a new required step in the per-chapter scaffolding skeleton:

```md
## Numeric Disambiguation        # required when the chapter contains any numeric/symbolic structure
- Per-claim symbolic meaning + period-attested enumeration (if resolved)
- ONE-TIME enumeration policy
- Cross-reference to `03-source-integrity-notes.md` numeric register
- Cross-reference to `content/_shared/arabic/06-abjad-numerals.md` for
  any letter-count or value claim
```

Plus a new failure-mode in the §"Failure modes to avoid" list:

```md
6. **Asserting an invented enumeration.** If a chapter says "twelve X"
   without enumerating, and you cannot find the period-attested list,
   the correct handling is to flag for human review — never to invent
   the list. Invented enumerations are P0 BLOCKED findings in the
   challenger.
```

### 4.4 EXTEND the podcast-challenger spec — new **LOOP N: Numeric/Symbolic Disambiguation**

Added to `.github/agents/podcast-challenger.agent.md` (and mirrored in `.claude/agents/podcast-challenger.md`). The loop checks:

1. **Enumeration coverage:** every numeric claim ("N X") in the chapter has either (a) an enumeration in the per-chapter scaffolding's Numeric Disambiguation block, or (b) an explicit NEEDS HUMAN REVIEW flag in `03-source-integrity-notes.md`.
2. **One-time enumeration:** no enumeration is repeated across episodes. The challenger scans all per-chapter scaffolding files; if the same enumeration appears in more than one Numeric Disambiguation block, it flags P1.
3. **Abjad cipher coverage:** any abjad-encoded sequence in the chapter has either a decoded interpretation with source citation, or a NEEDS HUMAN REVIEW flag.
4. **Anachronism labeling:** any anachronistic gloss in the chapter has both the original-period referent and the modernization labeled in the scaffolding, with an explicit host-instruction to label on-air.
5. **No invented content:** any enumeration in the scaffolding lacking a source citation is flagged P0.

**Severity ladder:**
- **P0 (BLOCKED):** invented enumeration without source; abjad cipher decoded with an unsourced guess.
- **P1 (SHIP-WITH-CAUTION):** enumeration repeated across episodes; anachronism unlabeled.
- **P2 (note for next episode):** NEEDS HUMAN REVIEW items still pending after publication.

### 4.5 EXTEND `skills-staging/podcast/SKILL.md`

Add reference #21 in the pre-read list:

```md
21. `PODCAST_ROOT/.skill/handbook/numeric-symbolic-disambiguation.md` —
    protocol for handling symbolic / numeric structures in classical
    Islamic / Ismaili source material. Required when any chapter asserts
    a count without enumerating its members, contains an abjad-encoded
    cipher, or applies a modern gloss to a pre-modern referent. Defines
    the workflow, the authoritative-source preference order, the
    one-time enumeration rule, and the anachronism labeling protocol.
    Canonical worked example: Ch-02 of *The Master and the Disciple*.
```

And extend the SHARED_ARABIC mandatory pre-read paragraph to include `06-abjad-numerals.md`.

### 4.6 EXTEND the orchestrator's Phase 0d (chapter design) checklist

In `scripts/podcast/_authoring.py`'s Phase 0d prompt (and corresponding handbook entry), add a step:

> **Numeric / symbolic structure scan.** After chapter boundaries are determined, scan each chapter for: (a) numeric claims ("N X") without enumeration, (b) abjad-encoded sequences, (c) anachronistic glosses. Each finding is recorded in `_system/source/text/numeric-disambiguation-register.md` for downstream resolution per the protocol in `content/podcast/.skill/handbook/numeric-symbolic-disambiguation.md`.

This is the **detection** step. Resolution happens in Phase 3 (framing) and at the per-chapter scaffolding layer. The orchestrator only flags; it does not invent.

---

## 5. Files that would change (full manifest, for review)

If the plan is approved for execution:

**UPDATE (Phase 2 — book-specific):**
- `content/drafts/the-master-and-the-disciple/_notebooklm/02-glossary.md`
- `content/drafts/the-master-and-the-disciple/_notebooklm/03-source-integrity-notes.md`
- `content/drafts/the-master-and-the-disciple/_notebooklm/ch02-scaffolding.md`
- `content/drafts/the-master-and-the-disciple/_notebooklm/06-human-review-checklist.md`

**CREATE (Phase 2 — shared):**
- `content/_shared/arabic/06-abjad-numerals.md`

**CREATE (Phase 3 — handbook):**
- `content/podcast/.skill/handbook/numeric-symbolic-disambiguation.md`

**UPDATE (Phase 3 — pipeline wiring):**
- `content/podcast/.skill/handbook/pre-refined-source-mode.md`
- `skills-staging/podcast/SKILL.md`
- `.github/agents/podcast-challenger.agent.md`
- `.claude/agents/podcast-challenger.md`
- `scripts/podcast/_authoring.py` (Phase 0d numeric-scan step)

**Total:** 10 files (5 update + 5 create) across one commit.

---

## 6. Open questions awaiting human decision

These are items the plan cannot resolve on its own:

1. **The cryptic letter sequence `(ب ج لا د م لہ م)`** — consult the James W. Morris critical edition (I.B. Tauris). Three candidate interpretations are on file; the Morris edition may resolve it directly or via a footnote.
2. **The fifth intermediary (Thursday)** — same: confirm against Morris edition that the reading "Thursday = Dāʿī rank" is correct.
3. **The non-standard order of the seven luminaries** (Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon) — confirm against Morris edition whether the order in the iCloud source matches the Arabic original or is a translator's choice.
4. **The seven continents anachronism** — confirm with the user / translator whether the modernization was intentional editorial accommodation or an OCR/translation drift. If intentional, the scaffolding labels it as a deliberate modernization; if drift, the scaffolding restores the period referent (al-aqālīm al-sabʿa).

---

## 7. Sources cited

- [Abjad numerals — Wikipedia](https://en.wikipedia.org/wiki/Abjad_numerals)
- [Seven Seas — Wikipedia §"Medieval Arab geographers"](https://en.wikipedia.org/wiki/Seven_Seas)
- [Encyclopaedia Iranica — Dā'ī (Propagandists)](https://www.iranicaonline.org/articles/dai-propagandists/)
- [Encyclopaedia Iranica — Cosmogony vi. In Ismā'īlism](https://www.iranicaonline.org/articles/cosmogony-vi/)
- [The Institute of Ismaili Studies — Nasir Khusraw](https://www.iis.ac.uk/scholarly-contributions/nasir-khusraw/)
- [The Institute of Ismaili Studies — On Geography (Ikhwān al-Ṣafāʾ Epistle 4)](https://www.iis.ac.uk/publications-listing/on-geography/)
- [Encyclopaedia Iranica — Aḥsan al-Taqāsīm](https://www.iranicaonline.org/articles/ahsan-al-taqasim-fi-marefat-al-aqalim-celebrated-geographical-work/)
- [wikishia — Pledge of al-Aqaba](https://en.wikishia.net/view/Pledge_of_al-Aqaba)
- [The Book of the Sage and Disciple — Wikipedia](https://en.wikipedia.org/wiki/The_Book_of_the_Sage_and_Disciple)
- [The Book of Unveiling (Kitab al-Kashf) — IIS](https://www.iis.ac.uk/publications-listing/the-book-of-unveiling/)
- [Ja'far ibn Mansur al-Yaman — Wikipedia](https://en.wikipedia.org/wiki/Ja'far_ibn_Mansur_al-Yaman)
- [Hayat Al-Qulub Vol.3 §"Interpretation of the Seven oft-repeated"](https://al-islam.org/hayat-al-qulub-vol3-allamah-muhammad-baqir-al-majlisi/part-27-interpretation-seven-oft-repeated)
- [The world in Arab eyes: A reassessment of the climes in medieval Islamic scholarship — Cambridge](https://www.cambridge.org/core/journals/bulletin-of-the-school-of-oriental-and-african-studies/article/abs/world-in-arab-eyes-a-reassessment-of-the-climes-in-medieval-islamic-scholarship/86BB53AF4BBC155B0FCECB8A7D83A089)

## 8. Decisions on file (user, 2026-05-19)

- **12 jazāʾir framing:** symbolic + historical (both).
- **7-sphere cryptic letters:** flag for human review; do not decode.
- **Execution:** document the plan only. Do not execute.
