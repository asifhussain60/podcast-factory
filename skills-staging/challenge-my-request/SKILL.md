---
name: challenge-my-request
description: "Forces Claude to critically evaluate Asif's own request or reasoning — about how we're building the podcast-factory pipeline/tooling itself, NOT the content it produces — before complying, instead of defaulting to agreement. Invoke on self-referential phrasing: 'challenge this', 'challenge me', 'challenge my request', 'challenge my thinking/approach/reasoning', 'play devil's advocate', 'push back on this', 'poke holes in this', 'is this actually a good idea', 'am I wrong about this'. NEVER invoke on 'challenge <book-slug>', 'challenge book <slug>', 'challenge view <name>', 'challenge slides <slug>', 'render-challenge <slug>', or any phrasing naming a book/view/deck/chapter target — those belong to the five existing challenger agents (book-challenger, podcast-challenger, slide-deck-challenger, html-view-challenger, book-render-challenger), which this skill must never intercept. Scoped to this repo only."
---

# Challenge my request

Project-scoped skill for `~/PROJECTS/podcast-factory`. Asif asked for this because the default
mode — read a request, comply, report success — lets a bad idea, a wrong assumption, or a worse
path than the obvious one slide through unchallenged. This skill is the standing override for
that: when invoked, critical evaluation of *Asif's own request or reasoning* comes before any
compliance, plan, or file change.

This is about **how we work on the podcast-factory tooling and pipeline** — architecture
choices, script changes, process decisions, "should we do X" — not about judging book content,
which the five `*-challenger` agents already own. If the request at hand is "challenge
`purification-of-the-heart`" or any other book/view/deck/slug target, this skill does not apply —
that is one of the existing challenger agents, and this skill's own trigger list excludes those
phrasings on purpose. When genuinely ambiguous which is meant, ask rather than guess.

## What "challenge" means here

Not a bounded technical audit against a written standard (that's what the `*-challenger` agents
do, with severity tiers and convergence loops) — but it borrows that same shape, because a fixed
checklist run the same way every time is what makes a critique reproducible instead of vibes. Look
at what's actually being asked, run it through the category checklist below in order, and say
plainly if a better, safer, or simpler path exists — grounded in the real code and state of this
repo, never in assumption.

## Protocol

1. **Restate the request in one line**, in your own words, including any unstated assumption or
   hidden scope you can already see. This surfaces a wrong reading before any work happens.

2. **Ground before judging.** Read whatever the request actually touches — the relevant script(s)
   in `scripts/podcast/`, the phase modules under `scripts/podcast/phases/`, the orchestrator
   state for any book in play, the relevant `_system/*.json`, existing tests. Never critique from
   memory or from the description alone.

