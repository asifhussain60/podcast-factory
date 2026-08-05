/**
 * useAiActions — the Wave L-8 AI assist panel cluster: aiBusy/aiKind/aiResult/
 * aiOptions/aiError state, the section prompt-context builder (sectionText),
 * the runAi dispatcher (rewrite / research / autotag), the rewrite-option
 * apply handler (applySection), and the runAiFnRef indirection the PM
 * section-toolbar widget calls. Extracted verbatim from StudioEditor.tsx
 * (R2 pass 2 — one hook per commit).
 *
 * Contract notes (load-bearing, preserved exactly):
 *  - /api/ai/rewrite and /api/ai/research stay on RAW fetch by design (R2):
 *    both report errors as {error} + non-2xx WITHOUT an ok key, and this site
 *    displays that server message; apiFetch would replace it with a generic
 *    HTTP line. Only the autotag task (/api/ai/claude) uses apiFetch.
 *  - runAiFnRef is assigned during render (not in an effect), exactly as the
 *    component assigned it before extraction, so the PM section-toolbar
 *    mousedown never sees a stale closure between render and effect flush.
 *    (react-hooks/refs is warn-level for this deliberate pattern — same as
 *    useSectionDepth's mirror refs.) `runAiFnRef` is an OPTIONAL param: in
 *    StudioEditor the ref is created ahead of this hook's call site (StudioDecos
 *    — which reads runAiFnRef — is built before this hook runs, since it feeds
 *    useEditor's extensions array) and passed in; callers with no PM-widget
 *    indirection (e.g. ComposeAiTools, whose buttons call runAi() directly)
 *    fall back to an internally-created ref that nothing reads.
 *  - fetchErrorText is passed in: it is shared with the arabic/english/
 *    explain proposal clusters that remain in StudioEditor.
 *  - Dependency arrays are verbatim from the component (exhaustive-deps is
 *    advisory; identities of the passed-in helpers are unchanged).
 */
import { useCallback, useLayoutEffect, useRef, useState } from "react";
import type { useEditor } from "@tiptap/react";

import { apiFetch } from "../../../lib/api-fetch";

interface AiActionsArgs {
  editor: ReturnType<typeof useEditor>;
  activeSectionOrdinal: number | null;
  chapterTitle: string;
  /** Inspector tab setter — runAi auto-switches to the AI tab. */
  setInspectorTab: (tab: "details" | "comment" | "ai" | "refs") => void;
  /** Shared module-level error formatter (stable identity). */
  fetchErrorText: (e: unknown) => string;
  /** Component-level tick bump so the JSX re-reads editor state after apply. */
  refresh: () => void;
  /**
   * Section-level AI action ref, called from the section h2 floating toolbar.
   * Optional — see file header note. Created in StudioEditor (not here) when
   * a PM-widget indirection is needed.
   */
  runAiFnRef?: React.RefObject<(kind: string) => void>;
}

