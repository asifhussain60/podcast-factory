/**
 * useSectionDepth — section-level depth + tags (pipeline guesses, human
 * corrects): per-chapter load, ref-mirrored state for the decoration plugin,
 * and the ref-based writer the pickers call. Extracted verbatim from
 * StudioEditor.tsx (R2 pass 2 — one hook per commit).
 *
 * Contract notes (load-bearing, preserved exactly):
 *  - The PM decoration plugin reads sectionDepthsRef/sectionTagsRef and calls
 *    saveSectionDepthRef.current directly (module-level pickers) — the writer
 *    mutates the refs FIRST, then sets state, then dispatches refreshDepth so
 *    the plugin recomputes immediately (React batching would otherwise leave
 *    the refs stale until the next render).
 *  - The PATCH is fire-and-forget (non-blocking, offline-friendly).
 */
import { useEffect, useRef, useState } from "react";
import type { useEditor } from "@tiptap/react";

import { apiFetch } from "../../../lib/api-fetch";
import type { SaveDepthFn } from "./studio-editor-constants";

export function useSectionDepth(
  slug: string,
  chapter: string,
  editorRef: React.RefObject<ReturnType<typeof useEditor> | null>,
) {
  // Maps section ordinal → depth_level code string.
  const [sectionDepths, setSectionDepths] = useState<Record<number, string>>(
    {},
  );
  const sectionDepthsRef = useRef<Record<number, string>>({});
  sectionDepthsRef.current = sectionDepths;
  // Maps section ordinal → string[] of section tag IDs.
  const [sectionTagsMap, setSectionTagsMap] = useState<
    Record<number, string[]>
  >({});
  const sectionTagsRef = useRef<Record<number, string[]>>({});
  sectionTagsRef.current = sectionTagsMap;

  // Load section depths + tags from the API when chapter changes.
  useEffect(() => {
    if (!slug || !chapter) return;
    let cancelled = false;
    apiFetch<{
      sections?: {
        section_ordinal: number;
        depth_level: string;
        section_tags?: string[];
      }[];
    }>("/api/studio/section-depth", { query: { book: slug, chapter } })
      .then((json) => {
        if (cancelled || !json?.sections) return;
        const depthMap: Record<number, string> = {};
        const tagsMap: Record<number, string[]> = {};
        for (const s of json.sections) {
          depthMap[s.section_ordinal] = s.depth_level;
          tagsMap[s.section_ordinal] = Array.isArray(s.section_tags)
            ? s.section_tags
            : [];
        }
        setSectionDepths(depthMap);
        setSectionTagsMap(tagsMap);
      })
      .catch(() => {
        /* offline-friendly */
      });
    return () => {
      cancelled = true;
    };
  }, [slug, chapter]);

  // Persist a section depth change (human override).
  const saveSectionDepthRef = useRef<SaveDepthFn>(() => {});
  saveSectionDepthRef.current = (
    ordinal: number,
    slug_label: string,
    depthLevel: string,
    tags: string[],
  ) => {
    sectionDepthsRef.current = {
      ...sectionDepthsRef.current,
      [ordinal]: depthLevel,
    };
    sectionTagsRef.current = { ...sectionTagsRef.current, [ordinal]: tags };
    setSectionDepths({ ...sectionDepthsRef.current });
    setSectionTagsMap({ ...sectionTagsRef.current });
    editorRef.current?.view.dispatch(
      editorRef.current.state.tr.setMeta("refreshDepth", true),
    );
    apiFetch("/api/studio/section-depth", {
      method: "PATCH",
      body: {
        book: slug,
        chapter,
        ordinal,
        slug: slug_label,
        depth_level: depthLevel,
        tags,
      },
    }).catch(() => {
      /* non-blocking */
    });
  };

  return {
    sectionDepths,
    sectionDepthsRef,
    sectionTagsMap,
    sectionTagsRef,
    saveSectionDepthRef,
  };
}
