# Abjad numerals — Hisab al-Jummal reference

**Owned by:** no single skill. This file is the canonical shared reference for any letter-count claim, any abjad-encoded passage, and any letter-value calculation across both the podcast and journal skills.

**Read by:** podcast pre-refined-source-mode protocol, podcast Loop N challenger checks, any future journal Arabic-handling that touches abjad values, any per-book scaffolding that resolves cryptic letter sequences (e.g., Master & Disciple Ch-02).

**Write policy:** After creation, this file is **READ-ONLY for both skills**. Updates require explicit operator authorization. The single P4 whitelisted exception in [`_workspace/plan/podcast-plan.yaml`](../../../_workspace/plan/podcast-plan.yaml) (`meta.scope_in_writes_to_shared_exception`) covers the creation event; subsequent writes are forbidden.

---

## 1. What Abjad / Hisab al-Jummal is

**Abjad** (أَبْجَد) is the traditional ordering of the Arabic alphabet by numerical value. Each letter has a fixed integer value, and the system is used for:

- **Hisab al-Jummal** (حِسَاب الجُمَّل, "calculation of total") — summing the numerical values of the letters in a word or phrase to derive a number.
- **Chronograms** — encoding dates and verses by their letter sums.
- **Esoteric / mystical commentary** — Sufi, Ismaili, and other traditions read numerical correspondences between phrases and theological concepts.
- **Cipher sequences** — abbreviated initials (e.g., the seven spheres in Ismaili cosmogony) encoded as letter strings.

Two parallel orderings have coexisted historically:

1. **Mashriqi** (مَشرِقي, "Eastern") — used in the eastern Islamic world (Arabia, Persia, India). This is the variant Master & Disciple, Ja'far ibn Mansūr al-Yaman, Nāṣir-i Khusraw, and most classical Ismaili texts use.
2. **Maghribi** (مَغرِبي, "Western") — used in al-Andalus and the Maghreb. Letters from `ـس` onward differ in value.

**Default for this pipeline:** Mashriqi, unless a book's `_system/source-integrity-notes.md` explicitly flags it as Maghribi-tradition.

---

## 2. Mnemonic phrases

Each variant has a memorization device — eight nonsense words that string the letters in order.

### Mashriqi mnemonic

> أَبْجَدْ هَوَّزْ حُطِّيْ كَلِمَنْ سَعْفَصْ قَرَشَتْ ثَخَذْ ضَظَغْ
>
> `abjad hawwaz ḥuṭṭiyy kalaman saʿfaṣ qarashat thakhadh ḍaẓagh`

Twenty-eight letters, eight groups, ordered by ascending value (1 → 1000).

### Maghribi mnemonic

> أَبْجَدْ هَوَّزْ حُطِّيْ كَلَمَنْ صَعْفَضْ قُرِسَتْ ثَخَذْ ظَغَشْ
>
> `abjad hawwaz ḥuṭṭiyy kalaman ṣaʿfaḍ qurisat thakhadh ẓaghash`

Same first three groups; diverges from group 4 onward.

---

## 3. Mashriqi (Eastern) Abjad table — CANONICAL

The default lookup table. Use unless the source explicitly invokes the Maghribi variant.

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
|   |   |   |   |   |   | غ | ghayn | **1000** |

Total: 28 letters, values 1–1000 (non-contiguous: 1–9, 10–90, 100–1000).

---

## 4. Maghribi (Western) Abjad table — for explicit Maghribi sources only

