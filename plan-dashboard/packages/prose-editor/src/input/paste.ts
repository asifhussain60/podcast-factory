/**
 * paste.ts — the paste sanitizer.
 *
 * The inverse of the technique it replaces. The previous editor's "HTML
 * cleaner" was 715 lines and 77 chained `.replace()` calls over a serialized
 * HTML string: a DENY-list, enumerating what to strip, protecting known-good
 * blocks by extracting them into placeholder comments and splicing them back.
 * Every paste shape nobody anticipated was a new bug, and every new domain block
 * needed another protection pattern added to a list already thirty entries long.
 *
 * This is an ALLOW-list over a parsed DOM: parse into a detached document, walk
 * it, keep only what the schema (plus what registered extensions declare) can
 * represent, discard the rest. A paste shape nobody anticipated is handled by
 * construction, because the question asked is "is this permitted" rather than
 * "have we seen this before".
 *
 * Inline `style` is never preserved and that is not configurable. It is the
 * single largest source of foreign formatting, and a host's stylesheet cannot
 * win against an inline declaration.
 */
import { Plugin, PluginKey } from "@tiptap/pm/state";
import type { PasteAllowance } from "../extend/define.ts";

export interface PasteOptions {
  /** "schema" (default) keeps only representable markup; "plain" strips to
   *  text; "off" leaves ProseMirror's own handling alone. */
  mode?: "schema" | "plain" | "off";
  /** Extra tags to keep beyond the defaults. */
  allowTags?: readonly string[];
  /** Attributes kept, per tag. `*` applies to every tag. */
  allowAttributes?: Readonly<Record<string, readonly string[]>>;
  /**
   * Class names kept. Everything else is dropped.
   *
   * This is the hook a host needs: a class that carries MEANING rather than
   * styling (marking a quotation as scripture, say) must survive a paste, or
   * copying a passage from one place to another silently degrades it.
   */
  allowClasses?: readonly string[] | ((className: string) => boolean);
  /** Per-extension allowances, so a registered node's parse rule has something
   *  to match. Collected from the extensions passed to attach/mount. */
  extensionAllowances?: readonly PasteAllowance[];
  /** Last-resort host hook on the cleaned fragment, before ProseMirror parses. */
  transform?: (root: HTMLElement) => void;
}

/** Markup the base schema can represent. Anything else is unwrapped (its text
 *  survives; its tag does not) or dropped outright. */
const DEFAULT_TAGS = [
  "p",
  "br",
  "strong",
  "b",
  "em",
  "i",
  "s",
  "strike",
  "del",
  "code",
  "pre",
  "a",
  "ul",
  "ol",
  "li",
  "blockquote",
  "hr",
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "span",
  "div",
];

/** Dropped WITH their content: their text is chrome, not prose. */
const DROP_ENTIRELY = new Set([
  "script",
  "style",
  "noscript",
  "template",
  "head",
  "meta",
  "link",
  "object",
  "embed",
  "iframe",
  "svg",
  "canvas",
  "form",
  "input",
  "select",
  "textarea",
  "button",
]);

const DEFAULT_ATTRS: Record<string, readonly string[]> = {
  a: ["href", "title"],
  ol: ["start"],
  li: ["value"],
  code: ["class"],
  pre: ["class"],
  "*": ["class", "dir", "lang"],
};

export const pasteSanitizerKey = new PluginKey("rte-paste-sanitizer");

export function sanitizeHtml(
  html: string,
  options: PasteOptions,
  doc: Document,
): string {
  const allowedTags = new Set([
    ...DEFAULT_TAGS,
    ...(options.allowTags ?? []),
    ...(options.extensionAllowances ?? []).flatMap((a) => a.tags),
  ]);

  const attrRules: Record<string, Set<string>> = {};
  const addAttrs = (tag: string, attrs: readonly string[]) => {
    attrRules[tag] ??= new Set();
    for (const a of attrs) attrRules[tag].add(a);
  };
  for (const [tag, attrs] of Object.entries(DEFAULT_ATTRS))
    addAttrs(tag, attrs);
  for (const [tag, attrs] of Object.entries(options.allowAttributes ?? {})) {
    addAttrs(tag, attrs);
  }
  for (const allowance of options.extensionAllowances ?? []) {
    for (const [tag, attrs] of Object.entries(allowance.attributes ?? {})) {
      addAttrs(tag, attrs);
    }
  }

  const extensionClasses = new Set(
    (options.extensionAllowances ?? []).flatMap((a) => a.classes ?? []),
  );
  const classAllowed = (name: string): boolean => {
    if (extensionClasses.has(name)) return true;
    const rule = options.allowClasses;
    if (!rule) return false;
    return typeof rule === "function" ? rule(name) : rule.includes(name);
  };

  const root = doc.createElement("div");
  root.innerHTML = html;

  const walk = (node: Element): void => {
    // Snapshot: the loop reparents and removes children as it goes.
    for (const child of Array.from(node.children)) walk(child);

    const tag = node.tagName.toLowerCase();

    if (DROP_ENTIRELY.has(tag)) {
      node.remove();
      return;
    }

    if (!allowedTags.has(tag)) {
      // Unwrap rather than delete: the TEXT was the point; the tag was not.
      node.replaceWith(...Array.from(node.childNodes));
      return;
    }

    for (const attr of Array.from(node.attributes)) {
      const name = attr.name.toLowerCase();
      // Never negotiable. Inline style is the largest source of foreign
      // formatting, and a host stylesheet cannot outrank it.
      if (name === "style") {
        node.removeAttribute(attr.name);
        continue;
      }
      // Any event handler, whatever its name.
      if (name.startsWith("on")) {
        node.removeAttribute(attr.name);
        continue;
      }
      const permitted =
        attrRules[tag]?.has(name) || attrRules["*"]?.has(name) || false;
      if (!permitted) {
        node.removeAttribute(attr.name);
        continue;
      }
      if (name === "class") {
        const kept = attr.value.split(/\s+/).filter(classAllowed);
        if (kept.length) node.setAttribute("class", kept.join(" "));
        else node.removeAttribute("class");
      }
      if (name === "href" && /^\s*javascript:/i.test(attr.value)) {
        node.removeAttribute(attr.name);
      }
    }
  };

  for (const child of Array.from(root.children)) walk(child);

  // Comments carry editor-specific bookkeeping from wherever this was copied.
  const removeComments = (node: globalThis.Node): void => {
    for (const child of Array.from(node.childNodes)) {
      if (child.nodeType === 8) child.parentNode?.removeChild(child);
      else removeComments(child);
    }
  };
  removeComments(root);

  options.transform?.(root);
  return root.innerHTML;
}

export function createPasteSanitizer(options: PasteOptions = {}): Plugin {
  const mode = options.mode ?? "schema";
  return new Plugin({
    key: pasteSanitizerKey,
    props: {
      transformPastedHTML(html: string, view): string {
        if (mode === "off") return html;
        if (mode === "plain") {
          const tmp = view.dom.ownerDocument.createElement("div");
          tmp.innerHTML = html;
          return tmp.textContent ?? "";
        }
        return sanitizeHtml(html, options, view.dom.ownerDocument);
      },
    },
  });
}
