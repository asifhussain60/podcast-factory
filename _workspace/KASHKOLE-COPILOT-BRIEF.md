# KASHKOLE — Complete Project Brief for GitHub Copilot
*Self-contained context for independent work. Last updated: 2026-05-26.*

---

## 1. What KASHKOLE Is

**KASHKOLE** (also written KAHSKOLE in code — historical typo preserved throughout for compatibility) is a 122-chapter Ismaili scholarly compendium held in a SQL Server 2008 database. It was compiled by a living Ismaili dāʿī and consists of notes, study sessions, taʾwīl (esoteric Quranic exegesis), theological treatises, du'āʾ collections, and devotional poetry gathered across decades.

The content is organised into **19 binders** (subject collections), each containing multiple **chapters** (Urdu: *faṣl* / *bāb*), each chapter broken into **sections/topics** (Urdu: *mawḍūʿ*). The primary language is **Urdu** written right-to-left, with heavy embedded **Arabic** for Quranic quotations, hadith, and theological terminology.

The goal: transform this private Arabic/Urdu corpus into scholarship-quality English content suitable for podcast production on the existing `podcast-factory` pipeline.

---

## 2. Repository Location

Everything lives under:
```
/Users/ahmac/Code/podcast-factory/     ← repo root (git)
```

Key sub-paths:
```
_workspace/kashkole-ksessions/          ← all kashkole-specific work
  KAHSKOLE.sql                          ← full SQL Server schema + data export
  KSESSIONS.sql                         ← ksessions schema
  extracted/kashkole/                   ← per-chapter output tree (see §5)
  extracted/ksessions/                  ← separate ksessions content (parallel track)
  .venv/                                ← Python 3.14 venv (has anthropic, azure-cognitiveservices-translation)

tools/                                  ← first-party Python tooling
  source_extractor/                     ← DB → Markdown extraction
  content_translator/                   ← Phase 1 (translate) + Phase 2 (adapt)
  content_challenger/                   ← Phase 3 (challenge / QA)
  content_reviewer/                     ← optional human review assist
  content_classifier/                   ← genre/style classifier

_workspace/plan/_drivers/               ← batch automation scripts
  kashkole_translate_all.py             ← Phase 1 driver
  kashkole_adapt_all.py                 ← Phase 2 driver  ← CURRENT WORK
  kashkole_challenge_all.py             ← Phase 3 driver
  kashkole_pipeline_all.py             ← chains Phase 2 → Phase 3
  kashkole_gate_report.py              ← pre-Phase 4 gate summary
  kashkole_run_remaining.py            ← utility: run only unadapted chapters
  commit_binders.sh                    ← git commit helper

_workspace/plan/                        ← ledgers, scope, reports
  kashkole-translation-cost-ledger.jsonl
  kashkole-adapt-cost-ledger.jsonl
  kashkole-challenge-cost-ledger.jsonl  ← not yet populated
  kashkole-podcast-scope.yaml          ← binder in/out decision
  kashkole-adapt-failures.log
  kashkole-translation-failures.log
```

---

## 3. Database Schema (Abbreviated)

The SQL Server database `KASHKOLE` has this hierarchy:

```
Binders (19 rows)
  BinderID, BinderName (Urdu), SortKey

BinderChapters (122 rows)
  BinderChapterID, BinderID → Binders, ChapterID → Chapters
  BinderChapterOrder, BinderChapterSort

Chapters (122 unique chapters)
  ChapterID, ChapterName (Urdu)

ChapterTopics (N per chapter)
  TopicID, ChapterID → Chapters, TopicSort, TopicLabel

TopicDataUnicode (per topic)
  TopicID → ChapterTopics, DataUnicode (HTML blob, Urdu RTL text)
```

Additionally:
- `HQAyats` — Quran corpus (surah/ayat → Arabic text + English translation)
- `TopicAyats` — curated per-topic Quran citation links (surah, start ayat, end ayat)

The source extractor queries these tables, converts HTML → Markdown, and renders Quran widget blocks into clean `⟪quran S:A⟫` markers.

