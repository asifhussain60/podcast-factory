/**
 * GET /api/intake/voices → the approved voice-casting pools for the intake picker.
 *
 * Reads scripts/podcast/voice-library.yaml through the TS reader
 * (src/lib/voice-library.ts), the same data the Python pipeline casts from.
 * Adding a voice is one YAML entry — no code change here or in the picker.
 */
import type { APIRoute } from 'astro';
import { loadVoicePools } from '../../../lib/voice-library';
import { apiOk, apiServerError } from '../../../lib/api-responses';

export const prerender = false;

export const GET: APIRoute = async () => {
  try {
    return apiOk(loadVoicePools());
  } catch (e) {
    return apiServerError(`could not read voice library: ${String(e)}`);
  }
};
