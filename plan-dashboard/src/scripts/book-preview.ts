/**
 * book-preview.ts — client driver for /studio/<slug>/preview.
 *
 * Two independent concerns:
 * (1) The "Generate PDF" button: a themed confirmation (confirmDialog — the
 * same vanilla, promise-based dialog the Composer uses, never a native
 * window.confirm()), then POSTs to the existing /api/studio/generate-book-pdf
 * endpoint (unchanged — writes book/book.pdf, the canonical file delivered to
 * readers and Google Drive). This is a deliberate, separate action from the
 * page's own live preview render, which refreshes automatically on every load
 * whenever book.md/visual-layout.json/citation-style.json changed.
 * (2) The Zoom slider: sets the --pv-zoom custom property (percent of the
 * .pv-pages container width, capped at 90% in CSS) consumed by .pv-page-img,
 * persisted to localStorage so the preference carries across books/visits.
 */
import { confirmDialog } from "./confirm-dialog";

const ZOOM_KEY = "pv-zoom-pct";
const ZOOM_MIN = 30;
const ZOOM_MAX = 90;

const pagesEl = document.querySelector<HTMLElement>(".pv-pages");
const zoomRange = document.getElementById(
  "pv-zoom-range",
) as HTMLInputElement | null;
const zoomValue = document.getElementById("pv-zoom-value");

if (pagesEl && zoomRange) {
  const applyZoom = (pct: number): void => {
    const clamped = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, pct));
    pagesEl.style.setProperty("--pv-zoom", `${clamped}%`);
    if (zoomValue) zoomValue.textContent = `${clamped}%`;
    zoomRange.value = String(clamped);
  };

  let saved: number;
  try {
    saved = Number(localStorage.getItem(ZOOM_KEY)) || 50;
  } catch {
    saved = 50;
  }
  applyZoom(saved);

  zoomRange.addEventListener("input", () => {
    const pct = Number(zoomRange.value);
    applyZoom(pct);
    try {
      localStorage.setItem(ZOOM_KEY, String(pct));
    } catch {
      /* localStorage best-effort */
    }
  });
}

const dataEl = document.getElementById("preview-data");
const genBtn = document.getElementById(
  "pv-generate",
) as HTMLButtonElement | null;
const statusEl = document.getElementById("pv-status");

if (dataEl && genBtn) {
  let slug = "";
  try {
    slug =
      (JSON.parse(dataEl.textContent || "{}") as { slug?: string }).slug ?? "";
  } catch {
    slug = "";
  }

  const primaryBtn: HTMLButtonElement = genBtn; // narrowed non-null for the closures below
  const ssBtn = document.getElementById(
    "pv-generate-ss",
  ) as HTMLButtonElement | null;

  // Run one of the two render endpoints behind a themed confirm, updating the
  // shared status line. Both buttons are disabled while either is in flight.
  async function runGenerate(
    endpoint: string,
    confirm: { title: string; body: string; confirmLabel: string },
    pending: string,
    doneLabel: string,
  ): Promise<void> {
    if (!slug) return;
    if (!(await confirmDialog(confirm))) return;
    primaryBtn.disabled = true;
    if (ssBtn) ssBtn.disabled = true;
    if (statusEl) statusEl.textContent = pending;
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ slug }),
      });
      const json = (await res.json()) as {
        ok: boolean;
        error?: string;
        data?: { kb: number };
      };
      if (!json.ok) throw new Error(json.error || "render failed");
      if (statusEl)
        statusEl.textContent = `${doneLabel} (${json.data?.kb ?? "?"} KB).`;
    } catch (err) {
      if (statusEl)
        statusEl.textContent = `Generate failed: ${(err as Error).message}`;
    } finally {
      primaryBtn.disabled = false;
      if (ssBtn) ssBtn.disabled = false;
    }
  }

  primaryBtn.addEventListener("click", () =>
    runGenerate(
      "/api/studio/generate-book-pdf",
      {
        title: "Generate the PDF?",
        body: "This writes book/book.pdf — the file delivered to readers and Google Drive — from what you see in this preview.",
        confirmLabel: "Generate",
      },
      "Rendering PDF… this can take a minute.",
      "PDF generated",
    ),
  );

  if (ssBtn) {
    ssBtn.addEventListener("click", () =>
      runGenerate(
        "/api/studio/generate-self-study-pdf",
        {
          title: "Generate the self-study PDF?",
          body:
            "This generates a labeled study summary and a source-grounded contextual note for " +
            "every chapter (a few minutes), then writes book/book-self-study.pdf. Your reading " +
            "edition (book.pdf) and its Google Drive copy are left untouched.",
          confirmLabel: "Generate",
        },
        "Generating study content + rendering… this takes a few minutes.",
        "Self-study PDF generated",
      ),
    );
  }
}