| Letter | Name | Value | Letter | Name | Value | Letter | Name | Value |
|---|---|---:|---|---|---:|---|---|---:|
| ا | ʾalif | **1** | ي | yāʾ | **10** | ق | qāf | **100** |
| ب | bāʾ | **2** | ك | kāf | **20** | ر | rāʾ | **200** |
| ج | jīm | **3** | ل | lām | **30** | س | sīn | **300** |
| د | dāl | **4** | م | mīm | **40** | ت | tāʾ | **400** |
| ه | hāʾ | **5** | ن | nūn | **50** | ث | thāʾ | **500** |
| و | wāw | **6** | ص | ṣād | **60** | خ | khāʾ | **600** |
| ز | zāy | **7** | ع | ʿayn | **70** | ذ | dhāl | **700** |
| ح | ḥāʾ | **8** | ف | fāʾ | **80** | ظ | ẓāʾ | **800** |
| ط | ṭāʾ | **9** | ض | ḍād | **90** | غ | ghayn | **900** |
|   |   |   |   |   |   | ش | shīn | **1000** |

**Key Mashriqi ↔ Maghribi differences:**
- ش (shīn): Mashriqi 300, Maghribi 1000
- س (sīn): Mashriqi 60, Maghribi 300
- ص (ṣād): Mashriqi 90, Maghribi 60
- ض (ḍād): Mashriqi 800, Maghribi 90
- ظ (ẓāʾ): Mashriqi 900, Maghribi 800
- غ (ghayn): Mashriqi 1000, Maghribi 900

For any letter where the variants disagree, scaffolding MUST name which table was applied.

---

## 5. Counting rules (Hisab al-Jummal practice)

### 5.1 The standard rule

Sum the value of each letter that appears in the word's written form.

### 5.2 Special letters

- **ة (tāʾ marbūṭa)** — Counts as **ه (hāʾ) = 5**, NOT as ت (tāʾ) = 400. The marbūṭa is a closed/feminine form of hāʾ in classical orthography.
- **ى (alif maqṣūra)** — Counts as **ي (yāʾ) = 10** in most calculations, though some traditions count it as ا (ʾalif) = 1. Default to yāʾ unless the source convention specifies otherwise.
- **ء (hamza)** — Carries no value by itself. Its bearer letter (ا / و / ي / ه) contributes its own value.
- **Shadda (ّ)** — A diacritic; does NOT double the letter for counting purposes. The letter is summed ONCE.
- **Sukūn / fatḥa / kasra / ḍamma** — Diacritics carry no value.
- **Tanwīn (ـً / ـٍ / ـٌ)** — The nūn-sound is NOT a separate letter; do not add ن = 50.
- **Definite article ال** — Counted as ا (1) + ل (30) = 31.

### 5.3 Practical algorithm

```
hisab(word) =
  for each letter L in word.normalized():
    + table[L]
```

Where `normalized()` strips diacritics, expands shadda to a single letter, and maps ة→ه, ى→ي per §5.2.

---

## 6. Reference calculations (verified)

The following calculations are canonical references. Any pipeline output that contradicts these is wrong; any framing that uses these MUST match exactly.

| Phrase | Arabic | Letter-by-letter (Mashriqi) | Sum |
|---|---|---|---:|
| Allāh | الله | ا(1) + ل(30) + ل(30) + ه(5) | **66** |
| Basmala (in shorthand abjad usage; full phrase) | بسم الله الرحمن الرحيم | (per classical reckoning) | **786** |
| Muḥammad | محمد | م(40) + ح(8) + م(40) + د(4) | **92** |
| ʿAlī | علي | ع(70) + ل(30) + ي(10) | **110** |
| Lā ilāha illā Allāh (the shahāda) | لا اله الا الله | (per classical reckoning) | **165** |

The basmala value **786** is the most-cited Hisab al-Jummal result in popular Islamic culture (often inscribed at the top of correspondence in lieu of writing the basmala in full); it derives from the full phrase bismillāh al-raḥmān al-raḥīm.

---

## 7. Calculations relevant to Master & Disciple Ch-02 (worked examples)

Per `_workspace/plan/numeric-symbolic-disambiguation-plan.md` §2.3, the following calculations are referenced in the chapter and must be reproducible from this table.

