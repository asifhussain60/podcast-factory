/**
 * Uniform API response helpers — all API routes should use these helpers
 * so error shapes are consistent and typed on the client side.
 */

/** Standard success envelope. Extra headers merge after the JSON default. */
export function apiOk<T>(
  data: T,
  status = 200,
  headers?: Record<string, string>,
): Response {
  return new Response(JSON.stringify({ ok: true, data }), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

/** Standard error envelope. Extra headers merge after the JSON default. */
export function apiError(
  message: string,
  status = 400,
  headers?: Record<string, string>,
): Response {
  return new Response(JSON.stringify({ ok: false, error: message }), {
    status,
    headers: { "content-type": "application/json", ...headers },
  });
}

/** Standard 404. */
export function apiNotFound(message = "not found"): Response {
  return apiError(message, 404);
}

/** Standard 500. */
export function apiServerError(message = "internal server error"): Response {
  return apiError(message, 500);
}
