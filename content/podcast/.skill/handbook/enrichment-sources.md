# Chapter Enrichment — Authorized Sources and Citation Format

**Authoritative status:** Canonical reference for Phase 0f (chapter enrichment) of the podcast skill. Any enrichment that draws on outside material MUST come from this whitelist and MUST be cited per the format below. Material from outside the whitelist is rejected.

**Scope:** Applies to every podcasted source book under `content/podcast/library/<category>/<book-slug>/`. Per the A/B/C rule encoded in `skills-staging/podcast/SKILL.md`, outside enrichment may not exceed 60% of any chapter's final word count.

---

## 1. The whitelist

Sources are tiered. Tier 1 has highest priority; lower tiers fill in where Tier 1 doesn't speak to the theme.

### Tier 1 — The Author's Own Corpus (per-book)

When the source book has a known author, the author's other writings are the highest-priority enrichment. They preserve voice and avoid theological displacement.

**Tier 1 is book-specific.** Each book enumerates its author's corpus at `BOOK_DIR/_system/enrichment-whitelist.md`. The handbook does not name any one author's works here. Examples of what such a file contains — for one book's author — live at [`worked-examples.md` §7](worked-examples.md#7--tier-1-enrichment-whitelist-book-specific).

If a book's enrichment-whitelist.md is missing or empty, Tier 1 simply does not contribute to that book's enrichment and the lower tiers carry the load. There is no global Tier 1 fallback.

### Tier 2 — Quran

The Quran as primary scripture. Quote with both transliteration and English translation; provide phonetic for the transliteration.

### Tier 3 — Hadith of the Prophet Muhammad (PBUH)

The six canonical Sunni collections (*Kutub al-Sittah*): Sahih al-Bukhari, Sahih Muslim, Sunan al-Tirmidhi, Sunan Abu Dawud, Sunan al-Nasa'i, Sunan Ibn Majah. Supplementary curated collections: *Riyad al-Salihin* (Imam al-Nawawi), *Al-Adab al-Mufrad* (al-Bukhari). Use grading (sahih, hasan, da'if) when contested.

### Tier 4 — Imam Ali ibn Abi Talib (AS) and his companions

- *Nahj al-Balagha* (compiled by al-Sharif al-Radi, c. 1009 CE) — sermons (*khutab*), letters (*kutub*), aphorisms (*hikam*) of Imam Ali. Cited by section number.
- *Ghurar al-Hikam wa Durar al-Kalim* (al-Amidi) — extended aphorisms of Imam Ali.
- Companions of Imam Ali — Salman al-Farsi, Abu Dharr al-Ghifari, Miqdad ibn al-Aswad, Ammar ibn Yasir. Traditions cited by authenticated chain.

### Tier 5 — Ahl al-Bayt (Imam Ali's progeny)

Authenticated traditions from any member of the progeny of Imam Ali ibn Abi Talib (AS) and Sayyida Fatima al-Zahra (AS) — the household of the Prophet through Ali's line. This includes but is not limited to:

