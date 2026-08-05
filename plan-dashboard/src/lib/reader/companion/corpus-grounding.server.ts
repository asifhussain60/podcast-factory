/**
 * corpus-grounding.server.ts — what the knowledge base already knows about the
 * sentence you selected.
 *
 * SERVER ONLY (better-sqlite3). The Scholar's explanation is otherwise the model's
 * own recall; this hands it the book's own corpus first — the doctrine atoms,
 * quotations, hadith and etymologies extracted from the library — so a card is
 * grounded in material that was verified once rather than recalled fresh.
 *
 * Deliberately modest, because the corpus is modest (430 atoms). Salient terms are
 * pulled out of the passage, each is matched against atom bodies, and atoms are
 * ranked by how many DISTINCT terms they hit. An atom matching one common word is
 * not evidence of anything, so the floor is two — and when nothing clears it,
 * nothing is injected and the card is exactly what it would have been. A grounding
 * step that always finds something is a grounding step that finds nothing.
 *
 * Mirrors api/studio/corpus-search.ts's database handle; that route stays as it is
 * (doctrine-only, for the Key Focus palette) — this one spans every atom type.
 */
import Database from "better-sqlite3";
import { join } from "node:path";

const DB_PATH = join(
  new URL("../../../../../content/knowledge-base/knowledge.db", import.meta.url)
    .pathname,
);

/** Terms carried by almost any English sentence — matching on them proves nothing. */
const STOPWORDS = new Set([
  "about",
  "after",
  "against",
  "among",
  "because",
  "before",
  "between",
  "could",
  "every",
  "first",
  "have",
  "himself",
  "into",
  "itself",
  "might",
  "other",
  "should",
  "since",
  "their",
  "there",
  "these",
  "thing",
  "things",
  "those",
  "through",
  "under",
  "until",
  "where",
  "which",
  "while",
  "whose",
  "would",
  "said",
  "says",
  "come",
  "comes",
  "came",
  "make",
  "makes",
  "made",
  "know",
  "knows",
  "knew",
  "been",
  "being",
  "that",
  "this",
  "with",
  "from",
  "they",
  "them",
  "then",
  "than",
  "when",
  "what",
  "your",
  "yours",
  "ours",
  "shall",
]);

export interface CorpusAtom {
  id: string;
  type: string;
  body: string;
  /** How many distinct passage terms this atom matched. */
  hits: number;
}

const MAX_TERMS = 8;
const MIN_HITS = 2;
const BODY_CHARS = 600;

/**
 * The passage's salient terms: long-enough Latin words that are not stopwords,
 * plus every Arabic run (an Arabic term in the passage is the single strongest
 * signal there is, so it is never filtered).
 */
export function salientTerms(passage: string): string[] {
  const arabic = (passage.match(/[؀-ۿݐ-ݿ]{3,}/g) ?? []).map((t) => t.trim());
  const latin = (passage.toLowerCase().match(/[a-z]{5,}/g) ?? []).filter(
    (w) => !STOPWORDS.has(w),
  );
  // Longest first: a rarer word is a better probe than a common one, and only
  // the first MAX_TERMS are queried.
  const unique = [...new Set([...arabic, ...latin])].sort(
    (a, b) => b.length - a.length,
  );
  return unique.slice(0, MAX_TERMS);
}

/**
 * Atoms worth showing the model for this passage, best first.
 *
 * Never throws: a missing or unreadable knowledge base means no grounding, which
 * is a weaker card — not a failed explanation.
 */
export function groundingFor(passage: string, limit = 4): CorpusAtom[] {
  const terms = salientTerms(passage);
  if (terms.length < MIN_HITS) return [];

  let db: Database.Database | null = null;
  try {
    db = new Database(DB_PATH, { readonly: true, fileMustExist: true });
    const stmt = db.prepare(
      `SELECT id, type, substr(body, 1, ?) AS body
         FROM atoms
        WHERE body LIKE '%' || ? || '%'
        ORDER BY confidence DESC
        LIMIT 25`,
    );
    const tally = new Map<string, CorpusAtom>();
    for (const term of terms) {
      const rows = stmt.all(BODY_CHARS, term) as Omit<CorpusAtom, "hits">[];
      for (const row of rows) {
        const seen = tally.get(row.id);
        if (seen) seen.hits += 1;
        else tally.set(row.id, { ...row, hits: 1 });
      }
    }
    return [...tally.values()]
      .filter((a) => a.hits >= MIN_HITS)
      .sort((a, b) => b.hits - a.hits)
      .slice(0, limit);
  } catch {
    return [];
  } finally {
    db?.close();
  }
}

/**
 * The atoms as a block for the model's user turn.
 *
 * The instruction is the important half: this is material to draw on, not text to
 * paraphrase into the explanation, and a quotation is copied exactly or left out.
 * Without that line a grounded card reads like the corpus and cites nothing.
 */
export function groundingBlock(atoms: CorpusAtom[]): string {
  if (!atoms.length) return "";
  const items = atoms
    .map(
      (a, i) => `${i + 1}. [${a.type}] ${a.body.replace(/\s+/g, " ").trim()}`,
    )
    .join("\n");
  return [
    "Material from this library's own knowledge base that bears on the passage.",
    "Draw on it where it genuinely helps; ignore what does not fit. Quote any of it",
    "exactly or not at all, and never invent a source, a verse number or a root.",
    "",
    items,
  ].join("\n");
}
