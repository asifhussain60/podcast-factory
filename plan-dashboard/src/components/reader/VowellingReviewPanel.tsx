/**
 * VowellingReviewPanel — human review of proposed Arabic diacritics.
 *
 * The model proposes; this is where a human decides. Nothing reaches `book.md`
 * until it is accepted here, and applying goes through the Composer's own chapter
 * writer, so an accepted mark lands in `composer-edits.json` and survives the next
 * compose like any other Composer edit.
 *
 * The panel is built around what a reviewer actually has to judge. Vocalisation is
 * not a spelling question — on an Arabic verb it decides voice, and this book is
 * largely reported speech, so `لم يخلق` reads as "he did not create" or "it was not
 * created" depending on marks the source does not supply. Each row therefore shows
 * the SOURCE line above the proposal rather than a diff: the reviewer needs to see
 * the bare consonants they are being asked to fix a reading onto. The proposal is
 * editable in place, and a hand-edit is put through the same skeleton gate the
 * model's answer went through — so the letters stay the source's whoever typed last.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { mountPanelTextSize } from "../../scripts/panel-text-size";

/** Asks the host page to open a chapter. The Composer listens; nothing else has
 *  to know this panel exists, and the panel needs no handle on the page's own
 *  chapter picker. Keyed by the anchorKey both sides already agree on — the
 *  proposal's `chapter_key` and the Composer's chapter `key` are the same
 *  string, both derived from the chapter heading in book.md. */
export const GOTO_CHAPTER_EVENT = "pf:goto-chapter";

interface Proposal {
  id: string;
  chapter_key: string;
  chapter_title: string;
  source: string;
  proposed: string;
  resolved: string;
  status: "pending" | "accepted" | "rejected" | "applied";
  marks_added: number;
  note: string;
}

interface State {
  proposals: Proposal[];
  candidates: number;
  unproposed: number;
}

async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  const json = await res.json();
  if (!res.ok || json?.ok === false)
    throw new Error(json?.error ?? `Request failed (${res.status})`);
  return (json?.data ?? json) as T;
}

