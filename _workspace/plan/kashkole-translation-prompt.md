# KAHSKOLE Translation + Adaptation — Autonomous Session Prompt

**Paste the body below (everything inside the `===` rulers) as the first message
in a fresh Claude Code session, working directory:
`/Users/ahmac/Code/podcast-factory`. Pick a fresh branch off `develop`:
`feature/kashkole-translation`.**

This session is designed to be re-invokable. Each session run finishes one
batch (the pilot, then one binder at a time), halts and surfaces for human
review, and commits per-chapter so the next session resumes cleanly from
`bundle.yml.stage`.

================================================================================

# KAHSKOLE Translation + Adaptation — Operator Instructions

You are picking up multi-session autonomous work in the **podcast-factory**
repo. The KAHSKOLE corpus (122 chapters, 1,337 topics, all Urdu) has been
fully extracted into byte-faithful bundles, reviewed, and given an editorial
overlay (English chapter titles for all 122, English topic titles for 235 of
the 1,337). The bilingual reader is built and waiting for translated English
to populate.

**Mission:** Produce a polished, articulate English layer for each KAHSKOLE
chapter — faithful to the Urdu source, augmented with explicit citations to
authentic Fatimid-era Ismaili sources from Claude's training, and validated
by a per-chapter challenger.

Before starting, READ in order:

1. [CLAUDE.md](../../CLAUDE.md) — repo conventions, authorization tiers
2. [_workspace/plan/kashkole-rollout-summary.md](kashkole-rollout-summary.md) — what's already done
3. [_workspace/plan/kashkole-taxonomy-r1-proposal.md](kashkole-taxonomy-r1-proposal.md) — chapter retitles + dedup clusters (approved)
4. [_workspace/plan/kashkole-r2-handoff.md](kashkole-r2-handoff.md) — topic retitles (235 of 1,337 done, 1,102 deferred)
5. [tools/source_extractor/README.md](../../tools/source_extractor/README.md) — bundle layout
6. [scripts/podcast/translate_bundle.py](../../scripts/podcast/translate_bundle.py) — existing Azure translation entry point (Phase 0a-translate)
7. [podcast-reader/src/pages/kashkole/[shelf]/[book].astro](../../podcast-reader/src/pages/kashkole/[shelf]/[book].astro) — the bilingual reader expecting your output

This prompt **overrides** the default cautious tool-use cadence within each
phase. Work continuously through a single batch. Halt and surface ONLY at
the gates defined in §Surface conditions.

---

## Hard guardrails — non-negotiable

| Rule | Why |
|---|---|
| **NEVER modify `raw-extract.md`** | The Urdu source is byte-faithful to the KAHSKOLE SQL database. Translation writes a sibling `raw-extract.en.md`; adaptation writes a sibling `adapted-extract.en.md`. The Urdu source never changes. |
| **NO WebFetch / WebSearch** | All augmentation comes from Claude's training. Authentic Fatimid sources (Kirmani, al-Mu'ayyad, Qadi al-Nu'man, al-Sijistani, Nasir-i Khusraw, al-Hamidi, Ibn al-Walid) are well-represented in training and must be cited by **work name**, not "Ismaili tradition" generally. |
| **Every augmentation needs provenance** | One JSONL line per augmentation in `adaptation-citations.jsonl`: `{section_id, augmentation_excerpt, source_work, source_author, source_authority, confidence}`. Anything lacking high-confidence attribution gets dropped, not invented. |
| **Per-chapter cost cap: $5 Azure** | Halt the chapter and log if exceeded. The translation Azure call is the only paid component; adaptation is in-conversation. |
| **Per-session cost cap: $50 Azure** | Halt and surface to operator if cumulative session cost exceeds this. |
| **Per-session chapter cap: 10 chapters** | Even if context allows more, halt after 10 chapters and surface — quality degrades on long sessions. |
| **No chapter with `needs_human_review: true` runs without explicit flag** | 78 of 122 chapters carry this flag from the autonomous rollout. Pilot can run on the 3 explicitly chosen even if flagged, but the binder-loop only processes chapters where `needs_human_review: false` unless `--include-flagged` is passed. |
| **No remote push, no merge to develop, no amend, no force-push** | Local commits only. Operator merges after review. |

