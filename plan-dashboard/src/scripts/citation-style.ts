/**
 * citation-style.ts — client for /studio/<slug>/style (Book Pipeline v2).
 *
 * The three family chips render the live preview with CSS :has() alone — no JS
 * needed for that. This module only (a) reflects the previously-saved family on
 * load and (b) persists a new choice to book/citation-style.json via the
 * citation-style endpoint, updating the save-state line. Mirrors the fetch shape
 * used by book-composer.ts (apiOk/apiError envelopes).
 */
type ApiEnvelope<T> = { ok: true; data: T } | { ok: false; error: string };

const form = document.querySelector<HTMLFormElement>(".bs-styleform");
const saveLine = document.getElementById("bs-save");
const slug = form?.dataset.slug ?? "";

function radios(): HTMLInputElement[] {
  return form
    ? Array.from(
        form.querySelectorAll<HTMLInputElement>('input[name="citation-style"]'),
      )
    : [];
}

function setStatus(text: string, state: "" | "saved" | "error"): void {
  if (!saveLine) return;
  saveLine.textContent = text;
  saveLine.classList.toggle("is-saved", state === "saved");
  saveLine.classList.toggle("is-error", state === "error");
}

async function loadSaved(): Promise<void> {
  if (!slug) return;
  try {
    const res = await fetch(
      `/api/studio/citation-style?slug=${encodeURIComponent(slug)}`,
    );
    const json = (await res.json()) as ApiEnvelope<{ family: string }>;
    if (!json.ok) return;
    const saved = json.data.family;
    const match = radios().find((r) => r.value === saved);
    if (match && !match.checked) match.checked = true;
  } catch {
    /* Non-fatal: the pre-checked default stands if the fetch fails. */
  }
}

async function save(family: string): Promise<void> {
  if (!slug) return;
  setStatus("Saving…", "");
  try {
    const res = await fetch("/api/studio/citation-style", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ slug, family }),
    });
    const json = (await res.json()) as ApiEnvelope<{ family: string }>;
    if (json.ok) {
      setStatus(`Saved — the book will print in the ${family} style.`, "saved");
    } else {
      setStatus(`Couldn't save: ${json.error}`, "error");
    }
  } catch (e) {
    setStatus(`Couldn't save: ${String(e)}`, "error");
  }
}

if (form) {
  form.addEventListener("change", (ev) => {
    const target = ev.target as HTMLInputElement;
    if (target?.name === "citation-style" && target.checked) save(target.value);
  });
  void loadSaved();
}
