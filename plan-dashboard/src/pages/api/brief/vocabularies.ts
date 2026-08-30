/**
 * GET /api/brief/vocabularies → the option lists the Intake wizard renders.
 *
 * Thin pass-through to scripts/podcast/brief_vocabularies.py, which exports each
 * list from the pipeline registry that owns it. Deliberately does NOT serve the
 * seven fields /api/intake/form-options already owns — no vocabulary gets two
 * owners — so the wizard reads from both endpoints and merges them.
 */
import type { APIRoute } from "astro";
import { runPythonJson } from "../../../lib/intake-cli";
import { apiOk, apiError, apiServerError } from "../../../lib/api-responses";

export const prerender = false;

export const GET: APIRoute = async () => {
  try {
    const out = (await runPythonJson("brief_vocabularies.py", ["get"])) as {
      ok: boolean;
      error?: string;
      vocabularies?: Record<
        string,
        { value: string; label: string; description: string }[]
      >;
      defaults?: Record<string, string>;
      profile_narrative_frame?: Record<string, string>;
      profile_bucket?: Record<string, string>;
      family_profiles?: Record<string, Record<string, string>>;
      profile_category?: Record<string, string>;
      profile_audio_engine?: Record<string, string>;
      profile_voice_cast?: Record<string, Record<string, string>>;
    };
    if (!out.ok) return apiError(out.error ?? "failed to read vocabularies");
    return apiOk({
      vocabularies: out.vocabularies ?? {},
      defaults: out.defaults ?? {},
      profileNarrativeFrame: out.profile_narrative_frame ?? {},
      profileBucket: out.profile_bucket ?? {},
      familyProfiles: out.family_profiles ?? {},
      profileCategory: out.profile_category ?? {},
      profileAudioEngine: out.profile_audio_engine ?? {},
      profileVoiceCast: out.profile_voice_cast ?? {},
    });
  } catch (e) {
    return apiServerError(String(e));
  }
};
