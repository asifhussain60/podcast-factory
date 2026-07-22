/**
 * studio-editor-pickers.ts — module-level imperative-DOM popovers (section
 * depth picker + section tag picker) with shared scroll lock. Extracted from
 * StudioEditor.tsx (R2 pass 1a — mechanical, verbatim). Deliberately OUTSIDE
 * React: the decoration plugin closure calls openDepthPicker()/openTagPicker()
 * directly at any point after import (ref-timing safety).
 */
import {
  CONTENT_SECTION_TAGS,
  WORKFLOW_SECTION_TAGS,
  type DepthLevel,
  type SaveDepthFn,
} from "./studio-editor-constants";

// Scroll lock: prevent body scroll while any picker is open.
let _scrollLockCount = 0;
let _savedBodyOverflow = "";
function _lockScroll() {
  if (_scrollLockCount++ === 0) {
    _savedBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
  }
}
function _unlockScroll() {
  if (--_scrollLockCount <= 0) {
    _scrollLockCount = 0;
    document.body.style.overflow = _savedBodyOverflow;
    _savedBodyOverflow = "";
  }
}

let _dpEl: HTMLDivElement | null = null;
let _dpSaveFn: SaveDepthFn = () => {};
let _dpOrd = 0;
let _dpSection = "";
let _dpOutside: ((e: MouseEvent) => void) | null = null;
let _dpKey: ((e: KeyboardEvent) => void) | null = null;

// Active tag set is tracked in the picker's DOM dataset so it survives open/close cycles
// without needing React state.
let _dpCurrentTags: string[] = [];

function _buildDepthPicker(levels: readonly DepthLevel[]): HTMLDivElement {
  const pop = document.createElement("div");
  pop.className = "sp-depth-popover";
  pop.setAttribute("role", "dialog");
  pop.setAttribute("aria-label", "Set section depth and tags");

  // ── Zone 1: depth level (single-select) ───────────────────────────────────
  const depthTitle = document.createElement("div");
  depthTitle.className = "sp-depth-popover__title";
  depthTitle.textContent = "Depth level";
  pop.appendChild(depthTitle);

  const grid = document.createElement("div");
  grid.className = "sp-depth-popover__grid";
  pop.appendChild(grid);

  for (const { key, label } of levels) {
    const opt = document.createElement("button");
    opt.type = "button";
    opt.className = `sp-depth-popover__opt sp-depth-${key}`;
    opt.setAttribute("data-depth-level", key);
    opt.textContent = label;
    grid.appendChild(opt);
  }

  const clearBtn = document.createElement("button");
  clearBtn.type = "button";
  clearBtn.className = "sp-depth-popover__clear";
  clearBtn.setAttribute("data-depth-level", "");
  clearBtn.textContent = "∅ clear depth";
  pop.appendChild(clearBtn);

  // ── Event handling (depth only — tags have their own picker) ──────────────
  pop.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    const depthBtn = target.closest("[data-depth-level]") as HTMLElement | null;
    if (depthBtn) {
      const level = depthBtn.dataset.depthLevel;
      if (level !== undefined) {
        _dpSaveFn(_dpOrd, _dpSection, level, _dpCurrentTags);
        closeDepthPicker();
      }
    }
  });

  document.body.appendChild(pop);
  return pop;
}

export function closeDepthPicker() {
  if (!_dpEl?.classList.contains("is-open")) return;
  _dpEl.classList.remove("is-open");
  if (_dpOutside) {
    document.removeEventListener("mousedown", _dpOutside, true);
    _dpOutside = null;
  }
  if (_dpKey) {
    document.removeEventListener("keydown", _dpKey, true);
    _dpKey = null;
  }
  _unlockScroll();
}

export function openDepthPicker(
  anchorEl: HTMLElement,
  saveFn: SaveDepthFn,
  ord: number,
  sectionText: string,
  currentLevel: string | undefined,
  levels: readonly DepthLevel[],
  currentTags: string[],
) {
  _dpSaveFn = saveFn;
  _dpOrd = ord;
  _dpSection = sectionText;
  _dpCurrentTags = [...currentTags];

  if (!_dpEl) _dpEl = _buildDepthPicker(levels);
  const pop = _dpEl;

  pop.querySelectorAll("[data-depth-level]").forEach((el) => {
    const k = (el as HTMLElement).dataset.depthLevel;
    el.classList.toggle("is-active", !!k && k === currentLevel);
  });

  const rect = anchorEl.getBoundingClientRect();
  const popW = 258;
  let left = rect.left;
  if (left + popW > window.innerWidth - 8) left = window.innerWidth - popW - 8;
  pop.style.top = `${rect.bottom + 6}px`;
  pop.style.left = `${Math.max(8, left)}px`;
  pop.classList.add("is-open");
  _lockScroll();

  if (_dpOutside) document.removeEventListener("mousedown", _dpOutside, true);
  if (_dpKey) document.removeEventListener("keydown", _dpKey, true);

  _dpOutside = (ev) => {
    if (!pop.contains(ev.target as Node) && ev.target !== anchorEl)
      closeDepthPicker();
  };
  _dpKey = (ev) => {
    if (ev.key === "Escape") closeDepthPicker();
  };

  requestAnimationFrame(() => {
    document.addEventListener("mousedown", _dpOutside!, true);
    document.addEventListener("keydown", _dpKey!, true);
  });
}

