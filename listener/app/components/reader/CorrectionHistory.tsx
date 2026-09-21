import { useState } from "react";

import {
  ACTION_WORDS,
  describe,
  historyMarkdown,
  type CorrectionEvent,
} from "~/lib/correctionHistory";
import type { Correction } from "~/lib/corrections";

/** Copy text; falls back to a hidden textarea where the async clipboard is refused. */
export async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.append(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    return ok;
  }
}

/**
 * One correction's recorded history, oldest first, with "Copy for AI": the correction, its
 * reason, the AI review, and every change — as Markdown an AI can act on without the panel.
 * Fetched on open, never with the list, so the list stays light.
 */
export function CorrectionHistory({
  correction: c,
  bookTitle,
  load,
}: {
  correction: Correction;
  bookTitle: string;
  load: (id: string) => Promise<CorrectionEvent[]>;
}) {
  const [events, setEvents] = useState<CorrectionEvent[] | null>(null);
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const toggle = async () => {
    const next = !open;
    setOpen(next);
    if (next) setEvents(await load(c.id));
  };

  const copy = async () => {
    const list = events ?? (await load(c.id));
    if (await copyText(historyMarkdown(bookTitle, [c], list))) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <>
      <button
        type="button"
        className="pf-cx-talk"
        aria-expanded={open}
        onClick={() => void toggle()}
      >
        History
      </button>
      {open ? (
        <div className="pf-cx-history">
          {events === null ? (
            <p className="pf-note">Loading…</p>
          ) : events.length === 0 ? (
            <p className="pf-note">Nothing recorded.</p>
          ) : (
            <ol className="pf-cx-history__list">
              {events.map((e, n) => (
                <li key={n} data-mine={e.mine}>
                  <span className="pf-cx-history__when">
                    {e.at.replace("T", " ").slice(0, 16)}
                  </span>{" "}
                  <strong>{e.mine ? "You" : e.actorName}</strong>{" "}
                  {ACTION_WORDS[e.action] ?? e.action}
                  {describe(e) === "" ? null : (
                    <span className="pf-cx-history__what">: {describe(e)}</span>
                  )}
                </li>
              ))}
            </ol>
          )}
          <button
            type="button"
            className="pf-button pf-button--sm pf-button--ghost"
            onClick={() => void copy()}
          >
            {copied ? "Copied" : "Copy for AI"}
          </button>
        </div>
      ) : null}
    </>
  );
}