---

## Pre-flight (do this first)

```bash
# 1. Verify branch hygiene
git checkout develop && git pull --ff-only 2>/dev/null  # may fail if no remote tracking; that's OK
git checkout -b feature/kashkole-translation 2>/dev/null || git checkout feature/kashkole-translation
git status   # must be clean

# 2. Verify Azure credentials (translate_bundle.py uses these)
security find-generic-password -s azure-openai-translator-key 2>&1 | head -3 || \
    echo "WARN: Azure key may not be in keychain"

# 3. Verify the bundles are where we expect
ls _workspace/kashkole-ksessions/extracted/kashkole/ | wc -l   # should be 19

# 4. Verify the venv
VENV=_workspace/kashkole-ksessions/.venv/bin/python
$VENV --version   # should be 3.14

# 5. Initialize cost ledger
mkdir -p _workspace/plan
touch _workspace/plan/kashkole-translation-cost-ledger.jsonl
```

If any check fails, surface immediately with the failing command.

---

## Phase 1 — Build `tools/content_translator/`

A new sibling to `tools/source_extractor/` and `tools/content_reviewer/`.
Sits alongside them; uses the existing Azure infrastructure.

### Directory layout

```
tools/content_translator/
├── __init__.py
├── __main__.py
├── README.md
├── cli.py
├── stages/
│   ├── __init__.py
│   ├── translate.py        ← Azure-based literal Urdu→English
│   ├── adapt.py            ← Claude (in-conversation) polish + augment
│   └── seal.py             ← Stamp bundle.yml stage transitions
├── prompts/
│   ├── translate.md        ← Azure system prompt (literal, terminology-preserving)
│   └── adapt.md            ← Adaptation conventions (read by the operating session)
└── data/
    └── fatimid-sources.yaml   ← Allowlist of named works that may be cited
```

### `translate.py` behavior

1. Read `_system/source/text/raw-extract.md`.
2. Split by section markers; translate section-by-section to preserve structure.
3. For each section, call Azure OpenAI (reuse `scripts/podcast/translate_bundle.py`'s
   Azure-call helper if possible — DO NOT duplicate Azure logic) with the prompt:
   > "Translate the following Urdu text to English. Preserve every section
   > marker, every `⟪ar:…⟫` marker, every `⟪quran X:Y⟫` marker, every blockquote,
   > every table. Preserve technical Ismaili/Arabic terms (al-ʿAql al-Awwal,
   > al-Mubdiʿ, al-Munbaʿithūn, etc.) verbatim with English gloss in parens on
   > first use. The output is a LITERAL translation, not an adaptation —
   > prose can stay choppy. Do not augment, do not skip, do not summarize."
4. Concatenate to `_system/source/text/raw-extract.en.md`.
5. Append `translation:` block to bundle.yml: `{ engine, model, completed_at, sections_translated, azure_cost_usd }`.
6. Stamp `bundle.yml.stage` from `reviewed` → `translated`.
7. Append a line to `_workspace/plan/kashkole-translation-cost-ledger.jsonl`:
   `{"binder_id":N,"chapter_id":M,"phase":"translate","cost_usd":X.XX,"completed_at":"..."}`.

### `adapt.py` behavior

This stage runs **in-conversation** (the operating session = Claude). The
script is a thin orchestrator that:

1. Reads `_system/source/text/raw-extract.md` (Urdu) and `raw-extract.en.md` (literal English) and `editorial-review.md` (reviewer annotations).
2. Reads `tools/content_classifier/data/kashkole-r1-decisions.yaml` (English chapter title) and `kashkole-r2-decisions.yaml` (topic retitles if available for this binder).
3. Reads `tools/content_translator/data/fatimid-sources.yaml` (citation allowlist).
4. Reads `tools/content_translator/prompts/adapt.md` (adaptation conventions — see §Adaptation conventions below).
5. Surfaces a structured prompt for the operating session to write `adapted-extract.en.md` + `adaptation-citations.jsonl`.

