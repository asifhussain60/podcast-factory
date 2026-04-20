/* flight-tracker.jsx — Unified flight tracker widget for the itinerary page.
   Mounts at #flight-tracker-root between <nav> and <section class="hero">.
   Uses the state machine from flight-state-machine.js and data from
   window.__tripData (populated by refreshItinerary).

   Dependencies (all loaded via itinerary.html):
     - React 18 UMD (window.React, window.ReactDOM)
     - window.normalizeFlights (site/js/normalize-flights.js)
     - window.flightStateMachine (site/js/flight-state-machine.js)
     - window.__tripData (set by itinerary.html refreshItinerary)
     - window.__API_BASE (set by itinerary.html)
*/

(function () {
  'use strict';

  var h, useState, useEffect, useRef, useCallback;

  var SM = window.flightStateMachine;
  var STATES = SM.STATES;

  // ── Static data ──

  var AIRPORTS = {
    LHR: { city: 'London, UK', tz: 'Europe/London' },
    EWR: { city: 'Newark, NJ', tz: 'America/New_York' },
    JFK: { city: 'New York, NY', tz: 'America/New_York' },
    IST: { city: 'Istanbul', tz: 'Europe/Istanbul' },
    LHE: { city: 'Lahore', tz: 'Asia/Karachi' },
    ISB: { city: 'Islamabad', tz: 'Asia/Karachi' },
    KHI: { city: 'Karachi', tz: 'Asia/Karachi' },
    DXB: { city: 'Dubai', tz: 'Asia/Dubai' },
    DOH: { city: 'Doha', tz: 'Asia/Qatar' },
    CDG: { city: 'Paris', tz: 'Europe/Paris' },
    FRA: { city: 'Frankfurt', tz: 'Europe/Berlin' },
    AMS: { city: 'Amsterdam', tz: 'Europe/Amsterdam' },
    ORD: { city: 'Chicago, IL', tz: 'America/Chicago' },
    LAX: { city: 'Los Angeles, CA', tz: 'America/Los_Angeles' },
    SFO: { city: 'San Francisco, CA', tz: 'America/Los_Angeles' },
    BOS: { city: 'Boston, MA', tz: 'America/New_York' },
    IAD: { city: 'Washington, DC', tz: 'America/New_York' },
    ATL: { city: 'Atlanta, GA', tz: 'America/New_York' },
    MIA: { city: 'Miami, FL', tz: 'America/New_York' },
    MCO: { city: 'Orlando, FL', tz: 'America/New_York' }
  };

  var CHECKIN_URLS = {
    UA: 'https://www.united.com/en/us/check-in',
    BA: 'https://www.britishairways.com/travel/olcilandingpagealiaspublic',
    TK: 'https://www.turkishairlines.com/en-int/online-services/check-in/',
    PK: 'https://www.piac.com.pk/en-pk/manage/check-in'
  };

  var MAX_POLLS_PER_SESSION = 200;
  var CIRCUIT_BREAKER_THRESHOLD = 3;

  // Track previous gate/terminal/baggage values for change detection
  var _prevArrivalInfo = {};  // keyed by flight id → { terminal, gate, baggageBelt }

  // ── Helpers ──

  function parseRoute(route) {
    if (!route) return { dep: '', arr: '' };
    var parts = route.split(/\s*[\u2192→]\s*/);
    return { dep: parts[0] || '', arr: parts[1] || '' };
  }

  function cityFor(code) {
    var a = AIRPORTS[code];
    return a ? a.city : '';
  }

  function tzFor(code) {
    var a = AIRPORTS[code];
    return a ? a.tz : null;
  }

  function tzAbbr(tz) {
    if (!tz) return '';
    try {
      var parts = new Intl.DateTimeFormat('en-US', { timeZone: tz, timeZoneName: 'short' })
        .formatToParts(new Date());
      var tzPart = parts.find(function(p) { return p.type === 'timeZoneName'; });
      return tzPart ? tzPart.value : '';
    } catch (e) { return ''; }
  }

  /** Format a time string (e.g. "2:55 PM ET") into a specific timezone */
  function convertTimeToTz(isoStr, tz) {
    if (!isoStr || !tz) return '';
    try {
      var d = new Date(isoStr);
      if (isNaN(d.getTime())) return '';
      return d.toLocaleTimeString('en-US', {
        timeZone: tz,
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short'
      });
    } catch (e) { return ''; }
  }

  function carrierCode(flightStr) {
    if (!flightStr) return '';
    var m = flightStr.trim().match(/^([A-Z]{2})/i);
    return m ? m[1].toUpperCase() : '';
  }

  function checkinUrl(flightStr) {
    var code = carrierCode(flightStr);
    return CHECKIN_URLS[code] || null;
  }

  function daysUntil(dateStr) {
    if (!dateStr) return null;
    var target = new Date(dateStr + 'T00:00:00');
    var now = new Date();
    now.setHours(0, 0, 0, 0);
    var diff = Math.ceil((target.getTime() - now.getTime()) / 86400000);
    return diff;
  }

  function formatDaysLabel(days) {
    if (days === null || days === undefined) return '';
    if (days === 0) return 'Today';
    if (days === 1) return 'Tomorrow';
    if (days > 1) return days + 'd';
    return '';
  }

  function formatLocalTime(isoStr) {
    if (!isoStr) return '';
    try {
      var d = new Date(isoStr);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) { return isoStr; }
  }

  function flightId(f) {
    return (f.flight || '').replace(/\s+/g, '');
  }

  /** Is the flight currently airborne based on status string? */
  function isInFlight(status) {
    if (!status) return false;
    var st = (status.status || '').toLowerCase();
    return st.includes('active') || st.includes('en route') || st.includes('enroute') ||
           st.includes('airborne') || st.includes('departed');
  }

  /** Compute ms remaining until arrival. Returns null if unknown. */
  function msToArrival(status) {
    if (!status || !status.arrival) return null;
    var arr = status.arrival;
    var arrIso = arr.actual || arr.scheduled;
    if (!arrIso) return null;
    var arrTime = new Date(arrIso).getTime();
    if (isNaN(arrTime)) return null;
    var remaining = arrTime - Date.now();
    return remaining > 0 ? remaining : 0;
  }

  /** Format ms into human-readable ETA: "5h 23m", "47m", "< 1m" */
  function formatETA(ms) {
    if (ms === null || ms === undefined) return '';
    var totalMin = Math.ceil(ms / 60000);
    if (totalMin < 1) return '< 1m';
    var hours = Math.floor(totalMin / 60);
    var mins = totalMin % 60;
    if (hours > 0) return hours + 'h ' + (mins > 0 ? mins + 'm' : '');
    return mins + 'm';
  }

  // ── StatusBadge ──

  function StatusBadge(props) {
    var severity = props.severity || 'loading';
    var label = props.label || 'Checking\u2026';
    return h('div', { className: 'ft-status ft-status--' + severity },
      h('span', { className: 'ft-status-dot' }),
      ' ' + label
    );
  }

  // ── ETABadge (replaces StatusBadge when airborne) ──

  function ETABadge(props) {
    var remaining = props.remaining; // ms
    var severity = props.severity || 'on-time';
    if (remaining === null || remaining === undefined) return null;
    var label = formatETA(remaining);
    var isUrgent = remaining < 30 * 60000; // < 30 min
    return h('div', { className: 'ft-eta ft-eta--' + severity + (isUrgent ? ' ft-eta--urgent' : '') },
      h('i', { className: 'fa-solid fa-clock' }),
      h('span', { className: 'ft-eta-value' }, label),
      h('span', { className: 'ft-eta-label' }, ' remaining')
    );
  }

  // ── WhenToLeave (estimated pickup/departure time from airport) ──
  // Based on real-world airport data:
  //   International: deplaning ~20min + immigration/customs ~30-45min + baggage ~20min = ~75min
  //   Domestic:      deplaning ~10min + baggage ~15min = ~25min
  // Sources: TSA, CBP averages, airline industry data
  var AIRPORT_BUFFER_MIN = {
    international: 75,  // deplaning(20) + immigration/customs(35) + baggage(20)
    domestic: 25        // deplaning(10) + baggage(15)
  };

  // Breakdown for display
  var BUFFER_BREAKDOWN = {
    international: { deplane: 20, customs: 35, baggage: 20 },
    domestic:      { deplane: 10, customs: 0,  baggage: 15 }
  };

  function isInternational(routeStr) {
    var route = parseRoute(routeStr);
    var depA = AIRPORTS[route.dep];
    var arrA = AIRPORTS[route.arr];
    if (!depA || !arrA) return true; // default to international
    // Check if departure and arrival are in different countries via timezone
    // Timezones starting with the same region (America, Europe, Asia) in different zones = international
    return depA.tz !== arrA.tz;
  }

  /**
   * Compute "ready to leave airport" and "arrive at hotel" times.
   * Returns breakdown with deboard, customs, baggage, drive info.
   */
  function computeWhenToLeave(status, flight) {
    if (!status || !status.arrival) return null;
    var arrIso = status.arrival.actual || status.arrival.scheduled;
    if (!arrIso) return null;
    var arrMs = new Date(arrIso).getTime();
    if (isNaN(arrMs)) return null;

    var intl = isInternational(flight.route);
    var bufferMin = intl ? AIRPORT_BUFFER_MIN.international : AIRPORT_BUFFER_MIN.domestic;
    var breakdown = intl ? BUFFER_BREAKDOWN.international : BUFFER_BREAKDOWN.domestic;
    // Drive time + buffer override from trip manifest
    var trip = window.__tripData;
    var driveMin = null;
    var destination = '';
    var bufferOverridden = false;
    if (trip) {
      destination = trip.base || trip.hotel || '';
      if (trip.groundTransit) {
        if (trip.groundTransit.fromAirport) driveMin = trip.groundTransit.fromAirport;
        // Manifest airportBuffer overrides defaults (e.g. Global Entry / MPC holders)
        if (trip.groundTransit.airportBuffer != null) {
          bufferMin = trip.groundTransit.airportBuffer;
          bufferOverridden = true;
        }
      }
    }
    var readyMs = arrMs + bufferMin * 60000;

    // Format times in arrival airport's local tz
    var route = parseRoute(flight.route);
    var arrTz = tzFor(route.arr);
    var fmtOpts = { hour: 'numeric', minute: '2-digit', timeZoneName: 'short' };
    var fmtOptsTz = arrTz ? Object.assign({ timeZone: arrTz }, fmtOpts) : fmtOpts;

    var readyLabel = '';
    try { readyLabel = new Date(readyMs).toLocaleTimeString('en-US', fmtOptsTz); }
    catch (e) { readyLabel = new Date(readyMs).toLocaleTimeString('en-US', fmtOpts); }

    var arriveByLabel = '';
    if (driveMin) {
      var arriveByMs = readyMs + driveMin * 60000;
      try { arriveByLabel = new Date(arriveByMs).toLocaleTimeString('en-US', fmtOptsTz); }
      catch (e) { arriveByLabel = new Date(arriveByMs).toLocaleTimeString('en-US', fmtOpts); }
    }

    return {
      readyLabel: readyLabel,
      bufferMin: bufferMin,
      breakdown: breakdown,
      bufferOverridden: bufferOverridden,
      isInternational: intl,
      driveMin: driveMin,
      destination: destination,
      arriveByLabel: arriveByLabel
    };
  }

  function WhenToLeave(props) {
    var status = props.status;
    var flight = props.flight;
    var info = computeWhenToLeave(status, flight);
    if (!info) return null;

    // Build buffer breakdown text
    var breakdownText;
    if (info.bufferOverridden) {
      breakdownText = info.bufferMin + 'min airport buffer';
    } else {
      var parts = [];
      if (info.breakdown.deplane) parts.push(info.breakdown.deplane + 'min deplane');
      if (info.breakdown.customs) parts.push(info.breakdown.customs + 'min customs');
      if (info.breakdown.baggage) parts.push(info.breakdown.baggage + 'min bags');
      breakdownText = parts.join(' + ') + ' (' + info.bufferMin + 'min total)';
    }

    return h('div', { className: 'ft-when-to-leave' },
      h('div', { className: 'ft-wtl-header' },
        h('i', { className: 'fa-solid fa-car-side ft-wtl-icon' }),
        h('span', { className: 'ft-wtl-label' }, 'Leave airport by'),
        h('span', { className: 'ft-wtl-time' }, info.readyLabel)
      ),
      h('div', { className: 'ft-wtl-details' },
        h('span', { className: 'ft-wtl-breakdown' },
          h('i', { className: 'fa-solid fa-clock-rotate-left' }),
          ' ' + breakdownText
        ),
        info.driveMin ?
          h('span', { className: 'ft-wtl-drive' },
            h('i', { className: 'fa-solid fa-route' }),
            ' ~' + info.driveMin + ' min drive'
          ) : null,
        info.arriveByLabel && info.destination ?
          h('span', { className: 'ft-wtl-dest' },
            h('i', { className: 'fa-solid fa-location-dot' }),
            ' Arrive ' + info.destination + ' ~' + info.arriveByLabel
          ) : null
      )
    );
  }

  // ── Live Indicator ──
  // Shows real-time data freshness: "Live · Just now" → "Live · 3m ago" → "Stale · 8m ago"

  function LiveIndicator(props) {
    var lastFetched = props.lastFetched;
    if (!lastFetched) return null;
    var ageMs = Date.now() - lastFetched;
    var ageMin = Math.floor(ageMs / 60000);
    var isStale = ageMin >= 5;
    var label;
    if (ageMs < 60000) label = 'Just now';
    else if (ageMin < 60) label = ageMin + 'm ago';
    else label = Math.floor(ageMin / 60) + 'h ago';
    return h('div', { className: 'ft-live-ind' + (isStale ? ' ft-live-ind--stale' : '') },
      h('span', { className: 'ft-live-dot' }),
      h('span', { className: 'ft-live-text' }, (isStale ? 'Stale' : 'Live') + ' \u00B7 ' + label)
    );
  }

  // ── Skeleton loading component ──
  // Shows shimmer placeholders while waiting for first API response

  function SkeletonCard() {
    return h('div', { className: 'ft-card ft-skeleton' },
      h('div', { className: 'ft-full' },
        // Departure skeleton
        h('div', null,
          h('div', { className: 'ft-skel-line ft-skel-lg' }),
          h('div', { className: 'ft-skel-line ft-skel-md' }),
          h('div', { className: 'ft-skel-line ft-skel-sm' })
        ),
        // Centre skeleton
        h('div', { className: 'ft-route-col' },
          h('div', { className: 'ft-skel-line ft-skel-sm ft-skel-center' }),
          h('div', { className: 'ft-skel-bar' }),
          h('div', { className: 'ft-skel-line ft-skel-md ft-skel-center' }),
          h('div', { className: 'ft-skel-pill' })
        ),
        // Arrival skeleton
        h('div', { className: 'ft-right' },
          h('div', { className: 'ft-skel-line ft-skel-lg' }),
          h('div', { className: 'ft-skel-line ft-skel-md' }),
          h('div', { className: 'ft-skel-line ft-skel-sm' })
        )
      )
    );
  }

  // ── FullTracker (ACTIVE_FLIGHT state) ──

  function FullTracker(props) {
    var f = props.flight;
    var status = props.status;
    var liveUnavailable = props.liveUnavailable;
    var arrivalChanges = props.arrivalChanges || {};
    if (!f) return null;

    var route = parseRoute(f.route);
    var depCity = cityFor(route.dep);
    var arrCity = cityFor(route.arr);
    var depTz = tzFor(route.dep);
    var arrTz = tzFor(route.arr);
    var depTzAbbr = tzAbbr(depTz);
    var arrTzAbbr = tzAbbr(arrTz);

    var depTimeChanged = status && status.departure && status.departure.actual &&
      status.departure.actual !== status.departure.scheduled;
    var arrTimeChanged = status && status.arrival && status.arrival.actual &&
      status.arrival.actual !== status.arrival.scheduled;
    var isLate = status && (status.severity === 'delayed' || status.severity === 'late' || status.severity === 'cancelled');

    // Progress percentage
    var pct = 0;
    if (status) {
      var st = (status.status || '').toLowerCase();
      if (st.includes('landed') || st.includes('arrived')) {
        pct = 100;
      } else if (st.includes('active') || st.includes('en route') || st.includes('enroute') || st.includes('airborne') || st.includes('departed')) {
        var dep = status.departure;
        var arr = status.arrival;
        var depTime = dep && (dep.actual || dep.scheduled) ? new Date(dep.actual || dep.scheduled).getTime() : 0;
        var arrTime = arr && (arr.actual || arr.scheduled) ? new Date(arr.actual || arr.scheduled).getTime() : 0;
        var now = Date.now();
        if (depTime && arrTime && arrTime > depTime) {
          pct = Math.min(95, Math.max(5, Math.round((now - depTime) / (arrTime - depTime) * 100)));
        } else {
          pct = 50;
        }
      } else if (st.includes('boarding') || st.includes('gate')) {
        pct = 3;
      }
    }

    return h('div', { className: 'ft-card' + (status ? ' ft-card--loaded' : '') },
      h('div', { className: 'ft-full' },
        // Departure column
        h('div', null,
          h('div', { className: 'ft-airport' }, route.dep),
          depCity ? h('div', { className: 'ft-city' }, depCity) : null,
          h('div', { className: 'ft-time' + (depTimeChanged ? ' ft-time--changed' + (isLate ? ' ft-time--late' : '') : '') },
            h('span', { className: 'ft-time-scheduled' }, f.depart || ''),
            depTzAbbr ? h('span', { className: 'ft-tz-inline' }, ' ' + depTzAbbr) : null,
            depTimeChanged ? h('span', { className: 'ft-time-actual' }, ' ' + formatLocalTime(status.departure.actual)) : null
          ),
          // Show departure time in arrival timezone (small)
          depTz && arrTz && depTz !== arrTz && status && status.departure && (status.departure.actual || status.departure.scheduled) ?
            h('div', { className: 'ft-tz-alt' }, convertTimeToTz(status.departure.actual || status.departure.scheduled, arrTz)) : null,
          h('div', { className: 'ft-chips' },
            status && status.departure && status.departure.terminal ?
              h('span', { className: 'ft-terminal-tile' }, status.departure.terminal) : null,
            status && status.departure && status.departure.gate ?
              h('span', { className: 'ft-chip' }, h('i', { className: 'fa-solid fa-door-open' }), ' Gate ' + status.departure.gate) : null
          )
        ),

        // Centre route column
        h('div', { className: 'ft-route-col' },
          h('div', { className: 'ft-flight-num' }, f.flight || ''),
          h('div', { className: 'ft-route-line' },
            h('div', { className: 'ft-progress', style: { width: pct + '%' } }),
            h('i', {
              className: 'fa-solid fa-plane ft-plane-icon',
              style: { left: 'calc(' + Math.max(pct, 0) + '% - 12px)' }
            })
          ),
          h('div', { className: 'ft-meta-row' },
            f.seat ? h(React.Fragment, null, h('i', { className: 'fa-solid fa-chair' }), ' Seat ' + f.seat) : null
          ),
          status && status.aircraft ?
            h('div', { className: 'ft-aircraft' }, h('i', { className: 'fa-solid fa-plane-up' }), ' ' + status.aircraft) : null,
          status && isInFlight(status) && msToArrival(status) !== null ?
            h(ETABadge, { remaining: msToArrival(status), severity: status.severity }) :
            (status ? h(StatusBadge, { severity: status.severity, label: status.label }) :
              h(StatusBadge, { severity: 'loading', label: 'Checking\u2026' })),
          // "When to leave" — shown under ETA when airborne
          status && isInFlight(status) ?
            h(WhenToLeave, { status: status, flight: f }) : null,
          liveUnavailable ?
            h('div', { className: 'ft-live-unavailable' }, h('i', { className: 'fa-solid fa-wifi-weak' }), ' Live status unavailable') : null
        ),

        // Arrival column
        h('div', { className: 'ft-right' },
          h('div', { className: 'ft-airport' }, route.arr),
          arrCity ? h('div', { className: 'ft-city' }, arrCity) : null,
          h('div', { className: 'ft-time' + (arrTimeChanged ? ' ft-time--changed' + (isLate ? ' ft-time--late' : '') : '') },
            h('span', { className: 'ft-time-scheduled' }, f.arrive || ''),
            arrTzAbbr ? h('span', { className: 'ft-tz-inline' }, ' ' + arrTzAbbr) : null,
            arrTimeChanged ? h('span', { className: 'ft-time-actual' }, ' ' + formatLocalTime(status.arrival.actual)) : null
          ),
          // Show arrival time in departure timezone (small)
          depTz && arrTz && depTz !== arrTz && status && status.arrival && (status.arrival.actual || status.arrival.scheduled) ?
            h('div', { className: 'ft-tz-alt' }, convertTimeToTz(status.arrival.actual || status.arrival.scheduled, depTz)) : null,
          h('div', { className: 'ft-chips' },
            status && status.arrival && status.arrival.terminal ?
              h('span', { className: 'ft-terminal-tile' + (arrivalChanges.terminal ? ' ft-terminal-tile--changed' : '') },
                status.arrival.terminal) : null,
            status && status.arrival && status.arrival.gate ?
              h('span', { className: 'ft-chip' + (arrivalChanges.gate ? ' ft-chip--changed' : '') },
                h('i', { className: 'fa-solid fa-door-open' }), ' Gate ' + status.arrival.gate) : null,
            status && status.arrival && status.arrival.baggageBelt ?
              h('span', { className: 'ft-chip ft-chip--baggage' },
                h('i', { className: 'fa-solid fa-suitcase-rolling' }), ' Carousel ' + status.arrival.baggageBelt) : null
          )
        )
      )
    );
  }

  // ── CompactBar (PRE_TRIP, BETWEEN_FLIGHTS, COLLAPSED) ──

  function CompactBar(props) {
    var f = props.flight;
    var nextFlight = props.nextFlight;
    var state = props.state;
    if (!f) return null;

    var route = parseRoute(f.route);
    var icon, primary, secondary, badge;

    if (state === STATES.PRE_TRIP) {
      var days = daysUntil(f.date);
      icon = 'fa-solid fa-plane-departure';
      primary = '\u2708 ' + f.flight + ' \u00B7 ' + (f.route || '');
      secondary = f.depart ? f.date + ' \u00B7 ' + f.depart : f.date;
      badge = days !== null && days > 0 ? 'Departs in ' + formatDaysLabel(days) : null;
    } else if (state === STATES.COLLAPSED) {
      var nextDays = nextFlight ? daysUntil(nextFlight.date) : null;
      icon = 'fa-solid fa-plane-arrival';
      primary = '\u2708 Landed at ' + route.arr;
      secondary = nextFlight ? 'Return: ' + nextFlight.flight + ' \u00B7 ' + (nextFlight.route || '') : '';
      badge = nextDays !== null && nextDays > 0 ? nextDays + 'd' : null;
    } else {
      // BETWEEN_FLIGHTS
      var daysLeft = daysUntil(f.date);
      icon = 'fa-solid fa-clock';
      primary = (f.flight || '') + ' \u00B7 ' + (f.route || '');
      secondary = f.depart ? f.date + ' \u00B7 ' + f.depart : f.date;
      badge = daysLeft !== null && daysLeft > 0 ? 'In ' + daysLeft + 'd' : null;
    }

    return h('div', { className: 'ft-card ft-compact' },
      h('i', { className: icon + ' ft-compact-icon' }),
      h('div', { className: 'ft-compact-main' },
        h('div', { className: 'ft-compact-primary' }, primary),
        secondary ? h('div', { className: 'ft-compact-secondary' }, secondary) : null
      ),
      badge ? h('span', { className: 'ft-compact-badge' }, badge) : null
    );
  }

  // ── CheckInReminder ──

  function CheckInReminder(props) {
    var f = props.flight;
    if (!f) return null;

    var url = checkinUrl(f.flight);
    var route = parseRoute(f.route);

    return h('div', { className: 'ft-card ft-checkin' },
      h('i', { className: 'fa-solid fa-triangle-exclamation ft-checkin-icon' }),
      h('div', { className: 'ft-checkin-main' },
        h('div', { className: 'ft-checkin-label' }, 'Check in now'),
        h('div', { className: 'ft-checkin-flight' }, f.flight + ' \u00B7 ' + (f.route || '')),
        h('div', { className: 'ft-checkin-details' }, f.date + (f.depart ? ' \u00B7 ' + f.depart : ''))
      ),
      url ? h('a', {
        href: url,
        target: '_blank',
        rel: 'noopener noreferrer',
        className: 'ft-checkin-link'
      }, h('i', { className: 'fa-solid fa-arrow-up-right-from-square' }), ' Check In') : null
    );
  }

  // ── PostTrip ──

  function PostTrip(props) {
    var f = props.flight;
    var status = props.status;
    if (!f) return null;
    var route = parseRoute(f.route);
    var arrCity = cityFor(route.arr);
    var arrTime = '';
    if (status && status.arrival) {
      arrTime = status.arrival.actual ? formatLocalTime(status.arrival.actual) :
                status.arrival.scheduled ? formatLocalTime(status.arrival.scheduled) : '';
    }
    if (!arrTime && f.arrive) arrTime = f.arrive;

    return h('div', { className: 'ft-card ft-post' },
      h('i', { className: 'fa-solid fa-plane-arrival ft-post-icon' }),
      h('div', { className: 'ft-post-main' },
        h('div', { className: 'ft-post-primary' },
          h('span', { className: 'ft-post-flight' }, f.flight || ''),
          ' \u00B7 ',
          h('span', null, route.dep + ' \u2192 ' + route.arr)
        ),
        h('div', { className: 'ft-post-secondary' },
          'Arrived' + (arrCity ? ' ' + arrCity : '') + (arrTime ? ' at ' + arrTime : '') +
          (status && status.arrival && status.arrival.terminal ? ' \u00B7 Terminal ' + status.arrival.terminal : '')
        )
      ),
      h('span', { className: 'ft-post-badge' }, h('i', { className: 'fa-solid fa-circle-check' }), ' Complete')
    );
  }

  // ── StickyBar ──

  function StickyBar(props) {
    var visible = props.visible;
    var f = props.flight;
    var status = props.status;
    var onClickFn = props.onClick;

    if (!f) return null;

    return h('div', {
      className: 'ft-sticky-bar' + (visible ? ' ft-sticky-visible' : ''),
      onClick: onClickFn
    },
      h('i', { className: 'fa-solid fa-plane ft-sticky-icon' }),
      h('span', { className: 'ft-sticky-text' },
        f.flight + ' \u00B7 ' + (f.route || '') + (status ? ' \u00B7 ' + (f.arrive || '') : '')
      ),
      status && status.arrival && status.arrival.terminal ?
        h('span', { className: 'ft-sticky-chip' }, 'T' + status.arrival.terminal) : null,
      status && status.arrival && status.arrival.gate ?
        h('span', { className: 'ft-sticky-chip' }, 'Gate ' + status.arrival.gate) : null,
      status && isInFlight(status) && msToArrival(status) !== null ?
        h('span', { className: 'ft-sticky-eta' },
          h('i', { className: 'fa-solid fa-clock' }),
          ' ' + formatETA(msToArrival(status))
        ) :
        (status ? h('span', {
          className: 'ft-sticky-status ft-sticky-status--' + (status.severity || 'unknown')
        }, status.label || '') : null)
    );
  }

  // ── Main: FlightTracker ──

  function FlightTracker() {
    var flightsRef = useRef([]);
    var pollCountRef = useRef(0);
    var errorCountRef = useRef(0);
    var pollTimerRef = useRef(null);
    var activeFlightRef = useRef(null);

    var _fs = useState([]);
    var flights = _fs[0];
    var setFlights = _fs[1];

    var _ss = useState({});
    var liveStatuses = _ss[0];
    var setLiveStatuses = _ss[1];

    var _lu = useState(false);
    var liveUnavailable = _lu[0];
    var setLiveUnavailable = _lu[1];

    var _ac = useState({});
    var arrivalChanges = _ac[0];
    var setArrivalChanges = _ac[1];

    var _sv = useState(false);
    var stickyVisible = _sv[0];
    var setStickyVisible = _sv[1];

    // Track when each flight's data was last successfully fetched
    var _lf = useState({});
    var lastFetchedMap = _lf[0];
    var setLastFetchedMap = _lf[1];

    // Whether the first fetch has completed (for skeleton vs real data)
    var _ff = useState(false);
    var firstFetchDone = _ff[0];
    var setFirstFetchDone = _ff[1];

    var rootRef = useRef(null);

    // Load flights from __tripData
    var loadFlights = useCallback(function () {
      var trip = window.__tripData;
      if (!trip) return;
      var normalized = window.normalizeFlights(trip);
      flightsRef.current = normalized;
      setFlights(normalized);
    }, []);

    // Initial load + register __onTripRefresh
    useEffect(function () {
      loadFlights();
      window.__onTripRefresh = function () {
        loadFlights();
      };
      return function () {
        window.__onTripRefresh = null;
      };
    }, [loadFlights]);

    // Compute current state
    var stateResult = SM.computeFlightState(flights, liveStatuses);

    // Force tick counter — incremented by a timer to trigger re-render for collapse
    var _tick = useState(0);
    var setTick = _tick[1];

    // Auto-collapse timer: when a flight has landed, schedule a re-render
    // at the 1-hour mark so the state machine transitions to COLLAPSED
    useEffect(function () {
      var COLLAPSE_DELAY = 3600000; // 1 hour
      var timers = [];
      Object.keys(liveStatuses).forEach(function (id) {
        var s = liveStatuses[id];
        if (s && s.landed && s.landedAt) {
          var elapsed = Date.now() - s.landedAt;
          var remaining = COLLAPSE_DELAY - elapsed;
          if (remaining > 0 && remaining < COLLAPSE_DELAY) {
            var t = setTimeout(function () { setTick(function (n) { return n + 1; }); }, remaining + 500);
            timers.push(t);
          }
        }
      });
      return function () { timers.forEach(clearTimeout); };
    }, [liveStatuses]);
    var widgetState = stateResult.state;
    var activeFlight = stateResult.flight;
    var nextFlight = stateResult.nextFlight;
    activeFlightRef.current = activeFlight;

    // Real-time tick: re-render every 10s during active flight
    // Drives smooth ETA countdown, progress bar, and live indicator updates
    useEffect(function () {
      if (widgetState !== STATES.ACTIVE_FLIGHT) return;
      var interval = setInterval(function () { setTick(function (n) { return n + 1; }); }, 10000);
      return function () { clearInterval(interval); };
    }, [widgetState]);

    // Fetch live status for a single flight
    var fetchStatus = useCallback(function (f) {
      if (!f || !f.flight) return Promise.resolve();
      var id = flightId(f);
      var apiBase = window.__API_BASE || '';
      var url = apiBase + '/api/flight-status?flight=' + encodeURIComponent(id);
      if (f.date) url += '&date=' + encodeURIComponent(f.date);

      return fetch(url, { credentials: 'include' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (!data.ok) {
            errorCountRef.current++;
            if (errorCountRef.current >= CIRCUIT_BREAKER_THRESHOLD) {
              setLiveUnavailable(true);
            }
            return;
          }
          if (data.configured === false) return;
          errorCountRef.current = 0;
          setLiveUnavailable(false);

          // Gate / Terminal change detection for arrival
          var fid = flightId(f);
          var prev = _prevArrivalInfo[fid];
          var arrData = data.arrival || {};
          var newTerminal = arrData.terminal || null;
          var newGate = arrData.gate || null;
          var newBaggage = arrData.baggageBelt || null;

          if (prev) {
            var termChanged = prev.terminal && newTerminal && prev.terminal !== newTerminal;
            var gateChanged = prev.gate && newGate && prev.gate !== newGate;
            var baggageChanged = prev.baggageBelt && newBaggage && prev.baggageBelt !== newBaggage;
            if (termChanged || gateChanged || baggageChanged) {
              var changes = {};
              var alertParts = [];
              if (termChanged) {
                changes.terminal = true;
                alertParts.push('Terminal changed: T' + prev.terminal + ' \u2192 T' + newTerminal);
              }
              if (gateChanged) {
                changes.gate = true;
                alertParts.push('Gate changed: ' + prev.gate + ' \u2192 ' + newGate);
              }
              if (baggageChanged) {
                changes.baggageBelt = true;
                alertParts.push('Baggage carousel changed: ' + prev.baggageBelt + ' \u2192 ' + newBaggage);
              }
              setArrivalChanges(function (ac) {
                var next = Object.assign({}, ac);
                next[fid] = changes;
                return next;
              });
              // Fire toast alert
              if (window.notify) {
                window.notify.warning(
                  '\u2708\uFE0F ' + (f.flight || '') + ' \u2014 ' + alertParts.join(' \u00B7 '),
                  { duration: 15000 }
                );
              }
            }
          }
          _prevArrivalInfo[fid] = { terminal: newTerminal, gate: newGate, baggageBelt: newBaggage };

          setLiveStatuses(function (prev) {
            var next = Object.assign({}, prev);
            var landed = (data.status || '').toLowerCase();
            var isLanded = landed.includes('landed') || landed.includes('arrived');
            var prevEntry = prev[id];
            // Preserve original landedAt timestamp once set
            var landedAt = (prevEntry && prevEntry.landedAt) ? prevEntry.landedAt :
                           (isLanded ? Date.now() : null);
            next[id] = Object.assign({}, data, {
              landed: isLanded,
              landedAt: landedAt
            });
            return next;
          });
          // Record fetch timestamp for stale detection
          setLastFetchedMap(function (prev) {
            var next = Object.assign({}, prev);
            next[id] = Date.now();
            return next;
          });
          if (!firstFetchDone) setFirstFetchDone(true);
        })
        .catch(function () {
          errorCountRef.current++;
          if (errorCountRef.current >= CIRCUIT_BREAKER_THRESHOLD) {
            setLiveUnavailable(true);
          }
        });
    }, []);

    // Adaptive polling with Page Visibility API
    useEffect(function () {
      if (widgetState === STATES.HIDDEN || widgetState === STATES.POST_TRIP) return;
      if (liveUnavailable) return;

      function poll() {
        if (pollCountRef.current >= MAX_POLLS_PER_SESSION) return;
        // Skip polling when tab is hidden to conserve API budget
        if (document.hidden) {
          pollTimerRef.current = setTimeout(poll, 30000);
          return;
        }

        pollCountRef.current++;
        var currentFlights = flightsRef.current;
        // Only fetch active flight to conserve API quota (halves calls for multi-leg trips)
        var active = activeFlightRef.current;
        var toFetch = active ? [active] : currentFlights.slice(0, 1);

        var promises = toFetch.map(function (f) {
          return fetchStatus(f);
        });

        Promise.all(promises).then(function () {
          if (liveUnavailable) return;
          var interval = SM.getPollingInterval(currentFlights);
          if (interval) {
            pollTimerRef.current = setTimeout(poll, interval);
          }
        });
      }

      // Initial fetch
      poll();

      // Poll immediately when tab becomes visible (data may be stale)
      function onVisChange() {
        if (!document.hidden && pollTimerRef.current) {
          clearTimeout(pollTimerRef.current);
          pollTimerRef.current = null;
          poll();
        }
      }
      document.addEventListener('visibilitychange', onVisChange);

      return function () {
        if (pollTimerRef.current) {
          clearTimeout(pollTimerRef.current);
          pollTimerRef.current = null;
        }
        document.removeEventListener('visibilitychange', onVisChange);
      };
    }, [widgetState, liveUnavailable, fetchStatus]);

    // IntersectionObserver for sticky bar
    useEffect(function () {
      if (widgetState !== STATES.ACTIVE_FLIGHT) {
        setStickyVisible(false);
        return;
      }
      var el = rootRef.current;
      if (!el || typeof IntersectionObserver === 'undefined') return;

      var observer = new IntersectionObserver(function (entries) {
        // When the widget scrolls out of view, show sticky bar
        setStickyVisible(!entries[0].isIntersecting);
      }, { threshold: 0 });

      observer.observe(el);
      return function () { observer.disconnect(); };
    }, [widgetState]);

    function scrollToWidget() {
      var el = rootRef.current;
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Don't render anything if hidden
    if (widgetState === STATES.HIDDEN) return null;

    var activeId = activeFlight ? flightId(activeFlight) : '';
    var activeStatus = liveStatuses[activeId] || null;

    var widgetContent;
    switch (widgetState) {
      case STATES.ACTIVE_FLIGHT:
        // Show skeleton while waiting for first API response
        if (!firstFetchDone && !activeStatus) {
          widgetContent = h(SkeletonCard);
        } else {
          widgetContent = h(React.Fragment, null,
            h(LiveIndicator, { lastFetched: lastFetchedMap[activeId] || null }),
            h(FullTracker, {
              flight: activeFlight,
              status: activeStatus,
              liveUnavailable: liveUnavailable,
              arrivalChanges: arrivalChanges[activeId] || {}
            })
          );
        }
        break;
      case STATES.PRE_TRIP:
        widgetContent = h(CompactBar, { flight: activeFlight, state: widgetState });
        break;
      case STATES.COLLAPSED:
        widgetContent = h(CompactBar, { flight: activeFlight, nextFlight: nextFlight, state: widgetState });
        break;
      case STATES.BETWEEN_FLIGHTS:
        widgetContent = h(CompactBar, { flight: activeFlight, state: widgetState });
        break;
      case STATES.CHECK_IN_REMINDER:
        widgetContent = h(CheckInReminder, { flight: activeFlight });
        break;
      case STATES.POST_TRIP:
        widgetContent = h(PostTrip, { flight: activeFlight, status: activeStatus });
        break;
      default:
        widgetContent = null;
    }

    // Determine severity for root-level styling
    // Default to 'on-time' when in active-flight state but API hasn't responded yet
    var rootSeverity;
    if (activeStatus) {
      rootSeverity = activeStatus.severity || 'on-time';
    } else if (widgetState === STATES.ACTIVE_FLIGHT) {
      rootSeverity = 'on-time';
    } else if (widgetState === STATES.CHECK_IN_REMINDER) {
      rootSeverity = 'delayed';
    } else if (widgetState === STATES.PRE_TRIP || widgetState === STATES.BETWEEN_FLIGHTS) {
      rootSeverity = 'pre-trip';
    } else {
      rootSeverity = 'unknown';
    }

    return h('div', { className: 'ft-root', ref: rootRef, 'data-severity': rootSeverity },
      widgetContent,
      widgetState === STATES.ACTIVE_FLIGHT ?
        h(StickyBar, {
          visible: stickyVisible,
          flight: activeFlight,
          status: activeStatus,
          onClick: scrollToWidget
        }) : null
    );
  }

  // ── Mount ──

  function mount() {
    var el = document.getElementById('flight-tracker-root');
    if (!el) return;
    // Wait for React (loaded by tweaker-loader)
    function tryMount() {
      if (!window.React || !window.ReactDOM) {
        setTimeout(tryMount, 50);
        return;
      }
      h = React.createElement;
      useState = React.useState;
      useEffect = React.useEffect;
      useRef = React.useRef;
      useCallback = React.useCallback;
      var root = ReactDOM.createRoot(el);
      root.render(h(FlightTracker));
    }
    tryMount();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();
