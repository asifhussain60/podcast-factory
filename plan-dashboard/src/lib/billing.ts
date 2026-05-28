/**
 * Billing utility — cost roll-up helpers for infrastructure snapshot data.
 * Used by overview.astro, infrastructure.astro, and any page showing spend.
 */

interface ServiceRecord {
  month_cost_usd?: number;
  [key: string]: unknown;
}

interface VendorRecord {
  services?: ServiceRecord[];
  [key: string]: unknown;
}

/** Sum all service costs for a single vendor. */
export function sumVendorCost(vendor: VendorRecord): number {
  return (vendor.services ?? []).reduce(
    (s, svc) => s + (svc.month_cost_usd ?? 0),
    0,
  );
}

/** Sum all service costs across all vendors. */
export function sumAllVendorCosts(vendors: VendorRecord[]): number {
  return vendors.reduce((total, v) => total + sumVendorCost(v), 0);
}

/** Sum an arbitrary numeric field across all vendor services. */
export function sumAllVendorField(
  vendors: VendorRecord[],
  field: string,
): number {
  return vendors.reduce(
    (total, v) =>
      total +
      (v.services ?? []).reduce(
        (s, svc) => s + ((svc[field] as number) ?? 0),
        0,
      ),
    0,
  );
}
