// normalize-flights.test.js — Node built-in test runner
// Run: node --test site/js/__tests__/normalize-flights.test.js

import { describe, it } from 'node:test';
import assert from 'node:assert/strict';

// Shim window for the IIFE
globalThis.window = globalThis.window || {};
await import('../normalize-flights.js');
const { normalizeFlights } = globalThis.window;

describe('normalizeFlights', () => {

  it('returns [] for undefined / null / missing flights', () => {
    assert.deepStrictEqual(normalizeFlights(undefined), []);
    assert.deepStrictEqual(normalizeFlights(null), []);
    assert.deepStrictEqual(normalizeFlights({}), []);
    assert.deepStrictEqual(normalizeFlights({ flights: null }), []);
    assert.deepStrictEqual(normalizeFlights({ flights: undefined }), []);
  });

  it('normalizes old object format { inbound, outbound }', () => {
    const trip = {
      flights: {
        inbound: { flight: 'UA 147', route: 'LHR → EWR', date: '2026-04-20', depart: '12:00 PM BST', arrive: '2:55 PM ET', seat: '34D' },
        outbound: { flight: 'UA 16', route: 'EWR → LHR', date: '2026-04-28', depart: '5:25 PM ET', arrive: '5:55 AM +1', seat: '33D' }
      }
    };
    const result = normalizeFlights(trip);
    assert.equal(result.length, 2);
    assert.equal(result[0].flight, 'UA 147');
    assert.equal(result[0].direction, 'inbound');
    assert.equal(result[0].leg, 1);
    assert.equal(result[0].seat, '34D');
    assert.equal(result[1].flight, 'UA 16');
    assert.equal(result[1].direction, 'outbound');
    assert.equal(result[1].leg, 2);
  });

  it('normalizes single inbound only', () => {
    const trip = {
      flights: {
        inbound: { flight: 'BA 117', route: 'LHR → JFK', date: '2026-05-01' }
      }
    };
    const result = normalizeFlights(trip);
    assert.equal(result.length, 1);
    assert.equal(result[0].flight, 'BA 117');
    assert.equal(result[0].direction, 'inbound');
    assert.equal(result[0].leg, 1);
    assert.equal(result[0].seat, null);
  });

  it('normalizes ingest array format [{ airline, departure, arrival, date }]', () => {
    const trip = {
      flights: [
        { airline: 'UA 147', departure: 'LHR', arrival: 'EWR', date: '2026-04-20' }
      ]
    };
    const result = normalizeFlights(trip);
    assert.equal(result.length, 1);
    assert.equal(result[0].flight, 'UA 147');
    assert.equal(result[0].depart, 'LHR');
    assert.equal(result[0].arrive, 'EWR');
    assert.equal(result[0].route, 'LHR → EWR');
    assert.equal(result[0].leg, 1);
  });

  it('passes through new array format', () => {
    const flights = [
      { flight: 'UA 147', route: 'LHR → EWR', date: '2026-04-20', depart: '12:00 PM BST', arrive: '2:55 PM ET', seat: '34D', direction: 'inbound', leg: 1 },
      { flight: 'UA 16', route: 'EWR → LHR', date: '2026-04-28', depart: '5:25 PM ET', arrive: '5:55 AM +1', seat: '33D', direction: 'outbound', leg: 2 }
    ];
    const result = normalizeFlights({ flights });
    assert.equal(result.length, 2);
    assert.equal(result[0].flight, 'UA 147');
    assert.equal(result[0].direction, 'inbound');
    assert.equal(result[0].leg, 1);
    assert.equal(result[1].flight, 'UA 16');
    assert.equal(result[1].leg, 2);
  });

  it('defaults missing optional fields in new array format', () => {
    const trip = {
      flights: [
        { flight: 'UA 147', date: '2026-04-20' }
      ]
    };
    const result = normalizeFlights(trip);
    assert.equal(result.length, 1);
    assert.equal(result[0].flight, 'UA 147');
    assert.equal(result[0].seat, null);
    assert.equal(result[0].direction, null);
    assert.equal(result[0].leg, 1);
    assert.equal(result[0].route, null);
  });

  it('handles empty object flights', () => {
    assert.deepStrictEqual(normalizeFlights({ flights: {} }), []);
  });

  it('handles empty array flights', () => {
    assert.deepStrictEqual(normalizeFlights({ flights: [] }), []);
  });
});