The operating session then:
- Walks each section of `raw-extract.en.md`
- Polishes the prose (eliminate translation choppiness, weave sentences)
- Preserves all technical terminology, Quran citations, ⟪ar:⟫ markers
- Adds 0–3 augmentations per section where it adds high-value context:
  - "As Kirmani elaborates in *Rahat al-ʿAql*, the Munbaʿithūn..."
  - "Qadi al-Nuʿmān's *Daʿāʾim al-Islām* expands this point with..."
- Each augmentation gets a JSONL line with explicit citation
- Preserves section markers; section structure stays intact

After writing the files:
6. Stamp `bundle.yml.stage` from `translated` → `adapted`.
7. Append `adaptation:` block to bundle.yml: `{ completed_at, sections_adapted, augmentations_added, augmentations_by_source }`.

### `seal.py` behavior

Validates outputs and stamps `stage: adapted` → `challenged` after the
challenger runs (see Phase 2).

### CLI

```bash
$VENV -m tools.content_translator translate --binder N --chapter M
$VENV -m tools.content_translator adapt     --binder N --chapter M   # surfaces adaptation prompt to this session
$VENV -m tools.content_translator seal      --binder N --chapter M
$VENV -m tools.content_translator status                              # ledger summary
```

Smoke test on **binder 1 chapter 75** (`munbathin`) — the smallest pilot
chapter. Verify outputs exist + bundle.yml updated. Commit Phase 1:

```bash
git add tools/content_translator/
git commit -m "feat(content-translator): translation + adaptation tool (autonomous Phase 1)"
```

---

## Phase 2 — Build the `kashkole-challenger`

Sibling to `podcast-challenger` (see `infra/claude-agents/`) and
`tools/content_reviewer/`. Two parts:

### 2a — Deterministic checks at `tools/content_challenger/kashkole/`

```
tools/content_challenger/
├── __init__.py
├── cli.py
└── kashkole/
    ├── __init__.py
    ├── validators.py       ← deterministic checks
    └── report.py           ← compose challenger-report.md
```

Deterministic checks (run with Python, no LLM):
- **Section count match:** `adapted-extract.en.md` has the same number of `<!-- section N -->` markers as `raw-extract.md`
- **Terminology preservation:** Every Arabic technical term from the R1/R2 glossary present in Urdu source has its corresponding English gloss in adapted output
- **Quran citation preservation:** Every `⟪quran S:A⟫` in source has a parallel `Quran S:A` citation in adapted output
- **`⟪ar:⟫` preservation:** Arabic-inline markers preserved (count match)
- **Citation provenance:** Every `adaptation-citations.jsonl` line has all required fields
- **Source attribution allowlist:** All `source_work` values appear in `tools/content_translator/data/fatimid-sources.yaml`
- **Fidelity ratio:** Adapted English length should be within 50%–250% of literal English length per section (catches truncation and runaway elaboration)
- **No hallucinated citations:** Every Quran reference in the adapted output that wasn't in the source is flagged for human review

### 2b — LLM challenger at `infra/claude-agents/kashkole-challenger.md`

Subagent spec, mirrors `podcast-challenger.md`. Reads the deterministic
checks, then runs a convergence loop (up to 3 iterations):

1. Read `raw-extract.md` (Urdu), `raw-extract.en.md` (literal), `adapted-extract.en.md` (polished+augmented), `adaptation-citations.jsonl`, `editorial-review.md`
2. Validate semantic quality on the four axes:
   - **Translation fidelity** — does the adapted English faithfully convey what the Urdu says?
   - **Augmentation authenticity** — are citations to Kirmani / al-Mu'ayyad / Qadi al-Nu'man / al-Sijistani / etc. accurate and from training-grounded knowledge?
   - **Paragraph flow** — does prose read smoothly section-by-section? (preserving section structure, not merging)
   - **Integrity** — no invented hadith, no misattributed verses, no doctrinal positions the original author would reject
3. For each finding, emit one of:
   - `auto_fix` — challenger writes the patched line itself
   - `needs_human` — flag for human review with a brief rationale
