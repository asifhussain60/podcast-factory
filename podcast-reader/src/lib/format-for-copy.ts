/**
 * Formatters for the copy-to-clipboard buttons on episode and chapter pages.
 *
 * Episode formatter renders the parsed contract as structured markdown
 * (title, audience, key tensions, tone constraints, anchor passages as
 * block-quotes, show notes). Chapter formatter returns the .txt source
 * as-is since chapter files are already markdown-flavoured prose.
 */

import type { ChapterContract } from './contract-parser';

export function formatContractForCopy(contract: ChapterContract): string {
  const lines: string[] = [];

  const epLabel = contract.episodeNumber !== null ? `Episode ${contract.episodeNumber}` : 'Episode';
  lines.push(`# ${epLabel}: ${contract.title}`);
  lines.push('');

  // Metadata line
  const metaParts: string[] = [];
  if (contract.angle) metaParts.push(`*Angle: ${contract.angle}*`);
  if (contract.episodeFormat) metaParts.push(`*Format: ${contract.episodeFormat}*`);
  if (contract.hostDynamic) metaParts.push(`*Hosts: ${contract.hostDynamic}*`);
  if (contract.lengthTarget) metaParts.push(`*Length: ${contract.lengthTarget}*`);
  if (contract.adaptationMode) metaParts.push(`*Adaptation: ${contract.adaptationMode}*`);
  if (contract.sourceChapterRef) metaParts.push(`*Source ch.: ${contract.sourceChapterRef}*`);
  if (metaParts.length > 0) {
    lines.push(metaParts.join(' · '));
    lines.push('');
  }

  if (contract.audience) {
    lines.push('## Audience & Framing');
    lines.push('');
    lines.push(contract.audience.trim());
    lines.push('');
  }

  if (contract.keyTensions.length > 0) {
    lines.push(`## Key Tensions (${contract.keyTensions.length})`);
    lines.push('');
    contract.keyTensions.forEach((t, i) => {
      lines.push(`### ${i + 1}.`);
      lines.push('');
      lines.push(t.trim());
      lines.push('');
    });
  }

  if (contract.toneConstraints.length > 0) {
    lines.push('## Tone Constraints');
    lines.push('');
    contract.toneConstraints.forEach((t) => {
      lines.push(`- ${t.trim().replace(/\n+/g, ' ')}`);
    });
    lines.push('');
  }

  if (contract.anchorPassages.length > 0) {
    lines.push(`## Anchor Passages (${contract.anchorPassages.length})`);
    lines.push('');
    contract.anchorPassages.forEach((p) => {
      // Render each passage as a markdown block-quote
      const blockQuoted = p.text.trim().split('\n').map((ln) => `> ${ln}`).join('\n');
      lines.push(blockQuoted);
      if (p.cite) lines.push(`> *— ${p.cite}*`);
      lines.push('');
    });
  }

  if (contract.showNotes?.blurb || (contract.showNotes?.bullets && contract.showNotes.bullets.length > 0)) {
    lines.push('## Show Notes');
    lines.push('');
    if (contract.showNotes.blurb) {
      lines.push(contract.showNotes.blurb.trim());
      lines.push('');
    }
    if (contract.showNotes.bullets && contract.showNotes.bullets.length > 0) {
      contract.showNotes.bullets.forEach((b) => lines.push(`- ${b.trim()}`));
      lines.push('');
    }
  }

  return lines.join('\n').replace(/\n{3,}/g, '\n\n').trim() + '\n';
}

export function formatChapterForCopy(source: string, title: string): string {
  // Chapter .txt files are already markdown. If the source doesn't start
  // with a heading, prepend the chapter title so the copied content has
  // proper structure wherever it lands.
  const trimmed = source.trim();
  if (trimmed.startsWith('#')) return trimmed + '\n';
  return `# ${title}\n\n${trimmed}\n`;
}