The `KSESSIONS.sql` database follows the same pattern but for a separate "ksessions" (K-sessions) content track.

---

## 4. Three-Phase Pipeline

### Phase 1 — Translation (✅ COMPLETE)

**Tool:** `tools/content_translator/stages/translate.py`  
**CLI:** `python -m tools.content_translator translate kashkole --binder N --chapter N`  
**Driver:** `_workspace/plan/_drivers/kashkole_translate_all.py`  
**Engine:** Azure Translator v3 (`azure-cognitiveservices-translation`)  
**Stage transition:** `extracted` → `translated`  

What it does:
- Reads `_system/source/text/raw-extract.md` (Urdu HTML → Markdown, produced by source extractor)
- Posts each section to Azure Translate (Urdu → English)
- Writes `_system/source/text/raw-extract.en.md` — machine translation, section-by-section
- Updates `bundle.yml` with `stage: translated`, translation metadata, and Azure cost

Cost: **$38.37 USD total** across all 122 chapters (~$0.31/chapter average).  
~33 chapters were English-origin passthroughs (zero cost); ~89 were machine-translated.

### Phase 2 — Adaptation (🟡 IN PROGRESS — 119/122 complete)

**Tool:** `tools/content_translator/stages/adapt_auto.py`  
**CLI:** `python -m tools.content_translator adapt-auto kashkole --binder N --chapter N`  
**Driver:** `_workspace/plan/_drivers/kashkole_adapt_all.py`  
**Engine:** `claude-haiku-4-5-20251001` via `claude -p` (Max subscription — $0.00 API cost)  
**Stage transition:** `translated` → `adapted`  

What it does:
- Reads `raw-extract.en.md` (machine translation) + `raw-extract.md` (original Urdu, for Arabic term anchoring)
- Calls `claude -p` with a structured prompt: transform raw Azure output into IIS/Daftary/Walker/Hunzai scholarly English
- Adds `## Section Title` headings after each `<!-- section N -->` marker
- On first occurrence of Arabic/Urdu theological terms: adds transliteration + gloss (e.g., `ʿaql (intellect)`)
- Adds 0–3 augmentations per section from Fatimid-era primary sources (`[^cite-N]` footnotes)
- Preserves all `⟪ar:…⟫`, `⟪quran S:A⟫` markers verbatim
- Chunks large chapters (>25KB) into multiple sequential `claude -p` calls (each chunk = new PID)
- Writes `adapted-extract.en.md` + `adaptation-citations.jsonl`
- Updates `bundle.yml`: `stage: adapted`, adaptation metadata

**Citation JSONL schema per entry:**
```json
{
  "cite_id": "cite-1",
  "section_id": 1382,
  "section_position": 1,
  "excerpt": "Short description of the cited claim",
  "source_work": "Daʿaʾim al-Islam",
  "source_author": "al-Qadi al-Nuʿman",
  "source_authority": "Fatimid jurist",
  "source_location_hint": "Kitab al-Janaʾiz",
  "confidence": "high",
  "training_grounded": true
}
```

**Style target:** IIS (Institute of Ismaili Studies) / Farhad Daftary / Paul Walker / W. Ivanow / S.J. Hunzai scholarly register. Formal, precise, no colloquialisms, Islamic terms transliterated in ALA-LC style.

**Chunk handling:** `MAX_CHUNK_BYTES = 25,000`. Chapters up to 565KB are split into 15–30 sequential chunks. Each chunk processes its batch of sections, then the next chunk picks up where the previous ended. The outer driver (`kashkole_adapt_all.py`) has `timeout=None` (fix applied 2026-05-26) — per-chunk timeout of 1800s is enforced inside `adapt_auto.py`.

**Cost:** $0.00 — all calls go through Max subscription `claude -p`.

### Phase 3 — Challenge / QA (⏳ PENDING — 0/122 complete)

**Tool:** `tools/content_challenger/kashkole/challenge_auto.py`  
**CLI:** `python -m tools.content_translator challenge kashkole --binder N --chapter N`  
**Driver:** `_workspace/plan/_drivers/kashkole_challenge_all.py`  
**Stage transition:** `adapted` → `challenged`  

