/**
 * The serializer's public vocabulary.
 *
 * A serializer here is a total function from a ProseMirror document to a string
 * in the host's output format. "Total" is the operative word and the reason
 * these types exist: the failure this package is built to prevent is a node type
 * that no rule handles, quietly contributing nothing to the saved file.
 */
import type { Mark as PMMark, Node as PMNode } from "@tiptap/pm/model";

export type AttrMap = Record<string, unknown>;

/** What a node rule is handed. Everything it could need to decide its own
 *  output, so a rule never has to reach back into the document itself. */
export interface NodeSerializeContext {
  readonly node: PMNode;
  readonly attrs: AttrMap;
  /** null at the top level. */
  readonly parent: PMNode | null;
  /** This node's index among its parent's children. */
  readonly index: number;
  readonly isFirstChild: boolean;
  readonly isLastChild: boolean;
  /** Serialized children, joined by the format's block separator. */
  children(): string;
  /** Serialized children as separate strings — for a rule that must interleave
   *  something between blocks (a blank quote marker, a list bullet). */
  childBlocks(): string[];
  /** Inline content with marks applied. Leaf-level; does not recurse blocks. */
  inline(): string;
  /** Plain text, no marks and no syntax. */
  text(): string;
  /** Prefix every line: `first` on the first, `rest` (defaults to `first`) after.
   *  The blockquote/list idiom, written once rather than in each rule. */
  prefixLines(value: string, first: string, rest?: string): string;
}

export type NodeSerializerRule = (ctx: NodeSerializeContext) => string;

export interface MarkSerializeContext {
  readonly mark: PMMark;
  readonly attrs: AttrMap;
  /** The already-serialized text this mark wraps. */
  readonly inner: string;
}

export type MarkSerializerRule = (ctx: MarkSerializeContext) => string;

export interface SerializerRules {
  nodes: Readonly<Record<string, NodeSerializerRule>>;
  marks: Readonly<Record<string, MarkSerializerRule>>;
  /**
   * Order marks are applied in, innermost first. Without a declared order the
   * output depends on the order ProseMirror happens to store marks in, which is
   * stable in practice and unspecified in principle — and an unstable
   * serializer turns every save into a spurious diff.
   */
  markOrder?: readonly string[];
  /** Separator between top-level blocks. Defaults to a blank line. */
  blockSeparator?: string;
}

/** A serializer, plus the schema type names it can write. `covers` is what the
 *  coverage assertion checks against, so it must be honest — an over-claimed
 *  name defeats the whole guarantee. */
export interface Serializer {
  serialize(doc: PMNode): string;
  readonly covers: readonly string[];
}

/**
 * How the host tells the package to serialize.
 *
 * `custom` exists so a host that ALREADY has a proven serializer can adopt this
 * package without restaking its output contract on new code — it hands over the
 * function it already trusts, and declares what that function covers so the
 * assertion still runs. `markdown` is the built-in for greenfield hosts.
 */
export type SerializerSpec =
  | {
      kind: "custom";
      serialize(doc: PMNode): string;
      /** Every node and mark name the function above handles. */
      covers: readonly string[];
    }
  | {
      kind: "markdown";
      rules?: Partial<SerializerRules>;
      options?: MarkdownOptions;
    };

export interface MarkdownOptions {
  /** Bullet marker for unordered lists. Default "-". */
  bullet?: "-" | "*" | "+";
  /** Emphasis delimiter. Default "*". */
  emphasis?: "*" | "_";
  /** Strong delimiter. Default "**". */
  strong?: "**" | "__";
  /** Fence for code blocks. Default "```". */
  codeFence?: "```" | "~~~";
  /** Emit the code block's language after the fence. Default true. */
  fenceLanguage?: boolean;
  /**
   * How to write a hard break. Default "error" — deliberately.
   *
   * Inventing a representation the host's reader cannot parse back does not
   * save the break, it relocates the loss to the next read. A host that wants
   * hard breaks picks a spelling it has actually tested round-tripping.
   */
  hardBreak?: "backslash" | "twoSpaces" | "newline" | "error";
  /** Escape markdown punctuation in text. Default false: escaping REWRITES
   *  bytes in an existing corpus, which is itself a form of corruption. */
  escapeMarkdown?: boolean;
}
