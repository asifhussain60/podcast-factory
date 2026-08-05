/**
 * useEditorPrefs — reading-comfort controls (font, text size, paper tint).
 * View-only preferences, persisted to the shared cx-editor-* localStorage keys
 * so a choice made here carries to/from the Book Composer. Extracted verbatim
 * from StudioEditor.tsx (R2 pass 2 — one hook per commit).
 */
import { useEffect, useState } from "react";

import {
  EDITOR_FONT_IDS,
  EDITOR_PAPER_IDS,
  readEditorPref,
  readEditorSize,
} from "./studio-editor-constants";

export function useEditorPrefs() {
  const [editorFont, setEditorFont] = useState<string>(() =>
    readEditorPref("cx-editor-font", "sans", EDITOR_FONT_IDS),
  );
  const [editorPaper, setEditorPaper] = useState<string>(() =>
    readEditorPref("cx-editor-paper", "light", EDITOR_PAPER_IDS),
  );
  const [editorSize, setEditorSize] = useState<number>(() => readEditorSize());
  useEffect(() => {
    try {
      localStorage.setItem("cx-editor-font", editorFont);
    } catch {
      /* best-effort */
    }
  }, [editorFont]);
  useEffect(() => {
    try {
      localStorage.setItem("cx-editor-paper", editorPaper);
    } catch {
      /* best-effort */
    }
  }, [editorPaper]);
  useEffect(() => {
    try {
      localStorage.setItem("cx-editor-size", String(editorSize));
    } catch {
      /* best-effort */
    }
  }, [editorSize]);

  return {
    editorFont,
    setEditorFont,
    editorPaper,
    setEditorPaper,
    editorSize,
    setEditorSize,
  };
}
