# Kashkole binder-first translation and knowledge-corpus plan

Last reviewed: 2026-08-14

## Purpose

Translate Kashkole from Urdu into articulate English in a deterministic,
binder-first order, then move each successfully closed and verified binder into
the knowledge corpus immediately without creating duplicate atoms.

This plan replaces the earlier largest-topic-first operating order. That order
was efficient by character throughput, but it fragmented usable completion
across binders. The new rule is simple: finish one approved binder
holistically, close its translation and verification gates, import its eligible
atoms into the knowledge corpus, prove the import is idempotent, then move to
the next approved binder.

## Scope

Approved for the working list:

- 16 named binders listed below.

Ignored by Asif and excluded from the execution list:

- دعات اور مناصیب کی سیرت و واقعات
- منتخب اشعار
- منتخب دعاؤں کا مجموعۃ

Held outside this plan:

- The unnamed binder.
- Any topic with zero body text unless it belongs to an approved binder and is
  needed as a structural placeholder.

## Binder order and category map

Order is by current translation completion, closest to completion first. The
category fields are provisional routing metadata for translation, review, and
later knowledge-corpus insertion. They should be stored with the binder manifest
before new translation work resumes.

| Order | Binder | Translation progress | Primary category | Secondary category | Corpus routing note |
|---:|---|---:|---|---|---|
| 1 | Quranic Studies | 100.0% closed | quranic_taveel | haqaiq | Qur'anic exposition, tafsir-like analysis, and deeper interpretive material. Candidate atom level: taveel or haqaiq depending on chapter/topic. Closed 2026-08-14 with 84/84 topics translated and 84 ok after review-topic repair. |
| 2 | The Wise Reminder | 59.1% | quranic_taveel | spirituality | Qur'anic reminder and soul/spirit teachings. Candidate atom level: taveel, advanced, or haqaiq by topic. |
| 3 | دعائم الاسلام : صلواۃ | 56.2% | shariat | mamsool | Prayer law with inner correspondences. Candidate atom level: mamsool for symbolic correspondences, general for plain law. |
| 4 | مسودے | 53.9% | mixed_manuscripts | review_required | Drafts and mixed sessions. Must classify chapter-by-chapter before corpus insertion. |
| 5 | علی ابن ابی طالب علیہ السلام | 35.2% | history_sirah | virtues | Imam Ali material, sermons, letters, virtues, and historical/doctrinal reflection. |
| 6 | ISLAM IMAN IHSAN | 32.0% | doctrine | spirituality | Foundational doctrine and spiritual stations. Candidate atom level: general or advanced. |
| 7 | دعائم الاسلام : ولایت | 30.0% | shariat | doctrine | Walayah as law, doctrine, and inner authority. Candidate atom level: general, advanced, or taveel by topic. |
| 8 | قرآنی قصص الانبیا کے حقائق | 28.0% | haqaiq | quranic_narrative | Inner realities of prophetic narratives. Candidate atom level: haqaiq. |
| 9 | منتخب علمی مضامین | 17.9% | doctrine | hikmah | Selected scholarly essays. Mixed but mostly doctrine, wisdom, death, intellect, and esoteric topics. |
| 10 | توحید مبدع تعالی | 7.1% | tawhid | doctrine | Theology of divine unity and the Originator. Candidate atom level: advanced or haqaiq. |
| 11 | علوم مبدا و معاد | 0.0% | mabda_maad | cosmology | Origin and return, cosmology, intellects, souls, and resurrection. Candidate atom level: mabda_maad. |
| 12 | کلمات ربانی کی تاویلات | 0.0% | taveel | quran_hadith | Interpretations of verses, hadith, surahs, and letters. Candidate atom level: taveel or taveel_haqaiq mapping to supported level taveel/haqaiq. |
| 13 | آداب و اخلاق حسنۃ | 0.0% | akhlaq_adab | ethics | Ethics, manners, sayings, counsel, and conduct. Candidate atom level: general or advanced. |
| 14 | غزالی - کیمیائی السعادۃ | 0.0% | akhlaq_tazkiyah | spirituality | Ghazali-based self-discipline and purification. Candidate atom level: general or advanced. |
| 15 | دعائم الاسلام : الصوم | 0.0% | shariat | mamsool | Fasting law, special nights, and inner correspondences. Candidate atom level: mamsool where symbolic. |
| 16 | دعائم الاسلام : طہارت | 0.0% | shariat | mamsool | Purity law and inner meaning of purification. Candidate atom level: mamsool where symbolic, general where legal. |

## Deterministic execution rules

1. Binder manifest is authoritative.
   The translator reads a manifest with one row per approved binder. Each row
   records binder name, order, primary category, secondary category, status,
   and corpus routing note.

2. One binder is active at a time.
   Workers may run in parallel inside the current binder, but no worker may pull
   work from the next binder until the active binder is closed.

3. Chapter order is stable.
   Within a binder, process chapters by source order if a source numeric order
   is available. If the mirror only has names, use the deterministic order
   already present in the extracted mirror and persist that order into the
   manifest.

