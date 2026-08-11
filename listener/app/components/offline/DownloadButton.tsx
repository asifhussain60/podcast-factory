import { faCheck, faDownload, faTrash, faXmark } from "@fortawesome/free-solid-svg-icons";
import { useCallback, useState, useSyncExternalStore } from "react";

import { Icon } from "~/components/Icon";
import { megabytes } from "~/lib/facts";
import { download, isDownloaded, remove, subscribe } from "~/lib/offline";

/**
 * Keep this episode on the device, or let it go.
 *
 * ONE control with three states rather than two controls, because "download"
 * and "remove" are the same decision seen from either side, and a row that grows
 * a second button once you press the first teaches that pressing things adds
 * clutter.
 *
 * The label is never only an icon: a downward arrow beside a track is read as
 * "download" by people who already know that convention and as nothing by
 * everyone else, and this row already carries a Play whose meaning is obvious.
 */
export function DownloadButton({
  src,
  slug,
  bookTitle,
  number,
  title,
  durationS,
  transcriptSrc,
  /** Compact: the label is dropped and the icon carries it, with the name in aria. */
  compact = false,
}: {
  src: string;
  slug: string;
  bookTitle: string;
  number: number;
  title: string;
  durationS: number | null;
  transcriptSrc: string | null;
  compact?: boolean;
}) {
  const held = useOfflineFlag(src);
  const [progress, setProgress] = useState<{ loaded: number; total: number | null } | null>(
    null,
  );
  const [failed, setFailed] = useState(false);

  const start = useCallback(async () => {
    setFailed(false);
    setProgress({ loaded: 0, total: null });
    try {
      await download(
        { src, slug, bookTitle, number, title, durationS, transcriptSrc },
        setProgress,
      );
    } catch {
      // Almost always the network going away mid-download. Said on the button
      // rather than in an alert: the listener is looking at this row.
      setFailed(true);
    } finally {
      setProgress(null);
    }
  }, [src, slug, bookTitle, number, title, durationS, transcriptSrc]);

  if (progress !== null) {
    const pct =
      progress.total === null || progress.total === 0
        ? null
        : Math.min(100, Math.round((progress.loaded / progress.total) * 100));

    return (
      <span
        className="pf-download pf-download--busy"
        role="status"
        aria-label={`Downloading episode ${number}${pct === null ? "" : `, ${pct}%`}`}
      >
        {/* A real <progress>, not a div with a width. The width would have to be
            an inline style — the one thing a stylesheet cannot express — and the
            element that exists for this already reports itself to a screen
            reader and handles the value-unknown case by omitting `value`. */}
        <progress
          className="pf-download__bar"
          max={100}
          {...(pct === null ? {} : { value: pct })}
        />
        <span className="pf-download__label">
          {pct === null ? megabytes(progress.loaded) : `${pct}%`}
        </span>
      </span>
    );
  }

  if (held) {
    return (
      <button
        type="button"
        onClick={() => void remove(src)}
        className="pf-download pf-download--held"
        aria-label={`Remove the download of episode ${number}`}
        title="On this device — press to remove"
      >
        <Icon icon={faCheck} className="pf-download__held" />
        <Icon icon={faTrash} className="pf-download__drop" />
        {compact ? null : <span className="pf-download__label">On this device</span>}
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={() => void start()}
      className="pf-download"
      aria-label={`Download episode ${number} to this device`}
    >
      <Icon icon={failed ? faXmark : faDownload} />
      {compact ? null : (
        <span className="pf-download__label">{failed ? "Try again" : "Download"}</span>
      )}
    </button>
  );
}

/**
 * Whether this episode is on the device, kept in step across every copy of the
 * button and the Downloads page at once.
 *
 * `useSyncExternalStore` rather than local state because the same episode has a
 * control in two places — its row on the book page and its row on Downloads —
 * and removing it from one must not leave the other saying it is still here.
 * The server snapshot is always false: there is no IndexedDB there, and
 * rendering "on this device" on the server would be a hydration mismatch on
 * every row.
 */
function useOfflineFlag(src: string): boolean {
  return useSyncExternalStore(
    subscribe,
    () => isDownloaded(src),
    () => false,
  );
}
