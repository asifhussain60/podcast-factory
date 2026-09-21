import { useEffect, useState } from "react";
import { faPenNib, faXmark } from "@fortawesome/free-solid-svg-icons";
import { useParams, useRouteLoaderData } from "react-router";

import { Icon } from "~/components/Icon";
import type { Anchor } from "~/lib/anchor";
import type { Correction, Occurrence } from "~/lib/corrections";
import type { loader as readerLoader } from "~/routes/book.$slug.read.$chapter";
import { ChapterReview } from "./ChapterReview";
import { CorrectionCard } from "./CorrectionCard";
import { CorrectionCompose, type Draft } from "./CorrectionCompose";
import { onCorrectionRequest } from "./correctionBus";
import { SourcePane } from "./SourcePane";
import { useCorrectionMarks } from "./useCorrectionMarks";
import { useCorrections } from "./useCorrections";

type Tab = "corrections" | "source";
type Scope = "chapter" | "book";
type Filter = "all" | "open" | "mine";

const isUndecided = (c: Correction) =>
  c.status === "open" || c.status === "suggested";

/**
 * The correction panel and its edge tab — for moderators and admins ONLY.
 *
 * A third host for the reader's right-hand drawer (the same markup and classes the notes and
 * Companion drawers use), because a correction needs the passage, the source, the replacement and
 * the reason in view at once and a bar floating over the paragraph is the wrong shape for that. On
 * a wide screen it DOCKS beside the text, so a moderator can keep selecting passages with it
 * open — and the Source tab keeps the chapter's source beside the chapter for reading against it.
 *
 * It renders nothing at all for anyone else. The server is the real gate (the corrections route
 * answers 404 to a non-moderator); this is only about not drawing what cannot be used.
 */