export default function VowellingReviewPanel({
  slug,
  docked,
}: {
  slug: string;
  /** Rendered inside the Book Composer's drawer rather than standing alone. The
   *  drawer supplies the frame AND the text-size stepper, so this panel drops
   *  both — a second stepper for the same stored preference, sitting a few
   *  centimetres below the first, is a control that can only ever agree with the
   *  one above it. Same "the host already decided" reasoning as CompanionPanel's
   *  chapter name and float toggle. */
  docked?: boolean;
}) {
  // The stepper is this panel's own ONLY when it stands alone; docked, it
  // inherits --panel-fs from the drawer that declares it.
  const rootRef = useRef<HTMLElement>(null);
  const sizeRef = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<State | null>(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [refused, setRefused] = useState<{ source: string; reason: string }[]>(
    [],
  );
  const [drafts, setDrafts] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    try {
      setState(await api<State>(`/api/studio/vowelling?slug=${slug}`));
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [slug]);

  useEffect(() => {
    void load();
  }, [load]);

  // Mount the stepper once the LOADED panel has rendered. Keyed on `state`
  // because the first render returns the "Loading…" shell, which carries neither
  // ref — an effect with an empty dep list ran against two nulls and silently did
  // nothing, leaving an empty bar. Disposing on cleanup keeps the module's
  // broadcast registry free of detached nodes across re-renders.
  useEffect(() => {
    if (docked || !state || !sizeRef.current || !rootRef.current) return;
    return mountPanelTextSize(sizeRef.current, rootRef.current);
  }, [state, docked]);

  const post = useCallback(
    async (body: Record<string, unknown>, label: string) => {
      setBusy(label);
      setError(null);
      try {
        const out = await api<{
          refused?: { source: string; reason: string }[];
        }>("/api/studio/vowelling", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slug, ...body }),
        });
        if (out?.refused) setRefused(out.refused);
        await load();
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy("");
      }
    },
    [slug, load],
  );

  if (error && !state)
    return (
      <aside
        className={`vrp${docked ? " vrp--docked" : ""}`}
        aria-label="Arabic vowelling review"
      >
        <p className="vrp-error" role="alert">
          {error}
        </p>
      </aside>
    );
  if (!state)
    return (
      <aside
        className={`vrp${docked ? " vrp--docked" : ""}`}
        aria-label="Arabic vowelling review"
      >
        <p className="vrp-empty">Loading…</p>
      </aside>
    );

  const pending = state.proposals.filter((p) => p.status === "pending");
  const accepted = state.proposals.filter((p) => p.status === "accepted");
  const applied = state.proposals.filter((p) => p.status === "applied");

  return (
    <aside
      className={`vrp${docked ? " vrp--docked" : ""}`}
      aria-label="Arabic vowelling review"
      ref={rootRef}
    >
      {!docked && <div className="cx-panel-bar" ref={sizeRef} />}
      <header className="vrp-head">
        <h2 className="vrp-title">Vowelling</h2>
        <p className="vrp-lede">
          The printed source is a bare text, so these marks are supplied, not
          recovered. Nothing reaches the book until you accept it — and an
          accepted reading is yours, not the model&rsquo;s.
        </p>
      </header>

      <p className="vrp-counts">
        {state.candidates} passages · {pending.length} to review ·{" "}
        {accepted.length} accepted · {applied.length} in the book
      </p>

      <div className="vrp-actions">
        <button
          type="button"
          className="vrp-btn"
          disabled={!!busy || state.unproposed === 0}
          onClick={() => void post({ action: "propose", limit: 8 }, "propose")}
        >
          {busy === "propose"
            ? "Proposing…"
            : `Propose next ${Math.min(8, state.unproposed)}`}
        </button>
        <button
          type="button"
          className="vrp-btn vrp-btn--primary"
          disabled={!!busy || accepted.length === 0}
          onClick={() => void post({ action: "apply" }, "apply")}
        >
          {busy === "apply"
            ? "Applying…"
            : `Apply ${accepted.length} to the book`}
        </button>
      </div>

      {error && (
        <p className="vrp-error" role="alert">
          {error}
        </p>
      )}

      {refused.length > 0 && (
        <div className="vrp-refused">
          <h3 className="vrp-sub">
            Refused by the skeleton check ({refused.length})
          </h3>
          {/* Surfaced rather than swallowed: a passage the model keeps failing on
              is a passage worth looking at yourself. */}
          <ul>
            {refused.map((r, i) => (
              <li key={i}>
                <span className="vrp-ar" dir="rtl" lang="ar">
                  {r.source.slice(0, 60)}
                </span>
                <span className="vrp-reason">{r.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {state.proposals.length === 0 && (
        <p className="vrp-empty">
          No proposals yet. {state.candidates} passages are eligible —
          Qur&rsquo;anic runs are excluded because they are already vowelled
          from the canonical mushaf.
        </p>
      )}

      <ul className="vrp-list">
        {state.proposals.map((p) => (
          <li key={p.id} className="vrp-row" data-status={p.status}>
            {/* Docked, the chapter name is the way TO that chapter. This panel
                lists the whole book while the Composer shows one chapter, which
                is the one thing the retired review page did better — you could
                see every passage and the prose around it at once. Making the
                label a jump gives that back: work down the list and the chapter
                beside you follows. Standalone it stays plain text, because there
                is no chapter picker on that page to drive. */}
            {docked ? (
              <button
                type="button"
                className="vrp-chapter vrp-chapter--jump"
                title={`Open “${p.chapter_title}” in the Composer`}
                onClick={() =>
                  window.dispatchEvent(
                    new CustomEvent(GOTO_CHAPTER_EVENT, {
                      detail: { key: p.chapter_key },
                    }),
                  )
                }
              >
                {p.chapter_title}
              </button>
            ) : (
              <p className="vrp-chapter">{p.chapter_title}</p>
            )}
            <p className="vrp-ar vrp-ar--source" dir="rtl" lang="ar">
              {p.source}
            </p>
            <label className="vrp-field-label" htmlFor={`v-${p.id}`}>
              Proposed reading (+{p.marks_added} marks)
            </label>
            <textarea
              id={`v-${p.id}`}
              className="vrp-ar vrp-input"
              dir="rtl"
              lang="ar"
              rows={2}
              readOnly={p.status === "applied"}
              value={drafts[p.id] ?? p.resolved}
              onChange={(e) =>
                setDrafts({ ...drafts, [p.id]: e.currentTarget.value })
              }
            />
            <div className="vrp-row-actions">
              <button
                type="button"
                className="vrp-act"
                disabled={!!busy || p.status === "applied"}
                aria-pressed={p.status === "accepted"}
                onClick={() =>
                  void post(
                    {
                      action: "decide",
                      id: p.id,
                      status: "accepted",
                      resolved: drafts[p.id] ?? p.resolved,
                    },
                    p.id,
                  )
                }
              >
                Accept
              </button>
              <button
                type="button"
                className="vrp-act"
                disabled={!!busy || p.status === "applied"}
                aria-pressed={p.status === "rejected"}
                onClick={() =>
                  void post(
                    { action: "decide", id: p.id, status: "rejected" },
                    p.id,
                  )
                }
              >
                Reject
              </button>
              <span className="vrp-status">{p.status}</span>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
