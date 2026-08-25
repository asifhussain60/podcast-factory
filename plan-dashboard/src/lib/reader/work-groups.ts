/**
 * work-groups.ts — multi-volume groupings DECLARED on disk.
 *
 * The Studio shelf already folds a multi-volume work into one collapsible deck,
 * but it decides what a volume is from the SLUG: `<work>-vol-NN`. That shape is
 * true of a work whose volumes are nested directories under one parent — Asas
 * al-Taweel, al-Anwaar al-Lateefah — and it is the only shape the shelf could
 * see.
 *
 * Mukhtasar ul-Asar is the other shape. Its two volumes are independently
 * published, FLAT, top-level folders (`content/Islamic/mukhtasar-ul-asar-1/`
 * and `-2/`), each with its own `_system/`, `book/` and `m4a/`. Nothing about
 * those two slugs says they are one work, so the shelf drew them as two
 * unrelated books while the Podcast Factory Library — reading a declaration —
 * stacked them correctly. The two surfaces disagreed about what a work IS.
 *
 * This module removes the disagreement by reading the SAME declaration the
 * Library reads: `content/<Bucket>/_listener-groups/<name>.yml`, whose only
 * other reader is `scripts/podcast/sync_listener_work_groups.py`. Its module
 * docstring is the authority on why that convention exists rather than a real
 * `work.yml` — in short, a `work.yml` dropped beside two already-published flat
 * books would make `_paths.is_work_parent()` treat them as an unfinished nested
 * work with zero discoverable volumes. Nothing on disk moves to be grouped.
 *
 * WHAT THIS DELIBERATELY DOES NOT READ: `work.yml`. The nested case already
 * works, through the slug shape, and it works even for a work that has NO
 * manifest at all (asaas-al-taveel has none — its deck is assembled purely from
 * its volumes). Reading both here would mean two mechanisms competing to group
 * the same slugs, and the failure that produces — a volume in two decks — is
 * worse than the one being fixed.
 *
 * The parse is pinned against its Python counterpart by a shared fixture,
 * `plan-dashboard/scripts/lib/work-groups.fixtures.json`, because a divergence
 * is silent in the same direction as the original bug: one surface stacks a set
 * and the other does not, and neither says why.
 */

import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { parse } from "yaml";

import { BUCKETS, getRepoRoot } from "../content-paths";

/** Mirrors `sync_listener_work_groups.LISTENER_GROUPS_DIR`. The leading
 *  underscore is load-bearing: every content scan on both sides of the repo
 *  skips `_`-prefixed directories, which is what keeps this folder from being
 *  read as a book. */
export const LISTENER_GROUPS_DIR = "_listener-groups";

export interface WorkGroupVolume {
  slug: string;
  order: number;
}

export interface WorkGroup {
  workSlug: string;
  title: string;
  bucket: string;
  volumes: WorkGroupVolume[];
}

/**
 * One manifest, parsed — or `null` when it does not describe a group.
 *
 * The acceptance rules are `_group_from_manifest`'s, deliberately, down to the
 * two that look like edge cases and are not:
 *
 *   • `work_slug` falls back to the file's own name, so a declaration need not
 *     repeat itself.
 *   • FEWER THAN TWO volumes is not a group. A one-volume "set" would render a
 *     deck the reader must open to find a single book inside — strictly worse
 *     than the plain card it replaced.
 *
 * A malformed volume entry is skipped rather than failing the whole manifest:
 * the remaining volumes are still a true statement about the work, and dropping
 * all of them over one bad row would silently un-group a shipped set.
 */
export function parseWorkGroupManifest(
  data: unknown,
  defaultSlug: string,
): WorkGroup | null {
  if (!data || typeof data !== "object" || Array.isArray(data)) return null;
  const m = data as Record<string, unknown>;

  const workSlug =
    typeof m.work_slug === "string" && m.work_slug ? m.work_slug : defaultSlug;
  const title = typeof m.title === "string" ? m.title : "";
  const bucket = typeof m.bucket === "string" ? m.bucket : "";
  if (!workSlug || !title || !bucket || !Array.isArray(m.volumes)) return null;

  const volumes: WorkGroupVolume[] = [];
  for (const v of m.volumes) {
    if (!v || typeof v !== "object" || Array.isArray(v)) continue;
    const row = v as Record<string, unknown>;
    if (typeof row.slug !== "string" || !row.slug) continue;
    volumes.push({
      slug: row.slug,
      order: typeof row.order === "number" ? row.order : 0,
    });
  }
  if (volumes.length < 2) return null;

  volumes.sort((a, b) => a.order - b.order);
  return { workSlug, title, bucket, volumes };
}

/**
 * Every declared grouping on disk, across every bucket.
 *
 * Generic over bucket and slug — no book is named here, and adding a set is
 * adding a file. Unreadable or malformed manifests are skipped rather than
 * thrown: this builds a SHELF, and a shelf that fails to render because one
 * declaration has a typo is a worse outcome than one set drawn unstacked.
 */
export async function readDeclaredWorkGroups(): Promise<WorkGroup[]> {
  const root = join(getRepoRoot(), "content");
  const groups: WorkGroup[] = [];

  for (const bucket of BUCKETS) {
    const dir = join(root, bucket, LISTENER_GROUPS_DIR);
    let names: string[];
    try {
      names = (await readdir(dir)).filter((n) => n.endsWith(".yml")).sort();
    } catch {
      continue; // no declarations in this bucket, which is the normal case
    }
    for (const name of names) {
      try {
        const raw = await readFile(join(dir, name), "utf-8");
        const group = parseWorkGroupManifest(
          parse(raw),
          name.replace(/\.yml$/, ""),
        );
        if (group) groups.push(group);
      } catch {
        /* unreadable or unparseable — skipped, never fatal */
      }
    }
  }
  return groups;
}

/**
 * slug -> its place in a declared work, for the volumes of every group.
 *
 * A flat lookup rather than the group list, because the shelf asks the question
 * one book at a time and asking it as "which group is this in?" is what the
 * caller already does for the `-vol-NN` case.
 */
export function volumeIndex(
  groups: WorkGroup[],
): Map<string, { workSlug: string; title: string; order: number }> {
  const index = new Map<
    string,
    { workSlug: string; title: string; order: number }
  >();
  for (const g of groups) {
    for (const v of g.volumes) {
      // First declaration wins. Two manifests claiming one volume is a mistake
      // somebody has to fix; silently moving the book to whichever file sorted
      // last would hide it.
      if (!index.has(v.slug)) {
        index.set(v.slug, {
          workSlug: g.workSlug,
          title: g.title,
          order: v.order,
        });
      }
    }
  }
  return index;
}
