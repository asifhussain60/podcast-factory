<!--
  SINGLE LIVING SOURCE for "where the Podcast Factory Astro Site work stands."
  The SessionStart hook (.claude/hooks/site-work-status.sh) injects this into every
  new conversation so the next session inherits context with zero re-reminding (WC7e).
  KEEP IT SHORT (a screen at most) and CURRENT — update the three fields below at the
  end of any site-work session. Stale status is worse than none.
-->
# Site work — current status

**Last updated:** 2026-05-29

**In progress:** Cortex standard hardening (WC7) — SHIPPED + pushed to `origin/develop`
(commits up to `3a8f263`). Standard at `docs/standards/html-view-quality.md` + one-screen
digest; deterministic lint gate (`npm run lint:views`) wired into pre-commit + prebuild;
SessionStart continuity hook live. Astro scoped `<style>` accepted as DoD-compliant; only
oversized blocks (>50 lines) flagged.

**Last decision:** Astro scoped `<style>` blocks are DoD-compliant (compile to scoped
external CSS) — gate flags only oversized page-stylesheets. Per-view redesigns + any
shipped-view styling change are discussed ONE PAGE AT A TIME before touching anything.

**Next step:** Burn down the remaining **51 lint warnings** toward `--strict`, page by page
with approval. Suggested order: (1) extract the oversized `<style>` blocks on the 4
architecture view pages (db-schema, intelligence, quality, system-map) into `src/styles/`;
(2) author SVG a11y triples (2 view-page + 8 component SVGs); (3) remove `<svg>` width/height
attrs on components with a render check; (4) NarrativeBase skip-link; (5) library/wisdom
subpages (lowest priority — not architecture views). Run `npm run lint:views` for live state.

---

*How to use: the rules for HOW views are built live in
[docs/standards/html-view-quality-digest.md](../../docs/standards/html-view-quality-digest.md)
(MUST card) and [the full standard](../../docs/standards/html-view-quality.md). WHAT each
view shows is agreed per-page. Run `npm run lint:views` from `plan-dashboard/` to see the
current conformance state.*
