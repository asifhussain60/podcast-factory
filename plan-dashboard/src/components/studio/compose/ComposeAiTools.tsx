/**
 * ComposeAiTools.tsx — Research / Auto-tag (section-level, useAiActions) and
 * Arabic / English / Explain term curation (useTermCuration), reusing the
 * SAME hooks StudioEditor.tsx uses, fed the Book Composer's own vanilla
 * TipTap editor instance via the compose-editor-bridge. Appended into the
 * Refinement tab alongside Compose's existing selection-based AI actions
 * (Rewrite/Expand/Condense/Simplify/Explain/Etymology, still vanilla JS).
 *
 * Mounted imperatively (React 19 createRoot) by book-composer.ts, not as a
 * static Astro island — its editor/chapter props change every time the user
 * switches chapters, which a client:only island cannot receive after mount.
 *
 * Find & Replace and Denoise are explicitly NOT here — they stay on
 * /edit as book-wide maintenance utilities (see the approved plan).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Editor } from "@tiptap/core";

import { ApiFetchError } from "../../../lib/api-fetch";
import { busyDialog } from "../../../scripts/confirm-dialog";
import type { GlossaryEntry } from "../editor/studio-editor-constants";
import { useAiActions } from "../editor/useAiActions";
import { useTermCuration } from "../editor/useTermCuration";
import type { ComposeEditorBridge } from "../../../scripts/compose-editor-bridge";

function fetchErrorText(e: unknown): string {
  if (e instanceof ApiFetchError)
    return e.status === 0 ? String(e.cause ?? e) : e.message;
  return String(e);
}

interface Props {
  slug: string;
  chapter: string;
  chapterTitle: string;
  /** Non-null: this component is only mounted after mountChapterEditor()
   *  has already constructed the live editor instance (see book-composer.ts). */
  editor: Editor;
  bridge: ComposeEditorBridge;
  glossaryAll: GlossaryEntry[];
}

