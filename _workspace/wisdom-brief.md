# KASHKOLE — Complete Project Brief for GitHub Copilot
*Self-contained context for independent work. Last updated: 2026-05-26. §18 added: intelligence pipeline integration design.*

---

## 1. What KASHKOLE Is

**KASHKOLE** (also written KAHSKOLE in code — historical typo preserved throughout for compatibility) is a 122-chapter Ismaili scholarly compendium held in a SQL Server 2008 database. It was compiled by a living Ismaili dāʿī and consists of notes, study sessions, taʾwīl (esoteric Quranic exegesis), theological treatises, du'āʾ collections, and devotional poetry gathered across decades.

The content is organised into **19 binders** (subject collections), each containing multiple **chapters** (Urdu: *faṣl* / *bāb*), each chapter broken into **sections/topics** (Urdu: *mawḍūʿ*). The primary language is **Urdu** written right-to-left, with heavy embedded **Arabic** for Quranic quotations, hadith, and theological terminology.

The primary goal (revised 2026-05-26): feed this corpus into the podcast-factory's **intelligence pipeline** as a doctrinal knowledge base that augments future book podcast productions. Kashkole is not being produced as a podcast series itself — it is the doctrinal substrate that makes every future book smarter. A secondary goal (future phase) is podcast production from select Kashkole binders.

---

## 2. Repository Location

Everything lives under:
```
/Users/asifhussain/PROJECTS/podcast-factory/     ← repo root (git)
```

Key sub-paths:
```
_workspace/wisdom-corpus/          ← all wisdom-specific work
  KAHSKOLE.sql                          ← full SQL Server schema + data export
  KSESSIONS.sql                         ← ksessions schema
  extracted/wisdom/                   ← per-chapter output tree (see §5)
  extracted/ksessions/                  ← separate ksessions content (parallel track)
  .venv/                                ← Python 3.14 venv (has anthropic, azure-cognitiveservices-translation)

tools/                                  ← first-party Python tooling
  source_extractor/                     ← DB → Markdown extraction
  content_translator/                   ← Phase 1 (translate) + Phase 2 (adapt)
  content_challenger/                   ← Phase 3 (challenge / QA)
  content_reviewer/                     ← optional human review assist
  content_classifier/                   ← genre/style classifier

_workspace/plan/_drivers/               ← batch automation scripts
  wisdom_translate_all.py             ← Phase 1 driver
  wisdom_adapt_all.py                 ← Phase 2 driver  ← CURRENT WORK
  wisdom_challenge_all.py             ← Phase 3 driver
  wisdom_pipeline_all.py             ← chains Phase 2 → Phase 3
  wisdom_gate_report.py              ← pre-Phase 4 gate summary
  wisdom_run_remaining.py            ← utility: run only unadapted chapters
  commit_binders.sh                    ← git commit helper

_workspace/plan/                        ← ledgers, scope, reports
  wisdom-translation-cost-ledger.jsonl
  wisdom-adapt-cost-ledger.jsonl
  wisdom-challenge-cost-ledger.jsonl  ← not yet populated
  wisdom-podcast-scope.yaml          ← binder in/out decision
  wisdom-adapt-failures.log
  wisdom-translation-failures.log
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
**CLI:** `python -m tools.content_translator translate wisdom --binder N --chapter N`  
**Driver:** `_workspace/plan/_drivers/wisdom_translate_all.py`  
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
**CLI:** `python -m tools.content_translator adapt-auto wisdom --binder N --chapter N`  
**Driver:** `_workspace/plan/_drivers/wisdom_adapt_all.py`  
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

**Chunk handling:** `MAX_CHUNK_BYTES = 25,000`. Chapters up to 565KB are split into 15–30 sequential chunks. Each chunk processes its batch of sections, then the next chunk picks up where the previous ended. The outer driver (`wisdom_adapt_all.py`) has `timeout=None` (fix applied 2026-05-26) — per-chunk timeout of 1800s is enforced inside `adapt_auto.py`.

**Cost:** $0.00 — all calls go through Max subscription `claude -p`.

### Phase 3 — Challenge / QA (⏳ PENDING — 0/122 complete)

**Tool:** `tools/content_challenger/wisdom/challenge_auto.py`  
**CLI:** `python -m tools.content_translator challenge wisdom --binder N --chapter N`  
**Driver:** `_workspace/plan/_drivers/wisdom_challenge_all.py`  
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

Writes `wisdom-challenger-report.md` alongside `adapted-extract.en.md` in each chapter's text directory.

### Phase 4 — Podcast Intake (⏳ BLOCKED ON GATE)

After Phase 3 completes, 80 chapters from 13 binders are ingested into the main `podcast-factory` pipeline via `scripts/podcast/intake_book.py --from-bundle`. The remaining 42 chapters (6 binders) are excluded from podcast intake — see §8.

---

## 5. Per-Chapter File Structure

Every chapter lives at:
```
_workspace/wisdom-corpus/extracted/wisdom/
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
            wisdom-challenger-report.md ← QA report (Phase 3, when done)
            _extraction-notes.md          ← notes on OCR quality, skips, anomalies
