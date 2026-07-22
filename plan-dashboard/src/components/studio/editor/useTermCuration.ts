/**
 * useTermCuration — the three AI term-proposal flows ("Arabic", "English",
 * "Explain" immediate actions): proposal/busy/error state, the propose calls
 * (/api/ai/arabic-term, /api/ai/english-term, /api/ai/explain), the confirm/
 * apply handlers with position re-verification before replacing the selection,
 * the across-chapter/book replace variants (via /api/studio/replace), the
 * arabic-review curation save (/api/studio/arabic-review), and the dismiss
 * handlers. Extracted verbatim from StudioEditor.tsx (R2 pass 2 — one hook
 * per commit).
 *
 * Contract notes (load-bearing, preserved exactly):
 *  - /api/ai/arabic-term and /api/ai/explain use the hand-rolled ok-shape
 *    (typed apiFetch envelope with an `error` key checked on 200);
 *    /api/ai/english-term is the strict envelope with the unwrapped
 *    `payload.english`. All three keep their exact response handling.
 *  - Position re-verification before applying (textBetween(from, to) must
 *    still equal the proposed `original`) is preserved byte-for-byte.
 *  - saveEnglishCuration is non-blocking by design — a failed curation save
 *    never stops the text replacement; it also fires the
 *    "arabic-curation:saved" CustomEvent the review panel listens for.
 *  - replaceInEditorDoc is passed in: it belongs to the find-and-replace
 *    cluster that remains in StudioEditor; the across-variants reuse it to
 *    mirror the canonical-file replace into the live doc.
 *  - fetchErrorText is passed in: it is shared with the Replace/Noise
 *    clusters that remain in StudioEditor (same as useAiActions).
 *  - Dependency arrays are verbatim from the component (exhaustive-deps is
 *    advisory; identities of the passed-in helpers are unchanged).
 */
import { useCallback, useState } from "react";
import type { useEditor } from "@tiptap/react";

import { apiFetch } from "../../../lib/api-fetch";
import type { GlossaryEntry } from "./studio-editor-constants";

interface TermCurationArgs {
  editor: ReturnType<typeof useEditor>;
  isReadOnlyStage: boolean;
  chapterTitle: string;
  slug: string;
  chapter: string;
  /** Glossary lookup (exact/latin-insensitive match over all fields). */
  findGlossaryTerm: (raw: string) => GlossaryEntry | null;
  /** Mirrors a confirmed canonical-file replace into the live editor doc. */
  replaceInEditorDoc: (pairs: { find: string; replace: string }[]) => void;
  /** Shared module-level error formatter (stable identity). */
  fetchErrorText: (e: unknown) => string;
  /** Component-level tick bump so the JSX re-reads editor state after apply. */
  refresh: () => void;
}

