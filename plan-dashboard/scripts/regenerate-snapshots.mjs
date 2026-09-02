#!/usr/bin/env node
/**
 * regenerate-snapshots.mjs
 *
 * First-cut snapshot regenerator. The podcast-planner agent will eventually
 * supersede this — it can author plain-English descriptions that the static
 * loader below cannot. This script exists so:
 *
 *  1. The dashboard always has SOMETHING fresh to render, even without the agent.
 *  2. CI can verify the snapshots compile and the dashboard builds without
 *     having to invoke a model.
 *  3. The SSE sentinel pulses when this is invoked, so the dashboard refreshes.
 *
 * What it does:
 *  - Reads content/drafts/*\/_system/orchestrator-state.json for each book in flight.
 *  - Reads _workspace/plan/refactor/plan.yaml for roadmap statuses.
 *  - Reads _workspace/plan/debt/pipeline-debt.md for the open debt list.
 *  - Reads `git log -n 10 --pretty=format:"%h|%s|%ad" --date=short` for recent commits.
 *  - PRESERVES existing plain-English fields if the source file already has them
 *    (the agent's job is to author those; this script is mechanical).
 *  - Touches .snapshot-version so the SSE loop pushes a refresh event.
 */

import { readFile, writeFile, readdir, stat } from "node:fs/promises";
import { existsSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";
import yaml from "js-yaml";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const APP = path.resolve(HERE, "..");
const REPO = path.resolve(APP, "..");
const DATA = path.join(APP, "src", "data");
const CONTENT = path.join(REPO, "content");
/**
 * Where a book's folder lives.
 *
 * This used to be a single constant pointing at `content/drafts` — a directory the
 * type-first restructure DELETED on 2026-06-04. Nothing failed loudly: `readdir`
 * threw ENOENT, the catch returned `[]`, and from that day the dashboard reported
 * "0 books in flight" as a fact. It was still saying it on 2026-07-30 with six books
 * mid-pipeline, one of them failed since June. A dead path that degrades to an empty
 * list is worse than one that crashes, because the empty list looks like an answer.
 *
 * Buckets first, then the legacy trees — the same order, and the same reason, as
 * `_paths.py` / `content-paths.ts`: a partial migration must never hide a book.
 */
// Pinned to scripts/podcast/_content_types.py::BUCKETS by
// tests/test_snapshot_regenerator_parity.py. "Supplications" was appended to the
// authority on 2026-07-19 and to content-paths.ts, but not here, not in the .py
// mirror and not in site-health-smoke.mjs — and because the two generators are
// pinned to EACH OTHER they agreed while both being wrong. Latent only until the
// first supplication book lands, at which point it would have been invisible to
// every snapshot JSON. Restated rather than imported because this script runs
// under plain node with no TS resolver; the test is what keeps the restatement true.
const BUCKETS = [
  "Islamic",
  "Technical",
  "Fiction",
  "Guides",
  "Supplications",
  "Sessions",
  "Audiobook",
];
const BOOK_ROOTS = [
  ...BUCKETS.map((b) => path.join(CONTENT, b)),
  path.join(CONTENT, "drafts"),
  path.join(CONTENT, "published", "books"),
];
const PLAN_YAML = path.join(
  REPO,
  "_workspace",
  "plan",
  "refactor",
  "plan.yaml",
);
const WAVE_ACCEPTANCE = path.join(
  REPO,
  "_workspace",
  "plan",
  "operations",
  "wave-acceptance-checklist.md",
);
const WAVE_EVENTS = path.join(
  REPO,
  "_workspace",
  "plan",
  "refactor",
  "wave-execution-events.jsonl",
);
// An agent entry's DERIVED fields are re-read from its spec on every run; only
// these are hand-authored in the JSON and therefore merge-preserved. Keep this
// list identical to AGENT_CURATED_FIELDS in regenerate-snapshots.py.
const AGENT_CURATED_FIELDS = [
  "icon",
  "tone",
  "boundary_in",
  "boundary_out",
  "does_not",
  "cost_profile",
  "failure_mode",
];

const SENTINEL = path.join(APP, ".snapshot-version");
const TRACE_STEPS =
  process.argv.includes("--trace-steps") || process.env.SNAPSHOT_TRACE === "1";

const WAVE_NUM_BY_LETTER = { A: 1, B: 2, C: 3, D: 4, E: 5 };

function parseChecklistDoneWaves(markdown) {
  const out = new Set();
  if (!markdown || typeof markdown !== "string") return out;

  const lines = markdown.split("\n");
  let currentWave = null;
  let waveRows = 0;
  let waveChecked = 0;

  const flush = () => {
    if (currentWave !== null && waveRows > 0 && waveRows === waveChecked) {
      out.add(currentWave);
    }
  };

  for (const raw of lines) {
    const line = raw.trim();
    const waveMatch = line.match(/^##\s+Wave\s+(\d+)\b/i);
    if (waveMatch) {
      flush();
      currentWave = Number(waveMatch[1]);
      waveRows = 0;
      waveChecked = 0;
      continue;
    }

    const rowMatch = line.match(/^- \[([ xX])\]\s+\*\*P\d+(?:\.\d+\w?)?\*\*/);
    if (currentWave !== null && rowMatch) {
      waveRows += 1;
      if (String(rowMatch[1]).toLowerCase() === "x") waveChecked += 1;
    }
  }

  flush();
  return out;
}

/**
 * One vocabulary out, whatever went in.
 *
 * plan.yaml is written by hand and says a step is finished in eight different
 * ways — `completed`, `complete`, `done`, `shipped`, `built_committed`,
 * `pilot_complete`, `resolved`, `completed_2026_05_28`. This function used to pass
 * every one of them straight through, and only invented `complete` itself on the
 * wave-level path. The site asks `status === "complete"`, so on 2026-07-30 the
 * Roadmap read **56 / 140 steps done when 117 were** — 61 finished steps counted as
 * unfinished because they had spelled it `completed`. Per-wave counts and the
 * Overview's in-flight list were wrong the same way.
 *
 * So the mapping happens HERE, once, rather than in each of the four consumers:
 * `complete | in_progress | deferred | pending`, and nothing else can reach the
 * snapshot. A ninth spelling in plan.yaml lands on `pending` — visibly not-done,
 * which is the safe direction to be wrong in, and easy to spot and add.
 *
 * Mirrored EXACTLY in regenerate-snapshots.py (`normalize_step_status`); the two
 * are byte-parity-tested by tests/test_snapshot_regenerator_parity.py.
 */
const STATUS_DONE = new Set([
  "complete",
  "completed",
  "done",
  "shipped",
  "built_committed",
  "pilot_complete",
  "resolved",
]);

function normalizeStepStatus(raw) {
  const s = String(raw ?? "")
    .trim()
    .toLowerCase();
  if (!s) return "pending";
  // `completed_2026_05_28` and friends: a done marker with the date welded on.
  if (STATUS_DONE.has(s) || s.startsWith("completed_")) return "complete";
  if (s === "in_progress" || s === "in-progress") return "in_progress";
  if (s === "deferred") return "deferred";
  return "pending";
}

function deriveStepStatus(step, wave) {
  if (typeof step.status === "string" && step.status.trim())
    return normalizeStepStatus(step.status);
  const waveStatus = String(wave?.execution_status ?? "").toLowerCase();
  if (waveStatus.startsWith("completed")) return "complete";
  return "pending";
}

async function readJsonIfExists(p) {
  try {
    return JSON.parse(await readFile(p, "utf-8"));
  } catch {
    return null;
  }
}

async function recentWaveEvents(limit = 15) {
  try {
    const raw = await readFile(WAVE_EVENTS, "utf-8");
    const rows = raw
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => {
        try {
          return JSON.parse(l);
        } catch {
          return null;
        }
      })
      .filter(Boolean);
    return rows.slice(-limit).reverse();
  } catch {
    return [];
  }
}

/** Every book slug, across every bucket. Sorted, so the two generators agree. */
async function listBooks() {
  const slugs = new Set();
  for (const root of BOOK_ROOTS) {
    let entries;
    try {
      entries = await readdir(root, { withFileTypes: true });
    } catch {
      continue; // a bucket with no books yet, or a legacy tree already gone
    }
    for (const e of entries) {
      if (!e.isDirectory()) continue;
      if (e.name.startsWith("_")) continue;
      if (e.name !== e.name.toLowerCase()) continue;
      slugs.add(e.name);
    }
  }
  return [...slugs].sort();
}

/** The book's folder, wherever it lives. Null when no root holds it. */
async function bookDir(slug) {
  for (const root of BOOK_ROOTS) {
    const p = path.join(root, slug);
    try {
      if ((await stat(p)).isDirectory()) return p;
    } catch {
      /* not here */
    }
  }
  return null;
}

/**
 * The book's own name, from meta.yml. The state file has no title field at all,
 * so a caller that reaches for one there prints the slug forever — which is what
 * `books_in_flight` did until 2026-08-06 while the shipped shelf beside it read
 * the real title. One helper now, so the two lists cannot disagree about what a
 * book is called.
 *
 * MIRROR: regenerate-snapshots.py::book_title.
 */
async function bookTitle(dir, slug) {
  try {
    const meta = yaml.load(await readFile(path.join(dir, "meta.yml"), "utf-8"));
    if (typeof meta?.title === "string" && meta.title.trim())
      return meta.title.trim();
  } catch {
    /* no meta.yml: the slug is a worse name than the title, but it is a name */
  }
  return slug;
}

/**
 * What KIND of book this is — its `content_profile`, the same field the pipeline
 * routes on. Read from `_system/series-config.yaml` rather than guessed from the
 * bucket: a `books`-category item can be Islamic or Fiction, which is exactly why
 * the bucket resolver takes the profile and not the category.
 *
 * MIRROR: regenerate-snapshots.py::book_kind.
 */
async function bookKind(dir) {
  try {
    const cfg = yaml.load(
      await readFile(path.join(dir, "_system", "series-config.yaml"), "utf-8"),
    );
    if (typeof cfg?.content_profile === "string" && cfg.content_profile.trim())
      return cfg.content_profile.trim();
  } catch {
    /* no series-config: "unknown" is honest, a guessed profile is not */
  }
  return "unknown";
}

async function bookState(slug) {
  const dir = await bookDir(slug);
  if (!dir) return null;
  const p = path.join(dir, "_system", "orchestrator-state.json");
  try {
    const s = await stat(p);
    if (!s.isFile()) return null;
    const data = JSON.parse(await readFile(p, "utf-8"));
    return {
      slug,
      phase: data.phase ?? "unknown",
      phase_status: data.phase_status ?? "unknown",
      last_completed_phase: data.last_completed_phase ?? null,
    };
  } catch {
    return null;
  }
}

/**
 * The published shelf: every book whose status says it is out, with its episode count.
 *
 * `books_shipped` was carried forward from whatever the JSON already held and computed
 * by nothing, so it sat at `[]` and the Overview's hero opened with "0 books published,
 * 0 episodes" — under a headline about turning manuscripts into podcast series, with
 * two finished books and twenty-eight episodes on disk. The Library page had them the
 * whole time; it reads content directly instead of the snapshot.
 *
 * `status` is the field, not the folder — draft vs published stopped being a location
 * in the 2026-06-04 restructure. Sorted by slug so the two generators agree.
 *
 * MIRROR: regenerate-snapshots.py::books_shipped.
 */
async function booksShipped() {
  const out = [];
  for (const slug of await listBooks()) {
    const dir = await bookDir(slug);
    if (!dir) continue;
    const state = await readJsonIfExists(
      path.join(dir, "_system", "orchestrator-state.json"),
    );
    if (state?.status !== "published") continue;
    const title = await bookTitle(dir, slug);
    // One episode is one `EP##-*.txt` framing file. NOT the sibling directories:
    // some books carry a per-episode folder as well and some do not, so counting
    // directories reported 0 for a 20-episode book and double for a 4-episode one.
    let episodes = 0;
    try {
      const entries = await readdir(path.join(dir, "episodes"), {
        withFileTypes: true,
      });
      episodes = entries.filter(
        (e) => e.isFile() && /^EP\d+.*\.txt$/.test(e.name),
      ).length;
    } catch {
      /* a published book with no episode folder counts zero, not undefined */
    }
    out.push({
      slug,
      title,
      shipped: state.published_at ?? null,
      episodes,
    });
  }
  return out;
}

/**
 * Real money spent in the 30 days before HEAD, in dollars.
 *
 * The Roadmap has always had a "Spend / 30 Days" card and it has always read $0,
 * because `metrics` was the one field the generator never wrote — the page summed an
 * absent key and rendered the zero as if it had measured something. The ledgers were
 * there the whole time: `<book>/_system/cost-ledger.jsonl`, one JSON object a line,
 * `cost_usd` already priced per call.
 *
 * The window ends at HEAD's COMMIT time, not at wall clock, which is the same rule
 * `generatedAt` follows and for the same reason: regenerating at an unchanged commit
 * has to be a no-op, and a window that slides with the clock would make these files
 * perpetually dirty.
 *
 * Only real money — the ledger prices paid APIs (Azure, Gemini); flat-rate Max work
 * writes no row, so nothing here can inflate into token-equivalent theatre.
 *
 * MIRROR: regenerate-snapshots.py::burn_30d_usd.
 */
async function burn30dUsd() {
  const end = Date.parse(generatedAt());
  if (Number.isNaN(end)) return 0;
  const start = end - 30 * 24 * 60 * 60 * 1000;
  let cents = 0; // integer accumulation, so the two generators cannot drift on float
  for (const slug of await listBooks()) {
    const dir = await bookDir(slug);
    if (!dir) continue;
    let raw;
    try {
      raw = await readFile(
        path.join(dir, "_system", "cost-ledger.jsonl"),
        "utf-8",
      );
    } catch {
      continue; // a book that has cost nothing yet has no ledger
    }
    for (const line of raw.split("\n")) {
      if (!line.trim()) continue;
      let row;
      try {
        row = JSON.parse(line);
      } catch {
        continue; // a torn last line mid-write is not a reason to report nothing
      }
      const usd = Number(row?.cost_usd);
      if (!usd) continue;
      const t = Date.parse(String(row?.ts ?? ""));
      if (Number.isNaN(t) || t < start || t > end) continue;
      cents += Math.round(usd * 100);
    }
  }
  return cents / 100;
}

function currentCommit() {
  try {
    return execSync("git -C " + REPO + " rev-parse --short HEAD", {
      encoding: "utf-8",
    }).trim();
  } catch {
    return "unknown";
  }
}

/**
 * Commit timestamp of HEAD, ISO-8601. Console-log only as of 2026-08-05 — it
 * used to be stamped into the tracked snapshots too, which meant a file could
 * never carry its own not-yet-created commit hash and every run produced a
 * metadata-only diff on the NEXT commit, forever. Not written to disk anymore.
 */
function generatedAt() {
  try {
    const out = execSync("git -C " + REPO + " log -1 --format=%cI", {
      encoding: "utf-8",
    }).trim();
    return out || new Date().toISOString();
  } catch {
    return new Date().toISOString();
  }
}

async function readPlanYaml() {
  if (!existsSync(PLAN_YAML)) return null;
  try {
    return yaml.load(await readFile(PLAN_YAML, "utf-8"));
  } catch {
    return null;
  }
}

async function mergeDashboard() {
  const existing = (await readJsonIfExists(
    path.join(DATA, "dashboard-snapshot.json"),
  )) ?? { roadmap: [], waves: [], debt: [], metrics: {} };

  let doneWaves;
  try {
    const checklistRaw = await readFile(WAVE_ACCEPTANCE, "utf-8");
    doneWaves = parseChecklistDoneWaves(checklistRaw);
  } catch {
    doneWaves = new Set();
  }

  const slugs = await listBooks();
  const states = (await Promise.all(slugs.map(bookState))).filter(Boolean);
  const inFlight = await Promise.all(
    states
      .filter(
        (s) =>
          s.phase !== "done" && !["shipped", "merged"].includes(s.phase_status),
      )
      .map(async (s) => {
        const existingMatch = existing.books_in_flight?.find(
          (b) => b.slug === s.slug,
        );
        const dir = await bookDir(s.slug);
        return {
          slug: s.slug,
          title: dir ? await bookTitle(dir, s.slug) : s.slug,
          // DISK WINS. These preferred the previously-snapshotted value, so the
          // first phase a book was ever seen in became the phase it displayed
          // forever: `degrees-of-excellence` sat at "per-chapter-slides/running"
          // for days after finishing 0book-render. A carried-forward value is only
          // right for a field the state file does not hold — which is why
          // cost_to_date_usd below still carries and these two no longer do.
          phase: s.phase,
          phase_status: s.phase_status,
          cost_to_date_usd: existingMatch?.cost_to_date_usd ?? 0,
          kind: dir ? await bookKind(dir) : "unknown",
        };
      }),
  );

  const planYaml = await readPlanYaml();
  let roadmap = existing.roadmap ?? [];
  // plan.yaml splits waves across several list keys (`waves`, `waves_ghj`,
  // `waves_o_ph`, `waves_refactor`, ...). Auto-discover every `waves`/`waves_*`
  // key — mirror of the same discovery in regenerate-snapshots.py — so a new
  // block never requires a generator change.
  const allPlanWaves = Object.entries(planYaml ?? {})
    .filter(
      ([k, v]) => (k === "waves" || k.startsWith("waves_")) && Array.isArray(v),
    )
    .flatMap(([, v]) => v);
  if (allPlanWaves.length > 0) {
    const ids = new Set();
    for (const wave of allPlanWaves) {
      for (const step of wave.steps ?? []) {
        ids.add(step.id);
      }
    }
    // Remove steps that no longer exist in the YAML
    roadmap = roadmap.filter((r) => ids.has(r.id));
    // Add or refresh steps from YAML.
    const existingIds = new Set(roadmap.map((r) => r.id));
    const existingById = new Map(roadmap.map((r) => [r.id, r]));
    const waveOrder = allPlanWaves.map((w) => w.id);
    for (const wave of allPlanWaves) {
      for (const step of wave.steps ?? []) {
        const prev = existingById.get(step.id);
        const next = {
          ...(prev ?? {}),
          id: step.id,
          wave: wave.id,
          title: step.title ?? prev?.title ?? step.id,
          status: deriveStepStatus(step, wave),
          tier: step.tier ?? prev?.tier ?? "T1",
          depends_on: step.depends_on ?? prev?.depends_on ?? [],
          plain: step.plain ?? prev?.plain ?? "",
          tools: step.tools ?? prev?.tools ?? [],
          last_touched: step.last_touched ?? prev?.last_touched,
        };

        const waveNum = WAVE_NUM_BY_LETTER[wave.id];
        if (waveNum && doneWaves.has(waveNum)) {
          next.status = "complete";
        }

        existingById.set(step.id, next);
        if (!existingIds.has(step.id)) roadmap.push(next);

        if (TRACE_STEPS) {
          const source =
            typeof step.status === "string" ? step.status : "(none)";
          const waveExec = wave.execution_status ?? "(none)";
          const prevStatus = prev?.status ?? "(none)";
          console.log(
            `[roadmap-trace] ${step.id} | source=${source} | wave=${waveExec} | prev=${prevStatus} | final=${next.status}`,
          );
        }
      }
    }

    roadmap = roadmap.map((entry) => existingById.get(entry.id) ?? entry);
    // Keep roadmap sorted by wave order then step id
    roadmap.sort((a, b) => {
      const wa = waveOrder.indexOf(a.wave);
      const wb = waveOrder.indexOf(b.wave);
      if (wa !== wb) return wa - wb;
      return String(a.id).localeCompare(String(b.id), undefined, {
        numeric: true,
      });
    });
  }

  // Wave metadata (id/name/plain) drives the PlanDesign grouping — rebuild it
  // from plan.yaml so a newly added waves_* block surfaces without a generator
  // change. Mirror of the same rebuild in regenerate-snapshots.py: one entry
  // per id (letters collide across blocks; prefer the entry carrying steps),
  // skip empty bands, keep the previous plain-English summary when the YAML
  // has none.
  let wavesMeta = existing.waves ?? [];
  if (allPlanWaves.length > 0) {
    const prevById = new Map((existing.waves ?? []).map((w) => [w.id, w]));
    const picked = new Map();
    const order = [];
    for (const w of allPlanWaves) {
      if (!w?.id) continue;
      if (!picked.has(w.id)) {
        order.push(w.id);
        picked.set(w.id, w);
      } else if (w.steps?.length && !picked.get(w.id)?.steps?.length) {
        picked.set(w.id, w);
      }
    }
    wavesMeta = [];
    for (const wid of order) {
      const w = picked.get(wid);
      if (!w.steps?.length) continue; // empty band — no roadmap steps to show
      const plain =
        String(w.summary ?? "")
          .trim()
          .split("\n")[0] ||
        prevById.get(wid)?.plain ||
        "";
      wavesMeta.push({ id: wid, name: w.name ?? wid, plain });
    }
  }

  const merged = {
    ...existing,
    generator: "regenerate-snapshots",
    roadmap,
    waves: wavesMeta,
    books_in_flight: inFlight,
    metrics: { ...(existing.metrics ?? {}), burn_30d_usd: await burn30dUsd() },
    books_shipped: await booksShipped(),
    wave_execution_events: await recentWaveEvents(),
  };
  // Legacy fields from before 2026-08-05: a tracked file can never contain its
  // own not-yet-created commit hash, so stamping one guaranteed a metadata-only
  // diff on every subsequent commit, forever. Stripped here (not just stopped
  // going forward) so one regen run cleans an already-committed file.
  delete merged.generated_at;
  delete merged.source_commit;

  await writeFile(
    path.join(DATA, "dashboard-snapshot.json"),
    JSON.stringify(merged, null, 2) + "\n",
    "utf-8",
  );
  return merged;
}

async function touchExisting(name) {
  const p = path.join(DATA, name);
  const existing = await readJsonIfExists(p);
  if (!existing) return;
  delete existing.generated_at;
  delete existing.source_commit;
  await writeFile(p, JSON.stringify(existing, null, 2) + "\n", "utf-8");
}

/**
 * Regenerate architecture-snapshot.json from live canonical sources:
 *  - agents:  counted and populated from infra/claude-agents/*.md
 *  - adrs:    parsed from _workspace/plan/architecture.md DR-* table rows
 *  - phases/layers/modules/archetypes: preserved from existing snapshot
 *    (authored by the podcast-planner agent; this script never overwrites them)
 */
async function mergeArchitecture() {
  const p = path.join(DATA, "architecture-snapshot.json");
  const snap = (await readJsonIfExists(p)) ?? {
    phases: [],
    agents: [],
    layers: [],
    adrs: [],
    modules: [],
    archetypes: [],
  };

  // ── Agents: built from infra/claude-agents/*.md ────────────────────────
  const agentsDir = path.join(REPO, "infra", "claude-agents");
  let agentFiles = [];
  try {
    const entries = await readdir(agentsDir);
    // sorted to match the .py leg's sorted() — readdir order is not guaranteed
    agentFiles = entries
      .filter((f) => f.endsWith(".md") && f !== "_README.md")
      .sort();
  } catch {}

  const existingAgentById = new Map((snap.agents ?? []).map((a) => [a.id, a]));
  const agents = await Promise.all(
    agentFiles.map(async (f) => {
      const id = f.replace(".md", "");
      const prev = existingAgentById.get(id) ?? {};
      let content;
      try {
        content = await readFile(path.join(agentsDir, f), "utf-8");
      } catch {
        // A transient read failure must not delete an agent already recorded.
        return Object.keys(prev).length ? prev : null;
      }
      const fmMatch = content.match(/^---\n([\s\S]*?)\n---/);
      let fm = {};
      if (fmMatch) {
        try {
          fm = yaml.load(fmMatch[1]) ?? {};
        } catch {}
      }
      const desc = String(fm.description ?? "");
      const titleCase = id
        .split("-")
        .map((w) => w[0].toUpperCase() + w.slice(1))
        .join(" ");
      const entry = {
        id,
        name: titleCase,
        role: desc.split(".")[0].slice(0, 80),
        icon: "robot",
        tone: "neutral",
        plain: desc.length > 240 ? desc.slice(0, 237) + "\u2026" : desc,
        what_it_knows: `See infra/claude-agents/${f}`,
        boundary_in: "",
        boundary_out: "",
        does_not: "",
        cost_profile: "varies",
        failure_mode: "surfaces error and halts",
      };
      for (const key of AGENT_CURATED_FIELDS) {
        if (prev[key]) entry[key] = prev[key];
      }
      return entry;
    }),
  ).then((list) => list.filter(Boolean));

  // ── ADRs: parsed from architecture.md ──────────────────────────────────
  const archPath = path.join(REPO, "_workspace", "plan", "architecture.md");
  let adrs = snap.adrs ?? [];
  if (existsSync(archPath)) {
    const md = await readFile(archPath, "utf-8");
    const existingAdrById = new Map(adrs.map((a) => [a.id, a]));
    const matches = [...md.matchAll(/\|\s*(DR-\d+)\s*\|\s*\*\*([^*]+)\*\*/g)];
    if (matches.length > 0) {
      adrs = matches.map((m) => {
        const id = m[1].trim();
        const title = m[2].trim();
        return existingAdrById.get(id) ?? { id, title, plain: title };
      });
    }
  }

  const merged = {
    ...snap,
    agents,
    adrs,
  };
  delete merged.generated_at;
  delete merged.source_commit;
  await writeFile(p, JSON.stringify(merged, null, 2) + "\n", "utf-8");
}

async function main() {
  const dash = await mergeDashboard();
  await mergeArchitecture();
  await touchExisting("infrastructure-snapshot.json");

  try {
    writeFileSync(SENTINEL, new Date().toISOString() + "\n", "utf-8");
  } catch {}

  console.log(`snapshots regenerated @ ${generatedAt()}`);
  console.log(`  source_commit: ${currentCommit()}`);
  console.log(`  books in flight: ${dash.books_in_flight.length}`);
  console.log(`  roadmap steps: ${dash.roadmap.length}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
