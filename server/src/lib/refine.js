// refine.js — voice DNA refinement handler.
// Reads the voice fingerprint via the consolidated voice-fingerprint.js cache
// so the fingerprint can be edited without restarting the proxy.
// Uses the named prompt registry for the system instruction.

import { getFingerprint, FINGERPRINT_PATH_RESOLVED } from "./voice-fingerprint.js";
import { loadPrompt } from "../prompts/index.js";

export function makeRefineHandler(anthropic, defaultModel) {
  return async function refineHandler(req, res) {
    const { text, model, max_tokens } = req.body ?? {};
    if (typeof text !== "string" || text.trim().length === 0) {
      return res.status(400).json({ ok: false, error: "text (non-empty string) is required" });
    }
    if (text.length > 20_000) {
      return res.status(413).json({ ok: false, error: "text exceeds 20000 chars — split into smaller chunks" });
    }

    let fingerprint;
    try {
      fingerprint = await getFingerprint();
    } catch (err) {
      return res.status(500).json({
        ok: false,
        error: `Could not load voice fingerprint at ${FINGERPRINT_PATH_RESOLVED}: ${err.message}`,
      });
    }

    const { system: instruction } = loadPrompt("refine-general");
    const system = `${fingerprint}\n\n---\n\n${instruction}`;

    try {
      const msg = await anthropic.messages.create({
        model: model ?? defaultModel,
        max_tokens: max_tokens ?? 2048,
        system,
        messages: [{ role: "user", content: text }],
      });
      const refined = msg.content.map((b) => (b.type === "text" ? b.text : "")).join("").trim();
      res.json({
        ok: true,
        model: msg.model,
        stopReason: msg.stop_reason,
        usage: msg.usage,
        refined,
      });
    } catch (err) {
      res.status(502).json({ ok: false, error: err?.message ?? String(err) });
    }
  };
}
