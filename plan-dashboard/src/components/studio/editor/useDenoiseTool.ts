/**
 * useDenoiseTool — the noise-marking / denoise tool: popup open/close +
 * pattern state, the rule-based pattern generalisation from the selection,
 * the scope toggle (chapter/book), the preview/apply call
 * (/api/studio/denoise), and denoiseInEditorDoc (the in-editor mirror that
 * applies the confirmed pattern deletion to the live doc). Extracted
 * verbatim from StudioEditor.tsx (R2 pass 2 — one hook per commit).
 *
 * Contract notes (load-bearing, preserved exactly):
 *  - The post-apply order in runDenoise is preserved byte-for-byte:
 *    mirror into the live doc (skipped on read-only stages) → done-message →
 *    refresh(). Autosave is triggered implicitly by the mirrored ProseMirror
 *    transactions, exactly as before — no explicit scheduling call exists.
 *  - denoiseInEditorDoc stays internal: unlike replaceInEditorDoc (which
 *    useTermCuration consumes), nothing outside runDenoise calls it, so it
 *    is not returned. Hooks compose at the component level, never import
 *    each other.
 *  - chapterLabel stays in StudioEditor: only the popup JSX reads it (it is
 *    shared with the Replace popup); no function in this cluster touches it,
 *    so it is not passed in.
 *  - fetchErrorText is passed in: it is the shared module-level formatter
 *    (same as useReplaceTool / useAiActions / useTermCuration).
 *  - Dependency arrays are verbatim from the component (exhaustive-deps is
 *    advisory; identities of the passed-in helpers are unchanged).
 */
import { useCallback, useState } from "react";
import type { useEditor } from "@tiptap/react";

import { apiFetch } from "../../../lib/api-fetch";

interface DenoiseToolArgs {
  editor: ReturnType<typeof useEditor>;
  isReadOnlyStage: boolean;
  slug: string;
  chapter: string;
  /** Current text selection — generalised into the pattern on open. */
  selection: string;
  /** Shared module-level error formatter (stable identity). */
  fetchErrorText: (e: unknown) => string;
  /** Component-level tick bump so the JSX re-reads editor state after apply. */
  refresh: () => void;
}

export function useDenoiseTool({
  editor,
  isReadOnlyStage,
  slug,
  chapter,
  selection,
  fetchErrorText,
  refresh,
}: DenoiseToolArgs) {
  // ── Noise → pattern → denoise across chapters ────────────────────────────
  // Highlight a recurring artifact (a page header, an OCR scar, a stray marker)
  // → "Noise" opens this popup with a PATTERN generalised from the selection
  // (literal text, but digit-runs and whitespace loosened so one selection
  // catches its variants). Preview shows the count + a few real samples per
  // chapter before anything changes; Apply strips every match from the canonical
  // chapter .txt files via /api/studio/denoise (with .bak undo) and mirrors the
  // deletion into the live editor doc.
  const [noiseOpen, setNoiseOpen] = useState(false);
  const [noisePattern, setNoisePattern] = useState("");
  const [noiseScope, setNoiseScope] = useState<"chapter" | "book">("chapter");
  const [noisePreview, setNoisePreview] = useState<
    { chapter: string; count: number; samples: string[] }[] | null
  >(null);
  const [noiseTotal, setNoiseTotal] = useState(0);
  const [noiseBusy, setNoiseBusy] = useState(false);
  const [noiseError, setNoiseError] = useState("");
  const [noiseDone, setNoiseDone] = useState("");

  // Rule-based generalisation: escape regex specials, then loosen runs of digits
  // (\d+) and whitespace (\s+) so "[Page 12]" and "[Page 137]" collapse to one
  // pattern. The user can hand-edit the result before previewing.
  const deriveNoisePattern = useCallback((sel: string): string => {
    const escaped = sel.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return escaped.replace(/\d+/g, "\\d+").replace(/\s+/g, "\\s+");
  }, []);

  const openNoise = useCallback(() => {
    setNoisePattern(deriveNoisePattern(selection));
    setNoiseScope("chapter");
    setNoisePreview(null);
    setNoiseTotal(0);
    setNoiseError("");
    setNoiseDone("");
    setNoiseOpen(true);
  }, [selection, deriveNoisePattern]);
  const closeNoise = useCallback(() => setNoiseOpen(false), []);

  // Mirror the confirmed pattern deletion into the live editor doc so the current
  // chapter updates instantly. Swept high→low so positions stay valid.
  const denoiseInEditorDoc = useCallback(
    (pattern: string) => {
      if (!editor) return;
      let re: RegExp;
      try {
        re = new RegExp(pattern, "g");
      } catch {
        return;
      }
      const hits: { from: number; to: number }[] = [];
      editor.state.doc.descendants((node, pos) => {
        if (!node.isText || !node.text) return;
        re.lastIndex = 0;
        let m: RegExpExecArray | null;
        while ((m = re.exec(node.text))) {
          if (m[0] === "") {
            re.lastIndex += 1;
            continue;
          }
          const from = pos + m.index;
          hits.push({ from, to: from + m[0].length });
        }
      });
      if (!hits.length) return;
      hits.sort((a, b) => b.from - a.from);
      let tr = editor.state.tr;
      for (const h of hits) tr = tr.delete(h.from, h.to);
      editor.view.dispatch(tr);
    },
    [editor],
  );

  const runDenoise = useCallback(
    async (apply: boolean) => {
      const pattern = noisePattern.trim();
      if (pattern === "") {
        setNoiseError("Enter a pattern to strip.");
        return;
      }
      setNoiseBusy(true);
      setNoiseError("");
      setNoiseDone("");
      try {
        const j = await apiFetch<{
          total?: number;
          results?: { chapter: string; count: number; samples: string[] }[];
        }>("/api/studio/denoise", {
          method: "POST",
          body: {
            slug,
            scope: noiseScope,
            chapter,
            pattern,
            apply,
          },
        });
        setNoisePreview(j.results ?? []);
        setNoiseTotal(j.total ?? 0);
        if (apply) {
          if (!isReadOnlyStage) denoiseInEditorDoc(pattern);
          const nCh = (j.results ?? []).length;
          setNoiseDone(
            j.total === 0
              ? "No matches found — nothing changed."
              : `Stripped ${j.total} match${j.total === 1 ? "" : "es"} across ${nCh} chapter${nCh === 1 ? "" : "s"}.` +
                  (noiseScope === "book" && nCh > 1
                    ? " Other chapters update when you open them."
                    : ""),
          );
          refresh();
        }
      } catch (e) {
        setNoiseError(fetchErrorText(e));
      } finally {
        setNoiseBusy(false);
      }
    },
    [
      slug,
      noiseScope,
      chapter,
      noisePattern,
      isReadOnlyStage,
      denoiseInEditorDoc,
    ],
  );

  return {
    noiseOpen,
    noisePattern,
    setNoisePattern,
    noiseScope,
    setNoiseScope,
    noisePreview,
    setNoisePreview,
    noiseTotal,
    noiseBusy,
    noiseError,
    noiseDone,
    setNoiseDone,
    openNoise,
    closeNoise,
    runDenoise,
  };
}
