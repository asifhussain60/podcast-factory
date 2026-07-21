/**
 * CompanionPanel — the private, reader-only Companion notes surface.
 *
 * Loose coupling by construction:
 *   - Talks only to a CompanionStore (default: API-backed) — swap persistence
 *     without touching this file.
 *   - `layout` flips docked (in-flow column) ↔ floating (fixed drawer) via ONE prop
 *     and one CSS modifier class; the toggle here just persists that choice.
 *   - Note kinds and source providers come from the registry, so this component
 *     never hard-codes the set of note types.
 *
 * It is never part of book.md or the PDF — it is a client island the reader mounts.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import CompanionCard from "./CompanionCard";
import {
  mountPassageSync,
  revealPassage,
  scrollAncestor,
} from "../../../lib/reader/companion/passage-sync";
import {
  KIND_DEFS,
  DEFAULT_KIND,
  SOURCE_PROVIDERS,
} from "../../../lib/reader/companion/registry";
import {
  defaultStore,
  type CompanionStore,
} from "../../../lib/reader/companion/store.client";
import type { CompanionNote } from "../../../lib/reader/companion/types";

export interface ChapterRef {
  key: string;
  title: string;
}

interface Props {
  slug: string;
  chapters: ChapterRef[];
  initialChapter?: string;
  /** CONTROLLED chapter. When a host already decides which chapter is on screen
   *  (the Book Composer does — its own Chapter dropdown), pass it here: the panel
   *  follows it and renders the chapter's NAME instead of a second dropdown.
   *  Standalone reader use omits it and keeps the picker, which is the only way
   *  to navigate chapters there. */
  chapter?: string;
  layout?: LayoutMode;
  store?: CompanionStore;
  /** CSS selector for the reading-prose container a captured passage must come from. */
  proseSelector?: string;
}

type LayoutMode = "docked" | "floating";

const LAYOUT_KEY = "pf-companion:layout";
const PRESENT_KEY = "pf-companion:present";
/** Exported so callers that re-mount this panel on a chapter change (e.g. the
 * Book Composer's imperatively-mounted Companion tab) can pre-seed the
 * remembered chapter — otherwise a stale localStorage value would win over a
 * fresh `initialChapter` prop on the next mount (see chapter-switch logic in
 * ../../../scripts/book-composer.ts). */
export const chapterKeyFor = (slug: string) => `pf-companion:chapter:${slug}`;

interface Draft {
  id?: string;
  kind: string;
  body: string;
  anchor: string;
  quote: string;
  provider: string;
  ref: string;
  locator: string;
}

const EMPTY_DRAFT: Draft = {
  kind: DEFAULT_KIND,
  body: "",
  anchor: "",
  quote: "",
  provider: "manual",
  ref: "",
  locator: "",
};

function readPref(key: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  return window.localStorage.getItem(key) ?? fallback;
}

