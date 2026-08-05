/**
 * fallback-ui-host.ts — the minimum that makes the built-in link button work in
 * a host that supplies no UI of its own.
 *
 * Explicitly NOT a modal system. The package owns no dialog implementation on
 * purpose: every real host already has one, and a second competing modal layer
 * is worse than none — it brings its own focus trap, its own stacking order and
 * its own idea of what a dialog looks like, none of which will match.
 *
 * A host supplies `ui` and this is never used.
 */
import type { DialogRequest, UiHost } from "../types.ts";

export function createFallbackUiHost(): UiHost {
  return {
    async openDialog<T>(request: DialogRequest): Promise<T | null> {
      const field = request.fields?.[0];
      if (!field) return null;
      const initial =
        request.initial && typeof request.initial[field.name] === "string"
          ? String(request.initial[field.name])
          : "";
      const answer = globalThis.prompt?.(
        `${request.title}\n${field.label}`,
        initial,
      );
      if (answer === null || answer === undefined) return null;
      return { [field.name]: answer } as T;
    },
    async confirm({ title, message }) {
      return globalThis.confirm?.(`${title}\n\n${message}`) ?? false;
    },
  };
}
