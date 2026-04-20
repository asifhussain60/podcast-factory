# RapidAPI Integrations

## AeroDataBox — Live Flight Status

| Field | Value |
|-------|-------|
| **Provider** | AeroDataBox via RapidAPI |
| **RapidAPI Host** | `aerodatabox.p.rapidapi.com` |
| **Keychain key** | `rapidapi-key` (loaded via `server/src/lib/keychain.js`) |
| **Server route** | `GET /api/flight-status?flight=UA147&date=2026-04-20` |
| **Rate limit** | 150 requests/month (free tier) |
| **Cache** | In-process, 5-minute TTL, keyed by `flight|date` |

### Endpoint

```
GET https://aerodatabox.p.rapidapi.com/flights/number/{flightCode}/{date}
```

Headers: `X-RapidAPI-Key`, `X-RapidAPI-Host`.

### Polling Budget

A typical 9-day trip with 2 flights uses approximately **80 API calls** at the adaptive
polling intervals defined in the flight tracker widget:

| Time Window | Interval | Justification |
|-------------|----------|---------------|
| >48h from any flight | None | AeroDataBox has no data this far out |
| 24–48h (check-in window) | 30 min | Gate assignments start appearing |
| 2–24h before departure | 5 min | Status changes become frequent |
| <2h before departure | 2 min | Boarding/delay updates |
| In-flight | 3 min | Progress bar needs smooth updates |
| Landed / all complete | None | Polling stops |

### Circuit Breaker

After **3 consecutive API errors** (HTTP 4xx/5xx or timeout), polling stops automatically.
The widget displays last-known-good data with a "Live status unavailable" indicator.
Polling resumes on the next state-machine transition (entering a new time window).

A `maxPollsPerSession` cap of **200** prevents runaway polling from any bug.

### Graceful Degradation

If `RAPIDAPI_KEY` is not configured in Keychain, the server returns:
```json
{ "ok": true, "configured": false, "message": "RapidAPI key not configured" }
```
The flight tracker widget renders static flight data without live status.

### Error Response

On upstream failure, the server returns HTTP 502:
```json
{ "ok": false, "error": "AeroDataBox HTTP 429", "detail": "..." }
```

---

## TrueWay APIs — Geocoding, Directions, Distance Matrix *(Planned — Phase D)*

> Deferred to a separate PR post-trip. OpenRouteService works today.
> TrueWay consolidates geocoding, routing, and distance matrix under the same
> `rapidapi-key`, eliminating the `ORS_API_KEY` environment variable.

| API | Free Tier | Purpose |
|-----|-----------|---------|
| TrueWay Geocoding | 500 req/mo | Venue geocoding for distance matrix |
| TrueWay Directions | 500 req/mo | Drive time chips, reorder time recalc |
| TrueWay Matrix | 250 req/mo | Day route distance calculations |

Will be implemented in `server/src/lib/trueway.js` with the same interface as
the current `server/src/lib/ors.js`.
