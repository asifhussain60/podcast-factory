/**
 * Claude Code's plan-mode output (`~/.claude/plans/*.md`) is machine-global —
 * every repo the harness has touched writes into the same folder, with no
 * project tag inside the file. This module reads it live (same request-time
 * `fs` pattern `snag-list.astro` already uses for `_workspace/plan/`) and
 * best-effort filters to the plans that are actually about podcast-factory,
 * per Asif's explicit choice over the alternative (show everything, unfiltered).
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { homedir } from "node:os";
import { join, resolve } from "node:path";

export interface PlanSummary {
  slug: string;
  title: string;
  mtimeMs: number;
  wordCount: number;
  snippet: string;
}

export interface PlanDetail extends PlanSummary {
  raw: string;
}

function plansDir(): string {
  return resolve(homedir(), ".claude", "plans");
}

/** Book slugs already living in this repo's content buckets — matching one
 *  by name is as strong a signal as matching the repo name itself, and it
 *  costs one cheap readdir per bucket instead of a hardcoded, staling list. */
function bookSlugMarkers(): string[] {
  const buckets = ["Islamic", "Technical", "Fiction", "Guides"];
  const contentRoot = resolve(process.cwd(), "..", "content");
  const slugs: string[] = [];
  for (const bucket of buckets) {
    try {
      for (const entry of readdirSync(join(contentRoot, bucket), {
        withFileTypes: true,
      })) {
        if (entry.isDirectory()) slugs.push(entry.name.toLowerCase());
      }
    } catch {
      // bucket may not exist yet (e.g. Fiction) — fine, skip it.
    }
  }
  return slugs;
}

const STRONG_MARKERS = [
  "podcast-factory",
  "podcast factory",
  "plan-dashboard",
  "scripts/podcast",
  "_workspace/plan",
  "pending-work.yaml",
  "notebooklm",
  "safinaverse.com",
  "listener/app",
  "listener/scripts",
  "book-challenger",
  "book.md",
  "book-composer",
  "orchestrate_book",
  "content/islamic",
  "content/technical",
  "content/fiction",
  "content/guides",
  "the snag list",
  "the podcast factory library",
  "the podcast factory astro site",
];

/** Is this plan file's text about podcast-factory? Best-effort by design —
 *  a plan with no strong marker and no matching book slug is excluded, which
 *  will misfile some plans in either direction (Asif's own accepted tradeoff
 *  over showing the whole unfiltered machine-wide folder). */
function isRepoRelevant(text: string, slugMarkers: string[]): boolean {
  const lower = text.toLowerCase();
  if (STRONG_MARKERS.some((m) => lower.includes(m))) return true;
  return slugMarkers.some((slug) => lower.includes(slug));
}

function extractTitle(text: string, fallbackSlug: string): string {
  const heading = text.match(/^#{1,2}\s+(.+)$/m);
  if (heading) return heading[1].trim();
  return fallbackSlug
    .replace(/[-_]+/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

/** First real paragraph after the title — skips headings and blank lines,
 *  stops at the next heading or blank line, so it reads as one sentence-ish
 *  snippet rather than a wall of the whole Context section. */
function extractSnippet(text: string): string {
  const lines = text.split("\n");
  let started = false;
  const buf: string[] = [];
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (started) break;
      continue;
    }
    if (trimmed.startsWith("#")) {
      if (started) break;
      continue;
    }
    started = true;
    buf.push(trimmed);
    if (buf.join(" ").length > 220) break;
  }
  const snippet = buf.join(" ");
  return snippet.length > 220 ? snippet.slice(0, 217) + "…" : snippet;
}

function wordCount(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

function readPlanFiles(): Array<{ slug: string; path: string }> {
  const dir = plansDir();
  const out: Array<{ slug: string; path: string }> = [];
  try {
    const entries = readdirSync(dir, {
      encoding: "utf-8",
      withFileTypes: true,
    });
    for (const entry of entries) {
      if (entry.isFile() && entry.name.endsWith(".md")) {
        out.push({
          slug: entry.name.slice(0, -3),
          path: join(dir, entry.name),
        });
      } else if (entry.isDirectory()) {
        // one level deep only (covers the harness's `_done/` archive folder)
        try {
          const subEntries = readdirSync(join(dir, entry.name), {
            encoding: "utf-8",
          });
          for (const sub of subEntries) {
            if (sub.endsWith(".md")) {
              out.push({
                slug: sub.slice(0, -3),
                path: join(dir, entry.name, sub),
              });
            }
          }
        } catch {
          // unreadable subdirectory — skip it, not fatal to the page.
        }
      }
    }
  } catch {
    return out;
  }
  return out;
}

/** Every podcast-factory-relevant plan, newest first. Empty on any read
 *  failure (missing folder, permissions) rather than breaking the page. */
export function listPlans(): PlanSummary[] {
  const slugMarkers = bookSlugMarkers();
  const summaries: PlanSummary[] = [];
  for (const { slug, path } of readPlanFiles()) {
    let text: string;
    let mtimeMs: number;
    try {
      text = readFileSync(path, "utf-8");
      mtimeMs = statSync(path).mtimeMs;
    } catch {
      continue;
    }
    if (!isRepoRelevant(text, slugMarkers)) continue;
    summaries.push({
      slug,
      title: extractTitle(text, slug),
      mtimeMs,
      wordCount: wordCount(text),
      snippet: extractSnippet(text),
    });
  }
  return summaries.sort((a, b) => b.mtimeMs - a.mtimeMs);
}

/** One plan's full text, or null if it doesn't exist / isn't readable. */
export function readPlan(slug: string): PlanDetail | null {
  for (const candidate of readPlanFiles()) {
    if (candidate.slug !== slug) continue;
    try {
      const raw = readFileSync(candidate.path, "utf-8");
      const mtimeMs = statSync(candidate.path).mtimeMs;
      return {
        slug,
        title: extractTitle(raw, slug),
        mtimeMs,
        wordCount: wordCount(raw),
        snippet: extractSnippet(raw),
        raw,
      };
    } catch {
      return null;
    }
  }
  return null;
}
