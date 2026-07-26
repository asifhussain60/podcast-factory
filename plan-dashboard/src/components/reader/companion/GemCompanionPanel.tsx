/**
 * GemCompanionPanel — the reader's "Ismaili Scholar Companion" side panel.
 *
 * Explains a concept — or the sentence you just selected — in the Ismaili Scholar
 * Gem's voice (POST /api/ai/gem-explain). Since 2026-07-26 it is the ONLY writer of
 * Companion notes: the hand-authored notes panel that used to sit beside it in the
 * Composer's drawer was retired with its floating button, so this panel holds its
 * own state and talks to the note store and the AI route directly.
 *
 * Two ways in, one answer surface:
 *   Explain          — type a term, get it explained. Ephemeral; nothing is stored.
 *   From selection   — select a sentence IN THE CHAPTER: the panel explains it AND
 *                      files the answer as a Companion note against that chapter,
 *                      with the selected sentence as the note's verbatim `quote`.
 *                      The LIVE Session (/studio/<slug>/live) then highlights that
 *                      sentence and raises this explanation as you reach it.
 *
 * Where the note lands is deliberately narrow: _system/companion-notes/<chapter>.json,
 * which the LIVE Session reads and NOTHING else does — never book.md, never the PDF.
 * Its chapter key comes from `sectionKeyFromHeading`, the same rule that produces the
 * LIVE Session's TOC ids, so a filed note is always one the reader looks up.
 *
 * Design decision (2026-07-17): a slide-in side panel, so the prose stays readable
 * alongside the answer. Follows TermPopover's fetch/stale-guard; all styling lives
 * in gem-companion.css using the shared --c-* tokens (no inline styles).
 */
import { useEffect, useRef, useState } from "react";
import { sectionKeyFromHeading } from "../../../lib/reader/companion/keys";
import { defaultStore } from "../../../lib/reader/companion/store.client";

interface Result {
  body: string;
  etymology: string | null;
}

/** A note this panel filed, kept only so it can be taken back off the reader. */
interface Saved {
  chapter: string;
  id: string;
  quote: string;
}

interface Props {
  slug: string;
  bookTitle: string;
  /** Selector for the reading-prose container the selection must live inside. */
  proseSelector?: string;
  /** Render INSIDE a host drawer instead of as its own fixed slide-in.
   *  The Book Composer runs one shared right drawer with three surfaces (Tools,
   *  Arabic, Scholar), so this panel drops its own launcher button and its own
   *  close button there — the host's floating buttons own both jobs, and two
   *  competing drawers on one page is the thing that consolidation removed. */
  docked?: boolean;
}

