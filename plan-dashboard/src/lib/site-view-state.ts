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
 * Edit & Enrich — which chapter was last open, by its stable slug (not index:
 * the chapter list can be regenerated between visits, and an index would then
 * point at whatever happens to sit in that slot rather than the chapter the
 * reader actually meant). A `?ch=` deep link (from the Library chapter reader)
 * takes priority over this on arrival — see StudioEditor's mount effect.
 */
export const editorChapter = defineViewState<string>({
  surface: "studio-editor",
  field: "chapter",
  validate: (raw) => (raw.length > 0 ? raw : null),
});