```

### bundle.yml Schema (key fields)

```yaml
bundle_schema_version: 1
source: wisdom
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
  suggested_slug: wisdom-musawwadat-x8114-musawwadat
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

The source extractor (`tools/source_extractor/adapters/wisdom.py`) does:
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

**Scope file:** `_workspace/plan/wisdom-podcast-scope.yaml`

---

## 9. How to Run Each Phase

### Prerequisites
All commands must use the wisdom venv Python:
```bash
VENV=/Users/asifhussain/PROJECTS/podcast-factory/_workspace/wisdom-corpus/.venv/bin/python
```

### Phase 1 — Translate
```bash
# One chapter
$VENV -m tools.content_translator translate wisdom --binder 35 --chapter 100

# All chapters (batch, idempotent)
nohup $VENV _workspace/plan/_drivers/wisdom_translate_all.py >> /tmp/wisdom-translate.log 2>&1 &

# Dry run
$VENV _workspace/plan/_drivers/wisdom_translate_all.py --dry-run

# Single binder
$VENV _workspace/plan/_drivers/wisdom_translate_all.py --binder 35
```

### Phase 2 — Adapt
```bash
# One chapter
$VENV -m tools.content_translator adapt-auto wisdom --binder 35 --chapter 100

# All chapters (batch, idempotent — resumes from where it stopped)
nohup $VENV _workspace/plan/_drivers/wisdom_adapt_all.py >> /tmp/wisdom-adapt-full.log 2>&1 &

# Single binder only
$VENV _workspace/plan/_drivers/wisdom_adapt_all.py --binder 8
```

### Phase 3 — Challenge
```bash
# One chapter
$VENV -m tools.content_translator challenge wisdom --binder 35 --chapter 100

# All chapters
nohup $VENV _workspace/plan/_drivers/wisdom_challenge_all.py >> /tmp/wisdom-challenge.log 2>&1 &

# Warn-only mode (don't block on P1 findings)
$VENV _workspace/plan/_drivers/wisdom_challenge_all.py --warn-only
```

### Status check
```bash
# Stage counts
$VENV _workspace/plan/_drivers/wisdom_pipeline_all.py --status

# Full gate report (after Phase 3 completes)
$VENV _workspace/plan/_drivers/wisdom_gate_report.py --out _workspace/plan/wisdom-gate-report.md

# Quick stage count from filesystem
find _workspace/wisdom-corpus/extracted/wisdom -name "bundle.yml" | \
  xargs grep "^stage:" | awk -F': ' '{print $2}' | sort | uniq -c
```

---

## 10. Key Code Patterns

### Reading a chapter's bundle.yml
```python
from pathlib import Path
import yaml

bundle_path = Path("_workspace/wisdom-corpus/extracted/wisdom/01-musawwadat/01-x8114-musawwadat/bundle.yml")
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
     "wisdom", "--binder", "8", "--chapter", "132"],
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
  33ebda43  feat(wisdom): merge feature/wisdom-translation → develop
  03ff35ed  feat(wisdom-adapt): binder 8 partial — 5 chapters adapted
  26bd97b6  feat(wisdom-adapt): binder 6 — Imam ʿAlī (2 chapters adapted)
  99ce8566  fix(wisdom-adapt): remove 7200s outer timeout
```

All KASHKOLE work is on `develop`. The `feature/wisdom-translation` branch has been merged.

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
nohup /Users/asifhussain/PROJECTS/podcast-factory/_workspace/wisdom-corpus/.venv/bin/python \
  /Users/asifhussain/PROJECTS/podcast-factory/_workspace/plan/_drivers/wisdom_adapt_all.py \
  >> /tmp/wisdom-adapt-full.log 2>&1 &
