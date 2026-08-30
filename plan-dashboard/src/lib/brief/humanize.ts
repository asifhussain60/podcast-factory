/**
 * humanize.ts — a pipeline token as a reader should see it.
 *
 * Used by the Intake wizard's dropdowns and by the generated brief, so a value
 * reads identically on screen and on the page. Vocabulary fields carry a real
 * label from the registry that owns them and never reach this; it is the
 * fallback for the plain string lists (/api/intake/form-options) that have no
 * labels of their own.
 *
 * SmartForm keeps its own copy of this rule for the launcher's form. Left alone
 * deliberately: merging them means editing a working surface this change was
 * asked to leave untouched.
 */
export function humanizeToken(field: string, value: string): string {
  if (!value) return value;
  if (field === "source_language" || field === "target_language") {
    try {
      const name = new Intl.DisplayNames(["en"], { type: "language" }).of(
        value,
      );
      if (name && name.toLowerCase() !== value.toLowerCase())
        return `${name} (${value})`;
    } catch {
      /* not a language code — fall through to the generic form */
    }
  }
  const words = value.replace(/[_-]/g, " ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : value;
}
