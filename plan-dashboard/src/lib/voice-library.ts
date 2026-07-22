/**
 * voice-library.ts — TS reader for the approved voice-casting pools.
 *
 * Mirrors the Python loader scripts/podcast/_voice_library.py (the way
 * content-paths.ts mirrors _paths.py): both parse the SAME data file,
 * scripts/podcast/voice-library.yaml, so adding a voice is one YAML entry with
 * no UI code change (extensibility-first).
 *
 * Server-side only (reads the repo file + parses YAML). The intake voice picker
 * fetches these pools through GET /api/intake/voices.
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import yaml from "js-yaml";
import { getRepoRoot } from "./content-paths";

export interface VoiceEntry {
  name: string; // short label used by series-config voice_cast
  fullName: string; // descriptive label shown on the card
  voiceId: string; // ElevenLabs voice id
  accent: string; // british | american | arabic_bilingual
  sample: string | null; // clip filename under /voice-samples/ (null if absent)
}

export interface VoicePools {
  males: VoiceEntry[];
  females: VoiceEntry[];
}

interface RawEntry {
  name?: string;
  full_name?: string;
  voice_id?: string;
  accent?: string;
  sample?: string;
}

function voiceLibraryPath(): string {
  return join(getRepoRoot(), "scripts", "podcast", "voice-library.yaml");
}

function toEntry(raw: RawEntry): VoiceEntry {
  return {
    name: String(raw.name ?? ""),
    fullName: String(raw.full_name ?? raw.name ?? ""),
    voiceId: String(raw.voice_id ?? ""),
    accent: String(raw.accent ?? ""),
    sample: raw.sample ? String(raw.sample) : null,
  };
}

/** Read + parse the approved pools. Throws only on a missing/corrupt library. */
export function loadVoicePools(): VoicePools {
  const doc = yaml.load(readFileSync(voiceLibraryPath(), "utf-8")) as {
    males?: RawEntry[];
    females?: RawEntry[];
  } | null;
  const males = (doc?.males ?? []).filter((e) => e?.name).map(toEntry);
  const females = (doc?.females ?? []).filter((e) => e?.name).map(toEntry);
  return { males, females };
}
