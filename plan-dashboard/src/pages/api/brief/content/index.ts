/**
 * GET /api/brief/content → every existing piece of content, for the Intake picker.
 *
 * Read-only. Grouped by shelf on the client; sorted here so the order is stable
 * between loads. Title comes from meta.yml when there is one — `claude-code-training`
 * has none — falling back to the slug so nothing is nameless in the list.
 */
import type { APIRoute } from "astro";
import { existsSync } from "node:fs";
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
        return { slug: r.slug, title, bucket: r.bucket, status: r.status };
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
