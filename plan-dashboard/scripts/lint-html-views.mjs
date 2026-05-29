#!/usr/bin/env node
// lint-html-views.mjs — deterministic conformance gate for the Cortex HTML View
// Quality Standard (WC7c). Turns the standard's §11 mechanical checks into a real
// linter so MUST violations cannot be silently committed. Rule text lives in
// docs/standards/html-view-quality.md; the one-line digest in
// docs/standards/html-view-quality-digest.md. Cite findings by REQ-NNN.
//
// Severity model (config-driven, see html-view-lint.config.json):
//   error  -> non-zero exit (blocks commit / build) UNLESS --warn-only
//   warn   -> reported, never blocks
// Flags:
//   --warn-only   demote everything to warn, always exit 0 (the "ship-soft" mode)
//   --strict      promote every warn to error (the "fully green" target mode)
//   --json        machine-readable output
//   --files a,b   limit the scan to an explicit comma list (used by the pre-commit hook)
//
// Suppression:
//   - per-file rule exemptions live in config.allow { "<relpath>": ["RULE — reason"] }
//   - inline: a line containing `html-view-lint-disable-line` skips that line;
//     a file containing `html-view-lint-disable-file` skips the whole file.

import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join, relative, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');                 // plan-dashboard/
const CONFIG_PATH = join(ROOT, 'html-view-lint.config.json');

const argv = process.argv.slice(2);
const has = (f) => argv.includes(f);
const WARN_ONLY = has('--warn-only');
const STRICT = has('--strict');
const JSON_OUT = has('--json');
const filesArg = (() => {
  const i = argv.indexOf('--files');
  return i >= 0 && argv[i + 1] ? argv[i + 1].split(',').map((s) => s.trim()).filter(Boolean) : null;
})();

const config = JSON.parse(readFileSync(CONFIG_PATH, 'utf8'));

// ---- file collection ------------------------------------------------------
function walk(dir, acc = []) {
  if (!existsSync(dir)) return acc;
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, acc);
    else acc.push(p);
  }
  return acc;
}
const startsWithAny = (rel, prefixes) => prefixes.some((p) => rel === p || rel.startsWith(p));

function classify(rel) {
  if (startsWithAny(rel, config.exclude_paths)) return null;            // excluded by design
  const isCode = rel.endsWith('.astro') || rel.endsWith('.tsx');
  const isCss = rel.endsWith('.css');
  if (isCss) return startsWithAny(rel, config.css_paths) ? 'css' : null;
  if (!isCode) return null;
  if (startsWithAny(rel, config.blocking_exclude_subpaths)) return 'warn-code';
  if (startsWithAny(rel, config.blocking_paths)) return 'blocking-code';
  if (startsWithAny(rel, config.warn_paths)) return 'warn-code';
  return null;
}