- **Sayyida Fatima al-Zahra (AS)** — sermons (notably the *Khutba of Fadak*), supplications, and authenticated sayings.
- **Imam Hasan ibn Ali (AS)** — letters, sermons, and authenticated sayings.
- **Imam Hussain ibn Ali (AS)** — the sermons and letters from Karbala and before; the supplication of Arafa (*Du'a Arafa*) is the principal preserved du'a.
- **Sayyida Zaynab bint Ali (AS)** — sermons after Karbala (Kufa, Damascus).
- **Imam Ali Zayn al-Abidin (AS)** (also: Imam Ali Zainul Abideen, the fourth Imam) — *Sahifa al-Sajjadiyya* (the Psalms of Islam, du'as cited by number), *Risalat al-Huquq* (the Treatise of Rights).
- **Imam Muhammad al-Baqir (AS)** (the fifth Imam) — authenticated traditions on Quranic exegesis, fiqh, and ethics.
- **Imam Ja'far al-Sadiq (AS)** (the sixth Imam) — authenticated traditions in the Sunni and Shia hadith corpora.
- Subsequent Imams in Imam Ali's line as accepted by either Twelver or Ismaili tradition, where the saying is authenticated.

The whitelist extends to ANY verified member of Imam Ali's progeny, not just the figures named above. Citations follow the shape: speaker + source-work + section/du'a/letter number.

**Exception (out of scope — see Tier 5b):** the Aga Khans (Aga Khan III, IV, V) and Ismaili-specific institutional sources remain explicitly excluded by author policy, even though the Aga Khans claim descent in Imam Ali's line. Use other figures from the line above for equivalent attribution, or generalize without naming.

### Tier 5b — Out of scope (do NOT quote)

The following sources are excluded from podcast enrichment by author policy (Asif, 2026-05-17). If a quote from any of these appears in the original published source the chapter is adapted from, paraphrase the principle and attribute it to one of the allowed Tier 1–5 sources, OR generalize without naming the speaker / tradition.

- Aga Khans (Aga Khan III, IV, V) — farmans, addresses, writings.
- Ginans of the South Asian Ismaili tradition.
- The Holy Du'a of the Ismaili daily prayer (refer generically to "daily prayer" without identifying the tradition).
- Classical Ismaili philosophers — Nasir-i Khusraw, Hamid al-Din al-Kirmani, Abu Ya'qub al-Sijistani, Mu'ayyad fi al-Din al-Shirazi, Qadi al-Nu'man, Ja'far ibn Mansur al-Yaman.
- Any other Ismaili-specific named scholar or text.

### Tier 6 — Sufi Tradition

Used when the source book treats Sufi themes or is in dialogue with classical Sufi thought.

- Junaid al-Baghdadi (d. 910).
- Hasan al-Basri (d. 728).
- Rabi'a al-Adawiyya (d. 801).
- Jalal al-Din Rumi (d. 1273) — *Mathnawi*, *Diwan-i Shams*, *Fihi Ma Fihi*.
- Farid al-Din Attar (d. c. 1221) — *Mantiq al-Tayr* (Conference of the Birds), *Tadhkirat al-Awliya*.
- Sa'di Shirazi (d. 1292) — *Gulistan*, *Bustan*.
- Ibn Ata Allah al-Iskandari (d. 1309) — *Hikam* (Aphorisms).
- Al-Muhasibi (d. 857) — *Kitab al-Ri'aya*.

### Tier 7 — Modern Reference Works (for context only, not for direct quotation)

Used to verify dates, biographies, and citations. Not quoted in the chapter text. The handbook does not pre-name author-specific references here — each book's `BOOK_DIR/_system/enrichment-whitelist.md` may enumerate its own Tier-7 references alongside the Tier 1 corpus.

General-purpose references (apply across books):
- Annemarie Schimmel, *Mystical Dimensions of Islam*.
- Seyyed Hossein Nasr, *Islamic Spirituality* (anthologies).
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
| Author's own corpus — multi-volume | `(<Work Title>, Vol. <N>, Book of <Title>)` | per `BOOK_DIR/_system/enrichment-whitelist.md` |
| Author's own corpus — single-volume | `(<Work Title>, <Chapter/Section>)` | per `BOOK_DIR/_system/enrichment-whitelist.md` |
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

4. **Honor the author's affinity.** Note which sources the book's author cites frequently — those same sources amplify what's already in the text on enrichment. Cross-tradition material is appropriate where the theme is universal (intention, sincerity, knowledge-and-action, the disciplines of the heart), less appropriate where the author is making a specifically school-bound argument that doesn't have a clear parallel in the borrowed tradition.

5. **Cross-tradition is welcome where the theme is shared.** Universal themes — intention, action-over-knowledge, sincerity, the danger of vanity, service without expectation — are shared territory across Sunni, Shia, Ismaili, and Sufi traditions. Use that breadth honestly.

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