Runs 8 deterministic validators (V1–V8) plus optional LLM quality review:

| Check | Severity | Description |
|---|---|---|
| V1 | P0 | Section markers `<!-- section N (id=…) -->` present verbatim |
| V2 | P0/P1 | `⟪ar:…⟫` Arabic markers preserved (P0 if >50% lost, P1 otherwise) |
| V3 | P0 | `⟪quran S:A⟫` markers preserved |
| V4 | P1 | `## Heading` present after each section marker |
| V5 | P0 | `adaptation-citations.jsonl` is valid JSON-L |
| V6 | P1 | Citations reference allowlisted works only (known Fatimid/Ismaili corpus) |
| V7 | P1 | Length sanity: adapted text >40% of source length |
| V8 | P1 | No raw machine-translation artifacts (bracket patterns, mis-tagged nouns, etc.) |

Writes `kashkole-challenger-report.md` alongside `adapted-extract.en.md` in each chapter's text directory.

### Phase 4 — Podcast Intake (⏳ BLOCKED ON GATE)

After Phase 3 completes, 80 chapters from 13 binders are ingested into the main `podcast-factory` pipeline via `scripts/podcast/intake_book.py --from-bundle`. The remaining 42 chapters (6 binders) are excluded from podcast intake — see §8.

---

## 5. Per-Chapter File Structure

Every chapter lives at:
```
_workspace/kashkole-ksessions/extracted/kashkole/
  {NN}-{binder-slug}/
    {NN}-{chapter-slug}/
      bundle.yml                          ← pipeline manifest (schema v1)
      _system/
        source/
          {chapter-slug}.html             ← raw HTML from DB (original)
          text/
            raw-extract.md                ← Urdu markdown (source_extractor output)
                                            NOTE: some chapters have no Unicode DB
                                            content — raw-extract.md absent; only HTML
            raw-extract.en.md             ← Azure machine translation (Phase 1)
            adapted-extract.en.md         ← LLM-polished scholarly English (Phase 2)
            adaptation-citations.jsonl    ← per-section citation ledger (Phase 2)
            kashkole-challenger-report.md ← QA report (Phase 3, when done)
            _extraction-notes.md          ← notes on OCR quality, skips, anomalies
```

### bundle.yml Schema (key fields)

```yaml
bundle_schema_version: 1
source: kashkole
source_language: ur
stage: adapted        # extracted | translated | adapted | challenged
shelf:
  kind: binder
  id: 28              # binder ID in KASHKOLE DB
  name: مسودے         # Urdu binder name
  slug: musawwadat
book:
  kind: chapter
  id: 115             # chapter ID in KASHKOLE DB
  name: "[مسودۃ] مسودے"
  slug: x8114-musawwadat
pipeline_hints:
  suggested_slug: kashkole-musawwadat-x8114-musawwadat
  suggested_category: lectures
counts:
  sections: 16
  sections_with_content: 16
  inline_images: 2
  curated_citation_refs: 5
sections:
  kind: topic
  items:
    - position: 1
      id: 1382
      label: مسودۃ            # Urdu section label
      name_en: Draft           # English label (extracted from DB)
      has_content: true
      image_count_inline: 0
      curated_citations:
        - { surah: 2, ayat: 24 }
finalize:
  inline_citations_resolved: 3
  inline_citation_refs: [...]
  images: [...]
review:                        # content reviewer pass results
  ...
translation:
  engine: azure-translator-v3
  completed_at: "..."
  sections_translated: 7
  char_count: 95858
  azure_cost_usd: 0.958580
adaptation:
  engine: claude-haiku-4-5-20251001
  completed_at: "..."
  adapt_cost_usd: 0.000000
```

---

## 6. Urdu Source: What raw-extract.md Contains

