# Extraction Notes — Ayyuhal Walad

## Phase 0a

Source: `_system/source/Ayyuhal-Walad.pdf`, 30 pages (page 1 cover, page 2 TOC + translator's note, pages 3–30 body).
Method: `pypdf` text-layer extraction via `python3 extract_pdf.py`. Page boundaries preserved as `<!-- PAGE N -->` markers in `raw-extract.md`.
Result: 1,556 lines, ~13,000 source words. Clean text layer — no OCR fallback needed.

## Phase 0b

`normalized.md` step folded into the per-chapter authoring under Phase 0d. The Irfan Hasan English is dense with translator's parentheticals (extensive bracketed glosses) which were chosen for written reading, not for spoken hosts. The chapter prose modernizes the register, drops the inline gloss-stacking, preserves verbatim Quranic translations (now with Yusuf Ali named), and keeps prophetic and Imam Ali sayings verbatim.

## Phase 0c

Phonetics index built at `_phonetics.md`. All phonetic forms cross-checked against `content/_shared/arabic/03-arabic-english-manifest.md`. New entries proposed for inclusion (none were missing — the manifest covered the full corpus).

## Source-specific spelling decisions

The Irfan Hasan translation uses several spellings that differ from the canonical manifest. The chapter prose uses the manifest's canonical form (per R-NO-ABBREVIATION + manifest authority); the source's spelling is noted here for audit.

| Source spelling | Canonical (manifest) | Action |
|---|---|---|
| Ahya al-Uloom ad-Deen | Ihya Ulum al-Din | Use canonical in all five chapters (gloss "Revival of the Religious Sciences" on first mention per chapter). |
| Shafeeq Balkhi | Shaqiq al-Balkhi (alias: Shaqeeq) | Use canonical alias **Shaqeeq** in ch02. |
| Hatim Ism | Hatim bin Ism al-Asamm (alias: Haatim) | Use **Haatim** in ch02. |
| Zun Noon Misri | Dhu'l-Nun al-Misri (alias: Dhu'l-Nun) | Use **Dhu'l-Nun al-Misri** in ch03 with anti-mangling line in framing. |
| Hasan Busri | Hasan al-Basri | Use **Hasan al-Basri** in ch01, ch04. |
| Sufyan Suri | Sufyan al-Thawri (alias: Sufyan) | Use **Sufyan al-Thawri** on first mention in ch01, **Sufyan** thereafter. |
| Sahah Sitta | Sahih Sitta (canonical) | The source spells *Sahah Sitta*; the canonical is *Sahih Sitta*. Keep canonical form in ch05; framing carries Pronounce line for `Sahih Sitta` only. |
| Ka'aba | Ka'bah | Use **Ka'bah** in ch01. |
| Salaat | Salah | Source spells *Salaat*; canonical is *Salah*. Keep **Salah** in chapter; framing Pronounce line uses canonical. |
| Mureed (disciple) | Mureed (matches) | Use **Mureed / Mureeds** in ch03 (gloss on first use). |

## Source artifacts removed during refinement

The translator inserts long parenthetical explanations after almost every term. These are reading aids for written prose; spoken hosts would stumble. Where the parenthetical carries meaning the listener actually needs, it is paraphrased into the surrounding sentence; where it is redundant, it is dropped. The audit trail: the source PDF and `raw-extract.md` preserve the originals.

Examples of compressed translator parentheticals:
- `Tahajjud (third part of the night)` → kept the parenthetical as gloss on first chapter use only.
- `Mujahadah (intense inner spiritual struggle and exercises)` → glossed once on first mention; later mentions bare.
- `Ahadith (traditions)` → first use kept; later mentions use *hadith* / *sayings* in body prose.

## Translator-bracket markings

The translator notes (cover page 2) that bracketed material is his commentary, not Ghazali's words. In the chapters, the bracketed glosses are folded into the body prose only when load-bearing; otherwise dropped. Nothing the translator inserted is treated as Ghazali's own argument.
