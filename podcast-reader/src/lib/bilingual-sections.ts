/**
 * Split a KAHSKOLE raw-extract.md into per-topic sections for the bilingual
 * dual-panel view. Each section gets paired with its R2 English title (when
 * available) and rendered into HTML for both panels.
 *
 * Source layout in raw-extract.md:
 *   # <chapter name in Urdu>
 *   *Source: KASHKOLE, …*
 *
 *   <!-- section 1 (id=42, raw_sort=1): الاہیت اور خلقت کا فرق -->
 *   ...content...
 *
 *   <!-- section 2 (id=1070, …): ... -->
 *   ...content...
 *
 * Section header content (Urdu) survives into the panel; the topic_id from
 * the comment is used to look up the English retitle in R2 decisions.
 */
import { renderSourceMarkdown } from './source-render';
import { getTopicEnglish } from './decisions';

const SECTION_RE = /<!--\s*section\s+(\d+)\s+\(id=(\d+),\s*raw_sort=(\d+)\):\s*(.*?)\s*-->/g;

export interface BilingualSection {
  position: number;
  topicId: number;
  rawSort: number;
  urduLabel: string;
  englishTitle?: string;
  englishConfidence?: 'high' | 'medium' | 'low';
  bodyMarkdown: string;
  bodyHtml: string;
  /** Rendered HTML from the English translation file (null = translation pending). */
  englishBodyHtml: string | null;
  /** True if the English body came from adapted-extract.en.md (polished Phase 2). */
  englishIsAdapted: boolean;
}

export interface BilingualChapter {
  chapterHeader: string;          // First line of raw-extract (title + meta)
  preludeMarkdown: string;        // Anything before the first section marker
  preludeHtml: string;
  sections: BilingualSection[];
}

/** Parse section markers out of any markdown string, returning a map of topicId → body text. */
function extractSectionBodies(markdown: string): Map<number, string> {
  const map = new Map<number, string>();
  const matches: Array<{ idx: number; topicId: number; matchLen: number }> = [];
  let m: RegExpExecArray | null;
  const re = new RegExp(SECTION_RE.source, 'gm');
  while ((m = re.exec(markdown)) !== null) {
    matches.push({
      idx: m.index,
      topicId: parseInt(m[2], 10),
      matchLen: m[0].length,
    });
  }
  for (let i = 0; i < matches.length; i++) {
    const start = matches[i].idx + matches[i].matchLen;
    const end = i + 1 < matches.length ? matches[i + 1].idx : markdown.length;
    const body = markdown.slice(start, end).trim();
    map.set(matches[i].topicId, body);
  }
  return map;
}

export async function parseBilingual(
  binderId: number,
  chapterId: number,
  rawMarkdown: string,
  englishMarkdown?: string | null,
  englishIsAdapted?: boolean,
): Promise<BilingualChapter> {
  const matches: Array<{ idx: number; position: number; topicId: number; rawSort: number; label: string; matchLen: number }> = [];
  let m: RegExpExecArray | null;
  const re = new RegExp(SECTION_RE.source, 'gm');
  while ((m = re.exec(rawMarkdown)) !== null) {
    matches.push({
      idx: m.index,
      position: parseInt(m[1], 10),
      topicId: parseInt(m[2], 10),
      rawSort: parseInt(m[3], 10),
      label: m[4].trim(),
      matchLen: m[0].length,
    });
  }

  let chapterHeader = '';
  let preludeMarkdown = '';
  if (matches.length > 0) {
    preludeMarkdown = rawMarkdown.slice(0, matches[0].idx);
  } else {
    preludeMarkdown = rawMarkdown;
  }
  const headerMatch = preludeMarkdown.match(/^#\s+(.+?)$/m);
  if (headerMatch) chapterHeader = headerMatch[1].trim();

  const preludeHtml = renderSourceMarkdown(preludeMarkdown);

  // Pre-parse English bodies by topicId for fast lookup
  const enBodies = englishMarkdown ? extractSectionBodies(englishMarkdown) : new Map<number, string>();

  const sections: BilingualSection[] = [];
  for (let i = 0; i < matches.length; i++) {
    const start = matches[i].idx + matches[i].matchLen;
    const end = i + 1 < matches.length ? matches[i + 1].idx : rawMarkdown.length;
    const body = rawMarkdown.slice(start, end).trim();

    const enRetitle = await getTopicEnglish(binderId, chapterId, matches[i].topicId);

    const enBodyText = enBodies.get(matches[i].topicId) ?? null;
    const englishBodyHtml = enBodyText !== null ? renderSourceMarkdown(enBodyText) : null;

    sections.push({
      position: matches[i].position,
      topicId: matches[i].topicId,
      rawSort: matches[i].rawSort,
      urduLabel: matches[i].label,
      englishTitle: enRetitle?.en_title,
      englishConfidence: enRetitle?.confidence,
      bodyMarkdown: body,
      bodyHtml: renderSourceMarkdown(body),
      englishBodyHtml,
      englishIsAdapted: englishIsAdapted ?? false,
    });
  }

  return { chapterHeader, preludeMarkdown, preludeHtml, sections };
}
