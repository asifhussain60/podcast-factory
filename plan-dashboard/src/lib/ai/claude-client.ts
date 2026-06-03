/**
 * Server-only Claude (Anthropic) client.
 *
 * Reads `anthropic-api-key` from the macOS keychain on first call and caches the
 * key in process memory. NEVER imported from a browser bundle — only from
 * /src/pages/api/* endpoints. Mirrors lib/reader/gemini-server.ts.
 *
 * Used for the nuanced editorial tasks where Claude's instruction-following and
 * semantic judgment beat Gemini Flash: paragraph auto-tagging, complex instruct
 * edits, and the Finalize handoff brief. Fast/cheap tasks stay on Gemini.
 */
import Anthropic from '@anthropic-ai/sdk';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const exec = promisify(execFile);

const MODEL = 'claude-sonnet-4-6';

let cachedKey: string | null = null;
let keyPromise: Promise<string> | null = null;
let cachedClient: Anthropic | null = null;

async function getAnthropicKey(): Promise<string> {
  if (cachedKey) return cachedKey;
  if (process.env.ANTHROPIC_API_KEY) {
    cachedKey = process.env.ANTHROPIC_API_KEY;
    return cachedKey;
  }
  if (!keyPromise) {
    keyPromise = (async () => {
      try {
        // Keychain service name is `anthropic-api-key` (no -a account scope).
        const { stdout } = await exec('security',
          ['find-generic-password', '-s', 'anthropic-api-key', '-w']);
        const key = stdout.trim();
        if (!key) throw new Error('empty key from keychain');
        cachedKey = key;
        return key;
      } catch (e) {
        keyPromise = null;
        throw new Error(`Could not read anthropic-api-key from keychain: ${(e as Error).message}`);
      }
    })();
  }
  return keyPromise;
}

async function getClient(): Promise<Anthropic> {
  if (cachedClient) return cachedClient;
  const apiKey = await getAnthropicKey();
  cachedClient = new Anthropic({ apiKey });
  return cachedClient;
}

export interface ClaudeOptions {
  system?: string;
  maxTokens?: number;
  temperature?: number;
}

/**
 * Single-shot completion. Returns the concatenated text of all text blocks.
 * Throws on API error — callers convert to apiServerError.
 */
export async function claudeComplete(prompt: string, opts: ClaudeOptions = {}): Promise<string> {
  const client = await getClient();
  const msg = await client.messages.create({
    model: MODEL,
    max_tokens: opts.maxTokens ?? 1024,
    temperature: opts.temperature ?? 0.2,
    ...(opts.system ? { system: opts.system } : {}),
    messages: [{ role: 'user', content: prompt }],
  });
  return msg.content
    .filter((b): b is Anthropic.TextBlock => b.type === 'text')
    .map((b) => b.text)
    .join('')
    .trim();
}

export { MODEL as CLAUDE_MODEL };
