# Enrichment Log — Ayyuhal Walad

Per-chapter Phase 0e tracking. Lives here (not inline in the chapter files) because chapter files are uploaded to NotebookLM as-is — any inline metadata would be read literally by the hosts.

Authoring protocol: when enriching a chapter, append/update its entry below with status, citations added, ratio, and any verification notes. Do NOT put this information in the chapter file.

---

## ch01-frame-and-first-counsel.txt

- **Status:** applied (2026-05-16)
- **Last verified:** 2026-05-16 (iter 2 of challenger run)
- **Verified citations:**
  - Quran 39:9, 53:39, 99:7-8, 18:107, 18:110, 7:56 (English: Yusuf Ali)
  - Sahih al-Bukhari, Book 1, Hadith 1 (Umar ibn al-Khattab) — at the intention pivot
  - Nahj al-Balagha Hikam #366 (knowledge calling upon action)
  - Nahj al-Balagha Hikam #145 (vigil without intention)
  - Ghurar al-Hikam — Imam Ali on benefiting from knowledge
  - Holy Du`a Part III reference for parallel pleading
- **Notes:** Unverifiable specific Nasir-i Khusraw chapter citation replaced with a defensible general statement about his recurring `ilm`/`amal` theme across *Wajh-i Din* and *Diwan*.
- **Enrichment ratio:** ~22% (under the 60% cap)
- **Tier coverage:** T2 (Quran), T3 (Bukhari), T4 (Nahj al-Balagha, Ghurar al-Hikam), T5 (Holy Du`a, Nasir-i Khusraw), T6 (Junaid, Hasan al-Basri via Ghazali) — **5 tiers**

## ch02-hatim-eight-benefits.txt

- **Status:** applied (2026-05-16)
- **Last verified:** 2026-05-16 (iter 2 of challenger run)
- **Verified citations:**
  - Quran 79:40-41, 16:96, 49:13, 35:6, 36:60, 11:6, 65:3 (English: Yusuf Ali)
  - Sahih Muslim Hadith 1631 (three things that follow the corpse — Abu Hurayrah) — at Benefit 1
  - Farewell Sermon (Khutbat al-Wada`) excerpt on Taqwa over lineage — at Benefit 4
  - Attributed to Imam Ali (AS): "the most hostile of your enemies is your own self" — at Benefit 6
  - Sunan al-Tirmidhi Hadith 2344 (the birds and Tawakkul — Umar ibn al-Khattab, hasan sahih) — at Benefit 7
  - Nahj al-Balagha Hikam #57 (contentment as treasure) — at chapter close
- **Enrichment ratio:** ~25% (under the 60% cap)
- **Tier coverage:** T2 (Quran), T3 (Sahih Muslim, Tirmidhi, Farewell Sermon), T4 (Nahj al-Balagha + attributed) — **3 tiers**

## ch03-the-path.txt

- **Status:** applied (2026-05-16)
- **Last verified:** 2026-05-16 (iter 2 of challenger run)
- **Verified citations:**
  - Holy Du`a Part II reference (chain of guidance) — at Movement 1
  - Sahih al-Bukhari Hadith 13 / Sahih Muslim Hadith 45 ("none of you believes until…" — Anas ibn Malik) — at Movement 3 (Tasawwuf's horizontal axis)
  - Sunan al-Tirmidhi Hadith 2517 ("tie your camel" — Anas ibn Malik) — at Tawakkul
  - Sahih Muslim Hadith 1905 (the three first thrown into Hell — Abu Hurayrah) — at Ikhlas
- **Enrichment ratio:** ~22% (under the 60% cap)
- **Tier coverage:** T3 (Bukhari, Muslim, Tirmidhi), T5 (Holy Du`a) — **2-3 tiers** (advisory: no direct Imam Ali citation in this chapter; optional addition at Movement 3 or 4)

## ch04-four-cautions.txt

- **Status:** applied (2026-05-16)
- **Last verified:** 2026-05-16 (iter 2 of challenger run)
- **Verified citations:**
  - Quran 2:44, 11:113 (English: Yusuf Ali)
  - Sunan Abu Dawud Hadith 4800 (hasan — Abu Umamah) — at Caution 1
  - Nahj al-Balagha Hikam #133 (Imam Ali, "the world is a place of passage…") — at Caution 4
- **Enrichment ratio:** ~18% (under the 60% cap)
- **Tier coverage:** T2 (Quran), T3 (Abu Dawud), T4 (Nahj al-Balagha) — **3 tiers**

## ch05-method-and-closing-prayer.txt

- **Status:** applied (2026-05-16)
- **Last verified:** 2026-05-16 (iter 2 of challenger run)
- **Verified citations:**
  - Quran 3:185, 21:35, 29:57 (English: Yusuf Ali)
  - Nahj al-Balagha Letter 31 (Imam Ali to Imam Hasan, on the mirror principle) — at Matter 2
  - Structural parallel to the Ismaili Holy Du`a at the closing supplication
- **Enrichment ratio:** ~21% (under the 60% cap)
- **Tier coverage:** T2 (Quran), T4 (Nahj al-Balagha Letter 31), T5 (Holy Du`a structural parallel) — **3 tiers**

---

## Anti-pattern check (book-wide)

- No `[VERIFY CITATION]` markers remain in any chapter.
- No `[CONTEXT NEEDED]` markers remain.
- No fabricated hadith numbers — all hadith from canonical collections (Bukhari, Muslim, Tirmidhi, Abu Dawud, Musnad Ahmad) with named narrators.
- No source-shifting detected.
- No cross-tradition collisions — Sunni / Shia / Ismaili adjacencies are annotated as parallel traditions throughout.
- Quranic translator (Yusuf Ali) named at first verse in each chapter; subsequent verses inherit per the inline convention clause.

## Iteration history (challenger runs)

| Date | Iter | Verdict | Notes |
|---|---|---|---|
| 2026-05-16 | 1 | BLOCKED | 38 em-dashes auto-fixed; 4 P0 A3 (missing Yusuf Ali attribution) flagged |
| 2026-05-16 | 2 | SHIP-WITH-CAUTION | A3 resolved by author; C3 honorific policy remains as P1 (current state: compromise) |
| 2026-05-16 | 3 (planned, after architecture refactor) | TBD | Re-validate under chapter-is-source / episode-is-customize-prompt model |
