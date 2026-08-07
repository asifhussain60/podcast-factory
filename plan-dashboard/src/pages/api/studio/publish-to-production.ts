/**
 * publish-to-production.ts — POST /api/studio/publish-to-production
 *
 * The Book Composer's "Publish to production" button. Runs
 * scripts/podcast/publish_to_production.py, which accepts the book's Companion
 * cards, pushes its text and recordings to the Podcast Factory Library, turns the
 * book's visibility on, and then reads the live database back to prove each of
 * those things happened.
 *
 * STREAMS, rather than answering at the end. The run takes minutes when there are
 * recordings to upload, which is far past any sensible request timeout, and — more
 * to the point — a person watching a button that says nothing for four minutes
 * cannot tell a slow upload from a hung one. Each line of the child's output is
 * one NDJSON event, forwarded the moment it arrives.
 *
 * There is no JSON body on the way back and no `apiOk` wrapper for that reason:
 * the LAST event is the result. The client reads `{ event: "done", verified }`.
 *
 * Body: { slug, accept?, transcripts?, media?, rebuildPdf?, dryRun? }
 * The four options default to the safe everyday run — accept cards, transcribe
 * new episodes, upload media, do not re-render the PDF.
 */
import type { APIRoute } from "astro";
import { spawn } from "node:child_process";
import { join } from "node:path";
import {
  findContentDirSync,
  getRepoRoot,
  getPythonBin,
} from "../../../lib/content-paths";
import { apiError, apiOk } from "../../../lib/api-responses";

export const prerender = false;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/** Body flags -> the driver's flags. Every one of these SUBTRACTS work, so a
 *  body that says nothing gets the complete publish rather than a partial one. */
function flagsFor(body: Record<string, unknown>): string[] {
  const flags: string[] = [];
  if (body.accept === false) flags.push("--no-accept");
  if (body.transcripts === false) flags.push("--skip-transcripts");
  if (body.media === false) flags.push("--skip-media");
  if (body.rebuildPdf === true) flags.push("--rebuild-pdf");
  if (body.dryRun === true) flags.push("--dry-run");
  return flags;
}

/**
 * GET ?slug=… — has this book anything to publish?
 *
 * Free by construction: the driver's `--state` mode reads the book off disk and
 * touches no network, because the Composer asks this on every page load. It
 * answers `pending` for three different situations that the button treats alike
 * — never published, last publish unverified, chapters or cards changed since —
 * and `reason` is what the button's tooltip says.
 */
export const GET: APIRoute = async ({ url }) => {
  const slug = String(url.searchParams.get("slug") ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (!findContentDirSync(slug))
    return apiError(`Book not found: ${slug}`, 404);

  const script = join(
    getRepoRoot(),
    "scripts",
    "podcast",
    "publish_to_production.py",
  );
  const state = await new Promise<Record<string, unknown> | null>((resolve) => {
    const proc = spawn(getPythonBin(), [script, slug, "--state", "--json"], {
      cwd: getRepoRoot(),
    });
    let out = "";
    proc.stdout.on("data", (d) => (out += d));
    proc.on("error", () => resolve(null));
    proc.on("close", () => {
      const line = out
        .trim()
        .split("\n")
        .filter((l) => l.trim().startsWith("{"))
        .pop();
      try {
        resolve(line ? JSON.parse(line) : null);
      } catch {
        resolve(null);
      }
    });
  });

  // An unreadable state is reported as PENDING, never as up-to-date. The button
  // exists to stop a change being forgotten, so its failure direction is to ask
  // rather than to reassure.
  return apiOk(
    state ?? {
      pending: true,
      reason: "could not read this book's publish state",
    },
  );
};

export const POST: APIRoute = async ({ request }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return apiError("Invalid JSON body");
  }

  const slug = String(body.slug ?? "").trim();
  if (!SLUG_RE.test(slug)) return apiError("Invalid slug");
  if (!findContentDirSync(slug))
    return apiError(`Book not found: ${slug}`, 404);

  const script = join(
    getRepoRoot(),
    "scripts",
    "podcast",
    "publish_to_production.py",
  );
  const child = spawn(
    getPythonBin(),
    [script, slug, "--json", ...flagsFor(body)],
    { cwd: getRepoRoot() },
  );

  const encoder = new TextEncoder();
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      let closed = false;
      const send = (event: Record<string, unknown>) => {
        if (!closed)
          controller.enqueue(encoder.encode(JSON.stringify(event) + "\n"));
      };

      // stdout is already one NDJSON event per line, so it is forwarded as-is
      // rather than parsed and re-serialised — anything this route could not
      // parse would otherwise be silently dropped on its way to the panel.
      // A partial line is held until its newline arrives.
      let buffer = "";
      child.stdout.setEncoding("utf8");
      child.stdout.on("data", (chunk: string) => {
        buffer += chunk;
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          // A line that will not parse is FORWARDED AS TEXT, never dropped: it
          // is almost always a warning printed by a tool the driver called, and
          // swallowing it would hide the one thing explaining a failed check.
          try {
            send(JSON.parse(line));
          } catch {
            send({ event: "log", text: line.trim() });
          }
        }
      });

      // The driver writes its own errors as events; anything on stderr came from
      // Python itself (a traceback, an import failure) and is worth seeing.
      child.stderr.setEncoding("utf8");
      child.stderr.on("data", (chunk: string) => {
        const text = chunk.trim();
        if (text) send({ event: "log", text });
      });

      child.on("error", (error) => {
        send({ event: "error", text: `could not start: ${error.message}` });
        send({
          event: "done",
          verified: false,
          text: "the publish did not start",
        });
        closed = true;
        controller.close();
      });

      child.on("close", (code) => {
        if (buffer.trim()) {
          try {
            send(JSON.parse(buffer));
          } catch {
            send({ event: "log", text: buffer.trim() });
          }
        }
        // A non-zero exit with no `done` event means the driver died rather than
        // finished. Emitting one here is what stops the panel spinning forever.
        if (code !== 0) {
          send({
            event: "exit",
            code,
            text: `the publish exited with code ${code}`,
          });
        }
        closed = true;
        controller.close();
      });
    },
    cancel() {
      // The browser navigated away or the user closed the panel. Killing the
      // child is right: the alternative is a half-finished publish nobody is
      // watching, and every step of the driver is safe to run again.
      child.kill("SIGTERM");
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "content-type": "application/x-ndjson; charset=utf-8",
      "cache-control": "no-store",
      // Without this a proxy may buffer the whole response and deliver the
      // progress all at once at the end, which is the thing this route exists
      // to avoid.
      "x-accel-buffering": "no",
    },
  });
};
