/**
 * Split a KAHSKOLE raw-extract.md into per-topic sections for the bilingual
 * dual-panel view. Each section gets paired with its R2 English title (when
 * available) and rendered into HTML for both panels.
 *
 * Source layout in raw-extract.md:
 *   # <chapter name in Urdu>
 *   *Source: WISDOM, …*
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
}

export interface BilingualChapter {
  chapterHeader: string;          // First line of raw-extract (title + meta)
  preludeMarkdown: string;        // Anything before the first section marker
  preludeHtml: string;
  sections: BilingualSection[];
}

export async function parseBilingual(
  binderId: number,
  chapterId: number,
  rawMarkdown: string,
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

  const sections: BilingualSection[] = [];
  for (let i = 0; i < matches.length; i++) {
    const start = matches[i].idx + matches[i].matchLen;
    const end = i + 1 < matches.length ? matches[i + 1].idx : rawMarkdown.length;
    const body = rawMarkdown.slice(start, end).trim();

    const enRetitle = await getTopicEnglish(binderId, chapterId, matches[i].topicId);

    sections.push({
      position: matches[i].position,
      topicId: matches[i].topicId,
      rawSort: matches[i].rawSort,
      urduLabel: matches[i].label,
      englishTitle: enRetitle?.en_title,
      englishConfidence: enRetitle?.confidence,
      bodyMarkdown: body,
      bodyHtml: renderSourceMarkdown(body),
    });
  }

  return { chapterHeader, preludeMarkdown, preludeHtml, sections };
}
