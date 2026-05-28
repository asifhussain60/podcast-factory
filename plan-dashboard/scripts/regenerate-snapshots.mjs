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

import { readFile, writeFile, readdir, stat } from 'node:fs/promises';
import { existsSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execSync } from 'node:child_process';
import yaml from 'js-yaml';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const APP = path.resolve(HERE, '..');
const REPO = path.resolve(APP, '..');
const DATA = path.join(APP, 'src', 'data');
const DRAFTS = path.join(REPO, 'content', 'drafts');
const PLAN_YAML = path.join(REPO, '_workspace', 'plan', 'refactor', 'plan.yaml');
const WAVE_ACCEPTANCE = path.join(REPO, '_workspace', 'plan', 'operations', 'wave-acceptance-checklist.md');
const WAVE_EVENTS = path.join(REPO, '_workspace', 'plan', 'refactor', 'wave-execution-events.jsonl');
const SENTINEL = path.join(APP, '.snapshot-version');
const TRACE_STEPS = process.argv.includes('--trace-steps') || process.env.SNAPSHOT_TRACE === '1';

const WAVE_NUM_BY_LETTER = { A: 1, B: 2, C: 3, D: 4, E: 5 };

function parseChecklistDoneWaves(markdown) {
  const out = new Set();
  if (!markdown || typeof markdown !== 'string') return out;

  const lines = markdown.split('\n');
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
      if (String(rowMatch[1]).toLowerCase() === 'x') waveChecked += 1;
    }
  }

  flush();
  return out;
}

function deriveStepStatus(step, wave) {
  if (typeof step.status === 'string' && step.status.trim()) return step.status.trim();
  const waveStatus = String(wave?.execution_status ?? '').toLowerCase();
  if (waveStatus.startsWith('completed')) return 'complete';
  return 'pending';
}

async function readJsonIfExists(p) {
  try { return JSON.parse(await readFile(p, 'utf-8')); } catch { return null; }
}

async function recentWaveEvents(limit = 15) {
  try {
    const raw = await readFile(WAVE_EVENTS, 'utf-8');
    const rows = raw
      .split('\n')
      .map((l) => l.trim())
      .filter(Boolean)
      .map((l) => {
        try { return JSON.parse(l); } catch { return null; }
      })
      .filter(Boolean);
    return rows.slice(-limit).reverse();
  } catch {
    return [];
  }
}

async function listBooks() {
  try {
    const entries = await readdir(DRAFTS, { withFileTypes: true });
    return entries.filter((e) => e.isDirectory() && !e.name.startsWith('_') && e.name === e.name.toLowerCase()).map((e) => e.name);
  } catch { return []; }
}

async function bookState(slug) {
  const p = path.join(DRAFTS, slug, '_system', 'orchestrator-state.json');
  try {
    const s = await stat(p);
    if (!s.isFile()) return null;
    const data = JSON.parse(await readFile(p, 'utf-8'));
    return {
      slug,
      phase: data.phase ?? 'unknown',
      phase_status: data.phase_status ?? 'unknown',
      last_completed_phase: data.last_completed_phase ?? null,
    };
  } catch { return null; }
}

function recentCommits() {
  try {
    const out = execSync('git -C ' + REPO + ' log -n 10 --pretty=format:"%h|%s|%ad" --date=short', { encoding: 'utf-8' });
    return out.trim().split('\n').map((line) => {
      const [sha, subject, date] = line.split('|');
      return { sha, subject, date };
    });
  } catch { return []; }
}

function currentCommit() {
  try { return execSync('git -C ' + REPO + ' rev-parse --short HEAD', { encoding: 'utf-8' }).trim(); }
  catch { return 'unknown'; }
}

async function readPlanYaml() {
  if (!existsSync(PLAN_YAML)) return null;
  try { return yaml.load(await readFile(PLAN_YAML, 'utf-8')); } catch { return null; }
}

