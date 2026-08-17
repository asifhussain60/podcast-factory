/**
 * compose-narration.ts — the Book Composer's chapter read-aloud player.
 *
 * Chapter narration audio (scripts/podcast/reader_narration.py, one MP3 per
 * chapter via Azure TTS) has always existed, but only ever got produced at
 * the very end of a book's run — the `publish_driver` step, AFTER Asif has
 * already reviewed and approved the book in this very Composer ("the compose
 * tab is the review gate"). So there was no way to listen to a chapter while
 * reviewing it; narration only existed for books that had already shipped.
 *
 * This module closes that gap with the smallest possible surface: ONE control
 * (`#cx-narration`), shown only in Read mode on the reading-edition lane, that
 * either plays the current chapter's narration (if `book/narration/
 * manifest.json` already has it) or offers a "Generate narration" button that
 * spawns the SAME engine the publish-time driver uses
 * (`api/studio/narration.ts` -> `generate_reader_narration.py` ->
 * `reader_narration.render_reader_narration`) — so a chapter narrated here
 * before publish and a chapter narrated automatically at publish time can
 * never diverge.
 *
 * Deliberately NOT wired into the pipeline: this module only ever calls the
 * generate endpoint in response to a click. No automatic Azure-TTS spend, no
 * page-load side effect, and no highlighting/cue-sync in v1 — a chapter's
 * audio is a plain HTML5 <audio> element; the manifest's timed cues (per-block
 * `startS`/`endS`) are there for a future pass to read-along with, not this
 * one.
 *
 * The one thing genuinely worth getting right is knowing whether narration
 * for a given chapter EXISTS. The manifest lists whole-book render outcomes
 * ("rendered" / "skipped" chapter keys, plus a book-level `reason` when the
 * whole run was skipped), and "skipped" is ambiguous on its own — it means
 * both "already current, the file is fine" and "no speakable text in this
 * chapter, no file was ever written". Rather than parse that ambiguity, this
 * module asks the one question that matters directly: a HEAD request against
 * the audio route itself. If the file is there, it plays; if not, no amount
 * of clever list-reading changes that.
 */

export interface NarrationChapterMeta {
  key: string;
  available: boolean;
  durationS: number | null;
}

export interface ComposeNarrationOptions {
  slug: string;
  chapters: NarrationChapterMeta[];
  /** `#cx-narration` — the whole control, hidden outside Read + book lane. */
  container: HTMLElement;
  generateBtn: HTMLButtonElement;
  audio: HTMLAudioElement;
  status: HTMLElement;
  /** Injected for tests; defaults to `fetch`. */
  fetchImpl?: typeof fetch;
  pollIntervalMs?: number;
}

export interface ComposeNarration {
  /** Point the control at a different chapter (does not change visibility). */
  showChapter: (key: string) => void;
  /** Read mode + book lane together decide whether the control can show at all. */
  setEligible: (eligible: boolean) => void;
}

function audioUrl(slug: string, chapterKey: string): string {
  return (
    `/api/studio/narration-audio?slug=${encodeURIComponent(slug)}` +
    `&chapter=${encodeURIComponent(chapterKey)}`
  );
}

function formatDuration(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds) || seconds <= 0) return "";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60)
    .toString()
    .padStart(2, "0");
  return `${m}:${s}`;
}

