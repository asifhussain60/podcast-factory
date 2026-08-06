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

import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, relative, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, ".."); // plan-dashboard/
const CONFIG_PATH = join(ROOT, "html-view-lint.config.json");

const argv = process.argv.slice(2);
const has = (f) => argv.includes(f);
const WARN_ONLY = has("--warn-only");
const STRICT = has("--strict");
const JSON_OUT = has("--json");
const filesArg = (() => {
  const i = argv.indexOf("--files");
  return i >= 0 && argv[i + 1]
    ? argv[i + 1]
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    : null;
})();

const config = JSON.parse(readFileSync(CONFIG_PATH, "utf8"));

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
const startsWithAny = (rel, prefixes) =>
  prefixes.some((p) => rel === p || rel.startsWith(p));

function classify(rel) {
  if (startsWithAny(rel, config.exclude_paths)) return null; // excluded by design
  const isCode = rel.endsWith(".astro") || rel.endsWith(".tsx");
  const isCss = rel.endsWith(".css");
  if (isCss) return startsWithAny(rel, config.css_paths) ? "css" : null;
  if (!isCode) return null;
  if (startsWithAny(rel, config.blocking_exclude_subpaths)) return "warn-code";
  if (startsWithAny(rel, config.blocking_paths)) return "blocking-code";
  if (startsWithAny(rel, config.warn_paths)) return "warn-code";
  return null;
}