export function useTermCuration({
  editor,
  isReadOnlyStage,
  chapterTitle,
  slug,
  chapter,
  findGlossaryTerm,
  replaceInEditorDoc,
  fetchErrorText,
  refresh,
}: TermCurationArgs) {
  // "Arabic" immediate action — AI proposes a contextual Arabic term for the
  // highlighted text; the human confirms before it replaces the selection.
  // Positions are captured at propose-time and re-verified before applying.
  const [arabicProposal, setArabicProposal] = useState<{
    from: number;
    to: number;
    original: string;
    arabic: string;
    gloss: string;
    kind: string;
  } | null>(null);
  const [arabicBusy, setArabicBusy] = useState(false);
  const [arabicError, setArabicError] = useState("");
  // Result line after an across-chapter / across-book Arabic replace.
  const [arabicDone, setArabicDone] = useState("");

  // "English" immediate action — AI/glossary proposes the correct contextual
  // English rendering for a highlighted Arabic script or romanized term.
  const [englishProposal, setEnglishProposal] = useState<{
    from: number;
    to: number;
    original: string;
    english: string;
    gloss: string;
    phonetic?: string;
  } | null>(null);
  const [englishBusy, setEnglishBusy] = useState(false);
  const [englishError, setEnglishError] = useState("");

  // "Explain" immediate action — AI rewrites the highlighted excerpt into a
  // clearer, fuller version (kept in chapter context); the human reviews/edits
  // the proposed text before it replaces the selection.
  const [explainProposal, setExplainProposal] = useState<{
    from: number;
    to: number;
    original: string;
    text: string;
  } | null>(null);
  const [explainBusy, setExplainBusy] = useState(false);
  const [explainError, setExplainError] = useState("");

  // Paragraph text containing the current selection — context for the Arabic AI call.
  const selectionContext = useCallback((): string => {
    if (!editor) return "";
    const headPos = editor.state.selection.$head.pos;
    let ctx = "";
    let pos = 0;
    editor.state.doc.forEach((n) => {
      const nodeEnd = pos + n.nodeSize;
      if (headPos >= pos && headPos < nodeEnd) ctx = n.textContent;
      pos = nodeEnd;
    });
    return ctx;
  }, [editor]);

  // Propose an Arabic term for the highlighted selection (does NOT edit yet).
  const proposeArabic = useCallback(async () => {
    if (!editor || isReadOnlyStage) return;
    const { from, to } = editor.state.selection;
    const original = editor.state.doc.textBetween(from, to, " ").trim();
    if (!original || from === to) return;
    setArabicBusy(true);
    setArabicError("");
    setArabicProposal(null);
    setArabicDone("");
    setEnglishProposal(null);
    setExplainProposal(null);
    try {
      const json = await apiFetch<{
        arabic?: string;
        gloss?: string;
        kind?: string;
        error?: string;
      }>("/api/ai/arabic-term", {
        method: "POST",
        body: {
          text: original,
          context: selectionContext(),
          bookTitle: chapterTitle,
        },
      });
      if (!json?.arabic) {
        setArabicError(json?.error ?? "Request failed (200)");
      } else {
        setArabicProposal({
          from,
          to,
          original,
          arabic: json.arabic,
          gloss: json.gloss ?? "",
          kind: json.kind ?? "translation",
        });
      }
    } catch (e) {
      setArabicError(fetchErrorText(e));
    } finally {
      setArabicBusy(false);
    }
  }, [editor, isReadOnlyStage, selectionContext, chapterTitle]);

  const saveEnglishCuration = useCallback(
    async (phonetic: string | undefined, english: string) => {
      if (!phonetic || !english.trim()) return;
      try {
        const updated = await apiFetch<unknown>("/api/studio/arabic-review", {
          method: "POST",
          body: {
            slug,
            phonetic,
            decision: "replace_english",
            english_override: english.trim(),
            decided_by: "studio",
          },
        });
        window.dispatchEvent(
          new CustomEvent("arabic-curation:saved", { detail: updated }),
        );
      } catch {
        /* non-blocking — the text replacement still applies */
      }
    },
    [slug],
  );

  const proposeEnglish = useCallback(async () => {
    if (!editor || isReadOnlyStage) return;
    const { from, to } = editor.state.selection;
    const original = editor.state.doc.textBetween(from, to, " ").trim();
    if (!original || from === to) return;
    const term = findGlossaryTerm(original);
    const saved = (term?.english_override || "").trim();
    setEnglishBusy(true);
    setEnglishError("");
    setEnglishProposal(null);
    setArabicProposal(null);
    setArabicDone("");
    setExplainProposal(null);
    if (saved) {
      setEnglishProposal({
        from,
        to,
        original,
        english: saved,
        gloss: "Saved glossary rendering.",
        phonetic: term?.phonetic,
      });
      setEnglishBusy(false);
      return;
    }
    try {
      const arabic =
        term?.corrected_arabic ||
        term?.arabic_script ||
        (/[\u0600-\u06FF]/.test(original) ? original : "");
      const lookup = term?.transliteration || term?.phonetic || original;
      const json = await apiFetch<{
        english?: string;
        gloss?: string;
        error?: string;
      }>("/api/ai/english-term", {
        method: "POST",
        body: { text: lookup, arabic, bookTitle: chapterTitle },
      });
      if (!json?.english) {
        setEnglishError(json?.error ?? "Request failed (200)");
      } else {
        setEnglishProposal({
          from,
          to,
          original,
          english: json.english,
          gloss: json.gloss ?? "",
          phonetic: term?.phonetic,
        });
      }
    } catch (e) {
      setEnglishError(fetchErrorText(e));
    } finally {
      setEnglishBusy(false);
    }
  }, [editor, isReadOnlyStage, findGlossaryTerm, chapterTitle]);

  // Apply the confirmed proposal: replace the original range with the Arabic term,
  // but only if the text at those positions is unchanged since proposing.
  const applyArabic = useCallback(() => {
    if (!editor || !arabicProposal) return;
    const { from, to, original, arabic } = arabicProposal;
    const text = arabic.trim();
    if (!text) {
      setArabicError("Enter the Arabic text first.");
      return;
    }
    const current = editor.state.doc.textBetween(from, to, " ").trim();
    if (current !== original) {
      setArabicError("Selection changed — highlight the word again.");
      setArabicProposal(null);
      return;
    }
    editor.view.dispatch(
      editor.state.tr.replaceWith(from, to, editor.state.schema.text(text)),
    );
    setArabicProposal(null);
    setArabicError("");
    refresh();
  }, [editor, arabicProposal]);

  const cancelArabic = useCallback(() => {
    setArabicProposal(null);
    setArabicError("");
    setArabicDone("");
  }, []);

  const applyEnglish = useCallback(async () => {
    if (!editor || !englishProposal) return;
    const { from, to, original, english, phonetic } = englishProposal;
    const replacement = english.trim();
    if (!replacement) {
      setEnglishError("Enter the English rendering first.");
      return;
    }
    const current = editor.state.doc.textBetween(from, to, " ").trim();
    if (current !== original) {
      setEnglishError("Selection changed — highlight the word again.");
      setEnglishProposal(null);
      return;
    }
    await saveEnglishCuration(phonetic, replacement);
    editor.view.dispatch(
      editor.state.tr.replaceWith(
        from,
        to,
        editor.state.schema.text(replacement),
      ),
    );
    setEnglishProposal(null);
    setEnglishError("");
    refresh();
  }, [editor, englishProposal, saveEnglishCuration]);

  const cancelEnglish = useCallback(() => {
    setEnglishProposal(null);
    setEnglishError("");
  }, []);

  // Propose a clearer, fuller version of the highlighted excerpt (does NOT edit
  // yet). The whole chapter is sent as context so the AI stays inside it.
  const proposeExplain = useCallback(async () => {
    if (!editor || isReadOnlyStage) return;
    const { from, to } = editor.state.selection;
    const original = editor.state.doc.textBetween(from, to, " ").trim();
    if (!original || from === to) return;
    let chapterText = "";
    editor.state.doc.forEach((n) => {
      chapterText += `${n.textContent}\n\n`;
    });
    setExplainBusy(true);
    setExplainError("");
    setExplainProposal(null);
    setArabicProposal(null);
    setArabicDone("");
    setEnglishProposal(null);
    try {
      const json = await apiFetch<{ text?: string; error?: string }>(
        "/api/ai/explain",
        {
          method: "POST",
          body: {
            text: original,
            chapter: chapterText.trim(),
            bookTitle: chapterTitle,
          },
        },
      );
      if (!json?.text) {
        setExplainError(json?.error ?? "Request failed (200)");
      } else {
        setExplainProposal({ from, to, original, text: json.text });
      }
    } catch (e) {
      setExplainError(fetchErrorText(e));
    } finally {
      setExplainBusy(false);
    }
  }, [editor, isReadOnlyStage, chapterTitle]);

  // Apply the (edited) explanation: replace the original range, but only if the
  // text at those positions is unchanged since proposing.
  const applyExplain = useCallback(() => {
    if (!editor || !explainProposal) return;
    const { from, to, original, text } = explainProposal;
    const replacement = text.trim();
    if (!replacement) {
      setExplainError("The explanation is empty.");
      return;
    }
    const current = editor.state.doc.textBetween(from, to, " ").trim();
    if (current !== original) {
      setExplainError("Selection changed — highlight the passage again.");
      setExplainProposal(null);
      return;
    }
    editor.view.dispatch(
      editor.state.tr.replaceWith(
        from,
        to,
        editor.state.schema.text(replacement),
      ),
    );
    setExplainProposal(null);
    setExplainError("");
    refresh();
  }, [editor, explainProposal]);

  const cancelExplain = useCallback(() => {
    setExplainProposal(null);
    setExplainError("");
  }, []);

  // Replace EVERY occurrence of the original term with the (edited) Arabic — across
  // this chapter or the whole book — via the same canonical-file replace endpoint
  // used by find-and-replace, then mirror the change into the live editor doc.
  const applyArabicAcross = useCallback(
    async (scope: "chapter" | "book") => {
      if (!editor || !arabicProposal) return;
      const replace = arabicProposal.arabic.trim();
      if (!replace) {
        setArabicError("Enter the Arabic text first.");
        return;
      }
      const find = arabicProposal.original;
      setArabicBusy(true);
      setArabicError("");
      try {
        const j = await apiFetch<{
          total?: number;
          results?: { chapter: string; count: number }[];
        }>("/api/studio/replace", {
          method: "POST",
          body: {
            slug,
            scope,
            chapter,
            pairs: [{ find, replace }],
            apply: true,
          },
        });
        if (!isReadOnlyStage) replaceInEditorDoc([{ find, replace }]);
        const nCh = (j.results ?? []).length;
        const total = j.total ?? 0;
        setArabicDone(
          total === 0
            ? "No matches found — nothing changed."
            : `Replaced ${total} instance${total === 1 ? "" : "s"} across ${nCh} chapter${nCh === 1 ? "" : "s"}.`,
        );
        setArabicProposal(null);
        refresh();
      } catch (e) {
        setArabicError(fetchErrorText(e));
      } finally {
        setArabicBusy(false);
      }
    },
    [
      editor,
      arabicProposal,
      slug,
      chapter,
      isReadOnlyStage,
      replaceInEditorDoc,
    ],
  );

  const applyEnglishAcross = useCallback(
    async (scope: "chapter" | "book") => {
      if (!editor || !englishProposal) return;
      const replace = englishProposal.english.trim();
      if (!replace) {
        setEnglishError("Enter the English rendering first.");
        return;
      }
      const find = englishProposal.original;
      setEnglishBusy(true);
      setEnglishError("");
      try {
        await apiFetch("/api/studio/replace", {
          method: "POST",
          body: {
            slug,
            scope,
            chapter,
            pairs: [{ find, replace }],
            apply: true,
          },
        });
        await saveEnglishCuration(englishProposal.phonetic, replace);
        if (!isReadOnlyStage) replaceInEditorDoc([{ find, replace }]);
        setEnglishProposal(null);
        refresh();
      } catch (e) {
        setEnglishError(fetchErrorText(e));
      } finally {
        setEnglishBusy(false);
      }
    },
    [
      editor,
      englishProposal,
      slug,
      chapter,
      isReadOnlyStage,
      replaceInEditorDoc,
      saveEnglishCuration,
    ],
  );

  return {
    arabicProposal,
    setArabicProposal,
    arabicBusy,
    arabicError,
    arabicDone,
    englishProposal,
    setEnglishProposal,
    englishBusy,
    englishError,
    explainProposal,
    setExplainProposal,
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
  };
}