The source extractor (`tools/source_extractor/adapters/kashkole.py`) does:
1. Queries `TopicDataUnicode` HTML blobs per section
2. Converts HTML → Markdown via `html_to_md()` — preserves RTL Urdu text
3. Replaces in-DB Quran widget tables with `⟪quran S:A⟫` markers
4. Appends curated `TopicAyats` citations as a footer per section
5. Some chapters have no Unicode content in `TopicDataUnicode` (only images/PDFs) — those sections get `*(no Unicode content — see _extraction-notes.md)*`

The `raw-extract.md` is right-to-left Urdu with embedded Arabic phrases. Headers follow `<!-- section N (id=ID, raw_sort=N): Section Label -->` format.

---

## 7. Current Corpus State (2026-05-26)

| Stage | Count | Details |
|---|---|---|
| `challenged` | **93** | Phase 2+3 complete; ready for Phase 4 gate |
| `adapted` | **26** | Phase 2 complete; Phase 3 pending |
| `translated` | **3** | Phase 2 interrupted (b8/ch-08-qurani-ayaat-ki-taweel, b23/ch60, b23/ch63) |
| **Total** | **122** | Across 19 binders |

**Total corpus size:**
- `raw-extract.en.md` (all chapters): ~10.6 MB
- `adapted-extract.en.md` (119 chapters): ~10.5 MB
- Adaptation citations: 119 JSONL files

**Cost summary:**
- Phase 1 (Azure Translate): **$38.37 USD**
- Phase 2 (claude -p Max): **$0.00 USD**
- Phase 3: pending

---

## 8. Binders — Full Inventory

19 binders, processing order (smallest first to build momentum):

| Binder ID | English Name | Urdu Name | Chapters | Podcast Scope |
|---|---|---|---|---|
| 35 | The Wise Reminder | The Wise Reminder | 2 | ✅ In scope |
| 32 | Al-Ghazali — Kimiya | غزالی - کیمیائی السعادۃ | 2 | ✅ In scope |
| 36 | Islam Iman Ihsan | ISLAM IMAN IHSAN | 3 | ✅ In scope |
| 12 | Duʿāt Lives | دعات اور مناصیب کی سیرت و واقعات | 3 | ❌ Excluded |
| 5 | Devotional Poetry | منتخب اشعار | 3 | ❌ Excluded |
| 16 | Selected Duʿāʾs | منتخب دعاؤں کا مجموعۃ | 3 | ❌ Excluded |
| 18 | Prophet Stories | نبی کی کہانیاں | varies | ✅ In scope |
| 25 | Daʿāʾim: Ṭahāra | دعائم الاسلام - طہارت | 5 | ✅ In scope |
| 27 | Ādāb wa-Akhlāq | آداب و اخلاق حسنہ | 6 | ✅ In scope |
| 29 | Daʿāʾim: Ṣawm | دعائم الاسلام - صوم | 4 | ✅ In scope |
| 1 | Sciences of Origin/Return | علوم مبدأ و معاد | 12 | ✅ In scope |
| 24 | Tawḥīd | توحید مبدئ تعالی | 7 | ✅ In scope |
| 26 | Daʿāʾim: Ṣalāt | دعائم الاسلام - صلوات | 8 | ✅ In scope |
| 19 | Daʿāʾim: Wilāya | دعائم الاسلام - ولایۃ | 7 | ✅ In scope |
| 34 | Quranic Studies | Quranic Studies | 14 | ❌ Excluded |
| 28 | Drafts | مسودے | 10 | ❌ Excluded |
| 6 | Imam ʿAlī | امام علی ابن ابی طالب | 9 | ❌ Excluded |
| 8 | Taʾwīl of Divine Words | کلمات ربانی کی تاویلات | 8 | ✅ In scope |
| 23 | Selected Scholarly Treatises | منتخب علمی مضامین | 11 | ✅ In scope |

**Exclusion reasons:** Poetry (b5), duʿāʾ/prayer collections (b16), biographical records (b12), working drafts (b28), Quranic Studies already has dedicated treatment (b34), Imam ʿAlī content being handled separately (b6).

**Scope file:** `_workspace/plan/kashkole-podcast-scope.yaml`

---

