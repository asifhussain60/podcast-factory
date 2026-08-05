/** Errors this package throws. All extend ProseEditorError so a host can catch
 *  the package's failures without catching everything. */

export class ProseEditorError extends Error {
  constructor(message: string) {
    super(message);
    this.name = new.target.name;
  }
}

/**
 * Thrown at attach/mount when the editor's schema contains a node or mark that
 * the serializer has no rule for.
 *
 * This is the package's central guarantee made operational. Without it, an
 * unserializable type is not an error at all — it is a value that silently
 * becomes nothing the next time the document is saved, discovered later as
 * missing text in the file the editor writes. Failing at startup converts an
 * invisible data-loss bug into a loud, immediate, fixable one.
 */
export class SerializerCoverageError extends ProseEditorError {
  readonly missingNodes: readonly string[];
  readonly missingMarks: readonly string[];

  constructor(
    missingNodes: readonly string[],
    missingMarks: readonly string[],
  ) {
    const parts: string[] = [];
    if (missingNodes.length) parts.push(`nodes: ${missingNodes.join(", ")}`);
    if (missingMarks.length) parts.push(`marks: ${missingMarks.join(", ")}`);
    super(
      `The editor schema contains types the serializer cannot write, so anything ` +
        `typed with them would be lost on save (${parts.join("; ")}). ` +
        `Either give each a serializer rule, or remove it from the schema.`,
    );
    this.missingNodes = missingNodes;
    this.missingMarks = missingMarks;
  }
}

/** Thrown when two commands claim the same keyboard shortcut. Silent last-wins
 *  binding is how a shortcut ends up doing something other than its tooltip. */
export class ShortcutConflictError extends ProseEditorError {
  constructor(shortcut: string, existingId: string, incomingId: string) {
    super(
      `Shortcut "${shortcut}" is already bound to "${existingId}"; ` +
        `"${incomingId}" cannot claim it too.`,
    );
  }
}

/** Thrown when two registered extensions or commands share an id. */
export class DuplicateRegistrationError extends ProseEditorError {
  constructor(kind: string, name: string) {
    super(`A ${kind} named "${name}" is already registered.`);
  }
}
