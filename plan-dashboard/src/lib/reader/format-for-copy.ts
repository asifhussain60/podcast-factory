/**
 * Formatters for the copy-to-clipboard buttons on the chapter viewer.
 *
 * Trimmed from podcast-reader to the chapter formatter only — the episode
 * contract formatter is not used by the library viewer (yet). Add it back
 * when the episode view lands and the contract-parser is ported.
 */

export function formatChapterForCopy(source: string, title: string): string {
  // Chapter .txt files are already markdown. If the source doesn't start
  // with a heading, prepend the chapter title so the copied content has
  // proper structure wherever it lands.
  const trimmed = source.trim();
  if (trimmed.startsWith('#')) return trimmed + '\n';
  return `# ${title}\n\n${trimmed}\n`;
}
