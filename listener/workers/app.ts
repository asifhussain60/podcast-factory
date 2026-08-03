import { createRequestHandler, RouterContextProvider } from "react-router";
import { cloudflare } from "../app/context";

const requestHandler = createRequestHandler(
  () => import("virtual:react-router/server-build"),
  import.meta.env.MODE,
);

export default {
  fetch(request, env, ctx) {
    // Fresh per request: bindings are request-scoped, and a provider shared
    // across requests would leak one visitor's context into another's.
    const context = new RouterContextProvider();
    context.set(cloudflare, { env, ctx });
    return requestHandler(request, context);
  },
} satisfies ExportedHandler<Env>;