4. After loop converges (no auto-fixes remaining) or 3 iterations exhausted, write `kashkole-challenger-report.md` to the bundle and stamp `bundle.yml.stage: adapted → challenged`.

### CLI

```bash
$VENV -m tools.content_challenger.kashkole validate --binder N --chapter M   # deterministic only
$VENV -m tools.content_challenger.kashkole challenge --binder N --chapter M  # invokes the kashkole-challenger agent
```

Commit Phase 2:

```bash
git add tools/content_challenger/ infra/claude-agents/kashkole-challenger.md
git commit -m "feat(kashkole-challenger): per-chapter quality challenger (autonomous Phase 2)"
```

---

## Phase 3 — Pilot (3 chapters, halt+surface gate)

Run the full translate → adapt → challenge → seal pipeline on the 3 chapters
the user already locked:

| Binder | Chapter | Slug | Topics | Why this pilot |
|---|---|---|---|---|
| 1 | 75  | `04-saat-uqool` (was `munbathin`) | 5 | Smallest doctrinally-dense philosophical chapter — tests technical-terminology preservation |
| 1 | 74  | `02-aql-awwal` | 12 | Medium philosophical, heavy glossary use — tests citation density |
| 25 | 88  | `01-taharat-se-…` | 5 | Jurisprudential (Daʿāʾim al-Islām genre) — different genre stress-test |

For each:

```bash
$VENV -m tools.content_translator translate --binder $BID --chapter $CID
# (adaptation surfaces a prompt back to YOU — write the adapted-extract.en.md
#  and adaptation-citations.jsonl, citing only training-grounded Fatimid sources)
$VENV -m tools.content_translator adapt     --binder $BID --chapter $CID
$VENV -m tools.content_challenger.kashkole validate --binder $BID --chapter $CID
$VENV -m tools.content_challenger.kashkole challenge --binder $BID --chapter $CID
$VENV -m tools.content_translator seal      --binder $BID --chapter $CID
git add _workspace/kashkole-ksessions/extracted/kashkole/<shelf>/<chapter>/
git commit -m "feat(kashkole-translate): pilot chapter b${BID}/c${CID} translated + adapted + challenged"
```

After all 3 pilot chapters commit:

```bash
git add _workspace/plan/kashkole-translation-cost-ledger.jsonl
git commit -m "feat(kashkole-translate): pilot batch complete (3 chapters)"
```

**HALT and SURFACE to operator.** Summary message:

```
🟢 Pilot complete (3 chapters).
  - b1/c75 munbathin: $X.XX Azure, N augmentations
  - b1/c74 aql-awwal: $X.XX Azure, N augmentations
  - b25/c88 taharat: $X.XX Azure, N augmentations
  Total: $X.XX
Review at:
  http://localhost:4321/kashkole/07-uloom-mabda-wa-maad/04-saat-uqool/
  http://localhost:4321/kashkole/07-uloom-mabda-wa-maad/02-aql-awwal/
  http://localhost:4321/kashkole/13-daaim-al-islam-taharat/01-taharat-se-x7982-x1549/

Decide:
  [a] Approve pilot — proceed to Phase 4 (per-binder loop)
  [b] Revise — operator edits adapted-extract.en.md / adaptation-citations.jsonl
  [c] Adjust conventions — operator edits tools/content_translator/prompts/adapt.md
```

**Do NOT proceed to Phase 4 without explicit operator approval.**

---

## Phase 4 — Per-binder loop (one binder per session)

Order (smallest doctrinally-densest first, to validate quality before scale):

