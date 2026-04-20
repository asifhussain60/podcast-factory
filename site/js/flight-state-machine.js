/**
 * flight-state-machine.js — Computes the current display state for the
 * flight tracker widget based on flight data and the current time.
 *
 * States: PRE_TRIP | ACTIVE_FLIGHT | COLLAPSED | CHECK_IN_REMINDER |
 *         BETWEEN_FLIGHTS | POST_TRIP | HIDDEN
 *
 * Exported on window.flightStateMachine for use by flight-tracker.jsx.
 */
(function () {
  'use strict';

  var STATES = {
    PRE_TRIP: 'PRE_TRIP',
    ACTIVE_FLIGHT: 'ACTIVE_FLIGHT',
    COLLAPSED: 'COLLAPSED',
    CHECK_IN_REMINDER: 'CHECK_IN_REMINDER',
    BETWEEN_FLIGHTS: 'BETWEEN_FLIGHTS',
    POST_TRIP: 'POST_TRIP',
    HIDDEN: 'HIDDEN'
  };

  var MS_PER_HOUR = 3600000;
  var MS_PER_DAY = 86400000;

  /**
   * Parse a flight date string (YYYY-MM-DD) to midnight local Date.
   */
  function parseFlightDate(dateStr) {
    if (!dateStr) return null;
    var d = new Date(dateStr + 'T00:00:00');
    return isNaN(d.getTime()) ? null : d;
  }

  /**
   * Compute the widget state and which flight to display.
   *
   * @param {Array} flights - normalizeFlights() output
   * @param {Object} [liveStatuses] - map of flightId → { landed: boolean }
   * @param {Date} [now] - override for testing
   * @returns {{ state: string, flight: Object|null, nextFlight: Object|null, flights: Array }}
   */
  function computeFlightState(flights, liveStatuses, now) {
    if (!flights || flights.length === 0) {
      return { state: STATES.HIDDEN, flight: null, nextFlight: null, flights: [] };
    }

    now = now || new Date();
    liveStatuses = liveStatuses || {};
    var nowMs = now.getTime();

    // Sort by date (already chronological from normalize, but be safe)
    var sorted = flights.slice().sort(function (a, b) {
      var da = parseFlightDate(a.date);
      var db = parseFlightDate(b.date);
      if (!da || !db) return 0;
      return da.getTime() - db.getTime();
    });

    var firstDate = parseFlightDate(sorted[0].date);
    if (!firstDate) {
      return { state: STATES.HIDDEN, flight: null, nextFlight: null, flights: sorted };
    }

    // Check if a flight has landed (via live status data)
    function hasLanded(f) {
      var id = (f.flight || '').replace(/\s+/g, '');
      var live = liveStatuses[id];
      if (live && live.landed) return true;
      // Also mark as landed if its date is in the past (>24h ago)
      var fd = parseFlightDate(f.date);
      return fd && (nowMs - fd.getTime()) > MS_PER_DAY;
    }

    function isSameDay(d1, d2) {
      return d1.getFullYear() === d2.getFullYear() &&
             d1.getMonth() === d2.getMonth() &&
             d1.getDate() === d2.getDate();
    }

    // Find first non-landed flight
    var nextFlightIdx = -1;
    for (var i = 0; i < sorted.length; i++) {
      if (!hasLanded(sorted[i])) {
        nextFlightIdx = i;
        break;
      }
    }

    // All flights completed
    if (nextFlightIdx === -1) {
      var last = sorted[sorted.length - 1];
      return { state: STATES.POST_TRIP, flight: last, nextFlight: null, flights: sorted };
    }

    var nextFlight = sorted[nextFlightIdx];
    var nextFlightDate = parseFlightDate(nextFlight.date);
    var msToNext = nextFlightDate ? nextFlightDate.getTime() - nowMs : Infinity;
    var sameDay = nextFlightDate && isSameDay(now, nextFlightDate);

    // ACTIVE_FLIGHT: same calendar day as flight, or flight in-air (date passed <24h ago)
    if (sameDay || (msToNext <= 0 && msToNext > -MS_PER_DAY)) {
      var afterFlight = nextFlightIdx + 1 < sorted.length ? sorted[nextFlightIdx + 1] : null;
      return { state: STATES.ACTIVE_FLIGHT, flight: nextFlight, nextFlight: afterFlight, flights: sorted };
    }

    // PRE_TRIP: before the first flight, not same day
    if (nextFlightIdx === 0) {
      return { state: STATES.PRE_TRIP, flight: nextFlight, nextFlight: nextFlight, flights: sorted };
    }

    // Between flights (a previous flight has landed)
    var prevFlight = sorted[nextFlightIdx - 1];

    // CHECK_IN_REMINDER: within 48h of next flight (but not same day — that's ACTIVE)
    if (msToNext > 0 && msToNext <= 2 * MS_PER_DAY) {
      return { state: STATES.CHECK_IN_REMINDER, flight: nextFlight, nextFlight: nextFlight, flights: sorted };
    }

    // COLLAPSED: next flight >48h away but previous flight just landed (within 24h)
    var prevDate = parseFlightDate(prevFlight.date);
    var sincePrev = prevDate ? nowMs - prevDate.getTime() : Infinity;
    if (sincePrev < MS_PER_DAY) {
      return { state: STATES.COLLAPSED, flight: prevFlight, nextFlight: nextFlight, flights: sorted };
    }

    // BETWEEN_FLIGHTS: general between-flights state
    return { state: STATES.BETWEEN_FLIGHTS, flight: nextFlight, nextFlight: nextFlight, flights: sorted };
  }

  /**
   * Determine the polling interval in ms for the current state.
   */
  function getPollingInterval(flights, now) {
    if (!flights || flights.length === 0) return null;
    now = now || new Date();
    var nowMs = now.getTime();

    // Find the nearest upcoming flight date
    var nearest = null;
    var nearestMs = Infinity;
    for (var i = 0; i < flights.length; i++) {
      var fd = parseFlightDate(flights[i].date);
      if (!fd) continue;
      var diff = fd.getTime() - nowMs;
      if (diff > -MS_PER_DAY && Math.abs(diff) < Math.abs(nearestMs)) {
        nearest = flights[i];
        nearestMs = diff;
      }
    }

    if (!nearest) return null; // all done

    var msToFlight = nearestMs;
    var nearestDate = parseFlightDate(nearest.date);
    var sameDay = nearestDate &&
      now.getFullYear() === nearestDate.getFullYear() &&
      now.getMonth() === nearestDate.getMonth() &&
      now.getDate() === nearestDate.getDate();

    // Same day or in-flight (0 to -24h)
    if (sameDay || (msToFlight <= 0 && msToFlight > -MS_PER_DAY)) return 3 * 60 * 1000;  // 3 min
    // <2h before
    if (msToFlight > 0 && msToFlight <= 2 * MS_PER_HOUR) return 2 * 60 * 1000;  // 2 min
    // 2-24h
    if (msToFlight > 2 * MS_PER_HOUR && msToFlight <= MS_PER_DAY) return 5 * 60 * 1000;  // 5 min
    // 24-48h (check-in window)
    if (msToFlight > MS_PER_DAY && msToFlight <= 2 * MS_PER_DAY) return 30 * 60 * 1000;  // 30 min
    // >48h
    return null;
  }

  window.flightStateMachine = {
    STATES: STATES,
    computeFlightState: computeFlightState,
    getPollingInterval: getPollingInterval,
    parseFlightDate: parseFlightDate
  };

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { STATES: STATES, computeFlightState: computeFlightState, getPollingInterval: getPollingInterval, parseFlightDate: parseFlightDate };
  }
})();
