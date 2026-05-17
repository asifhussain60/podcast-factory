# Chapter Enrichment — Authorized Sources and Citation Format

**Authoritative status:** Canonical reference for Phase 0f (chapter enrichment) of the podcast skill. Any enrichment that draws on outside material MUST come from this whitelist and MUST be cited per the format below. Material from outside the whitelist is rejected.

**Scope:** Applies to every podcasted source book in `content/podcast/<book>/`. Per the A/B/C rule encoded in `skills-staging/podcast/SKILL.md`, outside enrichment may not exceed 60% of any chapter's final word count.

---

## 1. The whitelist

Sources are tiered. Tier 1 has highest priority; lower tiers fill in where Tier 1 doesn't speak to the theme.

### Tier 1 — The Author's Own Corpus

When the source book has a known author, the author's other writings are the highest-priority enrichment. They preserve voice and avoid theological displacement.

- For Ghazali (current book *Ayyuhal Walad*): *Ihya Ulum al-Din*, *Kimiya al-Sa'ada* (Alchemy of Happiness), *Munqidh min al-Dalal* (Deliverance from Error), *Mishkat al-Anwar* (Niche of Lights), *Bidayat al-Hidaya* (Beginning of Guidance), *Jawahir al-Quran* (Jewels of the Quran), *Arba'in* (Forty Steps), *Minhaj al-Abidin* (The Path of Worshippers).
- For other authors: their named corpus, cited by title + book/chapter.

### Tier 2 — Quran

The Quran as primary scripture. Quote with both transliteration and English translation; provide phonetic for the transliteration.

### Tier 3 — Hadith of the Prophet Muhammad (PBUH)

The six canonical Sunni collections (*Kutub al-Sittah*): Sahih al-Bukhari, Sahih Muslim, Sunan al-Tirmidhi, Sunan Abu Dawud, Sunan al-Nasa'i, Sunan Ibn Majah. Supplementary curated collections: *Riyad al-Salihin* (Imam al-Nawawi), *Al-Adab al-Mufrad* (al-Bukhari). Use grading (sahih, hasan, da'if) when contested.

### Tier 4 — Imam Ali ibn Abi Talib (AS) and the Ahl al-Bayt

- *Nahj al-Balagha* (compiled by al-Sharif al-Radi, c. 1009 CE) — sermons (*khutab*), letters (*kutub*), aphorisms (*hikam*) of Imam Ali. Cited by section number.
- *Ghurar al-Hikam wa Durar al-Kalim* (al-Amidi) — extended aphorisms of Imam Ali.
- *Sahifa al-Sajjadiyya* — du'as of Imam Zayn al-Abidin, Imam Ali's great-grandson. Cited by du'a number.
- Other Ahl al-Bayt traditions where authenticated.

### Tier 5 — Ismaili Tradition

- **The Holy Du'a** — the daily Ismaili prayer. Cited by part number (parts I–VI).
- **Ginans** — devotional poetry of the South Asian Ismaili tradition. Cited by ginan title + composer (e.g., Pir Hasan Kabirdin, Pir Sadr al-Din, Pir Shams al-Din, Saiyad Imam Shah, Saiyad Pir Sabz Ali). Translations attributed to the translator.
- **Farmans of the Aga Khans** — Aga Khan III (Sultan Muhammad Shah), Aga Khan IV (Shah Karim al-Hussaini), Aga Khan V (Rahim al-Hussaini). Cited by speaker, date, and location.
- **Classical Ismaili philosophers:**
  - Nasir-i Khusraw (1004–1088): *Wajh-i Din*, *Shish Fasl* (Six Chapters), *Jami' al-Hikmatayn*, *Safarnama*, *Diwan*.
  - Hamid al-Din al-Kirmani (d. c. 1021): *Rahat al-Aql* (The Repose of the Intellect), *Risalat al-Riyad*.
  - Abu Ya'qub al-Sijistani (d. c. 971): *Kitab al-Yanabi'* (Book of Wellsprings), *Kashf al-Mahjub*.
  - Mu'ayyad fi al-Din al-Shirazi (d. 1078): *Al-Majalis al-Mu'ayyadiyya*, *Diwan*.
  - Qadi al-Nu'man (d. 974): *Da'a'im al-Islam* (Pillars of Islam).
  - Ja'far ibn Mansur al-Yaman: *Sara'ir al-Nutaqa'*, *Ta'wil al-Zakat*.

