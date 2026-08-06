/**
 * gem-card.server.ts — what a Companion card IS, independent of who writes it.
 *
 * A card is made in three movements: everything before the model, the model, and
 * everything after it. Only the middle one differs between the two callers —
 * Gemini behind the Explain button, Claude behind the student-reader pass — so
 * the outer two live here and both callers use them.
 *
 *   prepareCard  grounding + the persona's system instruction + the user turn
 *   finishCard   the word cap, the Qur'anic citation resolution, the etymology veto
 *
 * SERVER ONLY (better-sqlite3, through the grounding and morphology modules).
 *
 * WHY THIS EXISTS (Asif, 2026-08-06). The student-reader lane stopped writing its
 * own prose and started handing its findings to the Ismaili Scholar — the same
 * Scholar the Explain button uses. Had the batch path composed those steps for
 * itself, "what an Explain produces" would have had two answers that agree only
 * as long as someone remembers to change both. It reaches this module through
 * `scripts/gem-card.mjs`, exactly as the Podcast Factory Library reaches the
 * site's renderer through `render-chapters.mjs`.
 *
 * There is no model call in this file, deliberately: it is the half that can be
 * tested without an API key.
 */
import { groundingFor, groundingBlock } from "./corpus-grounding.server";
import {
  morphologyGroundingBlock,
  vetoEtymologyItems,
} from "../../db/morphology.server";
import { capWords } from "./articulate-rules";
import { resolveQuranCitations } from "./quran-citation.server";
import {
  buildUserTurn,
  gemSystemInstruction,
  CONCEPT_LABEL,
  QUESTION_LABEL,
} from "../gems/engine";

/** The body budget. ~400 words is about half of what an ungoverned card ran to. */
export const DEFAULT_MAX_WORDS = 400;
/** Per etymology item, mirroring the persona's own "at most 60 words" rule. */
export const ETYMOLOGY_MAX_WORDS = 60;

export interface PreparedCard {
  /** The persona's system instruction, JSON envelope included. */
  system: string;
  /** The user turn: chapter, passage, and the ask. */
  user: string;
  /** Knowledge-base atoms that bore on the passage. Zero means the corpus had
   *  nothing — the caller decides what that is worth. */
  grounded: number;
  /** Whether any Arabic run in the passage resolved to a corpus root. */
  morphology: boolean;
}

/**
 * Everything the model needs, assembled in the order that matters.
 *
 * The corpus comes FIRST so the persona writes with it rather than being
 * corrected by it afterwards. Retrieval stays on the passage and its paragraph:
 * widening it to the whole chapter swamps the query and pulls atoms about
 * whatever else the chapter happens to mention. Morphology grounding is
 * unconditional — a local committed database, no spend — so any Arabic term that
 * resolves to one corpus root arrives with its verified root and Lane's meaning.
 */
export function prepareCard(opts: {
  gemId?: string;
  concept: string;
  context?: string;
  chapterContext?: string;
  bookTitle?: string;
  question?: string;
  ground?: boolean;
}): PreparedCard {
  const concept = opts.concept.trim();
  const question = (opts.question ?? "").trim();
  const retrievalText = `${concept} ${opts.context ?? ""}`;

  const atoms = opts.ground ? groundingFor(retrievalText) : [];
  const morphBlock = morphologyGroundingBlock(retrievalText);
  const grounded =
    atoms.length || morphBlock
      ? [
          opts.context ?? "",
          morphBlock,
          ...(atoms.length ? [groundingBlock(atoms)] : []),
        ]
          .filter(Boolean)
          .join("\n\n")
      : opts.context;

  return {
    system: gemSystemInstruction(opts.gemId),
    user: buildUserTurn({
      label: question ? QUESTION_LABEL : CONCEPT_LABEL,
      value: question || concept,
      bookTitle: opts.bookTitle,
      context: grounded,
      chapterContext: opts.chapterContext,
    }),
    grounded: atoms.length,
    morphology: Boolean(morphBlock),
  };
}

export interface FinishedCard {
  body: string;
  etymology: string[];
  etymologyVetoed: number;
}

/**
 * The line a researched card opens with (Asif, 2026-08-06).
 *
 * A card built from the open web must not look identical to one built from his
 * own corpora and the mushaf, and the difference has to be visible BEFORE the
 * first sentence rather than inferable from a source list at the bottom — this
 * is a religious text, and the weight a reader gives an explanation depends on
 * where it came from. The sources still go at the end, where a citation belongs.
 */
export const RESEARCH_NOTICE =
  "*Researched outside this library — the knowledge base carries nothing on this passage. Sources are listed at the end.*";

const SOURCES_HEADING = "**Sources consulted**";

/** Most sources listed under a card. Google returns as many chunks as it used —
 *  nine on the first passage tried — and a list that long stops being read.
 *  Order is preserved, so the cap keeps the ones the answer leant on most. */
const MAX_SOURCES = 6;

/**
 * Bound the card, name its verses, and drop any etymology the corpus contradicts.
 *
 * Order is load-bearing. Citations resolve AFTER the cap so the cap can never cut
 * a verse away from its rendering; the research notice and its sources are added
 * after BOTH, so they can never eat the body's word budget or be truncated away;
 * and the etymology veto is deterministic — an item whose claimed root
 * contradicts the morphology corpus is dropped, never rewritten, and
 * conservative by contract, since unknown and unparseable items always pass.
 */
export function finishCard(opts: {
  body: string;
  etymology?: string[];
  maxWords?: number;
  /** Present only on the researched path. An empty list is NOT the same as
   *  absent: it means a search ran and found nothing to stand on, which is a
   *  card that should not be filed at all (Asif, 2026-08-06). */
  researchSources?: string[];
}): FinishedCard {
  const budget =
    typeof opts.maxWords === "number" && opts.maxWords > 50
      ? Math.min(opts.maxWords, 2000)
      : DEFAULT_MAX_WORDS;
  const vetoed = vetoEtymologyItems(opts.etymology ?? []);

  let body = resolveQuranCitations(capWords(opts.body, budget));
  if (opts.researchSources?.length) {
    // Deduped on the whole entry, which is `[title](uri)` — the same site can
    // be returned several times under different redirect URIs, and listing it
    // twice makes a card look better-sourced than it is.
    const seen = new Set<string>();
    const list = opts.researchSources
      .filter((s) => !seen.has(s) && seen.add(s))
      .slice(0, MAX_SOURCES)
      .map((s) => `- ${s}`)
      .join("\n");
    body = `${RESEARCH_NOTICE}\n\n${body}\n\n${SOURCES_HEADING}\n\n${list}`;
  }

  return {
    body,
    etymology: vetoed.kept.map((e) => capWords(e, ETYMOLOGY_MAX_WORDS)),
    etymologyVetoed: vetoed.dropped.length,
  };
}