```
The driver is idempotent — it skips all 119 already-adapted chapters and resumes from the 3 remaining.

### Phase 3 — Challenge all 122 chapters
```bash
nohup /Users/asifhussain/PROJECTS/podcast-factory/_workspace/wisdom-corpus/.venv/bin/python \
  /Users/asifhussain/PROJECTS/podcast-factory/_workspace/plan/_drivers/wisdom_challenge_all.py \
  >> /tmp/wisdom-challenge.log 2>&1 &
```

### Gate review (manual)
After Phase 3, run:
```bash
python _workspace/plan/_drivers/wisdom_gate_report.py \
  --out _workspace/plan/wisdom-gate-report.md
```
Then open `wisdom-gate-report.md` and review. P0 failures block intake; P1 warnings are advisory.

### Phase 4 — Podcast intake (SUPERSEDED — see §18)

> **NOTE (2026-05-26):** The original plan to ingest 80 chapters into the podcast pipeline as standalone podcast series has been superseded. The new Phase 4 goal is to feed the entire corpus (all challenged chapters, regardless of binder exclusions) into the **intelligence pipeline** as a doctrinal knowledge corpus. See §18 for the full design. Podcast production from Kashkole content may still happen in a future phase, but it is not Phase 4.

---

## 14. Bilingual Reader Integration

A bilingual reader page was built (commit `b9e43c5`) at:
```
podcast-reader/src/pages/wisdom/[shelf]/[book].astro
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
_workspace/wisdom-corpus/.venv/bin/python   # Python 3.14.5

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
| Check progress | `find _workspace/wisdom-corpus/extracted/wisdom -name "bundle.yml" \| xargs grep "^stage:" \| awk -F': ' '{print $2}' \| sort \| uniq -c` |
| Resume adapt | `nohup {VENV} _workspace/plan/_drivers/wisdom_adapt_all.py >> /tmp/wisdom-adapt-full.log 2>&1 &` |
| Run challenge | `nohup {VENV} _workspace/plan/_drivers/wisdom_challenge_all.py >> /tmp/wisdom-challenge.log 2>&1 &` |
| Single chapter adapt | `{VENV} -m tools.content_translator adapt-auto wisdom --binder N --chapter N` |
| Single chapter challenge | `{VENV} -m tools.content_translator challenge wisdom --binder N --chapter N` |
| Gate report | `{VENV} _workspace/plan/_drivers/wisdom_gate_report.py` |
| Check failures | `cat _workspace/plan/wisdom-adapt-failures.log` |
| Commit adapted work | `git add _workspace/wisdom-corpus/extracted/wisdom/ _workspace/plan/wisdom-adapt-cost-ledger.jsonl && git commit -m "feat(wisdom-adapt): ..."` |

Where `{VENV}` = `/Users/asifhussain/PROJECTS/podcast-factory/_workspace/wisdom-corpus/.venv/bin/python`

**Files to read for deeper understanding:**
- `tools/content_translator/stages/adapt_auto.py` — full adaptation logic
- `tools/content_translator/stages/translate.py` — Phase 1 translation logic  
- `tools/content_challenger/wisdom/validator.py` — V1–V8 validator checks
- `tools/source_extractor/adapters/wisdom.py` — DB extraction logic
- `_workspace/plan/_drivers/wisdom_adapt_all.py` — batch driver with binder order
- `_workspace/plan/wisdom-podcast-scope.yaml` — in/out binder decisions

---

## 18. Intelligence Pipeline Integration (Phase 4 — NEW DESIGN, 2026-05-26)

### 18.1 Purpose and Goal

Kashkole is not being produced as a podcast series. Instead it serves as a **doctrinal knowledge corpus** that feeds the podcast-factory's intelligence pipeline — an Extractor → Librarian → Augmenter architecture that builds a growing cross-book knowledge base at `content/knowledge-base/`. Every future book the pipeline processes can query this base to receive contextually relevant prior treatments, Quranic commentary, and doctrinal depth — making each new book smarter.

Kashkole is uniquely suited to this role: 122 chapters of Ismaili scholarship covering Tawhīd, taʾwīl, Quranic exegesis, jurisprudence, ethics, cosmology, and biographical narrative — all now in polished scholarly English. No other source in the pipeline has this breadth of Ismaili doctrinal coverage.

### 18.2 Architecture of the Intelligence Pipeline

The pipeline lives in `scripts/podcast/knowledge/` and has three pieces (all scaffold-only as of 2026-05-26 — Wave 1 implementation is pending):

