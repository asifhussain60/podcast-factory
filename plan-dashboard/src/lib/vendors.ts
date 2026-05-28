/**
 * Vendor identity constants — single source of truth for vendor IDs
 * used in PipelineSpine, VendorLogo, infrastructure.astro, and SpendChart.
 */

export const VENDOR_IDS = {
  ANTHROPIC:   'anthropic',
  AZURE:       'azure',
  GOOGLE:      'google',
  GITHUB:      'github',
  NOTEBOOKLM:  'notebooklm',
  INTERNAL:    'internal',
} as const;

export type VendorId = typeof VENDOR_IDS[keyof typeof VENDOR_IDS];
