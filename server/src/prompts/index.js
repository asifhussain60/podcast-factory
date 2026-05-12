// prompts/index.js — named-prompt registry + loader.
//
// Each named prompt lives in its own file and exports a default object
// { name, system, ...meta }. This file is the single lookup surface.

import refineGeneralPrompt from "./refine-general.js";
import themeSwatchesPrompt from "./theme-swatches.js";
import themeReviewPrompt from "./theme-review.js";

const REGISTRY = Object.freeze({
  [refineGeneralPrompt.name]: refineGeneralPrompt,
  [themeSwatchesPrompt.name]: themeSwatchesPrompt,
  [themeReviewPrompt.name]: themeReviewPrompt,
});

export function listPrompts() {
  return Object.keys(REGISTRY).sort();
}

export function hasPrompt(name) {
  return typeof name === "string" && Object.prototype.hasOwnProperty.call(REGISTRY, name);
}

export function loadPrompt(name) {
  if (!hasPrompt(name)) {
    throw new Error(`unknown prompt "${name}". Registered: ${listPrompts().join(", ") || "<none>"}`);
  }
  return REGISTRY[name];
}
