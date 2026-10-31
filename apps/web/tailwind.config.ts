import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class', '[data-theme="dusk"]'],
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './lib/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)',
        'surface-1': 'var(--surface-1)',
        'surface-2': 'var(--surface-2)',
        'surface-3': 'var(--surface-3)',
        border: 'var(--border)',
        text: 'var(--text)',
        'text-muted': 'var(--text-muted)',
        brand: 'var(--brand)',
        'brand-2': 'var(--brand-2)',
        sky: 'var(--sky)',
        amber: 'var(--amber)',
        rose: 'var(--rose)',
        flame: 'var(--flame)',
        mint: 'var(--mint)',
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
        display: ['var(--font-display)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'monospace'],
        pixel: ['var(--font-pixel)', 'monospace'],
        devanagari: ['var(--font-devanagari)', 'sans-serif'],
        kannada: ['var(--font-kannada)', 'sans-serif'],
        tamil: ['var(--font-tamil)', 'sans-serif'],
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
        pill: '9999px',
      },
      transitionDuration: {
        instant: 'var(--dur-instant)',
        fast: 'var(--dur-fast)',
        base: 'var(--dur-base)',
        slow: 'var(--dur-slow)',
        epic: 'var(--dur-epic)',
      },
      transitionTimingFunction: {
        out: 'var(--ease-out)',
        'in-out': 'var(--ease-in-out)',
        in: 'var(--ease-in)',
      },
      backgroundImage: {
        aurora: 'var(--aurora)',
      },
      boxShadow: {
        card: 'var(--shadow-card)',
      },
      animation: {
        drift: 'drift 40s linear infinite',
        shimmer: 'shimmer 6s infinite linear',
      },
    },
  },
  plugins: [],
};

export default config;
