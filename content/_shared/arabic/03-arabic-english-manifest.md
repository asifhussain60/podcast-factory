# Arabic → English → Phonetic Manifest

Canonical lookup for every Arabic / Islamic term in active use across the
journal and podcast pipelines. No Arabic script — Latin only.

**Format**: `Common Latin spelling | English meaning | TTS-tuned phonetic | Notes`

The "common Latin spelling" column is what authors typically write before
respelling (e.g., `aoozu`, `shaytan`, `inshaAllah`). The "TTS-tuned phonetic" is
the canonical form that goes into the chapter or framing — the form NotebookLM
reads.

**Authority order**: this manifest wins for the canonical phonetic.
Book-specific overrides in `content/podcast/<book>/_system/pronunciation.md`
may add terms but must not contradict the spellings here.

---

## 1. Foundational openers (the recitation entries)

| Common Latin | English meaning | TTS-tuned phonetic | Notes |
|--------------|-----------------|--------------------|-------|
| aoozu / a'udhu / a'oodhu | I seek protection | **a-oo-thoo** | Opening of isti'aadha. Fallback `aoothoo` if `aoodhu` fails. |
| billah / billaahi | in Allah | **bil-laah-i** | |
| minash-shaytaan / mina-shaytaan | from Satan | **mi-nash-shay-taan** | Sun-letter assimilation; doubled `aa`. |
| ir-rajeem | the rejected (Satan) | **ir-ra-jeem** | Sun-letter assimilation; doubled `ee`. |
| Bismillah | In the name of Allah | **bis-mil-laah** | |
| ir-Rahmaan | the Most Compassionate | **ir-rah-maan** | Sun letter. |
| ir-Raheem | the Most Merciful | **ir-ra-heem** | Sun letter. |
| Alhamdulillah / al-hamdulillah | Praise be to Allah | **al-ham-du-lil-laah** | Moon letter for `al-h`. |
| Subhanallah / SubhanAllah | Glory be to Allah | **sub-haa-nal-laah** | |
| Allahu Akbar | Allah is greatest | **allaahu ak-bar** | |
| La ilaha illa Allah | There is no god but Allah | **laa i-laa-ha il-lal-laah** | |
| Astaghfirullah | I seek Allah's forgiveness | **as-tagh-fi-rul-laah** | |
| InshaAllah / in sha' Allah | God willing | **in-shaaa Allaah** | Triple `aaa` is intentional — extra hold. |
| MashaAllah / ma sha' Allah | as Allah willed | **maa-shaaa Allaah** | |
| JazakAllahu khayran | May Allah reward you | **ja-zaak Allaahu khai-ran** | |
| BarakAllahu feek | May Allah bless you | **baa-rak Allaahu feek** | |
| As-salaamu alaykum | Peace be upon you | **as-sa-laa-mu a-lay-kum** | Sun-letter assimilation. |
| Wa alaykumus-salaam | And upon you peace | **wa a-lay-ku-mus sa-laam** | |
| Ameen | Amen | **aa-meen** | Never `AY-men` or `uh-MEN`. |
| Innaa lillaahi wa innaa ilayhi raji'oon | Indeed we belong to God, and to Him we return | **in-naa lil-laa-hi wa in-naa i-lay-hi raa-ji-oon** | Supplication of loss. |

---

## 2. Divine names and the name "Allah"

| Common Latin | English meaning | TTS-tuned phonetic | Notes |
|--------------|-----------------|--------------------|-------|
| Allah | God | **Allaah** | Always double the final `aa`. Capital `A` only because it is a name; spoken stress is on the second syllable. |
| Allah Ta'ala | God, the Most Exalted | **Allaah ta-aa-laa** | |
| Subhanahu wa Ta'ala (SWT) | Glorified and Exalted is He | **sub-haa-na-hu wa ta-aa-laa** | Speak full English, never "S-W-T". |
| Rabb | Lord (of) | **rabb** | Geminated `bb`. |
| Rabbana | Our Lord | **rab-ba-naa** | |
| Rahmaan | the Most Compassionate | **rah-maan** | One of the Beautiful Names. |
| Raheem | the Most Merciful | **ra-heem** | |
| Hakeem | the All-Wise | **ha-keem** | |
| Aleem | the All-Knowing | **a-leem** | |
| Quddoos | the Most Holy | **qud-doos** | |

---

## 3. Honorifics after names

