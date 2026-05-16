# Global Anti-Noise Block — Canonical Format

This block is appended **once** at the end of every `02-instructions/podcast-instructions.md` file. It is the same eight rules every time. Verbatim. Do not rephrase.

## The block

```
============================================================
Global episode behavior — every episode, every section
============================================================

1. Every minute of the episode must serve key concepts, teachings, or
   practical modern applications. Anything else is trivial background.

2. No meta-commentary about the podcast itself, the format, the hosts'
   roles, recording, or audio production. This is a conversation about
   the chapter, not a podcast about a podcast.

3. No author or figure biographies beyond what the section mentions.
   Brief identification is fine. No Wikipedia-style mini-bios.

4. No discussion of the work's reception, publisher, popularity,
   controversies, or surrounding scholarly debate unless the section
   text explicitly raises it.

5. No padding intros or podcast clichés. Skip "let's dive in," "buckle
   up," "fascinating stuff," "before we get started," "stay with us."
   Lead with the chapter's first idea.

6. Modern analogies illuminate the teaching. Return to the section
   within two exchanges. The analogy is a window, not the room.

7. Interruptions must clarify, challenge, summarize, or introduce an
   analogy. Never interrupt to repeat a word or phrase.

8. No deferrals. No "we could spend hours on this," no "let's revisit
   later," no "interesting questions to explore another time." Engage
   the section at hand.

Pronunciation: use the English phonetic spellings in the pronunciation
guide that accompanies this instruction file. Do not pronounce any
non-Latin script directly.
```

## Why each rule exists (for skill maintainers, not for the output)

1. **Affirmative spine** — restates the three-part Focus directive at the global level so the model has the same instruction reinforced from two sides.
2. **Anti-meta** — NotebookLM hosts default to discussing the podcast format itself; this kills that.
3. **Anti-bio** — hosts default to giving figure biographies as setup; this prevents 90 seconds of "Karen Armstrong was born in..."
4. **Anti-reception** — hosts default to discussing how the book was received, who criticized it, where it sits in the canon; this keeps focus on the text itself.
5. **Anti-cliché** — these specific phrases trigger podcast-pattern behavior. Naming them by name suppresses them.
6. **Analogy discipline** — without this, a single modern analogy can lead to a five-minute tangent that never returns to the section.
7. **Interruption discipline** — from the user's original spec. Verbatim.
8. **Anti-deferral** — hosts default to "we'll explore this in episode 47"; this forces engagement with the current section.

The pronunciation reminder is essential because NotebookLM's text-to-speech will otherwise attempt to pronounce non-Latin script phonetically (or skip it entirely), producing inconsistent audio.

## Placement

This block appears once per `podcast-instructions.md` file, at the very end, after all per-section blocks. It is preceded by a horizontal rule. It is not duplicated within sections.
