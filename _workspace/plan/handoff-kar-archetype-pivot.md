# Mac Studio handoff — KaR archetype pivot (2026-05-22)

**Origin machine:** `macbook-air-secondary`
**Target machine:** `mac-studio-primary`
**Book:** `kitab-al-riyad` (Kitāb al-Riyāḍ) on branch `book/kitab-al-riyad`
**Decision date:** 2026-05-22
**Status:** Pipeline halted by operator. Switching to archetype-driven manual finish.

---

## TL;DR for Mac Studio

The Air halted the podcast pipeline mid-run on KaR. Instead of burning another 5.5–9.5h of API tokens to re-emit the remaining 12 chapters (which would all return SHIP-WITH-CAUTION needing author judgment anyway), we distilled all KaR-learned lessons into a reusable **Islamic Scholastic Text Archetype** at [content/podcast/library/archetypes/islamic-scholastic-text.md](../../content/podcast/library/archetypes/islamic-scholastic-text.md). Mac Studio's job now: read the archetype, apply it to finish KaR by hand (EP10 P1 cleanup + 12 chapter framings), then ship. **Do NOT relaunch the orchestrator on this book.** The archetype is the compounding artifact; the next Islamic book benefits from it.

---

## 0. What you, Mac Studio, do first

```bash
cd /Users/asifhussain/PROJECTS/journal   # or wherever the Studio repo lives
git fetch origin
git checkout book/kitab-al-riyad
git pull --ff-only origin book/kitab-al-riyad

# Confirm halt state
jq '{phase, phase_status, last_completed_phase,
     "per_chapter_completed": (.phases["per-chapter"].completed_slugs | length),
     "halt_reason": .phases["per-chapter"].halt_reason}' \
    content/drafts/kitab-al-riyad/_system/orchestrator-state.json

# Should show:
#   phase: "per-chapter"
#   phase_status: "halted_by_operator"
#   per_chapter_completed: 1
#   halt_reason: "Asif decision 2026-05-22: switch from LLM-driven re-emit
#                 to archetype-driven manual finish..."

# Read the archetype end-to-end (5,354 words, 11 sections; budget ~15-20 min)
less content/podcast/library/archetypes/islamic-scholastic-text.md
```

---

## 1. What changed on the Air (background you need)

### 1.1 What we did
- Killed the orchestrator (was processing ch10 fixer pass + ch14 challenger) cleanly via SIGTERM.
- Updated `orchestrator-state.json`: `phase_status` flipped from `running` → `halted_by_operator` with a `halt_reason` line naming Asif's decision (avoids the [orchestrator-resume bug](https://github.com/asifhussain60/podcast-factory/blob/book/kitab-al-riyad/_workspace/plan/operators/macbook-air-secondary.md) blocking future `--resume`).
- Created the Islamic Scholastic Text Archetype v1.0 at `content/podcast/library/archetypes/islamic-scholastic-text.md`.
- Saved an Air-local memory rule (`feedback_archetype_over_rerun.md`) so future sessions halt LLM-heavy re-runs the moment a book hits SHIP-WITH-CAUTION rather than burning tokens for the same lesson 13×.

### 1.2 Current pipeline state on KaR

| Item | State |
|---|---|
| Phase | `per-chapter` (HALTED) |
| Completed chapters | 1 of 13: `motion-stillness-hyle-and-form` (EP10) |
| EP10 verdict | **SHIP-WITH-CAUTION** — 3 P1s remain (need author judgment) |
| EP14 (prophets-as-teachers) | **PARTIAL** — drafts emitted, episode .txt emitted, challenger NOT run. Mid-process when killed. |
| EP01-EP09, EP11-EP13 (excluding EP10/EP14) | **NOT STARTED** — chapter source `.txt` files exist (TTS-safe per Phase 5), but no `episode-drafts/` for them yet |
| Trainer / merge / done phases | `pending` (deferred until all 13 episodes exist) |

### 1.3 What we explicitly did NOT do
- Did NOT clean up the EP14 partial-emit artifacts. They sit in `_system/episode-drafts/EP14-prophets-as-teachers-monotheism-and-the-ranks/` (5 draft files) + `episodes/EP14-...txt` (205 lines). You decide whether to use them as starting drafts (archetype-edit) or regenerate from scratch.
- Did NOT modify `_authoring.py` to inject archetype as system prompt. The archetype is a reference document right now. Optional future work: a `--archetype <name>` flag on the orchestrator.
- Did NOT push response-template.md changes (in working tree but unrelated to the archetype pivot — your call whether to include).

