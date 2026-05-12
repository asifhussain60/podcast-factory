// claude-client.js — thin browser client for the Babu Journal local proxy.
// Exposes window.BabuAI with promise-returning methods.
// Uses fetch only; no dependencies; safe to load before or after React.

(function () {
  // Env-aware API base. Localhost uses the dev proxy directly; every deployed
  // host (Cloudflare Pages production + preview) funnels through the single
  // Mac-hosted tunnel at journal-api.kashkole.com. Override via
  // window.BABU_AI_PROXY_URL before this script loads if you need to point at
  // something custom (e.g. a second machine's tunnel).
  function defaultApiBase() {
    if (typeof window === "undefined") return "http://localhost:3001";
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1" || host === "") {
      return "http://localhost:3001";
    }
    // Production: use same-origin relative paths. The Cloudflare Worker
    // at journal.kashkole.com proxies /api/* to journal-api.kashkole.com,
    // eliminating cross-origin preflight issues entirely.
    return "";
  }

  const BASE = (window.BABU_AI_PROXY_URL || defaultApiBase()).replace(/\/+$/, "");

  // Default fetch timeouts. Model-backed endpoints can genuinely take 30s+,
  // so we split into two classes. Callers can override via opts.timeoutMs.
  const DEFAULT_TIMEOUT_MS = 15000;
  const MODEL_TIMEOUT_MS = 60000;
  const MODEL_PATHS = [
    "/api/refine", "/api/chat", "/api/voice-test",
    "/api/theme-swatches", "/api/theme-review",
  ];

  function pickTimeout(path, override) {
    if (Number.isFinite(override) && override > 0) return override;
    return MODEL_PATHS.some((p) => path.startsWith(p)) ? MODEL_TIMEOUT_MS : DEFAULT_TIMEOUT_MS;
  }

  async function getJSON(path, init = {}) {
    // credentials:include lets the Cloudflare Access auth cookie ride along
    // cross-origin from journal(.dev)?.kashkole.com to journal-api.kashkole.com.
    // Safe on localhost — ignored when there's no cookie to send.
    const { timeoutMs, signal: callerSignal, ...rest } = init;
    const timeout = pickTimeout(path, timeoutMs);
    const ctl = new AbortController();
    const timer = setTimeout(() => ctl.abort(new Error(`request timed out after ${timeout}ms`)), timeout);
    if (callerSignal) {
      if (callerSignal.aborted) ctl.abort(callerSignal.reason);
      else callerSignal.addEventListener("abort", () => ctl.abort(callerSignal.reason), { once: true });
    }

    let r;
    try {
      r = await fetch(BASE + path, { credentials: "include", signal: ctl.signal, ...rest });
    } catch (err) {
      clearTimeout(timer);
      if (err?.name === "AbortError") {
        const e = new Error(callerSignal?.aborted ? "request cancelled" : `request timed out after ${timeout}ms`);
        e.code = callerSignal?.aborted ? "cancelled" : "timeout";
        throw e;
      }
      const e = new Error(err?.message || "network error");
      e.code = "network";
      throw e;
    }
    clearTimeout(timer);

    const body = await r.json().catch(() => ({ ok: false, error: "non-JSON response" }));
    if (!r.ok || body.ok === false || (body.ok && body.error)) {
      const msg = body.error || `HTTP ${r.status}`;
      const err = new Error(msg);
      err.status = r.status;
      err.body = body;
      throw err;
    }
    return body;
  }

  window.BabuAI = {
    baseUrl: BASE,

    async request(path, init = {}) {
      return getJSON(path, init);
    },

    async health() {
      return getJSON("/health");
    },

    async voiceTest() {
      return getJSON("/api/voice-test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
    },

    async refine(rawText, opts = {}) {
      if (!rawText || !rawText.trim()) throw new Error("refine: rawText is required");
      return getJSON("/api/refine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: rawText, ...opts }),
      });
    },

    async chat(payload) {
      return getJSON("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    },

    async referenceData(name) {
      if (!name || !/^[a-z][a-z0-9-]*$/.test(name)) throw new Error("referenceData: invalid name");
      return getJSON(`/api/reference-data/${name}`);
    },
  };
})();