These ARE spoken in full English form on every occurrence — never speak the
abbreviation aloud.

| Common Latin | Used for | TTS-tuned phonetic (rarely used; spell out instead) | Full spoken English |
|--------------|----------|------------------------------------------------------|---------------------|
| ﷺ / SAW / sallallahu alayhi wa sallam | The Prophet Muhammad | **sal-lal-laa-hu a-lay-hi wa sal-lam** | **peace and blessings of Allah be upon him** |
| (AS) — male | A prophet or Imam | **a-lay-his sa-laam** | **peace be upon him** |
| (AS) — female | A female honored figure | **a-lay-has sa-laam** | **peace be upon her** |
| (RA) — male | A male Companion | **ra-di-yal-laa-hu an-hu** | **may Allah be pleased with him** |
| (RA) — female | A female Companion | **ra-di-yal-laa-hu an-haa** | **may Allah be pleased with her** |
| (RA) — plural | Multiple Companions | **ra-di-yal-laa-hu an-hum** | **may Allah be pleased with them** |
| (RA) for departed scholar | A deceased Sunni scholar | **ra-hi-ma-hul-laah** | **may Allah have mercy upon him** |
| (RA) for departed saint | Departed saintly figure | **rah-ma-tul-laa-hi a-lay-hi** | **may Allah shower His mercy upon him** |

**Memoir-specific carve-out**: In the journal skill, Ali (AS) is glossed once
per chapter on first use as **AS — peace be upon him**. See
`content/babu-memoir/_system/translations-glossary.md` for the chapter-by-chapter
record. Subsequent uses in the same chapter are bare `Ali (AS)`.

---

## 4. Core devotional vocabulary

| Common Latin | English meaning | TTS-tuned phonetic | Notes |
|--------------|-----------------|--------------------|-------|
| Tawheed | Oneness of God | **taw-heed** | |
| Du'a / duaa | Supplication | **du-aa** | Glottal stop carried by the hyphen. |
| Quran / Qur'an | the Qur'an | **qur-aan** | Hyphen instead of apostrophe. |
| Surah | chapter (of the Quran) | **soo-rah** | |
| Ayah | verse | **aa-yah** | |
| Ayat | verses (plural) | **aa-yaat** | |
| Salah / Salat | ritual prayer | **sa-laah** | |
| Imaan / Iman | faith | **ee-maan** | |
| Ummah | the community (of believers) | **um-mah** | Geminated. |
| Sunnah | the Prophet's outward and inward way | **soon-nah** | Geminated. |
| Sharee'ah / Shari'a | the revealed law | **sha-ree-ah** | |
| Tareeqa / Tariqa | the spiritual path | **ta-ree-qa** | |
| Haqeeqa / Haqiqa | the inner truth / reality | **ha-qee-qa** | |
| Ma'rifa / ma'arifah | direct knowledge of God | **maa-ri-fah** | |
| Zikr / Dhikr | remembrance (of God) | **thikr** | `th` more reliable than `dh`. |
| Hadith | a saying or report of the Prophet | **ha-deeth** | |
| Ahadith | plural of hadith | **a-haa-deeth** | |
| Sahaba | the Companions of the Prophet | **sa-haa-bah** | |
| Ahl al-Bayt | the family of the Prophet | **ahl al-bayt** | |

---

## 5. Theology and inner life — the substitution-candidate vocabulary

Many of these have a clean English equivalent and SHOULD be replaced with the
English form unless theological precision demands the Arabic. See
[04-common-term-substitutions.md](04-common-term-substitutions.md) for the policy.

