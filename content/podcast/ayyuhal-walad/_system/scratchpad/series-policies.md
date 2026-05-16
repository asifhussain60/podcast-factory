# Series Policies — Ayyuhal Walad

**Purpose:** Series-wide directives lifted from `@@policy` markers in episode scratchpads. Each policy augments Stage 12 Hard Rules during refinement.

**Lifecycle:** Policies arrive here from `@@policy` markers, persist until explicitly deactivated, and apply to every refinement pass on every episode in this run.

**Editing this file directly:** Allowed. Set `active: false` to disable a policy without deleting it; remove a block entirely to forget the directive.

---

## Active policies

*(none yet — file initialized at 2026-05-16. The first `@@policy` markers processed will populate this section.)*

---

## Inactive / archived policies

*(none yet)*

---

## How policies augment Stage 12

A policy is added to the prompt context for Stage 12 refinement on every episode. The skill reads Hard Rules 1-8 from the playbook, then appends "Series policies in effect:" followed by every active policy here. The refinement attempts to honor every policy. Policies that contradict Hard Rules are silently overridden by the Hard Rules (Hard Rule 7 in the playbook: policies are additive, never destructive).

If two active policies conflict with each other (rare), the skill flags both in the marker manifest and asks the user to resolve.

## Policy provenance format

Each policy block looks like:

```yaml
- id: P-001
  active: true
  directive: "reduce formality across episodes — more conversational, fewer ceremonial connectors"
  type: voice
  origin:
    scratchpad: scratchpad/episode-01-frame-and-first-counsel.scratch.md
    date: 2026-05-16
    line: 8
  applied_to_episodes: [1]   # populated as each episode is refined under this policy
```

The `applied_to_episodes` field is updated by the skill after each refinement pass — it's a record of which episodes have been refined under this policy.
