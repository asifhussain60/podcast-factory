import { type VendorId } from '../lib/vendors';

type VendorLogoId = VendorId | 'source' | 'output';

interface Props {
  vendor: VendorLogoId;
  size?: number;
}

export default function VendorLogo({ vendor, size = 36 }: Props) {
  const sizeClass = size >= 40 ? 'vendor-logo is-lg' : 'vendor-logo is-md';
  switch (vendor) {
    case 'anthropic':
      return (
        <svg className={sizeClass} viewBox="0 0 48 48" role="img" aria-labelledby="vendor-logo-anthropic-title vendor-logo-anthropic-desc">
          <title id="vendor-logo-anthropic-title">Anthropic</title>
          <desc id="vendor-logo-anthropic-desc">Anthropic vendor logo.</desc>
          <rect width="48" height="48" rx="10" className="logo-bg-anthropic" />
          <path d="M16 34 L24 14 L32 34 M19.5 26 L28.5 26" className="logo-mark-anthropic" />
        </svg>
      );
    case 'google':
      return (
        <svg className={sizeClass} viewBox="0 0 48 48" role="img" aria-labelledby="vendor-logo-google-title vendor-logo-google-desc">
          <title id="vendor-logo-google-title">Google</title>
          <desc id="vendor-logo-google-desc">Google vendor logo.</desc>
          <rect width="48" height="48" rx="10" className="logo-bg-google" />
          <path d="M30 19 A 9 9 0 1 0 33 26 L24 26" className="logo-mark-google" />
        </svg>
      );
    case 'azure':
      return (
        <svg className={sizeClass} viewBox="0 0 48 48" role="img" aria-labelledby="vendor-logo-azure-title vendor-logo-azure-desc">
          <title id="vendor-logo-azure-title">Microsoft Azure</title>
          <desc id="vendor-logo-azure-desc">Microsoft Azure vendor logo.</desc>
          <rect width="48" height="48" rx="10" className="logo-bg-azure" />
          <rect x="13" y="13" width="10" height="10" className="logo-tile-1" />
          <rect x="25" y="13" width="10" height="10" className="logo-tile-2" />
          <rect x="13" y="25" width="10" height="10" className="logo-tile-3" />
          <rect x="25" y="25" width="10" height="10" className="logo-tile-4" />
        </svg>
      );
    case 'notebooklm':
      return (
        <svg className={sizeClass} viewBox="0 0 48 48" role="img" aria-labelledby="vendor-logo-notebooklm-title vendor-logo-notebooklm-desc">
          <title id="vendor-logo-notebooklm-title">NotebookLM</title>
          <desc id="vendor-logo-notebooklm-desc">NotebookLM vendor logo.</desc>
          <rect width="48" height="48" rx="10" className="logo-bg-notebooklm" />
          <path d="M14 18 Q14 14 18 14 L24 14 L24 34 L18 34 Q14 34 14 30 Z" className="logo-mark-notebooklm" />
          <path d="M34 18 Q34 14 30 14 L24 14 L24 34 L30 34 Q34 34 34 30 Z" className="logo-mark-notebooklm" />
          <path d="M32 11 L33 8 L34 11 L37 12 L34 13 L33 16 L32 13 L29 12 Z" className="logo-spark" />
        </svg>
      );
    case 'github':
      return (
        <svg className={sizeClass} viewBox="0 0 48 48" role="img" aria-labelledby="vendor-logo-github-title vendor-logo-github-desc">
          <title id="vendor-logo-github-title">GitHub</title>
          <desc id="vendor-logo-github-desc">GitHub vendor logo.</desc>
          <rect width="48" height="48" rx="10" className="logo-bg-github" />
          <path d="M24 12 A 12 12 0 0 0 20 35 V31 Q16 32 15 28 Q14 26 12 25 Q15 25 16 28 Q18 30 21 29 V27 Q15 26 15 21 Q15 19 16 17 Q16 14 17 14 Q19 14 20 16 Q22 15 24 15 Q26 15 28 16 Q29 14 31 14 Q32 14 32 17 Q33 19 33 21 Q33 26 27 27 V30 Q27 32 28 33 V36 A 12 12 0 0 0 24 12 Z" className="logo-mark-github" />
        </svg>
      );
    case 'source':
      return (
        <svg className={sizeClass} viewBox="0 0 48 48" role="img" aria-labelledby="vendor-logo-source-title vendor-logo-source-desc">
          <title id="vendor-logo-source-title">Source PDF</title>
          <desc id="vendor-logo-source-desc">Source PDF logo.</desc>
          <rect width="48" height="48" rx="10" className="logo-bg-source" />
          <path d="M16 12 L28 12 L34 18 L34 36 L16 36 Z" className="logo-mark-source" />
          <path d="M28 12 L28 18 L34 18" className="logo-mark-source-fold" />
          <text x="24" y="30" textAnchor="middle" className="logo-source-tag">PDF</text>
        </svg>
      );
    case 'output':
      return (
        <svg className={sizeClass} viewBox="0 0 48 48" role="img" aria-labelledby="vendor-logo-output-title vendor-logo-output-desc">
          <title id="vendor-logo-output-title">Published podcast</title>
          <desc id="vendor-logo-output-desc">Published podcast logo.</desc>
          <rect width="48" height="48" rx="10" className="logo-bg-output" />
          <circle cx="24" cy="22" r="6" className="logo-mark-output-head" />
          <path d="M14 38 Q14 30 24 30 Q34 30 34 38" className="logo-mark-output-body" />
          <path d="M36 18 Q40 22 36 26" className="logo-mark-output-wave" />
          <path d="M39 14 Q45 22 39 30" className="logo-mark-output-wave" />
        </svg>
      );
  }
}
