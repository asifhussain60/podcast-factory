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

  // ── StatusBadge ──

  function StatusBadge(props) {
    var severity = props.severity || 'loading';
    var label = props.label || 'Checking\u2026';
    return h('div', { className: 'ft-status ft-status--' + severity },
      h('span', { className: 'ft-status-dot' }),
      ' ' + label
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
      } else if (st.includes('active') || st.includes('en route') || st.includes('airborne')) {
        var dep = status.departure;
        var arr = status.arrival;
        var depTime = dep && (dep.actual || dep.scheduled) ? new Date(dep.actual || dep.scheduled).getTime() : 0;
        var arrTime = arr && arr.scheduled ? new Date(arr.scheduled).getTime() : 0;
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

    return h('div', { className: 'ft-card' },
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
          status ? h(StatusBadge, { severity: status.severity, label: status.label }) :
            h(StatusBadge, { severity: 'loading', label: 'Checking\u2026' }),
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
    if (!f) return null;
    var route = parseRoute(f.route);

    return h('div', { className: 'ft-card ft-post' },
      h('i', { className: 'fa-solid fa-plane-arrival ft-post-icon' }),
      h('span', { className: 'ft-post-text' },
        '\u2708 Trip complete \u00B7 Arrived ' + route.arr + (f.arrive ? ' ' + f.arrive : ''))
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
      status ? h('span', {
        className: 'ft-sticky-status ft-sticky-status--' + (status.severity || 'unknown')
      }, status.label || '') : null
    );
  }

  // ── Main: FlightTracker ──

  function FlightTracker() {
    var flightsRef = useRef([]);
    var pollCountRef = useRef(0);
    var errorCountRef = useRef(0);
    var pollTimerRef = useRef(null);

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
    var widgetState = stateResult.state;
    var activeFlight = stateResult.flight;
    var nextFlight = stateResult.nextFlight;

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
            next[id] = Object.assign({}, data, {
              landed: landed.includes('landed') || landed.includes('arrived')
            });
            return next;
          });
        })
        .catch(function () {
          errorCountRef.current++;
          if (errorCountRef.current >= CIRCUIT_BREAKER_THRESHOLD) {
            setLiveUnavailable(true);
          }
        });
    }, []);

    // Adaptive polling
    useEffect(function () {
      if (widgetState === STATES.HIDDEN || widgetState === STATES.POST_TRIP) return;
      if (liveUnavailable) return;

      function poll() {
        if (pollCountRef.current >= MAX_POLLS_PER_SESSION) return;
        pollCountRef.current++;

        var currentFlights = flightsRef.current;
        // Fetch status for all non-completed flights
        var promises = currentFlights.map(function (f) {
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

      return function () {
        if (pollTimerRef.current) {
          clearTimeout(pollTimerRef.current);
          pollTimerRef.current = null;
        }
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
        widgetContent = h(FullTracker, {
          flight: activeFlight,
          status: activeStatus,
          liveUnavailable: liveUnavailable,
          arrivalChanges: arrivalChanges[activeId] || {}
        });
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
        widgetContent = h(PostTrip, { flight: activeFlight });
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
