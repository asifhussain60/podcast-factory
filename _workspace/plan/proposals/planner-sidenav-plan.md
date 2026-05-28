# Planner Sidenav — Design Plan

> **Quick review table — scan this first**

| What | Detail |
|---|---|
| **Pages changed** | Base.astro, dashboard.astro (redirect), + 2 new pages (/plan, /live) |
| **Components created** | PlannerSidenav.tsx, PlanDesign.tsx, LiveExecution.tsx |
| **CSS** | New `.planner-sb-*` scope in theme.css — does NOT touch Architecture |
| **Data source** | Same dashboard-snapshot.json — no new snapshot work |
| **Live updates** | Uses existing `window.__onSnapshot` SSE hook — no new wiring |
| **No-change guarantee** | Architecture / Intelligence / Bookshelf pages — untouched |
| **Commit count** | 1 commit ("feat(planner): split into plan/live pages + animated sidenav") |

---

## Intent

> Make the Planner left sidebar a persistent, animated "plan command center" — always showing overall progress, per-wave completion bars, factory status, and what's next — regardless of which Planner sub-page you're on. The plan becomes a living document: bars animate on load, pulse when running, and re-animate on every SSE snapshot event.

---

## Part 1 — Sidebar design (PlannerSidenav.tsx)

The sidebar is 280px wide, sticky, always visible. Six sections top-to-bottom:

### Section 1 — Factory status (top anchor)

A single prominent status badge. This is the most important piece of information — at a glance, is the factory doing anything?

```
● IDLE            ← grey, static
● RUNNING (2)     ← blue, dot pulses at 1.8s interval
⚠ BLOCKED         ← red, no pulse
✓ ALL DONE        ← green, static
```

- Sub-line: "0 books in flight · 1 shipped" — links to /live
- When RUNNING: the dot uses `@keyframes pulse-dot` (opacity 1 → 0.35 → 1 over 1.8s, infinite). This is the only animated element that persists; all others only animate on load/update.

### Section 2 — Master progress bar

```
OVERALL PROGRESS
━━━━━━━━━━━━━━━━━━━━━━━━━━━
████░░░░░░░░░░░░░░░░░░░░░░   1 / 24
━━━━━━━━━━━━━━━━━━━━━━━━━━━
1 done  ·  0 active  ·  2 ready  ·  21 up next
```

- Green fill: `done / total`
- Progress bar uses `transform: scaleX()` with `transform-origin: left` — GPU-accelerated, no layout reflow
- Animation: `transition: transform 600ms cubic-bezier(0.34, 1.56, 0.64, 1)` — slight spring overshoot for a "alive" feel
- Initialises at `scaleX(0)`, sets to real value after mount (50ms delay so transition fires)
- On SSE re-render: re-triggers the animation by toggling a CSS class

### Section 3 — Wave breakdown (the richest section)

Five wave rows. Each row:

```
 ┌──────────────────────────────────┐
 │ [A]  Foundation         1 / 5    │
 │ ████░░░░░░░░░░░░░░░░░░░░░░░░░░  │  ← 4px bar
 └──────────────────────────────────┘
 [B]  Intelligence          0 / 4
 ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   ← future wave, dimmed
```

- Active wave (next incomplete one): elevated card with coloured left border + slightly lighter bg
- Complete waves: green left border, full bar, muted text
- Future waves (all-pending): greyed out, bar is ghost/empty
- Wave letter badge: coloured circle — green (complete), amber (active), grey (future)
- Bars: staggered animation — `transition-delay: calc(var(--wave-idx) * 80ms)` — so A fills first, then B, etc.
- Minimum visual bar width: 4px (never invisible even when 0%)
- Clicking a wave row: if on /plan page, scrolls main content to that wave group; if on /live page, navigates to /plan#wave-{id}

### Section 4 — What's next

A compact "action card" — one thing, always the highest-priority actionable step:

```
 NEXT UP
 ┌────────────────────────────────┐
 │  [A2]  Build the foundation    │
 │  layer the rest of the system  │
 │  sits on                       │
 │  Tools: Python · SQLite        │
 └────────────────────────────────┘
```

- Shows the first step with `status === 'ready'` (all dependencies met)
- If nothing is ready but something is in-progress: shows that in-progress step instead
- If all done: shows a completion state (no card, just a ✓ message)
- If something is blocked: shows the blocked count with a red indicator

### Section 5 — Debt pulse (conditional)

Only renders if `debt.length > 0`. Compact — a single line:

```
 ⚠ 2 known issues  (P0: 1 · P1: 1)
```