```
1.  binder 35 (2 chapters, 18 topics)   — The Wise Reminder (English-source, easiest)
2.  binder 32 (2 chapters, 15 topics)   — Al-Ghazali (English-source)
3.  binder 36 (3 chapters, 24 topics)   — Islam Iman Ihsan (English-mixed)
4.  binder 12 (3 chapters, 7 topics)    — Duʿāt lives
5.  binder 5  (3 chapters, 24 topics)   — Devotional poetry
6.  binder 16 (3 chapters, 14 topics)   — Selected duʿāʾs
7.  binder 18 (5 chapters, 26 topics)   — Prophet stories
8.  binder 25 (5 chapters, 42 topics)   — Daʿāʾim: Ṭahāra (remaining 4 chapters after pilot's c88)
9.  binder 27 (6 chapters, 40 topics)   — Ādāb
10. binder 29 (4 chapters, 43 topics)   — Daʿāʾim: Ṣawm
11. binder 1  (12 chapters, 156 topics) — Sciences of Origin and Return (philosophical core, run AFTER smaller binders to validate methodology)
12. binder 24 (7 chapters, 79 topics)   — Tawḥīd
13. binder 26 (8 chapters, 75 topics)   — Daʿāʾim: Ṣalāt
14. binder 19 (7 chapters, 87 topics)   — Daʿāʾim: Wilāya
15. binder 34 (14 chapters, 84 topics)  — Quranic Studies (English-source)
16. binder 28 (10 chapters, 75 topics)  — Drafts / mixed
17. binder 6  (9 chapters, 144 topics)  — Imam ʿAlī
18. binder 8  (8 chapters, 138 topics)  — Taʾwīl of the Divine Words
19. binder 23 (11 chapters, 214 topics) — Selected scholarly treatises (largest)
```

Per-binder loop body (within a single session):

```bash
BINDER_ID=<id>
for CHAPTER_ID in <chapter list for this binder>; do
  # Skip if already done
  CURRENT_STAGE=$($VENV -m tools.content_translator status --binder $BINDER_ID --chapter $CHAPTER_ID --format stage)
  [ "$CURRENT_STAGE" = "challenged" ] && continue
  # Skip if needs_human_review (unless --include-flagged passed via env)
  NHR=$($VENV -m tools.content_translator status --binder $BINDER_ID --chapter $CHAPTER_ID --format nhr)
  [ "$NHR" = "true" ] && [ "$INCLUDE_FLAGGED" != "1" ] && continue

  $VENV -m tools.content_translator translate --binder $BINDER_ID --chapter $CHAPTER_ID || {
    echo "translate failed binder=$BINDER_ID chapter=$CHAPTER_ID" \
      >> _workspace/plan/kashkole-translation-failures.log
    continue
  }
  # adaptation runs in-conversation — surface the prompt, write outputs
  $VENV -m tools.content_translator adapt --binder $BINDER_ID --chapter $CHAPTER_ID || continue
  $VENV -m tools.content_challenger.kashkole challenge --binder $BINDER_ID --chapter $CHAPTER_ID || continue
  $VENV -m tools.content_translator seal --binder $BINDER_ID --chapter $CHAPTER_ID

  # Commit per chapter (the unit of resume)
  git add _workspace/kashkole-ksessions/extracted/kashkole/<shelf>/<chapter>/ \
          _workspace/plan/kashkole-translation-cost-ledger.jsonl
  git commit -m "feat(kashkole-translate): b${BINDER_ID}/c${CHAPTER_ID} <chapter-en-title>"

  # Self-limit
  CUMULATIVE=$($VENV -m tools.content_translator status --format session-cost)
  [ "$(echo "$CUMULATIVE > 50" | bc)" = "1" ] && {
    echo "Session cost cap reached: \$$CUMULATIVE. Halting."
    break
  }
done
```

At end of binder: commit the binder block summary, **HALT and SURFACE** with:

```
🟢 Binder N (<English title>) complete.
  Chapters processed: M of K (skipped: K-M due to needs_human_review or prior completion)
  Cumulative session cost: $X.XX
  Cumulative corpus cost so far: $X.XX

Next binder: <N+1, English title> (M chapters, ~$Y estimated)
Reply 'continue' to start the next binder in this session, or end the session
and resume tomorrow.
```

---

## Adaptation conventions (the heart of this work)

The literal English from `raw-extract.en.md` is verbose and choppy because
Azure's literal translation. Your job in the adaptation pass is to render it
into prose that reads beautifully while preserving every doctrinal point.

### Style targets