| Phrase | Arabic | Letter-by-letter (Mashriqi) | Sum |
|---|---|---|---:|
| kun ("Be!") | كن | ك(20) + ن(50) | **70** |
| fa-yakun ("so it came to be") | فيكون | ف(80) + ي(10) + ك(20) + و(6) + ن(50) | **166** |
| kun fayakun (joined) | كن فيكون | 70 + 166 | **236** |
| al-irāda (the will) | الإرادة | ا(1) + ل(30) + ا(1) + ر(200) + ا(1) + د(4) + ه(5)* | **242** |
| al-amr (the command) | الأمر | ا(1) + ل(30) + ا(1) + م(40) + ر(200) | **272** |
| al-qawl (the speech) | القول | ا(1) + ل(30) + ق(100) + و(6) + ل(30) | **167** |
| Sum of the creative triad | irāda + amr + qawl | 242 + 272 + 167 | **681** |

*Note on al-irāda: ة (tāʾ marbūṭa) at the end counts as ه = 5 per §5.2. The standard rendering includes the alif maqṣūra in al-irādah's morphology depending on script convention; the figure above uses the most commonly attested orthography for the chapter's source register.

These figures are **referenced**, not asserted from the source text itself. The chapter's own claims about letter **counts** (not values) are separately validated in the disambiguation plan's §1.3.

---

## 8. When to use Abjad in the pipeline

### 8.1 Triggers (the chapter contains one of these)

1. An explicit letter-count claim ("the X letters of Y") — verify by counting.
2. An explicit numerical value claim about a word ("the value of Y is N") — verify with Hisab al-Jummal.
3. An abjad-encoded sequence (`(ب ج لا د م لہ م)` or similar bracketed letter strings) — these are CIPHERS; decode only if the source provides an authoritative key, otherwise flag NEEDS HUMAN REVIEW per challenger Loop N (`numeric-symbolic-disambiguation.md`).
4. A chronogram (a verse whose letter-sum encodes a Hijri date) — decode if a known chronogram pattern; flag otherwise.

### 8.2 Look-up order for any abjad question

```
1. THIS FILE              — canonical table + worked examples
2. _workspace/plan/numeric-symbolic-disambiguation-plan.md  — worked-example source
3. content/podcast/.skill/handbook/numeric-symbolic-disambiguation.md  — general protocol
4. Critical-edition / scholarly source — for cipher decoding, named tradition consensus
```

**Never invent a decoding.** If a letter sequence has no authoritative source, the only correct output is `NEEDS HUMAN REVIEW` annotated in the per-chapter scaffolding.

---

## 9. Cross-references

- `_workspace/plan/numeric-symbolic-disambiguation-plan.md` — the design document this file derives from.
- `content/podcast/.skill/handbook/numeric-symbolic-disambiguation.md` — the general protocol that USES this table.
- `_workspace/plan/podcast-plan.yaml` P4 — the phase that wires Loop N enforcement.
- `.github/agents/podcast-challenger.agent.md` Loop N — the runtime check that consults this file.

## 10. Provenance

- **Mashriqi table:** standard classical reference (consistent across Lane's lexicon, Edward Lane's *Arabic-English Lexicon* (1863), and the Encyclopaedia of Islam abjad entry).
- **Maghribi table:** Andalusian / Maghrebi tradition; differs from Mashriqi in the placement of ش, س, ص, ض, ظ, غ per the divergent mnemonic.
- **Hisab al-Jummal practice (counting rules):** standard across Sunni, Shia, and Ismaili scholarly traditions; the special-letter rules (§5.2) reflect majority practice.
- **Reference calculations (§6):** verified against multiple sources including the Encyclopaedia of Islam, classical Arabic primers, and the Wikipedia "Abjad numerals" entry's worked examples.
- **Ch-02 worked examples (§7):** derived directly from `_workspace/plan/numeric-symbolic-disambiguation-plan.md` §2.3, which sources them from the Master & Disciple chapter.

This file's creation is the single P4-whitelisted write into `content/_shared/`. After creation, READ-ONLY for both skills.
