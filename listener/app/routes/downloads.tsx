import {
  faBookOpen,
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
import {
  books,
  downloads,
  removeAll,
  removeBook,
  remove,
  removeText,
  subscribe,
  type DownloadMeta,
  type TextMeta,
} from "~/lib/offline";
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
  // Only the masthead's Dashboard link. Deliberately nothing else — see above.
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

const NO_TEXT: TextMeta[] = [];

function useTexts(): TextMeta[] {
  return useSyncExternalStore(subscribe, books, () => NO_TEXT);
}

export default function Downloads({ loaderData }: Route.ComponentProps) {
  const kept = useDownloads();
  const texts = useTexts();
  const player = usePlayer();

  /* ONE SECTION PER BOOK, whichever of the two things is here.
     Episodes and text were two lists at first, and that put "Ayyuha al-Walad"
     on the page twice under two headings — a book is one thing to the person
     who downloaded it, and which halves of it are on the device is a fact
     ABOUT it rather than a way of sorting it. In the order most recently added
     to, so what you just kept is where you look first. */
  const grouped = new Map<
    string,
    { bookTitle: string; episodes: DownloadMeta[]; text: TextMeta | null }
  >();
  for (const item of kept) {
    const found = grouped.get(item.slug);
    if (found === undefined)
      grouped.set(item.slug, { bookTitle: item.bookTitle, episodes: [item], text: null });
    else found.episodes.push(item);
  }
  for (const item of texts) {
    const found = grouped.get(item.slug);
    if (found === undefined)
      grouped.set(item.slug, { bookTitle: item.bookTitle, episodes: [], text: item });
    else found.text = item;
  }

  const nothing = grouped.size === 0;

  const bytes =
    kept.reduce((sum, item) => sum + item.bytes, 0) +
    texts.reduce((sum, item) => sum + item.bytes, 0);

  return (
    <AppShell here="downloads" isAdmin={loaderData.isAdmin}>
      <section className="pf-masthead pf-masthead--tight">
        <h1 className="pf-title">Downloads</h1>
        <p className="pf-lede">
          {kept.length === 0 && texts.length === 0
            ? "What you keep here works with no signal. Nothing is kept yet."
            : `${[
                kept.length > 0 ? count(kept.length, "episode") : null,
                texts.length > 0 ? `${count(texts.length, "book")} to read` : null,
              ]
                .filter(Boolean)
                .join(" and ")} on this device, taking ${megabytes(bytes)}. These work with no signal.`}
        </p>

        {nothing ? null : (
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

      {nothing ? (
        <EmptyState>
          Open a book and press <strong className="pf-strong">Download</strong> beside an
          episode, or <strong className="pf-strong">Read Offline</strong> above its
          chapters. What you keep stays here until you remove it, or until the book
          stops being shared with you.
        </EmptyState>
      ) : (
        [...grouped].map(([slug, book]) => (
          <section key={slug} className="pf-section pf-downloads__book">
            <div className="pf-downloads__head">
              <h2 className="pf-section__title">
                <Link to={`/book/${slug}`} className="pf-link">
                  {book.bookTitle}
                </Link>
              </h2>
              <p className="pf-section__count">
                {[
                  book.episodes.length > 0 ? count(book.episodes.length, "episode") : null,
                  book.text !== null ? count(book.text.chapters, "chapter") : null,
                ]
                  .filter(Boolean)
                  .join(" · ")}{" "}
                ·{" "}
                {megabytes(
                  book.episodes.reduce((sum, e) => sum + e.bytes, 0) +
                    (book.text?.bytes ?? 0),
                )}
              </p>
              <button
                type="button"
                onClick={() => {
                  void removeBook(slug);
                  void removeText(slug);
                }}
                className="pf-button pf-button--soft pf-button--sm"
                aria-label={`Remove everything downloaded from ${book.bookTitle}`}
              >
                <Icon icon={faTrash} />
                Remove
              </button>
            </div>

            {/* The text, when it is here. Above the episodes because reading is
                what a chapter list is FOR, and because this row is one line
                where the episodes are many. */}
            {book.text === null ? null : (
              <p className="pf-downloads__text">
                <Link
                  to={`/read-offline?book=${encodeURIComponent(slug)}`}
                  className="pf-button pf-button--soft"
                >
                  <Icon icon={faBookOpen} />
                  Read with no signal
                </Link>
                <button
                  type="button"
                  onClick={() => void removeText(slug)}
                  className="pf-download"
                  aria-label={`Remove the downloaded text of ${book.bookTitle}`}
                  title="Remove the text from this device"
                >
                  <Icon icon={faTrash} />
                </button>
              </p>
            )}

            {/* The same row this episode has on its book's page — same classes,
                same shape — so a downloaded episode does not become a different
                looking thing by being downloaded. */}
            {book.episodes.length === 0 ? null : (
            <ol className="pf-rows pf-rows--striped">
              {book.episodes
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
            )}
          </section>
        ))
      )}
    </AppShell>
  );
}
