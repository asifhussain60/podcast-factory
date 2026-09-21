import { useFetcher, useSearchParams } from "react-router";

import {
  NotesList,
  type ChapterRef,
  type EpisodeRef,
} from "~/components/reader/NotesList";
import type { Annotation, Bookmark, EpisodeNote } from "~/lib/marks";
import { TabScope, useChapterScope } from "./TabScope";

/**
 * Nothing is orphaned here, and this constant says so once.
 *
 * `NotesList` takes the set of marks whose passage could not be found. Only the READER can know
 * that — it is discovered by resolving each anchor against the rendered chapter, and this page
 * never renders one. A frozen empty set is the honest answer, and hoisting it out of the render
 * keeps `NotesList` from repainting on every unrelated state change.
 */
const EMPTY_SET: ReadonlySet<string> = new Set<string>();

type Kind = "bm" | "hl" | "nt";
const FILTERS: [Kind, string][] = [
  ["bm", "Bookmarks"],
  ["hl", "Highlights"],
  ["nt", "Notes"],
];
const hasNote = (a: Annotation) => (a.note ?? "").trim() !== "";

/**
 * Everything the reader has kept in this book, optionally narrowed to one chapter and one kind.
 *
 * The narrowing is `?chapter=` and `?only=`, set by the badges on the chapter list. With neither
 * present this is exactly the list it has always been — the same `NotesList`, given the same
 * props — so a reader who never presses a badge sees no change.
 */
export function MarksTab({
  slug,
  chapters,
  episodes,
  annotations,
  bookmarks,
  episodeNotes,
  onPlay,
}: {
  slug: string;
  chapters: ChapterRef[];
  episodes: EpisodeRef[];
  annotations: Annotation[];
  bookmarks: Bookmark[];
  episodeNotes: EpisodeNote[];
  onPlay: (number: number, seconds: number) => void;
}) {
  const fetcher = useFetcher();
  const [params, setParams] = useSearchParams();
  const scope = useChapterScope(chapters);
  const only = FILTERS.find(([k]) => k === params.get("only"))?.[0] ?? null;

  const post = (fields: Record<string, string>) =>
    void fetcher.submit(fields, {
      method: "post",
      action: `/book/${slug}/marks`,
    });

  const inScope = (key: string) => scope === null || scope.anchorKey === key;
  const shownAnnotations = annotations.filter(
    (a) =>
      inScope(a.anchorKey) &&
      (only === null ||
        (only === "nt" ? hasNote(a) : only === "hl" && !hasNote(a))),
  );
  const shownBookmarks =
    only === null || only === "bm"
      ? bookmarks.filter((b) => inScope(b.anchorKey))
      : [];
  // A moment in an episode belongs to no chapter and to none of the three kinds.
  const shownEpisodeNotes = scope === null && only === null ? episodeNotes : [];

  const choose = (kind: Kind) =>
    setParams(
      (current) => {
        if (current.get("only") === kind) current.delete("only");
        else current.set("only", kind);
        return current;
      },
      { replace: true, preventScrollReset: true },
    );

  return (
    <section className="pf-section">
      {scope === null ? null : (
        <TabScope slug={slug} tab="notes" title={scope.title} />
      )}
      <div className="pf-cx-filters" role="group" aria-label="Show only">
        {FILTERS.map(([kind, label]) => (
          <button
            key={kind}
            type="button"
            aria-pressed={only === kind}
            onClick={() => choose(kind)}
          >
            {label}
          </button>
        ))}
      </div>
      <NotesList
        annotations={shownAnnotations}
        bookmarks={shownBookmarks}
        chapters={chapters}
        // Both lists, because this page is the one place that holds everything marked in this
        // book — the reader's drawer shows chapters and an episode page shows episodes, each
        // showing what it can act on.
        episodes={episodes}
        episodeNotes={shownEpisodeNotes}
        onPlay={onPlay}
        // Nothing is resolved here: see EMPTY_SET.
        orphaned={EMPTY_SET}
        slug={slug}
        onRemoveAnnotation={(id) => post({ intent: "unannotate", id })}
        onRemoveBookmark={(id) => post({ intent: "unbookmark", id })}
        onRemoveEpisodeNote={(id) => post({ intent: "un-episode-note", id })}
        onEditAnnotation={(id, text) => {
          const a = annotations.find((x) => x.id === id);
          if (a === undefined) return;
          post({
            intent: "annotate",
            id: a.id,
            anchorKey: a.anchorKey,
            blockIndex: String(a.blockIndex),
            startOffset: String(a.startOffset),
            endOffset: String(a.endOffset),
            quote: a.quote,
            prefix: a.prefix,
            colour: a.colour,
            note: text,
          });
        }}
        onEditEpisodeNote={(id, text) => {
          const n = episodeNotes.find((x) => x.id === id);
          if (n === undefined) return;
          post({
            intent: "episode-note",
            id: n.id,
            number: String(n.number),
            seconds: String(n.seconds),
            quote: n.quote ?? "",
            note: text,
          });
        }}
      />
    </section>
  );
}