### Tier 6 — Sufi Tradition Near Ghazali

Used when the source book is by Ghazali or treats Sufi themes. These authors are in conversation with Ghazali's spirit.

- Junaid al-Baghdadi (d. 910) — whom Ghazali himself cites in *Ayyuhal Walad*.
- Hasan al-Basri (d. 728) — frequently cited by Ghazali.
- Rabi'a al-Adawiyya (d. 801).
- Jalal al-Din Rumi (d. 1273) — *Mathnawi*, *Diwan-i Shams*, *Fihi Ma Fihi*.
- Farid al-Din Attar (d. c. 1221) — *Mantiq al-Tayr* (Conference of the Birds), *Tadhkirat al-Awliya*.
- Sa'di Shirazi (d. 1292) — *Gulistan*, *Bustan*.
- Ibn Ata Allah al-Iskandari (d. 1309) — *Hikam* (Aphorisms).
- Al-Muhasibi (d. 857) — *Kitab al-Ri'aya*.

### Tier 7 — Modern Reference Works (for context only, not for direct quotation)

Used to verify dates, biographies, and citations. Not quoted in the chapter text.

- Annemarie Schimmel, *Mystical Dimensions of Islam*.
- Seyyed Hossein Nasr, *Islamic Spirituality* (anthologies).
- W. Montgomery Watt, *Muslim Intellectual: A Study of al-Ghazali*.
- Farhad Daftary, *The Isma'ilis: Their History and Doctrines* (for Ismaili tradition).

---

## 2. Citation format

Every direct quote or borrowed material gets an inline citation in parentheses. Provide enough information that a reader could locate the source. Be specific.

