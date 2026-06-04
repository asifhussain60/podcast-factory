/**
 * POST /api/ai/research
 *
 * Body: {
 *   paragraphText: string   — the paragraph being annotated
 *   instruction:   string   — what Asif wants to know or do
 *   bookTitle?:    string   — for context
 *   actionType?:   string   — 'research' | 'improve' | 'crossref' | 'note' | 'flag'
 * }
 *
 * Returns: { prompt: string, sources: string[] }
 *   prompt — a formatted, clipboard-ready prompt for VS Code Copilot / Claude Code
 *   sources — web sources Gemini cited (may be empty)
 *
 * Uses Gemini 2.0 Flash with Google Search grounding (Phase 1: returns prompt
 * text for clipboard; Phase 2 will wire direct pipeline actions).
 */

import type { APIRoute } from 'astro';
import { generateWithGrounding } from '../../../lib/reader/gemini-server';

export const prerender = false;

const ACTION_INTROS: Record<string, string> = {
  research:  'Research the following passage from the book and return a structured summary with web-sourced context:',
  improve:   'Suggest improvements for the following passage, citing modern scholarship where applicable:',
  crossref:  'Find cross-references, parallel passages, and related concepts for the following text:',
  note:      'Expand on the following passage with additional scholarly detail and context:',
  flag:      'Identify potential issues, inaccuracies, or points needing human review in the following passage:',
};

export const POST: APIRoute = async ({ request }) => {
  let body: { paragraphText: string; instruction: string; bookTitle?: string; actionType?: string };
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid JSON' }), {
      status: 400, headers: { 'content-type': 'application/json' },
    });
  }

  const { paragraphText, instruction, bookTitle, actionType = 'research' } = body;
  if (!paragraphText || !instruction) {
    return new Response(JSON.stringify({ error: 'paragraphText and instruction are required' }), {
      status: 400, headers: { 'content-type': 'application/json' },
    });
  }

  const intro = ACTION_INTROS[actionType] ?? ACTION_INTROS.research;
  const contextLine = bookTitle ? `Book context: "${bookTitle}"\n\n` : '';

  const geminiPrompt = `${intro}

${contextLine}Passage:
"${paragraphText}"

User instruction: ${instruction}

Please research this using current web sources and provide:
1. A concise answer / analysis (3–5 paragraphs)
2. Any directly relevant scholarly sources or citations
3. A ready-to-use prompt the editor could paste into an AI coding assistant to act on this paragraph

Format the final section as:
--- VS Code prompt ---
[prompt text here]
--- end prompt ---`;

  try {
    const { text, sources } = await generateWithGrounding(geminiPrompt);

    // Extract the VS Code prompt block if present, otherwise use the full response
    const promptMatch = text.match(/---\s*VS Code prompt\s*---\n([\s\S]*?)\n---\s*end prompt\s*---/i);
    const prompt = promptMatch
      ? promptMatch[1].trim()
      : `${instruction}\n\n---\nContext from "${bookTitle ?? 'this book'}":\n${paragraphText}`;

    return new Response(JSON.stringify({ prompt, sources, fullText: text }), {
      headers: { 'content-type': 'application/json' },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500, headers: { 'content-type': 'application/json' },
    });
  }
};
