import type { Config } from 'tailwindcss'

// CORTEX-aligned design tokens. See site/operator-review/src/index.css
// for the corresponding CSS custom properties and reader-theme variants.
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        ui: ['"Plus Jakarta Sans"', 'Inter', 'system-ui', 'sans-serif'],
        display: ['"Space Grotesk"', '"Plus Jakarta Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
        reader: ['Lato', 'system-ui', 'sans-serif'],
        serif: ['"Cormorant Garamond"', 'Lora', 'Georgia', 'serif'],
      },
      colors: {
        canvas: { DEFAULT: '#080b14', alt: '#0d111d', elevated: '#131725' },
        ink: {
          50: '#f8fafc', 100: '#cbd5e1', 200: '#94a3b8',
          300: '#64748b', 400: '#475569', 500: '#334155',
          600: '#1e293b', 700: '#0f172a',
        },
        accent: {
          cyan: '#00d4ff',
          purple: '#7b61ff',
          'purple-deep': '#5a3fd9',
          'purple-soft': '#a78bfa',
          magenta: '#ba55d3',
          emerald: '#10b981',
          rose: '#f43f5e',
          amber: '#f59e0b',
          sky: '#38bdf8',
        },
      },
      borderRadius: {
        pill: '9999px',
      },
      keyframes: {
        'cortex-pulse': {
          '0%, 100%': { boxShadow: '0 0 6px rgba(167,139,250,0.85)', opacity: '1' },
          '50%': { boxShadow: '0 0 16px rgba(167,139,250,1), 0 0 22px rgba(123,97,255,0.55)', opacity: '0.85' },
        },
        'eye-blink': {
          '0%, 92%, 100%': { transform: 'scaleY(1)' },
          '95%': { transform: 'scaleY(0.12)' },
        },
        'scan': {
          '0%': { left: '-60%' },
          '100%': { left: '110%' },
        },
      },
      animation: {
        'cortex-pulse': 'cortex-pulse 2s ease-in-out infinite',
        'eye-blink': 'eye-blink 4s ease-in-out infinite',
        'scan': 'scan 2.4s linear infinite',
      },
    },
  },
  plugins: [],
} satisfies Config
