/**
 * The package's central guarantee, under test.
 *
 * A schema type with no serializer rule must be a LOUD failure. The alternative
 * — which is what every editor that dispatches on node type with a silent
 * fallback does — is that the type contributes nothing to the saved file, and
 * the loss is discovered later as missing text nobody can account for.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import "./_dom.ts";

import { getSchema } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { assertSerializerTotal } from "../src/serialize/coverage.ts";
import { createMarkdownSerializer } from "../src/serialize/markdown.ts";
import { SerializerCoverageError } from "../src/errors.ts";
import { baseExtensions } from "../src/schema/base-extensions.ts";

test("the base schema is fully covered by the markdown serializer", () => {
  const schema = getSchema(baseExtensions());
  const serializer = createMarkdownSerializer();
  assert.doesNotThrow(() => assertSerializerTotal(schema, serializer.covers));
});

test("an unconfigured StarterKit is REFUSED, naming what it would lose", () => {
  // Underline and hardBreak have no markdown spelling. Unconfigured StarterKit
  // ships both, so a host that reached for the obvious default would have had
  // Mod-U and Shift+Enter discarding silently on every save.
  const schema = getSchema([StarterKit]);
  const serializer = createMarkdownSerializer();

  let err: SerializerCoverageError | null = null;
  try {
    assertSerializerTotal(schema, serializer.covers);
  } catch (e) {
    err = e as SerializerCoverageError;
  }

  assert.ok(err instanceof SerializerCoverageError, "must refuse the schema");
  assert.ok(err.missingNodes.includes("hardBreak"));
  assert.ok(err.missingMarks.includes("underline"));
  // The message must name the types — an error that says only "something is
  // uncovered" leaves the reader to bisect the schema by hand.
  assert.match(err.message, /hardBreak/);
  assert.match(err.message, /underline/);
});

test("opting into hard breaks requires ALSO choosing how to write one", () => {
  const schema = getSchema(baseExtensions({ hardBreak: true }));

  // Admitting the node without a spelling is exactly the trap: refused.
  assert.throws(
    () => assertSerializerTotal(schema, createMarkdownSerializer().covers),
    SerializerCoverageError,
  );

  // Both together is fine.
  assert.doesNotThrow(() =>
    assertSerializerTotal(
      schema,
      createMarkdownSerializer({ hardBreak: "backslash" }).covers,
    ),
  );
});

test("the engine itself throws rather than emitting nothing for an unknown type", () => {
  // Belt and braces: even a serializer built without ever calling attach must
  // not be able to silently drop a node.
  const schema = getSchema([StarterKit]);
  const doc = schema.nodeFromJSON({
    type: "doc",
    content: [
      {
        type: "paragraph",
        content: [
          { type: "text", text: "one" },
          { type: "hardBreak" },
          { type: "text", text: "two" },
        ],
      },
    ],
  });
  assert.throws(
    () => createMarkdownSerializer().serialize(doc),
    SerializerCoverageError,
  );
});
