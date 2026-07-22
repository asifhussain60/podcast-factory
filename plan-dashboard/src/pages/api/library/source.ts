import type { APIRoute } from "astro";
import { readFile, realpath, stat } from "node:fs/promises";
import { basename, extname, resolve } from "node:path";
import { findContent, getRepoRoot } from "../../../lib/content-paths";

export const prerender = false;

// Serves the files meta.yml points at OUTSIDE the book folder (raw source
// PDF/audio). The client passes only a FIELD NAME — the path comes from
// meta.yml on disk, so there is no client-controlled path to traverse.
// Targets must still resolve inside the repo root.
const ALLOWED_FIELDS = new Set(["source_pdf", "source_audio"]);

const MIME: Record<string, string> = {
  pdf: "application/pdf",
  mp3: "audio/mpeg",
  m4a: "audio/mp4",
  wav: "audio/wav",
};

export const GET: APIRoute = async ({ url }) => {
  const slug = url.searchParams.get("slug");
  const field = url.searchParams.get("field");
  if (!slug || !field)
    return new Response("missing slug or field", { status: 400 });
  if (!ALLOWED_FIELDS.has(field))
    return new Response("field not allowed", { status: 400 });

  const ref = await findContent(slug);
  if (!ref) return new Response("content not found", { status: 404 });

  let metaText: string;
  try {
    metaText = await readFile(resolve(ref.dir, "meta.yml"), "utf-8");
  } catch {
    return new Response("no meta.yml", { status: 404 });
  }
  const m = metaText.match(new RegExp(`^${field}\\s*:\\s*(.+)$`, "m"));
  if (!m) return new Response("field not set", { status: 404 });
  const relValue = m[1].trim().replace(/^['"]/, "").replace(/['"]$/, "");

  let target: string;
  let root: string;
  try {
    target = await realpath(resolve(ref.dir, relValue));
    root = await realpath(getRepoRoot());
  } catch {
    return new Response("not found", { status: 404 });
  }
  if (!target.startsWith(root + "/")) {
    return new Response("path escapes repo", { status: 400 });
  }

  let s;
  try {
    s = await stat(target);
  } catch {
    return new Response("not found", { status: 404 });
  }
  if (!s.isFile()) return new Response("not a file", { status: 400 });

  const ext = extname(target).toLowerCase().replace(/^\./, "");
  const mime = MIME[ext] ?? "application/octet-stream";
  const buf = await readFile(target);
  return new Response(buf, {
    status: 200,
    headers: {
      "content-type": mime,
      "content-length": String(buf.byteLength),
      "content-disposition": `inline; filename="${basename(target).replace(/"/g, "")}"`,
    },
  });
};
