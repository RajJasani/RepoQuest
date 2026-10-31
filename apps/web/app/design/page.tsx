'use client';

import { useTheme } from 'next-themes';
import { useCalmMode } from '@/lib/calm';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { fadeUp, spring } from '@/lib/motion';

export default function DesignPage() {
  const { theme, setTheme } = useTheme();
  const { calm, setCalm } = useCalmMode();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return <div className="min-h-screen bg-bg p-8" />;
  }

  const surfaceTokens = [
    { name: 'bg', token: 'var(--bg)', label: 'App Background' },
    { name: 'surface-1', token: 'var(--surface-1)', label: 'Cards, Sidebar' },
    { name: 'surface-2', token: 'var(--surface-2)', label: 'Raised Cards, Popovers' },
    { name: 'surface-3', token: 'var(--surface-3)', label: 'Hover, Inputs' },
  ];

  const brandTokens = [
    { name: 'brand', token: 'var(--brand)', label: 'Primary Actions, Links' },
    { name: 'brand-2', token: 'var(--brand-2)', label: 'Gradient, AI Moments' },
    { name: 'sky', token: 'var(--sky)', label: 'Info, Pip Body, P2' },
    { name: 'amber', token: 'var(--amber)', label: 'XP, Highlights, P1' },
    { name: 'rose', token: 'var(--rose)', label: 'Warm Accent, Warnings' },
    { name: 'flame', token: 'var(--flame)', label: 'Danger, P0 Severity' },
    { name: 'mint', token: 'var(--mint)', label: 'Success, Local Privacy' },
  ];

  const neutralTokens = [
    { name: 'border', token: 'var(--border)', label: 'Lines & Outlines' },
    { name: 'text', token: 'var(--text)', label: 'Primary Text' },
    { name: 'text-muted', token: 'var(--text-muted)', label: 'Secondary Text' },
  ];

  return (
    <div className="min-h-screen bg-bg text-text p-6 md:p-12 max-w-6xl mx-auto space-y-12">
      {/* Header with Theme & Calm Mode Controls */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-border">
        <div>
          <h1 className="font-display font-bold text-3xl md:text-4xl text-text">
            RepoQuest Design System
          </h1>
          <p className="text-text-muted mt-1">
            Pixel Cartography tokens, typography, motion, and themes.
          </p>
        </div>

        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 bg-surface-1 p-1.5 rounded-md border border-border">
            <span className="text-xs font-mono uppercase text-text-muted px-2">Theme:</span>
            <button
              onClick={() => setTheme('dusk')}
              className={`px-3 py-1 text-xs rounded font-medium transition-colors ${
                theme === 'dusk'
                  ? 'bg-brand text-bg'
                  : 'text-text hover:bg-surface-3'
              }`}
            >
              Dusk (Dark)
            </button>
            <button
              onClick={() => setTheme('parchment')}
              className={`px-3 py-1 text-xs rounded font-medium transition-colors ${
                theme === 'parchment'
                  ? 'bg-brand text-bg'
                  : 'text-text hover:bg-surface-3'
              }`}
            >
              Parchment (Light)
            </button>
          </div>

          <div className="flex items-center gap-2 bg-surface-1 p-1.5 rounded-md border border-border">
            <span className="text-xs font-mono uppercase text-text-muted px-2">Calm Mode:</span>
            <button
              onClick={() => setCalm(!calm)}
              className={`px-3 py-1 text-xs rounded font-medium transition-colors ${
                calm ? 'bg-mint text-bg' : 'text-text hover:bg-surface-3'
              }`}
            >
              {calm ? 'Calm: ON' : 'Calm: OFF'}
            </button>
          </div>
        </div>
      </header>

      {/* Color Tokens: Surfaces */}
      <section className="space-y-4">
        <h2 className="font-display font-bold text-xl text-text">1. Surfaces</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {surfaceTokens.map((t) => (
            <div
              key={t.name}
              className="p-4 rounded-md border border-border shadow-card flex flex-col justify-between h-28"
              style={{ backgroundColor: t.token }}
            >
              <span className="font-mono text-xs font-bold text-text">--{t.name}</span>
              <span className="text-xs text-text-muted">{t.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Color Tokens: Brand & Status */}
      <section className="space-y-4">
        <h2 className="font-display font-bold text-xl text-text">2. Brand & Status Accents</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
          {brandTokens.map((t) => (
            <div
              key={t.name}
              className="p-4 rounded-md bg-surface-1 border border-border shadow-card flex items-center gap-3"
            >
              <div
                className="w-10 h-10 rounded border border-border flex-shrink-0"
                style={{ backgroundColor: t.token }}
              />
              <div className="flex flex-col min-w-0">
                <span className="font-mono text-xs font-bold text-text truncate">--{t.name}</span>
                <span className="text-xs text-text-muted truncate">{t.label}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Color Tokens: Neutrals */}
      <section className="space-y-4">
        <h2 className="font-display font-bold text-xl text-text">3. Text & Borders</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {neutralTokens.map((t) => (
            <div
              key={t.name}
              className="p-4 rounded-md bg-surface-1 border border-border shadow-card flex items-center gap-3"
            >
              <div
                className="w-10 h-10 rounded border border-border flex-shrink-0"
                style={{ backgroundColor: t.token }}
              />
              <div className="flex flex-col min-w-0">
                <span className="font-mono text-xs font-bold text-text">--{t.name}</span>
                <span className="text-xs text-text-muted">{t.label}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Gradients & Special Shapes */}
      <section className="space-y-4">
        <h2 className="font-display font-bold text-xl text-text">4. Effects & Quest Card</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <div className="p-6 rounded-md bg-aurora text-bg flex flex-col justify-end h-36">
            <span className="font-display font-extrabold text-2xl">Aurora Gradient</span>
            <span className="text-xs opacity-90 font-mono">--aurora</span>
          </div>

          <div className="p-0.5 bg-border quest-card">
            <div className="p-6 bg-surface-1 quest-card h-full flex flex-col justify-between">
              <div>
                <span className="font-pixel text-xs text-amber uppercase tracking-wider">
                  QUEST CARD PREVIEW
                </span>
                <h3 className="font-display font-bold text-lg text-text mt-1">
                  10px Notched Corners
                </h3>
                <p className="text-xs text-text-muted mt-1">
                  Diagonal-cut corners with clip-path on top-left and bottom-right.
                </p>
              </div>
              <span className="font-mono text-xs text-brand">.quest-card</span>
            </div>
          </div>
        </div>
      </section>

      {/* Typography Scale */}
      <section className="space-y-6">
        <h2 className="font-display font-bold text-xl text-text">5. Typography Scale</h2>
        <div className="space-y-6 p-6 rounded-md bg-surface-1 border border-border shadow-card">
          <div className="pb-4 border-b border-border">
            <span className="font-mono text-xs text-text-muted block mb-1">Display XL (72px / 800)</span>
            <p className="font-display font-extrabold text-4xl sm:text-5xl md:text-6xl text-text leading-none tracking-tight">
              Pixel Cartography
            </p>
          </div>

          <div className="pb-4 border-b border-border">
            <span className="font-mono text-xs text-text-muted block mb-1">Display L (48px / 800)</span>
            <p className="font-display font-extrabold text-3xl sm:text-4xl text-text">
              Living Codebase Map
            </p>
          </div>

          <div className="pb-4 border-b border-border">
            <span className="font-mono text-xs text-text-muted block mb-1">H1 (32px / 700)</span>
            <h1 className="font-display font-bold text-2xl sm:text-3xl text-text">
              Autonomous AI Triage
            </h1>
          </div>

          <div className="pb-4 border-b border-border">
            <span className="font-mono text-xs text-text-muted block mb-1">H2 (24px / 700)</span>
            <h2 className="font-display font-bold text-xl sm:text-2xl text-text">
              Repository Architecture
            </h2>
          </div>

          <div className="pb-4 border-b border-border">
            <span className="font-mono text-xs text-text-muted block mb-1">H3 (18px / 600 - Inter)</span>
            <h3 className="font-sans font-semibold text-lg text-text">
              Good First Issue Recommendations
            </h3>
          </div>

          <div className="pb-4 border-b border-border">
            <span className="font-mono text-xs text-text-muted block mb-1">Body (15px / 400 - Inter)</span>
            <p className="font-sans text-sm sm:text-base text-text leading-relaxed">
              RepoQuest indexes repositories into an offline knowledge graph with pgvector.
              Every AI action stays completely on your local machine with 100% privacy.
            </p>
          </div>

          <div className="pb-4 border-b border-border">
            <span className="font-mono text-xs text-text-muted block mb-1">Small (13px / 400 - Inter)</span>
            <p className="font-sans text-xs sm:text-sm text-text-muted">
              Metadata, timestamps, and secondary descriptions.
            </p>
          </div>

          <div className="pb-4 border-b border-border">
            <span className="font-mono text-xs text-text-muted block mb-1">Code (13px / 400 - JetBrains Mono)</span>
            <code className="font-mono text-xs sm:text-sm text-brand block bg-surface-2 p-2 rounded border border-border">
              SELECT id, title, 1 - (embedding &lt;=&gt; :q) AS sim FROM issues ORDER BY sim DESC LIMIT 5;
            </code>
          </div>

          <div>
            <span className="font-mono text-xs text-text-muted block mb-1">Pixel label (12px / 400 - Silkscreen)</span>
            <span className="font-pixel text-xs text-amber uppercase tracking-wider">
              STARTER QUEST +50 XP
            </span>
          </div>
        </div>
      </section>

      {/* Multilingual Support Preview */}
      <section className="space-y-4">
        <h2 className="font-display font-bold text-xl text-text">6. Multilingual Fonts</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-md bg-surface-1 border border-border shadow-card">
            <span className="font-mono text-xs text-text-muted block mb-2">Devanagari (Hindi)</span>
            <p className="font-devanagari text-base text-text">
              ओपन सोर्स की अपनी यात्रा शुरू करें।
            </p>
          </div>

          <div className="p-4 rounded-md bg-surface-1 border border-border shadow-card">
            <span className="font-mono text-xs text-text-muted block mb-2">Kannada</span>
            <p className="font-kannada text-base text-text">
              ಓಪನ್ ಸೋರ್ಸ್ ಅನ್ವೇಷಣೆಯನ್ನು ಪ್ರಾರಂಭಿಸಿ.
            </p>
          </div>

          <div className="p-4 rounded-md bg-surface-1 border border-border shadow-card">
            <span className="font-mono text-xs text-text-muted block mb-2">Tamil</span>
            <p className="font-tamil text-base text-text">
              திறந்த மூலப் பயணத்தை இன்றே தொடங்குங்கள்.
            </p>
          </div>
        </div>
      </section>

      {/* Motion & Framer Motion Preview */}
      <section className="space-y-4">
        <h2 className="font-display font-bold text-xl text-text">7. Motion Presets</h2>
        <motion.div
          variants={fadeUp}
          initial="hidden"
          animate="show"
          className="p-6 rounded-md bg-surface-1 border border-border shadow-card flex items-center justify-between"
        >
          <div>
            <h4 className="font-display font-bold text-base text-text">Framer Motion Presets</h4>
            <p className="text-xs text-text-muted mt-1">
              Supports fadeUp, snappy/gentle springs, and calm mode automatic suppression.
            </p>
          </div>
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            transition={spring.snappy}
            className="px-4 py-2 bg-brand text-bg rounded font-medium text-xs cursor-pointer select-none"
          >
            Snappy Spring Button
          </motion.div>
        </motion.div>
      </section>
    </div>
  );
}
