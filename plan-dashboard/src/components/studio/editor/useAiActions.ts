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
 *    useSectionDepth's mirror refs.)
 *  - fetchErrorText is passed in: it is shared with the arabic/english/
 *    explain proposal clusters that remain in StudioEditor.
 *  - Dependency arrays are verbatim from the component (exhaustive-deps is
 *    advisory; identities of the passed-in helpers are unchanged).
 */
import { useCallback, useRef, useState } from "react";
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
}

export function useAiActions({
  editor,
  activeSectionOrdinal,
  chapterTitle,
  setInspectorTab,
  fetchErrorText,
  refresh,
}: AiActionsArgs) {
  // Wave L-8 — AI assist panel state.
  const [aiBusy, setAiBusy] = useState(false);
  const [aiKind, setAiKind] = useState("");
  const [aiResult, setAiResult] = useState(""); // research / autotag plain text
  const [aiOptions, setAiOptions] = useState<string[]>([]); // rewrite option cards
  const [aiError, setAiError] = useState("");

  // Section-level AI action ref: called from the section h2 floating toolbar.
  const runAiFnRef = useRef<(kind: string) => void>(() => {});

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
          let opts = (json.data?.options ?? json.options ?? []) as string[];
          // Fallback fix: if opts[0] is a raw JSON string (from API error path), re-parse it.
          if (
            opts.length === 1 &&
            typeof opts[0] === "string" &&
            opts[0].trimStart().startsWith("{")
          ) {
            try {
              const inner = JSON.parse(opts[0]) as { options?: string[] };
              if (Array.isArray(inner.options) && inner.options.length > 0)
                opts = inner.options;
            } catch {
              /* keep opts as-is */
            }
          }
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

  // Render-time assignment (same as the pre-extraction component) so the PM
  // widget always calls the latest closure — see contract notes above.
  runAiFnRef.current = (kind: string) => void runAi(kind);

  return {
    aiBusy,
    aiKind,
    aiResult,
    aiOptions,
    aiError,
    runAi,
    applySection,
    runAiFnRef,
  };
}
