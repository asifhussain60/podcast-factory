# Tradition Whitelists

This directory holds tradition-specific YAML files that the `/podcast` skill loads on demand based on the detected or user-specified `source-tradition`.

## Files

| File | Status | Use when |
|---|---|---|
| `ismaili.yml` | Comprehensive | Source is from the Ismaili tradition (Fatimid, classical, or modern) |
| `islamic.yml` | Starter | Source is broadly Islamic but not specifically Ismaili |
| `christian.yml` | Starter | Source is Christian (specify branch in source text if relevant) |
| `philosophical.yml` | Starter | Source is philosophical (Western, Eastern, or comparative) |
| `scientific.yml` | Starter | Source is scientific (peer-reviewed papers, scientific essays) |
| `literary.yml` | Starter | Source is literary (novels, fiction, poetry, plays, literary essays) |

## When the skill uses these

The `/podcast` skill loads exactly one of these files per run, determined by:

1. User-specified `source-tradition=<name>` flag, OR
2. Auto-detected tradition from Stage 04 (if confidence ≥ 0.80), OR
3. User confirmation prompt (if confidence 0.60–0.79), OR
4. Default to `none` (no file loaded; generic enrichment only) if all of the above fail.

## When no tradition file is loaded

If `source-tradition=none` (explicit or default), the skill uses only:
- Generic historical context relevant to the source's period.
- Modern analogies from neutral domains (engineering, daily life, mentorship in general).
- No tradition-specific quotations or teachings.

## Generic-only posture

None of these files is privileged in skill code. The Ismaili whitelist's depth comes from curation, not from any code path. To support a new tradition, add a new `<name>.yml` with the same schema.

## Schema

Each file uses the same YAML schema:

```yaml
name: <tradition-name>
description: <short description>

figures:
  - <figure 1>
  - <figure 2>

signal_terms:
  - <term 1>
  - <term 2>

allowed_enrichment_sources:
  - <source 1>
  - <source 2>

forbidden_enrichment_sources:
  - <source 1>

tone_preferences:
  - <preference 1>

modern_analogy_register:
  preferred_domains:
    - <domain 1>
  acceptable_domains:
    - <domain 1>
  avoid_domains:
    - <domain 1>

quote_attribution_requirements:
  - <requirement 1>
```

## Expanding a starter file

Starter files (islamic, christian, philosophical, scientific, literary) are deliberately minimal. To expand:

1. Add figures to the `figures` list with consistent naming.
2. Add signal terms (vocabulary that suggests this tradition) to `signal_terms`.
3. Add specific allowed sources to `allowed_enrichment_sources` — the more specific, the better.
4. Add forbidden sources to prevent silent enrichment from those sources.
5. Refine `tone_preferences` based on observed behavior on real sources.
6. Refine `modern_analogy_register` based on what reads well in podcasts.

Every expansion is a manual curation step. The skill never auto-expands these files.
