/**
 * The seam Python crosses to reach the Ismaili Scholar.
 *
 * `_scholar_bridge.py` shells out to gem-card.mjs and reads one JSON object off
 * stdout. Everything below is a fact that module depends on: the field names, the
 * shape of a failure, and the promise that no model is called. A change here that
 * these tests do not catch shows up as a chapter of dropped findings and a log
 * line nobody reads.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";

const BRIDGE = fileURLToPath(new URL("./gem-card.mjs", import.meta.url));

/** Spawn the bridge exactly as `_scholar_bridge.py` does: JSON in on stdin,
 *  one JSON object out on stdout. (`execFile` has no `input` option — passing
 *  one leaves stdin open and the child waits forever.) */
function bridge(command, payload) {
  return new Promise((resolve, reject) => {
    const child = spawn("node", [BRIDGE, command]);
    let stdout = "";
    child.stdout.on("data", (d) => (stdout += d));
    child.on("error", reject);
    child.on("close", (code) => {
      const last = stdout.trim().split("\n").at(-1) || "{}";
      try {
        resolve({ code, data: JSON.parse(last) });
      } catch {
        reject(new Error(`unparseable bridge reply: ${last.slice(0, 200)}`));
      }
    });
    child.stdin.end(JSON.stringify(payload));
  });
}

test("prepare returns everything Python needs and computes nothing twice", async () => {
  const { code, data } = await bridge("prepare", {
    concept: "whose witnesses are seven kingdoms",
    context: "The twelve constellations are given witnesses.",
    bookTitle: "The Master and the Disciple",
    question: "What are the seven kingdoms that witness the constellations?",
  });

  assert.equal(code, 0);
  assert.equal(data.ok, true);
  // The turn.
  assert.ok(data.system.length > 100, "the persona's system instruction");
  assert.ok(
    data.user.includes("What are the seven kingdoms"),
    "the question is asked",
  );
  // The two things Python would otherwise have had to reimplement.
  assert.equal(data.anchor, "whose witnesses are seven kingdoms");
  assert.ok(
    data.tightenSystem.includes("tightening"),
    "the second pass travels with the first",
  );
  assert.equal(typeof data.tightenMinChars, "number");
  // The grounding verdict, which is what decides whether a card is paid for.
  assert.equal(typeof data.grounded, "number");
  assert.equal(typeof data.morphology, "boolean");
});

test("prepare reports zero grounding rather than inventing some", async () => {
  const { data } = await bridge("prepare", {
    concept: "zzzqqq wwwvvv xxxyyy nnnmmm",
  });
  assert.equal(data.ok, true);
  assert.equal(data.grounded, 0);
  assert.equal(data.morphology, false);
});

test("parse reads the model's reply with the button's own parser", async () => {
  const raw = JSON.stringify({
    body: "The seven kingdoms are the governing spheres.",
    etymology: ["مُلْك: from the root م-ل-ك, to own or rule."],
  });
  const { code, data } = await bridge("parse", { raw });

  assert.equal(code, 0);
  assert.equal(data.ok, true);
  assert.equal(data.body, "The seven kingdoms are the governing spheres.");
  assert.equal(data.etymology.length, 1);
});

test("parse refuses a reply that is still a JSON envelope", async () => {
  // The regression that shipped a card beginning `{"body": "…` on
  // the-master-and-the-disciple, 2026-08-06. `toResult` cannot read a broken
  // envelope, so it hands the envelope back as the body — and the tightening
  // pass downstream will rewrite it into something that reads like prose. The
  // only place to stop it is here, before anything else touches it.
  const { code, data } = await bridge("parse", {
    raw: '{"body": "An explanation.", "etymology": []',
  });
  assert.notEqual(code, 0);
  assert.equal(data.ok, false);
  assert.match(data.error, /envelope/);
});

test("parse still accepts a reply that was never JSON at all", async () => {
  // The fallback is right for a plain-prose reply; only an unread ENVELOPE is
  // a failure. Narrowing this to "must be JSON" would drop good cards.
  const { data } = await bridge("parse", {
    raw: "The seven kingdoms are the governing spheres.",
  });
  assert.equal(data.ok, true);
  assert.equal(data.body, "The seven kingdoms are the governing spheres.");
});

test("finish resolves a citation, so the machine form never reaches a reader", async () => {
  const { data } = await bridge("finish", { body: "The verse is Q|18:65." });
  assert.ok(!data.body.includes("Q|18:65"));
  assert.ok(data.body.includes("Al-Kahf"));
});

test("a tightening that dropped an Arabic run is refused and the original stands", async () => {
  const body = `The term عِلْم runs through this passage. ${"Filler sentence here. ".repeat(20)}`;
  const { data } = await bridge("finish", {
    body,
    tightenedRaw: "The term runs through this passage.",
  });
  assert.equal(data.tightened, false, "the guards refused it");
  assert.ok(data.body.includes("عِلْم"), "the scholarship survived");
});

test("a tightening that kept everything is used", async () => {
  const body = `The term عِلْم runs through this passage. ${"Filler sentence here. ".repeat(20)}`;
  const tightenedRaw = "The term عِلْم runs through this passage.";
  const { data } = await bridge("finish", { body, tightenedRaw });
  assert.equal(data.tightened, true);
  assert.equal(data.body, tightenedRaw);
});

test("finish never sees a raw envelope — it takes prose the caller already read", async () => {
  // The ordering fix. `finish` has no `raw` field at all, so the tightener can
  // only ever have been given a parsed body.
  const { code, data } = await bridge("finish", {
    raw: JSON.stringify({ body: "x", etymology: [] }),
  });
  assert.notEqual(code, 0);
  assert.equal(data.ok, false);
});

test("a failure is a JSON object and a non-zero exit, never a stack trace", async () => {
  for (const [command, payload] of [
    ["prepare", {}],
    ["finish", {}],
    ["parse", {}],
    ["explain", {}],
  ]) {
    const { code, data } = await bridge(command, payload);
    assert.notEqual(code, 0, `${command} must fail loudly`);
    assert.equal(data.ok, false);
    assert.equal(typeof data.error, "string");
  }
});
