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
const SENTINEL = path.join(APP, '.snapshot-version');

async function readJsonIfExists(p) {
  try { return JSON.parse(await readFile(p, 'utf-8')); } catch { return null; }
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
  if (planYaml?.waves) {
    const ids = new Set();
    for (const wave of planYaml.waves) {
      for (const step of (wave.steps ?? [])) {
        ids.add(step.id);
      }
    }
    roadmap = roadmap.filter((r) => ids.has(r.id));
  }

  const merged = {
    ...existing,
    generated_at: new Date().toISOString(),
    source_commit: currentCommit(),
    generator: 'regenerate-snapshots.mjs',
    roadmap,
    books_in_flight: inFlight,
    recent_commits: recentCommits(),
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

async function main() {
  const dash = await mergeDashboard();
  await touchExisting('architecture-snapshot.json');
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
