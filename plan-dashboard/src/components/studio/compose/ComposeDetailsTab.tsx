/**
 * ComposeDetailsTab.tsx — the "Tell the AI" chapter-instruction box (the
 * orphaned /api/ai/instruct route's first consumer) and the deferred
 * action-item marks queue (useAnnotations), fed the Book Composer's own
 * vanilla TipTap editor via the compose-editor-bridge.
 *
 * The per-paragraph Comment box and the Section-depth list left this tab on
 * 2026-07-22 (Asif: "I don't need comments, section depth, citations — I need
 * a text box where I say what I want and the AI makes the changes"). Their
 * HOOKS remain wired: useAnnotations still powers the marks queue, and
 * useSectionDepth still feeds the bridge boxes the editor-margin depth
 * widgets read — only the tab UI is gone.
 *
 * Mounted imperatively (React 19 createRoot) by book-composer.ts alongside
 * ComposeAiTools — see that file's header comment for why (editor/chapter
 * props change on every chapter switch, which a client:only island can't
 * receive after mount).
 */
import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import type { Editor } from "@tiptap/core";

import { ACTION_REGISTRY } from "../editor/studio-editor-constants";
import { useAnnotations } from "../editor/useAnnotations";
import { useSectionDepth } from "../editor/useSectionDepth";
import type { ComposeEditorBridge } from "../../../scripts/compose-editor-bridge";

// Deferred (queued) marks only — the immediate/AI actions (Arabic, English,
// Explain) live in ComposeAiTools instead, right next to the AI tools.
const DEFERRED_ACTIONS = ACTION_REGISTRY.filter(
  (a) => (a.applyMode ?? "deferred") === "deferred",
);
const DEFERRED_BY_KIND = Object.fromEntries(
  DEFERRED_ACTIONS.map((a) => [a.kind, a]),
);

// Outcome grouping for the mark buttons (2026-07-22, Asif-approved reorg): a
// wall of nine equal buttons told the reader nothing about what each family
// is FOR. Text marks are runnable from the queue today (through the
// Composer's own immediate-AI machinery); the knowledge/visual marks wait for
// a pipeline drain pass that does not exist yet — and the UI says so plainly
// instead of overpromising.
const MARK_GROUPS: { name: string; kinds: string[] }[] = [
  { name: "Text", kinds: ["rewrite", "expand", "condense", "simplify"] },
  { name: "Knowledge", kinds: ["etymology", "define", "xref", "addcorpus"] },
  { name: "Visual", kinds: ["visualize"] },
];

/** Compose-side operations the queue calls back into (book-composer.ts). */
export interface ComposeQueueOps {
  /** Scroll to and select the mark's anchored text in the editor. */
  jumpTo: (anchor: string) => void;
  /** Run the matching immediate AI action on the anchored text; `onApplied`
   *  fires when the human ACCEPTS a result (the mark then clears itself). */
  runNow: (kind: string, anchor: string, onApplied: () => void) => void;
  /** Mark kinds runNow can serve (the text transforms). */
  runnableKinds: readonly string[];
  /** Flush the prose autosave and reload preserving chapter + Edit mode —
   *  the Composer's own idiom after content changes. Returns false (and does
   *  not reload) if the save failed. */
  applyAndSync?: (note: string) => Promise<boolean>;
}

interface Props {
  slug: string;
  chapter: string;
  editor: Editor;
  bridge: ComposeEditorBridge;
  queueOps?: ComposeQueueOps;
}

