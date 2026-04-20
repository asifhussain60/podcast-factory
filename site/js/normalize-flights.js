/**
 * normalizeFlights(trip) — read-time normalization of trip.flights into a
 * canonical ordered array. Handles three input formats:
 *
 *  1. Old object: { inbound: {...}, outbound: {...} }
 *  2. Ingest array: [{ airline, departure, arrival, date }]
 *  3. New array: [{ flight, route, date, depart, arrive, seat, direction, leg }]
 *
 * Returns: Array of { flight, route, date, depart, arrive, seat, direction, leg }
 * Never mutates the source data.
 */
(function () {
  'use strict';

  function normalizeFlights(trip) {
    if (!trip || !trip.flights) return [];

    var flights = trip.flights;

    // Format 3: new array — pass-through (detect by Array.isArray)
    if (Array.isArray(flights)) {
      return flights.map(function (f, i) {
        // Could be ingest format (airline/departure/arrival) or new format (flight/route/depart/arrive)
        if (f.airline && !f.flight) {
          // Format 2: ingest array
          return normalizeIngestEntry(f, i);
        }
        // Format 3: new array — fill defaults for optional fields
        return {
          flight: f.flight || null,
          route: f.route || null,
          date: f.date || null,
          depart: f.depart || null,
          arrive: f.arrive || null,
          seat: f.seat || null,
          direction: f.direction || null,
          leg: f.leg != null ? f.leg : i + 1
        };
      });
    }

    // Format 1: old object { inbound, outbound, ... }
    if (typeof flights === 'object') {
      var result = [];
      var legIndex = 1;
      // Canonical ordering: inbound first, then outbound, then any other keys
      var keys = Object.keys(flights);
      var ordered = [];
      if (flights.inbound) ordered.push('inbound');
      if (flights.outbound) ordered.push('outbound');
      keys.forEach(function (k) {
        if (k !== 'inbound' && k !== 'outbound') ordered.push(k);
      });

      ordered.forEach(function (key) {
        var f = flights[key];
        if (!f || typeof f !== 'object') return;
        result.push({
          flight: f.flight || null,
          route: f.route || null,
          date: f.date || null,
          depart: f.depart || null,
          arrive: f.arrive || null,
          seat: f.seat || null,
          direction: key === 'inbound' || key === 'outbound' ? key : (f.direction || null),
          leg: legIndex++
        });
      });
      return result;
    }

    return [];
  }

  function normalizeIngestEntry(f, index) {
    // Map ingest fields: airline→flight, departure→depart, arrival→arrive
    var depart = f.departure || null;
    var arrive = f.arrival || null;
    // Synthesize route from departure/arrival city names if available
    var route = null;
    if (depart && arrive) {
      route = depart + ' \u2192 ' + arrive;
    }
    return {
      flight: f.airline || null,
      route: route,
      date: f.date || null,
      depart: depart,
      arrive: arrive,
      seat: f.seat || null,
      direction: f.direction || null,
      leg: f.leg != null ? f.leg : index + 1
    };
  }

  // Expose globally
  window.normalizeFlights = normalizeFlights;

  // Also export for Node.js testing
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { normalizeFlights: normalizeFlights };
  }
})();
