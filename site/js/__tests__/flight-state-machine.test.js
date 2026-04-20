// flight-state-machine.test.js — Node built-in test runner
// Run: node --test site/js/__tests__/flight-state-machine.test.js

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

globalThis.window = globalThis.window || {};
await import('../flight-state-machine.js');
const { STATES, computeFlightState, getPollingInterval } = globalThis.window.flightStateMachine;

const FLIGHTS_2LEG = [
  { flight: 'UA 147', route: 'LHR → EWR', date: '2026-04-20', depart: '12:00 PM BST', arrive: '2:55 PM ET', seat: '34D', direction: 'inbound', leg: 1 },
  { flight: 'UA 16', route: 'EWR → LHR', date: '2026-04-28', depart: '5:25 PM ET', arrive: '5:55 AM +1', seat: '33D', direction: 'outbound', leg: 2 }
];

describe('computeFlightState', () => {

  it('returns HIDDEN for empty / no flights', () => {
    assert.equal(computeFlightState([]).state, STATES.HIDDEN);
    assert.equal(computeFlightState(null).state, STATES.HIDDEN);
    assert.equal(computeFlightState(undefined).state, STATES.HIDDEN);
  });

  it('PRE_TRIP: 3 days before first flight', () => {
    const now = new Date('2026-04-17T10:00:00');
    const result = computeFlightState(FLIGHTS_2LEG, {}, now);
    assert.equal(result.state, STATES.PRE_TRIP);
    assert.equal(result.flight.flight, 'UA 147');
  });

  it('ACTIVE_FLIGHT: day of first flight', () => {
    const now = new Date('2026-04-20T14:00:00');
    const result = computeFlightState(FLIGHTS_2LEG, {}, now);
    assert.equal(result.state, STATES.ACTIVE_FLIGHT);
    assert.equal(result.flight.flight, 'UA 147');
  });

  it('COLLAPSED: first flight landed, next >48h away, within 24h of landing', () => {
    const now = new Date('2026-04-20T20:00:00');
    const statuses = { UA147: { landed: true } };
    const result = computeFlightState(FLIGHTS_2LEG, statuses, now);
    assert.equal(result.state, STATES.COLLAPSED);
    assert.equal(result.flight.flight, 'UA 147');
    assert.equal(result.nextFlight.flight, 'UA 16');
  });

  it('BETWEEN_FLIGHTS: between flights, >48h to next', () => {
    const now = new Date('2026-04-23T12:00:00');
    const result = computeFlightState(FLIGHTS_2LEG, {}, now);
    assert.equal(result.state, STATES.BETWEEN_FLIGHTS);
    assert.equal(result.flight.flight, 'UA 16');
  });

  it('CHECK_IN_REMINDER: 24-48h before next flight', () => {
    const now = new Date('2026-04-27T08:00:00');
    const result = computeFlightState(FLIGHTS_2LEG, {}, now);
    assert.equal(result.state, STATES.CHECK_IN_REMINDER);
    assert.equal(result.flight.flight, 'UA 16');
  });

  it('ACTIVE_FLIGHT: day of second flight', () => {
    const now = new Date('2026-04-28T16:00:00');
    const result = computeFlightState(FLIGHTS_2LEG, {}, now);
    assert.equal(result.state, STATES.ACTIVE_FLIGHT);
    assert.equal(result.flight.flight, 'UA 16');
  });

  it('POST_TRIP: all flights completed', () => {
    const now = new Date('2026-04-30T10:00:00');
    const result = computeFlightState(FLIGHTS_2LEG, {}, now);
    assert.equal(result.state, STATES.POST_TRIP);
    assert.equal(result.flight.flight, 'UA 16');
    assert.equal(result.nextFlight, null);
  });

  it('single-flight trip on flight day → ACTIVE_FLIGHT', () => {
    const single = [{ flight: 'BA 117', date: '2026-04-20', leg: 1 }];
    const now = new Date('2026-04-20T08:00:00');
    const result = computeFlightState(single, {}, now);
    assert.equal(result.state, STATES.ACTIVE_FLIGHT);
  });

  it('HIDDEN for no-flight trip', () => {
    assert.equal(computeFlightState([]).state, STATES.HIDDEN);
  });
});

describe('getPollingInterval', () => {

  it('returns null for empty flights', () => {
    assert.equal(getPollingInterval([]), null);
  });

  it('returns null when >48h from any flight', () => {
    const now = new Date('2026-04-15T10:00:00');
    assert.equal(getPollingInterval(FLIGHTS_2LEG, now), null);
  });

  it('returns 30min in check-in window (24-48h)', () => {
    const now = new Date('2026-04-18T12:00:00'); // 36h before Apr 20 midnight
    assert.equal(getPollingInterval(FLIGHTS_2LEG, now), 30 * 60 * 1000);
  });

  it('returns 5min when 2-24h before flight', () => {
    const now = new Date('2026-04-19T14:00:00');
    assert.equal(getPollingInterval(FLIGHTS_2LEG, now), 5 * 60 * 1000);
  });

  it('returns 2min when <2h before flight', () => {
    const now = new Date('2026-04-19T23:00:00');
    assert.equal(getPollingInterval(FLIGHTS_2LEG, now), 2 * 60 * 1000);
  });

  it('returns 3min when in-flight', () => {
    const now = new Date('2026-04-20T14:00:00');
    assert.equal(getPollingInterval(FLIGHTS_2LEG, now), 3 * 60 * 1000);
  });
});
