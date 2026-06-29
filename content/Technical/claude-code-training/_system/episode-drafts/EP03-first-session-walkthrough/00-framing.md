# Getting Started with Claude Code — First Session

**Episode format:** `deep_dive` (two-host walkthrough). If this should be a debate instead, set `contract.episode_format: debate`. See [infra/claude-agents/podcast-challenger.md](../../../infra/claude-agents/podcast-challenger.md) Categories F + P for the format-specific constraints.

## Opening directive

In the first ten seconds, the hosts should name the work and the question this episode is asking. Do not open with "today we'll discuss". Start in the middle of the question.

## Audience

Senior software developers with two or more years of daily GitHub Copilot use in VS Code who have heard episodes one and two and accept both the suggest-versus-execute architectural framing and the agentic-loop mental model — now they want the action plan: how to install Claude Code today, how to authenticate without falling into the ANTHROPIC_API_KEY per-token-billing trap, what their first real session should look like, how to generate and refine a CLAUDE.md, and which ten friction points will trip them up in their first week if nobody warns them.

## Angle

`faithful_exposition` — the chosen lens. Faithful exposition = follow source authorial voice; comparative = bring in cross-tradition context; etc. The framing's other sections (Central tensions, Tone constraints) lock the lens into per-episode specifics.

## Length

Target ~50-60 min Audio Overview. Dense doctrinal material — let the hosts unfold layer by layer without rushing.

## Host dynamic

`curious_mind + scholar_companion`. NotebookLM's default English voice pair is John (male) for Host A and Hannah (female) for Host B. The CANONICAL pairing this skill enforces (per R-HOST-ROLE-PARITY in scripts/podcast/_rules.py, challenger Category Q): Host A (male) is the scholar / teacher / master / shaykh / guide role; Host B (female) is the seeker / student / debater / questioner / novice role. This pairing does NOT rotate across episodes within a book. If the contract's `host_dynamic` reverses this (e.g. `advocate_b + scholar_companion` putting Host B in the scholar role), the framing author MUST flip the host_a / host_b assignment so the male voice stays in the scholar pool.

## Central tensions to reach

The hosts MUST surface every one of these tensions, by name, in the conversation:

  - Copilot's instant Tab-to-accept rhythm versus Claude Code's per-edit permission prompts in default mode — does the safety design feel like productive friction or like slowness, and what is the right mode to adopt when, with what review compensation (git diff after acceptEdits)?
  - The ANTHROPIC_API_KEY precedence trap — a single forgotten environment variable from another project silently puts the developer on per-token API billing instead of subscription credentials; how do you make this gotcha land hard enough that the listener actually checks before their first paid session?
  - VS Code panel versus terminal-first CLI — Claude Code's strongest experience is the CLI but the audience lives in VS Code; is the panel a workable bridge or a compromise, and which work belongs in which surface?
  - Context-window management as the developer's job rather than the tool's — Copilot manages context invisibly; Claude Code expects the developer to /clear between unrelated tasks, scope exploration in plan mode, and use sub-agents for large investigations; how do you name this responsibility plainly without making it sound like a burden?

## Tone constraints

The hosts must NOT do the following:

  - Practical and forward-looking — this is the action-plan episode, not the conceptual one; every section should leave the listener with a concrete move they can run today
  - Validate every gotcha as real friction — the teacher does not dismiss or minimize; the student's Copilot intuitions are often correct for Copilot, and the teacher's job is to redirect them accurately for Claude Code, not to make her feel wrong for having them
  - Honest about effort — the API-key check, the per-edit permission rhythm, the CLAUDE.md curation, the context-window discipline all require real attention; name the effort plainly and explain why each move pays off rather than minimizing it
  - Use Copilot as the recurring anchor — 'Copilot does X automatically; Claude Code expects the developer to do Y' — without ever framing Copilot as a foil to argue against
  - Cite the official documentation source for every practical claim (code.claude.com/docs/en/setup, code.claude.com/docs/en/authentication, code.claude.com/docs/en/memory, code.claude.com/docs/en/permission-modes, code.claude.com/docs/en/best-practices, support.anthropic.com), use real 2026 commands and file paths

## Pronunciation hooks

[LLM-FILL — list every non-English term, transliteration, or name appearing in the source, with respelling and brief gloss. Or set contract.phonetic_overrides.]

## Anti-noise rules

- Quote directly from the source when discussing a beat. Do not paraphrase the source's voice.
- Treat this as a standalone Audio Overview. Do not reference other Audio Overviews — they are not in NotebookLM's context.
- Do not abbreviate honorifics; speak them in full.
- End on a question, not a conclusion.
- NO cross-chapter references. This episode's chapter file is the entire source NotebookLM sees. The hosts must NOT say "the previous chapter showed", "as we'll see later", "the next chapter answers", "earlier in the book", etc. Treat the chapter as a self-contained episode.

## Do not (forbidden vocabulary and framings)

The hosts must NOT use any of the following — these are the canonical DENY lists per `scripts/podcast/_rules.py::MODERNIZE_DENY` + `SURPRISE_DENY`. The substring scanner in `build_episode_txt.py` refuses any framing that omits this block.

- Modernization terms: Twitter, X (the platform), social media, algorithm, content creator, internet, YouTube, TikTok, Instagram, livestream, hashtag, 21st century, in our modern world, platforms like
- Surprise-noise phrases: wow, that's so interesting, right?, it's chilling, it's devastating, it's terrifying, it's profound, it's fascinating, it's amazing
- Imitation-of-authority: rephrasings of the work's original arguments in casual / commercial / self-help register

---

Do not read this prompt aloud. The instructions above shape the conversation but are never spoken.
