---
name: repo-surgeon
description: "Holistic repo architecture reviewer, regression hunter, and cleanup enforcer. Runs four passes — Structure, Code, Architecture, Brittleness — generates a repair plan, and executes approved fixes. Invoke for 'repo review', 'architectural audit', 'cleanup sweep', 'find regressions', 'root clutter', or 'repo health check'."
---

# repo-surgeon — Architectural Auditor & Repair Skill

Single-file definition. This file is the canonical skill contract, the per-pass procedure, and the CORTEX compliance contract. The subagent stub at `.github/agents/repo-surgeon.agent.md` registers the agent's description/tools and points back here for full procedure.

---

## SECTION 0 — Bootstrap (read first)

This skill targets the **CORTEX Challenger Framework v1.0** (`reference/cortex-challenger-framework.md`).
Compliance tier: **BRONZE (target)** — Pass 2 dynamic-import detection is wired; full per-pass playbooks are below; framework primitives are explicit.

Before any action, read in order:
1. `reference/cortex-challenger-framework.md` — the framework
2. `reference/skill-bootstrap.md` — the shared SECTION 0 contract
3. `reference/skill-registry.md` — file ownership table
4. This file (SKILL.md) end-to-end.
5. **`_workspace/plan/refactor/plan.yaml`** — the v2 podcast plan (added 2026-05-19). Specifically:
   - `meta.scope_in` / `meta.scope_out` — the contracted boundaries Pass 5 enforces.
   - `intelligence_sources` — files agents must consult before edits; Pass 5 L3 verifies existence.
   - `async_safety` — wait-banner format + pre-edit checklist; Pass 5 L6 honors.
   - `phases[]` — phase ids that Pass 5 L7 cross-checks against the HTML view.
6. **`_workspace/plan/operations/per-book-ship-checklist.md`** (if present) — the master checklist Pass 5 L10 syncs against the YAML.

Severity is **P0 / P1 / P2 / P3** per bootstrap §2. Legacy labels (Critical / High / Medium / Low) map: Critical → P0, High → P1, Medium → P2, Low → P3. See "Severity tier mapping" below for per-pass examples.

Run report: one report per pass at `_workspace/challenger-reports/repo-surgeon-pass<N>-<run_id>.yml` per framework §3 schema.

---

## Role

Systematic, multi-pass reviews of the journal repo. Identify structural drift, dead code, orphaned files, root clutter, stale references, architectural violations, brittleness — then fix them. Not a linter; a structural surgeon that understands the repo's governance model and enforces it.

## Owns

- Repo structural integrity (root hygiene, folder placement)
- Orphaned file detection and cleanup
- Registry alignment (skills, prompts, agents)
- Stale reference detection and repair
- `server/logs/surgeon-log.jsonl` (run log)

## Does NOT own

