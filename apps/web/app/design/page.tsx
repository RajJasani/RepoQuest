'use client';

import { useTheme } from 'next-themes';
import { useCalmMode } from '@/lib/calm';
import { useEffect, useState } from 'react';

// Brand components
import { Logo, CompassIcon } from '@/components/brand/Logo';
import { SignatureStrip } from '@/components/brand/SignatureStrip';
import { Pip, PipState } from '@/components/brand/Pip';
import { PixelIcon, PixelIconName } from '@/components/brand/PixelIcon';
import { ContourBackground } from '@/components/brand/ContourBackground';

// Motion helpers
import {
  Reveal,
  Stagger,
  StaggerItem,
  Stamp,
  CountUp,
  TypewriterText,
  Odometer,
} from '@/components/motion';

// UI components
import {
  Button,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  QuestCard,
  StatusChip,
  SeverityPill,
  CitationChip,
  Skeleton,
  Progress,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  Drawer,
  DrawerHeader,
  DrawerTitle,
  DrawerDescription,
  DrawerContent,
  DrawerFooter,
  Tooltip,
  UndoToast,
  showToast,
} from '@/components/ui';

export default function DesignPage() {
  const { theme, setTheme } = useTheme();
  const { calm, setCalm } = useCalmMode();
  const [mounted, setMounted] = useState(false);

  // Interactive states
  const [interactivePipState, setInteractivePipState] = useState<PipState>('idle');
  const [pixelIconMono, setPixelIconMono] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [odometerValue, setOdometerValue] = useState(1420);
  const [countUpKey, setCountUpKey] = useState(0);
  const [typewriterKey, setTypewriterKey] = useState(0);

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
    <div className="min-h-screen bg-bg text-text p-6 md:p-12 max-w-6xl mx-auto space-y-20 relative">
      {/* Header with Theme & Calm Mode Controls */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-border">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <Logo variant="full" size="sm" />
          </div>
          <h1 className="font-display font-bold text-3xl md:text-4xl text-text">
            RepoQuest Design System
          </h1>
          <p className="text-text-muted mt-1 text-sm">
            Pixel Cartography tokens, brand assets, motion helpers, and accessible UI components.
          </p>
        </div>

        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2 bg-surface-1 p-1.5 rounded-md border border-border">
            <span className="text-xs font-mono uppercase text-text-muted px-2">Theme:</span>
            <button
              onClick={() => setTheme('dusk')}
              className={`px-3 py-1 text-xs rounded font-medium transition-colors ${
                theme === 'dusk'
                  ? 'bg-brand text-white'
                  : 'text-text hover:bg-surface-3'
              }`}
            >
              Dusk (Dark)
            </button>
            <button
              onClick={() => setTheme('parchment')}
              className={`px-3 py-1 text-xs rounded font-medium transition-colors ${
                theme === 'parchment'
                  ? 'bg-brand text-white'
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
                calm ? 'bg-mint text-white' : 'text-text hover:bg-surface-3'
              }`}
            >
              {calm ? 'Calm: ON (Paused)' : 'Calm: OFF (Active)'}
            </button>
          </div>
        </div>
      </header>

      {/* SECTION 1: MOTION HELPERS */}
      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div>
            <h2 className="font-display font-bold text-2xl text-text">1. Motion Helpers</h2>
            <p className="text-xs text-text-muted mt-1">
              Reveal, Stagger, Stamp, CountUp, TypewriterText, and Odometer honoring reduced motion and Calm mode.
            </p>
          </div>
          <span className="text-xs font-mono px-2 py-1 rounded bg-surface-2 border border-border">
            components/motion
          </span>
        </div>

        <Reveal direction="up">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Reveal & Stagger */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Reveal & Stagger</CardTitle>
              <CardDescription>Entrance transitions with 40ms stagger cap</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Stagger gap={0.06}>
                <StaggerItem>
                  <div className="p-2.5 rounded bg-surface-2 border border-border text-xs flex justify-between">
                    <span>Task 1: Index Repositories</span>
                    <StatusChip variant="mint" label="Ready" />
                  </div>
                </StaggerItem>
                <StaggerItem>
                  <div className="p-2.5 rounded bg-surface-2 border border-border text-xs flex justify-between">
                    <span>Task 2: Embed Code Chunks</span>
                    <StatusChip variant="sky" label="Embedding" pulse />
                  </div>
                </StaggerItem>
                <StaggerItem>
                  <div className="p-2.5 rounded bg-surface-2 border border-border text-xs flex justify-between">
                    <span>Task 3: Build Architecture Graph</span>
                    <StatusChip variant="amber" label="Pending" />
                  </div>
                </StaggerItem>
              </Stagger>
            </CardContent>
          </Card>

          {/* Stamp */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Pixel Stamps</CardTitle>
              <CardDescription>Bouncy -8deg ink stamps with squash</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-4 items-center justify-center py-4">
              <Stamp text="APPROVED" variant="mint" />
              <Stamp text="REJECTED" variant="flame" />
              <Stamp text="REVIEWED" variant="amber" />
              <Stamp text="VERIFIED" variant="brand" />
            </CardContent>
          </Card>

          {/* CountUp */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base">CountUp</CardTitle>
                <CardDescription>Animated integer/currency numbers</CardDescription>
              </div>
              <button
                type="button"
                onClick={() => setCountUpKey((k) => k + 1)}
                className="text-xs px-2 py-1 rounded bg-surface-2 hover:bg-surface-3 border border-border"
              >
                Replay
              </button>
            </CardHeader>
            <CardContent className="py-2 space-y-4">
              <div className="flex items-baseline justify-between border-b border-border/50 pb-2">
                <span className="text-xs text-text-muted">Repository XP:</span>
                <span className="font-mono text-2xl font-bold text-amber">
                  <CountUp key={`xp-${countUpKey}`} to={4850} prefix="+" suffix=" XP" duration={0.8} />
                </span>
              </div>
              <div className="flex items-baseline justify-between">
                <span className="text-xs text-text-muted">Indexed Chunks:</span>
                <span className="font-mono text-xl font-bold text-brand">
                  <CountUp key={`chunks-${countUpKey}`} to={1284} duration={0.6} />
                </span>
              </div>
            </CardContent>
          </Card>

          {/* TypewriterText */}
          <Card className="md:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base">TypewriterText</CardTitle>
                <CardDescription>Word-by-word streaming simulation</CardDescription>
              </div>
              <button
                type="button"
                onClick={() => setTypewriterKey((k) => k + 1)}
                className="text-xs px-2 py-1 rounded bg-surface-2 hover:bg-surface-3 border border-border"
              >
                Re-stream
              </button>
            </CardHeader>
            <CardContent>
              <div className="p-3 bg-surface-2 rounded border border-border font-sans text-sm min-h-[64px] leading-relaxed">
                <TypewriterText
                  key={`typewriter-${typewriterKey}`}
                  text="RepoQuest analyzed PR #482: Verified 0 secret leaks, 100% test coverage preserved, and valid new-side line citations across all 4 touched files."
                  speedMs={35}
                />
              </div>
            </CardContent>
          </Card>

          {/* Odometer */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base">Odometer</CardTitle>
                <CardDescription>Rolling digit transitions</CardDescription>
              </div>
              <div className="flex gap-1">
                <button
                  type="button"
                  onClick={() => setOdometerValue((v) => v - 100)}
                  className="px-2 py-0.5 text-xs bg-surface-2 hover:bg-surface-3 border border-border rounded"
                >
                  -100
                </button>
                <button
                  type="button"
                  onClick={() => setOdometerValue((v) => v + 150)}
                  className="px-2 py-0.5 text-xs bg-surface-2 hover:bg-surface-3 border border-border rounded"
                >
                  +150
                </button>
              </div>
            </CardHeader>
            <CardContent className="flex items-center justify-center py-4">
              <div className="text-3xl font-bold text-text bg-surface-2 px-4 py-2 rounded-lg border border-border shadow-inner">
                <Odometer value={odometerValue} />
              </div>
            </CardContent>
          </Card>
        </div>
      </Reveal>
      </section>

      {/* SECTION 2: UI BUTTONS IN ALL STATES */}
      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div>
            <h2 className="font-display font-bold text-2xl text-text">2. Buttons (All Variants & States)</h2>
            <p className="text-xs text-text-muted mt-1">
              Aurora Primary, Secondary, Ghost, Danger with confirm dialog, Signature Strip loader, and disabled states.
            </p>
          </div>
          <span className="text-xs font-mono px-2 py-1 rounded bg-surface-2 border border-border">
            components/ui/Button
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Primary Aurora */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Primary (Aurora)</CardTitle>
              <CardDescription>--aurora gradient, 10px radius</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">Default / Hover</span>
                <Button variant="primary" className="w-full">
                  Primary Action
                </Button>
              </div>
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">Shimmer CTA (M1)</span>
                <Button variant="primary" shimmer className="w-full">
                  Explore Quest Map
                </Button>
              </div>
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">Loading State</span>
                <Button variant="primary" loading className="w-full">
                  Indexing Repo...
                </Button>
              </div>
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">Disabled State</span>
                <Button variant="primary" disabled className="w-full">
                  Disabled Action
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Secondary */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Secondary</CardTitle>
              <CardDescription>Surface-2 fill with border</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">Default / Hover</span>
                <Button variant="secondary" className="w-full">
                  Secondary Action
                </Button>
              </div>
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">Loading State</span>
                <Button variant="secondary" loading className="w-full">
                  Fetching Commits
                </Button>
              </div>
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">Disabled State</span>
                <Button variant="secondary" disabled className="w-full">
                  Unavailable Option
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Ghost */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Ghost</CardTitle>
              <CardDescription>Transparent with hover fill</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">Default / Hover</span>
                <Button variant="ghost" className="w-full">
                  Ghost Button
                </Button>
              </div>
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">Loading State</span>
                <Button variant="ghost" loading className="w-full">
                  Syncing
                </Button>
              </div>
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">Disabled State</span>
                <Button variant="ghost" disabled className="w-full">
                  Disabled Ghost
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Danger */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Danger</CardTitle>
              <CardDescription>Flame fill + confirmation dialog</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">With Confirm Dialog</span>
                <Button
                  variant="danger"
                  dangerWithConfirm
                  confirmTitle="Delete Indexed Repository?"
                  confirmDescription="This permanently removes all pgvector embeddings and audit histories."
                  onClick={() => showToast.error('Repository deleted.')}
                  className="w-full"
                >
                  Delete Repository
                </Button>
              </div>
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">Loading State</span>
                <Button variant="danger" loading className="w-full">
                  Deleting...
                </Button>
              </div>
              <div>
                <span className="text-[11px] font-mono text-text-muted block mb-1">Disabled State</span>
                <Button variant="danger" disabled className="w-full">
                  Cannot Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* SECTION 3: CARDS & QUEST CARDS */}
      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div>
            <h2 className="font-display font-bold text-2xl text-text">3. Cards & Quest Cards</h2>
            <p className="text-xs text-text-muted mt-1">
              Standard 16px radius Card vs Notched QuestCard (section 15.2 wrapper technique & Parchment hard shadow).
            </p>
          </div>
          <span className="text-xs font-mono px-2 py-1 rounded bg-surface-2 border border-border">
            components/ui/QuestCard
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card hoverEffect>
            <CardHeader>
              <div className="flex justify-between items-center">
                <CardTitle>Standard Card (16px Radius)</CardTitle>
                <StatusChip variant="mint" label="Surface-1" />
              </div>
              <CardDescription>Standard container for metrics, logs, and audit lists.</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-text-muted leading-relaxed">
                Cards use 1px border with token-aware `--shadow-card`. On hover, border brightness raises and
                lifts smoothly by 0.5px.
              </p>
            </CardContent>
            <CardFooter className="flex justify-between border-t border-border pt-4">
              <span className="font-mono text-xs text-text-muted">radius: 16px</span>
              <Button size="sm" variant="secondary">View Details</Button>
            </CardFooter>
          </Card>

          <QuestCard glow showStrip>
            <div className="flex justify-between items-start mb-3">
              <div>
                <span className="font-pixel text-[11px] text-amber uppercase tracking-wider block">
                  MAIN PILLAR HERO
                </span>
                <h3 className="font-display font-bold text-xl text-text mt-0.5">
                  Autonomous AI Triage
                </h3>
              </div>
              <SeverityPill level="P0" showFullLabel />
            </div>
            <p className="text-sm text-text-muted leading-relaxed mb-4">
              Built with the §15.2 wrapper technique: 10px notched corners survive clip-path clipping,
              a Signature Strip sits on top, and Parchment hard shadows render cleanly.
            </p>
            <div className="flex items-center justify-between pt-3 border-t border-border/50">
              <span className="font-mono text-xs text-brand">Notched Corner: 10px</span>
              <Button size="sm" variant="primary">Start Triage</Button>
            </div>
          </QuestCard>
        </div>
      </section>

      {/* SECTION 4: PILLS, CHIPS & BADGES */}
      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div>
            <h2 className="font-display font-bold text-2xl text-text">4. Pills, Chips & Citations</h2>
            <p className="text-xs text-text-muted mt-1">
              StatusChip with live pulsing dot, SeverityPill (icon + label + color), and mono CitationChip.
            </p>
          </div>
          <span className="text-xs font-mono px-2 py-1 rounded bg-surface-2 border border-border">
            chips & pills
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Status Chips */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Status Chips</CardTitle>
              <CardDescription>With optional live pulsing dot</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2.5">
              <StatusChip variant="mint" label="Ready" />
              <StatusChip variant="sky" label="Embedding" pulse />
              <StatusChip variant="amber" label="Thinking" pulse />
              <StatusChip variant="flame" label="Failed" />
              <StatusChip variant="rose" label="Blocked" />
              <StatusChip variant="neutral" label="Idle" />
            </CardContent>
          </Card>

          {/* Severity Pills */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Severity Pills</CardTitle>
              <CardDescription>Always icon + label + color (WCAG AA)</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2.5">
              <SeverityPill level="P0" showFullLabel />
              <SeverityPill level="P1" showFullLabel />
              <SeverityPill level="P2" showFullLabel />
              <SeverityPill level="P3" showFullLabel />
              <SeverityPill level="good-first-issue" />
            </CardContent>
          </Card>

          {/* Citation Chips */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Citation Chips</CardTitle>
              <CardDescription>Mono citation links with line ranges</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2.5">
              <CitationChip index={1} path="apps/api/app/main.py" lines={[12, 34]} />
              <CitationChip index={2} path="services/triage.py" lines={[88, 102]} />
              <CitationChip index={3} path="components/brand/Pip.tsx" lines="L50-70" />
            </CardContent>
          </Card>
        </div>
      </section>

      {/* SECTION 5: PROGRESS, SKELETON & TABS */}
      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div>
            <h2 className="font-display font-bold text-2xl text-text">5. Progress, Skeleton & Tabs</h2>
            <p className="text-xs text-text-muted mt-1">
              Signature Strip progress bars, 1.4s diagonal shimmer skeleton, and layoutId sliding tabs.
            </p>
          </div>
          <span className="text-xs font-mono px-2 py-1 rounded bg-surface-2 border border-border">
            progress & navigation
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Progress */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Signature Strip Progress</CardTitle>
              <CardDescription>Determinate & indeterminate cycling</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="flex justify-between text-xs font-mono text-text-muted mb-1">
                  <span>Chunking (45%)</span>
                  <span>45%</span>
                </div>
                <Progress value={45} height={8} />
              </div>
              <div>
                <div className="flex justify-between text-xs font-mono text-text-muted mb-1">
                  <span>Embedding Chunks (85%)</span>
                  <span>85%</span>
                </div>
                <Progress value={85} height={8} />
              </div>
              <div>
                <div className="flex justify-between text-xs font-mono text-text-muted mb-1">
                  <span>Indeterminate Progress</span>
                  <span>Cycling</span>
                </div>
                <Progress indeterminate height={8} />
              </div>
            </CardContent>
          </Card>

          {/* Skeleton Shimmer */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Skeleton (1.4s Shimmer)</CardTitle>
              <CardDescription>Surface-3 blocks with diagonal sweep</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-full" />
              <div className="flex gap-3 pt-2">
                <Skeleton className="h-10 w-10 rounded-full" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-3 w-1/2" />
                  <Skeleton className="h-3 w-4/5" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Tabs with layoutId underline */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Sliding Tabs</CardTitle>
              <CardDescription>Shared layoutId underline animation</CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="triage">Triage</TabsTrigger>
                  <TabsTrigger value="models">Models</TabsTrigger>
                </TabsList>
                <TabsContent value="overview">
                  <p className="text-xs text-text-muted leading-relaxed">
                    Repository graph and architecture overview with full local indexing.
                  </p>
                </TabsContent>
                <TabsContent value="triage">
                  <p className="text-xs text-text-muted leading-relaxed">
                    Issue triage queue: automated duplicate detection and priority tagging.
                  </p>
                </TabsContent>
                <TabsContent value="models">
                  <p className="text-xs text-text-muted leading-relaxed">
                    Local LLM benchmarking leaderboard and racing benchmark results.
                  </p>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* SECTION 6: OVERLAYS (DIALOG, DRAWER, TOOLTIP, TOAST) */}
      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div>
            <h2 className="font-display font-bold text-2xl text-text">6. Overlays (Dialog, Drawer, Tooltip & Toasts)</h2>
            <p className="text-xs text-text-muted mt-1">
              Accessible modals, right-side sliding drawer, instant tooltips, and Sonner undo toasts with draining line.
            </p>
          </div>
          <span className="text-xs font-mono px-2 py-1 rounded bg-surface-2 border border-border">
            overlays & feedback
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Dialog Demo */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Modal Dialog</CardTitle>
              <CardDescription>Scale 96% entrance + backdrop</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="secondary" onClick={() => setDialogOpen(true)} className="w-full">
                Open Dialog
              </Button>

              <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Repository Settings</DialogTitle>
                    <DialogDescription>
                      Configure local embeddings provider and similarity thresholds.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-3 py-2 text-sm text-text-muted">
                    <p>pgvector index: <span className="font-mono text-text">HNSW cosine</span></p>
                    <p>Ollama model: <span className="font-mono text-text">nomic-embed-text</span></p>
                  </div>
                  <DialogFooter>
                    <Button variant="secondary" onClick={() => setDialogOpen(false)}>Cancel</Button>
                    <Button variant="primary" onClick={() => setDialogOpen(false)}>Save Settings</Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>
            </CardContent>
          </Card>

          {/* Drawer Demo */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Slide Drawer</CardTitle>
              <CardDescription>24px gentle spring slide</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="secondary" onClick={() => setDrawerOpen(true)} className="w-full">
                Open Drawer
              </Button>

              <Drawer open={drawerOpen} onOpenChange={setDrawerOpen}>
                <DrawerHeader>
                  <DrawerTitle>Module: services/indexer.py</DrawerTitle>
                  <DrawerDescription>Top-level architecture details and dependencies.</DrawerDescription>
                </DrawerHeader>
                <DrawerContent className="space-y-4 text-sm text-text-muted">
                  <div className="p-3 bg-surface-2 rounded border border-border">
                    <h5 className="font-mono text-xs font-bold text-text mb-1">Exports</h5>
                    <p className="font-mono text-xs">run_indexer, compute_hash, sync_labels</p>
                  </div>
                  <div className="p-3 bg-surface-2 rounded border border-border">
                    <h5 className="font-mono text-xs font-bold text-text mb-1">Key Files</h5>
                    <p className="font-mono text-xs">worker.py, rag.py, explorer.py</p>
                  </div>
                </DrawerContent>
                <DrawerFooter>
                  <Button variant="secondary" onClick={() => setDrawerOpen(false)} className="w-full">
                    Close Drawer
                  </Button>
                </DrawerFooter>
              </Drawer>
            </CardContent>
          </Card>

          {/* Tooltips Demo */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Tooltips</CardTitle>
              <CardDescription>150ms fast fade on hover/focus</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-2.5 items-center justify-center py-2">
              <Tooltip content="WCAG AA compliant across all tokens" side="top">
                <Button variant="secondary" size="sm" className="w-full">
                  Hover for Tooltip (Top)
                </Button>
              </Tooltip>
              <Tooltip content="100% offline local privacy" side="bottom">
                <Button variant="ghost" size="sm" className="w-full">
                  Hover for Tooltip (Bottom)
                </Button>
              </Tooltip>
            </CardContent>
          </Card>

          {/* Toasts Demo */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Toast Notifications</CardTitle>
              <CardDescription>With draining line undo toast</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => showToast.success('Repository indexed!')}
                  className="flex-1 text-xs"
                >
                  Success
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => showToast.error('Connection failed!')}
                  className="flex-1 text-xs"
                >
                  Error
                </Button>
              </div>
              <Button
                size="sm"
                variant="primary"
                onClick={() =>
                  showToast.undo('Issue #482 marked as duplicate', () => {
                    showToast.info('Undo action executed!');
                  })
                }
                className="w-full text-xs"
              >
                Trigger Undo Toast
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Standalone Undo Toast Showcase */}
        <div className="p-4 rounded-md bg-surface-1 border border-border shadow-card flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <h4 className="font-display font-bold text-sm text-text">Undo Toast Preview (Draining Line)</h4>
            <p className="text-xs text-text-muted mt-0.5">
              5s progress bar empties left-to-right using GPU-accelerated scaleX transform.
            </p>
          </div>
          <div className="w-full sm:w-auto">
            <UndoToast
              message="Label 'good-first-issue' added"
              onUndo={() => showToast.info('Action reverted!')}
              durationMs={8000}
            />
          </div>
        </div>
      </section>

      {/* SECTION 7: BRAND ASSETS SHOWCASE */}
      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div>
            <h2 className="font-display font-bold text-2xl text-text">7. Brand Assets</h2>
            <p className="text-xs text-text-muted mt-1">Logo, Signature Strip, Pip Mascot, and Pixel Icons.</p>
          </div>
          <span className="text-xs font-mono px-2 py-1 rounded bg-surface-2 border border-border">
            components/brand
          </span>
        </div>

        {/* Logo & Signature Strip */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Logo & Variants</CardTitle>
              <CardDescription>Bricolage Grotesque ExtraBold + Signature Strip Dot</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Logo variant="full" size="lg" showTagline />
              <div className="flex items-center gap-4 pt-2">
                <Logo variant="wordmark" size="md" />
                <CompassIcon size={32} />
                <CompassIcon size={32} mono className="text-text" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Signature Strip</CardTitle>
              <CardDescription>Sky, Amber, Rose, Flame pixels</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 py-2">
              <div className="p-3 bg-surface-2 rounded flex justify-between items-center">
                <span className="text-xs text-text-muted">Divider</span>
                <SignatureStrip variant="divider" size={8} />
              </div>
              <div className="p-3 bg-surface-2 rounded flex justify-between items-center">
                <span className="text-xs text-text-muted">Loader</span>
                <SignatureStrip variant="loader" size={8} />
              </div>
              <div className="p-3 bg-surface-2 rounded flex justify-between items-center">
                <span className="text-xs text-text-muted">Cap</span>
                <SignatureStrip variant="cap" size={8} />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Pip Gallery (All 6 States) */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-display font-bold text-lg text-text">Pip Mascot (All 6 States)</h3>
            <span className="text-xs font-mono text-text-muted">
              {calm ? 'Calm Mode Active (Static Poses)' : 'Animated Mode'}
            </span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {pipStates.map(({ state, label, desc }) => (
              <div
                key={state}
                className={`p-4 rounded-md bg-surface-1 border transition-all text-center flex flex-col items-center justify-between gap-3 ${
                  interactivePipState === state ? 'border-brand shadow-card' : 'border-border'
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
        </div>

        {/* Pixel Icons */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-display font-bold text-lg text-text">Pixel Icons (16x16 Grid)</h3>
            <button
              onClick={() => setPixelIconMono(!pixelIconMono)}
              className="px-3 py-1 text-xs rounded border border-border bg-surface-1 text-text hover:bg-surface-2"
            >
              {pixelIconMono ? 'Mono: ON' : 'Mono: OFF'}
            </button>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            {pixelIconsList.map((iconName) => (
              <div
                key={iconName}
                className="p-4 rounded-md bg-surface-1 border border-border shadow-card flex flex-col items-center justify-center gap-2 text-center"
              >
                <div className="w-14 h-14 rounded-md bg-surface-2 border border-border flex items-center justify-center">
                  <PixelIcon name={iconName} size={28} mono={pixelIconMono} />
                </div>
                <span className="font-mono text-xs text-text capitalize">{iconName.replace('-', ' ')}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Contour Background Hero */}
        <div className="relative h-48 w-full rounded-lg border border-border overflow-hidden bg-surface-1 shadow-card flex items-center justify-center">
          <ContourBackground opacity={0.12} />
          <div className="relative z-10 text-center max-w-md px-6">
            <span className="font-pixel text-xs text-amber uppercase tracking-wider block mb-1">
              HERO MAP CONTOURS
            </span>
            <h4 className="font-display font-bold text-xl text-text">
              24 Elevation Terrain Contours
            </h4>
            <p className="text-xs text-text-muted mt-1">
              Pauses off-screen & freezes completely in Calm mode.
            </p>
          </div>
        </div>
      </section>

      {/* SECTION 8: COLOR TOKENS & TYPOGRAPHY */}
      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-border pb-2">
          <div>
            <h2 className="font-display font-bold text-2xl text-text">8. Color Tokens & Typography</h2>
            <p className="text-xs text-text-muted mt-1">WCAG AA audited design tokens and typography hierarchy.</p>
          </div>
          <span className="text-xs font-mono px-2 py-1 rounded bg-surface-2 border border-border">
            design tokens
          </span>
        </div>

        {/* Surfaces */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {surfaceTokens.map((item) => (
            <div
              key={item.name}
              className="p-4 rounded-md border border-border space-y-1 shadow-card"
              style={{ backgroundColor: item.token }}
            >
              <div className="font-mono text-xs font-bold text-text">{item.name}</div>
              <div className="text-xs text-text-muted">{item.label}</div>
            </div>
          ))}
        </div>

        {/* Brand Tokens */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-4">
          {brandTokens.map((item) => (
            <div key={item.name} className="p-4 rounded-md border border-border space-y-2 bg-surface-1 shadow-card">
              <div className="w-full h-10 rounded border border-border" style={{ backgroundColor: item.token }} />
              <div className="font-mono text-xs font-bold text-text">{item.name}</div>
              <div className="text-[11px] text-text-muted leading-tight">{item.label}</div>
            </div>
          ))}
        </div>

        {/* Neutrals & Borders */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          {neutralTokens.map((item) => (
            <div key={item.name} className="p-4 rounded-md border border-border space-y-2 bg-surface-1 shadow-card">
              <div className="w-full h-10 rounded border border-border" style={{ backgroundColor: item.token }} />
              <div className="font-mono text-xs font-bold text-text">{item.name}</div>
              <div className="text-xs text-text-muted">{item.label}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
