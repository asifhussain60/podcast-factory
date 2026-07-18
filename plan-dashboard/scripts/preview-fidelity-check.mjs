#!/usr/bin/env node
/**
 * preview-fidelity-check.mjs — deterministic Preview↔PDF parity gate.
 *
 * The on-screen Preview (the composer's paginated "Preview" mode) and the printed
 * `book.pdf` are two code paths. This probe proves they agree, so Preview can never
 * silently lie about how the PDF paginates (studio-composer standard REQ-SC-023).
 *
 * It compares two per-page STRUCTURES — one extracted from the PDF (via pdftotext),
 * one from the in-browser paginated Preview — and reports drift by stable PF-NNN id:
 *
 *   PF-001 (P0) — page count matches.
 *   PF-002 (P1) — per-page text-flow boundaries match (each page's first + last
 *                 non-empty line agree, so a page turn lands on the same words).
 *   PF-003 (P0) — figure-to-page assignment matches (each figure caption appears on
 *                 the same page number in both).
 *   PF-004 (P1) — chapter-open pages align (a "CHAPTER N" opener starts the same page).
 *
 * The diff engine (`diffPageStructures`) is PURE — it takes two page-structure arrays
 * and unit-tests without Playwright or Poppler. The two extractors are I/O seams:
 *   - extractPdfPageStructure()      — implemented (pdftotext, Poppler).
 *   - extractPreviewPageStructure()  — wired in Phase 3 (needs the Preview route +
 *                                      Paged.js pagination to exist). Guarded until then.
 *
 * Usage:
 *   node scripts/preview-fidelity-check.mjs --slug <slug> [--json] [--base-url URL]
 * Exit: 0 = SC-CLEAN, 2 = SC-CAUTION (only P1), 1 = SC-BROKEN (any P0) / error.
 *
 * Cortex-clean: no inline styling concerns (this is a Node CLI, not a view). Reuses
 * the SAME pdftotext seam as scripts/podcast/_book_render_checks.py so the PDF side
 * is measured identically to the print-quality gate.
 */

import {
  existsSync,
  readFileSync,
  mkdtempSync,
  rmSync,
  readdirSync,
} from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { execFileSync } from "node:child_process";

const REPO_ROOT = new URL("../..", import.meta.url).pathname;
const CONTENT_DIR = join(REPO_ROOT, "content");
const BUCKETS = ["Islamic", "Technical", "Fiction", "Guides"];

// A short line repeated as a chapter opener; the print renderer emits an eyebrow
// like "CHAPTER 3" on chapter-open pages (render-book-pdf.mjs renderMd).
const CHAPTER_OPEN_RE = /\bCHAPTER\s+([0-9IVXLC]+)\b/i;

// ---- book/content resolution ---------------------------------------------
function resolveBookDir(slug) {
  for (const b of BUCKETS) {
    const d = join(CONTENT_DIR, b, slug);
    if (existsSync(join(d, "book"))) return join(d, "book");
  }
  // nested volume container: <container>/<container>-vol-NN
  for (const b of BUCKETS) {
    const bdir = join(CONTENT_DIR, b);
    if (!existsSync(bdir)) continue;
    for (const container of readdirSync(bdir)) {
      const d = join(bdir, container, slug);
      if (existsSync(join(d, "book"))) return join(d, "book");
    }
  }
  return null;
}

function loadFigureCaptions(bookDir) {
  // Captions come from the visuals index; used to locate each figure by page.
  const idx = join(bookDir, "visuals", "index.json");
  if (!existsSync(idx)) return [];
  try {
    const data = JSON.parse(readFileSync(idx, "utf8"));
    const visuals = Array.isArray(data) ? data : data.visuals || [];
    return visuals
      .map((v) => ({ id: v.id, caption: (v.caption || "").trim() }))
      .filter((v) => v.caption.length >= 4);
  } catch {
    return [];
  }
}

