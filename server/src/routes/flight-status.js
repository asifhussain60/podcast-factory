// routes/flight-status.js — AeroDataBox proxy for live flight status.
//
//   GET /api/flight-status?flight=UA147&date=2026-04-20
//
// Proxies to RapidAPI's AeroDataBox endpoint. Returns normalised status with
// timing deltas and a severity level (on-time / delayed / late / cancelled).
//
// Without RAPIDAPI_KEY, returns { ok: true, configured: false } so the client
// renders gracefully without live data.
//
// Cache: in-process, keyed by flight+date, TTL 5 minutes. Avoids burning the
// 150 req/month free tier on repeated page refreshes.

import express from "express";
import { loadRapidApiKey } from "../lib/keychain.js";

const CACHE = new Map();
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

const AERODATABOX_HOST = "aerodatabox.p.rapidapi.com";

function cacheKey(flight, date) {
  return `${flight.toUpperCase().replace(/\s+/g, "")}|${date}`;
}

// Parse "UA 147" or "UA147" → { iata: "UA", number: "147" }
function parseFlight(raw) {
  const m = raw.trim().match(/^([A-Z]{2})\s*(\d{1,4})$/i);
  if (!m) return null;
  return { iata: m[1].toUpperCase(), number: m[2] };
}

// Normalise AeroDataBox response into a clean status object.
function normalise(flights, flightStr) {
  if (!Array.isArray(flights) || flights.length === 0) {
    return { status: "unknown", message: "No data available" };
  }
  // Pick the best match (first entry is usually the one).
  const f = flights[0];
  const dep = f.departure || {};
  const arr = f.arrival || {};

  const scheduledDep = dep.scheduledTime?.local || dep.scheduledTimeLocal || null;
  const actualDep = dep.actualTime?.local || dep.actualTimeLocal || dep.revisedTime?.local || dep.revisedTimeLocal || null;
  const scheduledArr = arr.scheduledTime?.local || arr.scheduledTimeLocal || null;
  const actualArr = arr.actualTime?.local || arr.actualTimeLocal || arr.revisedTime?.local || arr.revisedTimeLocal || null;

  // Compute delay in minutes (departure-based, more useful for travellers).
  let delayMinutes = null;
  if (scheduledDep && actualDep) {
    const sched = new Date(scheduledDep);
    const actual = new Date(actualDep);
    if (!isNaN(sched) && !isNaN(actual)) {
      delayMinutes = Math.round((actual - sched) / 60000);
    }
  }
  // Also check arrival delay.
  let arrivalDelayMinutes = null;
  if (scheduledArr && actualArr) {
    const sched = new Date(scheduledArr);
    const actual = new Date(actualArr);
    if (!isNaN(sched) && !isNaN(actual)) {
      arrivalDelayMinutes = Math.round((actual - sched) / 60000);
    }
  }

  // Use the worse of the two delays for severity.
  const worstDelay = Math.max(delayMinutes ?? 0, arrivalDelayMinutes ?? 0);

  // AeroDataBox status field.
  const rawStatus = (f.status || "").toLowerCase();

  let severity, label;
  if (rawStatus.includes("cancel")) {
    severity = "cancelled";
    label = "Cancelled";
  } else if (rawStatus.includes("divert")) {
    severity = "cancelled";
    label = "Diverted";
  } else if (worstDelay >= 60) {
    severity = "late";
    label = `Late ${worstDelay}min`;
  } else if (worstDelay >= 15) {
    severity = "delayed";
    label = `Delayed ${worstDelay}min`;
  } else if (rawStatus.includes("landed") || rawStatus.includes("arrived")) {
    severity = "on-time";
    label = "Landed";
  } else if (rawStatus.includes("active") || rawStatus.includes("en route") || rawStatus.includes("airborne")) {
    severity = "on-time";
    label = "In Flight";
  } else {
    severity = "on-time";
    label = "On Time";
  }

  return {
    status: rawStatus || "unknown",
    severity,          // on-time | delayed | late | cancelled
    label,             // human-readable badge text
    flight: flightStr,
    departure: {
      airport: dep.airport?.iata || null,
      scheduled: scheduledDep,
      actual: actualDep,
      terminal: dep.terminal || null,
      gate: dep.gate || null,
    },
    arrival: {
      airport: arr.airport?.iata || null,
      scheduled: scheduledArr,
      actual: actualArr,
      terminal: arr.terminal || null,
      gate: arr.gate || null,
    },
    delayMinutes,
    arrivalDelayMinutes,
    aircraft: f.aircraft?.model || null,
  };
}

export function createFlightStatusRouter() {
  const router = express.Router();
  const { key: RAPIDAPI_KEY } = loadRapidApiKey();

  router.get("/api/flight-status", async (req, res) => {
    try {
      const { flight, date } = req.query;
      if (!flight || typeof flight !== "string") {
        return res.status(400).json({ ok: false, error: "flight query param required (e.g. UA147)" });
      }
      if (!RAPIDAPI_KEY) {
        return res.json({ ok: true, configured: false, message: "RapidAPI key not configured" });
      }
      const parsed = parseFlight(flight);
      if (!parsed) {
        return res.status(400).json({ ok: false, error: "Invalid flight format. Expected e.g. UA147 or UA 147" });
      }

      const flightCode = `${parsed.iata}${parsed.number}`;
      const dateStr = date && /^\d{4}-\d{2}-\d{2}$/.test(date) ? date : new Date().toISOString().slice(0, 10);

      // Check cache.
      const ck = cacheKey(flightCode, dateStr);
      const cached = CACHE.get(ck);
      if (cached && Date.now() - cached.at < CACHE_TTL_MS) {
        return res.json({ ok: true, cached: true, ...cached.data });
      }

      // Call AeroDataBox.
      const url = `https://${AERODATABOX_HOST}/flights/number/${flightCode}/${dateStr}`;
      const resp = await fetch(url, {
        headers: {
          "X-RapidAPI-Key": RAPIDAPI_KEY,
          "X-RapidAPI-Host": AERODATABOX_HOST,
        },
        signal: AbortSignal.timeout(10000),
      });

      if (resp.status === 404) {
        const data = { status: "unknown", severity: "unknown", label: "Not Found", flight: flightCode };
        return res.json({ ok: true, ...data });
      }
      if (!resp.ok) {
        const body = await resp.text().catch(() => "");
        return res.status(502).json({ ok: false, error: `AeroDataBox HTTP ${resp.status}`, detail: body.slice(0, 200) });
      }

      const flights = await resp.json();
      const data = normalise(flights, flightCode);

      // Cache.
      CACHE.set(ck, { at: Date.now(), data });

      res.json({ ok: true, cached: false, ...data });
    } catch (err) {
      if (err.name === "TimeoutError") {
        return res.status(504).json({ ok: false, error: "AeroDataBox request timed out" });
      }
      res.status(502).json({ ok: false, error: err?.message ?? String(err) });
    }
  });

  return router;
}
