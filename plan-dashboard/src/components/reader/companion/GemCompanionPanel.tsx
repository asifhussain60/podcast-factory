/**
 * GemCompanionPanel — the reader's AI "Companion" side panel.
 *
 * A slide-in drawer (right dock) that keeps the book visible beside it and lets a
 * reader either EXPLAIN a concept (POST /api/ai/gem-explain) or ASK a question
 * (POST /api/ai/gem-answer) in the Ismaili Scholar Gem's voice. Ephemeral AI
 * generation — distinct from the sibling CompanionPanel (manual, persisted notes),
 * so it holds its own state and calls the AI routes directly (no CompanionStore).
 *
 * Design decision (2026-07-17): a slide-in side panel, so the prose stays readable
 * alongside the answer. Mirrors the notes-panel drawer shell (companion-notes.css)
 * and TermPopover's fetch/stale-guard; all styling lives in gem-companion.css using
 * the shared --c-* tokens (no inline styles).
 */
import { useEffect, useRef, useState } from "react";

type Mode = "explain" | "ask";

interface Result {
  body: string;
  etymology: string | null;
}

interface Props {
  slug: string;
  bookTitle: string;
  /** Selector for the reading-prose container the selection must live inside. */
  proseSelector?: string;
  /** Render INSIDE a host drawer instead of as its own fixed slide-in.
   *  The Book Composer runs one shared right drawer with three surfaces (Tools,
   *  Companion notes, Scholar), so this panel drops its own launcher button and
   *  its own close button there — the host's floating buttons own both jobs, and
   *  two competing drawers on one page is the thing that consolidation removed. */
  docked?: boolean;
}

/** Split a model answer into paragraphs for readable rendering. */
function paragraphs(text: string): string[] {
  return text
    .split(/\n{2,}/)
    .map((p) => p.replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

export default function GemCompanionPanel({
  slug,
  bookTitle,
  proseSelector = ".bookv-body",
  docked = false,
}: Props) {
  void slug; // reserved for future per-book gem selection / caching
  const [open, setOpen] = useState(docked);
  const [mode, setMode] = useState<Mode>("explain");
  const [input, setInput] = useState("");
  const [context, setContext] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<string | null>(null);

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
  }, [open, mode]);

  function useSelection() {
    if (typeof window === "undefined") return;
    const sel = window.getSelection();
    const text = (sel ? sel.toString() : "").replace(/\s+/g, " ").trim();
    if (!text) {
      setHint("Select a word or phrase in the chapter first, then try again.");
      return;
    }
    const container = document.querySelector(proseSelector);
    const anchorNode = sel?.anchorNode ?? null;
    if (container && anchorNode && !container.contains(anchorNode)) {
      setHint("Select text inside the chapter, not the panel.");
      return;
    }
    const para =
      anchorNode instanceof Node
        ? (anchorNode.parentElement?.closest("p, li, blockquote") ?? null)
        : null;
    setInput(text);
    setContext(
      (para?.textContent || "").replace(/\s+/g, " ").trim().slice(0, 600),
    );
    setHint(null);
  }

  async function submit() {
    const value = input.trim();
    if (!value) {
      setHint(
        mode === "explain"
          ? "Enter or select a concept to explain."
          : "Enter a question to ask.",
      );
      return;
    }
    const id = ++reqId.current;
    setLoading(true);
    setError(null);
    setHint(null);
    setResult(null);

    const endpoint =
      mode === "explain" ? "/api/ai/gem-explain" : "/api/ai/gem-answer";
    const payload =
      mode === "explain"
        ? { concept: value, context: context || undefined, bookTitle }
        : { question: value, context: context || undefined, bookTitle };

    try {
      // Deliberately raw fetch (not apiFetch): the 429 branch reads `retryMs`
      // from the error body, which apiFetch discards when it throws (R1).
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
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
      setResult({
        body: String(data.body ?? ""),
        etymology: data.etymology ?? null,
      });
    } catch (e) {
      if (id !== reqId.current) return;
      setError((e as Error).message);
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void submit();
    }
  }

  if (!open && !docked) {
    return (
      <button
        type="button"
        className="gcp-launcher"
        ref={launcherRef}
        onClick={() => setOpen(true)}
        aria-label="Ask the Scholar"
        title="Ask the Scholar"
      >
        <i className="fa-solid fa-book-open-reader" aria-hidden="true" />
      </button>
    );
  }

  return (
    <aside
      className={docked ? "gcp gcp--docked" : "gcp"}
      role="complementary"
      aria-label="AI Companion — Ismaili Scholar"
      onKeyDown={(e) => {
        if (e.key === "Escape" && !docked) setOpen(false);
      }}
    >
      <div className="gcp-head">
        <div>
          <p className="gcp-eyebrow">AI Companion</p>
          <h2 className="gcp-title">Ismaili Scholar</h2>
        </div>
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

      <div className="gcp-modes" role="group" aria-label="Companion mode">
        <button
          type="button"
          aria-pressed={mode === "explain"}
          className="gcp-mode"
          data-active={mode === "explain"}
          onClick={() => setMode("explain")}
        >
          Explain a concept
        </button>
        <button
          type="button"
          aria-pressed={mode === "ask"}
          className="gcp-mode"
          data-active={mode === "ask"}
          onClick={() => setMode("ask")}
        >
          Ask a question
        </button>
      </div>

      <label className="gcp-label" htmlFor="gcp-input">
        {mode === "explain" ? "Concept to explain" : "Your question"}
      </label>
      <textarea
        id="gcp-input"
        ref={inputRef}
        className="gcp-input"
        rows={mode === "explain" ? 2 : 3}
        placeholder={
          mode === "explain"
            ? "e.g. wilayah — or select it in the text and use “From selection”."
            : "e.g. How does this chapter define the role of the Imam?"
        }
        value={input}
        onChange={(e) => setInput(e.currentTarget.value)}
        onKeyDown={onKeyDown}
      />

      <div className="gcp-actions">
        <button
          type="button"
          className="gcp-btn gcp-btn--ghost"
          onClick={useSelection}
        >
          <i className="fa-solid fa-highlighter" aria-hidden="true" /> From
          selection
        </button>
        <button
          type="button"
          className="gcp-btn gcp-btn--primary"
          onClick={() => void submit()}
          disabled={loading}
        >
          {loading ? "Thinking…" : mode === "explain" ? "Explain" : "Ask"}
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
