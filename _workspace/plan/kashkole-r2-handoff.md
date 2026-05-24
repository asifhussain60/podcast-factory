# KAHSKOLE Round 2 Topic Retitles — Partial + Handoff Document

**Status:** Round 2 PARTIAL committed (235 of 1,337 topics, covering 9 small binders).
**Branch:** `feature/kashkole-taxonomy`
**Deferred:** 10 remaining binders (1,102 topics) queued for a fresh-context session.

## What this session shipped

Round 2 *partial* now covers these 9 binders fully:

| Binder | English Title | Topics |
|---|---|---|
| 5 | Selected Devotional Poetry | 24 |
| 12 | Lives and Episodes of the Duʿāt and Their Ranks | 7 |
| 16 | A Collection of Selected Supplications | 14 |
| 18 | Inner Realities of the Qurʾānic Prophet Stories | 26 |
| 25 | Daʿāʾim al-Islām: Ṭahāra (Purity) | 42 |
| 27 | Ādāb and Noble Character | 40 |
| 29 | Daʿāʾim al-Islām: Ṣawm (Fasting) | 43 |
| 32 | Al-Ghazālī, Kīmiyāʾ al-Saʿāda | 15 |
| 36 | Islām, Īmān, Iḥsān | 24 |
| **TOTAL** | | **235** |

Output:
- [tools/content_classifier/data/kashkole-r2-decisions.yaml](../../tools/content_classifier/data/kashkole-r2-decisions.yaml) — 235 topic retitles with source Urdu/English + proposed English title + confidence.

Confidence distribution: **227 high / 6 medium / 2 low** — very strong (96.6% high-confidence). The 2 low-confidence titles are sparse-content stubs in the source (b12/c138 "سیرت" and b18/c147 "بسم") which simply name something the source author didn't develop further.

## What's deferred to the next session

10 binders, **1,102 topics**:

| Binder | English Title | Topics | Difficulty |
|---|---|---|---|
| 1 | Sciences of Origin and Return | 156 | High (philosophical core — technical Ismaili terminology) |
| 6 | ʿAlī ibn Abī Ṭālib | 144 | High (mix of Urdu poetry, ḥadīth, sermons) |
| 8 | Taʾwīl of the Divine Words | 138 | High (Arabic ḥadīth/Quran fragments as titles) |
| 19 | Daʿāʾim al-Islām: Wilāya | 87 | Medium |
| 23 | Selected Scholarly Treatises | 214 | Medium-High (Miṣbāḥ, Master and Disciple) |
| 24 | Tawḥīd of the Originator | 79 | High (kalām terminology) |
| 26 | Daʿāʾim al-Islām: Ṣalāt | 75 | Medium |
| 28 | Drafts and Miscellaneous | 75 | Medium (mixed Urdu + English session notes) |
| 34 | Qurʾānic Studies | 84 | Medium (already-English-source) |
| 35 | The Wise Reminder | 18 | Low (already-English-source) |
| **TOTAL** | | **1,102** | |

## How to resume in a fresh session

Open a clean Claude Code session (fresh context budget) and use this resumption prompt:

```
Resume KAHSKOLE Round 2 topic retitling. Continue from
tools/content_classifier/data/kashkole-r2-decisions.yaml.

State:
- 235 retitles already committed (binders 5, 12, 16, 18, 25, 27, 29, 32, 36)
- 10 binders deferred (1, 6, 8, 19, 23, 24, 26, 28, 34, 35) — 1,102 topics
- Approved Round 1 decisions at tools/content_classifier/data/kashkole-r1-decisions.yaml
- Conventions established in _workspace/plan/kashkole-r2-handoff.md

Resume strategy:
1. Read kashkole-r2-decisions.yaml header + _workspace/plan/kashkole-r2-handoff.md.
2. Pull topic data for the 10 deferred binders only (run
   tools/content_classifier/scripts/pull_deferred_topics.py).
3. Generate retitles BINDER BY BINDER in batches: smallest first
   (B35, B19, B24, B26, B28, B6, B34, B8, B1, B23).
4. After each binder, ESTIMATE remaining context budget and either
   continue or commit-and-handoff for the next session.
5. Apply the SAME conventions as the partial batch:
   - Preserve Arabic/Ismaili technical terms with transliteration + English gloss
   - Confidence: high if term + gloss is well-established
   - For mixed Urdu+English-source content (binders 34, 35), refine English
     titles to consistent capitalization + add domain context
   - For Arabic ḥadīth/Quran-fragment titles (binder 8), provide a working
     English summary; do NOT translate the Arabic literally
   - Conservative: do NOT propose merging or restructuring deferred binders
     — that's Round 3 territory after translation
6. Append entries to kashkole-r2-decisions.yaml under the same top-level
   `topic_retitles` list. Set `batch: "round-2-complete"` when finishing
   the last binder. Update `covered_binders` to include all 19.
7. Commit per binder block (one git commit per 1-2 binders), so resume is
   possible at any granularity.
8. NO bundle modification, NO SQL modification. Only the YAML file changes.

Quality bar: the small-binder batch achieved 96.6% high confidence. Match
or exceed that on the deferred binders.
```

## Naming conventions (reference for the resumption session)

These are the conventions applied to the 235 small-binder titles:

**Arabic/Urdu technical terms** — preserve with transliteration + English gloss:
- "عقل اول" → "Al-ʿAql al-Awwal — The First Intellect"
- "نفس کلیۃ" → "Nafs Kulliyya — The Universal Soul"
- "مبدع تعالی" → "Al-Mubdiʿ Taʿālā — The Originator (Most High)"

**Quranic verse references** — give an English-language summary, not a literal translation, of the verse-fragment title:
- "ذالک الکتاب لا ریب فیہ" → "Exegesis of 'That Is the Book; in It There Is No Doubt' (Q2:2)"

**Ḥadīth-fragment titles** — give the well-known English summary plus the Arabic in italics:
- "من عرف نفسہ فقد عرف ربہ" → "Man ʿArafa Nafsahu Faqad ʿArafa Rabbahu — 'Who Knows Himself Knows His Lord' (Hadith)"

**Already-English titles** (Quranic Studies B34, Wise Reminder B35, Ghazali B32, Sunday Sessions in B28):
- Clean up capitalization (TitleCase or sentence-case)
- Add domain context if title is opaque (e.g., "Disciplining The Soul" → "Disciplining the Soul (from al-Ghazālī's Iḥyāʾ)")
- Preserve transliterated Arabic terms with diacritics if appropriate

**Devotional poetry titles** (B5):
- Use the poem's matlaʿ (opening line) transliterated, then a brief English description
- "Madh-E-Abbas Madh-E-Haider Hai" → "Madḥ-e ʿAbbās, Madḥ-e Ḥaydar Hai — Praise of ʿAbbās Is Praise of Ḥaydar (ʿAlī)"

**Confidence levels**:
- `high` (default for ~96%): technical term with established gloss, OR descriptive title with unambiguous translation
- `medium`: interpretive choice in translation (e.g., when "تصور" could mean "imagination" or "conception")
- `low`: sparse source ("بسم", "سیرت" alone) — title is a stub; gloss needs revision after content is reviewed

## Approval

Once the partial batch is reviewed and approved, set `approved_at` in the YAML and commit. The deferred 10 binders are then queued; no Round 2 commitment is final until all 1,337 are done.
