import { useCallback, useEffect, useState } from "react";

import type {
  ChapterProgress,
  Correction,
  Occurrence,
  SourceView,
} from "~/lib/corrections";
import type { CorrectionEvent } from "~/lib/correctionHistory";

/**
 * A book's corrections, and the seven things a person can do to them.
 *
 * Plain `fetch`, not a router form submission, for the reason the marks store does: a router
 * submission revalidates every loader on the page, and saving a correction must not reload
 * the chapter the moderator is in the middle of reading.
 *
 * The SERVER decides every outcome. This hook never assumes a write worked: it reloads the
 * list after each one, so what is shown is what was stored — including when the answer was
 * "no" (403), "somebody changed it first" (409), or the row is gone (404).
 */
interface Payload {
  corrections: Correction[];
  chapters: ChapterProgress[];
}

export function useCorrections(slug: string, enabled: boolean) {
  const [items, setItems] = useState<Correction[]>([]);
  const [chapters, setChapters] = useState<ChapterProgress[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const fetchList = useCallback(async (): Promise<Payload | null> => {
    try {
      const response = await fetch(`/book/${slug}/corrections`, {
        credentials: "same-origin",
      });
      if (!response.ok) return null;
      return (await response.json()) as Payload;
    } catch {
      // Offline or interrupted: keep what is on screen rather than blanking the list.
      return null;
    }
  }, [slug]);

  const load = useCallback(async () => {
    const list = await fetchList();
    if (list !== null) {
      setItems(list.corrections);
      setChapters(list.chapters);
    }
  }, [fetchList]);

  // State is set in the promise's continuation, never in the effect body itself, so the
  // effect only starts a request and cleans up after it.
  useEffect(() => {
    if (!enabled) return;
    let live = true;
    void fetchList().then((list) => {
      if (!live || list === null) return;
      setItems(list.corrections);
      setChapters(list.chapters);
    });
    return () => {
      live = false;
    };
  }, [enabled, fetchList]);

  /** Returns whether it worked, so the caller knows whether to close its form. */
  const send = useCallback(
    async (fields: Record<string, string | number>): Promise<boolean> => {
      setBusy(true);
      setError(null);
      try {
        const body = new FormData();
        for (const [key, value] of Object.entries(fields))
          body.set(key, String(value));

        const response = await fetch(`/book/${slug}/corrections`, {
          method: "POST",
          body,
          credentials: "same-origin",
        });
        const answer = (await response.json().catch(() => ({}))) as {
          error?: string;
        };
        if (!response.ok) {
          setError(answer.error ?? "That did not work.");
          return false;
        }
        return true;
      } catch {
        setError("Could not reach the server. Nothing was changed.");
        return false;
      } finally {
        await load();
        setBusy(false);
      }
    },
    [slug, load],
  );

  /** Other places the same wording appears, for "fix everywhere". Empty on any failure. */
  const occurrences = useCallback(
    async (quote: string, chapter: string, block: number) => {
      const query = new URLSearchParams({
        occurrences: quote,
        chapter,
        block: String(block),
      });
      try {
        const response = await fetch(`/book/${slug}/corrections?${query}`, {
          credentials: "same-origin",
        });
        return response.ok
          ? ((await response.json()) as { occurrences: Occurrence[] })
              .occurrences
          : [];
      } catch {
        return [];
      }
    },
    [slug],
  );

  /** The source for one chapter — scan and/or extracted. Empty on any failure. */
  const source = useCallback(
    async (chapter: string) => {
      try {
        const response = await fetch(
          `/book/${slug}/corrections?${new URLSearchParams({ source: chapter })}`,
          { credentials: "same-origin" },
        );
        return response.ok
          ? ((await response.json()) as { source: SourceView[] }).source
          : [];
      } catch {
        return [];
      }
    },
    [slug],
  );

  /** The recorded history of one correction, or of the whole book. Empty on any failure. */
  const history = useCallback(
    async (id: string | "all") => {
      try {
        const response = await fetch(
          `/book/${slug}/corrections?${new URLSearchParams({ history: id })}`,
          { credentials: "same-origin" },
        );
        return response.ok
          ? ((await response.json()) as { history: CorrectionEvent[] }).history
          : [];
      } catch {
        return [];
      }
    },
    [slug],
  );

  return {
    history,
    items,
    chapters,
    error,
    busy,
    send,
    occurrences,
    source,
    clearError: () => setError(null),
  };
}