| Common Latin | English meaning(s) | TTS-tuned phonetic | Default action |
|--------------|--------------------|--------------------|----------------|
| nafs | soul / self / lower self / irascible soul | **nafs** | **Substitute to English**, context-driven. See 04 §2. |
| nafs ammara | the soul that commands to evil | **naf-sul am-maa-rah** | **the inciting / commanding soul** (substitute). |
| nafs lawwama | the self-reproaching soul | **naf-sul law-waa-mah** | **the self-reproaching soul** (substitute). |
| nafs mutmainna | the soul at peace | **naf-sul mut-ma-in-nah** | **the soul at peace** (substitute). |
| ruh | spirit | **rooh** | **Substitute to English** "spirit" unless contrasted with *nafs*. |
| qalb | heart (spiritual seat) | **qalb** | **Substitute to English** "heart" unless used as a technical term. |
| aql | intellect / reason | **aql** | **Substitute to English** "intellect" or "reason". |
| hawa | low desire / passion | **ha-waa** | **Substitute to English** "lower desire" or "passion". |
| shaytan / shaitan | Satan | **shay-taan** | **Substitute to English** "Satan" by default. |
| iblees | Iblis (the proper name of Satan) | **ib-lees** | Keep when naming him as a character (the Quranic narrative); substitute "Satan" otherwise. |
| jinn | jinn (unseen sentient beings) | **jinn** | Keep. No clean English equivalent. |
| malak / malaa'ika | angel / angels | **ma-lak / ma-laa-i-ka** | **Substitute to English** "angel" / "angels". |
| akhirah | the Hereafter | **aa-khi-rah** | **Substitute to English** "the Hereafter" or "the next life". |
| dunya | this world / worldly life | **dun-ya** | **Substitute to English** "this world" or "worldly life". |
| jannah | paradise / garden | **jan-nah** | **Substitute to English** "paradise". |
| jahannam | hell | **ja-han-nam** | **Substitute to English** "hell". |
| qiyamah | the Resurrection / Day of Standing | **qi-yaa-mah** | **Substitute to English** "the Resurrection" or "the Day of Standing". |
| ilm | (sacred) knowledge | **ilm** | **Substitute to English** "knowledge" unless contrasted with *ma'rifa*. |
| hikmah | wisdom | **hik-mah** | **Substitute to English** "wisdom". |
| sabr | patience / patient endurance | **sabr** | **Substitute to English** "patience" or "patient endurance". |
| shukr | gratitude | **shukr** | **Substitute to English** "gratitude". |
| tawakkul | reliance on God (after right action) | **ta-wak-kul** | Keep (technical Sufi term). Gloss on first use. |
| ikhlaas | sincerity (single-hearted) | **ikh-laas** | Keep (technical). Gloss on first use. |
| ihsaan | spiritual excellence (worshipping God as if seeing Him) | **ih-saan** | Keep (technical). Gloss on first use. |
| taqwa | God-consciousness / watchful awareness | **taq-waa** | Keep (technical). Gloss on first use. |
| taqleed | following recognized authority in religion | **taq-leed** | Keep (technical). Gloss on first use. |
| tasawwuf | Sufism / the inner discipline of the soul | **ta-saw-wuf** | Keep when discussing the tradition by name. Substitute "Sufism" otherwise. |
| zuhd | renunciation / detachment from the world | **zuhd** | **Substitute to English** "renunciation" or "detachment". |
| wara' | scrupulousness | **wa-raa** | **Substitute to English** "scrupulousness". |
| niyyah | intention | **nee-yah** | **Substitute to English** "intention". |
| bid'a | innovation outside established practice | **bid-ah** | Keep with a brief gloss on first use. |
| halal | permitted | **ha-laal** | Keep (widely recognized English borrowing). |
| haram | forbidden | **ha-raam** | Keep (widely recognized English borrowing). |
| fard / fard al-ayn | obligatory / personal obligation | **fard / fard al-ayn** | Keep (technical). Gloss on first use. |
| fard kifaya | communal obligation | **fard ki-faa-yah** | Keep (technical). Gloss on first use. |

---

## 6. Ritual practice

| Common Latin | English meaning | TTS-tuned phonetic | Notes |
|--------------|-----------------|--------------------|-------|
| wudu | minor ritual washing | **wu-doo** | |
| ghusl | major ritual washing | **ghusl** | |
| adhan | call to prayer | **a-thaan** | `th` for the dhaal. |
| iqamah | second call before prayer starts | **i-qaa-mah** | |
| rak'ah / raka'at | a cycle of the prayer / cycles | **ra-kah / ra-ka-aat** | |
| sajda / sujood | prostration / prostrations | **saj-dah / su-jood** | |
| ruku' | bowing in prayer | **ru-koo** | |
| tahajjud | the optional prayer in the last third of the night | **ta-haj-jud** | |
| fajr | dawn prayer | **fajr** | |
| dhuhr | noon prayer | **thuhr** | `th` for the dhaal. |
| asr | afternoon prayer | **asr** | |
| maghrib | sunset prayer | **magh-rib** | |
| isha | night prayer | **i-shaa** | |
| sawm | fasting | **sawm** | |
| ramadan | the month of fasting | **ra-ma-daan** | Long alif at the end. |
| iftar | the breaking-of-fast meal | **if-taar** | |
| suhoor | the pre-dawn meal | **su-hoor** | |
| zakat | obligatory alms | **za-kaat** | |
| sadaqa | voluntary charity | **sa-da-qah** | |
| hajj | the major pilgrimage | **hajj** | Geminated. |
| umrah | the minor pilgrimage | **um-rah** | |
| ka'bah | the Cube (in Mecca) | **kaa-bah** | Hyphen for the hamza. |
| qibla | the prayer direction | **qib-lah** | |

