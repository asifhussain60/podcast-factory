/**
 * intake-cli.ts — shell out to the pipeline's intake helper CLIs and return their
 * JSON. The Python modules are the SINGLE source of truth (dropdown vocabularies,
 * cost estimate); the Astro endpoints are thin pass-throughs so the UI can never
 * drift from what the pipeline accepts. Mirrors the proven build-bundle.ts spawn
 * pattern (spawn('/usr/bin/python3', …), capture stdout, parse JSON).
 */
import { join } from 'node:path';
import { spawn } from 'node:child_process';
import { getRepoRoot } from './content-paths';

/** Run `scripts/podcast/<module>.py <args…>` and parse its single JSON stdout line. */
export function runPythonJson(module: string, args: string[]): Promise<unknown> {
  const script = join(getRepoRoot(), 'scripts', 'podcast', module);
  return new Promise((resolve, reject) => {
    const proc = spawn('/usr/bin/python3', [script, ...args], { cwd: getRepoRoot() });
    let stdout = '';
    let stderr = '';
    proc.stdout.on('data', (d) => (stdout += d));
    proc.stderr.on('data', (d) => (stderr += d));
    proc.on('error', reject);
    proc.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`${module} exited ${code}: ${stderr || stdout}`));
        return;
      }
      try {
        resolve(JSON.parse(stdout.trim()));
      } catch {
        reject(new Error(`${module}: non-JSON output: ${stdout.slice(0, 200)}`));
      }
    });
  });
}
