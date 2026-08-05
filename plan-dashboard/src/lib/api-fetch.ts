/**
 * api-fetch.ts — the one shared HTTP client for the site's own API routes (R1).
 *
 * Every browser-side call to /api/* goes through apiFetch<T>() so path/query
 * building, JSON body handling, error surfacing, and envelope unwrapping live
 * in ONE place (previously: 87 hand-rolled fetch() calls with divergent error
 * handling). Server routes emit the api-responses.ts envelope
 * ({ok:true,data}|{ok:false,error}); this client UNWRAPS it — and, during the
 * migration window, transparently accepts legacy raw-JSON routes too, so a
 * route can adopt the envelope without breaking already-migrated callers.
 *
 * Error contract: apiFetch THROWS ApiFetchError on transport failure, non-2xx
 * status, or an {ok:false} envelope. Call sites that historically ignored
 * failures keep their own try/catch — the migration preserves each site's
 * observable behavior, it only centralizes the mechanics.
 *
 * Timeout: opt-in via timeoutMs (AbortController, mirroring
 * localServerClient.ts). No default timeout — long-running AI actions
 * (ask/rewrite/denoise) legitimately take minutes.
 */

export class ApiFetchError extends Error {
  /** HTTP status; 0 for transport/abort failures. */
  status: number;

  constructor(message: string, status: number, options?: ErrorOptions) {
    super(message, options);
    this.name = "ApiFetchError";
    this.status = status;
  }
}

export interface ApiFetchOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  /** Query parameters; null/undefined values are dropped. */
  query?: Record<string, string | number | boolean | null | undefined>;
  /** JSON body (stringified + content-type set automatically). */
  body?: unknown;
  /** Abort the request after this many ms (no default — see header note). */
  timeoutMs?: number;
  /** Extra headers (merged after the JSON defaults). */
  headers?: Record<string, string>;
  /** External AbortSignal (composed with the timeout when both given). */
  signal?: AbortSignal;
}

function buildUrl(path: string, query?: ApiFetchOptions["query"]): string {
  if (!query) return path;
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query)) {
    if (v === null || v === undefined) continue;
    params.set(k, String(v));
  }
  const qs = params.toString();
  return qs ? `${path}${path.includes("?") ? "&" : "?"}${qs}` : path;
}

/** True for the api-responses.ts envelope shape. */
function isEnvelope(
  x: unknown,
): x is { ok: boolean; data?: unknown; error?: unknown } {
  return (
    typeof x === "object" &&
    x !== null &&
    "ok" in x &&
    typeof (x as { ok: unknown }).ok === "boolean" &&
    ((x as { ok: boolean }).ok ? "data" in x : "error" in x)
  );
}

/**
 * Fetch a site API route, returning the (envelope-unwrapped) JSON payload.
 * Throws ApiFetchError on transport error, non-2xx, or {ok:false}.
 */
export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const { method = "GET", query, body, timeoutMs, headers, signal } = options;

  const ctrl = timeoutMs ? new AbortController() : null;
  const timer = ctrl ? setTimeout(() => ctrl.abort(), timeoutMs) : null;
  if (ctrl && signal) {
    if (signal.aborted) ctrl.abort();
    else signal.addEventListener("abort", () => ctrl.abort(), { once: true });
  }

  let res: Response;
  try {
    res = await fetch(buildUrl(path, query), {
      method,
      headers: {
        ...(body !== undefined ? { "content-type": "application/json" } : {}),
        ...headers,
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: ctrl ? ctrl.signal : signal,
    });
  } catch (e) {
    throw new ApiFetchError(`${method} ${path}: ${(e as Error).message}`, 0, {
      cause: e,
    });
  } finally {
    if (timer) clearTimeout(timer);
  }

  // Parse JSON even on error statuses — error envelopes carry the message.
  let parsed: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = null; // non-JSON body; fall through to status-based error
    }
  }

  if (isEnvelope(parsed)) {
    if (!parsed.ok) {
      throw new ApiFetchError(
        String(parsed.error ?? `HTTP ${res.status}`),
        res.status,
      );
    }
    if (!res.ok) {
      // Defensive: {ok:true} with an error status — trust the status.
      throw new ApiFetchError(
        `${method} ${path}: HTTP ${res.status}`,
        res.status,
      );
    }
    return parsed.data as T;
  }

  if (!res.ok) {
    throw new ApiFetchError(
      `${method} ${path}: HTTP ${res.status} ${res.statusText}`,
      res.status,
    );
  }
  return parsed as T;
}