---

## 7. Lifecycle and family

| Common Latin | English meaning | TTS-tuned phonetic | Notes |
|--------------|-----------------|--------------------|-------|
| nikah | Islamic marriage contract | **ni-kaah** | |
| mahr | bride-gift | **mahr** | |
| iddah | post-divorce / widowhood waiting period | **id-dah** | |
| talaq | divorce | **ta-laaq** | |
| khutba | sermon | **khut-bah** | |
| janazah | funeral prayer | **ja-naa-zah** | |
| shahadah | the testimony of faith | **sha-haa-dah** | |
| shaheed | martyr | **sha-heed** | |

---

## 8. Named scholarly works and figures (Ismaili + Sunni + Shia)

| Common Latin | English meaning | TTS-tuned phonetic | Notes |
|--------------|-----------------|--------------------|-------|
| Imam Abu Hamid Muhammad al-Ghazali | the author of *Ihya* | **i-maam a-boo haa-mid mu-ham-mad al-gha-zaa-lee** | 1058–1111 CE. |
| Ihya Ulum al-Din | *Revival of the Religious Sciences* (Ghazali) | **ih-yaa oo-loom ad-deen** | Sun-letter assimilation in *ad-deen*. |
| Kimiya al-Sa'adah | *The Alchemy of Happiness* (Ghazali) | **kee-mee-yaa as-sa-aa-dah** | |
| Mishkat al-Anwar | *Niche of Lights* (Ghazali) | **mish-kaat al-an-waar** | |
| Munqidh min al-Dalal | *Deliverance from Error* (Ghazali) | **mun-qith min ath-tha-laal** | |
| Bidayat al-Hidaya | *Beginning of Guidance* (Ghazali) | **bi-daa-yat al-hi-daa-yah** | |
| Jawahir al-Quran | *Gems of the Qur'an* (Ghazali) | **ja-waa-hir al-qur-aan** | |
| Ayyuhal Walad | *O Beloved Son* (Ghazali) | **eye-yoo-hal waa-lad** | The Ayyuhal Walad podcast source. |
| Majmu'a Rasail | *Collection of Treatises* | **maj-moo-a ra-saa-il** | |
| Nahj al-Balagha | *Peak of Eloquence* (Imam Ali AS) | **nahj al-ba-laa-ghah** | |
| Sahifa al-Sajjadiyya | *Scripture of al-Sajjad* (Imam Zayn al-Abidin AS) | **sa-hee-fa as-saj-jaa-dee-yah** | |
| Ghurar al-Hikam | *Aphorisms of Imam Ali* | **ghu-rar al-hi-kam** | |
| Riyad al-Salihin | *Gardens of the Righteous* (an-Nawawi) | **ri-yaad as-saa-li-heen** | |
| Bukhari | Sahih al-Bukhari (hadith collection) | **bu-khaa-ree** | |
| Muslim | Sahih Muslim (hadith collection) | **mus-lim** | |
| Tirmidhi | Jami al-Tirmidhi | **tir-mi-thee** | `th` for dhaal. |
| Nasa'i | Sunan al-Nasa'i | **na-saa-ee** | Hyphen for hamza. |
| Abu Dawud | Sunan Abi Dawud | **a-boo daa-wood** | |
| Ibn Majah | Sunan Ibn Majah | **ibn maa-jah** | |
| Junaid al-Baghdadi | early Sufi master | **joo-nayd al-bagh-daa-dee** | |
| Hasan al-Basri | early Muslim ascetic | **ha-san al-bas-ree** | |
| Hatim bin Ism (al-Asamm) | Sufi master, "the deaf one" | **haa-tim ibn ism al-a-samm** | |
| Shaqiq al-Balkhi | Sufi master, Hatim's teacher | **sha-qeeq al-bal-khee** | |
| Sufyan al-Thawri | early jurist and ascetic | **suf-yaan ath-thaw-ree** | |
| Shibli | Sufi master | **shib-lee** | |
| Luqman | Quranic sage, advisor to his son | **luq-maan** | |
| Rumi | Jalal al-Din Rumi (Sufi poet) | **roo-mee** | |
| Attar | Farid al-Din Attar (Sufi poet) | **at-taar** | |
| Sa'di | Sa'di of Shiraz (Persian poet) | **saa-dee** | |
| Ibn Ata Allah | Ibn Ata Allah al-Iskandari | **ibn a-taa Allaah** | |
| Nasir-i Khusraw | Ismaili philosopher | **naa-sir-i khus-raw** | |
| Hamid al-Din al-Kirmani | Ismaili philosopher | **haa-mid ad-deen al-kir-maa-nee** | |
| Pir Hasan Kabirdin | Ismaili Pir | **peer ha-san ka-beer-din** | |
| Aga Khan | His Highness the Aga Khan (Ismaili Imam) | **aa-ga khaan** | |

