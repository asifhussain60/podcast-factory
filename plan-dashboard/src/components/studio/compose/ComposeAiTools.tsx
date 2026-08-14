/**
 * ComposeAiTools.tsx — Research / Auto-tag (section-level, useAiActions) and
 * Arabic / English / Explain term curation (useTermCuration), reusing the
 * SAME hooks StudioEditor.tsx uses, fed the Book Composer's own vanilla
 * TipTap editor instance via the compose-editor-bridge.
 *
 * Mounted imperatively (React 19 createRoot) by book-composer.ts at the
 * static `#cx-ai-tools-mount` anchor, not as a client:only Astro island —
 * its editor/chapter props change every time the user switches chapters,
 * which an island can't receive after mount. That mount point is NOT where
 * this component's buttons are drawn any more (2026-08-14 consolidation):
 * the Refine & Notes panel is now grouped into collapsible sections built by
 * book-composer.ts's renderAiActions, and this file's controls belong beside
 * the vanilla ones in those same sections (Add term/Explain in "Arabic &
 * language", Analyze section in "Whole chapter") rather than in a stranded
 * third block below them. `createPortal` renders each group into the
 * matching `#cx-ai-portal-*` div renderAiActions creates inside its own
 * section body — one React root, two portals, no duplicated hook state.
 * Arabic term + English term merged into one "Add term" sub-group (same
 * action, just which language); Research + Auto-tag merged the same way
 * into "Analyze section". Explain is UNCHANGED here — it is what survived
 * the panel's other duplicate Explain button, which called the same
 * `/api/ai/explain` endpoint from vanilla JS (see book-composer-ai-config.ts).
 *
 * Find & Replace and Denoise are explicitly NOT here — they stay on
 * /edit as book-wide maintenance utilities (see the approved plan).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
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
      ? {
          title: "Researching the section…",
          icon: "fa-solid fa-magnifying-glass",
        }
      : { title: "Auto-tagging the section…", icon: "fa-solid fa-tags" }
    : arabicBusy
      ? { title: "Proposing the Arabic term…", icon: "fa-solid fa-language" }
      : englishBusy
        ? {
            title: "Proposing the English term…",
            icon: "fa-solid fa-spell-check",
          }
        : explainBusy
          ? {
              title: "Explaining the selection…",
              icon: "fa-solid fa-lightbulb",
            }
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

  // Portal targets are built by book-composer.ts's renderAiActions() once at
  // boot, well before any chapter's editor (and this component) ever mounts
  // — see that function's own comments for why the ordering is safe. Guarded
  // with a null check anyway rather than assumed, so a missing target skips
  // that group's portal instead of throwing.
  const arabicPortalTarget =
    typeof document !== "undefined"
      ? document.getElementById("cx-ai-portal-arabic")
      : null;
  const chapterPortalTarget =
    typeof document !== "undefined"
      ? document.getElementById("cx-ai-portal-chapter")
      : null;

  return (
    <div className="cx-ai-tools" data-tick={tick}>
      {arabicPortalTarget &&
        createPortal(
          <>
            {/* Arabic term + English term merged 2026-08-14: same action
                (propose a glossary entry), only the language differs. */}
            <div className="cx-ai-subgroup">
              <span className="cx-ai-subgroup-label">Add term</span>
              <button
                type="button"
                className="cx-btn-ai"
                disabled={!hasSelection || arabicBusy}
                onClick={proposeArabic}
              >
                {arabicBusy ? "…" : "Arabic"}
              </button>
              <button
                type="button"
                className="cx-btn-ai"
                disabled={!hasSelection || englishBusy}
                onClick={proposeEnglish}
              >
                {englishBusy ? "…" : "English"}
              </button>
            </div>
            <div className="cx-ai-row">
              <button
                type="button"
                className="cx-btn-ai"
                disabled={!hasSelection || explainBusy}
                onClick={proposeExplain}
              >
                {explainBusy ? "…" : "Explain"}
              </button>
            </div>

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
                  <button
                    type="button"
                    onClick={() => applyArabicAcross("chapter")}
                  >
                    Apply in chapter
                  </button>
                  <button
                    type="button"
                    onClick={() => applyArabicAcross("book")}
                  >
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
                  <button
                    type="button"
                    onClick={() => applyEnglishAcross("chapter")}
                  >
                    Apply in chapter
                  </button>
                  <button
                    type="button"
                    onClick={() => applyEnglishAcross("book")}
                  >
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
          </>,
          arabicPortalTarget,
        )}

      {chapterPortalTarget &&
        createPortal(
          <>
            {/* Research section + Auto-tag section merged 2026-08-14: both
                run in the background over the whole section, no selection
                needed — one sub-group, two outcomes. */}
            <div className="cx-ai-subgroup">
              <span className="cx-ai-subgroup-label">Analyze section</span>
              <button
                type="button"
                className="cx-btn-ai"
                disabled={aiBusy || activeSectionOrdinal === null}
                onClick={() => runAi("research")}
              >
                {aiBusy && aiKind === "research" ? "Researching…" : "Research"}
              </button>
              <button
                type="button"
                className="cx-btn-ai"
                disabled={aiBusy || activeSectionOrdinal === null}
                onClick={() => runAi("autotag")}
              >
                {aiBusy && aiKind === "autotag" ? "Tagging…" : "Auto-tag"}
              </button>
            </div>

            {(aiResult || aiError) && (
              <div className={`cx-ai-result${aiError ? " is-error" : ""}`}>
                {aiError || aiResult}
              </div>
            )}
          </>,
          chapterPortalTarget,
        )}
    </div>
  );
}
