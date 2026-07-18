/**
 * StudioEditor.tsx — WC8 Studio (spike → real build). TipTap/ProseMirror foundation.
 *
 * Feel-check feedback FC-1/FC-3/FC-4 applied (2026-05-29):
 *   FC-1  Verse refs render as a COMPACT chapter:verse chip (e.g. 99:7-8) appended
 *         after the natural-language reference — the prose is NEVER mutated (so the
 *         NotebookLM source still reads "Surah Az-Zalzalah, verses 7 to 8"). The chip
 *         is the hover target (data-surah/data-verse → reused QuranPopover).
 *   FC-3  Change-tracking is Microsoft-Word track-changes: jsdiff WORD-level insertions
 *         (underlined) + deletions (strikethrough widget), persisted off-cursor. Every
 *         paragraph shows a hover affordance (CSS); clicking selects only that paragraph
 *         (active-paragraph decoration).
 *   FC-4  Arabic toggle: when on, glossary phonetic tokens are swapped to Arabic script
 *         (clean Amiri webfont, distinct colour) via decorations — non-destructive.
 *
 * Manual actions (edits, tags) are the learning-loop training signal. External CSS only.
 * Library policy frozen: @tiptap/* + @floating-ui/react + diff(jsdiff) — no new libs.
 */
import {
  useState,
  useRef,
  useMemo,
  useCallback,
  useEffect,
  type CSSProperties,
} from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Extension } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as PMNode } from "@tiptap/pm/model";
import { diffWords } from "diff";
import * as Toast from "@radix-ui/react-toast";
import { ApiFetchError, apiFetch } from "../../../lib/api-fetch";
import { stageRole } from "../../../lib/reader/stage-roles";
import type { EnrichmentSummary } from "../../../lib/reader/enrichment-ledger";
import TransformationDashboard from "./TransformationDashboard";

import {
  ACTION_BY_KIND,
  ACTION_REGISTRY,
  ARABIC_PAIR_RE,
  ARABIC_SCRIPT_RUN,
  DEFAULT_DEPTH_PROFILE,
  DEPTH_LEVELS_BY_PROFILE,
  EDITOR_FONTS,
  EDITOR_PAPERS,
  EDITOR_SIZE_MAX,
  EDITOR_SIZE_MIN,
  SECTION_TAGS,
  SURAH_MAP,
  SURAH_VERSE_RE,
  scanMarkers,
  truncate,
  type ActionDef,
  type ClientActionItem,
  type GlossaryEntry,
  type SaveDepthFn,
} from "./studio-editor-constants";
import { MarkerHighlight } from "./marker-highlight";
import { useAutosaveDraft } from "./useAutosaveDraft";
import { useEditorPrefs } from "./useEditorPrefs";
import { useSectionDepth } from "./useSectionDepth";
import { useStageApproval } from "./useStageApproval";
import { openDepthPicker, openTagPicker } from "./studio-editor-pickers";
import type { Chapter, Lineage, PipelineStep } from "./studio-editor-types";

// Preserve the pre-split export surface (Lineage was exported from this file).
export type { Lineage };

/**
 * R2 apiFetch migration: reconstruct the exact error string each call site
 * displayed pre-migration — the server's message for HTTP-level failures
 * (what `json.error` carried), and `String(cause)` for transport failures
 * (what `catch (e) { String(e) }` produced around a raw fetch()).
 */
function fetchErrorText(e: unknown): string {
  if (e instanceof ApiFetchError)
    return e.status === 0 ? String(e.cause ?? e) : e.message;
  return String(e);
}

interface Props {
  slug: string;
  chapters: Chapter[];
  glossary?: GlossaryEntry[];
  glossaryAll?: GlossaryEntry[];
  initialChapIdx?: number;
  contentProfile?: string;
  /** Archived view-only stage lineages (e.g. an earlier episode structure). */
  archivedLineages?: Lineage[];
  /** Pipeline phases for the left-rail timeline. */
  pipelineSteps?: PipelineStep[];
  /** The phase this page represents (the rail expands its versions here). */
  activeStep?: string;
  /** Book-level enrichment summary for the transformation dashboard. */
  enrichment?: EnrichmentSummary | null;
  /** Count of Arabic-overlay glossary terms (transformation dashboard footnote). */
  glossaryCount?: number;
}

