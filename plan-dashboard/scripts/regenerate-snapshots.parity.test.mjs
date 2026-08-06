/**
 * The two snapshot generators must emit byte-identical files.
 *
 * `npm run snapshot` is `node regenerate-snapshots.mjs || python3 regenerate-snapshots.py`
 * — the Python side is the fallback when Node fails, so whichever one runs decides
 * what lands in git. Both files say so in comments ("MIRROR: …", "both regenerators
 * must emit byte-identical snapshots") and until 2026-08-06 nothing checked it.
 *
 * It had already drifted. `book_kind` read a book's `series-config.yaml`, one of
 * which declared the same key twice: PyYAML takes the last value, js-yaml refuses
 * the file, so the two generators disagreed about that book — silently, and only in
 * whichever field the losing parser fell back on. This test is what turns that class
 * of divergence into a failure instead of a diff nobody reads.
 *
 * WHY THIS EXISTS BESIDE `tests/test_snapshot_regenerator_parity.py`
 * ------------------------------------------------------------------
 * That suite is the older and broader one, and it is NOT this. It reads the two
 * generators' SOURCE TEXT and asserts the five specific ways they drifted before
 * (ensure_ascii, wall-clock timestamps, the generator field, wave ordering, SHA
 * typing), plus properties of the committed JSON. Every one of those checks can
 * pass on a pair of generators that produce different files, because none of them
 * runs either generator.
 *
 * That is precisely how the 2026-08-06 divergence hid: it was data-dependent, not
 * textual. Both generators asked js-yaml/PyYAML to read a book's config, the two
 * parsers disagreed about a duplicated key, and no amount of reading the generator
 * source could show it. This test closes that by DIFFERENTIAL EXECUTION — run both,
 * compare the bytes — which is the only check that fails for a reason neither
 * generator's source reveals. Keep both: source assertions catch a drift before it
 * can produce output, this catches drift that only appears once it does.
 *
 * It runs each generator for real, against the real repo, because the divergence
 * lived in the content the generators read and a fixture would not have contained it.
 * The tracked JSONs are restored in a `finally` whatever happens.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPTS = path.dirname(fileURLToPath(import.meta.url));
const DATA = path.join(SCRIPTS, "..", "src", "data");

// Every file the generators write. Saved and restored together: a half-restored
// set is worse than either generator's output.
const SNAPSHOTS = [
  "dashboard-snapshot.json",
  "architecture-snapshot.json",
  "infrastructure-snapshot.json",
].map((f) => path.join(DATA, f));

function readAll() {
  return SNAPSHOTS.map((p) =>
    existsSync(p) ? readFileSync(p, "utf-8") : null,
  );
}

function writeAll(saved) {
  saved.forEach((content, i) => {
    if (content !== null) writeFileSync(SNAPSHOTS[i], content, "utf-8");
  });
}

function pythonAvailable() {
  try {
    execFileSync("python3", ["-c", "import yaml"], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

test("both snapshot generators emit byte-identical files", (t) => {
  if (!pythonAvailable()) {
    // The Python path needs only PyYAML. Where it is absent the fallback cannot
    // run at all, so there is no second output to disagree with.
    t.skip(
      "python3 with PyYAML not available — no fallback generator to compare",
    );
    return;
  }

  const saved = readAll();
  try {
    execFileSync("node", [path.join(SCRIPTS, "regenerate-snapshots.mjs")], {
      stdio: "ignore",
    });
    const fromNode = readAll();

    writeAll(saved);
    execFileSync("python3", [path.join(SCRIPTS, "regenerate-snapshots.py")], {
      stdio: "ignore",
    });
    const fromPython = readAll();

    SNAPSHOTS.forEach((p, i) => {
      assert.equal(
        fromPython[i],
        fromNode[i],
        `${path.basename(p)} differs between regenerate-snapshots.mjs and ` +
          `regenerate-snapshots.py. Whichever generator runs is an accident of ` +
          `whether node succeeded, so the two must agree exactly.`,
      );
    });
  } finally {
    writeAll(saved);
  }
});