export default function CompanionPanel({
  slug,
  chapters,
  initialChapter,
  chapter: controlledChapter,
  layout,
  store,
  proseSelector = ".bookv-body",
}: Props) {
  const st = store ?? defaultStore;
  const validKeys = new Set(chapters.map((c) => c.key));
  const remembered = readPref(chapterKeyFor(slug), "");
  const isControlled = controlledChapter !== undefined;
  const [uncontrolledChapter, setChapterState] = useState(
    (remembered && validKeys.has(remembered) && remembered) ||
      initialChapter ||
      chapters[0]?.key ||
      "general",
  );
  // A controlled host wins outright — including over the remembered value, which
  // is what used to force the Composer to unmount and remount this panel on every
  // chapter switch just to stop stale notes showing.
  const chapter = isControlled ? controlledChapter : uncontrolledChapter;

  const setChapter = useCallback(
    (next: string) => {
      setChapterState(next);
      if (typeof window !== "undefined")
        window.localStorage.setItem(chapterKeyFor(slug), next);
    },
    [slug],
  );
  const [notes, setNotes] = useState<CompanionNote[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [captureHint, setCaptureHint] = useState<{
    msg: string;
    ok: boolean;
  } | null>(null);
  const [mode, setMode] = useState<LayoutMode>(
    layout ?? (readPref(LAYOUT_KEY, "docked") as LayoutMode),
  );
  const [present, setPresent] = useState(readPref(PRESENT_KEY, "0") === "1");
  const [open, setOpen] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const doc = await st.read(slug, chapter);
      setNotes(doc.notes);
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    } finally {
      setLoading(false);
    }
  }, [st, slug, chapter]);

  useEffect(() => {
    void load();
  }, [load]);

  // ── the link between a card and the sentence it annotates ──────────────────
  // Marking the passages has to wait for the notes, and `loading` is what says
  // they have arrived: an effect with `[]` deps here would run against the first
  // render, which is the "Loading…" shell with no notes and (in the Composer) a
  // chapter that has not been shown yet, and silently mark nothing.
  const [activeNote, setActiveNote] = useState<string | null>(null);
  const [marked, setMarked] = useState<Set<string>>(new Set());
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (loading) return;
    return mountPassageSync({
      proseSelector,
      notes: notes.map((n) => ({ id: n.id, quote: n.quote })),
      onActive: setActiveNote,
      onMarked: (ids) => setMarked(new Set(ids)),
    });
  }, [notes, loading, proseSelector]);

  // Raise the live card to the top of the panel. Scrolls the panel's OWN
  // scroller by an offset rather than calling scrollIntoView, which would also
  // scroll the window — and the window is the chapter the reader is reading.
  useEffect(() => {
    if (!activeNote) return;
    const card = listRef.current?.querySelector<HTMLElement>(
      `[data-note-id="${CSS.escape(activeNote)}"]`,
    );
    if (!card) return;
    const scroller = scrollAncestor(card);
    if (!scroller) return;
    const delta =
      card.getBoundingClientRect().top -
      scroller.getBoundingClientRect().top -
      8;
    if (Math.abs(delta) < 2) return;
    const reduce = window.matchMedia?.(
      "(prefers-reduced-motion: reduce)",
    )?.matches;
    scroller.scrollTo({
      top: scroller.scrollTop + delta,
      behavior: reduce ? "auto" : "smooth",
    });
  }, [activeNote]);

  function persistLayout(next: LayoutMode) {
    setMode(next);
    if (typeof window !== "undefined")
      window.localStorage.setItem(LAYOUT_KEY, next);
  }
  function persistPresent(next: boolean) {
    setPresent(next);
    if (typeof window !== "undefined")
      window.localStorage.setItem(PRESENT_KEY, next ? "1" : "0");
  }

  function startNew() {
    setCaptureHint(null);
    setDraft({ ...EMPTY_DRAFT });
  }
  function startEdit(note: CompanionNote) {
    setCaptureHint(null);
    setDraft({
      id: note.id,
      kind: note.kind,
      body: note.body,
      anchor: note.anchor ?? "",
      quote: note.quote ?? "",
      provider: note.source?.provider ?? "manual",
      ref: note.source?.ref ?? "",
      locator: note.source?.locator ?? "",
    });
  }
  function cancelDraft() {
    setCaptureHint(null);
    setDraft(null);
  }

  // Capture the reader's current text selection as the note's verbatim passage.
  // Fired from the button's onClick so it works for BOTH mouse and keyboard
  // (Enter/Space synthesize a click); a bare onMouseDown preventDefault keeps a
  // mouse press from collapsing the selection before the click reads it.
  function captureSelection() {
    if (typeof window === "undefined") return;
    const sel = window.getSelection();
    const text = (sel ? sel.toString() : "").replace(/\s+/g, " ").trim();
    if (!text) {
      setCaptureHint({
        msg: "Select a sentence in the chapter first, then Capture.",
        ok: false,
      });
      return;
    }
    const container = document.querySelector(proseSelector);
    const anchorNode = sel?.anchorNode ?? null;
    if (container && anchorNode && !container.contains(anchorNode)) {
      setCaptureHint({
        msg: "Select text inside the chapter, not the panel.",
        ok: false,
      });
      return;
    }
    setDraft((d) => (d ? { ...d, quote: text } : d));
    setCaptureHint({
      msg: "Passage captured — it will highlight in the reader.",
      ok: true,
    });
  }

  async function saveDraft() {
    if (!draft || !draft.body.trim()) return;
    const source =
      draft.provider === "manual" && !draft.ref && !draft.locator
        ? { provider: "manual" }
        : {
            provider: draft.provider,
            ref: draft.ref || undefined,
            locator: draft.locator || undefined,
          };
    try {
      await st.upsert(slug, chapter, {
        id: draft.id,
        kind: draft.kind,
        body: draft.body,
        anchor: draft.anchor || undefined,
        quote: draft.quote.trim() || undefined,
        source,
      });
      setCaptureHint(null);
      setDraft(null);
      await load();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    }
  }

  async function removeNote(note: CompanionNote) {
    try {
      await st.remove(slug, chapter, note.id);
      await load();
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    }
  }

  const rootClass = `cpn cpn--${mode}${present ? " cpn--present" : ""}${open ? "" : " cpn--collapsed"}`;

  if (mode === "floating" && !open) {
    return (
      <button
        type="button"
        className="cpn-launcher"
        onClick={() => setOpen(true)}
      >
        <i className="fa-solid fa-book-open-reader" aria-hidden="true" />{" "}
        Companion
      </button>
    );
  }

  return (
    <aside className={rootClass} aria-label="Companion notes (private)">
      <header className="cpn-head">
        <div className="cpn-head-title">
          <i className="fa-solid fa-lock" aria-hidden="true" />
          <span>Companion</span>
          <span className="cpn-private">private</span>
        </div>
        <div className="cpn-head-tools">
          <button
            type="button"
            className="cpn-icon-btn"
            aria-pressed={present}
            aria-label={
              present ? "Exit present mode" : "Present mode (hide editing)"
            }
            onClick={() => persistPresent(!present)}
          >
            <i
              className={present ? "fa-solid fa-eye" : "fa-solid fa-eye-slash"}
              aria-hidden="true"
            />
          </button>
          {/* Only when the layout is the PANEL'S OWN to choose. A host that
              passes `layout` has placed this panel inside a container of its own
              — the Composer docks it in `.cx-surface` — and floating it there
              makes it `position: fixed` while its node stays in a container that
              gets `display: none` the moment you switch drawer surfaces. The
              panel would vanish with its own un-float button inside it. Same
              reasoning as the chapter dropdown below: a control for something
              the host already decided can only disagree with the host. */}
          {layout === undefined && (
            <button
              type="button"
              className="cpn-icon-btn"
              aria-label={mode === "docked" ? "Float panel" : "Dock panel"}
              onClick={() =>
                persistLayout(mode === "docked" ? "floating" : "docked")
              }
            >
              <i
                className={
                  mode === "docked"
                    ? "fa-solid fa-up-right-from-square"
                    : "fa-solid fa-down-left-and-up-right-to-center"
                }
                aria-hidden="true"
              />
            </button>
          )}
          {mode === "floating" && (
            <button
              type="button"
              className="cpn-icon-btn"
              aria-label="Close panel"
              onClick={() => setOpen(false)}
            >
              <i className="fa-solid fa-xmark" aria-hidden="true" />
            </button>
          )}
        </div>
      </header>

      {chapters.length > 0 &&
        (isControlled ? (
          /* The host already shows a Chapter dropdown; a second one for the same
             thing is redundant and can only ever disagree with it. Name the
             chapter instead, so it is still clear whose notes these are. */
          <p className="cpn-chapter cpn-chapter-name">
            <span className="cpn-field-label">Chapter</span>
            <span className="cpn-chapter-title">
              {chapters.find((c) => c.key === chapter)?.title ?? chapter}
            </span>
          </p>
        ) : (
          <div className="cpn-chapter">
            <label className="cpn-field-label" htmlFor="cpn-chapter-select">
              Chapter
            </label>
            <select
              id="cpn-chapter-select"
              className="cpn-select"
              value={chapter}
              onChange={(e) => setChapter(e.target.value)}
            >
              {chapters.map((c) => (
                <option key={c.key} value={c.key}>
                  {c.title}
                </option>
              ))}
            </select>
          </div>
        ))}

      {error && (
        <p className="cpn-error" role="alert">
          {error}
        </p>
      )}

      <div className="cpn-list" ref={listRef}>
        {loading && <p className="cpn-empty">Loading…</p>}
        {!loading && notes.length === 0 && (
          <p className="cpn-empty">No notes for this chapter yet.</p>
        )}
        {!loading &&
          notes.map((n) => (
            <CompanionCard
              key={n.id}
              note={n}
              readOnly={present}
              active={n.id === activeNote}
              onEdit={startEdit}
              onDelete={removeNote}
              onReveal={
                marked.has(n.id) ? () => revealPassage(n.id) : undefined
              }
            />
          ))}
      </div>

      {!present && !draft && (
        <button type="button" className="cpn-add" onClick={startNew}>
          <i className="fa-solid fa-plus" aria-hidden="true" /> Add note
        </button>
      )}

      {!present && draft && (
        <form
          className="cpn-composer"
          onSubmit={(e) => {
            e.preventDefault();
            void saveDraft();
          }}
        >
          <div className="cpn-composer-row">
            <label className="cpn-field-label" htmlFor="cpn-kind">
              Kind
            </label>
            <select
              id="cpn-kind"
              className="cpn-select"
              value={draft.kind}
              onChange={(e) => setDraft({ ...draft, kind: e.target.value })}
            >
              {KIND_DEFS.map((k) => (
                <option key={k.id} value={k.id}>
                  {k.label}
                </option>
              ))}
            </select>
          </div>

          <label className="cpn-field-label" htmlFor="cpn-anchor">
            Card title
          </label>
          <input
            id="cpn-anchor"
            className="cpn-input"
            value={draft.anchor}
            placeholder="Short label, e.g. milk before meat"
            onChange={(e) => setDraft({ ...draft, anchor: e.target.value })}
          />

          <label className="cpn-field-label" htmlFor="cpn-quote">
            Highlighted passage
          </label>
          <div className="cpn-capture-row">
            <input
              id="cpn-quote"
              className="cpn-input"
              value={draft.quote}
              placeholder="Select a sentence in the chapter, then Capture"
              onChange={(e) => setDraft({ ...draft, quote: e.target.value })}
            />
            <button
              type="button"
              className="cpn-btn"
              aria-label="Capture the selected passage"
              onMouseDown={(e) => e.preventDefault()}
              onClick={captureSelection}
            >
              <i className="fa-solid fa-highlighter" aria-hidden="true" />{" "}
              Capture
            </button>
          </div>
          {captureHint && (
            <p
              className={`cpn-hint${captureHint.ok ? " cpn-hint--ok" : ""}`}
              role="status"
              aria-live="polite"
            >
              {captureHint.msg}
            </p>
          )}

          <label className="cpn-field-label" htmlFor="cpn-body">
            Note
          </label>
          <textarea
            id="cpn-body"
            className="cpn-textarea"
            value={draft.body}
            rows={4}
            placeholder="The explanation or analogy you'd say out loud"
            onChange={(e) => setDraft({ ...draft, body: e.target.value })}
          />

          <div className="cpn-composer-row">
            <label className="cpn-field-label" htmlFor="cpn-provider">
              Source
            </label>
            <select
              id="cpn-provider"
              className="cpn-select"
              value={draft.provider}
              onChange={(e) => setDraft({ ...draft, provider: e.target.value })}
            >
              {SOURCE_PROVIDERS.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>

          {draft.provider !== "manual" && (
            <div className="cpn-composer-row cpn-composer-row--split">
              <input
                className="cpn-input"
                value={draft.ref}
                placeholder="Ref (e.g. EP05)"
                aria-label="Source reference"
                onChange={(e) => setDraft({ ...draft, ref: e.target.value })}
              />
              <input
                className="cpn-input"
                value={draft.locator}
                placeholder="At (e.g. 04:12)"
                aria-label="Source locator"
                onChange={(e) =>
                  setDraft({ ...draft, locator: e.target.value })
                }
              />
            </div>
          )}

          <div className="cpn-composer-actions">
            <button
              type="submit"
              className="cpn-btn cpn-btn--primary"
              disabled={!draft.body.trim()}
            >
              {draft.id ? "Save" : "Add"}
            </button>
            <button type="button" className="cpn-btn" onClick={cancelDraft}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <p className="cpn-foot">
        <i className="fa-solid fa-file-circle-xmark" aria-hidden="true" />{" "}
        Private to you · never in the PDF
      </p>
    </aside>
  );
}
