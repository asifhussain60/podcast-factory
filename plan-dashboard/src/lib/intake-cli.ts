/**
 * intake-cli.ts — shell out to the pipeline's intake helper CLIs and return their
 * JSON. The Python modules are the SINGLE source of truth (dropdown vocabularies,
 * cost estimate); the Astro endpoints are thin pass-throughs so the UI can never
 * drift from what the pipeline accepts. Mirrors the proven build-bundle.ts spawn
 * pattern (spawn('/usr/bin/python3', …), capture stdout, parse JSON).
 */
import { join } from "node:path";
import { spawn } from "node:child_process";
import { getRepoRoot, getPythonBin } from "./content-paths";

/** Run `scripts/podcast/<module>.py <args…>` and parse its single JSON stdout line. */
export function runPythonJson(
  module: string,
  args: string[],
  /** Written to the child's stdin and closed. For passages too large or too
   *  punctuation-heavy to hand over as an argv string. */
  stdin?: string,
): Promise<unknown> {
  const script = join(getRepoRoot(), "scripts", "podcast", module);
  return new Promise((resolve, reject) => {
    const proc = spawn(getPythonBin(), [script, ...args], {
      cwd: getRepoRoot(),
    });
    if (stdin !== undefined) {
      proc.stdin.on("error", reject);
      proc.stdin.end(stdin, "utf-8");
    }
    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => (stdout += d));
    proc.stderr.on("data", (d) => (stderr += d));
    proc.on("error", reject);
    proc.on("close", (code) => {
      if (code !== 0) {
        reject(new Error(`${module} exited ${code}: ${stderr || stdout}`));
        return;
      }
      try {
        resolve(JSON.parse(stdout.trim()));
      } catch {
        reject(
          new Error(`${module}: non-JSON output: ${stdout.slice(0, 200)}`),
        );
      }
    });
  });
}

/**
 * Spawn a pipeline driver DETACHED so it survives the request (and the browser
 * closing) — the Q10 launch contract. stdio is ignored and the child is unref'd
 * so this returns immediately; the endpoint NEVER runs the orchestrator in-request.
 * Returns the child pid. This is a SPEND action — only ever called from the
 * confirm / approval endpoints, which are the Tier-2 gate.
 */
export function spawnDetachedPython(module: string, args: string[]): number {
  const script = join(getRepoRoot(), "scripts", "podcast", module);
  const proc = spawn(getPythonBin(), [script, ...args], {
    cwd: getRepoRoot(),
    detached: true,
    stdio: "ignore",
  });
  proc.unref();
  return proc.pid ?? -1;
}
