/**
 * shortcuts.ts — one registry, keyed off the button definitions themselves.
 *
 * A shortcut is a FIELD on its ButtonDef, so a button and its accelerator
 * cannot drift apart. The editor this replaces needed a separate global
 * registration call per shortcut AND a fifth allow-list naming which of them
 * were enabled — and two shortcuts were registered and then left out of that
 * allow-list, so they silently did nothing while their tooltips advertised them.
 *
 * A duplicate binding THROWS at registration rather than last-wins. Silent
 * last-wins is how a shortcut ends up doing something other than what its
 * tooltip says, which is worse than not having it.
 */
import { ShortcutConflictError } from "../errors.ts";
import type { EditorApi } from "../types.ts";
import type { ButtonDef } from "../extend/define.ts";

export interface ShortcutBinding {
  /** "Mod-b", "Mod-Shift-z", "Alt-a". `Mod` is Cmd on Apple, Ctrl elsewhere. */
  shortcut: string;
  id: string;
  run: (api: EditorApi) => void | Promise<void>;
}

/** Canonical form: sorted modifiers, lowercased key, so "Shift-Mod-Z" and
 *  "Mod-Shift-z" are recognised as the same binding rather than as two. */
export function normalizeShortcut(shortcut: string): string {
  const parts = shortcut.split("-").filter(Boolean);
  const key = (parts.pop() ?? "").toLowerCase();
  const mods = parts.map((m) => m.toLowerCase()).sort();
  return [...mods, key].join("-");
}

function eventShortcut(e: KeyboardEvent, isApple: boolean): string {
  const mods: string[] = [];
  if (isApple ? e.metaKey : e.ctrlKey) mods.push("mod");
  if (e.altKey) mods.push("alt");
  if (e.shiftKey) mods.push("shift");
  // A non-Mod control key is its own modifier on Apple platforms.
  if (isApple && e.ctrlKey) mods.push("ctrl");
  return [...mods.sort(), e.key.toLowerCase()].join("-");
}

export interface ShortcutRegistry {
  /** @throws ShortcutConflictError if the combination is already claimed. */
  register(binding: ShortcutBinding): void;
  /** Attach to an element (the editor's own DOM). Returns the detach fn. */
  listen(target: HTMLElement, api: EditorApi): () => void;
  has(shortcut: string): boolean;
}

export function createShortcutRegistry(options?: {
  isApple?: boolean;
}): ShortcutRegistry {
  const bindings = new Map<string, ShortcutBinding>();
  const isApple =
    options?.isApple ??
    (typeof globalThis.navigator !== "undefined" &&
      /Mac|iPhone|iPad/.test(globalThis.navigator.platform ?? ""));

  return {
    register(binding) {
      const key = normalizeShortcut(binding.shortcut);
      const existing = bindings.get(key);
      if (existing && existing.id !== binding.id) {
        throw new ShortcutConflictError(
          binding.shortcut,
          existing.id,
          binding.id,
        );
      }
      bindings.set(key, binding);
    },
    has: (shortcut) => bindings.has(normalizeShortcut(shortcut)),
    listen(target, api) {
      const onKeyDown = (event: Event): void => {
        const e = event as KeyboardEvent;
        const binding = bindings.get(eventShortcut(e, isApple));
        if (!binding) return;
        e.preventDefault();
        void binding.run(api);
      };
      target.addEventListener("keydown", onKeyDown);
      return () => target.removeEventListener("keydown", onKeyDown);
    },
  };
}

/** Collect the shortcuts declared on a set of buttons. */
export function bindingsFromButtons(
  defs: readonly ButtonDef[],
): ShortcutBinding[] {
  return defs
    .filter((d): d is ButtonDef & { shortcut: string } => Boolean(d.shortcut))
    .map((d) => ({ shortcut: d.shortcut, id: d.id, run: d.run }));
}
