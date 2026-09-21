import { useEffect, useState } from "react";

import type { SourceView } from "~/lib/corrections";
import { locateSpan } from "~/lib/sourceMatch";

const QUALITY = {
  clean: "Clean",
  noisy: "Noisy",
  unreliable: "Unreliable — handwritten or badly scanned",
} as const;

/**
 * The source a chapter was made from, beside the corrections.
 *
 * Two kinds, and they are labelled for what they are, because the difference matters to whoever is
 * judging a fix: the SCAN is the original letters and can carry an OCR error; the EXTRACTED text
 * is the pipeline's own English and is already an interpretation. A scan's quality is shown, so a
 * handwritten one is never presented with the confidence of a clean one.
 *
 * The matching span is highlighted only in the extracted text, which is English like the book. A
 * scan is in the original script and cannot be matched to an English quote, so it is not guessed
 * at — the moderator is given the pages and the page range instead.
 */
export function SourcePane({
  load,
  chapter,
  quote,
  onUse,
}: {
  load: (chapter: string) => Promise<SourceView[]>;
  chapter: string;
  /** The passage being corrected, to find in the extracted text. */
  quote?: string;
  /** Put the moderator's selected source words into the correction. */
  onUse?: (text: string) => void;
}) {
  const [views, setViews] = useState<SourceView[] | null>(null);
  const [tab, setTab] = useState<SourceView["kind"] | null>(null);

  useEffect(() => {
    let live = true;
    void load(chapter).then((loaded) => {
      if (!live) return;
      setViews(loaded);
      setTab(loaded[0]?.kind ?? null);
    });
    return () => {
      live = false;
    };
  }, [load, chapter]);

  const view = views?.find((v) => v.kind === tab) ?? null;

  // Not memoised by hand: the React compiler already caches this, and a hand-written `useMemo`
  // over a value derived from state is what it refuses to preserve.
  let marked: { page: number; span: { start: number; end: number } } | null =
    null;
  if (view !== null && view.kind === "extracted" && quote) {
    for (const page of view.pages) {
      const span = locateSpan(page.text, quote);
      if (span !== null) {
        marked = { page: page.page, span };
        break;
      }
    }
  }

  if (views === null) return <p className="pf-cx-hint">Loading the source…</p>;
  if (view === null)
    return (
      <p className="pf-note pf-empty">
        No source text is on file for this chapter.
      </p>
    );

  const useSelection = () => {
    const text = window.getSelection()?.toString().trim() ?? "";
    if (text !== "") onUse?.(text);
  };

  return (
    <div className="pf-cx-source">
      <div className="pf-cx-source__bar">
        <div
          role="tablist"
          aria-label="Which source"
          className="pf-cx-source__tabs"
        >
          {views.map((v) => (
            <button
              key={v.kind}
              type="button"
              role="tab"
              aria-selected={tab === v.kind}
              onClick={() => setTab(v.kind)}
            >
              {v.kind === "scan" ? "Scanned source" : "Extracted text"}
            </button>
          ))}
        </div>
        <span className="pf-cx-source__meta">
          {view.firstPage === view.lastPage
            ? `p. ${view.firstPage}`
            : `pp. ${view.firstPage}–${view.lastPage}`}
        </span>
      </div>

      <p className="pf-cx-source__quality" data-quality={view.quality}>
        {view.kind === "scan" ? "Scan quality" : "Extraction"}:{" "}
        {QUALITY[view.quality]}
        {view.kind === "scan" && quote
          ? " · in the original script, so the passage is not marked — use the page range."
          : ""}
      </p>

      <div
        className="pf-cx-source__pages"
        lang={view.kind === "scan" ? "ar" : "en"}
        dir={view.kind === "scan" ? "rtl" : "ltr"}
      >
        {view.pages.map((page) => (
          <section key={page.page} aria-label={`Page ${page.page}`}>
            <h4 className="pf-cx-source__page">Page {page.page}</h4>
            <p>
              {marked !== null && marked.page === page.page ? (
                <>
                  {page.text.slice(0, marked.span.start)}
                  <mark className="pf-cx-match">
                    {page.text.slice(marked.span.start, marked.span.end)}
                  </mark>
                  {page.text.slice(marked.span.end)}
                </>
              ) : (
                page.text
              )}
            </p>
          </section>
        ))}
      </div>

      {onUse === undefined ? null : (
        <div className="pf-cx-source__foot">
          <span className="pf-cx-hint">Select words above, then</span>
          <button
            type="button"
            onClick={useSelection}
            className="pf-button pf-button--sm pf-button--soft"
          >
            Use selection in correction
          </button>
        </div>
      )}
    </div>
  );
}
