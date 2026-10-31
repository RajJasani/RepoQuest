import {
  Bricolage_Grotesque,
  Inter,
  JetBrains_Mono,
  Silkscreen,
  Noto_Sans_Devanagari,
  Noto_Sans_Kannada,
  Noto_Sans_Tamil,
} from 'next/font/google';

export const fontDisplay = Bricolage_Grotesque({
  weight: ['700', '800'],
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
  fallback: ['system-ui', 'sans-serif'],
});

export const fontSans = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
  fallback: ['system-ui', 'sans-serif'],
});

export const fontMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
  fallback: ['ui-monospace', 'monospace'],
});

export const fontPixel = Silkscreen({
  weight: '400',
  subsets: ['latin'],
  variable: '--font-pixel',
  display: 'swap',
  fallback: ['monospace'],
});

export const fontDevanagari = Noto_Sans_Devanagari({
  subsets: ['devanagari'],
  variable: '--font-devanagari',
  display: 'swap',
  fallback: ['sans-serif'],
});

export const fontKannada = Noto_Sans_Kannada({
  subsets: ['kannada'],
  variable: '--font-kannada',
  display: 'swap',
  fallback: ['sans-serif'],
});

export const fontTamil = Noto_Sans_Tamil({
  subsets: ['tamil'],
  variable: '--font-tamil',
  display: 'swap',
  fallback: ['sans-serif'],
});

export const fontVariables = [
  fontDisplay.variable,
  fontSans.variable,
  fontMono.variable,
  fontPixel.variable,
  fontDevanagari.variable,
  fontKannada.variable,
  fontTamil.variable,
].join(' ');