---

## 2. The work ahead for Mac Studio

### 2.1 Recommended sequence

**Step A — Read the archetype** (~15–20 min).
Sit with [`content/podcast/library/archetypes/islamic-scholastic-text.md`](../../content/podcast/library/archetypes/islamic-scholastic-text.md). The 11 sections (§1 Genre signature → §11 Provenance) are the doctrine. Pay extra attention to:
- **§3 Phase 0d/0e doctrine** — chapter-prose authoring rules (F20, F29, F24, citations, honorifics, em-dashes)
- **§4 Phase 0g doctrine** — 14-section framing template
- **§5 Pronunciation exhibit conventions** — imperative format + 20-row common-terms table
- **§6 Common P0/P1 trap catalog** — 8 empirically-observed failure modes with concrete fixes
- **§7 Forbidden patterns catalog** — copy-pasteable into framings

If anything feels wrong or missing, flag it BEFORE doing Step B (the archetype is v1.0, not infallible).

**Step B — EP10 P1 cleanup** (~30 min). Validates the archetype against real output before you spend 12 chapters of effort on it. Three fixes (see §4 below for exact text):
1. N3-a — Add Pronounce directive for `Al-hayula` to [EP10 framing](../../content/drafts/kitab-al-riyad/_system/episode-drafts/EP10-motion-stillness-hyle-and-form/00-framing.md)
2. N3-b — Add Pronounce directive for `Al-nafs` to same framing
3. A4 — Fix Q16:40 translator attribution (Pickthall → Yusuf Ali) in [ch10 chapter](../../content/drafts/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt)
After fixes: run `python3 scripts/podcast/build_episode_txt.py content/drafts/kitab-al-riyad EP10-motion-stillness-hyle-and-form` to re-emit the episode .txt. Then re-run the challenger to confirm P0=0/P1=0 (or just N3-a/N3-b/A4 cleared).

**Step C — Decide EP14 disposition** (~15 min). Inspect the 5 draft files in `_system/episode-drafts/EP14-prophets-as-teachers-monotheism-and-the-ranks/`. Options:
- **(Recommended)** Keep them as starting drafts and apply archetype edits — they were generated under v4-revised doctrine prompts which mostly align with the archetype. Faster than regenerating.
- Regenerate from scratch using the archetype as system prompt. Cleaner but ~$0.30 in LLM cost.

