/**
 * compose-placement-fields.ts — the seven controls on the Book Composer's
 * floating figure card (alignment, flow, width, anchor chapter, position in
 * chapter, caption, page fit).
 *
 * Moved verbatim out of ./book-composer.ts on 2026-09-04 (frontend size
 * ratchet). The builders are unchanged; they simply take what they used to
 * close over — the chapter list, the chapter index, and the placement `update`
 * — from one deps object instead of from `boot`'s scope. Behaviour, markup,
 * classes and event wiring are identical.
 */

import { anchorKey } from "../../scripts/lib/anchor-key.mjs";
import { WRAP_MAX } from "./compose-toolbar-config";
import type {
  Align,
  Chapter,
  Flow,
  PageFit,
  Placement,
} from "./compose-data-types";

export interface PlacementFieldDeps {
  /** The book's chapters, in order — the anchor dropdown's options. */
  chapters: Chapter[];
  /** Chapter by anchor key — how the position dropdown learns its paragraph count. */
  chapterByKey: Map<string, Chapter>;
  /** Persist a patch to one placement. */
  update(visualId: string, patch: Partial<Placement>): void;
}

export interface PlacementFields {
  alignField(p: Placement): HTMLElement;
  flowField(p: Placement): HTMLElement;
  widthField(p: Placement): HTMLElement;
  anchorField(p: Placement): HTMLElement;
  positionField(p: Placement): HTMLElement;
  captionField(p: Placement): HTMLElement;
  pageFitField(p: Placement): HTMLElement;
}

export function createPlacementFields({
  chapters,
  chapterByKey,
  update,
}: PlacementFieldDeps): PlacementFields {
  function field(label: string, control: HTMLElement): HTMLElement {
    const wrap = document.createElement("div");
    wrap.className = "cx-field";
    const l = document.createElement("label");
    l.textContent = label;
    wrap.append(l, control);
    return wrap;
  }

  function alignField(p: Placement): HTMLElement {
    const row = document.createElement("div");
    row.className = "cx-btn-row";
    (["left", "center", "right"] as Align[]).forEach((a) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cx-toggle";
      b.textContent = a;
      b.setAttribute("aria-pressed", String(p.align === a));
      b.addEventListener("click", () => update(p.visual_id, { align: a }));
      row.appendChild(b);
    });
    return field("Alignment", row);
  }

  function flowField(p: Placement): HTMLElement {
    const row = document.createElement("div");
    row.className = "cx-btn-row";
    (["standalone", "wrap"] as Flow[]).forEach((f) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "cx-toggle";
      b.textContent = f === "wrap" ? "wrap text" : "standalone";
      b.setAttribute("aria-pressed", String(p.flow === f));
      b.disabled = f === "wrap" && p.align === "center";
      // Choosing wrap clamps width into the contract (<=50%) so the user's intent
      // is honored rather than silently reverted to standalone.
      b.addEventListener("click", () =>
        update(
          p.visual_id,
          f === "wrap"
            ? { flow: f, width_pct: Math.min(p.width_pct, WRAP_MAX) }
            : { flow: f },
        ),
      );
      row.appendChild(b);
    });
    return field("Flow", row);
  }

  function widthField(p: Placement): HTMLElement {
    const input = document.createElement("input");
    input.type = "range";
    input.min = "10";
    input.max = String(p.flow === "wrap" ? WRAP_MAX : 100);
    input.step = "5";
    input.value = String(p.width_pct);
    input.setAttribute("aria-label", "Width percent");
    input.addEventListener("input", () =>
      update(p.visual_id, { width_pct: Number(input.value) }),
    );
    return field(`Width — ${p.width_pct}%`, input);
  }

  function anchorField(p: Placement): HTMLElement {
    const sel = document.createElement("select");
    sel.setAttribute("aria-label", "Anchor chapter");
    chapters.forEach((c) => {
      const o = document.createElement("option");
      o.value = c.anchor;
      o.textContent = c.title;
      o.selected = anchorKey(c.anchor) === anchorKey(p.anchor);
      sel.appendChild(o);
    });
    // Moving to a different chapter resets the paragraph position to the default.
    sel.addEventListener("change", () =>
      update(p.visual_id, { anchor: sel.value, anchor_para: null }),
    );
    return field("Anchor chapter", sel);
  }

  function positionField(p: Placement): HTMLElement {
    const paras = chapterByKey.get(anchorKey(p.anchor))?.paras ?? 0;
    const sel = document.createElement("select");
    const opt = (value: string, label: string, selected: boolean) => {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = label;
      o.selected = selected;
      sel.appendChild(o);
    };
    sel.setAttribute("aria-label", "Position in chapter");
    opt("", "After intro (default)", p.anchor_para == null);
    opt("0", "Chapter top", p.anchor_para === 0);
    for (let i = 1; i <= paras; i += 1)
      opt(String(i), `After paragraph ${i}`, p.anchor_para === i);
    sel.addEventListener("change", () =>
      update(p.visual_id, {
        anchor_para: sel.value === "" ? null : Number(sel.value),
      }),
    );
    return field("Position in chapter", sel);
  }

  function captionField(p: Placement): HTMLElement {
    const input = document.createElement("input");
    input.type = "text";
    input.value = p.caption;
    input.placeholder = "Caption (optional)";
    input.setAttribute("aria-label", "Caption");
    input.addEventListener("change", () =>
      update(p.visual_id, { caption: input.value }),
    );
    return field("Caption", input);
  }

  function pageFitField(p: Placement): HTMLElement {
    const sel = document.createElement("select");
    sel.setAttribute("aria-label", "Page fit");
    (["avoid", "before", "isolate-plate"] as PageFit[]).forEach((f) => {
      const o = document.createElement("option");
      o.value = f;
      o.textContent =
        f === "avoid"
          ? "keep together"
          : f === "before"
            ? "start on new page"
            : "own page";
      o.selected = p.page_fit === f;
      sel.appendChild(o);
    });
    sel.addEventListener("change", () =>
      update(p.visual_id, { page_fit: sel.value as PageFit }),
    );
    return field("Page fit", sel);
  }

  return {
    alignField,
    flowField,
    widthField,
    anchorField,
    positionField,
    captionField,
    pageFitField,
  };
}
