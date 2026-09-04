/**
 * compose-reading-assistant.ts — the Book Composer's reading-assistant marks.
 *
 * Moved verbatim out of ./book-composer.ts on 2026-09-04 (frontend size
 * ratchet). Behaviour is unchanged: these are the same functions, in the same
 * order, with nothing but `export` added to the four the Composer calls.
 *
 * Two renderers, deliberately, because the two surfaces cannot share one. The
 * READ view is ordinary DOM, so a sentence can be wrapped in a span; the EDIT
 * view is a ProseMirror document, where inserting elements would change the
 * doc, so the same scoring paints through the CSS Custom Highlight API instead.
 */

const READING_ASSISTANT_SENTENCE_CLASS = "cx-reading-assistant-sentence";
const READING_ASSISTANT_FOCUS_CLASS = "cx-reading-assistant-sentence--focus";
const READING_ASSISTANT_EDITOR_HIGHLIGHT = "cx-reading-assistant-focus";

type ReadingHighlightRegistry = {
  delete(name: string): void;
  set(name: string, highlight: object): void;
};

function readingHighlightRegistry(): ReadingHighlightRegistry | null {
  return (
    (CSS as typeof CSS & { highlights?: ReadingHighlightRegistry })
      .highlights ?? null
  );
}

export function clearEditorReadingAssistant(): void {
  readingHighlightRegistry()?.delete(READING_ASSISTANT_EDITOR_HIGHLIGHT);
}

function splitReadingAssistantSentences(text: string): string[] {
  return (
    text.match(
      /[^.!?\u061f\u06d4]+(?:[.!?\u061f\u06d4]+["'\u2019\u201d)]*|$)\s*/gu,
    ) ?? [text]
  );
}

export function clearReadingAssistant(root: ParentNode): void {
  root
    .querySelectorAll<HTMLElement>(`.${READING_ASSISTANT_SENTENCE_CLASS}`)
    .forEach((sentence) => {
      sentence.replaceWith(...sentence.childNodes);
    });
}

function readingAssistantWordSet(text: string): Set<string> {
  const stopWords = new Set([
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "but",
    "by",
    "for",
    "from",
    "had",
    "has",
    "have",
    "he",
    "her",
    "his",
    "i",
    "in",
    "is",
    "it",
    "its",
    "not",
    "of",
    "on",
    "or",
    "our",
    "she",
    "that",
    "the",
    "their",
    "them",
    "there",
    "they",
    "this",
    "to",
    "was",
    "we",
    "were",
    "which",
    "who",
    "will",
    "with",
    "you",
    "your",
  ]);
  return new Set(
    (text.toLocaleLowerCase().match(/[\p{L}\p{N}]{3,}/gu) ?? []).filter(
      (word) => !stopWords.has(word),
    ),
  );
}

export function applyReadingAssistant(root: ParentNode): void {
  clearReadingAssistant(root);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent || !node.textContent?.trim()) return NodeFilter.FILTER_REJECT;
      if (
        parent.closest(
          "script, style, h1, h2, h3, h4, h5, h6, audio, video, button, .cx-note-hl",
        )
      ) {
        return NodeFilter.FILTER_REJECT;
      }
      return NodeFilter.FILTER_ACCEPT;
    },
  });
  const textNodes: Text[] = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode as Text);

  const sentences: HTMLElement[] = [];
  for (const textNode of textNodes) {
    const fragment = document.createDocumentFragment();
    for (const part of splitReadingAssistantSentences(textNode.data)) {
      if (!part.trim()) {
        fragment.append(part);
        continue;
      }
      const sentence = document.createElement("span");
      sentence.className = READING_ASSISTANT_SENTENCE_CLASS;
      sentence.textContent = part;
      sentences.push(sentence);
      fragment.append(sentence);
    }
    textNode.replaceWith(fragment);
  }

  const groups = new Map<Element, HTMLElement[]>();
  for (const sentence of sentences) {
    const block = sentence.closest("p, li, blockquote, figcaption, dd, dt");
    if (!block) continue;
    const group = groups.get(block) ?? [];
    group.push(sentence);
    groups.set(block, group);
  }

  for (const candidates of groups.values()) {
    const wordSets = candidates.map((candidate) =>
      readingAssistantWordSet(candidate.textContent ?? ""),
    );
    let bestIndex = 0;
    let bestScore = Number.NEGATIVE_INFINITY;
    candidates.forEach((candidate, index) => {
      let sharedWords = 0;
      for (const word of wordSets[index]) {
        for (
          let otherIndex = 0;
          otherIndex < wordSets.length;
          otherIndex += 1
        ) {
          if (otherIndex !== index && wordSets[otherIndex].has(word))
            sharedWords += 1;
        }
      }
      const textLength = (candidate.textContent ?? "").trim().length;
      const score =
        sharedWords * 4 +
        Math.min(wordSets[index].size, 18) +
        (index === 0 ? 3 : 0) -
        (textLength < 24 ? 8 : 0);
      if (score > bestScore) {
        bestScore = score;
        bestIndex = index;
      }
    });
    candidates[bestIndex]?.classList.add(READING_ASSISTANT_FOCUS_CLASS);
  }
}

