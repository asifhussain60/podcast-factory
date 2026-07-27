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
import { alignBlocks } from "./block-align";

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
  /**
   * Render HUMAN edits as word-level track changes (tc-ins / tc-del).
   *
   * Separate from showPrevDiffRef, which governs the pipeline-stage diff in its
   * teal palette. Before 2026-07-27 the human diff had no switch at all: every
   * difference between the editor and the text as loaded was painted, always. In
   * Edit & Enrich that is the point — it is a track-changes surface. In the Book
   * Composer it meant that accepting one AI rewrite repainted the whole paragraph
   * as strikethrough-plus-underline, so the version you had just chosen became
   * the hardest one to read.
   */
  showEditDiffRef: Box<boolean>;
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
    showEditDiffRef,
    prevStageTextsRef,
    arabicRef,
    depthLevels,
    glossarySorted,
  } = bag;

  // Compiled ONCE per editor mount, not once per (glossary term x text node x
  // keystroke). `glossarySorted` is fixed for the life of the extension, so the
  // pattern never changes; only `lastIndex` does, and every use below resets it
  // before scanning. On a long chapter this is the difference between a few
  // hundred RegExp constructions per keypress and tens of thousands.
  const glossaryMatchers: { re: RegExp; script: string }[] = glossarySorted.map(
    (e) => ({
      re: new RegExp(
        `(?<![\\w-])${e.phonetic.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?![\\w'’-])`,
        "g",
      ),
      script: e.arabic_script,
    }),
  );
  const arabicRunRe = new RegExp(ARABIC_SCRIPT_RUN.source, "g");

  // Alignment is a pure function of (doc, baseline), and ProseMirror docs are
  // immutable, so one WeakMap entry per doc is exact — a selection-only
  // transaction reuses the previous result instead of rebuilding the table.
  const alignCache = new WeakMap<
    object,
    { baseline: string[]; aligned: (number | null)[] }
  >();
  function alignmentFor(
    doc: { textBetween?: unknown },
    baseline: string[],
    currentTexts: string[],
  ): (number | null)[] {
    const hit = alignCache.get(doc as object);
    if (hit && hit.baseline === baseline) return hit.aligned;
    const aligned = alignBlocks(baseline, currentTexts);
    alignCache.set(doc as object, { baseline, aligned });
    return aligned;
  }

  return Extension.create({
    name: "studioDecos",
    addProseMirrorPlugins() {
      return [
        new Plugin({
          key: new PluginKey("studioDecos"),
          // Keep the human-edit baseline structurally in step with the document.
          //
          // The baseline is a flat array of paragraph texts captured when the
          // chapter opened. Split a paragraph and the document now has one more
          // block than the baseline does, so the first half's baseline is the
          // WHOLE original paragraph — every later keystroke in it then diffs
          // against text that has merely moved to the sibling block, and the
          // moved half reappears as struck-out prose. Re-splitting the baseline
          // at the moment of the split keeps each half diffing against its own
          // half, so editing after a split tracks normally and nothing phantom
          // is ever drawn.
          //
          // This runs in `apply` — exactly once per transaction, outside the
          // render path — rather than in `decorations`, which must stay pure.
          state: {
            init: () => null,
            apply(tr, _value, oldState, newState) {
              if (!tr.docChanged) return null;
              const oldTexts: string[] = [];
              oldState.doc.forEach((n) => oldTexts.push(n.textContent));
              const newTexts: string[] = [];
              newState.doc.forEach((n) => newTexts.push(n.textContent));
              const delta = newTexts.length - oldTexts.length;
              if (delta !== 1 && delta !== -1) return null;

              const baseline = originalRef.current;
              if (!baseline.length) return null;
              const toOld = alignBlocks(baseline, oldTexts);
              const baseIndexOf = (k: number): number | null =>
                k >= 0 && k < toOld.length ? toOld[k] : null;

              if (delta === 1) {
                // A split: old block k became new blocks k and k+1.
                const k = newTexts.findIndex(
                  (t, i) => t !== oldTexts[i] || i >= oldTexts.length,
                );
                if (k < 0 || k + 1 >= newTexts.length) return null;
                if (oldTexts[k] !== newTexts[k] + newTexts[k + 1]) return null;
                const b = baseIndexOf(k);
                if (b == null) return null;
                const next = baseline.slice();
                next.splice(b, 1, newTexts[k], newTexts[k + 1]);
                originalRef.current = next;
              } else {
                // A merge: old blocks k and k+1 became new block k.
                const k = oldTexts.findIndex(
                  (t, i) => t !== newTexts[i] || i >= newTexts.length,
                );
                if (k < 0 || k + 1 >= oldTexts.length) return null;
                if (newTexts[k] !== oldTexts[k] + oldTexts[k + 1]) return null;
                const b = baseIndexOf(k);
                const b2 = baseIndexOf(k + 1);
                if (b == null || b2 == null || b2 !== b + 1) return null;
                const next = baseline.slice();
                next.splice(b, 2, baseline[b] + baseline[b2]);
                originalRef.current = next;
              }
              return null;
            },
          },
          props: {
            decorations(state) {
              const orig = originalRef.current;
              // The baseline each block is diffed against, and the map from a
              // CURRENT block to its counterpart in that baseline. Positional
              // indexing breaks the moment a paragraph is split or merged —
              // see alignBlocks.
              const baseline = showPrevDiffRef.current
                ? prevStageTextsRef.current
                : orig;
              const currentTexts: string[] = [];
              state.doc.forEach((n) => currentTexts.push(n.textContent));
              const alignment = alignmentFor(state.doc, baseline, currentTexts);
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
                      // Keyed on position + label so an unchanged chip keeps its
                      // DOM node across transactions instead of being rebuilt.
                      { side: -1, key: `qref-${from}-${label}` },
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
                        bar.className = "sp-para-tools sp-para-tools--marks";
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
                // A block with no counterpart in the baseline is genuinely new
                // (the second half of a split, or a paragraph just typed).
                // It gets the dirty background below, but NOT a word-diff —
                // diffing it against an unrelated block is what produced the
                // wall of struck-out neighbouring text.
                const baseIdx = alignment[idx];
                const before = baseIdx == null ? undefined : baseline[baseIdx];
                const insClass = prevDiff ? "aug-ins" : "tc-ins";
                const delClass = prevDiff ? "aug-del" : "tc-del";
                const after = node.textContent;
                // A PURE structural edit — splitting one paragraph in two, or
                // merging two into one — moves text between blocks without
                // changing a word of it. Diffing it would strike out the half
                // that merely moved next door: pressing Enter once painted 433
                // characters of untouched prose as "deleted", which reads as the
                // editor dumping text into the chapter. Only exact
                // concatenations qualify, so a split that also edits a word
                // still tracks that word normally.
                const isPureSplit =
                  before !== undefined &&
                  before === after + (currentTexts[idx + 1] ?? " ");
                const isPureMerge =
                  before !== undefined &&
                  baseIdx != null &&
                  after === before + (baseline[baseIdx + 1] ?? " ");
                // The stage diff has its own toggle; the human diff has this one,
                // which the Composer defaults to OFF. With it off the text simply
                // reads as text — the para-dirty tint below still marks WHICH
                // blocks changed, so "edited and unsaved" is never lost, only the
                // word-by-word markup.
                const showWordDiff = prevDiff || showEditDiffRef.current;
                if (
                  showWordDiff &&
                  before !== undefined &&
                  before !== after &&
                  !isPureSplit &&
                  !isPureMerge
                ) {
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
                            // The struck-out word is track-changes chrome, not
                            // prose: keep it out of the editable flow so a caret
                            // can never land inside it and it is never selected
                            // or copied as if it were text the author typed.
                            del.contentEditable = "false";
                            return del;
                          },
                          // Keyed so a still-deleted word is not torn down and
                          // rebuilt on every keystroke (the flicker that reads
                          // as "my typing is being doubled").
                          { side: -1, key: `${delClass}-${cursor}-${text}` },
                        ),
                      );
                    } else {
                      cursor += len;
                    }
                  }
                }

                // Para-dirty: warm background on blocks the user has edited vs the original.
                // Only shown in human-edit mode (not prev-stage diff) so it tracks real changes.
                if (!prevDiff && orig.length > 0 && before !== after) {
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
                    for (const { re, script } of glossaryMatchers) {
                      // Don't fire inside compounds/possessives: the compiled pattern
                      // skips a match adjacent to a letter, hyphen, or apostrophe (so
                      // "al-Quran"/"Ghazali's" stay English).
                      re.lastIndex = 0;
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
                          Decoration.inline(from, to, { class: "ar-hidden" }),
                        );
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
                            // Keyed so an unchanged overlay is reused instead of
                            // torn down and rebuilt on every transaction.
                            { side: -1, key: `ar-${from}-${script}` },
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
                  arabicRunRe.lastIndex = 0;
                  let am: RegExpExecArray | null;
                  while ((am = arabicRunRe.exec(child.text!))) {
                    const from = base + am.index;
                    const to = from + am[0].length;
                    if (!arabicRef.current && inPairedArabic(from)) continue;
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
  });
}
