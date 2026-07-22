/**
 * useReplaceTool — the global find-and-replace tool: popup open/close +
 * pair-list state, the scope toggle (chapter/book), the preview/apply call
 * (/api/studio/replace), and replaceInEditorDoc (the in-editor mirror that
 * applies confirmed canonical-file replacements to the live doc). Extracted
 * verbatim from StudioEditor.tsx (R2 pass 2 — one hook per commit).
 *
 * Contract notes (load-bearing, preserved exactly):
 *  - replaceInEditorDoc is RETURNED so the component can feed it to
 *    useTermCuration (the across-chapter/book Arabic/English variants reuse
 *    it); hooks compose at the component level, never import each other.
 *  - The post-apply order in runReplace is preserved byte-for-byte:
 *    mirror into the live doc (skipped on read-only stages) → done-message →
 *    refresh(). Autosave is triggered implicitly by the mirrored ProseMirror
 *    transactions, exactly as before — no explicit scheduling call exists.
 *  - Pairs apply in order (a later pair sees earlier results), matching the
 *    server; each pair is swept high→low so positions stay valid.
 *  - chapterLabel stays in StudioEditor: the noise/denoise popup (not
 *    extracted) shares it.
 *  - fetchErrorText is passed in: it is shared with the Noise cluster that
 *    remains in StudioEditor (same as useAiActions / useTermCuration).
 *  - Dependency arrays are verbatim from the component (exhaustive-deps is
 *    advisory; identities of the passed-in helpers are unchanged).
 */
import { useCallback, useState } from "react";
import type { useEditor } from "@tiptap/react";

import { apiFetch } from "../../../lib/api-fetch";

interface ReplaceToolArgs {
  editor: ReturnType<typeof useEditor>;
  isReadOnlyStage: boolean;
  slug: string;
  chapter: string;
  /** Current text selection — pre-fills the first find field on open. */
  selection: string;
  /** Shared module-level error formatter (stable identity). */
  fetchErrorText: (e: unknown) => string;
  /** Component-level tick bump so the JSX re-reads editor state after apply. */
  refresh: () => void;
}

export function useReplaceTool({
  editor,
  isReadOnlyStage,
  slug,
  chapter,
  selection,
  fetchErrorText,
  refresh,
}: ReplaceToolArgs) {
  // ── Global find-and-replace ──────────────────────────────────────────────
  // Highlight a phrase → "Replace" opens this popup pre-filled with the
  // selection. Multiple find→replace pairs run in one pass; the scope checkbox
  // switches between this chapter and every chapter in the book. Preview counts
  // matches without writing; Apply rewrites the canonical chapter .txt files via
  // /api/studio/replace and mirrors the change into the live editor doc.
  const [replaceOpen, setReplaceOpen] = useState(false);
  const [replacePairs, setReplacePairs] = useState<
    { find: string; replace: string }[]
  >([{ find: "", replace: "" }]);
  const [replaceScope, setReplaceScope] = useState<"chapter" | "book">(
    "chapter",
  );
  const [replacePreview, setReplacePreview] = useState<
    { chapter: string; count: number }[] | null
  >(null);
  const [replaceTotal, setReplaceTotal] = useState(0);
  const [replaceBusy, setReplaceBusy] = useState(false);
  const [replaceError, setReplaceError] = useState("");
  const [replaceDone, setReplaceDone] = useState("");

  const openReplace = useCallback(() => {
    setReplacePairs([{ find: selection.trim(), replace: "" }]);
    setReplaceScope("chapter");
    setReplacePreview(null);
    setReplaceTotal(0);
    setReplaceError("");
    setReplaceDone("");
    setReplaceOpen(true);
  }, [selection]);
  const closeReplace = useCallback(() => setReplaceOpen(false), []);
  const updatePair = (i: number, field: "find" | "replace", val: string) =>
    setReplacePairs((ps) =>
      ps.map((p, j) => (j === i ? { ...p, [field]: val } : p)),
    );
  const addPair = () =>
    setReplacePairs((ps) => [...ps, { find: "", replace: "" }]);
  const removePair = (i: number) =>
    setReplacePairs((ps) =>
      ps.length > 1 ? ps.filter((_, j) => j !== i) : ps,
    );

  // Mirror the confirmed replacements into the live editor doc so the current
  // chapter updates instantly. Pairs apply in order (a later pair sees earlier
  // results), matching the server. Each pair is swept high→low so positions
  // stay valid as text is replaced.
  const replaceInEditorDoc = useCallback(
    (pairs: { find: string; replace: string }[]) => {
      if (!editor) return;
      for (const { find, replace } of pairs) {
        if (!find) continue;
        const hits: { from: number; to: number }[] = [];
        editor.state.doc.descendants((node, pos) => {
          if (!node.isText || !node.text) return;
          let idx = node.text.indexOf(find);
          while (idx !== -1) {
            const from = pos + idx;
            hits.push({ from, to: from + find.length });
            idx = node.text.indexOf(find, idx + find.length);
          }
        });
        if (!hits.length) continue;
        hits.sort((a, b) => b.from - a.from);
        let tr = editor.state.tr;
        for (const h of hits) {
          tr = replace
            ? tr.replaceWith(h.from, h.to, editor.state.schema.text(replace))
            : tr.delete(h.from, h.to);
        }
        editor.view.dispatch(tr);
      }
    },
    [editor],
  );

  const runReplace = useCallback(
    async (apply: boolean) => {
      const pairs = replacePairs
        .map((p) => ({ find: p.find, replace: p.replace }))
        .filter((p) => p.find.trim() !== "");
      if (pairs.length === 0) {
        setReplaceError("Enter at least one phrase to find.");
        return;
      }
      setReplaceBusy(true);
      setReplaceError("");
      setReplaceDone("");
      try {
        const j = await apiFetch<{
          total?: number;
          results?: { chapter: string; count: number }[];
        }>("/api/studio/replace", {
          method: "POST",
          body: {
            slug,
            scope: replaceScope,
            chapter,
            pairs,
            apply,
          },
        });
        setReplacePreview(j.results ?? []);
        setReplaceTotal(j.total ?? 0);
        if (apply) {
          if (!isReadOnlyStage) replaceInEditorDoc(pairs);
          const nCh = (j.results ?? []).length;
          setReplaceDone(
            j.total === 0
              ? "No matches found — nothing changed."
              : `Replaced ${j.total} instance${j.total === 1 ? "" : "s"} across ${nCh} chapter${nCh === 1 ? "" : "s"}.` +
                  (replaceScope === "book" && nCh > 1
                    ? " Other chapters update when you open them."
                    : ""),
          );
          refresh();
        }
      } catch (e) {
        setReplaceError(fetchErrorText(e));
      } finally {
        setReplaceBusy(false);
      }
    },
    [
      slug,
      replaceScope,
      chapter,
      replacePairs,
      isReadOnlyStage,
      replaceInEditorDoc,
    ],
  );

  return {
    replaceOpen,
    replacePairs,
    replaceScope,
    setReplaceScope,
    replacePreview,
    setReplacePreview,
    replaceTotal,
    replaceBusy,
    replaceError,
    replaceDone,
    setReplaceDone,
    openReplace,
    closeReplace,
    updatePair,
    addPair,
    removePair,
    replaceInEditorDoc,
    runReplace,
  };
}