**Step D — Apply archetype forward to chapters 1-9, 11-13** (~3–4h total, can be split across sessions).
For each of the 11 remaining chapters (NOT including EP10 and EP14 if you keep EP14's partial drafts):
1. Run a single cheap `claude -p` call with the archetype as system prompt to generate a skeleton `00-framing.md` and supporting drafts.
2. Hand-edit the framing for archetype fidelity. The skeleton is the structural scaffold; your judgment goes into:
   - Naming the specific tensions for the chapter
   - Picking 3 governing analogies from the chapter's own images
   - Stating the central thesis verbatim for R-RECURRING-THESIS
   - Populating the Pronunciation block from the chapter's transliterated terms
3. Run `python3 scripts/podcast/build_episode_txt.py content/drafts/kitab-al-riyad EP##-<slug>` to emit episode .txt.
4. (Optional, per-chapter) Run the challenger to confirm SHIP-READY or SHIP-WITH-CAUTION. Skip BLOCKED only — don't auto-fixer-loop.

**Estimated cost for Step D**: 11 chapters × ~$0.10–0.50 per skeleton call = ~$1.10–5.50 total. Versus the ~$50–100+ the orchestrator would have spent for the same outcome.

**Step E — Trainer + merge + done** (~30 min, free, deterministic).
Once all 13 episode .txts exist:
```bash
# Clear the operator-halt to allow the orchestrator's deterministic post-per-chapter
# phases to run. Be specific — only clear the per-chapter-halt, not phase_status:
jq '.phase_status = "completed_by_operator" |
    .phases["per-chapter"].status = "completed" |
    .phases["per-chapter"].ts_completed = (now | todate)' \
    content/drafts/kitab-al-riyad/_system/orchestrator-state.json \
    > /tmp/state.tmp && mv /tmp/state.tmp \
    content/drafts/kitab-al-riyad/_system/orchestrator-state.json

# Then resume for trainer + merge + done (all deterministic, no LLM):
python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad
```

### 2.2 What NOT to do

- ❌ **Do NOT** run `python3 scripts/podcast/orchestrate_book.py --resume kitab-al-riyad` until you've completed Step D for all 11 remaining chapters. That re-launches the per-chapter loop with LLM authoring — exactly what we halted.
- ❌ **Do NOT** run `--retry-phase per-chapter`. Same outcome via a different door.
- ❌ **Do NOT** clear `phase_status: halted_by_operator` without writing a new `halt_reason` or `unhalt_reason` line. The halt is a deliberate marker for the next operator to see.
- ❌ **Do NOT** modify the archetype while doing EP10 cleanup. If a rule needs change, finish EP10 with the current rules, THEN propose archetype amendments — single source of truth for the validation run.

---

## 3. EP10 P1 fixes — exact text

### 3.1 N3-a: Add `Al-hayula` Pronounce directive

**File:** `content/drafts/kitab-al-riyad/_system/episode-drafts/EP10-motion-stillness-hyle-and-form/00-framing.md`
**Action:** Locate the `## Pronunciation` section. Add the following line near the related entries (after the existing `hayle` directive if present, otherwise near `Quran` / `Imam` / other established terms):

```
Pronounce "Al-hayula" as "al-ha-YOO-laa". Say it as four fluent syllables, accent on the third; this is the Arabic for prime matter. Do not spell it.
```

**Archetype reference:** [§5.1 Format](../../content/podcast/library/archetypes/islamic-scholastic-text.md) + [§5.3 Common terms table](../../content/podcast/library/archetypes/islamic-scholastic-text.md).

### 3.2 N3-b: Add `Al-nafs` Pronounce directive

**File:** same as 3.1.
**Action:** Add the following line in the same Pronunciation block:

```
Pronounce "Al-nafs" as "al-NAFS". Say it as two fluent syllables; this is the Arabic for the soul as a technical term.
```

**Archetype reference:** [§5.3 common-terms table](../../content/podcast/library/archetypes/islamic-scholastic-text.md).

### 3.3 A4: Fix Q16:40 translator attribution

**File:** `content/drafts/kitab-al-riyad/chapters/ch10-motion-stillness-hyle-and-form.txt`
**Line:** 105
**Current text:**
```
> *Our only word for a thing,when We will it,is that We say to it,"Be," and it is.* (Quran 16:40,Surah the chapter of the bee; translation rendered after Pickthall)
```

**Problem:** Pickthall's actual Q16:40 reads "But Our commandment is but one, as the twinkling of an eye." The chapter's rendering matches Yusuf Ali, not Pickthall.

**Recommended fix (option a)** — change translator attribution to Yusuf Ali (minimal edit, archetype-faithful):
```
> *Our only word for a thing, when We will it, is that We say to it, "Be," and it is.* (Quran 16:40; the chapter of the bee; Yusuf Ali)
```

**Alternative (option b)** if you prefer to label as author's paraphrase:
```
> *Our only word for a thing, when We will it, is that We say to it, "Be," and it is.* (Quran 16:40; the chapter of the bee; rendered by the author)
```

**Alternative (option c)** if you want to switch to actual Pickthall text:
```
> *But Our commandment is but one, as the twinkling of an eye.* (Quran 16:40; the chapter of the bee; Pickthall)
```

**Archetype reference:** [§3.5 "Verify before attributing"](../../content/podcast/library/archetypes/islamic-scholastic-text.md).

### 3.4 Re-emit + re-challenge

After the three fixes:

```bash
# Re-emit EP10 episode txt
python3 scripts/podcast/build_episode_txt.py \
    content/drafts/kitab-al-riyad \
    EP10-motion-stillness-hyle-and-form

# Re-run challenger to confirm P0/P1 clear
# (Use the podcast-challenger agent via Task tool or however the Studio invokes it)
```

Expected outcome: P0=0, P1=0 (N3-a, N3-b, A4 cleared), P2=1 (F6 advisory still — that one's a deliberate non-fix; archetype's Landing format is functionally equivalent to canonical steering phrases).

---

## 4. Podcast debt & gaps catalog (the "lessons learned" inventory)

These are the failure modes the KaR pipeline run surfaced, all documented in archetype §6. Listed here in priority order with severity and how to fix in remaining chapters.

### 4.1 P0 traps — block ship until fixed

| # | Trap | Where it shows up | Fix pattern |
|---|---|---|---|
| 4.1.1 | **Phase 0e template variable corruption** | Chapter prose contains strings like `Imam the canonical hadith compiler`, `Sahih the canonical hadith compiler`, `the major Sunni collection` | After Phase 0e (or LLM skeleton call), `grep -E "the canonical|the major (Sunni\|Shia) (compiler\|collection)\|the prominent compiler" chapters/*.txt`. Replace with specific collection name (Sahih al-Bukhari, Sahih Muslim, al-Kafi, etc.). |

### 4.2 P1 traps — block upload until fixed

| # | Trap | Validator | Where it shows up | Fix pattern |
|---|---|---|---|---|
| 4.2.1 | **Phonetic coverage gap (N3)** — scholarly transliteration not in Pronunciation block | F27 #1 + challenger N3 | Chapter has italicized Arabic (`*al-hayula*`, `*al-nafs*`, `*mawhumiya*`, `*takhayyuliya*`) without matching `Pronounce "X" as "..."` in framing | For each italicized Arabic term, either (a) add Pronounce directive to framing, OR (b) replace term with English equivalent per §3.1 substitution policy. Default to (b). |
| 4.2.2 | **Surah-naming inconsistency (N3)** | F27 #5 (`assert_no_arabic_surah_names`) | Chapter mixes `*Surat Ya Sin*` (Arabic) with `*Surat the chapter on sincerity*` (English) | Apply F29 R-SURAH-ENGLISH-ONLY consistently. Use English meaning everywhere — see §3.2 examples table for canonical mappings. |
| 4.2.3 | **Meta-artifact insertion (B1)** | Challenger B1 (semantic) | Garbled italic markers fused into prose: `by origination at *dar an earlier work on origination'*` | Grep chapter for `*dar`, `'*`, `**` (triple asterisk), `* *` (italic mid-space). Clean each. |
| 4.2.4 | **Full-name reintroduction after alias (J2)** | F27 #1 + challenger J2 | Framing uses stable label `the author`; chapter has section header `## Hamid al-Din Ahmad al-Kirmani` reintroducing full name | Apply R-STABLE-ROLE-LABELS to chapter section headers and bold-text reintroductions, not just prose. Grep for full Arabic names in headers. |
| 4.2.5 | **Em-dash density (B5)** | Challenger B5 | Chapter prose has em-dashes (—) | Replace all em-dashes with commas/semicolons/colons. Run `sed -i '' 's/—/,/g'` per chapter (or more nuanced editorial substitution). Phase 5 cleanup already did this for KaR — verify before assuming clean. |
| 4.2.6 | **Quranic translator attribution mismatch (A4)** | Challenger A4 (requires corpus) | Citation says `(... ; rendered after Pickthall)` but actual text matches Yusuf Ali | Verify each Quranic quote against the named translator's published rendering. If mismatch, change attribution or label as `rendered by the author`. (This is the EP10 A4 problem; archetype §3.5 names the discipline.) |

### 4.3 P2 advisories — non-blocking but worth fixing for quality

| # | Trap | Where | Fix |
|---|---|---|---|
| 4.3.1 | **Technical-term exemption without C4 justification** | Chapter retains `*al-nafs*`/`*al-ruh*` (legitimately — tripartite-soul vocabulary), framing doesn't explain | Add a `## Substitution-policy notes` subsection to framing's Tone constraints listing each retained Arabic term with one-line justification. |
| 4.3.2 | **Nahj al-Balagha citation uses English title wrapper** | Chapter cites `(the book *The Path of Eloquence*, Sermon 1)` instead of canonical `(Nahj al-Balagha, Sermon 1)` | Deliberate design — TTS-safe English wrapper. Archetype §3.5 endorses this; challenger flags as A1 advisory. No fix needed; ignore the advisory. |
| 4.3.3 | **Framing missing explicit `## Audience` section** | Audience defined in chapter contract YAML, not in framing markdown | Add `## Audience` section to framing copying the contract's `audience:` block. Cheap fix. |

### 4.4 Pipeline-infrastructure debt (NOT chapter-content; track separately)

| # | Issue | Severity | Fix |
|---|---|---|---|
| 4.4.1 | **Orchestrator-resume bug** | P1 infra | Stale `phase_status="running"` from unclean shutdown blocks `--resume`. Workaround: use `--retry-phase <phase>` OR manually edit state.json. Real fix needs heartbeat-age check in `run_resume()` (tracked in P5 sub-task). [See memory.](../../.claude/projects/-Users-asifhussain-PROJECTS-journal/memory/project_orchestrator_resume_bug.md) |
| 4.4.2 | **Cost-ledger silent fail on Python 3.9** | P2 infra | `AttributeError("module 'datetime' has no attribute 'UTC'")` because `datetime.UTC` is Python 3.11+. Cost spend NOT tracked on Python 3.9 runs. Fix: replace `datetime.UTC` with `datetime.timezone.utc` in cost-ledger writer. |
| 4.4.3 | **No `--archetype <name>` flag on orchestrator** | P2 enhancement | The archetype is a reference document. To make it active doctrine for the next book, you'd need to manually append §3+§4 to `_authoring.py` Phase 0e/0g system prompts. Future work: add a `--archetype` flag that auto-injects. |
| 4.4.4 | **No Quranic-quote corpus validator** | P2 enhancement | A4 findings (translator attribution mismatch) require manual verification today. Future F27 validator: `assert_quranic_quote_matches_named_translator()` with corpus of Yusuf Ali, Asad, Pickthall, Sahih International. |
| 4.4.5 | **No template-variable-corruption static check** | P2 enhancement | Phase 0e template variable bugs (§6.1) caught only by challenger semantic A2. Future F27 validator: `assert_no_phase_0e_template_variables()` grepping for known placeholder strings. |

---

## 5. Cost discipline reminder

**Budget for the manual finish**: ~$2–6 total for 11 chapter skeleton calls + $0 for build_episode_txt + $0 for trainer/merge/done. Compare to what we halted: ~$50–100+ over 5.5–9.5h of orchestrator runtime, ending in the same SHIP-WITH-CAUTION verdicts requiring author judgment.

**If you start a `claude -p` call for a skeleton chapter framing, scope it tightly:**
- One call per chapter (NOT multiple iterations).
- System prompt = archetype §3 + §4 only (NOT the full 5,354-word archetype).
- User prompt = "Generate a skeleton 00-framing.md for chapter <slug>, following the archetype. Stop after emitting the file."
- No `--permission-mode acceptEdits` unless you've staged the chapter contract YAML to be read.
- Exit after one file emitted. No fixer loop.

If a single chapter's skeleton call goes >5 min wall clock, kill it and try with a tighter prompt — that's a sign the system prompt is loaded with too much context.

---

## 6. Coordination notes

- **Air will not write to KaR while Studio is driving the manual finish.** Air is parking on this branch.
- **Operator file ownership**: Studio writes `_workspace/plan/operators/mac-studio-primary.md` to record progress. Air will NOT cross-write per [coordination-protocol.md §1](_workspace/plan/operators/coordination-protocol.md).
- **State.json ownership during manual mode**: Studio writes. Air reads only. When Studio finishes manual mode and triggers trainer+merge+done, the orchestrator will re-take state.json write authority for those deterministic phases.
- **Push discipline**: Studio pushes to `book/kitab-al-riyad` after each material milestone (EP10 P1 cleanup ship, EP14 decision, every 2–3 chapter framings, post-trainer). Air monitors via `git fetch` only.
- **If Studio needs to escalate (e.g., archetype rule wrong)**: open the conversation here in this handoff doc as section "## 7. Escalations" — Air will see on next fetch.

---

## 7. (placeholder) Escalations from Studio

*Write here if you need to flag a problem back to the Air. The Air will see it on next `git fetch origin book/kitab-al-riyad`.*

---

**End of handoff. Good luck.**
