# Long-Name → Short-Alias Policy

**Cross-skill.** Read by `/podcast` (chapter authoring + customize-prompt framing) and `/journal` (memoir refinement when long names appear).

When a person's full name is 3+ tokens or 18+ characters, **use the full name once on first chapter-occurrence and use the short alias for every subsequent reference**. This applies to:

- Arabic / Islamic figures (the primary use case — long honorific-laden names)
- Persian / Central Asian sages
- Western philosophers with multi-part names
- Any historical figure whose canonical short name is well established

**Why**: in audio, a four-word name spoken 30 times across a 15-minute episode is fatiguing and consumes airtime that should carry argument. In prose, it interrupts reader flow. The alias is how human conversation handles it.

---

## How to pick an alias

In order of preference:

1. **Established short form** — the form scholarly literature uses (Ghazali, Rumi, Junaid, Hatim).
2. **First name in canonical phonetic form** (Sufyan, Shibli) — when the established short form IS the first name.
3. **Family / locality name** (al-Balkhi → Balkhi) when the first name is too common to disambiguate.
4. **Disambiguated form** (Imam Ali AS) when sharing a name with another figure in the same series.

The alias MUST use the canonical phonetic spelling from `03-arabic-english-manifest.md` — never a fresh respelling.

---

## Canonical aliases (the manifest)

### Imams and Quranic figures

| Full name on first mention | Short alias thereafter | Phonetic (per manifest) |
|---|---|---|
| Imam Ali ibn Abi Talib (AS) | Imam Ali (AS) | i-maam a-lee |
| Imam Hasan ibn Ali (AS) | Imam Hasan (AS) | i-maam ha-san |
| Imam Husayn ibn Ali (AS) | Imam Husayn (AS) | i-maam hu-sayn |
| Imam Zayn al-Abidin (AS) | Imam Zayn (AS) | i-maam zayn |
| Imam Ja'far al-Sadiq (AS) | Imam Ja'far (AS) | i-maam jaa-far |
| Luqman al-Hakim | Luqman | luq-maan |

### Ghazali and the Sufi tradition

| Full name on first mention | Short alias thereafter | Phonetic |
|---|---|---|
| Imam Abu Hamid Muhammad al-Ghazali | Ghazali | gha-zaa-lee |
| Hatim bin Ism al-Asamm | Haatim | haa-tim |
| Shaqiq al-Balkhi | Shaqeeq | sha-qeeq |
| Hasan al-Basri | Hasan al-Basri | ha-san al-bas-ree |
| Sufyan al-Thawri | Sufyan | suf-yaan |
| Junaid al-Baghdadi | Junaid | joo-nayd |
| Jalal al-Din Rumi | Rumi | roo-mee |
| Farid al-Din Attar | Attar | at-taar |
| Sa'di of Shiraz | Sa'di | saa-dee |
| Ibn Ata Allah al-Iskandari | Ibn Ata Allah | ibn a-taa Allaah |
| Abu Yazid al-Bistami | Bistami | bis-taa-mee |
| Mansur al-Hallaj | al-Hallaj | al-hal-laaj |
| Abu Bakr al-Shibli | Shibli | shib-lee |

### Hadith collectors

| Full name on first mention | Short alias thereafter | Phonetic |
|---|---|---|
| Imam Muhammad al-Bukhari | Bukhari | bu-khaa-ree |
| Imam Muslim ibn al-Hajjaj | Muslim | mus-lim |
| Imam al-Tirmidhi | Tirmidhi | tir-mi-thee |
| Imam Abu Dawud | Abu Dawud | a-boo daa-wood |
| Imam Ibn Majah | Ibn Majah | ibn maa-jah |
| Imam al-Nasa'i | Nasa'i | na-saa-ee |
| Imam al-Nawawi | Nawawi | na-waa-wee |

### Ismaili tradition

| Full name on first mention | Short alias thereafter | Phonetic |
|---|---|---|
| Nasir-i Khusraw | Nasir Khusraw | naa-sir khus-raw |
| Hamid al-Din al-Kirmani | al-Kirmani | al-kir-maa-nee |
| Abu Ya'qub al-Sijistani | al-Sijistani | as-si-jis-taa-nee |
| Mu'ayyad fi al-Din al-Shirazi | al-Mu'ayyad | al-mu-ay-yad |
| Qadi al-Nu'man | Qadi al-Nu'man | qaa-dee an-nu-maan |
| Pir Hasan Kabirdin | Pir Hasan | peer ha-san |
| Pir Sadr al-Din | Pir Sadr | peer sadr |
| HH Aga Khan IV (Prince Karim al-Husseini) | Aga Khan IV | aa-ga khaan |

### Modern scholarship / translation

| Full name on first mention | Short alias thereafter |
|---|---|
| Irfan Hasan (translator) | Irfan Hasan |
| Yasmin Mogahed | Mogahed |
| Hamza Yusuf | Hamza Yusuf |

---

## Honorific handling alongside the alias

When the figure carries an honorific (PBUH / AS / RA), follow the honorific rule from `03-arabic-english-manifest.md` §3:

- Honorific written on first **typographic** appearance per chapter only.
- Honorific spoken in **full English** by NotebookLM hosts (every spoken occurrence): "Imam Ali, peace be upon him."
- The alias inherits the honorific format ("Imam Ali (AS)" not "Ali").

---

## Memoir-specific override

Memoir chapters that have already shipped retain Asif's voice choices. If a memoir chapter uses the full name in a place that this policy would alias, the memoir choice wins. This policy applies to:
- New memoir chapters where the name appears for the first time
- All podcast chapters and framings (no carve-out)
- All future content

---

## Adding a new alias

1. Verify the full name is in `03-arabic-english-manifest.md` §8 (named works and figures) with the canonical phonetic.
2. Pick the alias per the "How to pick an alias" rules above.
3. Append to the appropriate table here.
4. The next `/podcast` run will automatically apply the alias to the chapter and the framing's Name discipline block.

---

## Authority for challengers

- `podcast-challenger` Loop **J1** reads this file to verify the customize prompt's Name discipline block lists every long name in the chapter with its canonical alias.
- `podcast-challenger` Loop **J2** reads this file to verify the chapter file uses the alias after first mention for every long name in the manifest.
- `journal-challenger` Loop **N1** reads this file when reviewing memoir chapters that introduce a new named figure.

---

## Revision log

- 2026-05-17 — Seeded with ~30 canonical aliases covering Imams, Ghazali/Sufi tradition, hadith collectors, Ismaili figures, modern scholarship.