export default function StudioEditor({
  slug,
  chapters,
  glossary = [],
  glossaryAll = glossary,
  initialChapIdx = 0,
  contentProfile,
  archivedLineages = [],
  pipelineSteps: _pipelineSteps = [],
  activeStep: _activeStep = "edit",
  enrichment = null,
  glossaryCount = 0,
}: Props) {
  const depthLevels =
    DEPTH_LEVELS_BY_PROFILE[contentProfile ?? DEFAULT_DEPTH_PROFILE] ??
    DEPTH_LEVELS_BY_PROFILE[DEFAULT_DEPTH_PROFILE];

  // Lineage = a coherent stage set. 'current' is the live rebuild; archived
  // lineages (earlier full-stage runs) are view-only. The timeline rail swaps
  // between them; archived lineages are never editable.
  const lineages = useMemo<Lineage[]>(
    () => [
      { id: "current", label: "Current rebuild", chapters },
      ...archivedLineages,
    ],
    [chapters, archivedLineages],
  );
  const [activeLineageId] = useState("current");
  const activeLineage =
    lineages.find((l) => l.id === activeLineageId) ?? lineages[0];
  const isArchivedView = activeLineage.id !== "current";
  const viewChapters = activeLineage.chapters;

  // B: chapter switcher — pick which chapter's stages the editor shows.
  const [chapIdx, setChapIdx] = useState(initialChapIdx);
  const chap = viewChapters[chapIdx] ?? viewChapters[0];
  const stages = chap.stages;
  const metrics = chap.metrics;
  const chapter = chap.slug;
  const chapterTitle = chap.title;

  // The timeline's top step ("Review") is the last AVAILABLE stage — the one under
  // human review (editable); every older stage is a read-only comparison view.
  // Archived lineages are wholly read-only.
  const editableStageId =
    [...stages].reverse().find((s) => s.available)?.id ?? stages[0]?.id;
  const [stageId, setStageId] = useState<string>(editableStageId);
  const stage = stages.find((s) => s.id === stageId) ?? stages[0];
  const html = stage?.html ?? "";
  const isReadOnlyStage = stageId !== editableStageId || isArchivedView;
  // Does this chapter+stage have an unapproved draft on disk? (Seeded server-side;
  // the editor's current content already IS the draft when this is true.)
  const hasDraftForStage = !!(stage && (chap.drafted?.[stage.id] ?? false));

  // On chapter/lineage switch: reset to that chapter's editable stage and tell
  // the editorial cockpit (Slice 5b) to follow this chapter. (The approval +
  // finalize reload lives in useStageApproval — R2 pass 2.)
  useEffect(() => {
    setStageId(
      [...chap.stages].reverse().find((s) => s.available)?.id ??
        chap.stages[0]?.id,
    );
    window.dispatchEvent(
      new CustomEvent("studio:chapter-change", {
        detail: { chapter: chap.slug },
      }),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chapIdx, activeLineageId]);

  // Reading-comfort controls — extracted to useEditorPrefs (R2 pass 2).
  const {
    editorFont,
    setEditorFont,
    editorPaper,
    setEditorPaper,
    editorSize,
    setEditorSize,
  } = useEditorPrefs();

  // Per-paragraph comments: index → text. Stored in a ref for the PM plugin,
  // mirrored in state so the inspector panel re-renders.
  const commentsRef = useRef<Map<number, string>>(new Map());
  const [, setCommentsKey] = useState(0);
  const refreshComments = () => setCommentsKey((k) => k + 1);

  // Deferred AI action-item marks for the active chapter (persisted in the
  // knowledge DB; the CLI drain pass reads them). Held in a ref so PM widgets
  // built outside React always see the latest, mirrored to state for re-render.
  const actionsRef = useRef<ClientActionItem[]>([]);
  const [, setActionsKey] = useState(0);
  const refreshActions = () => setActionsKey((k) => k + 1);

  // Active paragraph index (inspector drives the comment textarea + tag panel).
  const [activeParaIdx, setActiveParaIdx] = useState<number | null>(null);
  // Active section ordinal (0-based h2 index) — drives AI actions and section highlight.
  const [activeSectionOrdinal, setActiveSectionOrdinal] = useState<
    number | null
  >(null);
  const activeSectionOrdinalRef = useRef<number | null>(null);
  activeSectionOrdinalRef.current = activeSectionOrdinal;

  // M-1 — Inspector tab state (Details · Comment · AI · References).
  const [inspectorTab, setInspectorTab] = useState<
    "details" | "comment" | "ai" | "refs"
  >("details");

  // Load action-item marks when the chapter changes. Clear synchronously first so
  // the previous chapter's marks never flash on the new chapter.
  useEffect(() => {
    if (!slug || !chapter) return;
    let cancelled = false;
    actionsRef.current = [];
    refreshActions();
    apiFetch<{ ok?: boolean; items?: ClientActionItem[] }>(
      "/api/studio/action-items",
      { query: { book: slug, chapter } },
    )
      .then((json) => {
        if (cancelled || !json?.ok || !Array.isArray(json.items)) return;
        actionsRef.current = json.items as ClientActionItem[];
        refreshActions();
        editorRef.current?.view.dispatch(
          editorRef.current.state.tr.setMeta("refreshTags", true),
        );
      })
      .catch(() => {
        /* offline-friendly */
      });
    return () => {
      cancelled = true;
    };
  }, [slug, chapter]);

  // editorRef: stable ref to the editor instance so non-React callbacks (PM widgets)
  // can dispatch transactions without capturing a stale `editor` closure.
  const editorRef = useRef<ReturnType<typeof useEditor>>(null);

  // Section depth + tags — extracted to useSectionDepth (R2 pass 2). The
  // decoration plugin reads the refs; the pickers call saveSectionDepthRef.
  const { sectionDepthsRef, sectionTagsRef, saveSectionDepthRef } =
    useSectionDepth(slug, chapter, editorRef);

  // Wave L-8 — AI assist panel + Finalize state.
  const [aiBusy, setAiBusy] = useState(false);
  const [aiKind, setAiKind] = useState("");
  const [aiResult, setAiResult] = useState(""); // research / autotag plain text
  const [aiOptions, setAiOptions] = useState<string[]>([]); // rewrite option cards
  const [aiError, setAiError] = useState("");

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

  // serializeToMarkdown / saveAndApprove / discardChanges declared after useEditor (below).

  // "View all chapters" mode — combines every chapter's current-tab content in the editor.
  // Dropdown is disabled; editor is read-only; Save/Approve hidden.
  const [viewAll, setViewAll] = useState(false);

  const buildCombinedHtml = useCallback(
    (sid: string) =>
      viewChapters
        .map((ch, i) => {
          const s =
            ch.stages.find((st) => st.id === sid && st.available) ??
            ch.stages.filter((st) => st.available).at(-1);
          const body =
            s?.html ??
            "<p><em>Stage not yet produced for this chapter.</em></p>";
          const sep = i < viewChapters.length - 1 ? "<hr>" : "";
          return `<h2>${ch.title}</h2>${body}${sep}`;
        })
        .join(""),
    [viewChapters],
  );

  const [selection, setSelection] = useState("");
  const [arabicOn, setArabicOn] = useState(true); // Arabic overlay ON by default (Islamic review default)
  const [, setTick] = useState(0);
  const refresh = () => setTick((t) => t + 1);

  const originalRef = useRef<string[]>([]); // original text per top-level node
  const arabicRef = useRef(true); // mirror of arabicOn for the plugin (ON by default)
  const hasFocusRef = useRef(false); // tracks editor DOM focus for para-active
  const editorContainerRef = useRef<HTMLElement | null>(null);
  const inspectorRef = useRef<HTMLElement | null>(null); // right inspector panel
  arabicRef.current = arabicOn;
  // Per-stage diff: when a read-only step is selected, the decoration plugin can diff each
  // paragraph against the PREVIOUS stage's text (prevStageTextsRef) instead of the human-edit
  // original — so "Show changes from {prev stage}" highlights what THAT step changed.
  const showPrevDiffRef = useRef(false);
  const prevStageTextsRef = useRef<string[]>([]);
  const [showPrevDiff, setShowPrevDiff] = useState(false);
  // Remove an action-item mark by id, called from the inline per-paragraph badge
  // toolbar (a PM widget built outside React). Held in a ref so the widget always
  // calls the latest closure.
  const removeActionFnRef = useRef<(id: number) => void>(() => {});
  // Section-level AI action ref: called from the section h2 floating toolbar.
  const runAiFnRef = useRef<(kind: string) => void>(() => {});

  // Glossary -> word-boundary regex (longest first), reused by the overlay plugin.
  const glossarySorted = useMemo(
    () =>
      [...glossary]
        .filter((e) => e.phonetic && e.arabic_script)
        .sort((a, b) => b.phonetic.length - a.phonetic.length),
    [glossary],
  );
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

  // FC-3 + FC-4 + active paragraph: one decoration plugin reading the refs.
  const StudioDecos = useMemo(
    () =>
      Extension.create({
        name: "studioDecos",
        addProseMirrorPlugins() {
          return [
            new Plugin({
              key: new PluginKey("studioDecos"),
              props: {
                decorations(state) {
                  const orig = originalRef.current;
                  // Group action-item marks by paragraph ordinal for inline badges.
                  const actsByPara = new Map<number, ClientActionItem[]>();
                  for (const a of actionsRef.current) {
                    const arr = actsByPara.get(a.para_ordinal);
                    if (arr) arr.push(a);
                    else actsByPara.set(a.para_ordinal, [a]);
                  }
                  const decos: Decoration[] = [];

                  // Section-level activation: read from ref (updated synchronously in onSelectionUpdate).
                  const activeSec = hasFocusRef.current
                    ? activeSectionOrdinalRef.current
                    : null;

                  // FC-1: Quran verse refs REPLACE their phrase with a compact chip. The
                  // underlying prose is NOT mutated (display:none decoration), so the
                  // NotebookLM source still reads "Surah Al-Kahf, verse 110". Collect the
                  // ranges so the Arabic overlay doesn't double-render inside them.
                  const refRanges: [number, number][] = [];
                  state.doc.descendants((tn, tpos) => {
                    if (!tn.isText || !tn.text) return;
                    SURAH_VERSE_RE.lastIndex = 0;
                    let rm: RegExpExecArray | null;
                    while ((rm = SURAH_VERSE_RE.exec(tn.text))) {
                      const num = SURAH_MAP[rm[1].replace(/’/g, "'")];
                      if (!num) continue;
                      const verse = rm[2];
                      const label = rm[3]
                        ? `${num}:${verse}–${rm[3]}`
                        : `${num}:${verse}`;
                      const from = tpos + rm.index;
                      const to = from + rm[0].length;
                      refRanges.push([from, to]);
                      decos.push(
                        Decoration.inline(from, to, { class: "ref-hidden" }),
                      );
                      decos.push(
                        Decoration.widget(
                          from,
                          () => {
                            const chip = document.createElement("span");
                            chip.className = "ref-quran sp-vchip";
                            chip.textContent = label;
                            chip.setAttribute("data-surah", String(num));
                            chip.setAttribute("data-verse", verse);
                            return chip;
                          },
                          { side: -1 },
                        ),
                      );
                    }
                  });
                  const inRef = (p: number) =>
                    refRanges.some(([a, b]) => p >= a && p < b);

                  // Wave N: track h2 ordinal (section index, 0-based) for depth markers.
                  let sectionOrdinal = 0;
                  let currentSectionIdx = -1; // ordinal of the section paragraphs currently belong to
                  let i = 0;
                  state.doc.forEach((node, offset) => {
                    const idx = i++;
                    const t = actsByPara.get(idx) || [];

                    // Option A: section depth badge + tag chips next to every h2.
                    if (
                      node.type.name === "heading" &&
                      node.attrs.level === 2
                    ) {
                      const ord = sectionOrdinal++;
                      currentSectionIdx = ord; // paragraphs following this h2 belong to section `ord`
                      const depthLevel = sectionDepthsRef.current[ord];
                      const secTags = sectionTagsRef.current[ord] ?? [];
                      const sectionSlug = node.textContent
                        .slice(0, 60)
                        .toLowerCase()
                        .replace(/[^a-z0-9]+/g, "-")
                        .replace(/^-|-$/g, "");
                      const tagKey = secTags.join(",");
                      decos.push(
                        Decoration.widget(
                          offset + node.nodeSize - 1,
                          () => {
                            const wrap = document.createElement("span");
                            wrap.className = "sp-section-annotation";
                            wrap.contentEditable = "false";

                            // Depth badge
                            const btn = document.createElement("button");
                            btn.type = "button";
                            btn.className = `sp-section-depth-btn${depthLevel ? ` sp-depth-${depthLevel}` : " sp-depth-none"}`;
                            const label = depthLevel
                              ? (depthLevels.find((l) => l.key === depthLevel)
                                  ?.label ?? depthLevel)
                              : "∅ depth";
                            btn.title = `Depth: ${label} — click to change`;
                            btn.textContent = label;
                            btn.addEventListener("mousedown", (ev) => {
                              ev.preventDefault();
                              ev.stopPropagation();
                              openDepthPicker(
                                btn,
                                saveSectionDepthRef.current,
                                ord,
                                sectionSlug,
                                depthLevel,
                                depthLevels,
                                secTags,
                              );
                            });
                            wrap.appendChild(btn);

                            // Separate tag picker button
                            const tagPickerBtn =
                              document.createElement("button");
                            tagPickerBtn.type = "button";
                            tagPickerBtn.className = `sp-section-tag-btn${secTags.length ? " has-tags" : ""}`;
                            tagPickerBtn.title = secTags.length
                              ? `Tags: ${secTags.join(", ")} — click to edit`
                              : "Add section tags";
                            tagPickerBtn.textContent = "#";
                            tagPickerBtn.addEventListener("mousedown", (ev) => {
                              ev.preventDefault();
                              ev.stopPropagation();
                              openTagPicker(
                                tagPickerBtn,
                                saveSectionDepthRef.current,
                                ord,
                                sectionSlug,
                                secTags,
                                depthLevel ?? "",
                              );
                            });
                            wrap.appendChild(tagPickerBtn);

                            // Tag chips (inline, display only)
                            for (const tid of secTags) {
                              const chip = document.createElement("span");
                              chip.className = `sp-section-tag-chip sp-tag-${tid}`;
                              chip.textContent =
                                SECTION_TAGS.find((t) => t.id === tid)?.label ??
                                tid;
                              chip.title = `Tag: ${tid}`;
                              wrap.appendChild(chip);
                            }

                            // Edit button: moves cursor into section body, activates section-level editing.
                            const editBtn = document.createElement("button");
                            editBtn.type = "button";
                            editBtn.className = "sp-section-edit-btn";
                            editBtn.textContent = "✏ Edit";
                            editBtn.title = "Click to edit this section";
                            editBtn.addEventListener("mousedown", (ev) => {
                              ev.preventDefault();
                              ev.stopPropagation();
                              const ed = editorRef.current;
                              if (!ed) return;
                              let bodyStart = -1;
                              let sec = -1;
                              ed.state.doc.forEach((n, o) => {
                                if (
                                  n.type.name === "heading" &&
                                  n.attrs.level === 2
                                ) {
                                  sec++;
                                  if (sec === ord) bodyStart = o + n.nodeSize;
                                }
                              });
                              if (bodyStart >= 0) {
                                ed.commands.setTextSelection(bodyStart + 1);
                                ed.view.focus();
                              }
                            });
                            wrap.appendChild(editBtn);

                            return wrap;
                          },
                          {
                            side: 1,
                            key: `sec-annot-${ord}-${depthLevel ?? "none"}-${tagKey}`,
                          },
                        ),
                      );

                      // AI toolbar on active section's h2 (right-aligned, above heading).
                      if (activeSec === ord) {
                        decos.push(
                          Decoration.widget(
                            offset + 1,
                            () => {
                              const bar = document.createElement("div");
                              bar.contentEditable = "false";
                              bar.className =
                                "sp-para-tools sp-para-tools--palette sp-para-tools--ai";
                              const AI_ACTIONS = [
                                {
                                  kind: "rewrite",
                                  label: "↺",
                                  title: "Rewrite section",
                                },
                                {
                                  kind: "research",
                                  label: "🔍",
                                  title: "Research context",
                                },
                                {
                                  kind: "autotag",
                                  label: "🏷",
                                  title: "Auto-tag section",
                                },
                              ];
                              for (const action of AI_ACTIONS) {
                                const b = document.createElement("button");
                                b.type = "button";
                                b.className = "sp-ptool sp-ptool--ai";
                                b.title = action.title;
                                b.textContent = action.label;
                                b.addEventListener("mousedown", (ev) => {
                                  ev.preventDefault();
                                  ev.stopPropagation();
                                  runAiFnRef.current(action.kind);
                                });
                                bar.appendChild(b);
                              }
                              return bar;
                            },
                            { side: -1, key: `sec-tools-${ord}` },
                          ),
                        );
                      }
                    }

                    // Section-active: h2 gets accent border via CSS; paragraphs get warm tint.
                    if (activeSec !== null && currentSectionIdx === activeSec) {
                      decos.push(
                        Decoration.node(offset, offset + node.nodeSize, {
                          class: "section-active",
                        }),
                      );
                    }

                    // Action-item marks: inline badge row (icons, click to remove).
                    if (t.length) {
                      decos.push(
                        Decoration.node(offset, offset + node.nodeSize, {
                          class: `para-marked act-${t[0].action_kind}`,
                        }),
                      );
                      decos.push(
                        Decoration.widget(
                          offset + 1,
                          () => {
                            const bar = document.createElement("div");
                            bar.contentEditable = "false";
                            bar.className =
                              "sp-para-tools sp-para-tools--marks";
                            bar.setAttribute("role", "toolbar");
                            bar.setAttribute(
                              "aria-label",
                              "Paragraph action marks",
                            );
                            for (const item of t) {
                              const def = ACTION_BY_KIND[item.action_kind];
                              if (!def) continue;
                              const b = document.createElement("button");
                              b.type = "button";
                              b.className = `sp-ptool act-${item.action_kind} is-on`;
                              b.title = `${def.label}${item.term_text ? ` · "${item.term_text}"` : ""} (click to remove)`;
                              const ic = document.createElement("i");
                              ic.className = `fa-solid ${def.icon}`;
                              ic.setAttribute("aria-hidden", "true");
                              b.appendChild(ic);
                              b.addEventListener("mousedown", (ev) => {
                                ev.preventDefault();
                                ev.stopPropagation();
                                removeActionFnRef.current(item.id);
                              });
                              bar.appendChild(b);
                            }
                            return bar;
                          },
                          {
                            side: -1,
                            key: `tools-${idx}-marks-${t.map((x) => x.id).join(",")}`,
                          },
                        ),
                      );
                    }
                    // FC-3 Word-level track changes vs the original snapshot.
                    // In prev-stage-diff mode: diff current node against the PREVIOUS stage's
                    // paragraph instead (showing what THIS step changed, not human edits).
                    const prevDiff = showPrevDiffRef.current;
                    const before = prevDiff
                      ? (prevStageTextsRef.current[idx] ?? "")
                      : orig[idx];
                    const insClass = prevDiff ? "aug-ins" : "tc-ins";
                    const delClass = prevDiff ? "aug-del" : "tc-del";
                    const after = node.textContent;
                    if (before !== undefined && before !== after) {
                      let cursor = offset + 1; // content start of a textblock
                      for (const part of diffWords(before, after)) {
                        const len = part.value.length;
                        if (part.added) {
                          decos.push(
                            Decoration.inline(cursor, cursor + len, {
                              class: insClass,
                            }),
                          );
                          cursor += len;
                        } else if (part.removed) {
                          const text = part.value;
                          decos.push(
                            Decoration.widget(
                              cursor,
                              () => {
                                const del = document.createElement("span");
                                del.className = delClass;
                                del.textContent = text;
                                return del;
                              },
                              { side: -1 },
                            ),
                          );
                        } else {
                          cursor += len;
                        }
                      }
                    }

                    // Para-dirty: warm background on blocks the user has edited vs the original.
                    // Only shown in human-edit mode (not prev-stage diff) so it tracks real changes.
                    if (
                      !prevDiff &&
                      orig[idx] !== undefined &&
                      orig[idx] !== after
                    ) {
                      decos.push(
                        Decoration.node(offset, offset + node.nodeSize, {
                          class: "para-dirty",
                        }),
                      );
                    }

                    const pairedRomanRanges: [number, number][] = [];
                    const pairedArabicRanges: [number, number][] = [];
                    const textContent = node.textContent;
                    ARABIC_PAIR_RE.lastIndex = 0;
                    let pairMatch: RegExpExecArray | null;
                    while ((pairMatch = ARABIC_PAIR_RE.exec(textContent))) {
                      const romanStart = offset + 1 + pairMatch.index;
                      const romanEnd = romanStart + pairMatch[1].length;
                      const arabicTextOffset = pairMatch[0].indexOf(
                        pairMatch[2],
                      );
                      const arabicStart =
                        offset + 1 + pairMatch.index + arabicTextOffset;
                      const arabicEnd = arabicStart + pairMatch[2].length;
                      const pairEnd =
                        offset + 1 + pairMatch.index + pairMatch[0].length;
                      pairedRomanRanges.push([romanStart, romanEnd]);
                      pairedArabicRanges.push([arabicStart, arabicEnd]);

                      if (arabicRef.current) {
                        decos.push(
                          Decoration.inline(romanStart, arabicStart, {
                            class: "ar-pair-hidden",
                          }),
                        );
                        decos.push(
                          Decoration.inline(arabicEnd, pairEnd, {
                            class: "ar-pair-hidden",
                          }),
                        );
                      } else {
                        decos.push(
                          Decoration.inline(romanEnd, pairEnd, {
                            class: "ar-pair-hidden",
                          }),
                        );
                      }
                    }
                    const inPairedRoman = (p: number) =>
                      pairedRomanRanges.some(([a, b]) => p >= a && p < b);
                    const inPairedArabic = (p: number) =>
                      pairedArabicRanges.some(([a, b]) => p >= a && p < b);

                    // FC-4 Arabic overlay (non-destructive): hide the English run, inject Arabic.
                    if (arabicRef.current && glossarySorted.length) {
                      node.descendants((child, childPos) => {
                        if (!child.isText || !child.text) return;
                        const base = offset + 1 + childPos;
                        for (const e of glossarySorted) {
                          // Don't fire inside compounds/possessives: skip if adjacent to a
                          // letter, hyphen, or apostrophe (so "al-Quran"/"Ghazali's" stay English).
                          const re = new RegExp(
                            `(?<![\\w-])${e.phonetic.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?![\\w'’-])`,
                            "g",
                          );
                          let mm: RegExpExecArray | null;
                          while ((mm = re.exec(child.text!))) {
                            const from = base + mm.index;
                            const to = from + mm[0].length;
                            if (inRef(from)) continue; // verse-ref phrase is already replaced by a chip
                            if (inPairedRoman(from)) continue; // paired terms already reveal their Arabic side
                            const after = child.text!.slice(
                              mm.index + mm[0].length,
                            );
                            if (
                              /^\s*\([\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF][^)]*\)/.test(
                                after,
                              )
                            ) {
                              continue;
                            }
                            decos.push(
                              Decoration.inline(from, to, {
                                class: "ar-hidden",
                              }),
                            );
                            const script = e.arabic_script;
                            decos.push(
                              Decoration.widget(
                                from,
                                () => {
                                  const s = document.createElement("span");
                                  s.className = "ar-script-chip";
                                  s.setAttribute("lang", "ar");
                                  s.setAttribute("dir", "rtl");
                                  s.textContent = script;
                                  return s;
                                },
                                { side: -1 },
                              ),
                            );
                          }
                        }
                      });
                    }

                    // Raw Arabic (typed straight into the prose, not a glossary
                    // token): colour every Arabic-LETTER run with the accent so it
                    // matches the glossary overlays — same naskh (from the editor
                    // font stack), same colour. Honorific / presentation-form glyphs
                    // (e.g. ﷺ, U+FDFA) fall outside these ranges, so they stay ink and
                    // read as prose rather than as terms.
                    node.descendants((child, childPos) => {
                      if (!child.isText || !child.text) return;
                      const base = offset + 1 + childPos;
                      const arRe = new RegExp(ARABIC_SCRIPT_RUN.source, "g");
                      let am: RegExpExecArray | null;
                      while ((am = arRe.exec(child.text!))) {
                        const from = base + am.index;
                        const to = from + am[0].length;
                        if (!arabicRef.current && inPairedArabic(from))
                          continue;
                        decos.push(
                          Decoration.inline(from, to, { class: "ar-raw" }),
                        );
                      }
                    });
                  });
                  return DecorationSet.create(state.doc, decos);
                },
              },
            }),
          ];
        },
      }),
    [glossarySorted],
  );

  const editor = useEditor({
    extensions: [StarterKit, MarkerHighlight, StudioDecos],
    content: html,
    onCreate({ editor }) {
      const texts: string[] = [];
      editor.state.doc.forEach((n) => texts.push(n.textContent));
      originalRef.current = texts;
    },
    onFocus({ editor }) {
      hasFocusRef.current = true;
      // Dispatch an empty transaction so the decoration plugin re-evaluates.
      editor.view.dispatch(editor.state.tr);
    },
    onBlur({ editor }) {
      hasFocusRef.current = false;
      setActiveParaIdx(null);
      activeSectionOrdinalRef.current = null;
      setActiveSectionOrdinal(null);
      editor.view.dispatch(editor.state.tr);
    },
    onUpdate() {
      refresh();
      scheduleAutosaveRef.current();
    },
    onSelectionUpdate({ editor }) {
      const { from, to } = editor.state.selection;
      setSelection(editor.state.doc.textBetween(from, to, " ").trim());
      // Track active paragraph index (for comment/tag panels) and active section ordinal (for AI).
      const $head = editor.state.selection.$head;
      let paraIdx = -1;
      let secOrd = -1;
      let curSec = -1;
      let i = 0;
      editor.state.doc.forEach((node, offset) => {
        if (node.type.name === "heading" && node.attrs.level === 2) curSec++;
        const depth1End = offset + (editor.state.doc.child(i)?.nodeSize ?? 0);
        if ($head.pos >= offset && $head.pos < depth1End) {
          paraIdx = i;
          secOrd = curSec;
        }
        i++;
      });
      const newSecOrd = secOrd >= 0 ? secOrd : null;
      activeSectionOrdinalRef.current = newSecOrd; // update ref immediately so the plugin sees it
      setActiveSectionOrdinal(newSecOrd);
      setActiveParaIdx(paraIdx >= 0 ? paraIdx : null);
      refresh(); // re-evaluate section decoration on caret moves
    },
  });

  // Keep editorRef in sync so depth-save dispatch always has the live editor.
  editorRef.current = editor;

  // Click outside the editor container → blur the editor DOM element.
  // The onBlur callback above handles clearing hasFocusRef + dispatching the decoration update.
  useEffect(() => {
    const onMouseDown = (e: MouseEvent) => {
      if (
        editorContainerRef.current &&
        !editorContainerRef.current.contains(e.target as Node)
      ) {
        editor?.view.dom.blur();
      }
    };
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, [editor]);

  // Switch the editor to the selected stage: load its text, re-snapshot redline
  // originals, and make only the under-review stage editable (upstream = read-only).
  // Action-item marks are chapter-level (not stage-level) — they reload on chapter
  // change and are intentionally NOT cleared here.
  useEffect(() => {
    if (!editor || !stage) return;
    if (viewAll) {
      editor.commands.setContent(buildCombinedHtml(stageId));
      originalRef.current = [];
      editor.setEditable(false);
    } else {
      editor.commands.setContent(stage.html);
      const texts: string[] = [];
      editor.state.doc.forEach((n) => texts.push(n.textContent));
      originalRef.current = texts;
      editor.setEditable(!isReadOnlyStage);
    }
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stageId, chapIdx, activeLineageId, viewAll, editor]);

  // (Re-)populate the previous-stage diff baseline whenever the selected step / chapter /
  // lineage changes, and set a sensible default for the "show changes" toggle: ON for a
  // read-only step with a moderate delta, OFF for the editable step or a huge compression
  // (a near-total rewrite would just be a wall of strikethrough).
  useEffect(() => {
    const m = metrics.find((x) => x.id === stageId);
    const prevId = m?.comparedTo ?? null;
    prevStageTextsRef.current = [];
    if (prevId) {
      const prevStage = stages.find((s) => s.id === prevId);
      if (prevStage?.html) {
        const div = document.createElement("div");
        div.innerHTML = prevStage.html;
        prevStageTextsRef.current = Array.from(div.children).map(
          (el) => el.textContent ?? "",
        );
      }
    }
    const big = m?.deltaPct != null && Math.abs(m.deltaPct) >= 60;
    const next = isReadOnlyStage && !!prevId && !big;
    showPrevDiffRef.current = next;
    setShowPrevDiff(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stageId, chapIdx, activeLineageId]);

  // ── Serialize / save / discard — declared here so editor is in scope ────────

  // Walk a ProseMirror text node and emit its content with inline mark syntax preserved.
  // Handles italic (*), bold (**), bold+italic (***) — the only marks used in stage files.
  const serializeInline = useCallback(function serializeInlineNode(
    node: PMNode,
  ): string {
    let out = "";
    node.forEach((child: PMNode) => {
      if (!child.isText || !child.text) {
        out += serializeInlineNode(child);
        return;
      }
      const text = child.text;
      const marks = child.marks.map((m) => m.type.name);
      const isBold = marks.includes("bold");
      const isItalic = marks.includes("italic");
      if (isBold && isItalic) out += `***${text}***`;
      else if (isBold) out += `**${text}**`;
      else if (isItalic) out += `*${text}*`;
      else out += text;
    });
    return out;
  }, []);

  const serializeToMarkdown = useCallback((): string => {
    if (!editor) return "";
    const lines: string[] = [];
    editor.state.doc.forEach((node) => {
      const type = node.type.name;
      if (type === "heading") {
        const level = node.attrs.level as number;
        lines.push("#".repeat(level) + " " + serializeInline(node));
      } else if (type === "blockquote") {
        const quoteLines: string[] = [];
        node.forEach((child: PMNode) => {
          const text = serializeInline(child).trimEnd();
          if (text) quoteLines.push(...text.split("\n"));
        });
        if (quoteLines.length === 0) lines.push(">");
        else quoteLines.forEach((line) => lines.push(`> ${line}`));
      } else {
        lines.push(serializeInline(node));
      }
      lines.push("");
    });
    return lines.join("\n").trimEnd() + "\n";
  }, [editor, serializeInline]);

  const normalizeCurrentEditorBaseline = useCallback(() => {
    if (!editor) return;
    const texts: string[] = [];
    editor.state.doc.forEach((n) => texts.push(n.textContent));
    originalRef.current = texts;
    window.dispatchEvent(new CustomEvent("chapter-editor:finalize"));
    editor.view.dispatch(editor.state.tr.setMeta("studioBaseline", Date.now()));
    refresh();
  }, [editor]);

  // ── Draft autosave — extracted to useAutosaveDraft (R2 pass 2). onUpdate
  // reaches the scheduler through scheduleAutosaveRef; saveAndApprove cancels
  // via autosaveTimer; discard suppresses the beforeunload flush.
  const {
    draftState,
    setDraftState,
    autosaveTimer,
    scheduleAutosaveRef,
    suppressFlushRef,
  } = useAutosaveDraft({
    slug,
    chapter,
    stageId: stage?.id,
    isReadOnlyStage,
    editorReady: !!editor,
    serializeToMarkdown,
    hasDraftForStage,
    chapIdx,
    activeLineageId,
    stageKey: stageId,
  });

  // ── Stage approval + finalize — extracted to useStageApproval (R2 pass 2).
  // Save & Approve / Accept flows, approval tokens + localStorage acceptance
  // keys, chapter finalize (Publish), and the chapter-switch approval reload.
  // The (pre-existing) local chap.drafted mutation stays here — the hook can't
  // mutate its own argument (react-hooks/immutability); deliberately NOT
  // memoized so the hook captures it exactly as it captured `chap` before.
  const clearDraftedFlag = (sid: string) => {
    if (chap.drafted) chap.drafted[sid] = false;
  };
  const {
    approvedStages,
    approvalTokens,
    acceptedApprovalKeys,
    finalized,
    saving,
    saveError,
    approvalToastOpen,
    setApprovalToastOpen,
    approvalToastText,
    publishing,
    saveAndApprove,
    acceptApprovedStage,
    toggleFinalized,
  } = useStageApproval({
    slug,
    chapter,
    chap,
    stage,
    editor,
    isArchivedView,
    chapIdx,
    activeLineageId,
    serializeToMarkdown,
    commentsRef,
    autosaveTimerRef: autosaveTimer,
    setDraftState,
    clearDraftedFlag,
    normalizeCurrentEditorBaseline,
    refresh,
  });

  const discardChanges = useCallback(async () => {
    if (!editor || !stage) return;
    // Cancel pending autosave and suppress the unload-flush, delete the draft,
    // then reload so the canonical (last-approved) chapter text is shown. ?ch=
    // keeps the open chapter; reload also clears local edits not yet autosaved.
    if (autosaveTimer.current) {
      clearTimeout(autosaveTimer.current);
      autosaveTimer.current = null;
    }
    suppressFlushRef.current = true;
    try {
      await apiFetch("/api/studio/draft", {
        method: "DELETE",
        body: { slug, chapter, stage: stage.id },
      });
    } catch {
      /* reload regardless — server keeps the canonical on failure */
    }
    const url = new URL(window.location.href);
    url.searchParams.set("ch", chapter);
    window.location.href = url.toString();
  }, [editor, stage, slug, chapter]);

  // Force a decoration recompute when Arabic mode flips. Set the ref BEFORE dispatching
  // (React state is async — the plugin reads arabicRef synchronously during the recompute).
  const toggleArabic = useCallback(() => {
    const next = !arabicRef.current;
    arabicRef.current = next;
    setArabicOn(next);
    if (editor) editor.view.dispatch(editor.state.tr.setMeta("arabic", true));
  }, [editor]);

  // Toggle the "changes from previous stage" redline (read-only steps). Ref-before-dispatch
  // so the decoration plugin sees the new value synchronously during the recompute.
  const togglePrevDiff = useCallback(() => {
    const next = !showPrevDiffRef.current;
    showPrevDiffRef.current = next;
    setShowPrevDiff(next);
    if (editor) editor.view.dispatch(editor.state.tr.setMeta("prevDiff", true));
  }, [editor]);

  // ── Wave L-8: AI assist + Finalize ──────────────────────────────────────
  // All text (heading + paragraphs) of a section, joined by double newline.
  const sectionText = useCallback(
    (ordinal: number | null): string => {
      if (!editor || ordinal === null) return "";
      const parts: string[] = [];
      let curSec = -1;
      editor.state.doc.forEach((node) => {
        if (node.type.name === "heading" && node.attrs.level === 2) curSec++;
        if (curSec === ordinal) {
          const t = node.textContent.trim();
          if (t) parts.push(t);
        }
      });
      return parts.join("\n\n");
    },
    [editor],
  );

  // Run an AI action on the active section. `kind` selects the route + model.
  const runAi = useCallback(
    async (kind: string) => {
      const text = sectionText(activeSectionOrdinal);
      if (!text.trim()) return;
      setAiBusy(true);
      setAiKind(kind);
      setAiResult("");
      setAiOptions([]);
      setAiError("");
      setInspectorTab("ai"); // auto-switch so result is visible immediately
      try {
        if (kind === "autotag") {
          const data = await apiFetch<{ tag?: string; reason?: string }>(
            "/api/ai/claude",
            { method: "POST", body: { task: "categorise", text } },
          );
          const { tag, reason } = data ?? {};
          setAiResult(`Suggested tag: ${tag}${reason ? ` — ${reason}` : ""}`);
          return;
        }
        let res: Response;
        if (kind === "rewrite") {
          // R2: intentionally left on raw fetch — /api/ai/rewrite reports
          // errors as {error} + non-2xx WITHOUT an ok key, and this site
          // displays that server message; apiFetch would replace it with a
          // generic HTTP line.
          res = await fetch("/api/ai/rewrite", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ text }),
          });
        } else if (kind === "research") {
          // R2: intentionally left on raw fetch — /api/ai/research has the
          // same non-envelope {error} + non-2xx error shape as rewrite.
          res = await fetch("/api/ai/research", {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({
              paragraphText: text,
              instruction:
                "Research this passage and provide scholarly context with web-sourced information.",
              bookTitle: chapterTitle,
              actionType: "research",
            }),
          });
        } else {
          setAiBusy(false);
          return;
        }
        const json = await res.json();
        if (!res.ok || json.ok === false) {
          setAiError(json.error ?? `Request failed (${res.status})`);
        } else if (kind === "rewrite") {
          let opts = (json.data?.options ?? json.options ?? []) as string[];
          // Fallback fix: if opts[0] is a raw JSON string (from API error path), re-parse it.
          if (
            opts.length === 1 &&
            typeof opts[0] === "string" &&
            opts[0].trimStart().startsWith("{")
          ) {
            try {
              const inner = JSON.parse(opts[0]) as { options?: string[] };
              if (Array.isArray(inner.options) && inner.options.length > 0)
                opts = inner.options;
            } catch {
              /* keep opts as-is */
            }
          }
          setAiOptions(opts.slice(0, 3).map((o) => String(o).trim()));
        } else if (kind === "research") {
          const body = json.fullText ?? json.prompt ?? "";
          const sources = (json.sources as string[] | undefined) ?? [];
          const sourced = sources.length
            ? `\n\nSources:\n${sources.map((s) => `• ${s}`).join("\n")}`
            : "";
          setAiResult(body + sourced);
        } else {
          setAiResult(
            typeof json.data === "string"
              ? json.data
              : JSON.stringify(json.data),
          );
        }
      } catch (e) {
        setAiError(fetchErrorText(e));
      } finally {
        setAiBusy(false);
      }
    },
    [activeSectionOrdinal, sectionText, chapterTitle, setInspectorTab],
  );

  // Apply a rewrite option to the active section: replaces all body paragraphs.
  const applySection = useCallback(
    (newText: string) => {
      if (!editor || activeSectionOrdinal === null) return;
      let bodyFrom = -1;
      let bodyTo = editor.state.doc.content.size;
      let curSec = -1;
      let foundSection = false;
      editor.state.doc.forEach((node, offset) => {
        if (node.type.name === "heading" && node.attrs.level === 2) {
          curSec++;
          if (curSec === activeSectionOrdinal) {
            bodyFrom = offset + node.nodeSize;
            foundSection = true;
          } else if (foundSection) {
            bodyTo = offset;
            foundSection = false;
          }
        }
      });
      if (bodyFrom < 0) return;
      const schema = editor.state.schema;
      const paragraphs = newText
        .split(/\n\s*\n/)
        .map((p) => p.trim())
        .filter(Boolean);
      const nodes =
        paragraphs.length > 0
          ? paragraphs.map((p) =>
              schema.nodes.paragraph.create(null, schema.text(p)),
            )
          : [schema.nodes.paragraph.create()];
      editor.view.dispatch(
        editor.state.tr.replaceWith(bodyFrom, bodyTo, nodes),
      );
      refresh();
    },
    [editor, activeSectionOrdinal],
  );

  // Persist a paragraph comment to SQLite (annotations API) on blur.
  const persistComment = useCallback(
    (idx: number, note: string) => {
      apiFetch("/api/annotations", {
        method: "PATCH",
        body: { book: slug, chapter, paraIdx: idx, note },
      }).catch(() => {
        /* non-blocking; comment is also saved with the stage */
      });
    },
    [slug, chapter],
  );

  // Pre-load saved paragraph comments from SQLite when the chapter changes.
  useEffect(() => {
    let cancelled = false;
    apiFetch<{ notes?: Record<string, unknown> }>("/api/annotations", {
      query: { book: slug, chapter },
    })
      .then((json) => {
        if (cancelled || !json) return;
        const notes = json.notes ?? {};
        for (const [idx, note] of Object.entries(notes)) {
          if (typeof note === "string" && note.trim()) {
            commentsRef.current.set(Number(idx), note);
          }
        }
        refreshComments();
      })
      .catch(() => {
        /* offline-friendly; stage-saved comments still load */
      });
    return () => {
      cancelled = true;
    };
  }, [slug, chapter]);

  let changedCount = 0;
  if (editor) {
    let i = 0;
    editor.state.doc.forEach((n) => {
      if (
        originalRef.current[i] !== undefined &&
        n.textContent !== originalRef.current[i]
      )
        changedCount++;
      i++;
    });
  }
  const markedCount = actionsRef.current.length;
  // "Approved" only counts while the stage is unchanged — any fresh edit reverts
  // the footer to "Save & Approve" so the new edit can be saved.
  // "Approved" holds only while the stage is unchanged AND has no outstanding
  // draft — any draft (even from a prior visit) reverts the footer to "Save &
  // Approve" so the in-progress edits can be committed.
  const approvalToken = stage ? (approvalTokens[stage.id] ?? "approved") : "";
  const approvalAccepted = !!(
    stage && acceptedApprovalKeys[`${stage.id}:${approvalToken}`]
  );
  const approvedClean =
    !!(stage && approvedStages[stage.id]) &&
    changedCount === 0 &&
    draftState !== "saved" &&
    !approvalAccepted;
  // Chapter's marks, ordered for the queue list (by paragraph, then insertion).
  const chapterActions = [...actionsRef.current].sort(
    (a, b) => a.para_ordinal - b.para_ordinal || a.id - b.id,
  );

  // Remove one action-item mark (optimistic; DELETE only if it was persisted).
  const removeAction = useCallback(
    (id: number) => {
      actionsRef.current = actionsRef.current.filter((a) => a.id !== id);
      editorRef.current?.view.dispatch(
        editorRef.current.state.tr.setMeta("refreshTags", true),
      );
      refreshActions();
      refresh();
      if (id < 0) return; // optimistic-only, never hit the server
      apiFetch("/api/studio/action-items", {
        method: "DELETE",
        body: { book: slug, chapter, id },
      }).catch(() => {
        /* non-blocking */
      });
    },
    [slug, chapter],
  );

  // Stamp an action item on the active paragraph (or the selected term). Toggles:
  // an identical existing mark is removed. Anchor text is stored so the CLI never
  // depends on the paragraph ordinal staying stable.
  const stampAction = useCallback(
    (def: ActionDef, useSelection: boolean) => {
      if (!editor || activeParaIdx === null || isReadOnlyStage) return;
      const scope: "paragraph" | "term" = useSelection ? "term" : "paragraph";
      const termText = useSelection ? selection.trim() : "";
      if (scope === "term" && !termText) return;
      let paraText = "";
      let i = 0;
      editor.state.doc.forEach((n) => {
        if (i === activeParaIdx) paraText = n.textContent;
        i++;
      });
      const anchorText = scope === "term" ? termText : paraText;
      const existing = actionsRef.current.find(
        (a) =>
          a.para_ordinal === activeParaIdx &&
          a.action_kind === def.kind &&
          a.term_text === termText,
      );
      if (existing) {
        removeAction(existing.id);
        return;
      }
      const tempId = -Date.now();
      actionsRef.current = [
        ...actionsRef.current,
        {
          id: tempId,
          scope,
          para_ordinal: activeParaIdx,
          term_text: termText,
          anchor_text: anchorText,
          action_kind: def.kind,
          status: "pending",
        },
      ];
      editor.view.dispatch(editor.state.tr.setMeta("refreshTags", true));
      refreshActions();
      refresh();
      apiFetch<{ ok?: boolean; item?: ClientActionItem }>(
        "/api/studio/action-items",
        {
          method: "POST",
          body: {
            book: slug,
            chapter,
            scope,
            paraOrdinal: activeParaIdx,
            termText,
            anchorText,
            actionKind: def.kind,
          },
        },
      )
        .then((json) => {
          if (json?.ok && json.item) {
            actionsRef.current = actionsRef.current.map((a) =>
              a.id === tempId ? (json.item as ClientActionItem) : a,
            );
            refreshActions();
          }
        })
        .catch(() => {
          /* non-blocking; optimistic mark stays visible */
        });
    },
    [
      editor,
      activeParaIdx,
      isReadOnlyStage,
      selection,
      slug,
      chapter,
      removeAction,
    ],
  );

  removeActionFnRef.current = removeAction;
  runAiFnRef.current = (kind: string) => void runAi(kind);

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

  // Friendly "N. Title" label for a chapter id (falls back to the raw id).
  const chapterLabel = useCallback(
    (id: string): string => {
      const idx = chapters.findIndex((c) => c.slug === id);
      return idx >= 0 ? `${idx + 1}. ${chapters[idx].title}` : id;
    },
    [chapters],
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

  const rawMarkers = scanMarkers(html.replace(/<[^>]+>/g, " "));
  const seen = new Map<string, { kind: string; text: string; count: number }>();
  for (const m of rawMarkers) {
    const key = `${m.kind}|${m.text}`;
    const e = seen.get(key);
    if (e) e.count += 1;
    else seen.set(key, { ...m, count: 1 });
  }
  const markers = [...seen.values()];
  const group = (kind: string) => markers.filter((m) => m.kind === kind);

  const renderGroup = (label: string, items: typeof markers, cls: string) =>
    items.length > 0 && (
      <div className="sp-mgroup">
        <h4 className="sp-mgroup-title">
          <span className={`sp-chip sp-chip--${cls}`}>{label}</span>
          <span className="sp-mgroup-count">{items.length}</span>
        </h4>
        <ul className="sp-marker-list">
          {items.map((m, i) => (
            <li key={i}>
              <span className="sp-marker-text">{m.text}</span>
              {m.count > 1 && (
                <span className="sp-marker-count">×{m.count}</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    );

  // Timeline rail items: the full transformation chain UP TO the editable Review
  // (latest at top, descending into older steps). Uncaptured intermediate stages
  // are shown muted + non-interactive so the whole journey is visible even when a
  // run didn't write every stage. Stages AFTER the editable top (e.g. narrator
  // not yet run) are omitted — they're not part of "the journey that led here".
  return (
    <Toast.Provider swipeDirection="right" duration={2600}>
      <div className="studio-editor">
        {/* Two columns: the editor and the contextual inspector. The left pipeline
          rail was removed (redundant nav — pipeline phases live in the breadcrumb
          and book-page tabs); the editor column widened and the reading-edition
          link moved into the editor head below. */}
        <main
          className="studio-editor__editor"
          ref={editorContainerRef}
          data-font={editorFont}
          data-paper={editorPaper}
          style={{ ["--prose-size"]: `${editorSize}px` } as CSSProperties}
        >
          {/* Consolidated editor header: chapter switcher · metrics · finalize. */}
          <div className="sp-editor-head">
            <div className="sp-chapsel">
              <label htmlFor="sp-chap">Chapter</label>
              <select
                id="sp-chap"
                value={chapIdx}
                disabled={viewAll}
                onChange={(e) => setChapIdx(Number(e.target.value))}
              >
                {viewChapters.map((c, i) => (
                  <option key={c.slug} value={i}>
                    {i + 1}. {c.title}
                  </option>
                ))}
              </select>
              <button
                type="button"
                className={`sp-viewall-btn${viewAll ? " is-on" : ""}`}
                onClick={() => setViewAll((v) => !v)}
                title={
                  viewAll
                    ? "Return to single-chapter view"
                    : "Combine all chapters in this tab"
                }
              >
                {viewAll ? "← Single chapter" : "All chapters →"}
              </button>
            </div>
            {!viewAll &&
              (() => {
                const m = metrics.find((x) => x.id === stageId);
                if (!m || !m.available) return null;
                const priorLabel = stages.find(
                  (s) => s.id === m.comparedTo,
                )?.label;
                const delta = m.deltaPct;
                return (
                  <div className="sp-metrics">
                    <span>
                      {m.words.toLocaleString()} words ·{" "}
                      {m.sentences.toLocaleString()} sentences
                    </span>
                    {delta !== null && priorLabel && (
                      <span
                        className={`sp-metric-delta ${delta < 0 ? "is-down" : delta > 0 ? "is-up" : ""}`}
                      >
                        {delta > 0 ? "+" : ""}
                        {delta}% vs {priorLabel}
                        {stageId === "denoised" &&
                          m.comparedTo === "core" &&
                          delta < 0 &&
                          ` (${Math.abs(delta)}% noise removed)`}
                      </span>
                    )}
                  </div>
                );
              })()}
            {!viewAll && !isArchivedView && (
              <button
                type="button"
                className={`sp-finalize-chapter${finalized ? " is-done" : ""}`}
                onClick={toggleFinalized}
                disabled={publishing}
                title={
                  finalized
                    ? "Chapter finalized — click to unlock"
                    : "Mark this chapter finalized"
                }
              >
                {finalized
                  ? "✓ Finalized"
                  : publishing
                    ? "Finalizing…"
                    : "Finalize chapter"}
              </button>
            )}
            <div className="sp-reading" role="group" aria-label="Reading view">
              <select
                className="sp-reading-font"
                aria-label="Editor font (view only)"
                title="Editor font — changes this editing view only, not the book"
                value={editorFont}
                onChange={(e) => setEditorFont(e.target.value)}
              >
                {EDITOR_FONTS.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name}
                  </option>
                ))}
              </select>
              <div
                className="sp-reading-size"
                role="group"
                aria-label="Editor text size"
              >
                <button
                  type="button"
                  className="sp-reading-step"
                  aria-label="Decrease editor text size"
                  onClick={() =>
                    setEditorSize((s) => Math.max(EDITOR_SIZE_MIN, s - 1))
                  }
                >
                  −
                </button>
                <span className="sp-reading-size-val" aria-live="polite">
                  {editorSize}
                </span>
                <button
                  type="button"
                  className="sp-reading-step"
                  aria-label="Increase editor text size"
                  onClick={() =>
                    setEditorSize((s) => Math.min(EDITOR_SIZE_MAX, s + 1))
                  }
                >
                  +
                </button>
              </div>
              <div
                className="sp-reading-paper"
                role="group"
                aria-label="Paper colour"
              >
                {EDITOR_PAPERS.map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    className={`sp-reading-paper-btn${editorPaper === p.id ? " is-on" : ""}`}
                    data-paper={p.id}
                    aria-pressed={editorPaper === p.id}
                    onClick={() => setEditorPaper(p.id)}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
            </div>
            <a
              className="sp-book-link"
              href={`/studio/${slug}/book`}
              title="Open the companion reading edition (the book)"
            >
              <span className="sp-book-glyph" aria-hidden="true">
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.6"
                >
                  <path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H20v15H5.5A1.5 1.5 0 0 0 4 19.5z" />
                  <path d="M4 19.5A1.5 1.5 0 0 1 5.5 18H20v3H5.5A1.5 1.5 0 0 1 4 19.5z" />
                </svg>
              </span>
              Reading edition
            </a>
          </div>
          {!viewAll && (
            <TransformationDashboard
              chapterTitle={chap.title}
              stages={stages}
              metrics={metrics}
              enrichment={enrichment}
              glossaryCount={glossaryCount}
            />
          )}
          {viewAll && (
            <div className="sp-viewall-banner">
              Showing all {viewChapters.length} chapters ·{" "}
              {stages.find((s) => s.id === stageId)?.label ?? stageId} stage ·
              read-only
            </div>
          )}
          {!viewAll &&
            stage &&
            (() => {
              const m = metrics.find((x) => x.id === stageId);
              const prevLabel = stages.find(
                (s) => s.id === m?.comparedTo,
              )?.label;
              const role = stageRole(stage.id);
              const isReviewTop =
                stage.id === editableStageId && !isArchivedView;
              const displayName = isReviewTop ? "Review" : stage.label;
              const delta = m?.deltaPct ?? null;
              let metricText: string | null = null;
              if (m?.available && delta !== null && prevLabel) {
                metricText =
                  stage.id === "denoised" &&
                  m.comparedTo === "core" &&
                  delta < 0
                    ? `${Math.abs(delta)}% noise removed`
                    : `${delta > 0 ? "+" : ""}${delta}% vs ${prevLabel}`;
              }
              return (
                <div className={`sp-stage-card sp-stage-card--${role.kind}`}>
                  <div className="sp-stage-card-main">
                    <span className="sp-stage-card-name">{displayName}</span>
                    {role.role && (
                      <span
                        className={`sp-stage-card-role sp-stage-card-role--${role.kind}`}
                      >
                        {role.role}
                      </span>
                    )}
                    {role.tool && (
                      <span className="sp-stage-card-tool">{role.tool}</span>
                    )}
                    {isReviewTop ? (
                      <span className="sp-stage-card-flag is-editable">
                        editable
                      </span>
                    ) : (
                      <span className="sp-stage-card-flag is-readonly">
                        read-only
                        {isArchivedView ? ` · ${activeLineage.label}` : ""}
                      </span>
                    )}
                    {metricText && (
                      <span className="sp-stage-card-metric">{metricText}</span>
                    )}
                  </div>
                  {isReadOnlyStage && prevLabel && (
                    <div className="sp-stage-card-diff">
                      <button
                        type="button"
                        className={`sp-augdiff-toggle${showPrevDiff ? " is-on" : ""}`}
                        onClick={togglePrevDiff}
                        title={
                          showPrevDiff
                            ? "Hide the changes"
                            : `Highlight what changed from ${prevLabel}`
                        }
                      >
                        {showPrevDiff
                          ? "Hide changes"
                          : `Show changes from ${prevLabel}`}
                      </button>
                      {showPrevDiff && (
                        <span className="sp-augdiff-legend">
                          <span className="aug-ins sp-augdiff-swatch">
                            added
                          </span>
                          <span className="aug-del sp-augdiff-swatch">
                            removed
                          </span>
                        </span>
                      )}
                    </div>
                  )}
                </div>
              );
            })()}
          <EditorContent editor={editor} />
        </main>

        <aside
          className="studio-editor__inspector"
          aria-label="Contextual inspector"
          ref={inspectorRef}
        >
          {/* View controls — Arabic overlay toggle + link to the phonetic map. */}
          {glossaryCount > 0 && (
            <div className="sp-global-strip">
              <button
                type="button"
                role="switch"
                aria-checked={arabicOn}
                aria-label={`Toggle Arabic script — currently ${arabicOn ? "on" : "off"}`}
                className={`sp-arabic-btn${arabicOn ? " is-on" : ""}`}
                onClick={toggleArabic}
                title={
                  arabicOn
                    ? "Hide Arabic script in the chapter"
                    : "Show Arabic script in the chapter"
                }
              >
                <i
                  className={`fa-solid ${arabicOn ? "fa-toggle-on" : "fa-toggle-off"}`}
                  aria-hidden="true"
                />
                <span className="sp-arabic-label">Toggle Arabic</span>
              </button>
              <a
                className="sp-phonetic-map"
                href={`/studio/${slug}/arabic-review#${chapter}`}
                title="Open the phonetic map (full Arabic review) for this chapter"
              >
                <i className="fa-solid fa-language" aria-hidden="true" />{" "}
                Phonetic Map
              </a>
            </div>
          )}

          {/* M-1 — Tabbed panel: Details · Comment · AI · References */}
          <div className="sp-panel-card">
            <div
              className="sp-tab-bar"
              role="tablist"
              aria-label="Inspector tabs"
            >
              {(["details", "ai", "refs", "comment"] as const).map((tab) => {
                const labels: Record<string, string> = {
                  details: "Details",
                  comment: "Comment",
                  ai: "AI",
                  refs: "References",
                };
                const hasDot =
                  tab === "ai" &&
                  (!!aiResult || aiOptions.length > 0 || aiBusy);
                return (
                  <button
                    key={tab}
                    type="button"
                    role="tab"
                    id={`sp-tab-${tab}`}
                    aria-controls="sp-tab-panel"
                    aria-selected={inspectorTab === tab}
                    data-tab={tab}
                    className={`sp-tab-btn${inspectorTab === tab ? " is-active" : ""}`}
                    onClick={() => setInspectorTab(tab)}
                  >
                    {labels[tab]}
                    {hasDot && (
                      <span className="sp-tab-dot" aria-label="result ready" />
                    )}
                  </button>
                );
              })}
            </div>

            <div
              className="sp-tab-pane"
              role="tabpanel"
              id="sp-tab-panel"
              aria-labelledby={`sp-tab-${inspectorTab}`}
              tabIndex={0}
            >
              {/* ── Details tab: chapter overview + tag buttons for active paragraph ── */}
              {inspectorTab === "details" && (
                <>
                  {selection ? (
                    <blockquote className="sp-insp-sel">{selection}</blockquote>
                  ) : (
                    <dl className="sp-insp-meta">
                      <dt>Chapter</dt>
                      <dd>{chapterTitle}</dd>
                      <dt>Changes</dt>
                      <dd>
                        {changedCount} edited · {markedCount} marked
                      </dd>
                      <dt>Comments</dt>
                      <dd>
                        {commentsRef.current.size > 0
                          ? `${commentsRef.current.size} paragraph${commentsRef.current.size !== 1 ? "s" : ""}`
                          : "—"}
                      </dd>
                    </dl>
                  )}
                  {/* Action items — deferred marks for the CLI drain pass (edit mode only). */}
                  {!isReadOnlyStage && (
                    <div className="sp-actions-block">
                      {/* One control panel — every action stays visible; buttons that
                        cannot run in the current context are disabled, never hidden. */}
                      <p className="sp-insp-hint">
                        Actions ·{" "}
                        {selection.trim()
                          ? `"${truncate(selection, 32)}"`
                          : activeParaIdx !== null
                            ? `paragraph ${activeParaIdx + 1}`
                            : "click a paragraph or select a word"}
                      </p>
                      <div
                        className="sp-action-palette"
                        role="toolbar"
                        aria-label="Editor actions"
                      >
                        {ACTION_REGISTRY.map((def) => {
                          const sel = selection.trim();
                          const hasSel = !!sel;
                          const hasPara = activeParaIdx !== null;
                          // A 'both'-scope action targets the highlighted word when one
                          // exists, otherwise the active paragraph.
                          const onTerm =
                            def.scope === "term" ||
                            (def.scope === "both" && hasSel);
                          const enabled =
                            def.scope === "term"
                              ? hasSel
                              : def.scope === "paragraph"
                                ? hasPara
                                : hasSel || hasPara;
                          const busy =
                            (def.kind === "arabic" && arabicBusy) ||
                            (def.kind === "english" && englishBusy) ||
                            (def.kind === "explain" && explainBusy);
                          const isOn =
                            def.applyMode === "immediate"
                              ? false
                              : actionsRef.current.some(
                                  (a) =>
                                    a.para_ordinal === activeParaIdx &&
                                    a.action_kind === def.kind &&
                                    a.term_text === (onTerm ? sel : ""),
                                );
                          return (
                            <button
                              key={def.kind}
                              type="button"
                              className={`sp-action-btn act-${def.kind}${isOn ? " is-on" : ""}`}
                              title={
                                enabled
                                  ? def.hint
                                  : def.scope === "term"
                                    ? "Select a word to enable"
                                    : "Click a paragraph to enable"
                              }
                              disabled={!enabled || busy}
                              aria-pressed={
                                def.applyMode === "immediate" ? undefined : isOn
                              }
                              onClick={() => {
                                if (def.applyMode === "immediate") {
                                  if (def.kind === "arabic")
                                    void proposeArabic();
                                  else if (def.kind === "english")
                                    void proposeEnglish();
                                  else if (def.kind === "explain")
                                    void proposeExplain();
                                  else if (def.kind === "replace")
                                    openReplace();
                                  else if (def.kind === "noise") openNoise();
                                } else {
                                  stampAction(def, onTerm);
                                }
                              }}
                            >
                              <i
                                className={`fa-solid ${def.icon}`}
                                aria-hidden="true"
                              />{" "}
                              <span className="sp-action-label">
                                {def.label}
                              </span>
                            </button>
                          );
                        })}
                      </div>
                      {explainBusy && (
                        <p className="sp-ai-status">
                          Writing a clearer explanation…
                        </p>
                      )}
                      {explainError && (
                        <p className="sp-ai-status sp-ai-status--error">
                          {explainError}
                        </p>
                      )}
                      {englishBusy && (
                        <p className="sp-ai-status">
                          Finding the English rendering…
                        </p>
                      )}
                      {englishError && (
                        <p className="sp-ai-status sp-ai-status--error">
                          {englishError}
                        </p>
                      )}
                      {explainProposal && (
                        <div className="sp-explain-confirm">
                          <p className="sp-explain-confirm__label">
                            Clearer explanation — edit before replacing:
                          </p>
                          <textarea
                            className="sp-explain-confirm__text"
                            value={explainProposal.text}
                            rows={6}
                            onChange={(e) =>
                              setExplainProposal({
                                ...explainProposal,
                                text: e.target.value,
                              })
                            }
                            aria-label="Explanation — edit before replacing"
                          />
                          <div className="sp-arabic-confirm__actions">
                            <button
                              type="button"
                              className="sp-arabic-confirm__apply"
                              onClick={applyExplain}
                              disabled={!explainProposal.text.trim()}
                            >
                              <i
                                className="fa-solid fa-check"
                                aria-hidden="true"
                              />{" "}
                              Replace
                            </button>
                            <button
                              type="button"
                              className="sp-arabic-confirm__cancel"
                              onClick={cancelExplain}
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}
                      {arabicBusy && (
                        <p className="sp-ai-status">Finding the Arabic term…</p>
                      )}
                      {arabicError && (
                        <p className="sp-ai-status sp-ai-status--error">
                          {arabicError}
                        </p>
                      )}
                      {arabicProposal && (
                        <div className="sp-arabic-confirm">
                          <p className="sp-arabic-confirm__row">
                            <span className="sp-arabic-confirm__en">
                              {truncate(arabicProposal.original, 28)}
                            </span>
                            <i
                              className="fa-solid fa-arrow-right-long"
                              aria-hidden="true"
                            />
                          </p>
                          <input
                            type="text"
                            className="sp-arabic-confirm__input"
                            lang="ar"
                            dir="rtl"
                            value={arabicProposal.arabic}
                            onChange={(e) =>
                              setArabicProposal({
                                ...arabicProposal,
                                arabic: e.target.value,
                              })
                            }
                            aria-label="Arabic term — edit before replacing"
                          />
                          {arabicProposal.gloss && (
                            <p className="sp-arabic-confirm__gloss">
                              {arabicProposal.gloss}
                            </p>
                          )}
                          {arabicDone ? (
                            <>
                              <p className="sp-arabic-confirm__doneline">
                                <i
                                  className="fa-solid fa-circle-check"
                                  aria-hidden="true"
                                />{" "}
                                {arabicDone}
                              </p>
                              <div className="sp-arabic-confirm__actions">
                                <button
                                  type="button"
                                  className="sp-arabic-confirm__cancel"
                                  onClick={cancelArabic}
                                >
                                  Close
                                </button>
                              </div>
                            </>
                          ) : (
                            <>
                              <p className="sp-arabic-confirm__scopehint">
                                Replace where?
                              </p>
                              <div className="sp-arabic-scope">
                                <button
                                  type="button"
                                  className="sp-arabic-scope__btn sp-arabic-scope__btn--primary"
                                  disabled={
                                    !arabicProposal.arabic.trim() || arabicBusy
                                  }
                                  onClick={applyArabic}
                                >
                                  <i
                                    className="fa-solid fa-check"
                                    aria-hidden="true"
                                  />{" "}
                                  This instance
                                </button>
                                <button
                                  type="button"
                                  className="sp-arabic-scope__btn"
                                  disabled={
                                    !arabicProposal.arabic.trim() || arabicBusy
                                  }
                                  onClick={() =>
                                    void applyArabicAcross("chapter")
                                  }
                                >
                                  <i
                                    className="fa-solid fa-file-lines"
                                    aria-hidden="true"
                                  />{" "}
                                  This chapter
                                </button>
                                <button
                                  type="button"
                                  className="sp-arabic-scope__btn"
                                  disabled={
                                    !arabicProposal.arabic.trim() || arabicBusy
                                  }
                                  onClick={() => void applyArabicAcross("book")}
                                >
                                  <i
                                    className="fa-solid fa-book"
                                    aria-hidden="true"
                                  />{" "}
                                  All chapters
                                </button>
                              </div>
                              <div className="sp-arabic-confirm__actions">
                                <button
                                  type="button"
                                  className="sp-arabic-confirm__cancel"
                                  onClick={cancelArabic}
                                >
                                  {arabicBusy ? "Replacing…" : "Cancel"}
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                      )}

                      {chapterActions.length > 0 && (
                        <div className="sp-action-queue">
                          <p className="sp-insp-hint">
                            Queued for the pipeline · {chapterActions.length}
                          </p>
                          <ul className="sp-action-queue-list">
                            {chapterActions.map((item) => {
                              const def = ACTION_BY_KIND[item.action_kind];
                              return (
                                <li
                                  key={item.id}
                                  className={`sp-aq-item act-${item.action_kind}`}
                                >
                                  <i
                                    className={`fa-solid ${def?.icon ?? "fa-circle"}`}
                                    aria-hidden="true"
                                  />
                                  <span className="sp-aq-label">
                                    {def?.label ?? item.action_kind}
                                  </span>
                                  <span className="sp-aq-target">
                                    {item.term_text
                                      ? `"${truncate(item.term_text, 24)}"`
                                      : `¶ ${item.para_ordinal + 1}`}
                                  </span>
                                  <button
                                    type="button"
                                    className="sp-aq-remove"
                                    title="Remove this mark"
                                    aria-label={`Remove ${def?.label ?? item.action_kind} mark`}
                                    onClick={() => removeAction(item.id)}
                                  >
                                    <i
                                      className="fa-solid fa-xmark"
                                      aria-hidden="true"
                                    />
                                  </button>
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                      )}
                    </div>
                  )}
                </>
              )}

              {/* ── Comment tab: per-paragraph comment textarea ── */}
              {inspectorTab === "comment" &&
                (activeParaIdx !== null && !isReadOnlyStage ? (
                  <div className="sp-comment-panel">
                    <label
                      className="sp-comment-label"
                      htmlFor="sp-comment-input"
                    >
                      Comment on paragraph {activeParaIdx + 1}
                    </label>
                    <textarea
                      id="sp-comment-input"
                      className="sp-comment-input"
                      rows={5}
                      placeholder="Note for the pipeline (saved with stage)…"
                      value={commentsRef.current.get(activeParaIdx) ?? ""}
                      onChange={(e) => {
                        const v = e.target.value;
                        if (v.trim()) commentsRef.current.set(activeParaIdx, v);
                        else commentsRef.current.delete(activeParaIdx);
                        refreshComments();
                      }}
                      onBlur={(e) =>
                        persistComment(activeParaIdx, e.target.value.trim())
                      }
                    />
                  </div>
                ) : (
                  <p className="sp-insp-hint">
                    {isReadOnlyStage
                      ? "Read-only stage."
                      : "Click a paragraph to add a comment."}
                  </p>
                ))}

              {/* ── AI tab: section-level Rewrite / Research / Auto-tag ── */}
              {inspectorTab === "ai" && (
                <div className="sp-ai-panel">
                  {activeSectionOrdinal !== null && !isReadOnlyStage && (
                    <div
                      className="sp-ai-tab-actions"
                      role="toolbar"
                      aria-label="AI actions"
                    >
                      <button
                        type="button"
                        className="sp-ai-tab-btn"
                        disabled={aiBusy}
                        onClick={() => runAi("rewrite")}
                      >
                        <i
                          className="fa-solid fa-arrows-rotate"
                          aria-hidden="true"
                        />{" "}
                        Rewrite
                      </button>
                      <button
                        type="button"
                        className="sp-ai-tab-btn"
                        disabled={aiBusy}
                        onClick={() => runAi("research")}
                      >
                        <i
                          className="fa-solid fa-magnifying-glass"
                          aria-hidden="true"
                        />{" "}
                        Research
                      </button>
                      <button
                        type="button"
                        className="sp-ai-tab-btn"
                        disabled={aiBusy}
                        onClick={() => runAi("autotag")}
                      >
                        <i className="fa-solid fa-tag" aria-hidden="true" />{" "}
                        Auto-tag
                      </button>
                    </div>
                  )}
                  {aiBusy && (
                    <p className="sp-ai-status">Working… ({aiKind})</p>
                  )}
                  {aiError && (
                    <p className="sp-ai-status sp-ai-status--error">
                      {aiError}
                    </p>
                  )}
                  {/* Rewrite option cards — each with an Apply button */}
                  {aiOptions.length > 0 && (
                    <div className="sp-ai-options">
                      {aiOptions.map((opt, i) => (
                        <div key={i} className="sp-ai-option-card">
                          <span className="sp-ai-option-num">{i + 1}</span>
                          <p className="sp-ai-option-text">{opt}</p>
                          <button
                            type="button"
                            className="sp-ai-option-apply"
                            onClick={() => applySection(opt)}
                            disabled={activeSectionOrdinal === null}
                            title="Replace section body with this rewrite"
                          >
                            Apply →
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  {/* Research / autotag plain-text result */}
                  {aiResult && <div className="sp-ai-result">{aiResult}</div>}
                  {!aiBusy &&
                    aiOptions.length === 0 &&
                    !aiResult &&
                    !aiError && (
                      <p className="sp-insp-hint">
                        Click into a section, then use the buttons above — or
                        click ↺ 🔍 🏷 in the toolbar that appears above the
                        section heading.
                      </p>
                    )}
                </div>
              )}

              {/* ── References tab: inline markers by category ── */}
              {inspectorTab === "refs" && (
                <div className="sp-insp-markers">
                  {stage?.augMeta && (
                    <p
                      className="sp-aug-meta"
                      title="Extracted from the augmented stage knowledge block"
                    >
                      {stage.augMeta}
                    </p>
                  )}
                  <ul className="sp-legend" aria-label="Inline highlight key">
                    <li className="sp-legend-row">
                      <span className="sp-legend-dot sp-legend-dot--quran" />
                      Quran chips
                    </li>
                    <li className="sp-legend-row">
                      <span className="sp-legend-dot sp-legend-dot--hadith" />
                      Hadith
                    </li>
                    <li className="sp-legend-row">
                      <span className="sp-legend-dot sp-legend-dot--work" />
                      al-Ghazali works
                    </li>
                  </ul>
                  {renderGroup("Quran", group("Quran"), "quran")}
                  {renderGroup("Hadith", group("Hadith"), "hadith")}
                  {renderGroup("Works", group("Work"), "work")}
                </div>
              )}
            </div>
          </div>

          {saveError && (
            <p className="sp-save-error" role="alert">
              {saveError}
            </p>
          )}
          {!viewAll && !isReadOnlyStage && stage && draftState !== "idle" && (
            <p
              className={`sp-draft-status sp-draft-status--${draftState}`}
              role="status"
            >
              {draftState === "saving" ? (
                <>
                  <i
                    className="fa-solid fa-cloud-arrow-up"
                    aria-hidden="true"
                  />{" "}
                  Saving draft…
                </>
              ) : draftState === "error" ? (
                <>
                  <i
                    className="fa-solid fa-triangle-exclamation"
                    aria-hidden="true"
                  />{" "}
                  Draft not saved — check connection
                </>
              ) : (
                <>
                  <i className="fa-solid fa-pen" aria-hidden="true" /> Draft
                  saved · not yet approved
                </>
              )}
            </p>
          )}
          {!viewAll && !isReadOnlyStage && stage && (
            <div className="sp-action-footer">
              {(changedCount > 0 || draftState === "saved") && (
                <button
                  type="button"
                  className="sp-discard"
                  onClick={discardChanges}
                  disabled={saving}
                  title="Discard the draft and revert to the approved chapter"
                >
                  <i className="fa-solid fa-rotate-left" aria-hidden="true" />{" "}
                  Discard
                </button>
              )}
              <button
                type="button"
                className={`sp-approve${approvedClean ? " is-done" : ""}`}
                onClick={approvedClean ? acceptApprovedStage : saveAndApprove}
                disabled={saving}
                title={
                  approvedClean
                    ? "Accept the approved text as final content"
                    : "Save the current text and approve this stage"
                }
              >
                {approvedClean
                  ? `${stage.label} approved`
                  : saving
                    ? "Saving…"
                    : "Save & Approve"}
              </button>
            </div>
          )}
        </aside>

        {arabicProposal && (
          <div
            className="sp-term-backdrop"
            role="dialog"
            aria-modal="true"
            aria-label="Arabic replacement"
          >
            <div className="sp-term-modal sp-term-modal--arabic">
              <header className="sp-term-modal__head">
                <div>
                  <p className="sp-term-modal__eyebrow">Arabic rendering</p>
                  <h3 className="sp-term-modal__title">
                    Choose the Arabic script
                  </h3>
                </div>
                <button
                  type="button"
                  className="sp-term-modal__close"
                  onClick={cancelArabic}
                  aria-label="Close"
                >
                  <i className="fa-solid fa-xmark" aria-hidden="true" />
                </button>
              </header>
              <div className="sp-term-modal__body">
                <p className="sp-term-modal__swap">
                  <span>{truncate(arabicProposal.original, 48)}</span>
                  <i
                    className="fa-solid fa-arrow-right-long"
                    aria-hidden="true"
                  />
                </p>
                <input
                  type="text"
                  className="sp-term-modal__input sp-term-modal__input--arabic"
                  lang="ar"
                  dir="rtl"
                  value={arabicProposal.arabic}
                  onChange={(e) =>
                    setArabicProposal({
                      ...arabicProposal,
                      arabic: e.target.value,
                    })
                  }
                  aria-label="Arabic term — edit before replacing"
                  autoFocus
                />
                {arabicProposal.gloss && (
                  <p className="sp-term-modal__gloss">{arabicProposal.gloss}</p>
                )}
                {arabicDone && (
                  <p className="sp-term-modal__done">
                    <i
                      className="fa-solid fa-circle-check"
                      aria-hidden="true"
                    />{" "}
                    {arabicDone}
                  </p>
                )}
                <p className="sp-term-modal__scopehint">Save where?</p>
                <div className="sp-term-scope">
                  <button
                    type="button"
                    className="sp-term-scope__btn sp-term-scope__btn--primary"
                    disabled={!arabicProposal.arabic.trim() || arabicBusy}
                    onClick={applyArabic}
                  >
                    <i className="fa-solid fa-check" aria-hidden="true" /> This
                    instance
                  </button>
                  <button
                    type="button"
                    className="sp-term-scope__btn"
                    disabled={!arabicProposal.arabic.trim() || arabicBusy}
                    onClick={() => void applyArabicAcross("chapter")}
                  >
                    <i className="fa-solid fa-file-lines" aria-hidden="true" />{" "}
                    This chapter
                  </button>
                  <button
                    type="button"
                    className="sp-term-scope__btn"
                    disabled={!arabicProposal.arabic.trim() || arabicBusy}
                    onClick={() => void applyArabicAcross("book")}
                  >
                    <i className="fa-solid fa-book" aria-hidden="true" /> All
                    chapters
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {englishProposal && (
          <div
            className="sp-term-backdrop"
            role="dialog"
            aria-modal="true"
            aria-label="English replacement"
          >
            <div className="sp-term-modal">
              <header className="sp-term-modal__head">
                <div>
                  <p className="sp-term-modal__eyebrow">English rendering</p>
                  <h3 className="sp-term-modal__title">
                    Choose the spoken English
                  </h3>
                </div>
                <button
                  type="button"
                  className="sp-term-modal__close"
                  onClick={cancelEnglish}
                  aria-label="Close"
                >
                  <i className="fa-solid fa-xmark" aria-hidden="true" />
                </button>
              </header>
              <div className="sp-term-modal__body">
                <p className="sp-term-modal__swap">
                  <span>{truncate(englishProposal.original, 48)}</span>
                  <i
                    className="fa-solid fa-arrow-right-long"
                    aria-hidden="true"
                  />
                </p>
                <input
                  type="text"
                  className="sp-term-modal__input"
                  value={englishProposal.english}
                  onChange={(e) =>
                    setEnglishProposal({
                      ...englishProposal,
                      english: e.target.value,
                    })
                  }
                  aria-label="English rendering — edit before replacing"
                  autoFocus
                />
                {englishProposal.gloss && (
                  <p className="sp-term-modal__gloss">
                    {englishProposal.gloss}
                  </p>
                )}
                <p className="sp-term-modal__scopehint">Save where?</p>
                <div className="sp-term-scope">
                  <button
                    type="button"
                    className="sp-term-scope__btn sp-term-scope__btn--primary"
                    disabled={!englishProposal.english.trim() || englishBusy}
                    onClick={() => void applyEnglish()}
                  >
                    <i className="fa-solid fa-check" aria-hidden="true" /> This
                    instance
                  </button>
                  <button
                    type="button"
                    className="sp-term-scope__btn"
                    disabled={!englishProposal.english.trim() || englishBusy}
                    onClick={() => void applyEnglishAcross("chapter")}
                  >
                    <i className="fa-solid fa-file-lines" aria-hidden="true" />{" "}
                    This chapter
                  </button>
                  <button
                    type="button"
                    className="sp-term-scope__btn"
                    disabled={!englishProposal.english.trim() || englishBusy}
                    onClick={() => void applyEnglishAcross("book")}
                  >
                    <i className="fa-solid fa-book" aria-hidden="true" /> All
                    chapters
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {explainProposal && (
          <div
            className="sp-term-backdrop"
            role="dialog"
            aria-modal="true"
            aria-label="Explanation replacement"
          >
            <div className="sp-term-modal sp-term-modal--wide">
              <header className="sp-term-modal__head">
                <div>
                  <p className="sp-term-modal__eyebrow">Clarify selection</p>
                  <h3 className="sp-term-modal__title">
                    Edit the replacement text
                  </h3>
                </div>
                <button
                  type="button"
                  className="sp-term-modal__close"
                  onClick={cancelExplain}
                  aria-label="Close"
                >
                  <i className="fa-solid fa-xmark" aria-hidden="true" />
                </button>
              </header>
              <div className="sp-term-modal__body">
                <textarea
                  className="sp-term-modal__textarea"
                  value={explainProposal.text}
                  rows={7}
                  onChange={(e) =>
                    setExplainProposal({
                      ...explainProposal,
                      text: e.target.value,
                    })
                  }
                  aria-label="Explanation — edit before replacing"
                  autoFocus
                />
                <div className="sp-term-modal__actions">
                  <button
                    type="button"
                    className="sp-term-modal__apply"
                    onClick={applyExplain}
                    disabled={!explainProposal.text.trim()}
                  >
                    <i className="fa-solid fa-check" aria-hidden="true" />{" "}
                    Replace
                  </button>
                  <button
                    type="button"
                    className="sp-term-modal__cancel"
                    onClick={cancelExplain}
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Global find-and-replace popup ── */}
        {replaceOpen && (
          <div
            className="sp-replace-backdrop"
            role="dialog"
            aria-modal="true"
            aria-label="Find and replace"
          >
            <div className="sp-replace-modal">
              <header className="sp-replace-head">
                <h3 className="sp-replace-title">
                  <i className="fa-solid fa-right-left" aria-hidden="true" />{" "}
                  Find &amp; replace
                </h3>
                <button
                  type="button"
                  className="sp-replace-close"
                  onClick={closeReplace}
                  aria-label="Close"
                >
                  <i className="fa-solid fa-xmark" aria-hidden="true" />
                </button>
              </header>

              <div className="sp-replace-body">
                {replacePairs.map((p, i) => (
                  <div key={i} className="sp-replace-row">
                    <input
                      className="sp-replace-input"
                      placeholder="Find…"
                      value={p.find}
                      aria-label={`Find phrase ${i + 1}`}
                      onChange={(e) => {
                        updatePair(i, "find", e.target.value);
                        setReplacePreview(null);
                        setReplaceDone("");
                      }}
                    />
                    <i
                      className="fa-solid fa-arrow-right-long sp-replace-arrow"
                      aria-hidden="true"
                    />
                    <input
                      className="sp-replace-input"
                      placeholder="Replace with…"
                      value={p.replace}
                      aria-label={`Replacement ${i + 1}`}
                      onChange={(e) => {
                        updatePair(i, "replace", e.target.value);
                        setReplacePreview(null);
                        setReplaceDone("");
                      }}
                    />
                    <button
                      type="button"
                      className="sp-replace-row-rm"
                      onClick={() => removePair(i)}
                      disabled={replacePairs.length === 1}
                      aria-label={`Remove replacement ${i + 1}`}
                    >
                      <i className="fa-solid fa-xmark" aria-hidden="true" />
                    </button>
                  </div>
                ))}

                <button
                  type="button"
                  className="sp-replace-add"
                  onClick={addPair}
                >
                  <i className="fa-solid fa-plus" aria-hidden="true" /> Add
                  another replacement
                </button>

                <label className="sp-replace-scope">
                  <input
                    type="checkbox"
                    checked={replaceScope === "book"}
                    onChange={(e) => {
                      setReplaceScope(e.target.checked ? "book" : "chapter");
                      setReplacePreview(null);
                      setReplaceDone("");
                    }}
                  />
                  <span>
                    Apply to <strong>all chapters</strong> in this book{" "}
                    {replaceScope === "book"
                      ? ""
                      : "(otherwise this chapter only)"}
                  </span>
                </label>

                {replaceError && (
                  <p className="sp-replace-msg sp-replace-msg--error">
                    {replaceError}
                  </p>
                )}
                {replaceDone && (
                  <p className="sp-replace-msg sp-replace-msg--ok">
                    {replaceDone}
                  </p>
                )}

                {replacePreview && !replaceDone && (
                  <div className="sp-replace-preview">
                    <p className="sp-replace-preview-total">
                      {replaceTotal} match{replaceTotal === 1 ? "" : "es"}
                      {replacePreview.length > 0
                        ? ` across ${replacePreview.length} chapter${replacePreview.length === 1 ? "" : "s"}`
                        : ""}
                    </p>
                    {replacePreview.length > 0 && (
                      <ul className="sp-replace-preview-list">
                        {replacePreview.map((r) => (
                          <li key={r.chapter}>
                            <span>{chapterLabel(r.chapter)}</span>
                            <span className="sp-replace-preview-n">
                              {r.count}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>

              <footer className="sp-replace-foot">
                <button
                  type="button"
                  className="sp-replace-btn sp-replace-btn--ghost"
                  onClick={() => void runReplace(false)}
                  disabled={replaceBusy}
                >
                  {replaceBusy ? "Working…" : "Preview"}
                </button>
                <button
                  type="button"
                  className="sp-replace-btn sp-replace-btn--apply"
                  onClick={() => void runReplace(true)}
                  disabled={
                    replaceBusy ||
                    (replacePreview !== null && replaceTotal === 0)
                  }
                >
                  {replacePreview && !replaceDone
                    ? `Replace ${replaceTotal}`
                    : "Replace"}
                </button>
              </footer>
            </div>
          </div>
        )}

        {noiseOpen && (
          <div
            className="sp-replace-backdrop"
            role="dialog"
            aria-modal="true"
            aria-label="Mark as noise"
          >
            <div className="sp-replace-modal">
              <header className="sp-replace-head">
                <h3 className="sp-replace-title">
                  <i className="fa-solid fa-eraser" aria-hidden="true" /> Mark
                  as noise
                </h3>
                <button
                  type="button"
                  className="sp-replace-close"
                  onClick={closeNoise}
                  aria-label="Close"
                >
                  <i className="fa-solid fa-xmark" aria-hidden="true" />
                </button>
              </header>

              <div className="sp-replace-body">
                <p className="sp-noise-hint">
                  The selection is generalised to a <strong>pattern</strong>{" "}
                  (digits and spacing loosened so variants match). Edit it if
                  needed, <strong>preview</strong> what it catches, then strip
                  every match. Removed text is backed up per file.
                </p>
                <input
                  className="sp-replace-input sp-noise-pattern"
                  value={noisePattern}
                  aria-label="Noise pattern (regular expression)"
                  spellCheck={false}
                  onChange={(e) => {
                    setNoisePattern(e.target.value);
                    setNoisePreview(null);
                    setNoiseDone("");
                  }}
                />

                <label className="sp-replace-scope">
                  <input
                    type="checkbox"
                    checked={noiseScope === "book"}
                    onChange={(e) => {
                      setNoiseScope(e.target.checked ? "book" : "chapter");
                      setNoisePreview(null);
                      setNoiseDone("");
                    }}
                  />
                  <span>
                    Strip from <strong>all chapters</strong> in this book{" "}
                    {noiseScope === "book"
                      ? ""
                      : "(otherwise this chapter only)"}
                  </span>
                </label>

                {noiseError && (
                  <p className="sp-replace-msg sp-replace-msg--error">
                    {noiseError}
                  </p>
                )}
                {noiseDone && (
                  <p className="sp-replace-msg sp-replace-msg--ok">
                    {noiseDone}
                  </p>
                )}

                {noisePreview && !noiseDone && (
                  <div className="sp-replace-preview">
                    <p className="sp-replace-preview-total">
                      {noiseTotal} match{noiseTotal === 1 ? "" : "es"}
                      {noisePreview.length > 0
                        ? ` across ${noisePreview.length} chapter${noisePreview.length === 1 ? "" : "s"}`
                        : " — nothing to strip"}
                    </p>
                    {noisePreview.length > 0 && (
                      <ul className="sp-replace-preview-list">
                        {noisePreview.map((r) => (
                          <li key={r.chapter}>
                            <span>{chapterLabel(r.chapter)}</span>
                            <span className="sp-replace-preview-n">
                              {r.count}
                            </span>
                            {r.samples?.length > 0 && (
                              <span className="sp-noise-samples">
                                {r.samples.map((s, k) => (
                                  <code key={k} className="sp-noise-sample">
                                    {s}
                                  </code>
                                ))}
                              </span>
                            )}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </div>

              <footer className="sp-replace-foot">
                <button
                  type="button"
                  className="sp-replace-btn sp-replace-btn--ghost"
                  onClick={() => void runDenoise(false)}
                  disabled={noiseBusy}
                >
                  {noiseBusy ? "Working…" : "Preview"}
                </button>
                <button
                  type="button"
                  className="sp-replace-btn sp-replace-btn--apply"
                  onClick={() => void runDenoise(true)}
                  disabled={
                    noiseBusy || noisePreview === null || noiseTotal === 0
                  }
                >
                  {noisePreview && !noiseDone
                    ? `Strip ${noiseTotal}`
                    : "Strip noise"}
                </button>
              </footer>
            </div>
          </div>
        )}
      </div>
      <Toast.Root
        className="sp-toast"
        open={approvalToastOpen}
        onOpenChange={setApprovalToastOpen}
      >
        <Toast.Title className="sp-toast-title">
          {approvalToastText}
        </Toast.Title>
      </Toast.Root>
      <Toast.Viewport className="sp-toast-viewport" />
    </Toast.Provider>
  );
}