- P0 items make the whole line red; P1-only is amber
- Clicking links to /live (which shows the full debt list)
- When debt is empty: this section doesn't render (no empty state needed)

### Section 6 — Nav links (bottom)

Separated by a rule from the content sections above:

```
 ─────────────────────────────────
  📋  Plan Design           ← active indicator
  ⚡  Execution Live
```

- Standard sidenav-link styling (same as Architecture sidebar)
- The active page is highlighted

---

## Part 2 — Page split (/plan and /live)

### /plan — Plan Design

Replaces the "The roadmap" tab content. Full-width, no tabs. What changes vs. today:

- Ace-style wave cards: each wave is a `ccard`-inspired block with a blue top-accent line (`border-top: 3px solid var(--c-accent)`)
- Progress bar inside each wave card header showing wave completion
- Step rows: Ace-style colored left-border status badges instead of pills
  - Done → `border-left: 3px solid var(--c-success)` + green text
  - In progress → `border-left: 3px solid var(--c-info)` + blue
  - Ready → `border-left: 3px solid var(--c-gold)` + amber
  - Blocked → `border-left: 3px solid var(--c-danger)` + red
  - Pending → `border-left: 3px solid var(--c-rule)` + muted

### /live — Execution Live

Replaces the "What's running right now" + "Health metrics" tabs. Full-width, no tabs. Ace-inspired layout:

- 4 KPI cards at top (with colored corner orb decoration): Books in flight / Steps done / $ 30d / Convergence avg
- Books in flight section: each book as a card with phase progress bar + cost
- 2-column grid below: Spend chart card (left) + Phase time table card (right)
- Activity feed at bottom: recent commits Ace-style (date | subject | short SHA)
- Debt/known issues: red/amber badge chips

### /dashboard redirect

The current `/dashboard` path gets a redirect to `/plan` so existing links don't break.

---

## Part 3 — Animation spec

All animations use CSS only (no JS animation loops). JavaScript only triggers class toggles.

| Element | Animation | Trigger | Duration |
|---|---|---|---|
| Master progress bar | `scaleX(0 → value)` | Mount + SSE update | 600ms, spring easing |
| Wave bars (A-E) | `scaleX(0 → value)` | Mount + SSE update | 500ms, staggered 80ms each |
| Running status dot | `opacity 1 → 0.35` pulse | Factory RUNNING | 1.8s, infinite |
| Wave card (active) | subtle `box-shadow` glow | Always-on for active wave | n/a |
| Step row hover | `translateY(-1px)` | CSS `:hover` | 120ms |

Spring easing: `cubic-bezier(0.34, 1.56, 0.64, 1)` — gives a 6% overshoot that makes bars feel alive without being distracting.

Re-animation on SSE: a `data-animated` attribute is set to `false` → `true` by a `useEffect` triggered by snapshot version change. CSS uses `[data-animated="true"]` as the selector for the fill width.

---

## Part 4 — Technical implementation

### Files changed

| File | Type | What changes |
|---|---|---|
| `src/layouts/Base.astro` | MODIFY | Add `'planner'` to section type; render `PlannerSidenav` when `section="planner"` |
| `src/pages/dashboard.astro` | MODIFY | Redirect to `/plan` (meta refresh + Response.redirect) |
| `src/pages/plan.astro` | NEW | Plan Design page — imports `PlanDesign.tsx`, uses `section="planner"` |
| `src/pages/live.astro` | NEW | Live Execution page — imports `LiveExecution.tsx`, uses `section="planner"` |
| `src/components/PlannerSidenav.tsx` | NEW | React island — all 6 sidebar sections, animation logic, SSE subscription |
| `src/components/PlanDesign.tsx` | NEW | Extracted + restyled from DashboardTabs RoadmapTab |
| `src/components/LiveExecution.tsx` | NEW | Extracted + restyled from DashboardTabs CurrentTab + MetricsTab |
| `src/styles/theme.css` | MODIFY | Add `.planner-sb-*` scope (~80 new lines). No existing rules touched. |

### Data flow

```
dashboard-snapshot.json
        │
        ▼ (Astro SSR, build time or on-demand)
plan.astro / live.astro
        │  passes props to ↓
        ├─► PlannerSidenav (client:load)  ← also subscribes to window.__onSnapshot
        └─► PlanDesign / LiveExecution (client:load)
```

`window.__onSnapshot` is already wired in Base.astro. `PlannerSidenav` subscribes in `useEffect` and updates its local state copy of the snapshot data whenever a new snapshot arrives via SSE.

### PlannerSidenav.tsx — key state shape

