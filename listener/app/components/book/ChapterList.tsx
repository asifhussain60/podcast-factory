import type { ReactNode } from "react";
import {
  faAngleRight,
  faBookOpen,
  faBookmark,
  faCheck,
  faHighlighter,
  faNoteSticky,
  faPenNib,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";
import { Link } from "react-router";

import { Icon } from "~/components/Icon";
import type { ChapterSignal } from "~/lib/chapterSignals";
import { count } from "~/lib/plural";
import { readingMinutes } from "~/lib/reading";

interface Chapter {
  anchorKey: string;
  title: string;
  wordCount: number;
}

/**
 * One badge: what is kept in a chapter, and the door to it.
 *
 * A LINK, not a decoration — it opens the tab that holds the thing it counts, already narrowed to
 * this chapter. That is why the row is no longer one big link: a link inside a link is not
 * something a browser can render, so the title carries the way into the chapter and each badge
 * carries its own.
 */
function Signal({
  icon,
  kind,
  n,
  to,
  label,
}: {
  icon: IconDefinition;
  kind: "bm" | "hl" | "nt" | "cx";
  n: number;
  to: string;
  label: string;
}) {
  if (n === 0) return null;
  const words = `${count(n, label)} — open`;
  return (
    <Link
      to={to}
      className="pf-signal"
      data-kind={kind}
      title={words}
      aria-label={words}
    >
      <Icon icon={icon} />
      <b>{n > 99 ? "99+" : n}</b>
    </Link>
  );
}

/**
 * The reading edition's chapters, each with what is in it.
 *
 * Badges sit in one group against the right edge and stack with one gap between them — a chapter
 * with a single badge shows a single badge rather than holes where the others would go. The
 * correction badge is drawn only for moderators and admins: `signals` carries zeros for anyone
 * else, and this component never asks who is looking.
 */
export function ChapterList({
  slug,
  chapters,
  signals,
  currentKey,
  download,
}: {
  slug: string;
  chapters: Chapter[];
  signals: Map<string, ChapterSignal>;
  currentKey: string | null;
  /** The print-edition button, when there is one. See `PrintEdition`. */
  download: ReactNode;
}) {
  const tab = (name: string, key: string, only?: string) =>
    `/book/${slug}?tab=${name}&chapter=${encodeURIComponent(key)}${
      only === undefined ? "" : `&only=${only}`
    }`;

  return (
    <section className="pf-section">
      <div className="pf-section__head pf-section__head--wrap">
        <div className="pf-section__naming">
          {/* `--lead` (Asif, 2026-08-16): there is no title here — the "Read" tab already says
              that — so the count is the section's heading rather than an afterthought. */}
          <span className="pf-section__count pf-section__count--lead">
            {count(chapters.length, "chapter")}
          </span>
        </div>
        {download}
      </div>

      <ol className="pf-rows pf-rows--striped pf-section__intro">
        {chapters.map((chapter) => {
          const s = signals.get(chapter.anchorKey);
          const key = chapter.anchorKey;
          return (
            <li key={key}>
              {/* No ordinal column. The heading already carries the book's OWN number where it
                  has one ("3. The Hours Before Dawn"), and our position counts the introduction
                  as the first entry — so the two disagreed by one on every line. */}
              <div className="pf-chapter">
                <Link
                  to={`/book/${slug}/read/${encodeURIComponent(key)}`}
                  aria-current={currentKey === key ? "true" : undefined}
                  className="pf-chapter__open"
                >
                  <span
                    className="pf-row__mark pf-row__badge"
                    aria-hidden="true"
                  >
                    <Icon icon={faBookOpen} />
                  </span>
                  <span className="pf-row__main">{chapter.title}</span>
                </Link>

                {s === undefined ? null : (
                  <span
                    className="pf-signals"
                    role="group"
                    aria-label="Kept in this chapter"
                  >
                    <Signal
                      icon={faBookmark}
                      kind="bm"
                      n={s.bookmarks}
                      to={tab("notes", key, "bm")}
                      label="bookmark"
                    />
                    <Signal
                      icon={faHighlighter}
                      kind="hl"
                      n={s.highlights}
                      to={tab("notes", key, "hl")}
                      label="highlight"
                    />
                    <Signal
                      icon={faNoteSticky}
                      kind="nt"
                      n={s.notes}
                      to={tab("notes", key, "nt")}
                      label="note"
                    />
                    <Signal
                      icon={faPenNib}
                      kind="cx"
                      n={s.open}
                      to={tab("corrections", key)}
                      label="open correction"
                    />
                  </span>
                )}

                {s === undefined || s.state === "none" ? (
                  <span className="pf-chapter__state" aria-hidden="true" />
                ) : (
                  <span
                    className="pf-chapter__state"
                    data-state={s.state}
                    role="img"
                    aria-label={
                      s.state === "done" ? "Finished" : "You stopped here"
                    }
                  >
                    {s.state === "done" ? <Icon icon={faCheck} /> : null}
                  </span>
                )}

                <span className="pf-row__meta">
                  {readingMinutes(chapter.wordCount)} min
                </span>
                <Icon icon={faAngleRight} className="pf-row__go" />
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
