import { createContext } from "react-router";

/**
 * The Worker's bindings and execution context, made available to every loader,
 * action and middleware.
 *
 * React Router 8 made middleware the default and replaced v7's
 * `AppLoadContext` interface-augmentation with typed contexts, so this is the
 * one place the shape is declared. `workers/app.ts` populates it per request —
 * D1 and R2 bindings only exist inside a request scope, so nothing here can be
 * hoisted to module level.
 */
export type CloudflareContext = {
  env: Env;
  ctx: ExecutionContext;
};

export const cloudflare = createContext<CloudflareContext>();
