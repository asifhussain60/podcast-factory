/**
 * coverage.ts — the startup gate.
 *
 * Walks the FINAL schema (base extensions + everything the host registered +
 * anything added through the raw-TipTap escape hatch) and refuses to run if any
 * type in it has no serializer rule.
 *
 * Running against the final schema rather than the declared extension list is
 * what makes the escape hatch safe: a host can drop in any TipTap extension it
 * likes, and if that extension widens the schema past what the serializer can
 * write, this still catches it.
 */
import type { Schema } from "@tiptap/pm/model";
import { SerializerCoverageError } from "../errors.ts";

/**
 * @throws SerializerCoverageError listing every uncovered node and mark.
 */
export function assertSerializerTotal(
  schema: Schema,
  covers: Iterable<string>,
): void {
  const covered = new Set(covers);

  const missingNodes = Object.keys(schema.nodes).filter((n) => !covered.has(n));
  const missingMarks = Object.keys(schema.marks).filter((m) => !covered.has(m));

  if (missingNodes.length || missingMarks.length) {
    throw new SerializerCoverageError(missingNodes, missingMarks);
  }
}
