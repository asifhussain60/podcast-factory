/**
 * GET /api/wisdom/topic?id=<n>
 *
 * Wave J (J2 + J5): Wisdom topic lookup — full TopicDataUnicode + linked Quran
 * ayats + glossary terms, served from source_library_server.py at localhost:4390.
 *
 * Consumed by the J5 TopicPopover component.
 * Returns 503 when local server is unreachable.
 */

import type { APIRoute } from "astro";
import { fetchLocalTopic } from "../../../lib/localServerClient";

export const prerender = false;

export const GET: APIRoute = async ({ url }) => {
  const idParam = url.searchParams.get("id");
  const id = Number(idParam);
  if (!idParam || !Number.isInteger(id) || id < 1) {
    return new Response(
      JSON.stringify({ error: "missing or invalid id param" }),
      { status: 400 },
    );
  }

  const data = await fetchLocalTopic(id);
  if (!data) {
    return new Response(
      JSON.stringify({ error: "local source library server unreachable" }),
      { status: 503, headers: { "content-type": "application/json" } },
    );
  }

  return new Response(JSON.stringify(data), {
    status: 200,
    headers: {
      "content-type": "application/json",
      "cache-control": "public, max-age=3600",
    },
  });
};