export function applyEditorReadingAssistant(editor: HTMLElement): boolean {
  clearEditorReadingAssistant();
  const registry = readingHighlightRegistry();
  const HighlightConstructor = (
    globalThis as typeof globalThis & {
      Highlight?: new (...ranges: Range[]) => object;
    }
  ).Highlight;
  if (!registry || !HighlightConstructor) return false;

  const groups = new Map<Element, Array<{ range: Range; text: string }>>();
  const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent || !node.textContent?.trim()) return NodeFilter.FILTER_REJECT;
      if (parent.closest("script, style, button, [contenteditable='false']")) {
        return NodeFilter.FILTER_REJECT;
      }
      return parent.closest("p, li, blockquote, figcaption, dd, dt")
        ? NodeFilter.FILTER_ACCEPT
        : NodeFilter.FILTER_REJECT;
    },
  });

  const textNodes: Text[] = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode as Text);
  for (const textNode of textNodes) {
    const block = textNode.parentElement?.closest(
      "p, li, blockquote, figcaption, dd, dt",
    );
    if (!block) continue;
    let offset = 0;
    for (const part of splitReadingAssistantSentences(textNode.data)) {
      const leadingLength = part.match(/^\s*/u)?.[0].length ?? 0;
      const trailingLength = part.match(/\s*$/u)?.[0].length ?? 0;
      const start = offset + leadingLength;
      const end = offset + part.length - trailingLength;
      offset += part.length;
      if (end <= start) continue;
      const range = document.createRange();
      range.setStart(textNode, start);
      range.setEnd(textNode, end);
      const group = groups.get(block) ?? [];
      group.push({ range, text: textNode.data.slice(start, end) });
      groups.set(block, group);
    }
  }

  const focusRanges: Range[] = [];
  for (const candidates of groups.values()) {
    const wordSets = candidates.map((candidate) =>
      readingAssistantWordSet(candidate.text),
    );
    let bestIndex = 0;
    let bestScore = Number.NEGATIVE_INFINITY;
    candidates.forEach((candidate, index) => {
      let sharedWords = 0;
      for (const word of wordSets[index]) {
        for (
          let otherIndex = 0;
          otherIndex < wordSets.length;
          otherIndex += 1
        ) {
          if (otherIndex !== index && wordSets[otherIndex].has(word))
            sharedWords += 1;
        }
      }
      const score =
        sharedWords * 4 +
        Math.min(wordSets[index].size, 18) +
        (index === 0 ? 3 : 0) -
        (candidate.text.length < 24 ? 8 : 0);
      if (score > bestScore) {
        bestScore = score;
        bestIndex = index;
      }
    });
    if (candidates[bestIndex]) focusRanges.push(candidates[bestIndex].range);
  }

  if (focusRanges.length === 0) return false;
  registry.set(
    READING_ASSISTANT_EDITOR_HIGHLIGHT,
    new HighlightConstructor(...focusRanges),
  );
  return true;
}