export function CorrectionLayer() {
  const data = useRouteLoaderData<typeof readerLoader>(
    "routes/book.$slug.read.$chapter",
  );
  const slug = useParams().slug ?? "";
  const enabled = data?.isModerator === true;
  const chapterKey = data?.chapter.anchorKey ?? "";

  const {
    items,
    chapters,
    error,
    busy,
    send,
    occurrences,
    source,
    clearError,
  } = useCorrections(slug, enabled);

  useCorrectionMarks(items, chapterKey, enabled);

  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [anchor, setAnchor] = useState<Anchor | null>(null);
  const [tab, setTab] = useState<Tab>("corrections");
  const [scope, setScope] = useState<Scope>("chapter");
  const [filter, setFilter] = useState<Filter>("all");

  // The selection bar's "Correct this passage".
  useEffect(() => {
    if (!enabled) return;
    return onCorrectionRequest(({ anchor: selected }) => {
      clearError();
      setAnchor(selected);
      setTab("corrections");
      setDraft({
        id: null,
        quote: selected.quote,
        prefix: selected.prefix,
        proposedText: selected.quote,
        rationale: "",
        kind: "meaning",
      });
      setOpen(true);
    });
  }, [enabled, clearError]);

  // Dock beside the text on a wide screen, so the page stays selectable while this is open. The
  // shell class is the one the Companion drawer already uses; nothing else is added.
  useEffect(() => {
    const shell = document.querySelector(".pf-shell");
    shell?.classList.toggle("pf-shell--docked", open);
    return () => shell?.classList.remove("pf-shell--docked");
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  if (!enabled) return null;

  const openCount = items.filter(isUndecided).length;
  const shown = items.filter(
    (c) =>
      (scope === "book" || c.anchorKey === chapterKey) &&
      (filter === "all" || (filter === "open" ? isUndecided(c) : c.mine)),
  );

  const submit = async (next: Draft, alsoAt: Occurrence[]) => {
    let ok = false;
    if (next.id !== null) {
      ok = await send({
        intent: "revise",
        id: next.id,
        proposedText: next.proposedText,
        rationale: next.rationale,
        kind: next.kind,
      });
    } else if (anchor !== null) {
      const here = {
        anchorKey: chapterKey,
        blockIndex: anchor.blockIndex,
        startOffset: anchor.startOffset,
        endOffset: anchor.endOffset,
        prefix: next.prefix,
      };
      ok =
        alsoAt.length > 0
          ? // "Fix everywhere": this place and the ticked ones, raised as ONE batch.
            await send({
              intent: "propose-many",
              quote: next.quote,
              proposedText: next.proposedText,
              rationale: next.rationale,
              kind: next.kind,
              items: JSON.stringify([here, ...alsoAt]),
            })
          : await send({
              intent: "propose",
              ...here,
              quote: next.quote,
              proposedText: next.proposedText,
              rationale: next.rationale,
              kind: next.kind,
            });
    }
    if (ok) setDraft(null);
  };

  const findOthers = (quote: string) =>
    anchor === null
      ? Promise.resolve([])
      : occurrences(quote, chapterKey, anchor.blockIndex);

  const editing = (c: Correction, proposedText = c.proposedText) => {
    clearError();
    setTab("corrections");
    setDraft({
      id: c.id,
      quote: c.quote,
      prefix: c.prefix,
      proposedText,
      rationale: c.rationaleHtml,
      kind: c.kind,
    });
  };

  const decide = (intent: string, c: Correction, note?: string) =>
    void send({
      intent,
      id: c.id,
      expectedUpdatedAt: c.updatedAt,
      ...(note === undefined ? {} : { note }),
    });

  return (
    <>
      {open ? null : (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-expanded={false}
          aria-label="Open corrections"
          title="Corrections"
          className="pf-edge-tab pf-edge-tab--end pf-edge-tab--correct"
        >
          <Icon icon={faPenNib} />
          <span className="pf-edge-tab__label">Corrections</span>
          {openCount === 0 ? null : (
            <span className="pf-edge-tab__count">{openCount}</span>
          )}
        </button>
      )}

      {open ? (
        <>
          <button
            type="button"
            aria-hidden="true"
            tabIndex={-1}
            onClick={() => setOpen(false)}
            className="pf-drawer__scrim"
          />
          <aside
            aria-label="Corrections"
            className="pf-drawer pf-drawer--end pf-drawer--docked pf-drawer--correct"
          >
            <div className="pf-drawer__head">
              <h2 className="pf-drawer__title">Corrections</h2>
              <button
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close corrections"
                className="pf-tool"
              >
                <Icon icon={faXmark} title="Close corrections" />
              </button>
            </div>

            <div className="pf-drawer__body pf-cx">
              <div role="tablist" aria-label="Panel" className="pf-cx-tabs">
                {(
                  [
                    ["corrections", "Corrections"],
                    ["source", "Source"],
                  ] as const
                ).map(([key, label]) => (
                  <button
                    key={key}
                    type="button"
                    role="tab"
                    aria-selected={tab === key}
                    onClick={() => setTab(key)}
                  >
                    {label}
                  </button>
                ))}
              </div>

              {error === null ? null : (
                <p role="alert" className="pf-message pf-message--warn">
                  {error}
                </p>
              )}

              {tab === "source" ? (
                <SourcePane load={source} chapter={chapterKey} />
              ) : (
                <>
                  <ChapterReview
                    chapters={chapters}
                    current={chapterKey}
                    busy={busy}
                    onReview={(key, on) =>
                      void send({
                        intent: "review",
                        anchorKey: key,
                        on: on ? 1 : 0,
                      })
                    }
                    onClaim={(key, on) =>
                      void send({
                        intent: "claim",
                        anchorKey: key,
                        on: on ? 1 : 0,
                      })
                    }
                  />

                  {draft === null ? (
                    <p className="pf-cx-idle">
                      <strong>Select any word, sentence or paragraph</strong>{" "}
                      and press <em>Correct this passage</em>. Everyone with
                      this power sees the same list.
                    </p>
                  ) : (
                    <CorrectionCompose
                      key={draft.id ?? "new"}
                      draft={draft}
                      busy={busy}
                      findOthers={findOthers}
                      renderSource={(use) => (
                        <SourcePane
                          load={source}
                          chapter={chapterKey}
                          quote={draft.quote}
                          onUse={use}
                        />
                      )}
                      onCancel={() => setDraft(null)}
                      onSubmit={submit}
                    />
                  )}

                  <section
                    aria-label="Corrections on this book"
                    className="pf-cx-list"
                  >
                    <div
                      className="pf-cx-filters"
                      role="group"
                      aria-label="Show"
                    >
                      {(
                        [
                          ["chapter", "This chapter"],
                          ["book", "Whole book"],
                        ] as const
                      ).map(([key, label]) => (
                        <button
                          key={key}
                          type="button"
                          aria-pressed={scope === key}
                          onClick={() => setScope(key)}
                        >
                          {label}
                        </button>
                      ))}
                      <span className="pf-cx-filters__gap" aria-hidden="true" />
                      {(
                        [
                          ["all", "All"],
                          ["open", "Open"],
                          ["mine", "Mine"],
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
                    </div>

                    {shown.length === 0 ? (
                      <p className="pf-note pf-empty">Nothing here yet.</p>
                    ) : (
                      shown.map((c) => (
                        <CorrectionCard
                          key={c.id}
                          correction={c}
                          busy={busy}
                          onEdit={(x) => editing(x)}
                          onUseSuggestion={editing}
                          onConfirm={(x) => decide("confirm", x)}
                          onAccept={(x) => decide("accept", x)}
                          onDismiss={(x, note) =>
                            decide(
                              x.status === "suggested"
                                ? "dismiss-suggestion"
                                : "dismiss",
                              x,
                              note,
                            )
                          }
                          onRemove={(x) =>
                            void send({ intent: "remove", id: x.id })
                          }
                          onComment={(x, body) =>
                            void send({ intent: "comment", id: x.id, body })
                          }
                          onUncomment={(commentId) =>
                            void send({ intent: "uncomment", id: commentId })
                          }
                        />
                      ))
                    )}
                  </section>
                </>
              )}
            </div>
          </aside>
        </>
      ) : null}
    </>
  );
}
