/**
 * articulate.server.ts — the pass that tightens a finished card, and the cap that
 * bounds it.
 *
 * A second model call reads the whole explanation and returns it tightened:
 * repetition removed, a heading not restated as its own first sentence, no closing
 * paragraph that says again what was just said. It is the only step here that can
 * make the card WORSE, so it is the only step with gates — Arabic runs survive,
 * citations survive, the result does not grow (articulate-rules.ts).
 *
 * Any gate fails and the ORIGINAL stands. So does any error, any empty answer, and
 * any timeout: this pass is an improvement, never a dependency. The gates and the
 * word cap live in articulate-rules.ts, which has no model client and is therefore
 * testable on its own.
 *
 * SERVER ONLY (calls gemini-server).
 */
import { generate } from "../gemini-server";
import {
  articulationGuardsPass,
  ARTICULATION_PROMPT as PROMPT,
  ARTICULATION_MIN_CHARS,
} from "./articulate-rules";

/**
 * Tighten `body`, or return it unchanged.
 *
 * Flash, not pro: this is an editing pass over text that already exists, and the
 * card is already two model calls deep by the time it runs.
 */
export async function articulate(body: string): Promise<string> {
  if (body.trim().length < ARTICULATION_MIN_CHARS) return body; // too short to have repetition worth a call
  try {
    const raw = await generate({
      model: "flash",
      systemInstruction: PROMPT,
      contents: [{ role: "user", parts: [{ text: body }] }],
      temperature: 0.2,
      maxOutputTokens: 4000,
    });
    const next = raw.replace(/^```(?:markdown)?\s*|\s*```$/g, "").trim();
    return articulationGuardsPass(body, next) ? next : body;
  } catch {
    return body;
  }
}
