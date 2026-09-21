import { useCallback, useState } from "react";

import {
  CorrectionCompose,
  type Draft,
} from "~/components/reader/CorrectionCompose";
import { copyText } from "~/components/reader/CorrectionHistory";
import { CorrectionRow } from "~/components/reader/CorrectionRow";
import { SourcePane } from "~/components/reader/SourcePane";
import type { useCorrections } from "~/components/reader/useCorrections";
import { historyMarkdown } from "~/lib/correctionHistory";
import type { Correction } from "~/lib/corrections";
import { count } from "~/lib/plural";
import { TabScope, useChapterScope } from "./TabScope";

type Filter = "open" | "mine" | "all";
const undecided = (c: Correction) =>
  c.status === "open" || c.status === "suggested";

/**
 * Every correction on this book, grouped by chapter, for moderators and admins.
 *
 * This is a SECOND front door onto the same thing the reader's panel edits, so it holds none of
 * the rules: each card is the shared `CorrectionRow`, whose buttons come from the `authority` the
 * server computed, and the route refuses whatever they should not have offered. What this page
 * adds is the view the reader's panel cannot give — the whole book at once, and a way to start
 * from a chapter's badge.
 *
 * A NEW correction is still raised in the reader, where the passage is; there is no text here to
 * select. Editing one that exists needs no selection, so that works in place.
 */
export function CorrectionsTab({
  slug,
  bookTitle,
  chapters,
  api,
}: {
  slug: string;
  bookTitle: string;
  chapters: { anchorKey: string; title: string }[];
  api: ReturnType<typeof useCorrections>;
}) {
  const scope = useChapterScope(chapters);
  const [filter, setFilter] = useState<Filter>("open");
  const [draft, setDraft] = useState<Draft | null>(null);
  const [copied, setCopied] = useState(false);
  const { items, error, busy, send, source, history, clearError } = api;

  const shown = items.filter(
    (c) =>
      (scope === null || c.anchorKey === scope.anchorKey) &&
      (filter === "all" || (filter === "open" ? undecided(c) : c.mine)),
  );
  const groups = chapters
    .map((chapter) => ({
      chapter,
      list: shown.filter((c) => c.anchorKey === chapter.anchorKey),
    }))
    .filter((g) => g.list.length > 0);

  const edit = (c: Correction, proposedText = c.proposedText) => {
    clearError();
    setDraft({
      id: c.id,
      quote: c.quote,
      prefix: c.prefix,
      proposedText,
      rationale: c.rationaleHtml,
      kind: c.kind,
    });
  };
  const none = useCallback(async () => [], []);

  const submit = async (next: Draft) => {
    if (next.id === null) return;
    const ok = await send({
      intent: "revise",
      id: next.id,
      proposedText: next.proposedText,
      rationale: next.rationale,
      kind: next.kind,
    });
    if (ok) setDraft(null);
  };

  const anchorOf = (id: string | null) =>
    items.find((c) => c.id === id)?.anchorKey ?? "";

  return (
    <section className="pf-section">
      {scope === null ? null : (
        <TabScope slug={slug} tab="corrections" title={scope.title} />
      )}

      <div className="pf-cx-filters" role="group" aria-label="Show">
        {(
          [
            ["open", "Open"],
            ["mine", "Mine"],
            ["all", "All"],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            aria-pressed={filter === key}
            onClick={() => setFilter(key)}
          >
            {label}
          </button>
        ))}
        <span className="pf-cx-filters__gap" aria-hidden="true" />
        <button
          type="button"
          title="Copy what is shown, with every change to it, for an AI"
          onClick={async () => {
            const all = await history("all");
            if (await copyText(historyMarkdown(bookTitle, shown, all)))
              setCopied(true);
          }}
        >
          {copied ? "Copied" : "Copy for AI"}
        </button>
      </div>

      {error === null ? null : (
        <p role="alert" className="pf-message pf-message--warn">
          {error}
        </p>
      )}

      {draft === null ? null : (
        <div className="pf-cx">
          <CorrectionCompose
            key={draft.id ?? "new"}
            draft={draft}
            busy={busy}
            findOthers={none}
            renderSource={(use) => (
              <SourcePane
                load={source}
                chapter={anchorOf(draft.id)}
                quote={draft.quote}
                onUse={use}
              />
            )}
            onCancel={() => setDraft(null)}
            onSubmit={(d) => void submit(d)}
          />
        </div>
      )}

      {groups.length === 0 ? (
        <p className="pf-note pf-empty">Nothing here yet.</p>
      ) : (
        groups.map(({ chapter, list }) => (
          <section key={chapter.anchorKey} className="pf-notes__chapter">
            <h3 className="pf-notes__heading">
              <span className="pf-notes__heading-main">{chapter.title}</span>
              <span className="pf-notes__count">
                {count(list.length, "correction")}
              </span>
            </h3>
            {list.map((c) => (
              <CorrectionRow
                key={c.id}
                correction={c}
                api={{ busy, send, history }}
                bookTitle={bookTitle}
                onEdit={(x) => edit(x)}
                onUseSuggestion={edit}
              />
            ))}
          </section>
        ))
      )}
    </section>
  );
}
