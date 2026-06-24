<!--
  SINGLE LIVING SOURCE for "where the work stands." The SessionStart hook
  (.claude/hooks/site-work-status.sh) injects this into every new conversation so
  the next session inherits context with zero re-reminding (WC7e). KEEP IT SHORT and
  CURRENT. Recover older entries from git history when needed.
-->
# Current work - status

**Last updated:** 2026-06-24 2:38 PM EST (Al Anwaar approval, noise, and Arabic P0 fixes)

**Current branch merged into develop:** Islamic/al-anwaar-al-lateefah.

**What changed:** Studio Save & Approve now keeps its button label stable and shows
the approval result through a Radix toast. Al Anwaar reference-tail noise is now a
pipeline noise class and has been stripped from current chapters. Islamic scholarly
chapters now persist glossary-backed Arabic script in chapter text, while phonetic
respelling remains in the glossary / Customize prompt. Finalize G13 blocks Islamic
books that do not have Arabic in chapters.

**Current Al Anwaar state:** vol-01 has a 27-entry glossary and Arabic script in
all 11 chapters. Ship validation passes all 14 gates, including G13
`arabic-script-in-chapters`.

**Site verification:** lint:views clean; Astro check has 0 errors and only existing
hints. Headless Chrome verified baked-in Arabic visible in the Studio editor, no
duplicate Arabic chips when the toggle is clicked, and Save & Approve text stable.

**Prior Studio status carried from develop:** Session 32 reworked the Studio Arabic
review/editor shell, unified action panel, Noise tool, raw Arabic styling, reading
width, and left-gutter mark icons. Deferred design decisions remain: NarrativeScroll
theme exception/retheme, REQ-010 typography sweep, section ids/number markers,
figure wrappers, print/smooth-scroll/metadata polish, system-map density split, and
SpendChart dead-code removal.
