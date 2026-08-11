import {
  faMicrophoneLines,
  faPause,
  faPlay,
  faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { useSyncExternalStore } from "react";
import { Link } from "react-router";

import type { Route } from "./+types/downloads";
import { AppShell } from "~/components/AppShell";
import { EmptyState } from "~/components/EmptyState";
import { Icon } from "~/components/Icon";
import { clock, usePlayer } from "~/components/player/Player";
import { megabytes } from "~/lib/facts";
import { downloads, removeAll, removeBook, remove, subscribe, type DownloadMeta } from "~/lib/offline";
import { count } from "~/lib/plural";
import { session } from "~/middleware/session";

/**
 * What is on this device.
 *
 * THE ONE PAGE THAT WORKS WITH NO NETWORK, and everything odd about it follows
 * from that. The service worker keeps a copy of this document (public/sw.js) and
 * redirects any other failed navigation here, so on a plane this is where the
 * app opens.
 *
 * Which means the list CANNOT come from the loader. A cached document carries
 * the loader data it was rendered with, so a server-rendered list would be
 * whatever was true the last time this page was opened online — and the whole
 * point of the page is to be right about what is on the device now. So the
 * loader returns only what the shell needs, and the list is read on the client
 * from IndexedDB. The stale cached copy is then still correct, because the part
 * that matters was never in it.
 */

export function meta(): Route.MetaDescriptors {
  return [
    { title: "Downloads — Podcast Factory" },
    { name: "description", content: "Episodes kept on this device for listening offline." },
  ];
}

export function loader({ context }: Route.LoaderArgs) {
  // Only the masthead's Access link. Deliberately nothing else — see above.
  return { isAdmin: context.get(session).viewer?.isAdmin === true };
}

/** The store, read the way React wants it read. Empty on the server. */
const NONE: DownloadMeta[] = [];

function useDownloads(): DownloadMeta[] {
  return useSyncExternalStore(
    subscribe,
    downloads,
    () => NONE,
  );
}

export default function Downloads({ loaderData }: Route.ComponentProps) {
  const kept = useDownloads();
  const player = usePlayer();

  // Grouped by book, in the order the books were most recently added to — the
  // list is a record of what you did, so the thing you just downloaded is where
  // you look first.
  const books = new Map<string, DownloadMeta[]>();
  for (const item of kept) {
    const bucket = books.get(item.slug);
    if (bucket === undefined) books.set(item.slug, [item]);
    else bucket.push(item);
  }

  const bytes = kept.reduce((sum, item) => sum + item.bytes, 0);

  return (
    <AppShell here="downloads" isAdmin={loaderData.isAdmin}>
      <section className="pf-masthead pf-masthead--tight">
        <h1 className="pf-title">Downloads</h1>
        <p className="pf-lede">
          {kept.length === 0
            ? "Episodes you keep here play with no signal. Nothing is kept yet."
            : `${count(kept.length, "episode")} on this device, taking ${megabytes(bytes)}. These play with no signal.`}
        </p>

        {kept.length === 0 ? null : (
          <p className="pf-masthead__action">
            <button
              type="button"
              onClick={() => void removeAll()}
              className="pf-button pf-button--soft"
            >
              <Icon icon={faTrash} />
              Remove everything
            </button>
          </p>
        )}
      </section>

      {kept.length === 0 ? (
        <EmptyState>
          Open a book and press <strong className="pf-strong">Download</strong> beside an
          episode. It stays here until you remove it, or until the book stops being
          shared with you.
        </EmptyState>
      ) : (
        [...books].map(([slug, episodes]) => (
          <section key={slug} className="pf-section pf-downloads__book">
            <div className="pf-downloads__head">
              <h2 className="pf-section__title">
                <Link to={`/book/${slug}`} className="pf-link">
                  {episodes[0].bookTitle}
                </Link>
              </h2>
              <p className="pf-section__count">
                {count(episodes.length, "episode")} ·{" "}
                {megabytes(episodes.reduce((sum, e) => sum + e.bytes, 0))}
              </p>
              <button
                type="button"
                onClick={() => void removeBook(slug)}
                className="pf-button pf-button--soft pf-button--sm"
                aria-label={`Remove every download from ${episodes[0].bookTitle}`}
              >
                <Icon icon={faTrash} />
                Remove
              </button>
            </div>

            {/* The same row this episode has on its book's page — same classes,
                same shape — so a downloaded episode does not become a different
                looking thing by being downloaded. */}
            <ol className="pf-rows pf-rows--striped">
              {episodes
                .slice()
                .sort((a, b) => a.number - b.number)
                .map((episode) => {
                  const isCurrent = player.current?.src === episode.src;
                  const isPlaying = isCurrent && player.playing;
                  const label = isPlaying
                    ? `Pause ${episode.title}`
                    : isCurrent
                      ? `Resume ${episode.title}`
                      : `Play ${episode.title}`;

                  return (
                    <li key={episode.src} className="pf-row">
                      <span className="pf-row__mark pf-row__badge" aria-hidden="true">
                        <Icon icon={faMicrophoneLines} />
                      </span>

                      <div className="pf-row__main">
                        <p>{episode.title}</p>
                      </div>

                      <span className="pf-track__facts">
                        <span className="pf-track__fact">{megabytes(episode.bytes)}</span>
                        {episode.durationS ? (
                          <span className="pf-track__fact pf-track__fact--time">
                            {clock(episode.durationS)}
                          </span>
                        ) : null}
                      </span>

                      <div className="pf-row__actions">
                        {/* A bin, not the book page's check-that-becomes-a-bin.
                            Everything on THIS page is on the device, so a tick
                            states the obvious and the only thing worth offering
                            is the way to let it go. */}
                        <button
                          type="button"
                          onClick={() => void remove(episode.src)}
                          className="pf-download"
                          aria-label={`Remove the download of ${episode.title}`}
                          title="Remove from this device"
                        >
                          <Icon icon={faTrash} />
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            isCurrent
                              ? player.toggle()
                              : player.play({
                                  slug: episode.slug,
                                  bookTitle: episode.bookTitle,
                                  number: episode.number,
                                  title: episode.title,
                                  src: episode.src,
                                  durationS: episode.durationS,
                                  // Null, not the media URL. Offline that URL is
                                  // unreachable, and for a downloaded episode the
                                  // player reads the words stored beside the audio.
                                  transcriptSrc: null,
                                })
                          }
                          aria-pressed={isCurrent}
                          aria-label={label}
                          title={label}
                          className={`pf-track__play${isPlaying ? " is-playing" : ""}`}
                        >
                          <Icon icon={isPlaying ? faPause : faPlay} />
                        </button>
                      </div>
                    </li>
                  );
                })}
            </ol>
          </section>
        ))
      )}
    </AppShell>
  );
}
