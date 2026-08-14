/**
 * book-composer-chapter-tools.ts — the two whole-chapter, selection-
 * independent tools on the Book Composer's Refinement tab: Rearticulate
 * (the pipeline's gated fidelity-checked rewrite engine) and Replace with
 * Arabic (the deterministic glossary substitution).
 *
 * Split out of book-composer.ts (DR-005 size ratchet). `deps` is the host's
 * live editor/chapter state, threaded in as getters so this module never
 * holds a stale snapshot of what book-composer.ts owns.
 */
import { confirmDialog, busyDialog } from "./confirm-dialog";
import { apiFetch } from "../lib/api-fetch";
import type { ChapterEditor } from "./book-md-editor";

export interface ChapterToolsDeps {
  getActiveEditor: () => ChapterEditor | null;
  getSelectedChapter: () => string;
  getChapterTitle: (chapterKey: string) => string;
  getSelectionText: () => { text: string; from: number; to: number } | null;
  flushActiveSave: () => Promise<boolean>;
  setAiStatus: (message: string, isError?: boolean) => void;
  reloadPreservingChapter: () => void;
  slug: string;
}

export function createChapterToolsController(deps: ChapterToolsDeps): {
  runRearticulate: (btn: HTMLButtonElement) => Promise<void>;
  runReplaceArabic: (btn: HTMLButtonElement) => Promise<void>;
} {
  const {
    getActiveEditor,
    getSelectedChapter,
    getChapterTitle,
    getSelectionText,
    flushActiveSave,
    setAiStatus,
    reloadPreservingChapter,
    slug,
  } = deps;

  // ── Rearticulate: whole-chapter rewrite through the pipeline's gated engine ──
  // The flow is deliberately page-reload-shaped (the Composer's normal re-sync
  // pattern, see reloadPreservingChapter): flush pending edits so the engine
  // reads what the author sees, lock the editor, shimmer while the detached
  // Python worker runs, then reload from disk. NO editor-document surgery — the
  // RCA-002 lesson is that live-editor writes racing book.md are how corruption
  // happens, so the editor is read-only for the whole run.
  let rearticulating = false;

  // ── Replace with Arabic: the deterministic glossary substitution ────────────
  // A PURE TRANSFORM applied to the live editor, exactly like Diacritics: send
  // the passage, get it back with its romanized glossary terms in Arabic script,
  // insert it, let the Composer's own autosave persist it.
  //
  // It used to confirm through a modal, write book.md server-side and reload the
  // page. All three were wrong. The modal asks about a deterministic, reversible,
  // free edit the author can undo with Cmd-Z. The server write under a live
  // editor is the RCA-002 shape. And the reload is why it read as broken: on a
  // book whose glossary cannot reach the words on screen the page bounced and
  // nothing changed, with nothing to say why.
  //
  // `unavailable` is what says why — the terms in the passage this book has no
  // Arabic for. That is the honest answer on `al-anwaar-al-lateefah`, whose
  // glossary holds 27 usable terms against roughly 250 italicised on the page.
  let substituting = false;

  async function runReplaceArabic(btn: HTMLButtonElement): Promise<void> {
    if (!getActiveEditor() || substituting) return;
    // The selection when there is one, the whole chapter when there is not.
    const sel = getSelectionText();
    const doc = getActiveEditor()!.editor.state.doc;
    const range = sel
      ? { from: sel.from, to: sel.to }
      : { from: 0, to: doc.content.size };
    const text = sel ? sel.text : doc.textBetween(0, doc.content.size, "\n\n");
    if (!text.trim()) {
      setAiStatus("Nothing to replace.", true);
      return;
    }
    substituting = true;
    btn.disabled = true;
    setAiStatus("Replacing romanized terms with Arabic…");
    try {
      const j = await apiFetch<{
        text: string;
        replaced: number;
        unavailable: string[];
      }>("/api/studio/replace-arabic", {
        method: "POST",
        body: { slug, text },
      });
      const n = Number(j.replaced ?? 0);
      const missing = Array.isArray(j.unavailable) ? j.unavailable : [];
      if (n > 0) {
        getActiveEditor()
          ?.editor.chain()
          .focus()
          .insertContentAt(range, String(j.text))
          .run();
      }
      const done = n
        ? `Replaced ${n} term${n === 1 ? "" : "s"} with Arabic.`
        : "No term here has Arabic in this book's glossary.";
      const note = missing.length
        ? ` No script for: ${missing.slice(0, 6).join(", ")}${missing.length > 6 ? "…" : ""}.`
        : "";
      setAiStatus(done + note, n === 0);
    } catch (e) {
      setAiStatus(`Replace with Arabic failed: ${(e as Error).message}`, true);
    } finally {
      substituting = false;
      btn.disabled = false;
    }
  }

  async function runRearticulate(btn: HTMLButtonElement): Promise<void> {
    if (!getActiveEditor() || rearticulating) return;
    const selectedChapter = getSelectedChapter();
    const title = getChapterTitle(selectedChapter);
    const go = await confirmDialog({
      title: "Rearticulate this chapter?",
      titleIcon: "fa-solid fa-feather-pointed",
      body: `“${title}” is rewritten in place as simple, articulate English.`,
      points: [
        {
          icon: "fa-solid fa-quote-left",
          text: "Speeches and quotations keep their speakers and their content.",
        },
        {
          icon: "fa-solid fa-mountain-sun",
          text: "Imagery stays imagery — nothing is flattened into abstraction.",
        },
        {
          icon: "fa-solid fa-language",
          text: "Arabic script is preserved verbatim, never romanized away.",
        },
        {
          icon: "fa-solid fa-shield-halved",
          text: "A result that fails the fidelity gates reverts automatically.",
        },
      ],
      footnote:
        "Takes a few minutes. The chapter is locked while the rewrite runs.",
      confirmLabel: "Rearticulate",
    });
    if (!go) return;
    const flushed = await flushActiveSave();
    if (!flushed) {
      setAiStatus(
        "Autosave is failing — resolve that before rearticulating.",
        true,
      );
      return;
    }
    rearticulating = true;
    btn.disabled = true;
    const editorDom = getActiveEditor()!.editor.view.dom as HTMLElement;
    getActiveEditor()!.editor.setEditable(false);
    editorDom.classList.add("cx-rearticulating");
    // Blocking progress modal for the whole run — on success it stays up
    // through the page reload, so the page never looks interactive while its
    // content is stale.
    const busy = busyDialog({
      title: "Rearticulating the chapter…",
      status: `“${title}”`,
      icon: "fa-solid fa-feather-pointed",
      note: "Rewriting as simple, articulate English behind the fidelity gates — this can take a few minutes.",
    });

    const unlock = (msg: string, isError: boolean) => {
      busy.close();
      rearticulating = false;
      btn.disabled = false;
      editorDom.classList.remove("cx-rearticulating");
      getActiveEditor()?.editor.setEditable(true);
      setAiStatus(msg, isError);
    };

    try {
      await apiFetch("/api/studio/rearticulate", {
        method: "POST",
        body: { slug, chapterKey: selectedChapter },
      });
    } catch (e) {
      unlock(`Rearticulate failed to start: ${String(e)}`, true);
      return;
    }

    // Poll the worker. A long chapter windows into several claude calls at up
    // to 900 s each, so the ceiling is generous; the GET converts a dead worker
    // into state:"error", so this loop cannot shimmer forever.
    const DEADLINE = Date.now() + 120 * 60 * 1000;
    const poll = async (): Promise<void> => {
      if (Date.now() > DEADLINE) {
        unlock(
          "Rearticulate timed out — check the book before retrying.",
          true,
        );
        return;
      }
      let status: Record<string, unknown>;
      try {
        status = (await apiFetch(
          `/api/studio/rearticulate?slug=${encodeURIComponent(slug)}`,
        )) as Record<string, unknown>;
      } catch {
        window.setTimeout(poll, 5000); // transient poll failure — keep waiting
        return;
      }
      if (status.state === "running" || status.state === "none") {
        const secs = Math.round(
          (Date.now() - (DEADLINE - 120 * 60 * 1000)) / 1000,
        );
        busy.update(
          `“${title}” — ${Math.floor(secs / 60)}m ${secs % 60}s elapsed`,
        );
        window.setTimeout(poll, 4000);
        return;
      }
      if (status.state === "error") {
        unlock(
          `Rearticulate failed: ${String(status.error ?? "unknown error")}`,
          true,
        );
        return;
      }
      const record = (status.record ?? {}) as Record<string, unknown>;
      if (record.status === "reverted") {
        const gates = Array.isArray(record.gates) ? record.gates : [];
        unlock(
          `Rearticulation reverted by the fidelity gates — the chapter is unchanged. ${String(gates[0] ?? "")}`,
          true,
        );
        return;
      }
      // adapted or partial: book.md changed on disk; re-sync the page the
      // Composer's normal way. The editor and the modal stay up — the page's
      // content is stale until the reload lands.
      busy.update("Done — reloading the chapter…");
      setAiStatus("Rearticulated. Reloading the chapter…");
      reloadPreservingChapter();
    };
    window.setTimeout(poll, 4000);
  }

  return { runRearticulate, runReplaceArabic };
}
