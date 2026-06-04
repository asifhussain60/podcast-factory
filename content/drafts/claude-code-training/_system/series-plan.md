# Series Plan — Claude Code Training

**Book slug:** `claude-code-training`
**Branch:** `site/claude-code`
**Generated:** 2026-06-02T20:32Z
**Orchestrator:** v1.2
**Unit mode:** `auto`
**Status:** AWAITING HUMAN APPROVAL

---

## Human-reviewed sections

### Length tier (AI recommendation)

**Tier:** `extended`
**Rationale:** All chapters target the same length tier — series is balanced.

### Essentiality recommendations

Episodes the LLM flagged as **optional**, **bonus**, or **skip** during Phase 0d
content analysis. CORE episodes are not listed (the default; cannot be removed
without breaking the arc). To act on a `skip` recommendation, delete the
contract + chapter file before resuming.

| # | Slug | Essential? | Why |
|---|---|---|---|
| — | — | — | All episodes flagged `core`. No essentiality concerns. |

### Episode list

Columns:
- **Format** — `deep_dive` (Mentor+Student exposition) | `debate` (named voices clash + arbiter) | `narrative` (historical/biographical) | `interview` (Q&A)
- **Essential** — `core` | `optional` | `bonus` | `skip` (see Essentiality recommendations above)
- **Upload** — file to drop in NotebookLM's *Sources* panel
- **Customize** — file whose contents go in NotebookLM's *Customize* box (written by Phase 0g)
- **Length cue** — what to declare in the customize prompt's opening directive
- **Hosts** — host pairing for NotebookLM's customize prompt

| # | Title | Words | Tier | Format | Essential | Upload (NotebookLM source) | Customize | Length cue | Hosts |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Claude Code vs GitHub Copilot — What's Different and Why It Matters | 6899 | extended | **deep_dive** | core | `chapters/ch01-copilot-to-claude-code-mental-shift.txt` | `episodes/EP01-copilot-to-claude-code-mental-shift.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 2 | How Claude Code Actually Works — The Agentic Mental Model | 8358 | extended | **deep_dive** | core | `chapters/ch02-how-claude-code-actually-works.txt` | `episodes/EP02-how-claude-code-actually-works.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |
| 3 | Getting Up and Running with Claude Code — Your First Session | 9246 | extended | **deep_dive** | core | `chapters/ch03-first-session-walkthrough.txt` | `episodes/EP03-first-session-walkthrough.txt` (TBD post-0g) | "target a 30–45 minute conversation" | Mentor + Scholar Companion |

### Source-chapter → episode map

| source chapter | source title | episode(s) | split reason |
|---|---|---|---|
| 1 | EP01 Source: Claude Code for Copilot Users — Understanding the Shift | ch01-copilot-to-claude-code-mental-shift.txt | Author pre-segmented as Episode 1 of 3 with discrete pedagogical purpose (the mental-model shift from autocomplete to agentic). 1:1 source-chapter→episode mapping honored; 2,885 source words expanded faithfully to 5,791 to land inside the Extended-tier word band without inflating the argument or introducing claims absent from the source. |
| 2 | EP02 Source: How Claude Code Actually Works — The Agentic Mental Model | ch02-how-claude-code-actually-works.txt | Author-segmented as Episode 2 of 3 with a single coherent eight-part architectural tour (loop, tools, CLAUDE.md, slash commands, hooks, MCP, permissions, cost); honored as one chapter — splitting would fragment the mental model EP03's hands-on session depends on, merging with neighbors would conflate the *what* with the *why* (EP01) or the *how* (EP03). Source 3,365 words expanded to 7,675 via faithful prose elaboration into the extended tier band. |
| 3 | EP03 Source: Getting Up and Running with Claude Code — Your First Session | ch03-first-session-walkthrough.txt | Author-segmented as Episode 3 of 3 — the practice capstone of the why/what/how arc — covering prerequisites, installation, authentication (with the ANTHROPIC_API_KEY billing trap), VS Code integration, first-session walkthrough, day-one workflows, undoing and recovery, CLAUDE.md setup via /init, the ten Copilot-user gotchas, command reference, configuration, and the day-one checklist as the listener's action plan; honored as one chapter — splitting would fragment the action plan, merging with neighbors would conflate the *how* with the *what* (EP02). Source 3,144 words expanded to 8,238 via faithful prose elaboration into the extended tier band. |