// Walk every configured root, not just src/. `packages/` was added 2026-07-26
// with the prose-editor workspace: a toolbar component is exactly the shape that
// trips REQ-049 (real <button>, never <div onclick>) and the zero-inline-styling
// DoD, so a package living beside src/ must not be held to a laxer standard than
// the code it replaces. Roots are config-driven so adding the next one is data.
const WALK_ROOTS = config.walk_roots ?? ["src"];
let candidates = WALK_ROOTS.flatMap((root) => walk(join(ROOT, root))).map((p) =>
  relative(ROOT, p),
);
if (filesArg) {
  const want = new Set(filesArg.map((f) => f.replace(/^plan-dashboard\//, "")));
  candidates = candidates.filter((rel) => want.has(rel));
}

// ---- checks ---------------------------------------------------------------
// Each check: { id, REQ, baseSeverity, scope: 'code'|'css', test(line)->bool|matchInfo }
// baseSeverity is the severity when the file is a *blocking* file; warn-scope files
// always report at 'warn' regardless. The four blocking checks below are the subset
// confirmed green repo-wide on 2026-05-29 (zero false positives).
const LINE_CHECKS = [
  {
    id: "INLINE-STYLE",
    REQ: "D-DoD",
    blocking: true,
    scope: "code",
    re: /\bstyle\s*=\s*["'{]/,
    msg: "inline style= attribute (use external CSS)",
  },
  {
    id: "EXTERNAL-SVG",
    REQ: "REQ-021",
    blocking: true,
    scope: "code",
    re: /<(img[^>]+\.svg|object[^>]+\.svg|embed[^>]+\.svg)/i,
    msg: "external SVG reference (inline the <svg>)",
  },
  {
    id: "SVG-WH-ATTR",
    REQ: "REQ-024",
    blocking: true,
    scope: "code",
    re: /<svg\b[^>]*\s(width|height)\s*=/i,
    msg: "width/height attr on <svg> (use viewBox only)",
  },
  // Quoted handler attrs only (onclick="…") — React's onClick={…} uses braces and
  // compiles to addEventListener, so it is deliberately NOT matched here.
  {
    id: "INLINE-HANDLER",
    REQ: "REQ-049",
    blocking: true,
    scope: "code",
    re: /\son(click|dblclick|change|submit|input|load|error|mouse\w+|key\w+|focus|blur)\s*=\s*["']/i,
    msg: "inline event-handler attribute (move into the page <script> / external JS)",
  },
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
    const bodyLines = m[1].split("\n").filter((l) => l.trim()).length;
    if (bodyLines > maxLines) {
      const line = src.slice(0, m.index).split("\n").length;
      out.push({ line, bodyLines });
    }
  }
  return out;
}

// Inline <script> BODIES (D-DoD, 2026-08-04). The DoD has always read "no inline
// <style>/<script> bodies in .astro/.tsx — all CSS/JS external", and the style half
// was gated from day one while the script half was not, so the gate reported clean
// over a 1,067-line script inlined in a page.
//
// Cited as D-DoD rather than a REQ-NNN on purpose: the full standard's REQ-007
// (file:// compatibility) asks for the OPPOSITE — all JS inline, no external .js —
// because it was written for standalone double-clickable artifacts. On this site the
// repo DoD wins, which the digest states outright ("On this site: external JS modules
// via Astro instead — DoD wins over 'inline JS'"). There is no REQ number for
// external-JS-only; inventing one would cite a rule that does not exist.
//
// WARN, never blocking, even on a blocking path. Every page on the blocking path that
// carries a script would fail on the day this landed, and extracting each one is real
// work that changes how a page hydrates — it is discussed with Asif a page at a time,
// not forced by a gate that lands overnight.
//
// NOT a finding: an empty <script></script>; a <script src=...>; a self-closing
// <script ... /> data block (`type="application/json"` set:html — data, not code);
// any non-JS `type=` including the JSON-LD of REQ-008, which the standard REQUIRES;
// and a body that is only `import "…"` statements — that IS the external-module
// pattern the DoD asks for, which is how both layouts point at site-chrome.ts.
// Astro's own `---` frontmatter fence is not a <script> tag and never matches.
const JS_TYPE = /^(module|text\/javascript|application\/javascript)$/i;

function scanScriptBlocks(src) {
  const out = [];
  const open = /<script\b([^>]*)>/g;
  let m;
  while ((m = open.exec(src))) {
    const attrs = m[1];
    // Self-closing `<script … />` — no body, and consuming to the next </script>
    // would swallow the following block whole.
    if (/\/\s*$/.test(attrs)) continue;
    const close = src.indexOf("</script>", open.lastIndex);
    if (close < 0) break;
    const body = src.slice(open.lastIndex, close);
    open.lastIndex = close + "</script>".length;

    if (/\bsrc\s*=/.test(attrs)) continue;
    const type = attrs.match(/\btype\s*=\s*["']([^"']+)["']/);
    if (type && !JS_TYPE.test(type[1].trim())) continue;

    // Strip block comments, then line comments and blanks.
    const code = body
      .replace(/\/\*[\s\S]*?\*\//g, "")
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l && !l.startsWith("//"));
    if (!code.length) continue;
    if (code.every((l) => /^import\b[^;]*;?$/.test(l))) continue;

    out.push({
      line: src.slice(0, m.index).split("\n").length,
      bodyLines: code.length,
    });
  }
  return out;
}

// CSS height-clamp is selector-aware: REQ-002 forbids clamps ONLY on the page-growth
// landmarks, never on cards/badges/progress-bars (where overflow:hidden is legitimate).
// We track the current rule's selector and flag a clamp only when that selector targets
// html / body / main / .container / a bare top-level `section`.
const FORBIDDEN_SELECTOR =
  /(^|[\s,>+~])(html|body|main|section(\[[^\]]*\])?)([\s,>+~{:]|$)|(^|[\s,>+~])\.container([\s,>+~{:]|$)/i;
const CLAMP_PROP =
  /(max-height\s*:|height\s*:\s*100vh|overflow\s*:\s*(hidden|scroll)\b)/i;

function scanCss(_rel, src) {
  const out = [];
  // Strip comments so a `/* overflow: hidden */` note doesn't trip the check.
  const noComments = src.replace(/\/\*[\s\S]*?\*\//g, (m) =>
    m.replace(/[^\n]/g, " "),
  );
  const lines = noComments.split("\n");
  let selector = "";
  let buf = "";
  lines.forEach((line, i) => {
    if (line.includes("html-view-lint-disable-line")) return;
    for (const ch of line) {
      if (ch === "{") {
        selector = buf.trim();
        buf = "";
      } else if (ch === "}") {
        selector = "";
        buf = "";
      } else buf += ch;
    }
    // Inside a block whose selector is a forbidden landmark?
    if (
      selector &&
      FORBIDDEN_SELECTOR.test(selector) &&
      CLAMP_PROP.test(line)
    ) {
      out.push({
        line: i + 1,
        selector: selector.slice(0, 60),
        src: line.trim().slice(0, 120),
      });
    }
  });
  return out;
}

// ── REQ-010 reading floor ────────────────────────────────────────────────────
// Prose intended for reading is 1.2rem minimum. This was ungated until
// 2026-08-06: the config carried two documented `_notes` exceptions for a rule
// that no code implemented, so forty-plus sub-floor prose selectors were never
// reported — including four-sentence FAQ answers at 0.92rem on a blocking-path
// page. Same shape as the INLINE-SCRIPT-BLOCK gap the config records for
// 2026-08-04: a rule everyone believed was gated, wasn't.
//
// WHAT IT FLAGS. Only a declaration whose value can be resolved to a definite
// length below the floor — `rem` and `px` (at the 16px root this site uses).
// `em`, `%`, `var()`, `calc()` and `clamp()` are SKIPPED rather than guessed:
// their computed size depends on a context the linter cannot see, and a floor
// rule that cries wolf on a `clamp()` teaches people to ignore it.
const READING_FLOOR_REM = 1.2;

// The prose elements REQ-010 names, as bare type selectors, plus the narrative
// classes it lists. `th` and `label` are deliberately ABSENT: the rule's own
// EXEMPT list covers mono-uppercase column headers, and in this codebase a
// `label` is form chrome rather than narrative copy. Both are better raised by
// a human reading the page than by a linter that cannot tell a caption from a
// column head.
const PROSE_SELECTOR =
  /(^|[\s,>+~])(p|li|td|dd|dt|blockquote|figcaption)([\s,>+~{:.[]|$)|\.(callout|qa-a|qa-q|gloss|section-description)\b/i;

// UI chrome per REQ-010's EXEMPT list: chips, badges, pills, breadcrumbs,
// jump-nav, metadata tags. Matched on the selector so a `.chip p` stays exempt.
const CHROME_SELECTOR =
  /\b(chip|badge|pill|tag|crumb|breadcrumb|jump|toolbar|tooltip|tip|legend|caption-meta|meta|kbd|code|mono|stat-label|axis|tick|nav)\b/i;

const FONT_SIZE_DECL = /font-size\s*:\s*([^;}]+)/i;

/** The declared size in rem, or null when it cannot be resolved definitely. */
function remValue(raw) {
  const v = raw.trim().toLowerCase();
  if (
    /var\(|calc\(|clamp\(|%|\bem\b(?!\s*$)/.test(v) &&
    !/^\d*\.?\d+rem$/.test(v)
  )
    return null;
  const rem = v.match(/^(\d*\.?\d+)\s*rem$/);
  if (rem) return parseFloat(rem[1]);
  const px = v.match(/^(\d*\.?\d+)\s*px$/);
  if (px) return parseFloat(px[1]) / 16;
  return null;
}

// Walks declaration by declaration rather than line by line. A line-based scan
// (the shape scanCss uses) silently misses `.x p { font-size: 0.5rem; }`,
// because by the time the line ends the closing brace has already cleared the
// selector — so every single-line rule reads as "no selector" and is skipped.
// Real stylesheets contain both shapes, and a floor rule that only sees the
// multi-line one is the same half-gate this check was written to replace.
function scanReadingFloor(_rel, src) {
  const out = [];
  const noComments = src.replace(/\/\*[\s\S]*?\*\//g, (m) =>
    m.replace(/[^\n]/g, " "),
  );
  const lines = noComments.split("\n");

  let selector = ""; // the selector of the block we are inside
  let pending = ""; // chars since the last `{`, `}` or `;`
  let line = 1;
  let declLine = 1; // the line the pending declaration STARTED on
  let disabled = false;

  const flushDecl = () => {
    const decl = pending.match(FONT_SIZE_DECL);
    pending = "";
    if (!decl || !selector || disabled) return;
    if (!PROSE_SELECTOR.test(selector) || CHROME_SELECTOR.test(selector))
      return;
    const rem = remValue(decl[1]);
    if (rem === null || rem >= READING_FLOOR_REM) return;
    out.push({
      line: declLine,
      selector: selector.slice(0, 60),
      rem,
      src: (lines[declLine - 1] ?? "").trim().slice(0, 120),
    });
  };

  for (const ch of noComments) {
    if (ch === "\n") {
      line += 1;
      disabled = (lines[line - 1] ?? "").includes(
        "html-view-lint-disable-line",
      );
      if (!pending.trim()) declLine = line;
      pending += " ";
      continue;
    }
    if (ch === "{") {
      selector = pending.trim();
      pending = "";
      declLine = line;
    } else if (ch === "}") {
      flushDecl();
      selector = "";
      declLine = line;
    } else if (ch === ";") {
      flushDecl();
      declLine = line;
    } else {
      if (!pending.trim()) declLine = line;
      pending += ch;
    }
  }
  return out;
}

// Whole-file checks (presence-based).
const FILE_CHECKS = [
  {
    id: "LANG-ATTR",
    REQ: "REQ-072",
    blocking: true,
    appliesTo: (rel) => rel.startsWith("src/layouts/"),
    ok: (src) => /<html\b[^>]*\blang=/.test(src),
    msg: "layout missing <html lang>",
  },
  {
    id: "SKIP-LINK",
    REQ: "REQ-071",
    blocking: false,
    appliesTo: (rel) => rel.startsWith("src/layouts/"),
    ok: (src) => /skip-link/.test(src),
    msg: "layout missing skip-to-content link",
  },
  {
    id: "SVG-A11Y-TRIPLE",
    REQ: "REQ-022",
    blocking: false,
    appliesTo: (rel) => rel.endsWith(".astro") || rel.endsWith(".tsx"),
    ok: (src) => {
      const svgs = (src.match(/<svg\b/gi) || []).length;
      const roles = (src.match(/role\s*=\s*["']img["']/gi) || []).length;
      const labelled = (src.match(/aria-labelledby\s*=/gi) || []).length;
      return svgs === 0 || (roles >= svgs && labelled >= svgs);
    },
    msg: "inline <svg> missing accessibility triple (role=img + aria-labelledby + <title>/<desc>)",
  },
];

// ---- run ------------------------------------------------------------------
const findings = [];
const allow = config.allow || {};
function suppressed(rel, ruleId) {
  const list = allow[rel];
  return (
    Array.isArray(list) &&
    list.some((e) => e.split(/[\s—:-]/)[0] === ruleId || e.startsWith(ruleId))
  );
}

for (const rel of candidates) {
  const kind = classify(rel);
  if (!kind) continue;
  const abs = join(ROOT, rel);
  let src;
  try {
    src = readFileSync(abs, "utf8");
  } catch {
    continue;
  }
  if (src.includes("html-view-lint-disable-file")) continue;
  const isBlockingFile = kind === "blocking-code";

  if (kind === "css") {
    if (!suppressed(rel, "HEIGHT-CLAMP")) {
      for (const hit of scanCss(rel, src)) {
        findings.push({
          rel,
          line: hit.line,
          id: "HEIGHT-CLAMP",
          REQ: "REQ-002",
          sev: resolveSeverity(false),
          msg: `height/overflow clamp on landmark selector "${hit.selector}"`,
          src: hit.src,
        });
      }
    }
    if (!suppressed(rel, "READING-FLOOR")) {
      for (const hit of scanReadingFloor(rel, src)) {
        findings.push({
          rel,
          line: hit.line,
          id: "READING-FLOOR",
          REQ: "REQ-010",
          // WARN, like INLINE-SCRIPT-BLOCK was when it landed and for the same
          // reason: the rule went ungated long enough to accumulate real
          // violations, and a check that blocks the build the day it is written
          // gets bypassed rather than obeyed. --strict promotes it with the rest.
          sev: resolveSeverity(false),
          msg: `prose below the ${READING_FLOOR_REM}rem reading floor (${hit.rem}rem) on "${hit.selector}"`,
          src: hit.src,
        });
      }
    }
    continue;
  }

  if (!suppressed(rel, "INLINE-STYLE-BLOCK")) {
    const maxLines = config.style_block_max_lines ?? 50;
    for (const hit of scanStyleBlocks(src, maxLines)) {
      findings.push({
        rel,
        line: hit.line,
        id: "INLINE-STYLE-BLOCK",
        REQ: "D-DoD",
        sev: resolveSeverity(false),
        msg: `oversized <style> block (${hit.bodyLines} lines > ${maxLines}) — move to src/styles/*.css`,
        src: "",
      });
    }
  }

  if (!suppressed(rel, "INLINE-SCRIPT-BLOCK")) {
    for (const hit of scanScriptBlocks(src)) {
      findings.push({
        rel,
        line: hit.line,
        id: "INLINE-SCRIPT-BLOCK",
        REQ: "D-DoD",
        // Always warn — see the header note above scanScriptBlocks(). Passing
        // `false` also means --strict promotes it with every other warn, which is
        // the right day to argue about extracting these.
        sev: resolveSeverity(false),
        msg: `inline <script> body (${hit.bodyLines} lines) — move to an external module and import it`,
        src: "",
      });
    }
  }

  const lines = src.split("\n");
  for (const chk of LINE_CHECKS) {
    if (chk.scope === "css") continue;
    if (suppressed(rel, chk.id)) continue;
    lines.forEach((line, i) => {
      if (line.includes("html-view-lint-disable-line")) return;
      if (chk.re.test(line)) {
        const sev = resolveSeverity(chk.blocking && isBlockingFile);
        findings.push({
          rel,
          line: i + 1,
          id: chk.id,
          REQ: chk.REQ,
          sev,
          msg: chk.msg,
          src: line.trim().slice(0, 120),
        });
      }
    });
  }
  for (const chk of FILE_CHECKS) {
    if (!chk.appliesTo(rel)) continue;
    if (suppressed(rel, chk.id)) continue;
    if (!chk.ok(src)) {
      const sev = resolveSeverity(chk.blocking);
      findings.push({
        rel,
        line: 0,
        id: chk.id,
        REQ: chk.REQ,
        sev,
        msg: chk.msg,
        src: "",
      });
    }
  }
}

function resolveSeverity(isErrorByDefault) {
  if (WARN_ONLY) return "warn";
  if (STRICT) return "error";
  return isErrorByDefault ? "error" : "warn";
}

// ---- report ---------------------------------------------------------------
const errors = findings.filter((f) => f.sev === "error");
const warns = findings.filter((f) => f.sev === "warn");

if (JSON_OUT) {
  console.log(
    JSON.stringify({ errors, warns, total: findings.length }, null, 2),
  );
} else {
  const fmt = (f) =>
    `  ${f.sev === "error" ? "✖" : "⚠"} ${f.rel}${f.line ? ":" + f.line : ""}  [${f.id} · ${f.REQ}] ${f.msg}${f.src ? "\n      " + f.src : ""}`;
  if (!findings.length) {
    console.log("html-view-lint: clean — no findings.");
  } else {
    if (errors.length) {
      console.log(`\nhtml-view-lint: ${errors.length} BLOCKING violation(s):`);
      errors.forEach((f) => console.log(fmt(f)));
    }
    if (warns.length) {
      console.log(
        `\nhtml-view-lint: ${warns.length} warning(s) (non-blocking; clean these to reach --strict):`,
      );
      warns.forEach((f) => console.log(fmt(f)));
    }
  }
  console.log(
    `\nMode: ${WARN_ONLY ? "warn-only" : STRICT ? "strict" : "default"} · errors=${errors.length} warns=${warns.length}`,
  );
}

process.exit(errors.length && !WARN_ONLY ? 1 : 0);
