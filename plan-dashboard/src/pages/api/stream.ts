import type { APIRoute } from 'astro';
import { watch, statSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

export const prerender = false;

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.resolve(HERE, '../../data');
const SENTINEL = path.resolve(HERE, '../../../.snapshot-version');

const SNAPSHOTS = [
  path.join(DATA_DIR, 'architecture-snapshot.json'),
  path.join(DATA_DIR, 'infrastructure-snapshot.json'),
  path.join(DATA_DIR, 'dashboard-snapshot.json'),
];

function readDashboardMeta() {
  try {
    const raw = readFileSync(path.join(DATA_DIR, 'dashboard-snapshot.json'), 'utf-8');
    const parsed = JSON.parse(raw);
    return { generated_at: parsed.generated_at, source_commit: parsed.source_commit };
  } catch {
    return { generated_at: new Date().toISOString(), source_commit: 'unknown' };
  }
}

export const GET: APIRoute = async () => {
  const stream = new ReadableStream({
    start(controller) {
      const enc = new TextEncoder();
      const push = (event: string, data: unknown) => {
        controller.enqueue(enc.encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`));
      };

      push('hello', { ok: true, at: new Date().toISOString() });
      push('snapshot', readDashboardMeta());

      const watchers = SNAPSHOTS.map((p) => {
        try {
          return watch(p, { persistent: false }, () => {
            try {
              statSync(p);
              push('snapshot', readDashboardMeta());
            } catch { /* file rotated, ignore */ }
          });
        } catch { return null; }
      }).filter(Boolean) as ReturnType<typeof watch>[];

      let sentinelWatcher: ReturnType<typeof watch> | null = null;
      try {
        sentinelWatcher = watch(SENTINEL, { persistent: false }, () => {
          push('snapshot', readDashboardMeta());
        });
      } catch { /* sentinel may not exist yet — that's fine */ }

      const heartbeat = setInterval(() => {
        try { controller.enqueue(enc.encode(`: keepalive\n\n`)); } catch { /* closed */ }
      }, 25_000);

      const cleanup = () => {
        clearInterval(heartbeat);
        watchers.forEach((w) => { try { w.close(); } catch {} });
        if (sentinelWatcher) { try { sentinelWatcher.close(); } catch {} }
        try { controller.close(); } catch {}
      };

      (controller as any).__cleanup = cleanup;
    },
    cancel() {
      const cb = (this as any).__cleanup;
      if (typeof cb === 'function') cb();
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
};
