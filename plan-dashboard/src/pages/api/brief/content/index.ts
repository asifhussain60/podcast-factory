/**
 * GET /api/brief/content → every existing piece of content, for the Intake picker.
 *
 * Read-only. Grouped by shelf on the client; sorted here so the order is stable
 * between loads. Title comes from meta.yml when there is one — `claude-code-training`
 * has none — falling back to the slug so nothing is nameless in the list.
 *
 * `touched` is when the book was last WORKED ON, so the picker can offer "what I
 * was working on" as an order (Asif, 2026-08-31). Taken from the newest mtime
 * among the few files a working session actually writes, rather than from the
 * folder's own mtime — a directory's timestamp moves when any child is added or
 * removed, including by a git checkout, so it answers "when did this folder
 * change" and not "when did I last work on this book".
 */
import type { APIRoute } from "astro";
import { existsSync, statSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import yaml from "js-yaml";
import { apiOk, apiServerError } from "../../../../lib/api-responses";
import { listContent } from "../../../../lib/content-paths";

export const prerender = false;

export const GET: APIRoute = async () => {
  try {
    const refs = await listContent();
    const items = await Promise.all(
      refs.map(async (r) => {
        let title = r.slug;
        const metaPath = join(r.dir, "meta.yml");
        if (existsSync(metaPath)) {
          try {
            const doc = yaml.load(await readFile(metaPath, "utf8")) as Record<
              string,
              unknown
            > | null;
            if (doc && typeof doc.title === "string" && doc.title.trim()) {
              title = doc.title.trim();
            }
          } catch {
            // Unparseable meta.yml: the slug is still a true name for it.
          }
        }
        // The state file is written by every phase; series-config and meta by
        // every settings save; book.md by every compose. Between them they
        // cover the ways a book gets worked on. A book missing all four is not
        // an error — it sorts to the bottom of "recently worked on", which is
        // exactly where a folder nobody has touched belongs.
        let touched = 0;
        for (const rel of [
          join("_system", "orchestrator-state.json"),
          join("_system", "series-config.yaml"),
          "meta.yml",
          join("book", "book.md"),
        ]) {
          try {
            touched = Math.max(touched, statSync(join(r.dir, rel)).mtimeMs);
          } catch {
            /* absent files simply do not vote */
          }
        }
        return {
          slug: r.slug,
          title,
          bucket: r.bucket,
          status: r.status,
          touched,
        };
      }),
    );
    items.sort(
      (a, b) =>
        a.bucket.localeCompare(b.bucket) || a.title.localeCompare(b.title),
    );
    return apiOk({ items });
  } catch (e) {
    return apiServerError(`Could not list content: ${String(e)}`);
  }
};