export function createComposeNarration(
  opts: ComposeNarrationOptions,
): ComposeNarration {
  const { slug, container, generateBtn, audio, status } = opts;
  const doFetch = opts.fetchImpl ?? fetch;
  const pollMs = opts.pollIntervalMs ?? 3000;

  const chapters = new Map<string, NarrationChapterMeta>(
    opts.chapters.map((c) => [c.key, c]),
  );
  let currentKey = opts.chapters[0]?.key ?? "";
  let eligible = false;
  let generating = false;
  /** Once the whole BOOK reports itself ineligible (wrong profile, no reading
   *  edition, etc.) there is nothing a retry can change — the button stays
   *  retired for the rest of this page view rather than offering a click that
   *  can only fail the same way again. */
  let bookDisabledReason: string | null = null;
  let pollTimer: ReturnType<typeof setTimeout> | null = null;

  function render(): void {
    if (!eligible) {
      container.hidden = true;
      return;
    }
    container.hidden = false;

    if (generating) {
      generateBtn.hidden = true;
      audio.hidden = true;
      status.textContent = "Generating narration for this book…";
      status.classList.remove("is-error");
      return;
    }

    if (bookDisabledReason) {
      generateBtn.hidden = true;
      audio.hidden = true;
      status.textContent = `Narration isn't available for this book — ${bookDisabledReason}.`;
      status.classList.remove("is-error");
      return;
    }

    const meta = chapters.get(currentKey);
    if (meta?.available) {
      generateBtn.hidden = true;
      audio.hidden = false;
      const src = audioUrl(slug, currentKey);
      if (audio.getAttribute("src") !== src) audio.setAttribute("src", src);
      status.textContent = formatDuration(meta.durationS);
      status.classList.remove("is-error");
      return;
    }

    generateBtn.hidden = false;
    generateBtn.disabled = false;
    audio.hidden = true;
    audio.removeAttribute("src");
  }

  /** Ground truth for "does this chapter's file exist" — see the module
   *  header on why this beats parsing the render summary's rendered/skipped
   *  lists. */
  async function probe(key: string): Promise<boolean> {
    try {
      const res = await doFetch(audioUrl(slug, key), { method: "HEAD" });
      return res.ok;
    } catch {
      return false;
    }
  }

  // Stop polling if the tab is closed/hidden mid-generation — a detached
  // Python process keeps running either way, but there is no reason to keep a
  // fetch loop alive against a page nobody will see the result on.
  window.addEventListener("pagehide", () => {
    if (pollTimer !== null) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  });

  async function pollOnce(): Promise<void> {
    let payload: Record<string, unknown>;
    try {
      const res = await doFetch(
        `/api/studio/narration?slug=${encodeURIComponent(slug)}`,
      );
      const body = (await res.json()) as { ok: boolean; data?: unknown };
      payload = (body.ok ? body.data : null) as Record<string, unknown>;
    } catch {
      payload = { state: "error", error: "lost contact with the server" };
    }

    const state = String(payload?.state ?? "error");
    if (state === "running") {
      pollTimer = setTimeout(() => void pollOnce(), pollMs);
      return;
    }

    generating = false;
    if (state === "error") {
      status.textContent = `Couldn't generate narration — ${String(payload?.error ?? "unknown error")}`;
      status.classList.add("is-error");
      render();
      return;
    }
    if (state === "skipped" && payload?.reason) {
      bookDisabledReason = String(payload.reason);
      render();
      return;
    }
    // "done", or a per-chapter "skipped" with no book-level reason: some
    // chapters rendered, some were already current. Ask the one question
    // that matters for THIS chapter directly.
    const available = await probe(currentKey);
    chapters.set(currentKey, {
      key: currentKey,
      available,
      durationS: chapters.get(currentKey)?.durationS ?? null,
    });
    if (!available) {
      status.textContent =
        "No narration was produced for this chapter (it may have no speakable English text).";
      status.classList.add("is-error");
    }
    render();
  }

  generateBtn.addEventListener("click", () => {
    if (generating || bookDisabledReason) return;
    generating = true;
    status.classList.remove("is-error");
    render();
    void (async () => {
      try {
        const res = await doFetch("/api/studio/narration", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ slug }),
        });
        if (!res.ok && res.status !== 409) {
          const body = (await res.json().catch(() => ({}))) as {
            error?: string;
          };
          throw new Error(body.error ?? `${res.status} ${res.statusText}`);
        }
      } catch (err) {
        generating = false;
        status.textContent = `Couldn't start narration — ${(err as Error).message}`;
        status.classList.add("is-error");
        render();
        return;
      }
      pollTimer = setTimeout(() => void pollOnce(), pollMs);
    })();
  });

  render();

  return {
    showChapter(key: string) {
      currentKey = key;
      render();
    },
    setEligible(next: boolean) {
      eligible = next;
      render();
    },
  };
}
