/**
 * POST /api/ai/instruct
 *
 * Body: {
 *   instruction: string,                                    // free-form user instruction
 *   blocks: [{ id: string, tag: string, text: string }],    // chapter blocks with ids
 *   scope?: 'all'|'selection',                              // future-use
 *   bookContext?: string,
 *   chapterTitle?: string,
 * }
 *
 * Returns: {
 *   edits: [{ block_id: string, action: 'replace'|'delete'|'insert_after', new_text?: string, reason?: string }],
 *   note?: string,
 * }
 *
 * Gemini Pro. The model receives every block with its stable id and
 * returns surgical edits. The client applies them in order; each
 * affected block flashes briefly then settles into the edit-highlight
 * color so the reader sees what the AI did.
 */

import type { APIRoute } from 'astro';
import { generate, rateLimitCheck } from '../../../lib/reader/gemini-server';

export const prerender = false;

const SYSTEM = `You are an editor making surgical, minimal edits to a scholarly Ismaili text on behalf of a careful reader.

You will receive:
  - the reader's INSTRUCTION (what they want changed),
  - the chapter as a list of BLOCKS, each with a stable id like "p:where-this-chapter-picks-up#3".

Return ONLY a JSON object:
  {
    "edits": [
      { "block_id": "<id>", "action": "replace", "new_text": "<plain text>", "reason": "<≤12 word why>" },
      { "block_id": "<id>", "action": "delete", "reason": "..." },
      { "block_id": "<id>", "action": "insert_after", "new_text": "...", "reason": "..." }
    ],
    "note": "<one-line summary of what you changed>"
  }

Rules:
  - Make the SMALLEST set of edits that satisfies the instruction. Don't rewrite blocks you don't need to.
  - Preserve every transliterated Arabic term (Hujjah, Sayyidina, Da'i, etc.) and proper noun verbatim unless the instruction explicitly asks you to fix transliteration.
  - new_text is PLAIN TEXT — no markdown, no HTML, no quotes wrapping it. Each block is one paragraph or one heading.
  - If the instruction is ambiguous or no edit is needed, return { "edits": [], "note": "no change — <reason>" }.
  - Never invent block_ids. Only edit blocks that exist in the input.
  - If the instruction asks for additions, prefer insert_after on the most relevant existing block.`;

export const POST: APIRoute = async ({ request }) => {
  const limit = rateLimitCheck();
  if (!limit.ok) return new Response(JSON.stringify({ error: 'rate_limited' }), { status: 429 });
  try {
    const { instruction, blocks, bookContext, chapterTitle } = await request.json();
    if (!instruction || !Array.isArray(blocks) || blocks.length === 0) {
      return new Response(JSON.stringify({ error: 'missing instruction or blocks' }), { status: 400 });
    }

    const blockList = blocks.map((b: any) => `[${b.id}] (${b.tag}) ${String(b.text).replace(/\s+/g, ' ').slice(0, 800)}`).join('\n');
    const truncated = blockList.length > 80_000 ? blockList.slice(0, 80_000) + '\n[...truncated]' : blockList;
    const user = [
      bookContext ? `Book: ${bookContext}` : '',
      chapterTitle ? `Chapter: ${chapterTitle}` : '',
      'BLOCKS (one per line, format: [id] (tag) text):',
      truncated,
      '',
      `INSTRUCTION: ${instruction}`,
    ].filter(Boolean).join('\n');

    const raw = await generate({
      model: 'pro',
      systemInstruction: SYSTEM,
      contents: [{ role: 'user', parts: [{ text: user }] }],
      temperature: 0.3,
      maxOutputTokens: 4000,
      jsonMode: true,
    });

    let parsed: any = { edits: [] };
    try {
      parsed = JSON.parse(raw);
    } catch {
      parsed = { edits: [], note: 'Model returned unparseable response.' };
    }
    if (!Array.isArray(parsed.edits)) parsed.edits = [];

    return new Response(JSON.stringify(parsed), {
      status: 200,
      headers: { 'content-type': 'application/json', 'cache-control': 'no-store' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: (e as Error).message }), { status: 500 });
  }
};