let candidates = walk(join(ROOT, 'src')).map((p) => relative(ROOT, p));
if (filesArg) {
  const want = new Set(filesArg.map((f) => f.replace(/^plan-dashboard\//, '')));
  candidates = candidates.filter((rel) => want.has(rel));
}

// ---- checks ---------------------------------------------------------------
// Each check: { id, REQ, baseSeverity, scope: 'code'|'css', test(line)->bool|matchInfo }
// baseSeverity is the severity when the file is a *blocking* file; warn-scope files
// always report at 'warn' regardless. The four blocking checks below are the subset
// confirmed green repo-wide on 2026-05-29 (zero false positives).
const LINE_CHECKS = [
  { id: 'INLINE-STYLE',   REQ: 'D-DoD',   blocking: true,  scope: 'code',
    re: /\bstyle\s*=\s*["'{]/, msg: 'inline style= attribute (use external CSS)' },
  { id: 'EXTERNAL-SVG',   REQ: 'REQ-021', blocking: true,  scope: 'code',
    re: /<(img[^>]+\.svg|object[^>]+\.svg|embed[^>]+\.svg)/i, msg: 'external SVG reference (inline the <svg>)' },
  { id: 'SVG-WH-ATTR',    REQ: 'REQ-024', blocking: true,  scope: 'code',
    re: /<svg\b[^>]*\s(width|height)\s*=/i, msg: 'width/height attr on <svg> (use viewBox only)' },
];

// Astro/JSX scoped <style> blocks compile to scoped EXTERNAL CSS at build, so a small
// one is idiomatic, not the runtime inline styling the DoD targets (Asif, 2026-05-29).
// We accept scoped blocks and flag only OVERSIZED ones — a block bigger than the
// threshold is a page-stylesheet inlined into the component and belongs in src/styles/
// (the WC6 case). Threshold: config.style_block_max_lines (default 50).
function scanStyleBlocks(src, maxLines) {
  const out = [];
  const re = /<style[^>]*>([\s\S]*?)<\/style>/g;
  let m;
  while ((m = re.exec(src))) {
    const bodyLines = m[1].split('\n').filter((l) => l.trim()).length;
    if (bodyLines > maxLines) {
      const line = src.slice(0, m.index).split('\n').length;
      out.push({ line, bodyLines });
    }
  }
  return out;
}

// CSS height-clamp is selector-aware: REQ-002 forbids clamps ONLY on the page-growth
// landmarks, never on cards/badges/progress-bars (where overflow:hidden is legitimate).
// We track the current rule's selector and flag a clamp only when that selector targets
// html / body / main / .container / a bare top-level `section`.
const FORBIDDEN_SELECTOR = /(^|[\s,>+~])(html|body|main|section(\[[^\]]*\])?)([\s,>+~{:]|$)|(^|[\s,>+~])\.container([\s,>+~{:]|$)/i;
const CLAMP_PROP = /(max-height\s*:|height\s*:\s*100vh|overflow\s*:\s*(hidden|scroll)\b)/i;

function scanCss(rel, src) {
  const out = [];
  // Strip comments so a `/* overflow: hidden */` note doesn't trip the check.
  const noComments = src.replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, ' '));
  const lines = noComments.split('\n');
  let selector = '';
  let buf = '';
  lines.forEach((line, i) => {
    if (line.includes('html-view-lint-disable-line')) return;
    for (const ch of line) {
      if (ch === '{') { selector = buf.trim(); buf = ''; }
      else if (ch === '}') { selector = ''; buf = ''; }
      else buf += ch;
    }
    // Inside a block whose selector is a forbidden landmark?
    if (selector && FORBIDDEN_SELECTOR.test(selector) && CLAMP_PROP.test(line)) {
      out.push({ line: i + 1, selector: selector.slice(0, 60), src: line.trim().slice(0, 120) });
    }
  });
  return out;
}

// Whole-file checks (presence-based).
const FILE_CHECKS = [
  { id: 'LANG-ATTR', REQ: 'REQ-072', blocking: true, appliesTo: (rel) => rel.startsWith('src/layouts/'),
    ok: (src) => /<html\b[^>]*\blang=/.test(src), msg: 'layout missing <html lang>' },
  { id: 'SKIP-LINK', REQ: 'REQ-071', blocking: false, appliesTo: (rel) => rel.startsWith('src/layouts/'),
    ok: (src) => /skip-link/.test(src), msg: 'layout missing skip-to-content link' },
  { id: 'SVG-A11Y-TRIPLE', REQ: 'REQ-022', blocking: false, appliesTo: (rel) => rel.endsWith('.astro') || rel.endsWith('.tsx'),
    ok: (src) => {
      const svgs = (src.match(/<svg\b/gi) || []).length;
      const roles = (src.match(/role\s*=\s*["']img["']/gi) || []).length;
      const labelled = (src.match(/aria-labelledby\s*=/gi) || []).length;
      return svgs === 0 || (roles >= svgs && labelled >= svgs);
    }, msg: 'inline <svg> missing accessibility triple (role=img + aria-labelledby + <title>/<desc>)' },
];

// ---- run ------------------------------------------------------------------
const findings = [];
const allow = config.allow || {};
function suppressed(rel, ruleId) {
  const list = allow[rel];
  return Array.isArray(list) && list.some((e) => e.split(/[\s—:-]/)[0] === ruleId || e.startsWith(ruleId));
}

for (const rel of candidates) {
  const kind = classify(rel);
  if (!kind) continue;
  const abs = join(ROOT, rel);
  let src;
  try { src = readFileSync(abs, 'utf8'); } catch { continue; }
  if (src.includes('html-view-lint-disable-file')) continue;
  const isBlockingFile = kind === 'blocking-code';

  if (kind === 'css') {
    if (!suppressed(rel, 'HEIGHT-CLAMP')) {
      for (const hit of scanCss(rel, src)) {
        findings.push({ rel, line: hit.line, id: 'HEIGHT-CLAMP', REQ: 'REQ-002',
          sev: resolveSeverity(false), msg: `height/overflow clamp on landmark selector "${hit.selector}"`, src: hit.src });
      }
    }
    continue;
  }

  if (!suppressed(rel, 'INLINE-STYLE-BLOCK')) {
    const maxLines = config.style_block_max_lines ?? 50;
    for (const hit of scanStyleBlocks(src, maxLines)) {
      findings.push({ rel, line: hit.line, id: 'INLINE-STYLE-BLOCK', REQ: 'D-DoD',
        sev: resolveSeverity(false),
        msg: `oversized <style> block (${hit.bodyLines} lines > ${maxLines}) — move to src/styles/*.css`, src: '' });
    }
  }

  const lines = src.split('\n');
  for (const chk of LINE_CHECKS) {
    if (chk.scope === 'css') continue;
    if (suppressed(rel, chk.id)) continue;
    lines.forEach((line, i) => {
      if (line.includes('html-view-lint-disable-line')) return;
      if (chk.re.test(line)) {
        const sev = resolveSeverity(chk.blocking && isBlockingFile);
        findings.push({ rel, line: i + 1, id: chk.id, REQ: chk.REQ, sev, msg: chk.msg, src: line.trim().slice(0, 120) });
      }
    });
  }
  for (const chk of FILE_CHECKS) {
    if (!chk.appliesTo(rel)) continue;
    if (suppressed(rel, chk.id)) continue;
    if (!chk.ok(src)) {
      const sev = resolveSeverity(chk.blocking);
      findings.push({ rel, line: 0, id: chk.id, REQ: chk.REQ, sev, msg: chk.msg, src: '' });
    }
  }
}

function resolveSeverity(isErrorByDefault) {
  if (WARN_ONLY) return 'warn';
  if (STRICT) return 'error';
  return isErrorByDefault ? 'error' : 'warn';
}

// ---- report ---------------------------------------------------------------
const errors = findings.filter((f) => f.sev === 'error');
const warns = findings.filter((f) => f.sev === 'warn');

if (JSON_OUT) {
  console.log(JSON.stringify({ errors, warns, total: findings.length }, null, 2));
} else {
  const fmt = (f) => `  ${f.sev === 'error' ? '✖' : '⚠'} ${f.rel}${f.line ? ':' + f.line : ''}  [${f.id} · ${f.REQ}] ${f.msg}${f.src ? '\n      ' + f.src : ''}`;
  if (!findings.length) {
    console.log('html-view-lint: clean — no findings.');
  } else {
    if (errors.length) { console.log(`\nhtml-view-lint: ${errors.length} BLOCKING violation(s):`); errors.forEach((f) => console.log(fmt(f))); }
    if (warns.length) { console.log(`\nhtml-view-lint: ${warns.length} warning(s) (non-blocking; clean these to reach --strict):`); warns.forEach((f) => console.log(fmt(f))); }
  }
  console.log(`\nMode: ${WARN_ONLY ? 'warn-only' : STRICT ? 'strict' : 'default'} · errors=${errors.length} warns=${warns.length}`);
}

process.exit(errors.length && !WARN_ONLY ? 1 : 0);
