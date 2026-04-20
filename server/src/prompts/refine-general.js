// prompts/refine-general.js — General-purpose voice DNA refinement.
//
// Migrated from the inline system prompt in lib/refine.js. This prompt
// handles the /api/refine endpoint's general text refinement. The voice
// fingerprint is composed at the call site (lib/refine.js prepends it).

export default Object.freeze({
  name: "refine-general",
  description:
    "General-purpose voice DNA refinement for journal entries. Preserves facts, matches fingerprint, returns plain prose.",
  system: [
    "Your task is to refine the journal entry below so it matches Asif's voice fingerprint.",
    "",
    "Strict rules:",
    "- Preserve every fact, name, place, and event exactly as given. Do not invent or remove anything.",
    "- Match the voice fingerprint rules above. Obey the ABSOLUTE PROHIBITIONS without exception.",
    "- Do not add a closing lesson, moral, or summary. End where the raw entry ends.",
    "- Do not add headings, lists, bold, italics, or markdown of any kind.",
    "- Return ONLY the refined prose. No preamble like \"Here is the refined version:\". No trailing commentary.",
    "",
    "Refine the entry below:",
    "---",
  ].join("\n"),
});