let _tpEl: HTMLDivElement | null = null;
let _tpSaveFn: SaveDepthFn = () => {};
let _tpOrd = 0;
let _tpSection = "";
let _tpCurrentDepth = "";
let _tpCurrentTags: string[] = [];
let _tpOutside: ((e: MouseEvent) => void) | null = null;
let _tpKey: ((e: KeyboardEvent) => void) | null = null;

function _syncTpButtons(pop: HTMLDivElement): void {
  pop.querySelectorAll("[data-section-tag]").forEach((el) => {
    const tid = (el as HTMLElement).dataset.sectionTag!;
    el.classList.toggle("is-active", _tpCurrentTags.includes(tid));
  });
}

function _buildTagPicker(): HTMLDivElement {
  const pop = document.createElement("div");
  pop.className = "sp-tag-popover";
  pop.setAttribute("role", "dialog");
  pop.setAttribute("aria-label", "Set section tags");

  const contentTitle = document.createElement("div");
  contentTitle.className = "sp-tag-popover__group-title";
  contentTitle.textContent = "Content labels";
  pop.appendChild(contentTitle);

  const contentGrid = document.createElement("div");
  contentGrid.className = "sp-tag-popover__grid";
  for (const { id, label } of CONTENT_SECTION_TAGS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `sp-tag-popover__tag sp-tag-popover__tag--${id}`;
    btn.setAttribute("data-section-tag", id);
    btn.textContent = label;
    contentGrid.appendChild(btn);
  }
  pop.appendChild(contentGrid);

  const sep = document.createElement("hr");
  sep.className = "sp-tag-popover__sep";
  pop.appendChild(sep);

  const workflowTitle = document.createElement("div");
  workflowTitle.className =
    "sp-tag-popover__group-title sp-tag-popover__group-title--workflow";
  workflowTitle.textContent = "Editorial flags";
  pop.appendChild(workflowTitle);

  const workflowGrid = document.createElement("div");
  workflowGrid.className =
    "sp-tag-popover__grid sp-tag-popover__grid--workflow";
  for (const { id, label } of WORKFLOW_SECTION_TAGS) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `sp-tag-popover__tag sp-tag-popover__tag--${id}`;
    btn.setAttribute("data-section-tag", id);
    btn.textContent = label;
    workflowGrid.appendChild(btn);
  }
  pop.appendChild(workflowGrid);

  pop.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    const tagBtn = target.closest("[data-section-tag]") as HTMLElement | null;
    if (tagBtn) {
      const tid = tagBtn.dataset.sectionTag!;
      if (_tpCurrentTags.includes(tid)) {
        _tpCurrentTags = _tpCurrentTags.filter((t) => t !== tid);
      } else {
        _tpCurrentTags = [..._tpCurrentTags, tid];
      }
      _syncTpButtons(pop);
      _tpSaveFn(_tpOrd, _tpSection, _tpCurrentDepth, _tpCurrentTags);
    }
  });

  document.body.appendChild(pop);
  return pop;
}

export function closeTagPicker() {
  if (!_tpEl?.classList.contains("is-open")) return;
  _tpEl.classList.remove("is-open");
  if (_tpOutside) {
    document.removeEventListener("mousedown", _tpOutside, true);
    _tpOutside = null;
  }
  if (_tpKey) {
    document.removeEventListener("keydown", _tpKey, true);
    _tpKey = null;
  }
  _unlockScroll();
}

export function openTagPicker(
  anchorEl: HTMLElement,
  saveFn: SaveDepthFn,
  ord: number,
  sectionText: string,
  currentTags: string[],
  currentDepth: string,
) {
  _tpSaveFn = saveFn;
  _tpOrd = ord;
  _tpSection = sectionText;
  _tpCurrentDepth = currentDepth;
  _tpCurrentTags = [...currentTags];

  if (!_tpEl) _tpEl = _buildTagPicker();
  const pop = _tpEl;

  _syncTpButtons(pop);

  const rect = anchorEl.getBoundingClientRect();
  const popW = 244;
  let left = rect.left;
  if (left + popW > window.innerWidth - 8) left = window.innerWidth - popW - 8;
  pop.style.top = `${rect.bottom + 6}px`;
  pop.style.left = `${Math.max(8, left)}px`;
  pop.classList.add("is-open");
  _lockScroll();

  if (_tpOutside) document.removeEventListener("mousedown", _tpOutside, true);
  if (_tpKey) document.removeEventListener("keydown", _tpKey, true);

  _tpOutside = (ev) => {
    if (!pop.contains(ev.target as Node) && ev.target !== anchorEl)
      closeTagPicker();
  };
  _tpKey = (ev) => {
    if (ev.key === "Escape") closeTagPicker();
  };

  requestAnimationFrame(() => {
    document.addEventListener("mousedown", _tpOutside!, true);
    document.addEventListener("keydown", _tpKey!, true);
  });
}