---

## Audit-trail-only sections (no human review)

### Audience (orchestrator config default)
Senior software developers with two or more years of daily GitHub Copilot use in VS Code, technically fluent and asking from a position of competence rather than frustration — they want to understand what Claude Code adds to their existing workflow, not be sold on switching tools.

### Angle (orchestrator config default)
faithful_exposition

### Host dynamic (AI-selected per chapter)
| Chapter | Host dynamic | Rationale |
|---|---|---|
| `copilot-to-claude-code-mental-shift` | curious_mind + scholar_companion | Scholar_companion is the experienced Claude Code practitioner who has made the Copilot-to-Claude-Code transition himself and respects Copilot enough not to argue against it; curious_mind is the senior software developer with 2+ years of daily Copilot use, asking pointed questions from competence rather than ignorance, who wants to understand what Claude Code adds rather than be won over. |
| `how-claude-code-actually-works` | curious_mind + scholar_companion | Scholar_companion is the experienced Claude Code practitioner who builds the agentic mental model from scratch using concrete tool-by-tool explanations; curious_mind is the senior software developer with two-plus years of daily Copilot use who has listened to EP01, accepts the architectural framing, and now wants the mechanics — her question hooks are 'how does that actually work?', 'what's the closest Copilot analogy?', and at key moments 'so this is genuinely new territory — how do developers handle it?' |
| `first-session-walkthrough` | curious_mind + scholar_companion | Scholar_companion is the experienced Claude Code practitioner who has guided many Copilot users through the first session and knows exactly where the friction points are — he anticipates them before the student hits them and validates each one as real friction rather than dismissing; curious_mind is the senior software developer with two-plus years of daily Copilot use who has internalized episodes one and two and is ready to go from understanding to doing — her question hooks are practical ('do I uninstall Copilot first?', 'I have ANTHROPIC_API_KEY set already — does that cause issues?', 'I am looking at a terminal prompt with no suggestions — where do I start?', 'how do I know if the context window is getting full?'), and her energy is forward-moving rather than impatient. |

---

## NotebookLM input checklist (per-episode workflow)

After Phase 0g writes the per-episode customize prompts, for each episode:

1. **Open NotebookLM** → "+ New notebook" (or use existing per-book notebook)
2. **Sources panel** → "+ Add source" → "Upload from file" → select the file
   listed in the **Upload** column of the Episode list
3. **Customize panel** (top right) → "Customize" → paste the entire contents of
   the **Customize** file
4. The customize prompt already declares: length cue, host pairing, format
   (deep_dive vs debate), focus areas, pronunciation block, tone constraints
5. **Generate** → ~10–15 min for NotebookLM to render audio
6. **Download** the MP3 → save at `audio/EP##-<slug>.mp3`
7. **Transcribe** via `python3 scripts/podcast/transcribe_episode.py`
   → drops at `transcripts/EP##-<slug>.transcript.txt`
8. **Audit** via `python3 scripts/podcast/audit_transcript.py <BOOK_DIR> EP##-<slug>`
   — catches Arabic pronunciation drift, missing phonetic cues, fabricated quotes
9. If audit flags issues: edit `pronunciation.md` overrides → re-paste customize
   prompt → re-generate

---

## Next step

Review the **Length tier**, **Essentiality recommendations**, **Episode list**,
and (if shown) **Source-chapter → episode map**.

If everything looks correct: `python3 scripts/podcast/orchestrate_book.py --resume claude-code-training`

If an episode's segmentation, title, format, or host_dynamic needs fixing: edit
the relevant `chapter-contracts/<slug>.yml` and `chapters/ch##[a-z]?-<slug>.txt`,
then re-invoke `--resume`. The orchestrator detects the change and re-validates.

If the tier choice is wrong: edit every `chapter-contracts/<slug>.yml` to
the desired `length_target`, then re-invoke `--resume`.

If you want to change unit mode (chapter ↔ section ↔ auto), reset Phase 0d:
  `python3 scripts/podcast/orchestrate_book.py --resume claude-code-training --retry-phase 0d`
(then edit `_system/orchestrator-state.json` `config.unit_mode` before resuming)
