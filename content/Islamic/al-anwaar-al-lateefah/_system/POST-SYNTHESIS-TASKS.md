# Post-synthesis tasks — al-anwaar-al-lateefah

These run AFTER `multi_source_synthesis.py` completes (state → `0c`) and BEFORE any
chapter design (0d). Deliverable = a proposal for Asif's approval. Do NOT run 0d
until he approves the structure.

## Task 1 — Volume / physical structure decision (LOCKED REQUIREMENT, added by Asif)

This is a humongous corpus (65-lecture spine = 1,093 spine teachings + 7 augmentation
corpora / 91 lectures). A single flat book with 4 categories would overwhelm the
reader/listener. With FULL synthesized context, determine the physical structure:

- **Should Tawheed (Unity), Mabda' (Origin), and Ma'ad (Return) each become a SEPARATE
  INDEPENDENT VOLUME** (vs one book with category sections)? Where does Metaphysical
  (Hijab, mohtajib, ranks of the dignitaries) belong — its own volume, or folded in?
- **How many logical volumes** does the material actually support? Justify the count
  from the teaching distribution in `_teaching-ledger.json` (count source=spine teachings
  per category; a category with enough distinct, non-overlapping teachings to sustain
  multiple deep-dive episodes warrants its own volume).
- Recommend a concrete physical layout. The repo's native mechanism is the multi-volume
  **work**: parent `content/Islamic/<work-slug>/` with `work.yml` + `vol-01/ … vol-NN/`
  (each a normal book dir), ONE branch per work (`branch_for_work` in `_branching.py`,
  `_paths.py` volume resolution, `work_rollup_status`). Map the proposed volumes onto
  that structure (slugs, titles, which categories → which volume).
- Per-volume: episode split, Tawheed sequenced simple→deep across its episodes, density
  sized to NotebookLM's sweet spot, no teaching repeated within OR across volumes/episodes
  (every teaching ID lands in exactly one place — track via the unified ledger).

## Task 2 — All augmentation accounted for (LOCKED REQUIREMENT, added by Asif)

EVERY augmentation fact from the 7 Urdu-lecture corpora transcribed yesterday
(ansaar-bhai, hazrat-zia, ibrahim-2011, ibrahim-2015, mabda-maad-2002,
mabda-maad-gh-2022, misc) must be ACCOUNTED FOR — either merged into the prose (genuine
gap that extends a spine teaching) or captured as an enrichment atom candidate. Nothing
silently dropped except true audio noise. Verify against `_curation-log.md`'s
"Augmentation disposition" table + `_atom-candidates.jsonl`; report any aug lecture span
with no disposition. Show, per volume, which augmentation corpora feed it.

## Output

Present Task 1 + Task 2 as ONE proposal (recommended volume structure first, with the
volume count + rationale), then STAND BY for Asif's approval. No 0d, no chapter design,
no file restructuring until approved.