/** Split a model answer into paragraphs for readable rendering. */
function paragraphs(text: string): string[] {
  return text
    .split(/\n{2,}/)
    .map((p) => p.replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

/** The element a selection boundary sits in (a text node reports its parent). */
function elementOf(node: Node | null): HTMLElement | null {
  if (!node) return null;
  return node instanceof Element
    ? (node as HTMLElement)
    : (node.parentElement ?? null);
}

/**
 * The chapter a selection belongs to, as the LIVE Session keys it.
 *
 * Two markups to satisfy with one rule. The Book Composer wraps each chapter in
 * `.cx-chapter[data-anchor="## 2. A Stranger in the City"]`, so the raw heading is
 * right there. A plain reading page has no such wrapper — the chapter is whatever
 * `## ` heading precedes the selection — so fall back to the nearest heading above
 * it and use its slug id (rendered by the same rule) or its text.
 */
function chapterKeyFor(node: Node | null): string {
  const el = elementOf(node);
  if (!el) return "";
  const wrapper = el.closest<HTMLElement>("[data-anchor]");
  if (wrapper?.dataset.anchor)
    return sectionKeyFromHeading(wrapper.dataset.anchor);

  const headings = Array.from(document.querySelectorAll<HTMLElement>("h1, h2"));
  let found: HTMLElement | null = null;
  for (const h of headings) {
    const pos = h.compareDocumentPosition(el);
    if (pos & Node.DOCUMENT_POSITION_FOLLOWING)
      found = h; // heading precedes the selection
    else break;
  }
  if (!found) return "";
  return found.id || sectionKeyFromHeading(found.textContent ?? "");
}

/** A short card title for the filed note — the passage, not a paraphrase of it. */
function labelFor(text: string): string {
  return text.length <= 72 ? text : `${text.slice(0, 69).trimEnd()}…`;
}

export default function GemCompanionPanel({
  slug,
  bookTitle,
  proseSelector = ".bookv-body",
  docked = false,
}: Props) {
  const [open, setOpen] = useState(docked);
  const [input, setInput] = useState("");
  const [context, setContext] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);
  const [saved, setSaved] = useState<Saved | null>(null);

  // Monotonic request id: only the newest in-flight request may write results,
  // so a late response can never overwrite a newer one (mirrors TermPopover).
  const reqId = useRef(0);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const launcherRef = useRef<HTMLButtonElement>(null);
  const wasOpen = useRef(false);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
      wasOpen.current = true;
    } else if (wasOpen.current) {
      // Return focus to the launcher on close (never steal it on first mount).
      launcherRef.current?.focus();
    }
  }, [open]);

  /**
   * Read the live selection out of the chapter.
   *
   * The container test is `closest(proseSelector)` from the selection, NOT
   * `document.querySelector(proseSelector).contains(...)`: the Composer renders
   * every chapter as its own `.cx-chapter` and hides all but one, so the old test
   * asked whether the selection was inside the FIRST chapter and rejected a
   * perfectly good selection in every chapter after it.
   */
  function readSelection(): {
    text: string;
    context: string;
    chapter: string;
  } | null {
    if (typeof window === "undefined") return null;
    const sel = window.getSelection();
    // Selection.toString() reports the RENDERED selection and comes back empty
    // when the document isn't focused — so fall back to the range's own text,
    // which is the same string and always present.
    const raw =
      sel?.toString() || (sel?.rangeCount ? sel.getRangeAt(0).toString() : "");
    const text = raw.replace(/\s+/g, " ").trim();
    if (!text) {
      setHint(
        "Select a word or sentence in the chapter first, then try again.",
      );
      return null;
    }
    const anchorEl = elementOf(sel?.anchorNode ?? null);
    if (!anchorEl?.closest(proseSelector)) {
      setHint("Select text inside the chapter, not the panel.");
      return null;
    }
    const para = anchorEl.closest("p, li, blockquote");
    return {
      text,
      context: (para?.textContent || "")
        .replace(/\s+/g, " ")
        .trim()
        .slice(0, 600),
      chapter: chapterKeyFor(sel?.anchorNode ?? null),
    };
  }

  /** Explain `concept`; when `passage` is given, file the answer for the reader. */
  async function explain(
    concept: string,
    ctx: string,
    passage?: { text: string; chapter: string },
  ): Promise<void> {
    const id = ++reqId.current;
    setLoading(true);
    setError(null);
    setHint(null);
    setResult(null);
    setSaved(null);

    try {
      // Deliberately raw fetch (not apiFetch): the 429 branch reads `retryMs`
      // from the error body, which apiFetch discards when it throws (R1).
      const res = await fetch("/api/ai/gem-explain", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          concept,
          context: ctx || undefined,
          bookTitle,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (id !== reqId.current) return; // superseded by a newer request
      if (res.status === 429) {
        const secs = Math.ceil((data.retryMs ?? 5000) / 1000);
        throw new Error(`The Companion is busy — try again in about ${secs}s.`);
      }
      if (!res.ok || !data.ok) {
        throw new Error(
          typeof data.error === "string"
            ? data.error
            : `Request failed (${res.status}).`,
        );
      }
      const answer: Result = {
        body: String(data.body ?? ""),
        etymology: data.etymology ?? null,
      };
      setResult(answer);
      if (passage) await file(answer, passage, id);
    } catch (e) {
      if (id !== reqId.current) return;
      setError((e as Error).message);
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  }

  /** Persist one explanation as a Companion note against its chapter. */
  async function file(
    answer: Result,
    passage: { text: string; chapter: string },
    id: number,
  ): Promise<void> {
    if (!passage.chapter) {
      setHint(
        "Explained, but not filed — I could not tell which chapter that selection is in.",
      );
      return;
    }
    // The etymology rides along in the note body: the LIVE Session's card is one
    // block of prose, so an answer split across two fields would lose half of itself.
    const body = answer.etymology
      ? `${answer.body}\n\nEtymology. ${answer.etymology}`
      : answer.body;
    try {
      const note = await defaultStore.upsert(slug, passage.chapter, {
        kind: "explanation",
        body,
        anchor: labelFor(passage.text),
        quote: passage.text,
        source: { provider: "scholar", label: "Ismaili Scholar" },
      });
      if (id !== reqId.current) return;
      setSaved({ chapter: passage.chapter, id: note.id, quote: passage.text });
    } catch (e) {
      if (id !== reqId.current) return;
      setHint(`Explained, but not filed: ${(e as Error).message}`);
    }
  }

  async function undoSave(): Promise<void> {
    if (!saved) return;
    const target = saved;
    setSaved(null);
    try {
      await defaultStore.remove(slug, target.chapter, target.id);
      setHint("Removed from the LIVE Session.");
    } catch (e) {
      setSaved(target);
      setError(`Could not remove it: ${(e as Error).message}`);
    }
  }

  function submit(): void {
    const value = input.trim();
    if (!value) {
      setHint("Enter or select a concept to explain.");
      return;
    }
    void explain(value, context);
  }

  function fromSelection(): void {
    const picked = readSelection();
    if (!picked) return;
    setInput(picked.text);
    setContext(picked.context);
    void explain(picked.text, picked.context, {
      text: picked.text,
      chapter: picked.chapter,
    });
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      submit();
    }
  }

  if (!open && !docked) {
    return (
      <button
        type="button"
        className="gcp-launcher"
        ref={launcherRef}
        onClick={() => setOpen(true)}
        aria-label="Ismaili Scholar Companion"
        title="Ismaili Scholar Companion"
      >
        <i className="fa-solid fa-book-open-reader" aria-hidden="true" />
      </button>
    );
  }

  return (
    <aside
      className={docked ? "gcp gcp--docked" : "gcp"}
      role="complementary"
      aria-label="Ismaili Scholar Companion"
      onKeyDown={(e) => {
        if (e.key === "Escape" && !docked) setOpen(false);
      }}
    >
      <div className="gcp-head">
        <h2 className="gcp-title">Ismaili Scholar Companion</h2>
        {!docked && (
          <button
            type="button"
            className="gcp-close"
            aria-label="Close Companion"
            onClick={() => setOpen(false)}
          >
            <i className="fa-solid fa-xmark" aria-hidden="true" />
          </button>
        )}
      </div>

      <label className="gcp-label" htmlFor="gcp-input">
        Concept to explain
      </label>
      <textarea
        id="gcp-input"
        ref={inputRef}
        className="gcp-input"
        rows={2}
        placeholder="e.g. wilayah — or select a sentence in the chapter and use “From selection”."
        value={input}
        onChange={(e) => setInput(e.currentTarget.value)}
        onKeyDown={onKeyDown}
      />

      <div className="gcp-actions">
        <button
          type="button"
          className="gcp-btn gcp-btn--primary"
          onClick={submit}
          disabled={loading}
        >
          {loading ? "Thinking…" : "Explain"}
        </button>
        <button
          type="button"
          className="gcp-btn gcp-btn--ghost"
          onClick={fromSelection}
          disabled={loading}
          title="Explain the selected sentence and show it in the LIVE Session"
        >
          <i className="fa-solid fa-highlighter" aria-hidden="true" /> From
          selection
        </button>
      </div>

      {context && (
        <p className="gcp-context" title={context}>
          <i className="fa-solid fa-quote-left" aria-hidden="true" /> Grounding
          in the selected passage.
        </p>
      )}
      {hint && <p className="gcp-hint">{hint}</p>}
      {error && (
        <p className="gcp-error" role="alert">
          {error}
        </p>
      )}

      {saved && (
        <p className="gcp-saved" role="status">
          <i className="fa-solid fa-circle-check" aria-hidden="true" /> Added to
          the LIVE Session — this passage will be highlighted there, with this
          explanation beside it.
          <button
            type="button"
            className="gcp-undo"
            onClick={() => void undoSave()}
          >
            Undo
          </button>
        </p>
      )}

      {loading && !result && (
        <div className="gcp-result gcp-result--loading" aria-busy="true">
          <span className="gcp-skel" />
          <span className="gcp-skel" />
          <span className="gcp-skel gcp-skel--short" />
        </div>
      )}

      {result && (
        <div className="gcp-result">
          {paragraphs(result.body).map((p, i) => (
            <p key={i}>{p}</p>
          ))}
          {result.etymology && (
            <p className="gcp-etym">
              <span className="gcp-etym-label">Etymology.</span>{" "}
              {result.etymology}
            </p>
          )}
          <p className="gcp-disclaimer">
            Generated by AI in a scholarly persona. Verify against the source;
            AI can make mistakes.
          </p>
        </div>
      )}
    </aside>
  );
}