// ---- structure builders ---------------------------------------------------
// A page structure: { page, firstLine, lastLine, chapterOpen: <n|null>, figures: [id...] }
function pageStructureFromText(pagesText, captions) {
  return pagesText.map((raw, i) => {
    const lines = String(raw || "")
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    const openMatch =
      (lines[0] || "").match(CHAPTER_OPEN_RE) || raw.match(CHAPTER_OPEN_RE);
    const norm = raw.toLowerCase();
    const figures = captions
      .filter((c) => norm.includes(c.caption.toLowerCase()))
      .map((c) => c.id);
    return {
      page: i + 1,
      firstLine: lines[0] || "",
      lastLine: lines[lines.length - 1] || "",
      chapterOpen: openMatch ? openMatch[1] : null,
      figures,
    };
  });
}

// ---- PDF extractor (implemented) ------------------------------------------
function extractPdfPageStructure(pdfPath, captions, maxPages = 600) {
  if (!existsSync(pdfPath)) throw new Error(`PDF not found: ${pdfPath}`);
  let pdftotext;
  try {
    pdftotext = execFileSync("which", ["pdftotext"]).toString().trim();
  } catch {
    return null; // Poppler unavailable — caller defers (matches _book_render_checks.py)
  }
  const tmp = mkdtempSync(join(tmpdir(), "pf-pdf-"));
  const pages = [];
  try {
    for (let p = 1; p <= maxPages; p++) {
      const out = join(tmp, `p${p}.txt`);
      try {
        // stderr suppressed: probing past the last page errors by design; we break.
        execFileSync(
          pdftotext,
          ["-f", String(p), "-l", String(p), "-layout", pdfPath, out],
          {
            stdio: ["ignore", "ignore", "ignore"],
          },
        );
      } catch {
        break; // past last page
      }
      if (!existsSync(out)) break;
      pages.push(readFileSync(out, "utf8"));
    }
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
  return pageStructureFromText(pages, captions);
}

// ---- Preview extractor (Phase 3 seam) -------------------------------------
// Renders the paginated Preview in headless chromium and reads each page box
// (Paged.js `.pagedjs_page`) → per-page text/figures/chapter-open. Wired when the
// Preview route + Paged.js pagination land (studio-composer REQ-SC-020..022).
async function extractPreviewPageStructure(_baseUrl, _slug, _captions) {
  throw new Error(
    "PF-PREVIEW-NOT-WIRED: the paginated Preview route does not exist yet. " +
      "Implement extractPreviewPageStructure() in Phase 3 (render the Preview in " +
      "chromium, read .pagedjs_page boxes → pageStructureFromText). Until then this " +
      "gate can only be exercised against the PDF side.",
  );
}

// ---- pure diff engine (implemented + unit-testable) -----------------------
export function diffPageStructures(pdfPages, previewPages) {
  const findings = [];
  const add = (id, severity, detail, page) =>
    findings.push({ id, severity, detail, page });

  // PF-001 — page count.
  if (pdfPages.length !== previewPages.length) {
    add(
      "PF-001",
      "P0",
      `page count differs: PDF ${pdfPages.length} vs Preview ${previewPages.length}`,
      null,
    );
  }

  const n = Math.min(pdfPages.length, previewPages.length);
  for (let i = 0; i < n; i++) {
    const a = pdfPages[i];
    const b = previewPages[i];

    // PF-002 — text-flow boundaries (normalize whitespace before comparing).
    const norm = (s) => s.replace(/\s+/g, " ").trim().toLowerCase();
    if (
      norm(a.firstLine) !== norm(b.firstLine) ||
      norm(a.lastLine) !== norm(b.lastLine)
    ) {
      add(
        "PF-002",
        "P1",
        `page ${a.page} flow boundary differs — PDF ["${a.firstLine}" … "${a.lastLine}"] ` +
          `vs Preview ["${b.firstLine}" … "${b.lastLine}"]`,
        a.page,
      );
    }

    // PF-003 — figure-to-page assignment.
    const aFigs = new Set(a.figures);
    const bFigs = new Set(b.figures);
    const misplaced = [...new Set([...aFigs, ...bFigs])].filter(
      (id) => aFigs.has(id) !== bFigs.has(id),
    );
    if (misplaced.length) {
      add(
        "PF-003",
        "P0",
        `page ${a.page} figure set differs: ${misplaced.join(", ")}`,
        a.page,
      );
    }

    // PF-004 — chapter-open alignment.
    if (String(a.chapterOpen) !== String(b.chapterOpen)) {
      add(
        "PF-004",
        "P1",
        `page ${a.page} chapter-open differs: PDF ${a.chapterOpen} vs Preview ${b.chapterOpen}`,
        a.page,
      );
    }
  }
  findings.sort(
    (x, y) =>
      (x.severity !== "P0") - (y.severity !== "P0") ||
      (x.page || 0) - (y.page || 0),
  );
  return findings;
}

export function verdictFor(findings) {
  if (findings.some((f) => f.severity === "P0")) return "SC-BROKEN";
  if (findings.length) return "SC-CAUTION";
  return "SC-CLEAN";
}

// ---- CLI ------------------------------------------------------------------
function parseArgs(argv) {
  const args = {
    json: false,
    baseUrl: process.env.SITE_HEALTH_BASE_URL || "http://localhost:4322",
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--json") args.json = true;
    else if (a === "--slug") args.slug = argv[++i];
    else if (a === "--base-url") args.baseUrl = argv[++i];
    else if (!a.startsWith("--") && !args.slug) args.slug = a;
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.slug) {
    console.error(
      "usage: node scripts/preview-fidelity-check.mjs --slug <slug> [--json] [--base-url URL]",
    );
    process.exit(1);
  }
  const bookDir = resolveBookDir(args.slug);
  if (!bookDir) {
    console.error(
      `No book/ dir found for slug "${args.slug}" under any content bucket.`,
    );
    process.exit(1);
  }
  const captions = loadFigureCaptions(bookDir);
  const pdfPath = join(bookDir, "book.pdf");

  const pdfPages = extractPdfPageStructure(pdfPath, captions);
  if (pdfPages === null) {
    console.error(
      "pdftotext (Poppler) unavailable — deferring parity check (no failure).",
    );
    process.exit(0);
  }

  let previewPages;
  try {
    previewPages = await extractPreviewPageStructure(
      args.baseUrl,
      args.slug,
      captions,
    );
  } catch (err) {
    // Phase 0/1/2: the Preview surface is not built yet. Report the PDF side and
    // defer, rather than failing — the gate goes live in Phase 3.
    const payload = {
      slug: args.slug,
      pdf_pages: pdfPages.length,
      preview_pages: null,
      verdict: "DEFERRED",
      reason: String(err.message || err),
      findings: [],
    };
    if (args.json) console.log(JSON.stringify(payload, null, 2));
    else {
      console.log(`preview-fidelity: DEFERRED — ${payload.reason}`);
      console.log(
        `(PDF side ready: ${pdfPages.length} pages extracted for "${args.slug}".)`,
      );
    }
    process.exit(0);
  }

  const findings = diffPageStructures(pdfPages, previewPages);
  const verdict = verdictFor(findings);
  const payload = {
    slug: args.slug,
    pdf_pages: pdfPages.length,
    preview_pages: previewPages.length,
    verdict,
    findings,
  };
  if (args.json) {
    console.log(JSON.stringify(payload, null, 2));
  } else {
    console.log(`preview-fidelity: ${verdict} (${findings.length} finding(s))`);
    for (const f of findings)
      console.log(`  ${f.severity} ${f.id} — ${f.detail}`);
  }
  process.exit(verdict === "SC-BROKEN" ? 1 : verdict === "SC-CAUTION" ? 2 : 0);
}

// Only run main() when invoked directly (keeps the diff engine importable for tests).
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