```
Extractor  (scripts/podcast/knowledge/extractor.py)
    Reads audit-vetted chapter text.
    Pulls atoms (Quran citations, hadith references, etc.).
    Writes per-book scratch JSONL: _system/knowledge-atoms-scratch.jsonl

Librarian  (scripts/podcast/knowledge/librarian.py)
    Reads the scratch file.
    Deduplicates: exact-match for Quran/hadith, fuzzy for quotes/definitions.
    Merges into canonical JSONL shards: content/knowledge-base/{type}.jsonl

Augmenter  (scripts/podcast/knowledge/augmenter.py)
    Stateless query helper called from inside other phases.
    Regex-scans a chapter's text for citations.
    Returns top-K prior atoms as prompt-ready context strings.
    Default-disabled until A/B Gate passes on at least one book pair.
```

Atom schemas are in `scripts/podcast/knowledge/_atom_schemas.py`. Wave 1 defines two types (`quran`, `hadith`). Waves 2/3 add `quotes`, `etymology`, `definitions`. Kashkole requires a **6th type: `doctrine`** (see §18.4).

Current library contents (2026-05-26):
```
content/knowledge-base/
  quran.jsonl        ← populated by prior books (size unknown, may be near-empty)
  hadith.jsonl       ← populated by prior books
  _conflicts/        ← pending-review atoms
  _index/            ← search indexes
  README.md
```

### 18.3 Dual-Layer Ingestion Strategy

Kashkole feeds the knowledge base in two parallel layers:

**Layer 1 — Atom extraction (fits Wave 1 schema)**

The `adapted-extract.en.md` files contain Quran references as `⟪quran S:A⟫` markers and hadith references embedded in `adaptation-citations.jsonl`. These map directly onto the existing `quran` and `hadith` atom types.

For each challenged Kashkole chapter:
- Parse all `⟪quran S:A⟫` markers → emit `quran` atoms tagged `source: "wisdom/<binder>/<chapter>"`
- Parse `adaptation-citations.jsonl` for entries where `source_work` matches a hadith collection → emit `hadith` atoms
- Write to scratch JSONL, then run Librarian to merge

Crucially: Kashkole's Quran atoms carry *taʾwīl context* — the surrounding adapted text explains the esoteric Ismaili interpretation of each verse. This is far richer than a bare citation. Store the surrounding paragraph (up to ~200 words) as `tafsir_note` in the `QuranBody`.

**Layer 2 — Doctrine context chunks (new `doctrine` atom type)**

The adapted English prose itself is the primary value. Each chapter is chunked into semantic units of ~500 words (at section boundaries, never mid-paragraph) and stored as `doctrine` atoms. These are retrieved by the Augmenter when a future book's chapter touches the same topic.

This is what "intelligently augment other content" means in concrete terms: when the pipeline authors a chapter on Tawhīd in a new book, the Augmenter queries for `doctrine` atoms tagged `topic: tawhid` and injects the top-2 Kashkole passages as background context into the authoring prompt. The author model then weaves in the doctrinal depth without having to rediscover it from scratch.

### 18.4 Doctrine Atom Schema

Add the following to `scripts/podcast/knowledge/_atom_schemas.py`:

```python
DoctrineGenre = Literal[
    "tawil",            # esoteric Quranic interpretation
    "theology",         # systematic doctrinal exposition
    "jurisprudence",    # Islamic law (Daaim al-Islam basis)
    "ethics",           # moral philosophy, adab
    "cosmology",        # mabda wa maad, origin/return
    "narrative",        # prophetic stories, biographical
    "scholarly",        # treatises, academic essays
]

class DoctrineBody(TypedDict, total=False):
    tradition: Literal["ismaili"]    # always ismaili for Kashkole
    genre: DoctrineGenre
    binder_id: int                   # numeric binder ID from KASHKOLE DB
    binder_slug: str                 # e.g. "tawheed-mubdi-taala"
    chapter_id: int                  # numeric chapter ID from KASHKOLE DB
    chapter_slug: str                # e.g. "01-tawheed-x3341-x7946-x1260"
    section_ids: list[int]           # which section IDs this chunk spans
    chunk_index: int                 # 0-based index within the chapter
    topic_tags: list[str]            # derived from section headings + binder classification
    text_en: str                     # ~500-word adapted English chunk (scholarly register)
    quran_refs: list[str]            # any ⟪quran S:A⟫ references in this chunk

# Canonical ID format:
#   doctrine:wisdom:<binder_id>:<chapter_id>:<chunk_index>
# Example:
#   doctrine:wisdom:24:650:0

# Add to AtomType:
AtomType = Literal["quran", "hadith", "doctrine"]   # Wave 1 + Kashkole extension
```

