const SENTENCE_CLASS = "pf-reading-assistant-sentence";
const FOCUS_CLASS = "pf-reading-assistant-sentence--focus";

function splitIntoSentences(text: string): string[] {
  const out: string[] = [];
  let start = 0;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const boundary =
      ch === "." ||
      ch === "!" ||
      ch === "?" ||
      ch === "…" ||
      ch === "؟" ||
      ch === "\u06d4" ||
      ch === "\n" ||
      ch === "\r";
    if (!boundary) continue;

    let end = i + 1;
    while (end < text.length && /\s/.test(text[end])) end += 1;
    const segment = text.slice(start, end);
    if (segment.length > 0) out.push(segment);
    start = end;
    i = end - 1;
  }

  const tail = text.slice(start);
  if (tail.length > 0) out.push(tail);
  return out;
}

export function clearReadingAssistantSentences(body: HTMLElement): void {
  for (const sentence of Array.from(
    body.querySelectorAll<HTMLElement>(`.${SENTENCE_CLASS}`),
  )) {
    sentence.replaceWith(...sentence.childNodes);
  }
}

function sentenceSkipNode(node: Node): boolean {
  if (node.nodeType !== Node.TEXT_NODE) return true;
  const parent = node.parentElement;
  if (parent === null) return true;
  return (
    parent.closest(
      "mark.pf-hl, mark.pf-cp, mark.pf-found, .pf-read-aloud, .pf-mark, .pf-find",
    ) !== null
  );
}

export function applyReadingAssistantSentences(
  body: HTMLElement,
): HTMLElement[] {
  clearReadingAssistantSentences(body);
  const sentences: HTMLElement[] = [];
  const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      if (sentenceSkipNode(node)) return NodeFilter.FILTER_REJECT;
      return node.nodeValue?.trim()
        ? NodeFilter.FILTER_ACCEPT
        : NodeFilter.FILTER_REJECT;
    },
  });

  const nodes: Text[] = [];
  let node: Node | null;
  while ((node = walker.nextNode()) !== null) {
    if (node instanceof Text) nodes.push(node);
  }

  for (const textNode of nodes) {
    const segments = splitIntoSentences(textNode.nodeValue ?? "");
    if (segments.length === 0) continue;
    const wrapped = document.createDocumentFragment();
    for (const segment of segments) {
      if (!segment.trim()) {
        wrapped.appendChild(document.createTextNode(segment));
        continue;
      }
      const leading = segment.match(/^\s+/)?.[0] ?? "";
      const trailing = segment.slice(leading.length);
      if (leading) wrapped.appendChild(document.createTextNode(leading));
      if (!trailing.trim()) {
        wrapped.appendChild(document.createTextNode(trailing));
        continue;
      }
      const span = document.createElement("span");
      span.className = SENTENCE_CLASS;
      span.textContent = trailing;
      sentences.push(span);
      wrapped.appendChild(span);
    }
    textNode.replaceWith(wrapped);
  }
  return sentences;
}

function readingAssistantWords(text: string): Set<string> {
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

export function focusReadingAssistantSentences(
  body: HTMLElement,
  sentences: HTMLElement[],
): void {
  const groups = new Map<Element, HTMLElement[]>();
  for (const sentence of sentences) {
    const block = sentence.closest("p, li, blockquote, figcaption, dd, dt");
    if (!block || !body.contains(block)) continue;
    const group = groups.get(block) ?? [];
    group.push(sentence);
    groups.set(block, group);
  }

  for (const candidates of groups.values()) {
    const wordSets = candidates.map((candidate) =>
      readingAssistantWords(candidate.textContent ?? ""),
    );
    let bestIndex = 0;
    let bestScore = Number.NEGATIVE_INFINITY;
    candidates.forEach((candidate, index) => {
      let sharedWords = 0;
      for (const word of wordSets[index]) {
        for (let other = 0; other < wordSets.length; other += 1) {
          if (other !== index && wordSets[other].has(word)) sharedWords += 1;
        }
      }
      const length = (candidate.textContent ?? "").trim().length;
      const score =
        sharedWords * 4 +
        Math.min(wordSets[index].size, 18) +
        (index === 0 ? 3 : 0) -
        (length < 24 ? 8 : 0);
      if (score > bestScore) {
        bestScore = score;
        bestIndex = index;
      }
    });
    candidates[bestIndex]?.classList.add(FOCUS_CLASS);
  }
}
