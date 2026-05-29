<!--
  SINGLE LIVING SOURCE for "where the Podcast Factory Astro Site work stands."
  The SessionStart hook (.claude/hooks/site-work-status.sh) injects this into every
  new conversation so the next session inherits context with zero re-reminding (WC7e).
  KEEP IT SHORT (a screen at most) and CURRENT — update the three fields below at the
  end of any site-work session. Stale status is worse than none.
-->
# Site work — current status

**Last updated:** 2026-05-29

**In progress:** Cortex standard hardening (WC7) — just completed: standard relocated to
`docs/standards/html-view-quality.md`, rules de-duplicated to one source + a one-screen
digest, a deterministic lint gate (`npm run lint:views`) wired into pre-commit + build,
and this session-continuity hook.

**Last decision:** Per-view redesigns (WC6 follow-on) are discussed with Asif ONE PAGE AT
A TIME before any change. The lint gate's blocking tier covers the 12 view pages + layouts
(currently green); `<style>`-block extraction, SVG a11y triples, and NarrativeBase's
skip-link are tracked as non-blocking warnings, not silently rewritten.

**Next step:** Asif chooses the first view to redesign one-at-a-time, OR opts to burn down
the lint warning backlog (`npm run lint:views` → 67 warnings) as a separate pass.

---

*How to use: the rules for HOW views are built live in
[docs/standards/html-view-quality-digest.md](../../docs/standards/html-view-quality-digest.md)
(MUST card) and [the full standard](../../docs/standards/html-view-quality.md). WHAT each
view shows is agreed per-page. Run `npm run lint:views` from `plan-dashboard/` to see the
current conformance state.*