## 9. How to Run Each Phase

### Prerequisites
All commands must use the kashkole venv Python:
```bash
VENV=/Users/ahmac/Code/podcast-factory/_workspace/kashkole-ksessions/.venv/bin/python
```

### Phase 1 — Translate
```bash
# One chapter
$VENV -m tools.content_translator translate kashkole --binder 35 --chapter 100

# All chapters (batch, idempotent)
nohup $VENV _workspace/plan/_drivers/kashkole_translate_all.py >> /tmp/kashkole-translate.log 2>&1 &

# Dry run
$VENV _workspace/plan/_drivers/kashkole_translate_all.py --dry-run

# Single binder
$VENV _workspace/plan/_drivers/kashkole_translate_all.py --binder 35
```

### Phase 2 — Adapt
```bash
# One chapter
$VENV -m tools.content_translator adapt-auto kashkole --binder 35 --chapter 100

# All chapters (batch, idempotent — resumes from where it stopped)
nohup $VENV _workspace/plan/_drivers/kashkole_adapt_all.py >> /tmp/kashkole-adapt-full.log 2>&1 &

# Single binder only
$VENV _workspace/plan/_drivers/kashkole_adapt_all.py --binder 8
```

### Phase 3 — Challenge
```bash
# One chapter
$VENV -m tools.content_translator challenge kashkole --binder 35 --chapter 100

# All chapters
nohup $VENV _workspace/plan/_drivers/kashkole_challenge_all.py >> /tmp/kashkole-challenge.log 2>&1 &

# Warn-only mode (don't block on P1 findings)
$VENV _workspace/plan/_drivers/kashkole_challenge_all.py --warn-only
```

### Status check
```bash
# Stage counts
$VENV _workspace/plan/_drivers/kashkole_pipeline_all.py --status

# Full gate report (after Phase 3 completes)
$VENV _workspace/plan/_drivers/kashkole_gate_report.py --out _workspace/plan/kashkole-gate-report.md

# Quick stage count from filesystem
find _workspace/kashkole-ksessions/extracted/kashkole -name "bundle.yml" | \
  xargs grep "^stage:" | awk -F': ' '{print $2}' | sort | uniq -c
```

---

## 10. Key Code Patterns

### Reading a chapter's bundle.yml
```python
from pathlib import Path
import yaml

bundle_path = Path("_workspace/kashkole-ksessions/extracted/kashkole/01-musawwadat/01-x8114-musawwadat/bundle.yml")
bundle = yaml.safe_load(bundle_path.read_text())
stage = bundle["stage"]          # "adapted", "challenged", etc.
binder_id = bundle["shelf"]["id"]
chapter_id = bundle["book"]["id"]
```

### Querying the KASHKOLE database
```python
from tools.source_extractor.db import query_json

# Get all chapters in binder 8
rows = query_json("KASHKOLE", """
    SELECT bc.ChapterID AS id, c.ChapterName AS name
    FROM BinderChapters bc
    JOIN Chapters c ON c.ChapterID = bc.ChapterID
    WHERE bc.BinderID = 8
    ORDER BY bc.BinderChapterOrder
    FOR JSON PATH;
""")
```

### Running adapt-auto programmatically
```python
import subprocess
result = subprocess.run(
    [str(VENV), "-m", "tools.content_translator", "adapt-auto",
     "kashkole", "--binder", "8", "--chapter", "132"],
    capture_output=True, text=True, cwd=REPO, timeout=None
)
```

### Section marker format in all text files
```
<!-- section 1 (id=1382, raw_sort=-1): مسودۃ -->
[Urdu or English content follows]

<!-- section 2 (id=3539, raw_sort=1): مولانا معد -->
[content]
```

### Arabic/Urdu inline marker format
```
⟪ar:لزمہ ولم یفارقہ⟫     ← Arabic phrase inline
⟪quran 2:24-26⟫            ← Quran reference widget
```

---

## 11. Text Quality Standards

The `adapted-extract.en.md` must conform to:

1. **IIS scholarly register** — Institute of Ismaili Studies house style. Formal, no contractions, no colloquialisms.
2. **ALA-LC transliteration** — Standard Library of Congress Arabic/Urdu romanization: ʿayn (ʿ), hamza (ʾ), macrons for long vowels (ā, ī, ū), dots for emphatic consonants (ḍ, ṭ, ẓ, ṣ).
3. **First-occurrence glossing** — Each Arabic/Urdu theological term gets transliteration + gloss on first occurrence only, then bare transliteration thereafter. E.g., *ʿaql* (intellect), *dāʿī* (summoner/missionary), *taʾwīl* (esoteric interpretation), *Nāṭiq* (the Speaking Imam).
4. **Citation augmentation** — 0–3 per section, using only works from the Fatimid-Ismaili canon: *Daʿāʾim al-Islām*, *Asās al-Taʾwīl*, *Rāḥat al-ʿAql*, *Kitāb al-ʿĀlim wa-l-Ghulām*, *Nahj al-Balāgha*, *Ikhwān al-Ṣafāʾ Rasāʾil*, *Kanz al-Walad*, *al-Yanābīʿ*, *al-Risāla al-Mudhhiba*, *Wajh al-Dīn*, etc.
5. **Section structure** — Every `<!-- section N -->` marker must be followed immediately by a `## Section Title` heading.
6. **Marker preservation** — All `⟪ar:…⟫` and `⟪quran S:A⟫` markers must pass through verbatim.

---

## 12. Git / Branch State

```
Branch: develop (current, merged 2026-05-26)
Remote: https://github.com/asifhussain60/podcast-factory.git

Recent relevant commits:
  33ebda43  feat(kashkole): merge feature/kashkole-translation → develop
  03ff35ed  feat(kashkole-adapt): binder 8 partial — 5 chapters adapted
  26bd97b6  feat(kashkole-adapt): binder 6 — Imam ʿAlī (2 chapters adapted)
  99ce8566  fix(kashkole-adapt): remove 7200s outer timeout
```

All KASHKOLE work is on `develop`. The `feature/kashkole-translation` branch has been merged.

---

## 13. What Remains To Be Done

### Immediate (resume adaptation)
Three chapters are stuck at `translated` — Phase 2 was interrupted:

| Chapter | Binder | Binder Name | Location |
|---|---|---|---|
| ch60 | 23 | Selected Scholarly Treatises | `08-muntakhab-ilmi-mazameen/06-risala-hikmat-al-mawt/` |
| ch63 | 23 | Selected Scholarly Treatises | `08-muntakhab-ilmi-mazameen/01-zaroori-maloomat/` |
| ~ch(qurani-ayaat)~ | 8 | Taʾwīl of Divine Words | `10-kalimat-rabbani-ki-taweelat/08-qurani-ayaat-ki-taweel/` |

**To resume:** 
```bash
nohup /Users/ahmac/Code/podcast-factory/_workspace/kashkole-ksessions/.venv/bin/python \
  /Users/ahmac/Code/podcast-factory/_workspace/plan/_drivers/kashkole_adapt_all.py \
  >> /tmp/kashkole-adapt-full.log 2>&1 &
```
The driver is idempotent — it skips all 119 already-adapted chapters and resumes from the 3 remaining.

### Phase 3 — Challenge all 122 chapters
```bash
nohup /Users/ahmac/Code/podcast-factory/_workspace/kashkole-ksessions/.venv/bin/python \
  /Users/ahmac/Code/podcast-factory/_workspace/plan/_drivers/kashkole_challenge_all.py \
  >> /tmp/kashkole-challenge.log 2>&1 &
```

### Gate review (manual)
After Phase 3, run:
```bash
python _workspace/plan/_drivers/kashkole_gate_report.py \
  --out _workspace/plan/kashkole-gate-report.md
```
Then open `kashkole-gate-report.md` and review. P0 failures block intake; P1 warnings are advisory.