- **Tone:** scholarly, calm, reverent. Mirror the register of the IIS
  publications (Daftary, Walker, Hunzai). Not preachy, not academic-cold.
- **Sentence rhythm:** vary — short declarative sentences interleaved with
  longer ones with subordinate clauses. Avoid run-ons.
- **Paragraph flow within sections:** each section's prose should read as a
  continuous argument; paragraphs should connect with topic + transition.
- **Cross-section flow:** preserved by section markers; do NOT merge sections.

### Terminology — preserve and gloss

First occurrence of any technical term: transliterate + gloss in parens.
Thereafter: transliteration alone.

Examples:
- al-ʿAql al-Awwal (the First Intellect) … later: al-ʿAql al-Awwal
- al-Munbaʿithūn (the Emanators, sg. al-Munbaʿith) … later: the Munbaʿithūn
- taʾwīl (esoteric exegesis) … later: taʾwīl
- Mubdiʿ Taʿālā (the Originator, Most High) … later: the Mubdiʿ

### Augmentation — what counts

Add 0–3 augmentations per section where they ADD VALUE:
- Cross-reference to a parallel passage in a named Fatimid-era work
- Disambiguate a term that has different Ismaili sub-tradition usages
- Quote a one-line attestation from a Fatimid source that strengthens the
  argument
- Explain a Quranic context that the original assumed the reader knew

Do NOT add augmentations for:
- Background that's already in the source
- "As is well known…" (if it's well-known, the original didn't need help)
- Modern scholarly commentary (Daftary, Halm, Walker) — those are
  secondary; cite primary sources first
- Anything you can't pin to a specific named work

### Allowed citation sources (from training, no WebFetch)

Primary Fatimid-era Ismaili works:
- Hamid al-Din al-Kirmani — *Rahat al-ʿAql*, *al-Riyad*, *al-Maṣābīḥ*, *Tanbīh al-Hādī*
- Al-Muʾayyad fī al-Dīn al-Shīrāzī — *al-Majālis al-Muʾayyadiyya*, *Dīwān*
- Qadi al-Nuʿmān — *Daʿāʾim al-Islām*, *Taʾwīl al-Daʿāʾim*, *Asās al-Taʾwīl*, *al-Iqtiṣār*
- Abū Yaʿqūb al-Sijistānī — *Kitāb al-Yanābīʿ*, *al-Iftikhār*, *Ithbāt al-Nubuwwāt*
- Nasir-i Khusraw — *Jāmiʿ al-Ḥikmatayn*, *Khwān al-Ikhwān*, *Wajh-i Dīn*
- Jaʿfar ibn Manṣūr al-Yaman — *Kitāb al-ʿĀlim wa-l-Ghulām*, *Asrār al-Nuṭaqāʾ*, *al-Kashf*
- Al-Ḥamīdī (Sayyidnā Ibrāhīm) — *Kanz al-Walad*
- Ibn al-Walīd (Sayyidnā ʿAlī) — *Tāj al-ʿAqāʾid*

Authoritative ḥadīth & exegesis:
- The Qurʾān itself (already cited inline; never fabricate ayat numbers)
- *Nahj al-Balāgha* (compiled by al-Sharīf al-Raḍī)
- *al-Ṣaḥīfa al-Sajjādiyya* (Imam Zayn al-ʿĀbidīn)
- Famous prophetic hadith from agreed-upon sources (no controversial chains)

Each citation must include the work name. "Ismaili tradition" or "the early
sources" is **not** a valid citation.

### Format

`adapted-extract.en.md` mirrors `raw-extract.md`'s structure:

```markdown
# <English chapter title from R1 decisions> — <Source title in Urdu/transliteration>

*Source: KASHKOLE, Binder N (<binder English title>), Chapter M. K topics. Translated and adapted: 2026-MM-DD.*

<!-- section 1 (id=NNNN, raw_sort=1): <Urdu label> -->

## <English topic title from R2 decisions, if any>

<polished paragraph 1>

<polished paragraph 2 — with [^cite-1] inline citation if an augmentation>

> ⟪quran 3:18⟫ [preserved Quran citation from source]

<more polished prose>

<!-- section 2 (id=...): ... -->

...
```

