import { lazy, Suspense, useEffect, useState, type ReactNode } from "react";

import { renderNote } from "~/lib/richNote";

export interface RichNoteEditorProps {
  /**
   * What the editor STARTS with. Read once, at mount — this is an uncontrolled
   * editor, the same contract a native `<textarea defaultValue>` has, not a
   * React-controlled `value`. ProseMirror owns keystroke-by-keystroke state
   * internally; forcing external content back in on every parent re-render
   * (the naive "controlled" wiring) fights the cursor. A caller that needs to
   * point this editor at a DIFFERENT note entirely should remount it (a `key`
   * change), not push a new `initialValue` into the same instance.
   */
  initialValue: string;
  /** Fires on every edit with the current content, already sanitized. */
  onChange: (html: string) => void;
  placeholder?: string;
  autoFocus?: boolean;
  ariaLabel: string;
}

/**
 * The one note-editing surface — used identically for a highlight's note
 * while reading and for a moment's note while listening.
 *
 * This app server-renders on a Cloudflare Worker with no DOM at all, and has
 * no prior client-only-component convention (no `.client.tsx`, no
 * `ClientOnly`). TipTap needs a real DOM to construct its editor view, so the
 * actual implementation (`RichNoteEditorInner`, which is the only thing
 * allowed to import `@tiptap/*`) is loaded via a DYNAMIC import behind a
 * `mounted` flag that only flips inside a `useEffect` — which fires strictly
 * after hydration commits. The `import()` call itself never runs during SSR,
 * not just "runs but renders nothing": nobody has to trust that an unmounted
 * component with a live `@tiptap` import is harmless on a runtime with no
 * `document`.
 *
 * Both the pre-mount and the Suspense-loading state render the same
 * read-only skeleton, built from `renderNote` — the note as it already reads,
 * not a blank box or a spinner — so the very first frame (server-rendered and
 * the client's first paint, byte-identical) already shows real content.
 */
export function RichNoteEditor(props: RichNoteEditorProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const fallback = <Skeleton value={props.initialValue} placeholder={props.placeholder} />;

  if (!mounted) return fallback;

  return (
    <Suspense fallback={fallback}>
      <RichNoteEditorInner {...props} />
    </Suspense>
  );
}

function Skeleton({ value, placeholder }: { value: string; placeholder?: string }): ReactNode {
  const rendered = renderNote(value);
  return (
    <div className="pf-rte pf-rte--loading">
      <div className="pf-rte__toolbar" />
      <div className="pf-rte__content">
        {rendered ?? (placeholder === undefined ? null : (
          <span className="pf-rte__placeholder">{placeholder}</span>
        ))}
      </div>
    </div>
  );
}

// Module-scope, and the ONLY place in the app allowed to reference
// `RichNoteEditorInner` statically. Any other static import of that module
// would pull `@tiptap/*` into whatever chunk imported it — including
// possibly the SSR chunk — and defeat this whole scheme.
const RichNoteEditorInner = lazy(() =>
  import("./RichNoteEditorInner").then((m) => ({ default: m.RichNoteEditorInner })),
);
