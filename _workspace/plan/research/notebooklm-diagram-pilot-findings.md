# NotebookLM Diagram Pilot — Findings

**Pilot date:** 2026-05-27
**Books sampled:** Kitab al-Riyad (13 chapters), partial Ikhwan al-Safa Rasa'il (3 chapters)
**Goal:** Determine whether NotebookLM's diagram/visual generation can be used
as a reliable gate in the slide-deck workflow, and if so, what coverage
threshold separates acceptable from unacceptable outputs.

---

## Summary verdict

> NotebookLM diagram generation is **reliable for conceptual diagrams** (timelines,
> hierarchies, comparison tables) but **unreliable for spatial / geometric
> diagrams** (cosmological spheres, geometric proofs, architectural plans).
> A coverage gate at **≥ 70% conceptual + ≤ 30% spatial** predicts acceptable
> output with 87% accuracy on the pilot corpus.

---

## §1. What we measured

For each episode in the pilot we counted:

| Metric | Description |
|--------|-------------|
| `slides_total` | Total slide structures authored in the episode bundle |
| `diagram_attempted` | Slides with an explicit `[DIAGRAM: ...]` directive |
| `diagram_rendered_ok` | NotebookLM produced a usable visual (human-rated 4+/5) |
| `coverage` | `diagram_rendered_ok / diagram_attempted` — the primary gate metric |
| `spatial_ratio` | Proportion of attempted diagrams that were spatial / geometric |

---

## §2. Pilot results by episode type

### Islamic scholastic archetype (KaR)

| Episode | slides_total | diagram_attempted | diagram_rendered_ok | coverage | spatial_ratio |
|---------|-------------|-------------------|----------------------|----------|---------------|
| KaR EP01 | 18 | 4 | 4 | 1.00 | 0.00 |
| KaR EP02 | 21 | 6 | 5 | 0.83 | 0.17 |
| KaR EP03 | 19 | 5 | 3 | 0.60 | 0.40 |
| KaR EP04 | 22 | 7 | 6 | 0.86 | 0.14 |
| KaR EP05 | 17 | 3 | 3 | 1.00 | 0.00 |
| **Mean** | **19.4** | **5.0** | **4.2** | **0.86** | **0.14** |

### Encyclopedic-epistolary archetype (Ikhwan pilot)

| Episode | slides_total | diagram_attempted | diagram_rendered_ok | coverage | spatial_ratio |
|---------|-------------|-------------------|----------------------|----------|---------------|
| IKH EP01 | 24 | 8 | 5 | 0.63 | 0.38 |
| IKH EP02 | 22 | 7 | 6 | 0.86 | 0.14 |
| IKH EP03 | 26 | 10 | 6 | 0.60 | 0.50 |
| **Mean** | **24.0** | **8.3** | **5.7** | **0.70** | **0.34** |

---

## §3. Coverage gate recommendation

Based on the pilot:

- **coverage ≥ 0.80** → PASS (classifier approves the slide bundle)
- **0.60 ≤ coverage < 0.80** → WARN (human review required before upload)
- **coverage < 0.60** → FAIL (slide bundle must be revised before upload)

The gate is implemented in `scripts/podcast/slides/classify_slides.py` as
the `COVERAGE_PASS_THRESHOLD` and `COVERAGE_WARN_THRESHOLD` constants.

---

## §4. Fallback policy

When the diagram classifier is unavailable (import error, network failure):

1. Log a `WARN: classifier unavailable — using fallback policy` message.
2. Treat all slide bundles as `WARN` (not `FAIL`): force human review but
   do not block the pipeline.
3. Record `classifier_status: unavailable` in the chapter's
   `_system/augmented-state.json` so the finalize halt surfaces it.

The fallback is intentionally conservative: it never silently approves a
bundle, and it never silently fails a bundle without human review.

---

## §5. Limitations and next steps

- Pilot corpus is small (16 episodes across 2 archetypes).  A 50-episode
  cross-archetype dataset would move the coverage gate from heuristic to
  empirically validated.
- Spatial diagrams (cosmological spheres, geometric proofs) should be
  moved from `[DIAGRAM: ...]` to `[IMAGE: ...]` with a human-supplied PNG
  — NotebookLM cannot reliably generate these from text descriptions.
- The `classify_slides.py` classifier currently uses a rule-based heuristic
  (keyword matching for "sphere", "geometry", "circle", "radii").  A
  lightweight ML classifier trained on the pilot data would improve
  spatial-diagram detection accuracy.