Augmentations cited with `[^cite-N]` footnotes; the JSONL file holds the
full citation. The bilingual reader will render footnotes on hover/click.

`adaptation-citations.jsonl`:

```jsonl
{"cite_id":"cite-1","section_id":42,"section_position":1,"excerpt":"As Kirmani writes in al-Riyad, the Munbaʿithūn proceed from the First Intellect in a single undivided moment...","source_work":"al-Riyad","source_author":"Hamid al-Din al-Kirmani","source_authority":"Fatimid Da'i, d. ~1020 CE","source_location_hint":"opening of the cosmological section","confidence":"high","training_grounded":true}
{"cite_id":"cite-2","section_id":42,"section_position":1,"excerpt":"...","source_work":"Tanbih al-Hadi","source_author":"Hamid al-Din al-Kirmani","source_authority":"Fatimid Da'i, d. ~1020 CE","source_location_hint":"chapter on emanation","confidence":"medium","training_grounded":true}
```

---

## Resume mechanics

The pipeline is **idempotent per chapter**. If a session is interrupted:

- The next session starts at the same place by checking `bundle.yml.stage`:
  - `reviewed` → translate (full chapter)
  - `translated` → adapt (skip translation, start at adapt)
  - `adapted` → challenge (skip translation + adapt)
  - `challenged` → skip entirely
- The cost ledger is append-only; cumulative cost is recomputed at session start
- The failure log is append-only; the loop checks before running

If `_workspace/plan/kashkole-translation-failures.log` already contains a
line for the current `(binder, chapter)` pair, **skip it**. Operator
reviews the failure log between sessions.

---

## Surface conditions

Surface to operator ONLY when:

1. **Pre-flight fails** — Azure key missing, venv broken, etc.
2. **Phase 1 or 2 build fails** — tool can't smoke-test
3. **Pilot complete (Phase 3)** — halt for explicit approval before Phase 4
4. **Binder complete (Phase 4)** — halt + summary at the end of each binder
5. **Cost cap exceeded** — $50/session or $5/chapter
6. **Unrecoverable error** — disk full, git broken, etc.

Do NOT surface for individual chapter failures within a binder. Log to
`_workspace/plan/kashkole-translation-failures.log` and continue.

---

## What success looks like (end state)

For each of the 122 chapters:

```
_workspace/kashkole-ksessions/extracted/kashkole/<shelf>/<chapter>/
├── bundle.yml                                          # stage: challenged
└── _system/source/text/
    ├── raw-extract.md                                  # Urdu source (BYTE-FAITHFUL, UNCHANGED)
    ├── raw-extract.en.md                               # NEW: literal English (Azure)
    ├── adapted-extract.en.md                           # NEW: polished + augmented (Claude)
    ├── adaptation-citations.jsonl                      # NEW: per-augmentation provenance
    ├── editorial-review.md                             # UNCHANGED
    ├── editorial-annotations.jsonl                     # UNCHANGED
    └── kashkole-challenger-report.md                   # NEW: challenger findings
```

The bilingual reader at `/kashkole/<shelf>/<book>/` will then show:
- Left panel: `adapted-extract.en.md` per topic
- Right panel: `raw-extract.md` per topic (Urdu, unchanged)
- Footnote tooltips for augmentations (citation drawn from JSONL)

---

## Cost projection

| Phase | Per chapter | Total (122 chapters) |
|---|---|---|
| Translation (Azure) | ~$0.50–$2 | ~$60–$240 |
| Adaptation (in-conversation) | $0 | $0 |
| Challenger (in-conversation) | $0 | $0 |
| **Total Azure** | | **~$60–$240** |

At 5–10 chapters per session: **15–25 sessions** to complete the full corpus.

---

## First session expectations

This session's deliverable: **Phase 1 + Phase 2 built, Phase 3 pilot completed
(3 chapters), halt + surface for operator review.**

If context allows after the pilot, do **not** start Phase 4. The pilot
output needs human review before scaling, and a fresh session next day
gets a clean context budget for the larger binders.

Begin.
