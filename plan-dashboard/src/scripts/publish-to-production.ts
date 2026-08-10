/**
 * publish-to-production.ts — the Book Composer's Publish button, end to end.
 *
 * Ask what to publish -> stream the run into a live panel -> show the
 * verification -> leave the button telling the truth about what is live.
 *
 * WHY THE BUTTON HAS A STATE AT ALL
 * ---------------------------------
 * "Any time I make a change to any chapter, the publish button should be
 * activated" (Asif, 2026-08-06). Two things keep that true, and they answer
 * different questions:
 *
 *   * On load, the server is asked. It compares a fingerprint of the composed
 *     prose and the Companion cards against the one recorded by the last
 *     VERIFIED publish, so the answer survives a reload, a different browser and
 *     a different machine — and it stays lit after a publish that could not
 *     prove itself.
 *   * On save, `markPending` lights it immediately. Waiting for a round-trip to
 *     agree would leave the button reading "up to date" over an edit that plainly
 *     is not, which is the single thing it exists to prevent.
 *
 * The failure direction is always "there is something to publish". A button that
 * wrongly says up-to-date loses work silently; one that wrongly asks costs a
 * click.
 */
import { publishOptionsDialog, publishProgressPanel } from "./publish-dialog";
import type { PublishChoice } from "./publish-dialog";

export interface PublishState {
  pending?: boolean;
  reason?: string;
  unreviewed?: number;
  cards?: number;
  publishedAt?: string;
}

const BUTTON_ID = "cx-publish-prod";

function button(): HTMLButtonElement | null {
  return document.querySelector<HTMLButtonElement>(`#${BUTTON_ID}`);
}

/** Paint the button from a state. `is-pending` is the lit look; the title is
 *  what a hover explains, and it is the server's own sentence. */
function paint(state: PublishState): void {
  const btn = button();
  if (!btn) return;
  const pending = state.pending !== false;
  btn.classList.toggle("is-pending", pending);
  const reason =
    state.reason ??
    (pending ? "there are changes to publish" : "live and up to date");
  // "both sites" rather than "to production" (Asif, 2026-08-10): one press now
  // publishes to localhost AND the live site, and a tooltip naming only one of
  // them would understate what the button is about to do.
  btn.title = pending
    ? `Publish to localhost and the live site — ${reason}`
    : `Published${state.publishedAt ? ` ${state.publishedAt.slice(0, 10)}` : ""} — ${reason}`;
  const label = btn.querySelector<HTMLElement>(".cx-hdr-btn-label");
  if (label) label.textContent = pending ? "Publish" : "Published";
}

/** Light the button now, without asking the server. Called after a save. */
export function markPending(
  reason = "chapters or cards changed since the last publish",
): void {
  paint({ pending: true, reason });
}

async function fetchState(slug: string): Promise<PublishState> {
  try {
    const res = await fetch(
      `/api/studio/publish-to-production?slug=${encodeURIComponent(slug)}`,
    );
    const json = (await res.json()) as { ok?: boolean; data?: PublishState };
    return json.ok && json.data ? json.data : { pending: true };
  } catch {
    // Unreachable server is not evidence that the book is current.
    return { pending: true, reason: "could not check what is live" };
  }
}

/** The options offered, and which are ticked. This is where the judgement about
 *  sensible defaults lives — the dialog itself decides nothing. */
export function choicesFor(state: PublishState): PublishChoice[] {
  const unreviewed = state.unreviewed ?? 0;
  const chaptersChanged = (state.reason ?? "").includes("changed");
  const choices: PublishChoice[] = [];

  // Only offered when there is something to accept — a ticked box that would do
  // nothing teaches the reader to stop reading the boxes.
  if (unreviewed > 0) {
    choices.push({
      id: "accept",
      icon: "fa-solid fa-check-double",
      label: `Accept ${unreviewed} unreviewed Companion card${unreviewed === 1 ? "" : "s"}`,
      hint: "They publish either way — this marks them as read so a later pass cannot withdraw them.",
      checked: true,
    });
  }

  choices.push({
    id: "rebuildPdf",
    icon: "fa-solid fa-file-pdf",
    label: "Re-render the reading edition first",
    // The hint explains the TICK, so it has to change with it. Saying "ticked
    // because…" over an unticked box is the kind of small lie that teaches a
    // reader the hints are decorative.
    hint: chaptersChanged
      ? "About a minute. Ticked because chapters changed — a stale PDF would disagree with the text on screen."
      : "About a minute. The PDF on disk already matches the chapters, so this is off.",
    // Intelligent default: the print edition is uploaded with the book, so an
    // edited chapter over a stale PDF sends readers a printed book that
    // disagrees with what they read on screen.
    checked: chaptersChanged,
  });

  choices.push({
    id: "transcripts",
    icon: "fa-solid fa-closed-captioning",
    label: "Transcribe any new episodes",
    hint: "Only genuinely new recordings cost anything; a re-publish is free.",
    checked: true,
  });

  choices.push({
    id: "media",
    icon: "fa-solid fa-headphones",
    label: "Upload recordings, slides and the print edition",
    hint: "Untick for a text-and-cards update — much faster, and files already live stay live.",
    checked: true,
  });

  return choices;
}