async function mergeDashboard() {
  const existing = (await readJsonIfExists(path.join(DATA, 'dashboard-snapshot.json'))) ?? { roadmap: [], waves: [], debt: [], metrics: {} };

  let doneWaves = new Set();
  try {
    const checklistRaw = await readFile(WAVE_ACCEPTANCE, 'utf-8');
    doneWaves = parseChecklistDoneWaves(checklistRaw);
  } catch {
    doneWaves = new Set();
  }

  const slugs = await listBooks();
  const states = (await Promise.all(slugs.map(bookState))).filter(Boolean);
  const inFlight = states
    .filter((s) => s.phase !== 'done' && !['shipped', 'merged'].includes(s.phase_status))
    .map((s) => {
      const existingMatch = existing.books_in_flight?.find((b) => b.slug === s.slug);
      return {
        slug: s.slug,
        title: existingMatch?.title ?? s.slug,
        phase: existingMatch?.phase ?? s.phase,
        phase_status: existingMatch?.phase_status ?? s.phase_status,
        cost_to_date_usd: existingMatch?.cost_to_date_usd ?? 0,
        kind: existingMatch?.kind ?? 'unknown',
      };
    });

  const planYaml = await readPlanYaml();
  let roadmap = existing.roadmap ?? [];
  // plan.yaml uses two wave-list keys due to the pre-existing structural split:
  //   `waves`     — waves A-E (and F, embedded in excluded_by_design)
  //   `waves_ghj` — waves G, H, I (added 2026-05-28)
  // Merge both arrays so the snapshot captures all planned steps.
  const allPlanWaves = [...(planYaml?.waves ?? []), ...(planYaml?.waves_ghj ?? [])];
  if (allPlanWaves.length > 0) {
    const ids = new Set();
    for (const wave of allPlanWaves) {
      for (const step of (wave.steps ?? [])) {
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
      for (const step of (wave.steps ?? [])) {
        const prev = existingById.get(step.id);
        const next = {
          ...(prev ?? {}),
          id: step.id,
          wave: wave.id,
          title: step.title ?? prev?.title ?? step.id,
          status: deriveStepStatus(step, wave),
          tier: step.tier ?? prev?.tier ?? 'T1',
          depends_on: step.depends_on ?? prev?.depends_on ?? [],
          plain: step.plain ?? prev?.plain ?? '',
          tools: step.tools ?? prev?.tools ?? [],
          last_touched: step.last_touched ?? prev?.last_touched,
        };

        const waveNum = WAVE_NUM_BY_LETTER[wave.id];
        if (waveNum && doneWaves.has(waveNum)) {
          next.status = 'complete';
        }

        existingById.set(step.id, next);
        if (!existingIds.has(step.id)) roadmap.push(next);

        if (TRACE_STEPS) {
          const source = typeof step.status === 'string' ? step.status : '(none)';
          const waveExec = wave.execution_status ?? '(none)';
          const prevStatus = prev?.status ?? '(none)';
          console.log(`[roadmap-trace] ${step.id} | source=${source} | wave=${waveExec} | prev=${prevStatus} | final=${next.status}`);
        }
      }
    }

    roadmap = roadmap.map((entry) => existingById.get(entry.id) ?? entry);
    // Keep roadmap sorted by wave order then step id
    roadmap.sort((a, b) => {
      const wa = waveOrder.indexOf(a.wave);
      const wb = waveOrder.indexOf(b.wave);
      if (wa !== wb) return wa - wb;
      return String(a.id).localeCompare(String(b.id), undefined, { numeric: true });
    });
  }

  const merged = {
    ...existing,
    generated_at: new Date().toISOString(),
    source_commit: currentCommit(),
    generator: 'regenerate-snapshots.mjs',
    roadmap,
    books_in_flight: inFlight,
    recent_commits: recentCommits(),
    wave_execution_events: await recentWaveEvents(),
  };

  await writeFile(path.join(DATA, 'dashboard-snapshot.json'), JSON.stringify(merged, null, 2) + '\n', 'utf-8');
  return merged;
}

async function touchExisting(name) {
  const p = path.join(DATA, name);
  const existing = await readJsonIfExists(p);
  if (!existing) return;
  existing.generated_at = new Date().toISOString();
  existing.source_commit = currentCommit();
  await writeFile(p, JSON.stringify(existing, null, 2) + '\n', 'utf-8');
}

/**
 * Regenerate architecture-snapshot.json from live canonical sources:
 *  - agents:  counted and populated from infra/claude-agents/*.md
 *  - adrs:    parsed from _workspace/plan/architecture.md DR-* table rows
 *  - phases/layers/modules/archetypes: preserved from existing snapshot
 *    (authored by the podcast-planner agent; this script never overwrites them)
 */
async function mergeArchitecture() {
  const p = path.join(DATA, 'architecture-snapshot.json');
  const snap = (await readJsonIfExists(p)) ?? { phases: [], agents: [], layers: [], adrs: [], modules: [], archetypes: [] };

  // ── Agents: built from infra/claude-agents/*.md ────────────────────────
  const agentsDir = path.join(REPO, 'infra', 'claude-agents');
  let agentFiles = [];
  try {
    const entries = await readdir(agentsDir);
    agentFiles = entries.filter(f => f.endsWith('.md') && f !== '_README.md');
  } catch {}

  const existingAgentById = new Map((snap.agents ?? []).map(a => [a.id, a]));
  const agents = await Promise.all(agentFiles.map(async (f) => {
    const id = f.replace('.md', '');
    if (existingAgentById.has(id)) return existingAgentById.get(id);
    const content = await readFile(path.join(agentsDir, f), 'utf-8');
    const fmMatch = content.match(/^---\n([\s\S]*?)\n---/);
    let fm = {};
    if (fmMatch) { try { fm = yaml.load(fmMatch[1]) ?? {}; } catch {} }
    const desc = String(fm.description ?? '');
    const titleCase = id.split('-').map(w => w[0].toUpperCase() + w.slice(1)).join(' ');
    return {
      id,
      name: titleCase,
      role: desc.split('.')[0].slice(0, 80),
      icon: 'robot',
      tone: 'neutral',
      plain: desc.length > 240 ? desc.slice(0, 237) + '\u2026' : desc,
      what_it_knows: `See infra/claude-agents/${f}`,
      boundary_in: '',
      boundary_out: '',
      does_not: '',
      cost_profile: 'varies',
      failure_mode: 'surfaces error and halts',
    };
  }));

  // ── ADRs: parsed from architecture.md ──────────────────────────────────
  const archPath = path.join(REPO, '_workspace', 'plan', 'architecture.md');
  let adrs = snap.adrs ?? [];
  if (existsSync(archPath)) {
    const md = await readFile(archPath, 'utf-8');
    const existingAdrById = new Map(adrs.map(a => [a.id, a]));
    const matches = [...md.matchAll(/\|\s*(DR-\d+)\s*\|\s*\*\*([^*]+)\*\*/g)];
    if (matches.length > 0) {
      adrs = matches.map(m => {
        const id = m[1].trim();
        const title = m[2].trim();
        return existingAdrById.get(id) ?? { id, title, plain: title };
      });
    }
  }

  const merged = { ...snap, generated_at: new Date().toISOString(), source_commit: currentCommit(), agents, adrs };
  await writeFile(p, JSON.stringify(merged, null, 2) + '\n', 'utf-8');
}

async function main() {
  const dash = await mergeDashboard();
  await mergeArchitecture();
  await touchExisting('infrastructure-snapshot.json');

  try { writeFileSync(SENTINEL, new Date().toISOString() + '\n', 'utf-8'); } catch {}

  console.log(`snapshots regenerated @ ${dash.generated_at}`);
  console.log(`  source_commit: ${dash.source_commit}`);
  console.log(`  books in flight: ${dash.books_in_flight.length}`);
  console.log(`  roadmap steps: ${dash.roadmap.length}`);
  console.log(`  recent commits: ${dash.recent_commits.length}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
