import { data } from "react-router";

/**
 * The single way to say "no".
 *
 * `data(...)` rather than `new Response(...)`: a bare Response short-circuits
 * the React render and produces a plain-text body, visibly unlike the styled
 * 404 a genuinely missing page produces. Routing the refusal through the error
 * path renders the real boundary instead, which is what makes a denied request
 * and a nonexistent one indistinguishable.
 *
 * Its own module so the middleware that need it do not have to import anything
 * that reaches the database.
 */
export function notFound(): never {
  throw data(null, { status: 404 });
}