/** Read an NDJSON body, one parsed object at a time, as it arrives. */
export async function* events(
  body: ReadableStream<Uint8Array>,
): AsyncGenerator<Record<string, unknown>> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        yield JSON.parse(line) as Record<string, unknown>;
      } catch {
        yield { event: "log", text: line };
      }
    }
  }
  if (buffer.trim()) {
    try {
      yield JSON.parse(buffer) as Record<string, unknown>;
    } catch {
      yield { event: "log", text: buffer };
    }
  }
}

/**
 * Wire the button.
 *
 * `flush` is the Composer's own "save anything pending" — passed in rather than
 * imported so this module does not depend on the editor. Publishing an unsaved
 * chapter would put yesterday's text in front of readers.
 */
export function initPublishToProduction(
  slug: string,
  bookTitle: string,
  flush?: () => Promise<boolean>,
): void {
  const btn = button();
  if (!btn) return;

  let state: PublishState = { pending: true, reason: "checking…" };
  void fetchState(slug).then((s) => {
    state = s;
    paint(s);
  });

  // Anything that changes what a reader would see lights the button at once.
  // Dispatched by the prose autosave and by every Companion note mutation; a
  // custom event rather than a call so neither of those has to know this button
  // exists.
  document.addEventListener("cx:content-changed", () => markPending());

  btn.addEventListener("click", async () => {
    if (btn.disabled) return;

    if (flush && !(await flush())) {
      const { noticeDialog } = await import("./confirm-dialog");
      await noticeDialog({
        title: "Unsaved edits could not be saved",
        body: "The open chapter has edits that failed to autosave. Resolve the save error first — otherwise readers would get the text without them.",
        danger: true,
      });
      return;
    }

    // Re-read rather than trusting what was fetched on load: the card count and
    // the fingerprint may both have moved during the session, and the numbers in
    // the dialog are the ones being agreed to.
    state = await fetchState(slug);

    const chosen = await publishOptionsDialog({
      bookTitle,
      reason:
        state.pending === false
          ? "Nothing has changed since the last publish — this will re-push it anyway."
          : `Reason: ${state.reason ?? "there are changes to publish"}.`,
      choices: choicesFor(state),
    });
    if (!chosen) return;

    const panel = publishProgressPanel(bookTitle);
    btn.disabled = true;
    let sawDone = false;

    try {
      const res = await fetch("/api/studio/publish-to-production", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ slug, ...chosen }),
      });
      if (!res.ok || !res.body)
        throw new Error(`the server answered ${res.status}`);

      for await (const ev of events(res.body)) {
        const kind = String(ev.event ?? "");
        if (kind === "step") panel.step(String(ev.name ?? ""));
        else if (kind === "warn") panel.log(String(ev.text ?? ""), "warn");
        else if (kind === "error") panel.log(String(ev.text ?? ""), "error");
        else if (kind === "check")
          panel.check(
            String(ev.name ?? ""),
            Boolean(ev.ok),
            String(ev.detail ?? ""),
          );
        else if (kind === "exit") panel.log(String(ev.text ?? ""), "error");
        else if (kind === "done") {
          sawDone = true;
          // A dry run is neither verified nor broken — see PublishOutcome.
          panel.finish(
            ev.dryRun ? "neutral" : ev.verified ? "ok" : "bad",
            String(ev.text ?? ""),
          );
        } else panel.log(String(ev.text ?? ""));
      }
      // A stream that ended without a verdict is a failure, not a success. The
      // panel would otherwise sit on its spinner with no way to close it.
      if (!sawDone)
        panel.finish(
          "bad",
          "The publish stopped before it could confirm anything. Nothing was verified.",
        );
    } catch (error) {
      panel.finish(
        "bad",
        `The publish could not run: ${(error as Error).message}`,
      );
    } finally {
      btn.disabled = false;
    }

    await panel.closed;
    paint(await fetchState(slug));
  });
}