### Phase 4 — Podcast intake (80 chapters, 13 binders)
For each in-scope binder, run:
```bash
python scripts/podcast/intake_book.py --from-bundle \
  _workspace/kashkole-ksessions/extracted/kashkole/{shelf}/{chapter}/bundle.yml
```
This creates a new `book/<slug>` branch and copies the adapted content into `content/drafts/<slug>/`.

---

## 14. Bilingual Reader Integration

A bilingual reader page was built (commit `b9e43c5`) at:
```
podcast-reader/src/pages/kashkole/[shelf]/[book].astro
```

It shows English and Urdu side-by-side. It prefers `adapted-extract.en.md` (Phase 2) with badge "adapted · phase 2", and falls back to `raw-extract.en.md` (Phase 1) with badge "machine translation · phase 1".

---

## 15. ksessions — Parallel Track

`extracted/ksessions/` holds content from the `KSESSIONS` database — a separate but related scholarly compendium. So far only one chapter has been extracted:
```
ksessions/10-master-and-the-disciple/01-true-sources-of-knowledge/
```

This track uses the same pipeline tools and bundle.yml schema. It is a lower priority than the main KASHKOLE corpus.

---

## 16. Environment and Dependencies

```bash
# Python venv (must use for all tool invocations)
_workspace/kashkole-ksessions/.venv/bin/python   # Python 3.14.5

# Key packages in venv:
#   anthropic>=0.104    (for claude -p calls in adapt_auto.py)
#   azure-cognitiveservices-translation   (Phase 1)
#   PyYAML, beautifulsoup4, lxml, pyodbc  (extraction)

# Claude CLI (claude -p, from Max subscription)
which claude    # /usr/local/bin/claude or similar
claude --version

# Azure credentials (Phase 1 only)
# Stored in macOS keychain:
#   security find-generic-password -s azure-translator-key   (existence check)
# Environment variable: AZURE_TRANSLATOR_KEY

# SQL Server connection (read-only, for source extraction)
# ODBC driver: FreeTDS or ODBC Driver 18 for SQL Server
# Connection string: uses pyodbc
# Server: localhost (SQL Server instance on local machine)
# Databases: KASHKOLE, KSESSIONS
```

---

## 17. Copilot Quick Reference

**Most common tasks and commands:**

| Task | Command |
|---|---|
| Check progress | `find _workspace/kashkole-ksessions/extracted/kashkole -name "bundle.yml" \| xargs grep "^stage:" \| awk -F': ' '{print $2}' \| sort \| uniq -c` |
| Resume adapt | `nohup {VENV} _workspace/plan/_drivers/kashkole_adapt_all.py >> /tmp/kashkole-adapt-full.log 2>&1 &` |
| Run challenge | `nohup {VENV} _workspace/plan/_drivers/kashkole_challenge_all.py >> /tmp/kashkole-challenge.log 2>&1 &` |
| Single chapter adapt | `{VENV} -m tools.content_translator adapt-auto kashkole --binder N --chapter N` |
| Single chapter challenge | `{VENV} -m tools.content_translator challenge kashkole --binder N --chapter N` |
| Gate report | `{VENV} _workspace/plan/_drivers/kashkole_gate_report.py` |
| Check failures | `cat _workspace/plan/kashkole-adapt-failures.log` |
| Commit adapted work | `git add _workspace/kashkole-ksessions/extracted/kashkole/ _workspace/plan/kashkole-adapt-cost-ledger.jsonl && git commit -m "feat(kashkole-adapt): ..."` |

Where `{VENV}` = `/Users/ahmac/Code/podcast-factory/_workspace/kashkole-ksessions/.venv/bin/python`

**Files to read for deeper understanding:**
- `tools/content_translator/stages/adapt_auto.py` — full adaptation logic
- `tools/content_translator/stages/translate.py` — Phase 1 translation logic  
- `tools/content_challenger/kashkole/validator.py` — V1–V8 validator checks
- `tools/source_extractor/adapters/kashkole.py` — DB extraction logic
- `_workspace/plan/_drivers/kashkole_adapt_all.py` — batch driver with binder order
- `_workspace/plan/kashkole-podcast-scope.yaml` — in/out binder decisions