export function useAiActions({
  editor,
  activeSectionOrdinal,
  chapterTitle,
  setInspectorTab,
  fetchErrorText,
  refresh,
  runAiFnRef: externalRunAiFnRef,
}: AiActionsArgs) {
  // Wave L-8 — AI assist panel state.
  const [aiBusy, setAiBusy] = useState(false);
  const [aiKind, setAiKind] = useState("");
  const [aiResult, setAiResult] = useState(""); // research / autotag plain text
  const [aiOptions, setAiOptions] = useState<string[]>([]); // rewrite option cards
  const [aiError, setAiError] = useState("");

  // Fallback ref for callers with no PM-widget indirection (see file header).
  const ownRunAiFnRef = useRef<(kind: string) => void>(() => {});
  const runAiFnRef = externalRunAiFnRef ?? ownRunAiFnRef;

  // All text (heading + paragraphs) of a section, joined by double newline.
  const sectionText = useCallback(
    (ordinal: number | null): string => {
      if (!editor || ordinal === null) return "";
      const parts: string[] = [];
      let curSec = -1;
      editor.state.doc.forEach((node) => {
        if (node.type.name === "heading" && node.attrs.level === 2) curSec++;
        if (curSec === ordinal) {
          const t = node.textContent.trim();
          if (t) parts.push(t);
        }
      });
      return parts.join("\n\n");
    },
    [editor],
  );

  // Run an AI action on the active section. `kind` selects the route + model.
  const runAi = useCallback(
    async (kind: string) => {
      const text = sectionText(activeSectionOrdinal);
      if (!text.trim()) return;
      setAiBusy(true);
      setAiKind(kind);
      setAiResult("");
      setAiOptions([]);
      setAiError("");
      setInspectorTab("ai"); // auto-switch so result is visible immediately
      try {
        if (kind === "autotag") {
          const data = await apiFetch<{ tag?: string; reason?: string }>(
            "/api/ai/claude",
            { method: "POST", body: { task: "categorise", text } },
          );
          const { tag, reason } = data ?? {};
          setAiResult(`Suggested tag: ${tag}${reason ? ` — ${reason}` : ""}`);
          return;
        }
        let res: Response;
        if (kind === "rewrite") {
          // R2: intentionally left on raw fetch — /api/ai/rewrite reports
          // errors as {error} + non-2xx WITHOUT an ok key, and this site
          // displays that server message; apiFetch would replace it with a
          // generic HTTP line.
          res = await fetch("/api/ai/rewrite", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ text }),
          });
        } else if (kind === "research") {
          // R2: intentionally left on raw fetch — /api/ai/research has the
          // same non-envelope {error} + non-2xx error shape as rewrite.
          res = await fetch("/api/ai/research", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({
              paragraphText: text,
              instruction:
                "Research this passage and provide scholarly context with web-sourced information.",
              bookTitle: chapterTitle,
              actionType: "research",
            }),
          });
        } else {
          setAiBusy(false);
          return;
        }
        const json = await res.json();
        if (!res.ok || json.ok === false) {
          setAiError(json.error ?? `Request failed (${res.status})`);
        } else if (kind === "rewrite") {
          // The envelope-leak re-parse that used to sit here moved into
          // /api/ai/rewrite on 2026-07-27. It was only ever on this surface, so
          // the Composer — calling the same endpoint — offered the raw
          // `{"options": [...]}` blob as a rewrite you could click into the book.
          // One guard, at the source both callers share.
          const opts = (json.data?.options ?? json.options ?? []) as string[];
          setAiOptions(opts.slice(0, 3).map((o) => String(o).trim()));
        } else if (kind === "research") {
          const body = json.fullText ?? json.prompt ?? "";
          const sources = (json.sources as string[] | undefined) ?? [];
          const sourced = sources.length
            ? `\n\nSources:\n${sources.map((s) => `• ${s}`).join("\n")}`
            : "";
          setAiResult(body + sourced);
        } else {
          setAiResult(
            typeof json.data === "string"
              ? json.data
              : JSON.stringify(json.data),
          );
        }
      } catch (e) {
        setAiError(fetchErrorText(e));
      } finally {
        setAiBusy(false);
      }
    },
    [activeSectionOrdinal, sectionText, chapterTitle, setInspectorTab],
  );

  // Apply a rewrite option to the active section: replaces all body paragraphs.
  const applySection = useCallback(
    (newText: string) => {
      if (!editor || activeSectionOrdinal === null) return;
      let bodyFrom = -1;
      let bodyTo = editor.state.doc.content.size;
      let curSec = -1;
      let foundSection = false;
      editor.state.doc.forEach((node, offset) => {
        if (node.type.name === "heading" && node.attrs.level === 2) {
          curSec++;
          if (curSec === activeSectionOrdinal) {
            bodyFrom = offset + node.nodeSize;
            foundSection = true;
          } else if (foundSection) {
            bodyTo = offset;
            foundSection = false;
          }
        }
      });
      if (bodyFrom < 0) return;
      const schema = editor.state.schema;
      const paragraphs = newText
        .split(/\n\s*\n/)
        .map((p) => p.trim())
        .filter(Boolean);
      const nodes =
        paragraphs.length > 0
          ? paragraphs.map((p) =>
              schema.nodes.paragraph.create(null, schema.text(p)),
            )
          : [schema.nodes.paragraph.create()];
      editor.view.dispatch(
        editor.state.tr.replaceWith(bodyFrom, bodyTo, nodes),
      );
      refresh();
    },
    [editor, activeSectionOrdinal],
  );

  // Keep the PM widget calling the LATEST closure — see the contract notes at
  // the top of this file. This was a render-phase assignment; it is now a
  // layout effect because mutating a caller-owned ref during render is unsafe
  // under concurrent rendering (React may render without committing, leaving
  // the ref pointing at a closure from a discarded pass) and the compiler lint
  // flags it as such. Timing is unchanged in practice: the only reader is a
  // ProseMirror widget mousedown handler, which can only fire after commit, and
  // useLayoutEffect runs before paint.
  useLayoutEffect(() => {
    runAiFnRef.current = (kind: string) => void runAi(kind);
  }, [runAiFnRef, runAi]);

  return {
    aiBusy,
    aiKind,
    aiResult,
    aiOptions,
    aiError,
    runAi,
    applySection,
  };
}