4. Topic order is stable.
   Within a chapter, process existing untranslated topics in descending source
   length only if the chapter has no source sequence. Otherwise use source
   sequence. This keeps long work early without crossing binder boundaries.

5. Completion means current source fingerprint.
   A translated topic counts complete only when its stored source hash matches
   the current Urdu title/body and the prompt/category version that produced it.

6. Partial work remains queued.
   A topic with missing windows, failed windows, stale prompt version, or review
   status is not a binder-close pass. It either gets repaired or appears in the
   binder punch list.

7. Categories are locked before corpus insertion.
   Translation can continue with provisional categories, but knowledge-corpus
   insertion must use confirmed category mappings and atom-level rules.

8. Corpus import is part of binder closure.
   A binder is not fully closed merely because translation passed. It reaches
   closed-and-usable status only after the corpus dry-run is clean, duplicate
   handling is reviewed, eligible atoms are inserted, `corpus_sync.py export
   --safe` captures the JSONL source of truth, and the import verification
   confirms the same binder will not create new atoms on rerun.

## Phase 1 - Build the binder manifest

Create a durable manifest for the 16 approved binders. Required fields:

- binder_name
- execution_order
- primary_category
- secondary_category
- translate_status: approved, running, closed, review, ignored
- corpus_status: not_ready, ready_for_mapping, inserted, held
- source_chars
- translated_source_chars
- remaining_source_chars
- topic_count
- translated_topic_count
- review_topic_count
- category_version
- notes

Gate to close the phase:

- The manifest includes exactly the 16 approved binders.
- The three ignored binders are recorded only as ignored scope, not in the
  executable queue.
- Every executable binder has a primary category.

## Phase 2 - Harden translation before resuming

Apply the book-orchestrator hardening patterns to Kashkole:

- Per-window persistence so a long topic can resume mid-topic.
- Retry wrapper around model calls.
- Consecutive-failure circuit breaker.
- Step ledger for title calls, window calls, topic assembly, chapter closure,
  and binder closure.
- Source fingerprint cache that includes Urdu source, prompt version, category
  version, and windowing parameters.
- Bounded worker setting per binder.
- Status command that reports current binder, chapter, topic, window, elapsed
  time, and failure streak.

Gate to close the phase:

- A dry-run shows the next binder queue without translating.
- A one-topic probe can be interrupted and resumed without losing completed
  windows.
- Repeated zero-token or empty-output failures stop the run before the queue is
  churned.

## Phase 3 - Close binders one by one

For each binder in execution order:

1. Mark binder status running.
2. Translate remaining topics chapter by chapter.
3. Reuse current translations whose source fingerprint still matches.
4. Store every completed window before moving to the next window.
5. Assemble each topic from stored windows.
6. Run topic gates.
7. Run chapter closure after every chapter.
8. Run binder closure only after every chapter closes.

Binder closure gates:

- All non-empty topics have current English.
- No topic is shorter than the minimum length gate unless explicitly accepted.
- Qur'anic Arabic quoted in the Urdu source survives in the English rendering.
- Topic title English exists for every translated topic.
- Category metadata exists on every topic through binder default or chapter
  override.
- Review items are listed with exact topic id, chapter, concern, and repair
  path.

## Phase 4 - Repair review items before moving on

The current known review set is inside the first two binders:

- Quranic Studies: four review topics.
- مسودے: two review topics.

Repair rule:

- Prefer surgical repair for a single missing Qur'anic run.
- Rerender only the affected window when surgical repair cannot be proven.
- Never rerender a full large topic to fix one isolated verse unless the stored
  window provenance is missing.

Gate to close the phase:

- The binder has zero unexplained review items, or Asif explicitly marks the
  item accepted for later human review.

## Phase 5 - Prepare the binder's knowledge-corpus import

Do not insert Kashkole topics into the atom store merely because they are
translated. After a binder has passed translation and verification, create a
mapping layer that turns its translated topics into knowledge-corpus records
with explicit provenance.

Required mapping:

- Atom id: doctrine:kashkole:<topic_id>:<chunk_index>. Long topics are split
  into stable, paragraph-preserving chunks so augmentation can use focused atoms
  instead of flooding prompts with an entire translated topic.
- Atom type: doctrine by default; poetry and hadith remain out of this binder
  plan unless separately approved.
- Tradition: fatimid-ismaili unless a topic is explicitly universal.
- Text: rendered English from topic_translation.
- Source: Kashkole binder, chapter, topic id, Urdu title, source hash.
- Category tags: primary_category, secondary_category, binder slug, chapter slug.
- Content level: one of the supported ladder values only:
  general, advanced, taveel, mamsool, mabda_maad, haqaiq.
- Dedup key: first exact source topic id, then normalized English text, then
  near-duplicate comparison inside the same binder/category/verse block.