---

## 9. Ismaili-specific terms

| Common Latin | English meaning | TTS-tuned phonetic | Notes |
|--------------|-----------------|--------------------|-------|
| Imam | spiritual guide; in Shia tradition, the rightful leader | **i-maam** | Keep. |
| Imamah | the institution of the Imamat | **i-maa-mah** | |
| Wilayah | spiritual authority, guardianship | **wi-laa-yah** | |
| Hujjah | the proof; senior rank in the Ismaili da'wah | **huj-jah** | |
| Da'i | summoner; teacher in the Ismaili da'wah | **daa-ee** | |
| Da'wah | the call; the missionary teaching of the Imamat | **daa-wah** | |
| Natiq | the speaking Prophet who reveals outward law | **naa-tiq** | |
| Asas | the foundation; the wasi who reveals inner meaning | **a-saas** | |
| Ta'wil | esoteric / disciplined interpretation | **ta-weel** | |
| Tanzil | revealed scripture in its outer form | **tan-zeel** | |
| Bay'ah | the oath of allegiance | **bay-ah** | |
| Farman | guidance of the present Imam | **far-maan** | |
| Ginan | devotional poem in the Khoja tradition | **gi-naan** | |
| Holy Du'a | the Ismaili daily prayer | **ho-lee du-aa** | English first word kept. |

---

## 10. Selected Quranic verse fragments (when transliterated in a chapter)

These should always carry the phonetic on first occurrence and follow with the
translator-named English rendering. Add to the per-book `_lexicon.md` as
encountered.

| Transliterated verse | Phonetic | Reference |
|----------------------|----------|-----------|
| Fadhkuruni Adhkurkum | **fath-ku-roo-nee ath-kur-kum** | Quran 2:152 — "Remember Me; I will remember you." |
| Innaa lillaahi wa innaa ilayhi raji'oon | **in-naa lil-laa-hi wa in-naa i-lay-hi raa-ji-oon** | Quran 2:156 — "Indeed we belong to God, and to Him we return." |
| Laqad kana lakum fi rasulillahi uswatun hasanah | **la-qad kaa-na la-kum fi ra-soo-lil-laa-hi us-wa-tun ha-sa-nah** | Quran 33:21. |
| Famun kana yarju liqaa-a Rabbihi fal-ya'mal amalan saaliha | **fa-mun kaa-na yar-joo li-qaa-a rab-bi-hi fal-ya-mal a-ma-lan saa-li-han** | Quran 18:110. |
| Innal ladhina aamanoo wa amilus saalihaat | **in-nal la-thee-na aa-ma-noo wa a-mi-lus saa-li-haat** | Quran 18:107. |

---

## 11. Adding a term

1. Locate the right section above (or open a new one if none fits).
2. Fill all four columns. The phonetic must follow
   [01-tts-pronunciation-key.md](01-tts-pronunciation-key.md) rules.
3. If the term belongs in the substitution policy, also add it to
   [04-common-term-substitutions.md](04-common-term-substitutions.md).
4. Cascade to the book's `_phonetics.md` / `_lexicon.md` and (if memoir-relevant)
   to `content/babu-memoir/_system/translations-glossary.md`.
5. Commit alongside the chapter that introduced the term.

---

*Latin-only by design. Last seeded 2026-05-17.*