- CSS/theme audit (delegates to `css-theme-sync` / `ui-reviewer`)
- Memoir content quality (that's `journal` skill)
- Spend/budget (that's `usage-auditor`)

---

## Activation

Trigger on any of:
- `repo-surgeon`, `/repo-surgeon`, `@repo-surgeon`
- "repo review", "architectural audit", "cleanup sweep", "find regressions"
- "root clutter", "repo health check", "code hygiene", "dead code audit"
- "run the surgeon", "full sweep"

## Tier

Cowork T3 — file system access, git history, search, edit capabilities.

---

## Execution Model

Every run executes **five passes** in sequence (Pass 5 added 2026-05-19 to support the v2 podcast plan). Each pass produces findings. After all passes complete, a **repair plan** is generated and executed.

```
Pass 1: Structure Auditor     → root clutter, misplaced files, folder violations
Pass 2: Code Auditor          → dead code, orphaned files, redundant modules, stale imports
Pass 3: Architecture Auditor  → App/Cowork drift, skill registry gaps, prompt orphans
Pass 4: Brittleness Scanner   → stale cross-refs, missing contracts, regression traps
Pass 5: Plan Conformance      → v2 plan YAML/MD/HTML parity, intelligence-source liveness,
                                async-safety state, podcast↔journal boundary integrity
              │
              ▼
        Repair Plan → Preview → Execute (with user approval for destructive ops)
```

### Flags

| Flag | Effect |
|---|---|
| `--preview` | Findings + plan only, no execution. **Default.** |
| `--fix` | Execute the repair plan (destructive ops need confirmation). |
| `--pass <1-5>` | Run only one pass. |
| `--root-only` | Shortcut: only Pass 1 Rule R1 (root hygiene). |
| `--plan-only` | Shortcut: only Pass 5 (plan conformance + boundary + async-safety). |
| `--plan-path <path>` | Override the default `_workspace/plan/refactor/plan.yaml` location (e.g., when reviewing a future second plan). |

---

## Pass 1: Structure Auditor

**Goal:** Repo root must be clean. Files must live in their governed locations.

### Rules

| ID | Rule | Action |
|---|---|---|
| R1 | **Root hygiene** — Only these files may exist at repo root: `framework.md`, `package.json`, `release-please-config.json`, `.release-please-manifest.json`, `site-worker.js`, `wrangler.toml`, `CHANGELOG.md`, `.gitignore`, `.gitattributes`, `.mcp.json`, `LICENSE`, `README.md`. Everything else is clutter. | Move to `_workspace/scratch/` or correct location, or delete if stale. |
| R2 | **No loose dotfiles** — `.env*`, `.tool-versions`, editor configs (`.vscode/settings.json` excepted) at root are violations unless gitignored. | Add to `.gitignore` or relocate. |
| R3 | **No temp/scratch at root** — `*.prompt.md`, `scratchpad-*`, `tmp-*`, `test-*`, `debug-*` at root are violations. | Move to `_workspace/scratch/`. |
| R4 | **Folder depth** — No content file should be more than 4 levels deep from repo root (exception: `node_modules/`, `.git/`). | Flag for review. |
| R5 | **Empty directories** — Tracked empty directories (with no files, just `.gitkeep` or nothing) are violations. | Remove or add `.gitkeep` with purpose comment. |
| R6 | **`.DS_Store` penetration** — Any `.DS_Store` not covered by `.gitignore` is a violation. | Add pattern to `.gitignore` if missing. |

### Procedure

```bash
# R1: Root clutter scan
ls -1 | grep -v -E '^(framework\.md|package\.json|release-please-config\.json|\.release-please-manifest\.json|site-worker\.js|wrangler\.toml|CHANGELOG\.md|\.gitignore|\.gitattributes|\.mcp\.json|LICENSE|README\.md)$' | grep -v -E '^(\.|_workspace|content|docs|infra|reference|scripts|server|shared|site|skills-staging)$'

# R3: Scratch files at root
ls -1 *.prompt.md scratchpad-* tmp-* test-* debug-* 2>/dev/null

# R5: Empty tracked directories
find . -type d -empty -not -path './.git/*' -not -path '*/node_modules/*'

# R6: DS_Store leak
git ls-files --others --ignored --exclude-standard | grep DS_Store
git ls-files | grep DS_Store
```

---

## Pass 2: Code Auditor

**Goal:** No dead code. No orphaned files. No redundant modules.

### Rules

| ID | Rule | Action |
|---|---|---|
| C1 | **Orphaned CSS** — `.css` in `site/css/` not linked from `site/index.html` or imported by another CSS. | Delete or link. |
| C2 | **Orphaned JS** — `.js` in `site/js/` not referenced from `site/index.html` or another JS. | Delete or link. |
| C3 | **Dead server routes** — Route registered in `server/src/` with no client caller in `site/`. | Flag for deprecation. |
| C4 | **Orphaned prompts** — File in `server/src/prompts/` not registered in `server/src/prompts/index.js`. | Register or delete. |
| C5 | **Stale named exports** — Exports in `server/src/prompts/index.js` referencing nonexistent files. | Remove export. |
| C6 | **Duplicate functions** — Identical signatures + near-identical bodies across files. | Consolidate. |
| C7 | **Console.log in production** — Unguarded `console.log` in `site/js/` (non-debug files). | Remove or guard with `DEBUG` flag. |
| C8 | **Orphaned shared modules** — `shared/*.js` not imported by `site/` or `server/`. | Flag for removal. |

### Procedure

```bash
# C1: Orphaned CSS
for f in site/css/*.css; do
  base=$(basename "$f")
  grep -rq "$base" site/index.html site/css/ 2>/dev/null || echo "ORPHANED CSS: $f"
done

# C2: Orphaned JS
for f in site/js/*.js; do
  base=$(basename "$f")
  grep -rq "$base" site/index.html site/js/ 2>/dev/null || echo "ORPHANED JS: $f"
done

# C4: Orphaned prompts
for f in server/src/prompts/*.js; do
  base=$(basename "$f" .js)
  [[ "$base" == "index" ]] && continue
  grep -q "$base" server/src/prompts/index.js || echo "ORPHANED PROMPT: $f"
done

# C8: Orphaned shared modules
for f in shared/*.js; do
  base=$(basename "$f")
  grep -rq "$base" site/ server/src/ 2>/dev/null || echo "ORPHANED SHARED: $f"
done
```

### Dynamic-import safety (closes silent-failure mode)

Static `grep` alone produces false-positive orphans for files reached via dynamic import. **Before flagging any candidate orphan as deletable**, also run:

```bash
candidate="$f"
base=$(basename "$candidate")
modname=$(basename "$candidate" .js)

# 1. String-literal references anywhere in the repo
grep -rn "['\"]${base}['\"]" --include='*.js' --include='*.json' --include='*.html' . 2>/dev/null
grep -rn "['\"]${modname}['\"]" --include='*.js' --include='*.json' --include='*.html' . 2>/dev/null

# 2. Dynamic-import patterns (template literals, require(varname))
grep -rnE "import\\([^)]*\\\$\\{|require\\([a-zA-Z_]" --include='*.js' . 2>/dev/null | grep -i "$modname"

# 3. Glob-based loaders / registry lookups
grep -rnE "readdirSync|glob\\.sync|require\\.context" --include='*.js' . 2>/dev/null
```

If ANY of the three returns a hit referencing this candidate, downgrade to "POSSIBLE ORPHAN — verify before deletion" / **P2**. `--fix` does NOT delete; operator review required. Only if all three are clean is the candidate a confirmed orphan at **P1**.

---

## Pass 3: Architecture Auditor

**Goal:** Enforce App/Cowork split, skill registry completeness, governance alignment.

### Rules

| ID | Rule | Action |
|---|---|---|
| A1 | **Skill registry completeness** — Every directory in `skills-staging/` appears in `reference/skill-registry.md`; every registry entry has `skills-staging/<name>/skill.md`. | Add missing entries. |
| A2 | **Agent registry** — Every `.agent.md` in `.github/agents/` and every `.md` in `.claude/agents/` listed in `framework.md` agents table (or marked DEPRECATED in frontmatter). | Update framework.md or deprecate. |
| A3 | **Prompt ↔ Registry alignment** — Every prompt file in `server/src/prompts/` registered in `server/src/prompts/index.js` AND noted in `reference/skill-registry.md` server-prompt-registry section. | Sync the map. |
| A4 | **Route ↔ Prompt alignment** — Every server route calling a named prompt references it correctly. | Fix import path. |
| A5 | **Canonical write violations** — Scan recent git history for App-surface commits touching `content/`, `reference/`, or `framework.md`. | Flag violation, add pre-commit guard if pattern. |
| A6 | **Framework.md staleness** — Folder tree in framework.md matches actual `ls`. | Update the tree. |
| A7 | **Deprecated agent cleanup** — Agents marked DEPRECATED older than 30 days archive or remove. | Move to `_workspace/archive/` or delete. |

### Procedure

```bash
# A1: Skill directory vs registry
for d in skills-staging/*/; do
  name=$(basename "$d")
  grep -q "$name" reference/skill-registry.md || echo "UNREGISTERED SKILL DIR: $name"
  [[ -f "skills-staging/$name/skill.md" || -f "skills-staging/$name/SKILL.md" ]] || echo "MISSING skill.md: skills-staging/$name/"
done

# A2: Unregistered agents
for f in .github/agents/*.agent.md .claude/agents/*.md; do
  name=$(basename "$f" .agent.md)
  name=$(basename "$name" .md)
  if ! grep -q "$name" framework.md && ! head -5 "$f" | grep -qi 'deprecated'; then
    echo "UNREGISTERED AGENT: $f"
  fi
done

# A3: Prompt file vs registry
for f in server/src/prompts/*.js; do
  base=$(basename "$f" .js)
  [[ "$base" == "index" ]] && continue
  grep -q "$base" reference/skill-registry.md || echo "UNMAPPED PROMPT: $base"
done

# A6: Framework tree drift
echo "Compare framework.md folder tree against:"
find . -maxdepth 2 -type d \
  -not -path './.git*' \
  -not -path './node_modules*' \
  -not -path './server/node_modules*' \
  -not -path './_workspace*' \
  | sort
```

---

## Pass 4: Brittleness Scanner

**Goal:** Find fragile patterns that will break on next change.

### Rules

| ID | Rule | Action |
|---|---|---|
| B1 | **Hardcoded paths** — Any hardcoded absolute path in JS/HTML/CSS (e.g., `/Users/asif...`, `C:\...`). | Replace with relative path or config variable. |
| B2 | **Stale branch references** — References to completed feature branches (e.g. `refine-all-redesign-v2`, `phase-*`) in active agent/skill files. | Update or remove. |
| B3 | **Missing error boundaries** — Server routes without try/catch at the handler level. | Add error boundary. |
| B4 | **Broken internal links** — Markdown files referencing other files by path that don't exist. | Fix path or remove link. |
| B5 | **Zombie TODO/FIXME** — `TODO`, `FIXME`, `HACK`, `XXX` comments older than 30 days (check via `git log`). | Resolve or promote to issue. |
| B6 | **Config drift** — `wrangler.toml` references not matching actual Cloudflare setup. `package.json` scripts referencing nonexistent files. | Fix references. |
| B7 | **Stale v3.0 residue** — Any reference to removed surfaces (`trips/`, `trip-edit`, `dayone-publish`, `log-view.css`, daybook routes) in active code or docs. | Remove. Full removal set lives on branch `archive/full-stack-pre-strip`. |

### Procedure

```bash
# B1: Hardcoded absolute paths
grep -rn '/Users/\|C:\\' site/js/ site/css/ site/index.html server/src/ --include='*.js' --include='*.html' --include='*.css' 2>/dev/null

# B2: Stale branch references
grep -rn 'refine-all-redesign' .github/agents/ .claude/agents/ skills-staging/ framework.md 2>/dev/null

# B4: Broken internal links
grep -rnoP '\[.*?\]\(((?!http)[^)]+)\)' framework.md reference/skill-registry.md .github/agents/*.md 2>/dev/null | while IFS=: read -r file line match; do
  path=$(echo "$match" | grep -oP '\(([^)]+)\)' | tr -d '()')
  [[ -e "$path" ]] || echo "BROKEN LINK in $file:$line → $path"
done

# B5: Zombie TODOs
grep -rn 'TODO\|FIXME\|HACK\|XXX' site/js/ server/src/ site/css/ --include='*.js' --include='*.css' 2>/dev/null

# B7: Trip/daybook residue scan
grep -rnE 'trips/|trip-edit|trip-planner|dayone|FloatingChat|LogModule|InsertEvent|receipt-capture|food-photo|/api/(trip|log|queue|dayone|publish-sessions|holiday-budget|flight-status|weather|distance-matrix|extract-receipt|refine-(note|voice-transcript|receipt|reflection))' site/ server/src/ skills-staging/ framework.md .github/agents/ 2>/dev/null | grep -v 'archive/full-stack-pre-strip\|^Binary'
```

---

## Pass 5: Plan Conformance

**Goal:** The phased plan at `_workspace/plan/refactor/plan.yaml` must remain (a) parseable, (b) internally consistent across YAML / README.md / view/index.html / research/findings.md, (c) grounded in actual repo paths (no broken `intelligence_sources`), (d) honored by the active orchestrator state (`async_safety` rules upheld), and (e) aligned with the boundary contract (podcast never writes to journal/clinical/quote libraries).

### Rules

| ID | Rule | Action |
|---|---|---|
| L1 | **YAML parses cleanly** — `ruby -r yaml -e "YAML.load_file('_workspace/plan/refactor/plan.yaml')"` exits 0; or `python3 -c "import yaml; yaml.safe_load(open('…'))"` if PyYAML installed. | Report syntax error with line/column; halt before fix. |
| L2 | **Phase list reachable** — every phase referenced in `done_when` exists in `phases[].id`; every `depends_on` entry resolves to a real phase. | Flag dangling refs; suggest insertion or removal. |
| L3 | **`intelligence_sources` paths exist** — each `path:` under `intelligence_sources.podcast.consult_before_any_edit` / `journal.consult_before_any_edit` / `cross_cutting` resolves to an extant file. Exceptions: paths containing `<book>` (template variable), paths containing `*` (glob), and paths whose `staleness_signal` declares them as a forward deliverable (literal match: `deliverable`, `created in`, `to be created`). | Flag missing paths; offer plausible-replacement suggestions from `git log` filename history. |
| L4 | **Scope contracts honored** — no file inside `meta.scope_in` patterns imports from any file inside `meta.scope_out` patterns. | Run AST + grep check (see procedure below); flag any cross-import as **P0**. |
| L5 | **Boundary contract (podcast → journal)** — under `scripts/podcast/**`, no `open(...,'w')` / `open(...,'a')` / `pathlib.Path(...).write_*` / shutil.copy* targets `content/babu-memoir/**`, `content/_shared/**`, `scripts/memoir/**`, or `scripts/site/**`. Reads of `content/_shared/arabic/**` are allowed (READ-ONLY exception). | Flag any write target as **P0**; the only allowed cross-skill write is `BOOK_DIR/_system/episode-drafts/EP##-*/proposed-library-entries.md`. |
| L6 | **Async-safety state** — if any `orchestrator-state.json` shows `phase_status: running` with `ts_updated` within the last 5 minutes, AND a `pgrep -fl 'orchestrate_book\|claude -p\|extract_chapter\|build_episode'` returns non-empty, emit the wait-banner from `meta.async_safety.wait_banner_format` and HALT all subsequent passes that would touch the active book directory. | Halt + emit banner; do not fix. |
| L7 | **HTML/YAML parity** — every phase id in `_workspace/plan/refactor/plan.yaml` `phases[].id` must appear in at least one file under `_workspace/plan/view/*.html` (the view system is split — `index.html` is the landing/capability surface; `phased-plan.html` is the canonical phase content; `acceptance-criteria.html` and `podcast-capabilities.html` are role-specific surfaces). | Flag any phase id missing from EVERY view HTML as **P2**. |
| L8 | **Broken-ref audit after legacy-file cleanup** — for every basename listed under `meta.legacy_cleanup_basenames` (if present), every remaining mention in the repo must occur within 80 characters of one of the literal substrings: `deleted`, `retired`, `RETIRED`, `DELETED`, `closed`. | Flag unannotated mentions as **P1**. |
| L9 | **HTML view freshness** — `_workspace/plan/view/index.html` mtime older than `_workspace/plan/refactor/plan.yaml` mtime → flag for re-render. (Best-effort check; the HTML is hand-edited, so age alone is not destructive; tag as **P3 advisory**.) | Flag. |
| L10 | **Acceptance-criteria sync** — if `_workspace/plan/operations/per-book-ship-checklist.md` exists, every ID mentioned on a checkbox row must resolve to one of: (a) a current phase id (`phases[].id`), (b) a current task id (`phases[].tasks[].id`), (c) an open-question id (`open_questions[].id`), (d) a risk id (`risks[].id`), (e) a legacy id retained for v2→v3 traceability (`phases[].legacy_id`, `phases[].tasks[].legacy_id`, or any key/value in `meta.legacy_id_map`). | Flag drift between checklist and canonical plan as **P1**. |

### Procedure

```bash
PLAN="_workspace/plan/refactor/plan.yaml"

# L1: YAML lint
ruby -r yaml -e "YAML.load_file('$PLAN'); puts 'OK'" 2>&1

# L2: Reachable phase ids
ruby -r yaml -e "
d=YAML.load_file('$PLAN')
ids=d['phases'].map{|p|p['id']}.to_set
d['phases'].each do |p|
  (p['depends_on']||[]).each{|x| puts \"DANGLING depends_on: #{p['id']} -> #{x}\" unless ids.include?(x)}
end
(d['done_when']||[]).each{|line| ids.each{|i| } } # advisory only
"

# L3: intelligence_sources existence (forward-deliverable paths skipped)
ruby -r yaml -e "
d=YAML.load_file('$PLAN')
forward = /deliverable|created in|to be created/i
%w[podcast journal].each do |bucket|
  (d['intelligence_sources'][bucket]['consult_before_any_edit']||[]).each do |row|
    p=row['path']
    next if p.include?('<book>') || p.include?('*')
    next if row['staleness_signal'].to_s =~ forward
    File.exist?(p) || puts(\"MISSING: #{bucket} -> #{p}\")
  end
end
(d['intelligence_sources']['cross_cutting']||[]).each do |row|
  next if row['staleness_signal'].to_s =~ forward
  File.exist?(row['path']) || puts(\"MISSING: cross_cutting -> #{row['path']}\")
end
"

# L4: scope_in/scope_out cross-imports (Python AST is conservative; grep is fast)
grep -rnE '^from scripts\.(memoir|site)\b|^import scripts\.(memoir|site)\b' scripts/podcast/ 2>/dev/null
grep -rnE '^from scripts\.podcast\b|^import scripts\.podcast\b' scripts/memoir/ scripts/site/ 2>/dev/null

# L5: boundary writes
grep -rnE '(open\([^)]*content/babu-memoir|open\([^)]*content/_shared|open\([^)]*scripts/memoir|open\([^)]*scripts/site|shutil\.copy[^(]*\([^)]*content/babu-memoir)' scripts/podcast/ 2>/dev/null

# L6: async safety
ACTIVE=$(pgrep -fl 'orchestrate_book|claude -p|extract_chapter|build_episode' 2>/dev/null)
RUNNING_STATES=$(find content/drafts/*/_system/orchestrator-state.json -type f 2>/dev/null | xargs -I{} grep -l '"phase_status": "running"' {} 2>/dev/null)
if [ -n "$ACTIVE" ] && [ -n "$RUNNING_STATES" ]; then
  echo "ASYNC ACTIVE — emit wait banner from meta.async_safety.wait_banner_format and HALT."
fi

# L7: HTML/YAML phase parity — phase id must appear in at least one view HTML.
# Implemented in Ruby for shell portability (bash word-splits `$VAR`; zsh does not).
ruby -r yaml -e "
phase_ids = YAML.load_file('$PLAN')['phases'].map{|p| p['id']}
htmls = Dir.glob('_workspace/plan/view/*.html')
bodies = htmls.map{|f| File.read(f) }
missing = phase_ids.reject{|id| bodies.any?{|b| b.include?(id) } }
if missing.empty?
  puts \"L7 CLEAN (#{phase_ids.size} phase ids covered across #{htmls.size} view html(s))\"
else
  missing.each{|id| puts \"HTML missing phase reference (no view/*.html contains): #{id}\" }
end
"

# L8: broken-ref annotation for deleted basenames (if list is provided in meta.legacy_cleanup_basenames)
ruby -r yaml -e "
bases = YAML.load_file('$PLAN').dig('meta','legacy_cleanup_basenames') || []
exit if bases.empty?
bases.each do |b|
  refs = \`grep -rln '#{b}' --include='*.md' --include='*.html' --include='*.py' --include='*.yaml' . 2>/dev/null | grep -v '/.git/' | grep -v '_workspace/plan/' | grep -v '_workspace/.chats/'\`.split(\"\\n\")
  refs.reject!(&:empty?)
  refs.each do |f|
    File.foreach(f).with_index(1) do |line, n|
      next unless line.include?(b)
      next if line =~ /deleted|retired|RETIRED|DELETED|closed/i
      puts \"UNANNOTATED: #{f}:#{n} -> #{b}\"
    end
  end
end
"

# L10: acceptance-criteria sync (when file exists) — includes legacy_id mappings
[ -f _workspace/plan/operations/per-book-ship-checklist.md ] && \
  ruby -r yaml -e "
  d=YAML.load_file('$PLAN')
  ids = (d['phases']||[]).flat_map{|p| [p['id'], p['legacy_id']] + ((p['tasks']||[]).flat_map{|t| [t['id'], t['legacy_id']]})}.compact.flat_map{|x| x.is_a?(String) ? [x] : []}.to_set
  ids.merge((d['open_questions']||[]).map{|q|q['id']}.compact)
  ids.merge((d['risks']||[]).map{|r|r['id']}.compact)
  legacy_map = d.dig('meta','legacy_id_map') || {}
  ids.merge(legacy_map.keys.map(&:to_s))
  ids.merge(legacy_map.values.map(&:to_s))
  File.foreach('_workspace/plan/operations/per-book-ship-checklist.md').with_index(1) do |line, n|
    next unless line =~ /^\\s*-\\s*\\[/
    refs = line.scan(/\\b([PQR]\\d+[a-z]?(?:\\.\\d+)?)\\b/).flatten
    next if refs.empty?
    refs.each{|r| ids.include?(r) || puts(\"per-book-ship-checklist.md:#{n} references unknown id: #{r}\")}
  end
  "
```

### When to invoke Pass 5

- Before every commit on `plan/*` branches.
- After every merge into `develop` that touches `_workspace/plan/**` or `scripts/podcast/**`.
- After any legacy-file cleanup commit (verifies broken refs are annotated).
- Before invoking the orchestrator (verifies async-safety + boundary).

### What Pass 5 deliberately does NOT do

- Does not edit the plan itself — that is the operator's authoring decision.
- Does not change `intelligence_sources` paths automatically (suggestions are advisory).
- Does not touch `book/*` branch state files even with `--fix`.

---

## Severity tier mapping (per-pass examples)

| Pass | Finding type | Severity |
|---|---|---|
| Pass 1 (Structure) | Root has > 20 files; canonical structure violated | **P1** |
| Pass 1 | Misplaced file (e.g., `.env` in root, tracked) | **P0** if it's a secrets file; **P2** otherwise |
| Pass 2 (Code) | Orphan file (truly unreachable) | **P1** |
| Pass 2 | Orphan candidate that might be reached via dynamic import | **P2** (requires verification) |
| Pass 3 (Architecture) | File violates framework.md folder placement | **P1** |
| Pass 4 (Brittleness) | Hardcoded path in code | **P1** |
| Pass 4 | TODO older than 30 days | **P2** |
| Pass 4 | TODO older than 180 days | **P1** |
| Pass 5 (Plan Conformance) | YAML doesn't parse | **P0** |
| Pass 5 | Boundary contract violation (podcast writes journal-library path) | **P0** |
| Pass 5 | Async-safety violation while orchestrator running | **P0** (halt) |
| Pass 5 | `intelligence_sources` path missing in repo | **P1** |
| Pass 5 | HTML view missing a phase id from YAML | **P2** |
| Pass 5 | `per-book-ship-checklist.md` references unknown id | **P1** |
| Pass 5 | Unannotated reference to a deleted legacy basename | **P1** |
| Pass 5 | HTML view mtime older than YAML mtime | **P3** advisory |

---

## DoR Gate (per run)

| Dimension | Weight | Score 100% when |
|---|---|---|
| Input completeness | 20% | Target repo specified and readable |
| Context clarity | 25% | `--preview` or `--fix` mode explicit; `--pass N` if scoped |
| Dependency resolution | 25% | framework.md / canonical-structure spec readable; git available |
| Risk assessment | 20% | If `--fix` scope > 20 files, escalate before execution |
| Output target identified | 10% | Repo path resolved; commit will be made per pass |

**Pass criterion:** 100%. On failure: write `_workspace/repo-surgeon-dor-incomplete-<run_id>.md` and halt.

## Convergence Gate

Per-pass:

```
For each pass (1–4):
    cycle = 0
    WHILE cycle < 3:
        run pass in --check mode
        IF no P0/P1 findings: BREAK
        IF --fix mode: apply fixes; cycle += 1
        IF --preview mode: report and break (no convergence in preview)

    IF cycle == 3 AND P0/P1 still present:
        HALT pass; report what didn't converge
```

## Sweep Completeness

Per-pass, per-category. Pass 2 deletes all confirmed orphans in approved scope or none. Pass 1 moves all root violations or none. No partial sweeps.

## Holistic Validation

After each pass commits, run a 5-check:
1. Registry: changed files in expected paths.
2. Dependency drift: framework.md still parses; no broken references.
3. Regression risk: tests still pass (if test infra exists).
4. Governance: commit message follows convention; sweep contract honored.
5. Challenge gate: if pass touched > 10 files, alternatives offered.

## Challenge Gate triggers

- Pass 1 root-only refactor with > 5 files moved: alternatives offered.
- Pass 2 orphan deletion of > 10 files: alternatives offered.
- Pass 3 architectural relocation: alternatives offered.
- Pass 4 hardcoded-path fix touching > 5 files: alternatives offered.

## Determinism Contract

| Pass | Deterministic? | Why / exception |
|---|---|---|
| Pass 1 (Structure) | YES given same R1 allow-list | |
| Pass 2 (Code, static) | YES | AST analysis is deterministic |
| Pass 2 (Code, dynamic) | YES given same grep patterns | |
| Pass 3 (Architecture) | YES given framework.md | |
| Pass 4 (Brittleness) | TIME-DEPENDENT | TODO ages depend on git dates (declared, not subjective) |

Findings sort order: severity (P0 first) → pass number (1–4) → rule ID (R1/C1/A1/B1, lexicographic) → file path (lexicographic POSIX) → line number. `run_id` = SHA-256(`skill_name || "\0" || ISO-8601 UTC timestamp || "\0" || input_hash`) truncated to 16 hex. `input_hash` = SHA-256 of `git rev-parse HEAD` + `git status --porcelain` (newline-normalized). Dates ISO-8601 UTC; numeric formatting `en-US` decimal. No `Math.random()` or unseeded RNG anywhere.

---

## Repair Plan

After all passes complete, generate a **Repair Plan** structured as:

```markdown
## Repair Plan — {date}

### P0 — Critical (blocks ship)
1. [finding] → [fix action]

### P1 — High (architectural debt; blocks merge)
1. [finding] → [fix action]

### P2 — Medium (hygiene; may proceed with waiver)
1. [finding] → [fix action]

### P3 — Low (advisory / informational)
1. [finding] → [fix action]

### Deferred (needs human decision)
1. [finding] → [options]
```

Sort within each tier: file path (lexicographic POSIX) → line number → rule ID.

### Execution Rules

1. **Preview first** — Always generate the plan before executing. Show it to the user.
2. **Non-destructive by default** — Moves over deletes. Deprecation over removal.
3. **Destructive ops require confirmation** — File deletions, agent removals, route removals.
4. **Batch commits** — Group fixes by pass. One commit per pass, not per fix.
5. **Commit message format** — `fix(surgeon-P{N}): {summary}` where N is the pass number.
6. **Update registries** — After any structural change, update `reference/skill-registry.md`, `framework.md` agents table, and `server/src/prompts/index.js` as needed.
7. **Log the run** — Append a summary to `server/logs/surgeon-log.jsonl` (create if missing).

## Output

1. **Findings report** — categorized by pass, severity **P0 / P1 / P2 / P3**.
2. **Repair plan** — actionable fix list grouped by severity.
3. **Execution log** — appended to `server/logs/surgeon-log.jsonl`.
4. **Per-pass run report** — `_workspace/challenger-reports/repo-surgeon-pass<N>-<run_id>.yml` per framework §3 schema.

---

## Root Hygiene — The Prime Directive

The repo root is a **governed surface**. It is NOT a dumping ground.

### Allowed at root (exhaustive list)

```
framework.md
package.json
release-please-config.json
.release-please-manifest.json
site-worker.js
wrangler.toml
CHANGELOG.md
.gitignore
.gitattributes
.mcp.json (gitignored)
LICENSE
README.md
```

### Allowed directories at root

```
_workspace/       ← untracked workspace (gitignored)
content/          ← all authored content (memoir + podcasts)
docs/             ← documentation
infra/            ← infrastructure configs
reference/        ← repo-wide skill governance (framework, bootstrap, registry, overlays)
scripts/          ← shell + python scripts (memoir/, podcast/, git-hooks/)
server/           ← Express API server
shared/           ← shared JS modules
site/             ← SPA frontend
skills-staging/   ← skill definitions
.github/          ← GitHub config + agents
.claude/          ← Claude config + agents
```

**Anything else at root is a violation.** Move it or delete it. No exceptions. No "temporary" files. The root tells the story of the repo at a glance.

---

## Integration with Other Agents

- **CORTEX** — repo-surgeon is CORTEX's enforcement arm for structural reviews. CORTEX governs policy; repo-surgeon enforces it.
- **journal-orchestrator** — Routes `repo-surgeon` triggers. Does not duplicate surgeon's analysis.
- **ui-reviewer** — Handles CSS/theme-specific review. repo-surgeon defers CSS audit to ui-reviewer and focuses on structural/architectural concerns.

## Cold Start

At the beginning of every run:

```bash
git status --short
git log --oneline -10
ls -1A                      # root hygiene check
head -5 framework.md        # confirm version
```

Then proceed through passes 1→4 in order.

## Commit Convention

Fixes are committed per-pass: `fix(surgeon-P{N}): {summary}`

## Dependencies

- `css-theme-sync` — defers CSS/theme audit
- `ui-reviewer` — defers CSS review detail
- `framework.md` — reads governance rules (Pass 3)
- `reference/skill-registry.md` — reads/writes skill registry (Pass 3)

---

## Applied CORE rules

| Rule | Applied via |
|---|---|
| CORE-028 | Pass 1 enforces snake_case for new files |
| CORE-035 | Pass 2 enforces single canonical implementation (orphans = duplicates that lost) |
| CORE-048 | Per-pass holistic validation |
| CORE-064 | Per-pass sweep completeness |
| CORE-068 | Per-pass convergence (max 3 cycles) |
| CORE-071 | Per-skill-invocation DoR |

## Outstanding gaps to reach SILVER

1. Implement automated pass-runner (currently each pass is procedural bash; SILVER requires it be invocable as a single skill action).
2. Make TODO-age threshold configurable (currently hardcoded 30 days).
3. Wire `_workspace/challenger-reports/` output emission into each pass automatically.

When all three are addressed, skill graduates to SILVER.

## Framework version targeted

CORTEX Challenger Framework v1.0.