```ts
const [snap, setSnap] = useState<SnapData>(initialSnap);   // initialised from Astro props
const [animated, setAnimated] = useState(false);            // triggers bar fill animation

useEffect(() => {
  setAnimated(false);
  const id = requestAnimationFrame(() => setAnimated(true));
  return () => cancelAnimationFrame(id);
}, [snap.source_commit]);   // re-animates only when snapshot changes

useEffect(() => {
  (window as any).__onSnapshot = (data: SnapData) => setSnap(data);
}, []);
```

---

## Part 5 — Self-review (second-pass critique)

> This section is the LLM reviewing its own proposal. Problems found and resolved.

**Problem 1:** "What's next" shows a single ready step — but the user might be on Wave C while Wave A still has pending steps. Which "next" is authoritative?

*Resolution:* Priority rule: the next ready step within the lowest-incomplete wave. If Wave A has a step with `status === 'ready'`, that shows regardless of what's happening in Wave B. This matches how the plan actually flows (waves are sequential).

**Problem 2:** Wave bar minimum visual width of 4px is fine on desktop, but if the sidebar is 280px and the bar area is ~230px after padding, 4px is about 1.7% — barely visible. 

*Resolution:* Use a CSS trick: `min-width: max(4px, calc(var(--pct) * 100%))`. This ensures the bar is always visually present. For 0% waves, the bar shows as a subtle 4px "seed dot" — communicates "not started" without disappearing.

**Problem 3:** Spring easing (`cubic-bezier(0.34, 1.56, 0.64, 1)`) looks great on the master bar but on 5 staggered wave bars it might look jittery. 

*Resolution:* Use spring easing only on the master bar. Wave bars use `ease-out` (`cubic-bezier(0.0, 0, 0.2, 1)`) — clean, no overshoot. Different easing for different weights of information.

**Problem 4:** The SSE `__onSnapshot` event carries the full snapshot payload. But the plan data (roadmap, waves) doesn't change unless someone runs the snapshot generator. Today, snapshots are regenerated manually. The sidebar animating on every SSE ping would be distracting if SSE fires frequently.

*Resolution:* Gate re-animation on `snap.source_commit !== prev.source_commit`. SSE can fire for heartbeat/status events; we only re-animate when the snapshot data actually changed (new commit hash).

**Problem 5:** Accessibility — the animated progress bars should have `role="progressbar"` with `aria-valuenow`, `aria-valuemin`, `aria-valuemax`. Screen readers don't benefit from visual animations.

*Resolution:* Add proper ARIA attributes to all progress bar elements. The animation is purely cosmetic CSS; the semantic data is always in the markup.

**Problem 6:** What happens on the first render before JavaScript hydrates? The sidebar is a React island (`client:load`) — there's a flash where the SSR-rendered shell appears before React takes over.

*Resolution:* Pass all data as Astro props (SSR), so the initial HTML render includes real data with bars at 0% width. JavaScript only adds the animation class. No flash of empty content.

**Problem 7 (design):** The current proposal has six sidebar sections. On a 768px-tall viewport (common laptop), all six sections need ~520px of height. That fits, but only just.

*Resolution:* The "Debt pulse" section collapses to zero height when debt is empty (which is the desired end-state as waves complete). Future waves collapse to 1-line compact rows when all-pending. This gives the sidebar room to breathe at the sizes that matter.

---

## Inline chat summary (for quick Asif review)

> This is the brief "what am I approving" version.

**What you'll see after implementation:**

1. The top nav "Planner" link takes you to `/plan` instead of `/dashboard` (existing `/dashboard` still works — redirects automatically)

2. The Planner section gets a left sidebar (same mechanics as Architecture) showing — at all times, on both `/plan` and `/live`:
   - **Factory status pill** — IDLE/RUNNING(n)/BLOCKED — pulses when running
   - **Master progress bar** — "1 of 24 steps done" with animated fill
   - **Five wave bars** — A through E, each showing X/Y with a mini bar, staggered fill animation on load
   - **What's next** — the single highest-priority actionable step (green card, step ID + title)
   - **Debt count** — only shown if open issues exist
   - **Nav links** — Plan Design / Execution Live at the bottom

3. `/plan` is a full-page redesigned roadmap view — Ace-style wave cards with progress bars and colored left-border status indicators

4. `/live` is a full-page execution view — 4 KPI cards (Ace stat widget style) + books in flight + spend chart + recent commits activity feed

5. Every progress bar animates on page load and re-animates when the SSE feed delivers a new snapshot (new commit). Animation is CSS-only, no JS loops.

**What doesn't change:** Architecture, Intelligence, Infrastructure, System Map, Bookshelf — all untouched.

**Cost:** 8 file changes, 1 commit.

---

*Awaiting approval to implement.*