Dedup strategy for `doctrine` atoms: **exact-match on canonical ID** (no fuzzy needed — each chunk is uniquely addressed by binder/chapter/chunk index).

### 18.5 Ingestion Path

Kashkole does NOT go through `orchestrate_book.py`. Its content is already in `adapted-extract.en.md` — translation and adaptation are done. The ingestion is a standalone batch:

```
wisdom_ingest_knowledge.py  (to be built at: _workspace/plan/_drivers/wisdom_ingest_knowledge.py)

Input:   _workspace/wisdom-corpus/extracted/wisdom/**/{chapter}/
         ├── bundle.yml                          (stage, binder_id, chapter_id)
         ├── _system/source/text/adapted-extract.en.md   (Layer 2 source)
         ├── _system/source/text/adaptation-citations.jsonl  (Layer 1 hadith source)
         └── _system/source/text/wisdom-challenger-report.md  (verdict filter)

Filter:  Only ingest chapters whose challenger-report verdict is PASS or WARN.
         Skip FAILs entirely until they are re-adapted and re-challenged (see §18.6).

Output:  Per-chapter scratch:
           _workspace/wisdom-corpus/extracted/wisdom/**/{chapter}/
             _system/knowledge-atoms-scratch.jsonl
         Then Librarian merges into:
           content/knowledge-base/quran.jsonl
           content/knowledge-base/hadith.jsonl
           content/knowledge-base/doctrine.jsonl  ← new shard
```

**Chunking algorithm:**

1. Parse `adapted-extract.en.md`, split on `<!-- section N -->` markers.
2. Group consecutive sections into chunks of ≤ 600 words. Never split mid-section.
3. Each chunk → one `doctrine` atom.
4. Derive `topic_tags` from: (a) binder classification (§18.7), (b) `## Section Title` headings in the chunk, (c) prominent Arabic terms after first-gloss markers.

### 18.6 Pre-requisite: Fix the 18 FAIL Chapters

From the gate report (`_workspace/plan/wisdom-gate-report.md`), 18 chapters failed Phase 3 validation. These must be re-adapted and re-challenged before they can be ingested. They are listed in §13 of the gate report.

Re-adaptation command (one chapter at a time):
```bash
{VENV} -m tools.content_translator adapt-auto wisdom --binder {N} --chapter {M}
{VENV} -m tools.content_translator challenge wisdom --binder {N} --chapter {M}
```

Or run the driver with `--fail-only` flag (needs to be added to `wisdom_adapt_all.py` if not present):
```bash
{VENV} _workspace/plan/_drivers/wisdom_adapt_all.py --fail-only
{VENV} _workspace/plan/_drivers/wisdom_challenge_all.py --fail-only
```

After all 18 re-challenge, re-run the gate report and confirm verdicts are now PASS or WARN.

### 18.7 Binder-to-Topic-Tag Mapping

Use this mapping when tagging doctrine atoms. These tags are what the Augmenter uses to match Kashkole context to future book chapters:

| Binder ID | Binder Slug | Primary Topic Tags |
|---|---|---|
| 35 | the-wise-reminder | `wisdom, spiritual-guidance, ismaili-ethics` |
| 32 | ghazali-kimiya-as-saadah | `ghazali, ethics, spiritual-discipline, nafs` |
| 36 | islam-iman-ihsan | `five-pillars, iman, ihsan, ismaili-practice` |
| 18 | qurani-qisas-al-anbiya | `prophets, quran-narrative, nubuwwa` |
| 25 | daaim-al-islam-taharat | `tahara, ritual-purity, jurisprudence, daaim` |
| 27 | adab-wa-akhlaq-hasana | `ethics, adab, moral-conduct, community` |
| 29 | daaim-al-islam-as-sawm | `sawm, fasting, jurisprudence, daaim` |
| 1 | uloom-mabda-wa-maad | `cosmology, mabda, maad, aql, nafs, origin-return` |
| 24 | tawheed-mubdi-taala | `tawhid, divine-oneness, tanzih, theology` |
| 26 | daaim-al-islam-salawat | `salat, prayer, jurisprudence, daaim` |
| 19 | daaim-al-islam-wilayat | `wilaya, imamate, authority, daaim` |
| 8 | kalimat-rabbani-ki-taweelat | `tawil, quran-exegesis, divine-words, esoteric` |
| 23 | muntakhab-ilmi-mazameen | `scholarship, treatise, theology, philosophy` |
| 34 | quranic-studies | `quran, tafsir, basmala, fatiha, arabic-grammar` |
| 6 | ali-ibn-abi-talib | `ali, imamate, khutba, nahjul-balagha` |
| 12 | daat-aur-seerah | `dawat, duat, history, biography` |
| 5 | muntakhab-ashaar | `poetry, devotional, marsiya` |