export default function ComposeAiTools({
  slug,
  chapter,
  chapterTitle,
  editor,
  bridge,
  glossaryAll,
}: Props) {
  const [tick, setTick] = useState(0);
  const refresh = useCallback(() => setTick((t) => t + 1), []);
  const [activeSectionOrdinal, setActiveSectionOrdinal] = useState<
    number | null
  >(null);

  // Lifted out of the effect so the mutation targets a ref-named local rather
  // than a field reached through the `bridge` prop — the bridge's boxes are
  // plain mutable refs shared with the vanilla decoration plugin, and naming
  // one here makes that ownership explicit to reader and lint alike.
  const { activeSectionOrdinalRef } = bridge;

  // Track which section the caret sits in — the same walk StudioEditor's
  // onSelectionUpdate performs, mirrored here since Compose's vanilla editor
  // has no React onSelectionUpdate callback of its own to piggyback on.
  useEffect(() => {
    if (!editor) return;
    const onSelUpdate = () => {
      const $head = editor.state.selection.$head;
      let curSec = -1;
      let secOrd = -1;
      let i = 0;
      editor.state.doc.forEach((node, offset) => {
        if (node.type.name === "heading" && node.attrs.level === 2) curSec++;
        const size = editor.state.doc.child(i)?.nodeSize ?? 0;
        if ($head.pos >= offset && $head.pos < offset + size) secOrd = curSec;
        i++;
      });
      const newOrd = secOrd >= 0 ? secOrd : null;
      activeSectionOrdinalRef.current = newOrd;
      setActiveSectionOrdinal(newOrd);
    };
    editor.on("selectionUpdate", onSelUpdate);
    onSelUpdate();
    return () => {
      editor.off("selectionUpdate", onSelUpdate);
    };
  }, [editor, activeSectionOrdinalRef]);

  const glossaryAllSorted = useMemo(
    () =>
      [...glossaryAll]
        .filter((e) => e.phonetic || e.transliteration || e.arabic_script)
        .sort((a, b) => {
          const ak = a.phonetic || a.transliteration || a.arabic_script || "";
          const bk = b.phonetic || b.transliteration || b.arabic_script || "";
          return bk.length - ak.length;
        }),
    [glossaryAll],
  );
  const findGlossaryTerm = useCallback(
    (raw: string): GlossaryEntry | null => {
      const needle = raw.trim();
      if (!needle) return null;
      const latinNeedle = needle.toLowerCase();
      for (const entry of glossaryAllSorted) {
        const values = [
          entry.phonetic,
          entry.transliteration,
          entry.arabic_script,
          entry.corrected_arabic,
        ]
          .filter(Boolean)
          .map((v) => String(v).trim());
        if (values.some((v) => v === needle || v.toLowerCase() === latinNeedle))
          return entry;
      }
      return null;
    },
    [glossaryAllSorted],
  );

  // Mirrors a confirmed canonical-file replace into the live doc — verbatim
  // from useReplaceTool.replaceInEditorDoc, reused standalone here since the
  // Replace tool's popup/pairs UI itself stays on /edit (out of scope).
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

  const { aiBusy, aiKind, aiResult, aiError, runAi } = useAiActions({
    editor,
    activeSectionOrdinal,
    chapterTitle,
    setInspectorTab: () => {}, // Compose's tab already IS Refinement — no auto-switch needed
    fetchErrorText,
    refresh,
  });

  const {
    arabicProposal,
    arabicBusy,
    arabicError,
    englishProposal,
    englishBusy,
    englishError,
    explainProposal,
    explainBusy,
    explainError,
    proposeArabic,
    proposeEnglish,
    proposeExplain,
    applyArabic,
    applyArabicAcross,
    applyEnglish,
    applyEnglishAcross,
    applyExplain,
    cancelArabic,
    cancelEnglish,
    cancelExplain,
  } = useTermCuration({
    editor,
    isReadOnlyStage: false,
    chapterTitle,
    slug,
    chapter,
    findGlossaryTerm,
    replaceInEditorDoc,
    fetchErrorText,
    refresh,
  });

  const hasSelection = !!editor && !editor.state.selection.empty;

  // Blocking progress modal while ANY of this panel's AI actions runs — the
  // same busyDialog the vanilla Refinement actions use, driven from the hooks'
  // own busy flags so the shared hooks stay untouched. One modal at a time;
  // the effect's cleanup closes it the moment the flag drops.
  const busyState = aiBusy
    ? aiKind === "research"
      ? { title: "Researching the section…", icon: "fa-solid fa-magnifying-glass" }
      : { title: "Auto-tagging the section…", icon: "fa-solid fa-tags" }
    : arabicBusy
      ? { title: "Proposing the Arabic term…", icon: "fa-solid fa-language" }
      : englishBusy
        ? { title: "Proposing the English term…", icon: "fa-solid fa-spell-check" }
        : explainBusy
          ? { title: "Explaining the selection…", icon: "fa-solid fa-lightbulb" }
          : null;
  const busyTitle = busyState?.title ?? null;
  const busyIcon = busyState?.icon ?? null;
  useEffect(() => {
    if (!busyTitle) return;
    const handle = busyDialog({
      title: busyTitle,
      icon: busyIcon ?? undefined,
      note: "The AI is working — a few seconds.",
    });
    return () => handle.close();
  }, [busyTitle, busyIcon]);

  return (
    <div className="cx-ai-tools" data-tick={tick}>
      <div className="cx-ai-tools-row">
        <button
          type="button"
          className="cx-btn-ai"
          disabled={aiBusy || activeSectionOrdinal === null}
          onClick={() => runAi("research")}
        >
          {aiBusy && aiKind === "research"
            ? "Researching…"
            : "Research section"}
        </button>
        <button
          type="button"
          className="cx-btn-ai"
          disabled={aiBusy || activeSectionOrdinal === null}
          onClick={() => runAi("autotag")}
        >
          {aiBusy && aiKind === "autotag" ? "Tagging…" : "Auto-tag section"}
        </button>
        <button
          type="button"
          className="cx-btn-ai"
          disabled={!hasSelection || arabicBusy}
          onClick={proposeArabic}
        >
          {arabicBusy ? "…" : "Arabic term"}
        </button>
        <button
          type="button"
          className="cx-btn-ai"
          disabled={!hasSelection || englishBusy}
          onClick={proposeEnglish}
        >
          {englishBusy ? "…" : "English term"}
        </button>
        <button
          type="button"
          className="cx-btn-ai"
          disabled={!hasSelection || explainBusy}
          onClick={proposeExplain}
        >
          {explainBusy ? "…" : "Explain"}
        </button>
      </div>

      {(aiResult || aiError) && (
        <div className={`cx-ai-result${aiError ? " is-error" : ""}`}>
          {aiError || aiResult}
        </div>
      )}

      {arabicProposal && (
        <div className="cx-ai-proposal">
          <p className="cx-ai-proposal-arabic" lang="ar" dir="rtl">
            {arabicProposal.arabic}
          </p>
          {arabicProposal.gloss && <p>{arabicProposal.gloss}</p>}
          {arabicError && <p className="cx-ai-error">{arabicError}</p>}
          <div className="cx-ai-proposal-actions">
            <button type="button" onClick={() => applyArabic()}>
              Apply here
            </button>
            <button type="button" onClick={() => applyArabicAcross("chapter")}>
              Apply in chapter
            </button>
            <button type="button" onClick={() => applyArabicAcross("book")}>
              Apply across book
            </button>
            <button type="button" onClick={cancelArabic}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {englishProposal && (
        <div className="cx-ai-proposal">
          <p>{englishProposal.english}</p>
          {englishError && <p className="cx-ai-error">{englishError}</p>}
          <div className="cx-ai-proposal-actions">
            <button type="button" onClick={() => applyEnglish()}>
              Apply here
            </button>
            <button type="button" onClick={() => applyEnglishAcross("chapter")}>
              Apply in chapter
            </button>
            <button type="button" onClick={() => applyEnglishAcross("book")}>
              Apply across book
            </button>
            <button type="button" onClick={cancelEnglish}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {explainProposal && (
        <div className="cx-ai-proposal">
          <p>{explainProposal.text}</p>
          {explainError && <p className="cx-ai-error">{explainError}</p>}
          <div className="cx-ai-proposal-actions">
            <button type="button" onClick={applyExplain}>
              Apply
            </button>
            <button type="button" onClick={cancelExplain}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
