/**
 * studio-decos.ts — the Studio editor's ProseMirror decoration plugin (Quran/
 * hadith verse chips, section depth/tag badges, action-item marks, word-level
 * diff highlighting, Arabic glossary overlay, raw-Arabic coloring). Extracted
 * verbatim from StudioEditor.tsx's inline `useMemo(() => Extension.create(...))`
 * (R2 pattern: behavior-preserving, one extraction per commit) so both the
 * Edit & Enrich editor (React) and the Book Composer editor (vanilla TipTap)
 * can mount the identical decorations from one implementation.
 *
 * Framework-agnostic: every piece of live state it reads is a plain
 * `{ current: T }` mutable box — satisfied equally by a React `useRef()` or a
 * plain object literal — so this file has zero React dependency. Callers
 * construct a `StudioDecosBag` and pass it to `createStudioDecos(bag)`.
 */

import { Extension } from "@tiptap/core";
import type { Editor } from "@tiptap/core";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import { diffWords } from "diff";

import {
  ACTION_BY_KIND,
  ARABIC_PAIR_RE,
  ARABIC_SCRIPT_RUN,
  SECTION_TAGS,
  SURAH_MAP,
  SURAH_VERSE_RE,
  type ClientActionItem,
  type DepthLevel,
  type GlossaryEntry,
  type SaveDepthFn,
} from "./studio-editor-constants";
import { openDepthPicker, openTagPicker } from "./studio-editor-pickers";

export interface Box<T> {
  current: T;
}

export interface StudioDecosBag {
  originalRef: Box<string[]>;
  actionsRef: Box<ClientActionItem[]>;
  hasFocusRef: Box<boolean>;
  activeSectionOrdinalRef: Box<number | null>;
  sectionDepthsRef: Box<Record<number, string>>;
  sectionTagsRef: Box<Record<number, string[]>>;
  saveSectionDepthRef: Box<SaveDepthFn>;
  editorRef: Box<Editor | null>;
  runAiFnRef: Box<(kind: string) => void>;
  removeActionFnRef: Box<(id: number) => void>;
  showPrevDiffRef: Box<boolean>;
  prevStageTextsRef: Box<string[]>;
  arabicRef: Box<boolean>;
  depthLevels: readonly DepthLevel[];
  glossarySorted: GlossaryEntry[];
}

export function createStudioDecos(bag: StudioDecosBag) {
  const {
    originalRef,
    actionsRef,
    hasFocusRef,
    activeSectionOrdinalRef,
    sectionDepthsRef,
    sectionTagsRef,
    saveSectionDepthRef,
    editorRef,
    runAiFnRef,
    removeActionFnRef,
    showPrevDiffRef,
    prevStageTextsRef,
    arabicRef,
    depthLevels,
    glossarySorted,
  } = bag;

  return Extension.create({
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
                if (node.type.name === "heading" && node.attrs.level === 2) {
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
                        const tagPickerBtn = document.createElement("button");
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
                            if (n.type.name === "heading" && n.attrs.level === 2) {
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
                            { kind: "rewrite", label: "↺", title: "Rewrite section" },
                            { kind: "research", label: "🔍", title: "Research context" },
                            { kind: "autotag", label: "🏷", title: "Auto-tag section" },
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
                        bar.className = "sp-para-tools sp-para-tools--marks";
                        bar.setAttribute("role", "toolbar");
                        bar.setAttribute("aria-label", "Paragraph action marks");
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
                if (!prevDiff && orig[idx] !== undefined && orig[idx] !== after) {
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
                  const arabicTextOffset = pairMatch[0].indexOf(pairMatch[2]);
                  const arabicStart =
                    offset + 1 + pairMatch.index + arabicTextOffset;
                  const arabicEnd = arabicStart + pairMatch[2].length;
                  const pairEnd = offset + 1 + pairMatch.index + pairMatch[0].length;
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
                        const after = child.text!.slice(mm.index + mm[0].length);
                        if (
                          /^\s*\([\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF][^)]*\)/.test(
                            after,
                          )
                        ) {
                          continue;
                        }
                        decos.push(
                          Decoration.inline(from, to, { class: "ar-hidden" }),
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
                    if (!arabicRef.current && inPairedArabic(from)) continue;
                    decos.push(Decoration.inline(from, to, { class: "ar-raw" }));
                  }
                });
              });
              return DecorationSet.create(state.doc, decos);
            },
          },
        }),
      ];
    },
  });
}
