'use client';

import { useTheme } from 'next-themes';
import { useCalmMode } from '@/lib/calm';
import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { fadeUp, spring } from '@/lib/motion';
import { Logo, CompassIcon } from '@/components/brand/Logo';
import { SignatureStrip } from '@/components/brand/SignatureStrip';
import { Pip, PipState } from '@/components/brand/Pip';
import { PixelIcon, PixelIconName } from '@/components/brand/PixelIcon';
import { ContourBackground } from '@/components/brand/ContourBackground';

export default function DesignPage() {
  const { theme, setTheme } = useTheme();
  const { calm, setCalm } = useCalmMode();
  const [mounted, setMounted] = useState(false);
  const [interactivePipState, setInteractivePipState] = useState<PipState>('idle');
  const [pixelIconMono, setPixelIconMono] = useState(false);

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

  const pipStates: { state: PipState; label: string; desc: string }[] = [
    { state: 'idle', label: 'Idle', desc: 'Slow 3s breathing float' },
    { state: 'thinking', label: 'Thinking', desc: 'Head tilt & pupil scan' },
    { state: 'exploring', label: 'Exploring', desc: 'Lantern glow & walking legs' },
    { state: 'success', label: 'Success', desc: 'Victory jump & amber sparks' },
    { state: 'error', label: 'Error', desc: 'Cross eyes & side-to-side shake' },
    { state: 'sleeping', label: 'Sleeping', desc: 'Closed eyes & drifting Zs' },
  ];

  const pixelIconsList: PixelIconName[] = [
    'compass',
    'flag',
    'shield',
    'cracked-shield',
    'scroll',
    'lantern',
    'key',
    'spark',
    'crown',
    'lock',
  ];

  return (
    <div className="min-h-screen bg-bg text-text p-6 md:p-12 max-w-6xl mx-auto space-y-16 relative">
      {/* Header with Theme & Calm Mode Controls */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-border">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Logo variant="full" size="sm" />
          </div>
          <h1 className="font-display font-bold text-3xl md:text-4xl text-text">
            RepoQuest Design System
          </h1>
          <p className="text-text-muted mt-1">
            Pixel Cartography tokens, brand assets, Pip mascot, pixel icons, and themes.
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
              {calm ? 'Calm: ON (Paused)' : 'Calm: OFF (Active)'}
            </button>
          </div>
        </div>
      </header>

      {/* Brand Assets Showcase: Logo */}
      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-bold text-2xl text-text">1. Brand Logo</h2>
          <span className="text-xs font-mono text-text-muted">§2 & §16 (8x8 Compass Rose + Signature Dot)</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 rounded-md bg-surface-1 border border-border shadow-card space-y-4">
            <span className="font-mono text-xs text-text-muted uppercase">Full Logo (Bricolage 800 + Dot Strip)</span>
            <div className="py-2">
              <Logo variant="full" size="lg" showTagline />
            </div>
            <div className="flex items-center gap-4 pt-2">
              <Logo variant="full" size="md" />
              <Logo variant="full" size="sm" />
            </div>
          </div>

          <div className="p-6 rounded-md bg-surface-1 border border-border shadow-card space-y-4">
            <span className="font-mono text-xs text-text-muted uppercase">Variants: Wordmark, Icon & Mono</span>
            <div className="flex flex-wrap items-center gap-6 py-2">
              <div>
                <span className="text-xs font-mono text-text-muted block mb-1">Wordmark</span>
                <Logo variant="wordmark" size="md" />
              </div>
              <div>
                <span className="text-xs font-mono text-text-muted block mb-1">Compass Icon</span>
                <CompassIcon size={36} />
              </div>
              <div>
                <span className="text-xs font-mono text-text-muted block mb-1">Mono Icon</span>
                <CompassIcon size={36} mono className="text-text" />
              </div>
              <div>
                <span className="text-xs font-mono text-text-muted block mb-1">Mono Full</span>
                <Logo variant="full" size="sm" mono />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Signature Strip */}
      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="font-display font-bold text-2xl text-text">2. Signature Strip</h2>
          <span className="text-xs font-mono text-text-muted">4 square pixels: Sky, Amber, Rose, Flame</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="p-6 rounded-md bg-surface-1 border border-border shadow-card space-y-4">
            <span className="font-mono text-xs text-text-muted uppercase">Divider Variant</span>
            <div className="py-4">
              <SignatureStrip variant="divider" size={8} />
            </div>
            <p className="text-xs text-text-muted">Centered 4-pixel divider for card footers and section ends.</p>
          </div>

          <div className="p-6 rounded-md bg-surface-1 border border-border shadow-card space-y-4">
            <span className="font-mono text-xs text-text-muted uppercase">Loader Variant</span>
            <div className="py-4 flex justify-center">
              <SignatureStrip variant="loader" size={10} />
            </div>
            <p className="text-xs text-text-muted">Sequentially pulsing loop for inline background tasks.</p>
          </div>

          <div className="p-6 rounded-md bg-surface-1 border border-border shadow-card space-y-4">
            <span className="font-mono text-xs text-text-muted uppercase">Cap Variant</span>
            <div className="py-4">
              <div className="h-1.5 w-full bg-surface-3 rounded-full overflow-hidden relative">
                <div className="h-full bg-brand w-2/3" />
                <div className="absolute top-0 right-1/3">
                  <SignatureStrip variant="cap" size={6} />
                </div>
              </div>
            </div>
            <p className="text-xs text-text-muted">4-color cap on top edge of progress bars and cards.</p>
          </div>
        </div>
      </section>

      {/* Pip Mascot Gallery (All 6 States) */}
      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display font-bold text-2xl text-text">3. Pip Mascot (All 6 States)</h2>
            <p className="text-xs text-text-muted mt-1">
              Exact 14x12 pixel grid with animated antenna, scanning eyes, legs, sparks, lantern, and Zs.
            </p>
          </div>
          <span className="text-xs font-mono px-2 py-1 rounded bg-surface-2 border border-border">
            {calm ? 'Calm Mode Active (Static Poses)' : 'Animated Mode'}
          </span>
        </div>

        {/* All 6 states side by side */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {pipStates.map(({ state, label, desc }) => (
            <div
              key={state}
              className={`p-4 rounded-md bg-surface-1 border transition-all text-center flex flex-col items-center justify-between gap-3 ${
                interactivePipState === state
                  ? 'border-brand shadow-card'
                  : 'border-border'
              }`}
              onClick={() => setInteractivePipState(state)}
            >
              <div className="h-28 flex items-center justify-center">
                <Pip state={state} size={84} />
              </div>
              <div className="w-full pt-2 border-t border-border">
                <h4 className="font-display font-bold text-sm text-text capitalize">{label}</h4>
                <p className="text-[11px] text-text-muted mt-0.5 line-clamp-1">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Interactive Pip Playground */}
        <div className="p-6 rounded-md bg-surface-1 border border-border shadow-card flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-6">
            <div className="w-32 h-32 flex items-center justify-center bg-surface-2 rounded-lg border border-border">
              <Pip state={interactivePipState} size={112} />
            </div>
            <div>
              <span className="text-xs font-mono text-amber uppercase tracking-wider font-semibold">
                Pip Playground
              </span>
              <h3 className="font-display font-bold text-xl text-text capitalize">
                State: {interactivePipState}
              </h3>
              <p className="text-xs text-text-muted mt-1">
                {pipStates.find((s) => s.state === interactivePipState)?.desc}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {pipStates.map(({ state, label }) => (
              <button
                key={state}
                onClick={() => setInteractivePipState(state)}
                className={`px-3 py-1.5 text-xs rounded font-medium border transition-colors ${
                  interactivePipState === state
                    ? 'bg-brand text-bg border-brand'
                    : 'bg-surface-2 text-text border-border hover:bg-surface-3'
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Pixel Icons (16x16) */}
      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display font-bold text-2xl text-text">4. Pixel Icons (16x16 Grid)</h2>
            <p className="text-xs text-text-muted mt-1">
              Custom pixel-art SVG sprite with crispEdges: compass, flag, shield, cracked-shield, scroll, lantern, key, spark, crown, lock.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPixelIconMono(!pixelIconMono)}
              className={`px-3 py-1 text-xs rounded font-medium border transition-colors ${
                pixelIconMono
                  ? 'bg-brand text-bg border-brand'
                  : 'bg-surface-1 text-text border-border hover:bg-surface-2'
              }`}
            >
              {pixelIconMono ? 'Mono: ON' : 'Mono: OFF (Colors)'}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          {pixelIconsList.map((iconName) => (
            <div
              key={iconName}
              className="p-4 rounded-md bg-surface-1 border border-border shadow-card flex flex-col items-center justify-center gap-3 text-center"
            >
              <div className="w-16 h-16 rounded-md bg-surface-2 border border-border flex items-center justify-center">
                <PixelIcon name={iconName} size={32} mono={pixelIconMono} />
              </div>
              <div>
                <span className="font-mono text-xs text-text capitalize block">
                  {iconName.replace('-', ' ')}
                </span>
                <span className="text-[10px] font-mono text-text-muted">16x16 SVG</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Contour Background Preview */}
      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="font-display font-bold text-2xl text-text">5. Contour Background</h2>
            <p className="text-xs text-text-muted mt-1">
              Hand-tuned wavy closed elevation paths with 40s linear drift animation. Pauses off-screen & in Calm mode.
            </p>
          </div>
          <span className="text-xs font-mono px-2 py-1 rounded bg-surface-2 border border-border">
            {calm ? 'Contour Static (Calm Mode)' : 'Contour Drifting'}
          </span>
        </div>

        <div className="relative h-64 w-full rounded-lg border border-border overflow-hidden bg-surface-1 shadow-card flex items-center justify-center">
          <ContourBackground opacity={0.12} />
          <div className="relative z-10 text-center max-w-md px-6">
            <span className="font-pixel text-xs text-amber uppercase tracking-wider block mb-2">
              HERO MAP BACKGROUND
            </span>
            <h3 className="font-display font-bold text-2xl text-text">
              Topographic Terrain Canvas
            </h3>
            <p className="text-xs text-text-muted mt-2">
              24 organic elevation contours move gently beneath the hero quest map without distracting from primary tasks.
            </p>
          </div>
        </div>
      </section>

      {/* Color Tokens: Surfaces */}
      <section className="space-y-4">
        <h2 className="font-display font-bold text-xl text-text">6. Surfaces</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {surfaceTokens.map((item) => (
            <div
              key={item.name}
              className="p-4 rounded-md border border-border space-y-2 shadow-card"
              style={{ backgroundColor: item.token }}
            >
              <div className="font-mono text-xs font-bold text-text">{item.name}</div>
              <div className="text-xs text-text-muted">{item.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Color Tokens: Brand & Semantics */}
      <section className="space-y-4">
        <h2 className="font-display font-bold text-xl text-text">7. Brand & Semantic Tokens</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4">
          {brandTokens.map((item) => (
            <div
              key={item.name}
              className="p-4 rounded-md border border-border space-y-2 bg-surface-1 shadow-card"
            >
              <div
                className="w-full h-12 rounded border border-border"
                style={{ backgroundColor: item.token }}
              />
              <div className="font-mono text-xs font-bold text-text">{item.name}</div>
              <div className="text-[11px] text-text-muted leading-tight">{item.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Color Tokens: Neutrals */}
      <section className="space-y-4">
        <h2 className="font-display font-bold text-xl text-text">8. Neutrals & Borders</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {neutralTokens.map((item) => (
            <div
              key={item.name}
              className="p-4 rounded-md border border-border space-y-2 bg-surface-1 shadow-card"
            >
              <div
                className="w-full h-12 rounded border border-border"
                style={{ backgroundColor: item.token }}
              />
              <div className="font-mono text-xs font-bold text-text">{item.name}</div>
              <div className="text-xs text-text-muted">{item.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Typography Hierarchy */}
      <section className="space-y-4">
        <h2 className="font-display font-bold text-xl text-text">9. Typography Stack</h2>
        <div className="p-6 rounded-md bg-surface-1 border border-border space-y-6 shadow-card">
          <div className="pb-4 border-b border-border">
            <span className="font-mono text-xs text-text-muted block mb-1">Display (48px / 800)</span>
            <p className="font-display font-extrabold text-3xl sm:text-5xl text-text">
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
        <h2 className="font-display font-bold text-xl text-text">10. Multilingual Fonts</h2>
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
        <h2 className="font-display font-bold text-xl text-text">11. Motion Presets</h2>
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