| Source type | Format | Example |
|---|---|---|
| Quran | `(Quran <Surah>:<Verse>)` or `(<Surah Name> <Surah>:<Verse>)` | `(Quran 53:39)` or `(An-Najm 53:39)` |
| Sahih al-Bukhari | `(Sahih al-Bukhari, Book <N>, Hadith <N>)` + narrator on next line | `(Sahih al-Bukhari, Book 1, Hadith 1)` |
| Sahih Muslim | `(Sahih Muslim, Book <N>, Hadith <N>)` | `(Sahih Muslim, Book 31, Hadith 5)` |
| Other Sunan | `(Sunan al-Tirmidhi, Hadith <N>)` etc. | `(Sunan al-Tirmidhi, Hadith 2459)` |
| Riyad al-Salihin | `(Riyad al-Salihin, Hadith <N>)` | `(Riyad al-Salihin, Hadith 1)` |
| Nahj al-Balagha | `(Nahj al-Balagha, Sermon <N>)` / `(NB Letter <N>)` / `(NB Aphorism <N>)` | `(Nahj al-Balagha, Sermon 1)` |
| Ghurar al-Hikam | `(Ghurar al-Hikam, <N>)` | `(Ghurar al-Hikam, 6900)` |
| Sahifa al-Sajjadiyya | `(Sahifa al-Sajjadiyya, Du'a <N>)` | `(Sahifa al-Sajjadiyya, Du'a 5)` |
| Ghazali — Ihya | `(Ihya Ulum al-Din, Vol. <N>, Book of <Title>)` | `(Ihya Ulum al-Din, Vol. 1, Book of Knowledge)` |
| Ghazali — other | `(<Title>, <Chapter/Section>)` | `(Kimiya al-Sa'ada, Chapter 1)` |
| Holy Du'a | `(Holy Du'a, Part <I–VI>)` | `(Holy Du'a, Part III)` |
| Ginan | `(<Ginan title>, by <Pir name>)` + translator credited if quoted in translation | `(Sakhi maro saheb sona varno, by Pir Hasan Kabirdin)` |
| Farman | `(Farman of HH Aga Khan <III/IV/V>, <location>, <date>)` | `(Farman of HH Aga Khan IV, Aiglemont, 19 December 1986)` |
| Ismaili philosopher | `(<Author>, <Work>, <section/chapter>)` | `(Nasir-i Khusraw, Wajh-i Din, Chapter 3)` |
| Sufi poetry | `(<Author>, <Work>, Book <N>, Verse <N>)` | `(Rumi, Mathnawi, Book 1, Verses 1–18)` |
| Sufi prose | `(<Author>, <Work>, <section>)` | `(Ibn Ata Allah, Hikam, Aphorism 1)` |

When quoting Arabic, provide:
1. The Arabic transliteration (italicized).
2. The phonetic guide in parentheses on first occurrence.
3. The English translation in italicized or quoted form.
4. The citation.

Example:
> *Inna a'malu bi al-niyyat* (IN-na ah-MAH-loo bi al-nee-YAHT).
> *Indeed, deeds are by intentions.* — (Sahih al-Bukhari, Book 1, Hadith 1; narrated by Umar ibn al-Khattab)

---

## 3. Enrichment principles

These principles govern HOW outside material is used inside an enriched chapter.

1. **The author's spine stays primary.** The original author's argument is the spine of each chapter. Enrichment material illuminates the spine; it never replaces it. The ≤60% cap is the hard floor on author-content; in practice many chapters will be 75–85% author content with 15–25% enrichment.

2. **Tradition-coherence over breadth.** Prefer two well-placed citations from the same tradition over six scattered citations across traditions. A chapter on intention can quote Quran 53:39, Sahih Bukhari Hadith 1 (narrated by Umar), and Nahj al-Balagha Aphorism 60 — all converging on intention — and that is stronger than six unrelated quotes.

3. **Quote, do not paraphrase, when adding scripture or hadith.** Verbatim quotation with citation is the only acceptable form for Quran, hadith, and Ahl al-Bayt traditions. Paraphrasing scripture is forbidden.

4. **Honor the author's affinity.** Ghazali cites Junaid, Hasan al-Basri, Quran, and hadith frequently. Enrichment that draws on those same sources amplifies what's already in the text. Enrichment that pulls Ismaili philosophical material is appropriate where the theme is universal (intention, sincerity, knowledge-and-action), less appropriate where Ghazali is making a specifically Ash'ari or Sufi-of-his-time argument that doesn't have a clear Ismaili parallel.

5. **Cross-tradition is welcome where the theme is shared.** Most of *Ayyuhal Walad* — intention, action over knowledge, sincerity, night-prayer, service without expectation, the danger of vanity — is shared territory across Sunni, Shia, Ismaili, and Sufi traditions. Use the breadth honestly.

6. **Cite, don't smuggle.** Every borrowed sentence has a citation. No "the tradition teaches that…" generalities. Specificity is what gives the chapter its weight.

7. **Pronunciation guidance carries through.** Any Arabic, Persian, or technical term introduced by enrichment is added to `_system/source/text/_lexicon.md` with its phonetic form, and the first occurrence in the chapter carries the phonetic guide.

---

## 4. Anti-patterns

Avoid:

- **Devotional padding** — adding *salawat* (PBUH), *radi Allahu anhu*, *alayhi al-salam* on every occurrence rather than at first mention only. The skill removes these on subsequent occurrences for readability while preserving them at first mention.
- **Inauthentic hadith** — hadith with weak (da'if) or fabricated (mawdu') grading should not be used unless the chapter is specifically discussing the contested ground. When in doubt, omit.
- **Source-shifting** — quoting Quran or hadith in a way that distorts its accepted meaning to fit the chapter's argument. The author's argument bends to the citation, not the reverse.
- **Mixed-tradition collisions** — placing a Sunni hadith and a Shi'a tradition side-by-side without acknowledging they come from different scholarly chains. Either keep them in separate sections, or annotate the difference.
- **English-only Quran citations** — always include Arabic transliteration with phonetic, then English translation. The Audio Overview hosts need to pronounce the original.

---

## 5. Versioning

This file is versioned. When new sources are added to or removed from the whitelist, increment the version and note the change.

**Version:** 1.0 (initial — 2026-05-16)
