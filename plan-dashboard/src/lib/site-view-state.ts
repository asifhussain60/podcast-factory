/**
 * site-view-state.ts — durable selections outside the Book Composer.
 *
 * The Composer keeps its own definitions in `scripts/compose-view-state.ts`
 * because it is a single self-contained surface with four of them. Everything
 * else on the site has one or two apiece, and they live here so the whole set
 * is visible in one place — `defineViewState` refuses a duplicate
 * surface+field, and that refusal is only useful if the definitions are
 * somewhere a person would look before adding another.
 *
 * Each is scoped by the slug of the thing being worked on, so two books never
 * restore into each other.
 */
import { defineViewState, oneOf } from "./view-state";

/** Pre-upload review — which of the two review tabs was last open. */
export const preUploadTab = defineViewState({
  surface: "pre-upload",
  field: "tab",
  validate: oneOf(["pronunciation", "ambiguity"] as const),
});

/** Edit & Enrich — which inspector tab was last open. */
export const editorInspectorTab = defineViewState({
  surface: "studio-editor",
  field: "inspector-tab",
  validate: oneOf(["details", "ai", "refs", "comment"] as const),
});

/**
 * LIVE Session — how far down the reading column the reader had got.
 *
 * Stored as a pixel offset rather than a chapter index: the view has no
 * chapter picker, it is one continuous scroll, and "where I was" in a reading
 * surface means the passage on screen, not the chapter containing it. A
 * negative or non-numeric value is rejected; an offset now past the end of a
 * shorter book simply lands at the bottom, which is harmless.
 */
export const liveScroll = defineViewState<number>({
  surface: "live",
  field: "scroll",
  serialize: (px) => String(Math.round(px)),
  validate: (raw) => {
    const px = Number(raw);
    return Number.isFinite(px) && px >= 0 ? px : null;
  },
});
