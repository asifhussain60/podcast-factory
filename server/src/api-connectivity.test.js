// api-connectivity.test.js — Babu Journal proxy API connectivity test suite.
//
// Verifies every external dependency the server relies on:
//   1. Key resolution   — Keychain or ANTHROPIC_API_KEY env var yields a valid key
//   2. Anthropic live   — SDK client can reach api.anthropic.com and authenticate
//   3. /health endpoint — server is up and reporting key source correctly
//   4. CF JWKS          — Cloudflare Access JWKS URL is reachable (conditional)
//
// Running modes:
//   npm run test:connectivity          — full live suite (server must be running)
//   SKIP_LIVE=1 npm run test:connectivity — skips Anthropic + endpoint probes (offline/CI)
//
// The test file is self-contained and adds zero npm dependencies.
// It uses Node's built-in test runner (node:test), available since Node 18.

import { describe, it, before } from "node:test";
import assert from "node:assert/strict";
import Anthropic from "@anthropic-ai/sdk";
import { loadAnthropicKey } from "./lib/keychain.js";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const SKIP_LIVE = process.env.SKIP_LIVE === "1";
const PORT = Number(process.env.PORT ?? 3001);
const BASE_URL = `http://127.0.0.1:${PORT}`;
const CF_TEAM = process.env.CF_ACCESS_TEAM_DOMAIN ?? "";
const ANTHROPIC_MODEL = process.env.ANTHROPIC_MODEL ?? "claude-sonnet-4-6";

// ---------------------------------------------------------------------------
// Helper: fetch with a short timeout so failures are fast
// ---------------------------------------------------------------------------
async function timedFetch(url, options = {}, timeoutMs = 5000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

// ---------------------------------------------------------------------------
// 1. Key Resolution
// ---------------------------------------------------------------------------
describe("1. Key resolution", () => {
  it("loadAnthropicKey() returns a key starting with sk-ant-", () => {
    let result;
    try {
      result = loadAnthropicKey();
    } catch (err) {
      assert.fail(
        `loadAnthropicKey() threw — no key available.\n` +
        `  Add to Keychain: security add-generic-password -s anthropic-api-key -a "$USER" -w 'sk-ant-...'\n` +
        `  Or set env:      export ANTHROPIC_API_KEY=sk-ant-...\n` +
        `  Original error:  ${err.message}`
      );
    }
    assert.ok(
      typeof result.key === "string" && result.key.startsWith("sk-ant-"),
      `Expected key starting with "sk-ant-", got: ${result.key?.slice(0, 12)}...`
    );
    assert.ok(
      result.source === "keychain" || result.source === "env",
      `Expected source to be "keychain" or "env", got: ${result.source}`
    );
    console.log(`    ✓ key resolved from: ${result.source}`);
  });
});

// ---------------------------------------------------------------------------
// 2. Anthropic Live Probe
// ---------------------------------------------------------------------------
describe("2. Anthropic API connectivity", () => {
  let anthropic;

  before(() => {
    if (SKIP_LIVE) return;
    const { key } = loadAnthropicKey();
    anthropic = new Anthropic({ apiKey: key });
  });

  it("sends a 1-token message and receives a valid response", { skip: SKIP_LIVE ? "SKIP_LIVE=1" : false }, async () => {
    let msg;
    try {
      msg = await anthropic.messages.create({
        model: ANTHROPIC_MODEL,
        max_tokens: 1,
        messages: [{ role: "user", content: "Reply with the single word: ok" }],
      });
    } catch (err) {
      assert.fail(
        `Anthropic API call failed.\n` +
        `  Check: API key validity, network access to api.anthropic.com\n` +
        `  Error: ${err.message}`
      );
    }

    assert.ok(msg.id, "Response should have an id");
    assert.ok(
      ["end_turn", "max_tokens"].includes(msg.stop_reason),
      `Unexpected stop_reason: ${msg.stop_reason}`
    );
    assert.ok(msg.model, "Response should include model name");
    assert.ok(msg.usage?.input_tokens > 0, "Should report input token usage");
    console.log(`    ✓ model: ${msg.model}  stop: ${msg.stop_reason}  tokens in/out: ${msg.usage.input_tokens}/${msg.usage.output_tokens}`);
  });
});

// ---------------------------------------------------------------------------
// 3. /health Endpoint
// ---------------------------------------------------------------------------
describe("3. /health endpoint", () => {
  it("returns ok:true with keySource and model", { skip: SKIP_LIVE ? "SKIP_LIVE=1" : false }, async () => {
    let res;
    try {
      res = await timedFetch(`${BASE_URL}/health`);
    } catch (err) {
      if (err.name === "AbortError" || err.code === "ECONNREFUSED") {
        assert.fail(
          `Cannot reach server at ${BASE_URL}.\n` +
          `  Start the server first:  cd server && npm run dev\n` +
          `  Or skip endpoint tests:  SKIP_LIVE=1 npm run test:connectivity`
        );
      }
      throw err;
    }

    assert.equal(res.status, 200, `Expected HTTP 200, got ${res.status}`);
    const body = await res.json();
    assert.equal(body.ok, true, `Expected ok:true, got: ${JSON.stringify(body)}`);
    assert.ok(body.keySource, `Expected keySource field in response`);
    assert.ok(body.model, `Expected model field in response`);
    console.log(`    ✓ server healthy  keySource=${body.keySource}  model=${body.model}`);
  });

  it("returns 200 on repeated calls (stable, not one-shot)", { skip: SKIP_LIVE ? "SKIP_LIVE=1" : false }, async () => {
    const results = await Promise.all(
      [1, 2, 3].map(() => timedFetch(`${BASE_URL}/health`).then((r) => r.status))
    );
    assert.deepEqual(results, [200, 200, 200], `Expected three 200s, got: ${results}`);
    console.log(`    ✓ 3 consecutive health checks all returned 200`);
  });
});

// ---------------------------------------------------------------------------
// 4. Cloudflare JWKS Reachability (conditional)
// ---------------------------------------------------------------------------
describe("4. Cloudflare Access JWKS", () => {
  const shouldSkip = SKIP_LIVE
    ? "SKIP_LIVE=1"
    : !CF_TEAM
    ? "CF_ACCESS_TEAM_DOMAIN not set — Cloudflare Access not configured"
    : false;

  it("JWKS URL returns HTTP 200 with a keys array", { skip: shouldSkip }, async () => {
    const jwksUrl = `https://${CF_TEAM}/cdn-cgi/access/certs`;
    let res;
    try {
      res = await timedFetch(jwksUrl, {}, 8000);
    } catch (err) {
      assert.fail(
        `Cannot reach Cloudflare JWKS at ${jwksUrl}.\n` +
        `  Check: CF_ACCESS_TEAM_DOMAIN is correct, internet is available\n` +
        `  Error: ${err.message}`
      );
    }

    assert.equal(res.status, 200, `Expected HTTP 200 from JWKS endpoint, got ${res.status}`);
    const body = await res.json();
    assert.ok(Array.isArray(body.keys), `Expected keys array in JWKS response`);
    assert.ok(body.keys.length > 0, `Expected at least one key in JWKS`);
    console.log(`    ✓ JWKS at ${jwksUrl}  keys: ${body.keys.length}`);
  });
});