- Quran references: stored as `quran_refs` on the doctrine atom and linked to
  existing `quran:S:A` atoms; never create a second atom for the same verse.
- Usage eligibility: only PASS topics are automatically eligible. WARN topics
  stay out of augmentation until their review item is explicitly accepted.
- Empty structural topics with zero source and zero English body are counted in
  the report but do not create atoms.

Category-to-content-level defaults:

| Primary category | Default content_level |
|---|---|
| quranic_taveel | taveel |
| taveel | taveel |
| haqaiq | haqaiq |
| mabda_maad | mabda_maad |
| shariat | general |
| tawhid | advanced |
| doctrine | general |
| history_sirah | general |
| akhlaq_adab | general |
| akhlaq_tazkiyah | advanced |
| mixed_manuscripts | advanced |

Override rule:

- Chapter and topic classifiers may raise general to advanced, taveel, mamsool,
  mabda_maad, or haqaiq, but they may not invent new content levels without a
  schema change.

Gate to close the phase:

- A dry-run report lists proposed new atoms, exact duplicates, near duplicates,
  held WARN topics, missing category tags, unsupported content levels, and Quran
  refs that could not be normalized.
- Every proposed atom has binder, chapter, topic id, chunk index, Urdu title,
  source hash, English text hash, category tags, and content level.
- Every near duplicate is either mapped as an existing atom/source variant or
  held for manual review.

## Phase 6 - Insert each closed binder into the knowledge corpus

The insertion pass is binder-gated:

1. Read the closed binder manifest.
2. Read translated topics for that binder.
3. Build proposed atom records.
4. Run a dry-run diff against knowledge.db.
5. Insert only when the diff is stable and reviewed.
6. Run the same insertion again as an idempotency check.
7. Export the committed corpus JSONL source of truth.
8. Stamp corpus_status inserted in the binder manifest.

Corpus insertion gates:

- No ignored binder is inserted.
- No untranslated topic is inserted.
- No review topic is inserted unless explicitly approved.
- No atom is inserted without category tags.
- No atom uses a content_level outside the supported ladder.
- Re-running insertion is idempotent.
- No Quran verse atom is duplicated; teachings reference existing Quran atoms by
  `quran_refs`.
- No near duplicate is silently inserted as a fresh atom.
- `content/knowledge-base/*.jsonl` reflects the inserted atoms after export.

Binder-close command sequence:

1. `python3 scripts/podcast/intelligence/translate_kashkole.py --status`
2. Run the binder verification gate and repair every non-accepted review item.
3. Run the binder corpus-import dry-run.
4. Review duplicate and held-topic report.
5. Apply the binder corpus import.
6. Rerun the same import and verify zero new atoms.
7. `python3 scripts/podcast/intelligence/corpus_sync.py export --safe`
8. Update the binder manifest: translation status closed, corpus status inserted.

## Phase 7 - Operating cadence

Recommended cadence:

1. Build manifest.
2. Harden translator.
3. Quranic Studies closed on 2026-08-14.
4. Run Quranic Studies corpus-import dry-run now.
5. Review duplicate/held-topic report.
6. Insert the verified Quranic Studies atoms and export JSONL.
7. Continue binder by binder in the approved order, starting with The Wise Reminder.
8. For every future binder, repeat translation closure, verification, dry-run,
   reviewed insert, idempotency check, JSONL export, then move on.

## Open decisions for Asif

1. Confirm whether the provisional categories above are acceptable as the first
   category manifest.
2. Decide whether mixed_manuscripts should be translated as one binder or split
   by chapter category before completion.
3. Decide whether shariat binders should create doctrine atoms immediately or
   wait for a dedicated fiqh/shariat atom subtype. Until then, shariat binders
   may close translation but their corpus_status stays held.
4. Decide whether history_sirah should remain doctrine-type atoms or get a
   distinct corpus type later. Until then, history_sirah binders may close
   translation but their corpus_status stays held.

## What is needed to import atoms now

For the already closed Quranic Studies binder, the missing implementation work
is not another plan. It is the binder import command that reads verified
`topic_translation` rows from `mirror.db`, maps them into atom records, runs the
duplicate/near-duplicate report, writes eligible atoms to `knowledge.db`, and
exports the JSONL corpus source of truth.

Required inputs:

- Closed binder identity: Quranic Studies.
- Verified topic translations: 84/84 translated and repaired.
- Category mapping: primary `quranic_taveel`, secondary `haqaiq`.
- Content-level default: `taveel`, with topic overrides to `haqaiq` only when
  the verified category demands it.
- Duplicate policy: exact topic id and normalized English text merge as existing
  sources; near duplicates are held for review.
- Verse policy: Quran references become `quran_refs`; verse atoms are linked,
  never recreated.

Required outputs:

- Binder corpus-import dry-run report.
- Inserted doctrine atoms for eligible verified topics.
- Manual-review entries for unresolved near duplicates or unsupported mappings.
- Safe JSONL export of the updated corpus.
- Binder manifest updated to `corpus_status: inserted`.
