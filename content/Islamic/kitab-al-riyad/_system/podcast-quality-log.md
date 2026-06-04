# Kitab al-Riyad — Podcast Quality Log

**Per-book learnings, captured across the iteration loop.** Updated by the
human-in-loop reviewer (Asif) after each episode's audit. Read by all
subsequent KaR episodes' customize prompts so each one starts with the
previous episode's lessons baked in.

For the framework-level / cross-book learnings, see
[`content/podcast/.skill/handbook/learning-log.md`](../../../../.skill/handbook/learning-log.md)
— those propagate to EVERY book, not just KaR.

---

## Iteration cap (so we don't loop forever)

- **Max 3 in-episode iterations** per episode (regenerate + re-audit cycle)
- If iteration 3 still fails on a HIGH-severity dimension, the issue is
  NOT episode-specific — escalate to a framework-level fix:
  - For Arabic terms: update `pronunciation.md` (book-level) or the shared
    Arabic manifest (cross-book)
  - For citation rules: update the framework Phase 0g prompt in
    `scripts/podcast/_authoring.py` AND log to handbook learning-log.md
  - For structural issues: update the chapter contract's
    `tone_constraints` or `anchor_passages`
- The 3rd iteration's audit result becomes "best effort" and gets logged
  here as a known caveat for this episode

## Success threshold per episode

Episode is **ship-ready** when ALL of:

| Dimension | Pass criterion |
|---|---|
| Arabic pronunciation | 0 mispronounced terms in transcript (per `audit_transcript.py`) |
| Citation fidelity | 0 fabricated Quranic verses / hadith / named-source quotations; verbatim quotes within ±2 words of source |
| Doctrinal accuracy | Does not contradict the chapter contract's `anchor_passages` or `key_tensions` |
| Listenability (Asif's call) | Subjective yes to "I'd listen to another episode like this" |
| Length | Within ±20% of the contract's `length_target` band (Extended = 30-45 min) |

LOW/MED issues are recorded but do not block ship-ready.

## Audit categorization

Every finding goes in one of three buckets. The bucket determines where the fix lands:

| Bucket | Symptom | Fix lands at | Affects |
|---|---|---|---|
| **Per-episode** | Only this episode's customize prompt missed something | `episodes/EP##-<slug>.txt` (edit + re-paste to NotebookLM) | Just this episode |
| **Per-book (KaR-wide)** | Same issue would happen in any KaR episode | `pronunciation.md` overrides OR this file's "KaR patterns" section | All future KaR episode regenerations |
| **Cross-book (framework)** | Same issue would happen in ANY book | Handbook `learning-log.md` + propagate to Phase 0g prompt | All future books in the pipeline |

---

## Per-episode log

Format per row: episode → iteration → outcome + key findings. Add a row each iteration.

| Episode | Iter | Outcome | Pronunciation | Citations | Doctrine | Listen | Length | Notes |
|---|---|---|---|---|---|---|---|---|
| EP05-the-intellect-as-the-first-creation | 1 | (pending) | ? | ? | ? | ? | ? | First test episode chosen 2026-05-21. Review when transcript audited. (Renumbered EP06→EP05 on 2026-05-23 per purely-sequential directive.) |

(More rows appended as iterations run.)

---

## KaR-specific patterns observed (apply to future KaR episodes)

(Empty — populated as findings accumulate. Format: `Pattern: <what to do>. Reason: <observed in EP##>. Applies to: <future episodes/scope>.`)

---

## Episodes shipped

(Empty — populated when an episode passes the success threshold.)