Note: Binders 34, 6, 5, 12, and 16 were excluded from podcast production but ARE included in knowledge base ingestion. Their doctrinal content is valuable for augmentation even if they are not suitable as standalone podcast series.

### 18.8 Augmenter Extension (Wave 2 work)

The Wave 1 Augmenter uses citation regex matching (e.g. "Quran 2:255" → look up `quran:2:255`). For `doctrine` atoms, which are semantic chunks rather than discrete citations, the Wave 2 Augmenter needs topic-tag matching:

```python
def augment_for_chapter(
    ...,
    types: tuple[str, ...] = ("quran", "hadith", "doctrine"),  # add doctrine
    ...
) -> str:
    # Wave 1: regex citation scan for quran + hadith (unchanged)
    # Wave 2 addition for doctrine:
    #   1. Extract topic signals from chapter_text:
    #      - Detect Arabic terms (⟪ar:…⟫ markers or first-gloss patterns)
    #      - Detect binder-level topic keywords (e.g. "tawhid", "wilaya", "tawil")
    #   2. Load doctrine.jsonl shards.
    #   3. Score each doctrine atom: intersection of chapter topic signals with atom topic_tags.
    #   4. Filter: exclude atoms from the current book_slug source.
    #   5. Return top-K (default 3 for doctrine, to stay within token budget).
```

The doctrine atom block injected into prompts should follow this format (spec §6.2 extended):
```
[PRIOR DOCTRINAL CONTEXT — Kashkole corpus]
Topic: tawhid, divine-oneness
Source: Kashkole binder "Tawhīd Mubdiʿ Taʿālā", chapter "Kalimāt al-Tawḥīd"
---
{chunk text, ~300 words, truncated at sentence boundary to fit token budget}
---
```

### 18.9 Files to Read for This Work

| File | Purpose |
|---|---|
| `scripts/podcast/knowledge/_atom_schemas.py` | Schema to extend with `doctrine` type |
| `scripts/podcast/knowledge/extractor.py` | Implement atom extraction for Kashkole |
| `scripts/podcast/knowledge/librarian.py` | Implement dedup + merge for doctrine shard |
| `scripts/podcast/knowledge/augmenter.py` | Extend with topic-tag matching for doctrine |
| `_workspace/plan/view/intelligence-pipeline.html` | Visual spec of the Extractor → Librarian → Augmenter design |
| `_workspace/plan/architecture.md` | Layer 3 (Intelligence) spec — read the Intelligence Layer section |
| `_workspace/plan/wisdom-gate-report.md` | Gate report: which chapters are PASS/WARN/FAIL |
| `content/knowledge-base/` | Current library shards |

### 18.10 Sequenced Action Plan

Execute in this order:

1. **Fix 18 FAILs** — re-adapt + re-challenge each failed chapter (§18.6). Verify all reach PASS or WARN.
2. **Extend `_atom_schemas.py`** — add `DoctrineBody`, `DoctrineGenre`, update `AtomType` (§18.4).
3. **Build `wisdom_ingest_knowledge.py`** — standalone driver that:
   - Walks all challenged chapters filtered to PASS + WARN verdict
   - Extracts Layer 1 atoms (quran, hadith) from markers + citations
   - Extracts Layer 2 doctrine chunks per §18.5 chunking algorithm
   - Writes scratch JSONL per chapter
   - Calls Librarian to merge into `content/knowledge-base/`
4. **Implement Librarian** (`librarian.py`) for the `doctrine` shard — exact-match dedup on canonical ID.
5. **Run ingestion** on all PASS + WARN chapters. Verify `content/knowledge-base/doctrine.jsonl` grows.
6. **Implement Augmenter Wave 2** — add topic-tag matching for doctrine atoms (§18.8). Keep default-disabled until A/B gate passes.

Steps 2–4 can be parallelised. Step 5 requires Step 3 complete. Step 6 requires Step 5 complete.