export default function ComposeDetailsTab({
  slug,
  chapter,
  editor,
  bridge,
  queueOps,
}: Props) {
  const [, setTick] = useState(0);
  const refresh = useCallback(() => setTick((t) => t + 1), []);
  const [activeParaIdx, setActiveParaIdx] = useState<number | null>(null);
  const [selection, setSelection] = useState("");

  // Track the caret's paragraph (comments/marks) and selected text (term marks).
  useEffect(() => {
    const onSelUpdate = () => {
      const { from, to } = editor.state.selection;
      setSelection(editor.state.doc.textBetween(from, to, " ").trim());
      const $head = editor.state.selection.$head;
      let paraIdx = -1;
      let i = 0;
      editor.state.doc.forEach((_node, offset) => {
        const size = editor.state.doc.child(i)?.nodeSize ?? 0;
        if ($head.pos >= offset && $head.pos < offset + size) paraIdx = i;
        i++;
      });
      setActiveParaIdx(paraIdx >= 0 ? paraIdx : null);
    };
    editor.on("selectionUpdate", onSelUpdate);
    onSelUpdate();
    return () => {
      editor.off("selectionUpdate", onSelUpdate);
    };
  }, [editor]);

  // The bridge's fields are plain mutable ref boxes shared with the vanilla
  // decoration plugin. Naming them as locals here makes that ownership explicit
  // to reader and lint alike, and keeps the writes below off the prop object.
  const {
    editorRef,
    actionsRef: bridgeActionsRef,
    removeActionFnRef: bridgeRemoveActionFnRef,
    sectionDepthsRef: bridgeSectionDepthsRef,
    sectionTagsRef: bridgeSectionTagsRef,
    saveSectionDepthRef: bridgeSaveSectionDepthRef,
  } = bridge;

  const {
    actionsRef,
    removeActionFnRef,
    markedCount,
    chapterActions,
    stampAction,
  } = useAnnotations({
    slug,
    chapter,
    editor,
    editorRef,
    activeParaIdx,
    isReadOnlyStage: false,
    selection,
    refresh,
  });

  const { sectionDepths, sectionTagsMap, saveSectionDepthRef } =
    useSectionDepth(slug, chapter, editorRef);

  // Publish this tab's live state into the shared bridge so the vanilla
  // decoration plugin (which reads these boxes from a PM widget mousedown)
  // never sees a stale value.
  //
  // These were render-phase assignments. Mutating a caller-owned object during
  // render is unsafe under concurrent rendering — React may render without
  // committing, leaving the bridge pointing at state from a discarded pass —
  // and the compiler lint rejects it. A layout effect keeps the observable
  // timing: the only reader is a widget mousedown, which cannot fire before
  // commit, and layout effects run before paint.
  useLayoutEffect(() => {
    editorRef.current = editor;
    bridgeActionsRef.current = actionsRef.current;
    bridgeRemoveActionFnRef.current = removeActionFnRef.current;
    bridgeSectionDepthsRef.current = sectionDepths;
    bridgeSectionTagsRef.current = sectionTagsMap;
    bridgeSaveSectionDepthRef.current = saveSectionDepthRef.current;
  });

  // ── "Tell the AI" — free-form chapter instruction via /api/ai/instruct ────
  const [instruction, setInstruction] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  // The result note survives the post-apply reload (see applyAndSync). Stored
  // as {slug, chapter, note} and validated here, so a stashed note can never
  // surface on a different book's or chapter's tab.
  const [aiNote, setAiNote] = useState(() => {
    try {
      const saved = sessionStorage.getItem("cx-instruct-note");
      if (saved) {
        sessionStorage.removeItem("cx-instruct-note");
        const p = JSON.parse(saved) as { slug?: string; chapter?: string; note?: string };
        if (p.slug === slug && p.chapter === chapter && p.note) return p.note;
      }
    } catch {
      /* best-effort */
    }
    return "";
  });
  const [aiReasons, setAiReasons] = useState<string[]>([]);

  const runInstruction = useCallback(async () => {
    const ask = instruction.trim();
    if (!ask || aiBusy) return;
    setAiBusy(true);
    setAiNote("Asking Gemini…");
    setAiReasons([]);
    // Snapshot the chapter's top-level blocks WITH stable ids. The snapshot is
    // also the apply-time guard: an edit only lands on a block whose text
    // still matches what the model was shown.
    const blocks: { id: string; tag: string; text: string }[] = [];
    editor.state.doc.forEach((node, _off, idx) => {
      blocks.push({ id: `b#${idx}`, tag: node.type.name, text: node.textContent });
    });
    try {
      const res = await fetch("/api/ai/instruct", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ instruction: ask, blocks, chapterTitle: chapter }),
      });
      const j = (await res.json()) as {
        error?: string;
        note?: string;
        edits?: {
          block_id: string;
          action: "replace" | "delete" | "insert_after";
          new_text?: string;
          reason?: string;
        }[];
      };
      if (j.error) throw new Error(j.error);
      if (editor.isDestroyed) return; // the user left Edit mode mid-fetch
      const edits = j.edits ?? [];
      if (!edits.length) {
        setAiNote(j.note || "No change needed.");
        return;
      }
      // ONE ProseMirror transaction for the whole application: atomic (all
      // edits land or none) and a single undo step. Edits are applied in
      // ASCENDING block order with every snapshot position remapped through
      // tr.mapping, so an earlier edit can never invalidate a later one's
      // coordinates. (The first version dispatched per-edit chains; an
      // insert_after silently broke the PAINT of a replace on another block.)
      let skipped = 0;
      const seenIdx = new Set<number>();
      const byIdx = edits
        .map((e) => ({ ...e, idx: Number(String(e.block_id ?? "").split("#")[1]) }))
        .filter((e) => {
          // Malformed / out-of-range / duplicate targets are counted, never guessed.
          if (!Number.isInteger(e.idx) || e.idx < 0 || e.idx >= blocks.length) {
            skipped++;
            return false;
          }
          if (seenIdx.has(e.idx)) {
            skipped++; // a second edit on the same block would use stale sizes
            return false;
          }
          seenIdx.add(e.idx);
          return true;
        })
        .sort((a, b) => a.idx - b.idx);
      // Snapshot walk: pos/size/current-text for every top-level block.
      const at: { pos: number; size: number; text: string }[] = [];
      editor.state.doc.forEach((node, off) => {
        at.push({ pos: off, size: node.nodeSize, text: node.textContent });
      });
      const { tr, schema } = editor.state;
      let applied = 0;
      const reasons: string[] = [];
      for (const e of byIdx) {
        const t = at[e.idx];
        if (!t || t.text !== blocks[e.idx].text) {
          skipped++;
          continue; // the chapter changed under the model — never guess
        }
        // Ascending order + tr.mapping: each snapshot position is remapped
        // through the steps already added, so earlier edits can never
        // invalidate a later one's coordinates.
        const pos = tr.mapping.map(t.pos, 1);
        if (e.action === "replace" && e.new_text) {
          // Replace the block's INLINE content, not the node itself — the
          // block keeps its type and attrs (a heading stays a heading).
          tr.insertText(e.new_text, pos + 1, pos + t.size - 1);
        } else if (e.action === "delete") {
          tr.delete(pos, pos + t.size);
        } else if (e.action === "insert_after" && e.new_text) {
          tr.insert(
            pos + t.size,
            schema.nodes.paragraph.create(null, schema.text(e.new_text)),
          );
        } else {
          skipped++;
          continue;
        }
        applied++;
        if (e.reason) reasons.push(e.reason);
      }
      const summary =
        `${j.note ? j.note + " — " : ""}${applied} edit${applied === 1 ? "" : "s"} applied` +
        (skipped ? `, ${skipped} skipped (unusable, or the text changed while the AI worked)` : "") +
        (reasons.length ? `. ${reasons.join(" · ")}` : ".");
      if (applied) {
        editor.view.dispatch(tr);
        setInstruction("");
        if (queueOps?.applyAndSync) {
          setAiNote("Applied — saving and refreshing…");
          const ok = await queueOps.applyAndSync(summary);
          if (!ok)
            setAiNote(
              "Applied in the editor, but the save failed — retry from the save status above.",
            );
          return; // on success the page is reloading; the note comes back after
        }
      }
      setAiReasons(reasons); // document order (ascending apply)
      setAiNote(summary);
    } catch (err) {
      setAiNote(`Failed: ${(err as Error).message}`);
    } finally {
      setAiBusy(false);
    }
  }, [instruction, aiBusy, editor, chapter, queueOps]);

  return (
    <div className="cx-details-tab">
      <section className="cx-details-block">
        <h3>Tell the AI</h3>
        <textarea
          className="cx-details-comment cx-instruct-box"
          aria-label="Tell the AI what to change in this chapter"
          placeholder="Say what you want changed in this chapter — e.g. “add diacritical marks to the citation”, “tighten the opening two paragraphs”…"
          value={instruction}
          disabled={aiBusy}
          onChange={(e) => setInstruction(e.target.value)}
        />
        <button
          type="button"
          className="cx-instruct-run"
          disabled={aiBusy || !instruction.trim()}
          onClick={() => void runInstruction()}
        >
          {aiBusy ? (
            <>
              <i
                className="fa-solid fa-circle-notch cx-autosave-spin"
                aria-hidden="true"
              />{" "}
              Working…
            </>
          ) : (
            <>
              <i className="fa-solid fa-wand-magic-sparkles" aria-hidden="true" />{" "}
              Make the changes
            </>
          )}
        </button>
        {aiNote && (
          <p className="cx-details-hint cx-instruct-note" role="status">
            {aiNote}
          </p>
        )}
        {aiReasons.length > 0 && (
          <ul className="cx-instruct-reasons">
            {aiReasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        )}
      </section>

      <section className="cx-details-block">
        <h3>
          Mark for follow-up
          {markedCount > 0 && (
            <span className="cx-count-badge">{markedCount}</span>
          )}
        </h3>
        {activeParaIdx === null && (
          <p className="cx-details-hint">
            Click into a paragraph (or select a phrase) to mark it.
          </p>
        )}
        {MARK_GROUPS.map((group) => (
          <div className="cx-mark-group" key={group.name}>
            <span className="cx-mark-group-name">{group.name}</span>
            <div className="cx-details-mark-row">
              {group.kinds.map((kind) => {
                const def = DEFERRED_BY_KIND[kind];
                if (!def) return null;
                return (
                  <button
                    key={def.kind}
                    type="button"
                    className="cx-btn-mark"
                    title={def.hint}
                    disabled={activeParaIdx === null}
                    onClick={() =>
                      stampAction(def, def.scope === "term" && !!selection)
                    }
                  >
                    <i className={`fa-solid ${def.icon}`} aria-hidden="true" />{" "}
                    {def.label}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
        <p className="cx-details-hint">
          Text marks can be run from the queue below. Knowledge and Visual
          marks are stored for a future pipeline pass — they wait until that
          pass exists.
        </p>
        {markedCount > 0 && (
          <ul className="cx-details-queue">
            {chapterActions.map((item) => {
              const def = DEFERRED_BY_KIND[item.action_kind];
              const snippet = item.term_text || item.anchor_text;
              const runnable = queueOps?.runnableKinds.includes(
                item.action_kind,
              );
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className="cx-queue-jump"
                    title="Jump to the marked text"
                    onClick={() => queueOps?.jumpTo(item.anchor_text)}
                  >
                    <strong>{def?.label ?? item.action_kind}</strong>
                    {snippet ? ` · ${snippet.slice(0, 60)}` : ""}
                  </button>
                  {runnable && queueOps && (
                    <button
                      type="button"
                      className="cx-queue-run"
                      title="Run this mark now with AI; accepting the result clears it"
                      onClick={() =>
                        queueOps.runNow(item.action_kind, item.anchor_text, () =>
                          removeActionFnRef.current(item.id),
                        )
                      }
                    >
                      Run now
                    </button>
                  )}
                  <button
                    type="button"
                    className="cx-queue-remove"
                    onClick={() => removeActionFnRef.current(item.id)}
                  >
                    Remove
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </section>

    </div>
  );
}
