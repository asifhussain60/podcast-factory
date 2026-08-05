/**
 * compose-editor-bridge.ts — the live-state handoff between the Book
 * Composer's vanilla chapter editor (book-composer.ts) and the React tool
 * islands mounted in its inspector tabs (the Companion, Refinement-extras,
 * and Details tabs). Both sides read/write the SAME per-chapter mutable-box
 * object, so the shared StudioDecos decoration factory (studio-decos.ts) —
 * itself framework-agnostic — sees live state regardless of which side wrote
 * it last, exactly the same contract StudioEditor.tsx already relies on for
 * its own refs.
 *
 * One bridge per chapter: book-composer.ts creates a fresh one on every
 * chapter switch so no state (comments, section tags, focus) leaks across
 * chapters. Compose has no pipeline "stage" concept (it edits the finished
 * book/book.md directly, not a pre-finalization draft), so showPrevDiffRef
 * always stays false and prevStageTextsRef is never read — the human-edit
 * diff (originalRef vs. the live doc) is the only diff view Compose needs.
 */
import type {
  DepthLevel,
  GlossaryEntry,
} from "../components/studio/editor/studio-editor-constants";
import type { StudioDecosBag } from "../components/studio/editor/studio-decos";

export type ComposeEditorBridge = StudioDecosBag;

export function createComposeEditorBridge(
  depthLevels: readonly DepthLevel[],
  glossarySorted: GlossaryEntry[],
): ComposeEditorBridge {
  return {
    originalRef: { current: [] },
    actionsRef: { current: [] },
    hasFocusRef: { current: false },
    activeSectionOrdinalRef: { current: null },
    sectionDepthsRef: { current: {} },
    sectionTagsRef: { current: {} },
    saveSectionDepthRef: { current: () => {} },
    editorRef: { current: null },
    runAiFnRef: { current: () => {} },
    removeActionFnRef: { current: () => {} },
    showPrevDiffRef: { current: false },
    // Human track changes are OFF by default here (2026-07-27). Compose is a
    // WRITING surface: accepting an AI rewrite repainted the whole paragraph as
    // strikethrough-plus-underline, so the version just chosen was the hardest
    // to read. The "Show changes" toggle in the editor toolbar turns them on for
    // as long as they are wanted, and the choice persists per browser.
    showEditDiffRef: { current: false },
    prevStageTextsRef: { current: [] },
    // OFF in the Composer (Asif, 2026-08-02). This decoration replaces a
    // romanized glossary term with an Arabic chip and hides the romanization in
    // an `.ar-hidden` span — but the rule that hides it, in
    // studio-editor-core.css, is scoped to `.studio-editor__editor`, the Edit &
    // Enrich wrapper. The Composer's host is `.cx-edit-host`, so the rule never
    // applied and BOTH scripts rendered on top of each other
    // ("theالْإِمَامَةimamate"). Latent since the Composer adopted this plugin,
    // and invisible only while the glossary was parsing as zero entries.
    //
    // Fixing the CSS scope was the obvious repair and is the wrong one. The
    // Composer is the surface Asif verifies the PRINTED book on, so it must show
    // what `book.md` actually says: Arabic that exists only as a view-time
    // decoration would report a book as fixed while the file still carries the
    // romanization — exactly the question being worked right now. Arabic reaches
    // the page through the compose pipeline or it does not reach it at all.
    arabicRef: { current: false },
    depthLevels,
    glossarySorted,
  };
}
