# Chapter-set advisory report — sharh-al-masail-ghulam-hussain

Generated: 2026-08-17T15:48:56+00:00
Source: `scripts/podcast/check_chapter_set.py` (challenger Category P)

## Summary
- P0 (would block ship if challenger ran): **0**
- P1 (ship-with-caution): **1**
- P2 (advisory): **1**

## Findings

- **P6** [P2] `maintenance-dissolution-and-inheritance` — chapter text contains 'khums' which belongs to book 'degrees-of-excellence''s mangle-map; possible cross-book bleed
- **P7** [P1] `<set>` — source lines 1-94 (94 lines) are not assigned to any episode (next assigned: sc 1 'Earning, Eating, and the Manners of the Table') — content silently dropped from the split