3. **Classify the request against the table below, then run every checklist item its row lists —
   in order, every item, even the ones that turn out not to apply.** Mark each ✅ Clear or
   🚩 Flag explicitly; don't skip an item silently. This is what makes the pass systematic and
   repeatable rather than an ad hoc gut check — the same request classified the same way runs the
   same checks every time. A request can match more than one row; run every row it matches.

   | Request shape | Checklist |
   |---|---|
   | New/changed pipeline **phase or gate** (anything under `scripts/podcast/phases/`, or a new state field in `orchestrate_book.py`) | • Does the new logic live in its own module under `phases/`, not added inline to `orchestrate_book.py` (the A4 split is deliberate)? <br>• If it can fail, does it set `manual_fallback` on the failed state — the field `watch_orchestrator.sh`'s `_needs_human_fix()` checks before deciding to halt vs. retry 20x? <br>• Does it need a `--retry-phase` or `--resume` path, and does that path already exist? |
   | New/changed **agent spec** (`infra/claude-agents/*.md`) | • Was it edited ONLY at the canonical path, never in a generated mirror (`.github/agents/*.agent.md`, `.claude/agents/*.md`, `.codex/agents/*.toml`)? <br>• Was `scripts/podcast/sync-agent-wrappers.sh` run (or flagged as needed) to regenerate the mirrors? <br>• Does its `description` name a trigger phrase that collides with an existing agent's `invoke for` list (as "challenge" would have, before this skill's own trigger was narrowed)? |
   | New/changed **skill** (`.claude/skills/*` or `skills-staging/*`) | • Project-scoped or genuinely cross-repo — and does it live in the matching location? <br>• Does its trigger phrasing collide with any existing skill's or agent's trigger list? <br>• Is the scope stated explicitly in its description, the way this skill and `podcast-factory-deploy` both do? |
   | Touches **`_rules.py`** (new `R-*` constant) or the **orchestrator state schema** | • Same-commit sweep of `framework.md` + `skills-staging/podcast/SKILL.md` + the `book-challenger` Category catalog, per the locked docs-sweep sub-rule? <br>• Any `challenger_contract` block in an affected agent spec still accurate? |
   | Touches one of the **11 fixture-pinned TS↔Python mirror pairs** (list below) | • Was the *other* half of the pair updated in the same change, not just the one Asif asked about? <br>• Do the fixtures under `plan-dashboard/scripts/lib/*.fixtures.json` still pass? |
   | Touches `_workspace/plan/architecture.md`, `refactor/plan.{md,yaml}`, `debt/pipeline-debt.md`, or **any** `infra/claude-agents/*.md` | • Was `cd plan-dashboard && npm run snapshot` run (or flagged as still needed) in the same response, before anything is called done? |
   | **Git/branch/commit/push** action | • Does it stay inside Tier 0/1 (commit, push `develop`, retry-phase, resume) or does it cross into Tier 2 (force-push, branch deletion, `develop`→`main`, `--no-verify`, `git reset --hard`) and therefore require an explicit ask regardless of how the request was phrased? <br>• Is this a `gh pr create` — this repo never opens PRs, it commits straight to `develop`? <br>• If this is one push among several today, does batching to ≤8 pushes/day still hold, or is this the push that breaks it? |
   | **Deploy or publish** action (`deploy_listener.sh`, any Cloudflare deploy, `publish_to_library.py`) | • Has Asif actually opened and tried it on `localhost` and said it's right — a green gate is not sign-off? <br>• Is this Tier 2 regardless of how confidently the request is phrased? |
   | Anything that **spends money** (new Azure/Gemini calls, a wider `claude -p` loop, more parallel agents) | • Is the spend proportional to what's actually needed, or does a narrower probe/cheaper model/existing cached result get the same answer? <br>• Would this be clearer reported in real dollars than left unstated? |
   | **Restarting a failed/stalled run** | • Have the actual logs and `last_error` been read, or is this a blind retry the repo has already been burned by twice? |
   | None of the above — a **general "build/add/change X"** with no obvious category | • Regression: does it break, weaken, or bypass a rule already locked in `CLAUDE.md`'s Authorization tiers, `Do NOT` list, or the standing operator rules? <br>• Root-cause miss: is this patching a symptom one layer above the actual cause? <br>• Duplication: does an existing script, agent, or pattern already solve this? <br>• Missed consequence: cost, reversibility, blast radius beyond what was literally asked? |

   **The 11 fixture-pinned mirror pairs** (verify this list against
   `plan-dashboard/scripts/lib/*.fixtures.json` before relying on it — it grows):
   `content-paths.ts`↔`_paths.py`, `peq-scores.ts`↔`_quality.py`+`_rules.py`,
   `anchor-key.mjs`↔`_book_edits.anchor_key`, `vowelling.mjs`↔`_vowelling.py`,
   plus the arabic-block, arabic-quote-line, buckwalter, para-blocks, quote-groups,
   surah-names, and work-groups pairs.

4. **Report the verdict in a fixed shape, before any plan or file change** — mirroring the
   verdict/severity language the `*-challenger` agents already use, so it reads consistently with
   everything else in this repo:
   - **Verdict:** `SOUND` (proceed as asked) / `NEEDS-REVISION` (proceed, but only after folding in
     a specific fix) / `BLOCKED-ON-RULE` (would violate a locked rule — do not proceed without an
     explicit override).
   - **Findings**, each tagged **P0** (breaks a locked rule or causes a real regression) / **P1**
     (real risk or clearly-better alternative exists) / **P2** (worth naming, not blocking), each
     citing the specific file, line, or rule it's grounded in — never a vague "this seems risky."
   - If `SOUND` with zero findings: say so in one sentence and proceed. Don't manufacture a finding
     to look thorough — an empty list is the success case, exactly as it is for the `*-challenger`
     agents.

5. **If Asif hears the pushback and still wants the original request**, treat that as a decision,
   not a re-opened debate: say so in one line and proceed with what he asked, under the assumption
   now stated explicitly. Don't relitigate a decision he already made twice.

## What this does not change

- Tier 2 actions (first orchestrator launch, publish, deploy, force-push, branch deletion,
  `develop`→`main`) still always ask, independent of whether this skill ran.
- This does not replace the `*-challenger` agents' book/view/deck audits, and does not replace the
  global `groundwork` skill's full six-phase protocol for genuinely large or ambiguous work — this
  is the lighter, faster, "look at this before I run with it" pass for the everyday back-and-forth
  of building the pipeline.
