'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { useSettings } from '@/lib/settings-context';
import { api, ApiError } from '@/lib/api';

import { AppShell } from '@/components/layout/AppShell';
import { ContourBackground } from '@/components/brand/ContourBackground';
import { PixelIcon } from '@/components/brand/PixelIcon';
import { PixelQuestMap } from '@/components/landing/PixelQuestMap';
import { ScanBeamInput } from '@/components/landing/ScanBeamInput';
import { Button } from '@/components/ui/Button';
import { QuestCard } from '@/components/ui/QuestCard';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/Dialog';
import { spring, ease } from '@/lib/motion';
import { showToast } from '@/components/ui/Toast';
import { KeyRound, Play } from 'lucide-react';

export default function LandingPage() {
  const router = useRouter();
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const { health, isBackendOffline } = useSettings();

  // URL & Token States
  const [repoUrl, setRepoUrl] = useState('');
  const [tokenDialogOpen, setTokenDialogOpen] = useState(false);
  const [githubToken, setGithubToken] = useState('');
  const [isStarting, setIsStarting] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);

  // Status checks
  const backendOk = !isBackendOffline;
  const dbOk = health?.database === 'ok' || health?.db === 'ok';
  const ollamaOk = health?.ollama === 'ok';

  // Handler for Start (Index Repo)
  const handleStart = async (validUrl: string) => {
    setIsStarting(true);
    try {
      const data = await api.post<{ repo_id: string; job_id: string }>('/repos', {
        url: validUrl,
        token: githubToken.trim() || undefined,
      });
      showToast.success('Repository added. Starting indexing quest...');
      router.push(`/repos/${data.repo_id}`);
    } catch (err: unknown) {
      const message = err instanceof ApiError ? err.message : 'Failed to add repository';
      showToast.error(message);
    } finally {
      setIsStarting(false);
    }
  };

  // Handler for Try Demo Mode
  const handleTryDemo = async () => {
    setIsDemoLoading(true);
    try {
      showToast.info('Loading bundled TaskBoard fixture 100% offline...');
      const data = await api.post<{ repo_id: string; full_name?: string }>('/demo/load');
      showToast.success(`Demo loaded: ${data.full_name || 'demo/taskboard'}`);
      router.push(`/repos/${data.repo_id}`);
    } catch (err: unknown) {
      const message = err instanceof ApiError ? err.message : 'Failed to load demo repository';
      showToast.error(message);
    } finally {
      setIsDemoLoading(false);
    }
  };

  // Headline words for rising sequence (A1)
  const line1Words = ['Help', 'maintainers', 'keep', 'up.'];
  const line2Words = ['Help', 'newcomers', 'get', 'started.'];

  return (
    <AppShell className="relative overflow-hidden">
      {/* Background contour terrain with 0 to 12% opacity */}
      <ContourBackground opacity={0.12} />

      <div className="relative z-10 space-y-16 py-6 md:py-12">
        {/* HERO SECTION: M1 Map Unfurl Choreography */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Left Column: Headline, Input, Buttons, Status */}
          <div className="lg:col-span-7 space-y-8">
            {/* Headline with rising words sequence */}
            <div className="space-y-1.5 font-display font-bold text-3xl sm:text-4xl md:text-5xl lg:text-6xl tracking-tight leading-[1.15]">
              {/* Line 1 */}
              <div className="flex flex-wrap gap-x-3 text-text">
                {line1Words.map((word, i) => (
                  <motion.span
                    key={`l1-${word}-${i}`}
                    initial={isStill ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={
                      isStill
                        ? { duration: 0 }
                        : { duration: 0.35, delay: 0.15 + i * 0.06, ease: ease.out }
                    }
                    className="inline-block"
                  >
                    {word}
                  </motion.span>
                ))}
              </div>

              {/* Line 2 with Aurora gradient sweep */}
              <div className="flex flex-wrap gap-x-3">
                {line2Words.map((word, i) => (
                  <motion.span
                    key={`l2-${word}-${i}`}
                    initial={isStill ? { opacity: 1, y: 0 } : { opacity: 0, y: 16 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={
                      isStill
                        ? { duration: 0 }
                        : {
                            duration: 0.35,
                            delay: 0.15 + (line1Words.length + i) * 0.06,
                            ease: ease.out,
                          }
                    }
                    className="inline-block bg-gradient-to-r from-brand via-brand-2 to-rose bg-clip-text text-transparent"
                    style={{
                      backgroundSize: '200% 100%',
                      animation: isStill ? 'none' : 'shimmer 3s ease-in-out infinite',
                    }}
                  >
                    {word}
                  </motion.span>
                ))}
              </div>
            </div>

            {/* Sub-headline description */}
            <motion.p
              initial={isStill ? { opacity: 1 } : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.45, duration: 0.3 }}
              className="text-base sm:text-lg text-text-muted max-w-xl leading-relaxed"
            >
              RepoQuest maps open source codebases into offline knowledge graphs. Triage issues, review PRs, and explore architectures 100% locally with Ollama and pgvector.
            </motion.p>

            {/* URL Input & Action Buttons (M1 step 3: 500ms snappy spring rise) */}
            <motion.div
              initial={isStill ? { opacity: 1, y: 0 } : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={isStill ? { duration: 0 } : { delay: 0.5, ...spring.snappy }}
              className="space-y-4 max-w-xl"
            >
              <div className="flex flex-col sm:flex-row gap-3">
                <ScanBeamInput
                  value={repoUrl}
                  onChange={setRepoUrl}
                  onSubmit={handleStart}
                  disabled={isStarting || isDemoLoading}
                  className="flex-1"
                />

                <Button
                  variant="primary"
                  loading={isStarting}
                  disabled={isStarting || isDemoLoading}
                  onClick={() => handleStart(repoUrl)}
                  className="h-14 px-6 text-base font-semibold shadow-md whitespace-nowrap min-w-[120px]"
                >
                  Start Quest
                </Button>
              </div>

              {/* Secondary Actions: Try Demo Mode & Add Token */}
              <div className="flex flex-wrap items-center justify-between gap-3 text-xs pt-1">
                <Button
                  variant="secondary"
                  size="sm"
                  loading={isDemoLoading}
                  disabled={isStarting || isDemoLoading}
                  onClick={handleTryDemo}
                  className="gap-2 border-brand/40 text-brand hover:bg-brand/10"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Try Demo Mode (Instant Offline)</span>
                </Button>

                <button
                  type="button"
                  onClick={() => setTokenDialogOpen(true)}
                  className="inline-flex items-center gap-1.5 text-text-muted hover:text-text hover:underline transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded p-1"
                >
                  <KeyRound className="w-3.5 h-3.5 text-amber" />
                  <span>
                    {githubToken ? 'Token configured ✓' : 'Add token for write access'}
                  </span>
                </button>
              </div>

              {/* Three Live Status Dots with A6 ripple */}
              <div className="flex items-center gap-6 pt-3 border-t border-border/50 text-xs font-mono">
                {/* Backend status */}
                <div className="flex items-center gap-2" title={backendOk ? 'FastAPI is online' : 'FastAPI is offline'}>
                  <span className="relative flex h-2.5 w-2.5">
                    {!isStill && backendOk && (
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-mint opacity-75" />
                    )}
                    <span
                      className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                        backendOk ? 'bg-mint' : 'bg-flame'
                      }`}
                    />
                  </span>
                  <span className={backendOk ? 'text-text' : 'text-flame font-medium'}>
                    Backend
                  </span>
                </div>

                {/* Database status */}
                <div
                  className="flex items-center gap-2"
                  title={dbOk ? 'PostgreSQL pgvector is online' : 'Database is down (fix: start postgres container)'}
                >
                  <span className="relative flex h-2.5 w-2.5">
                    {!isStill && dbOk && (
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-mint opacity-75" />
                    )}
                    <span
                      className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                        dbOk ? 'bg-mint' : 'bg-flame'
                      }`}
                    />
                  </span>
                  <span className={dbOk ? 'text-text' : 'text-flame font-medium'}>
                    Database
                  </span>
                </div>

                {/* Ollama status */}
                <div
                  className="flex items-center gap-2"
                  title={ollamaOk ? 'Local Ollama service is reachable' : 'Ollama is down (fix: run "ollama serve" or open /setup)'}
                >
                  <span className="relative flex h-2.5 w-2.5">
                    {!isStill && ollamaOk && (
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-mint opacity-75" />
                    )}
                    <span
                      className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                        ollamaOk ? 'bg-mint' : 'bg-flame'
                      }`}
                    />
                  </span>
                  <span className={ollamaOk ? 'text-text' : 'text-flame font-medium'}>
                    Ollama
                  </span>
                </div>
              </div>
            </motion.div>
          </div>

          {/* Right Column: Pixel Quest Map Realm (M1 step 4: 700ms diagonal wave) */}
          <div className="lg:col-span-5 flex justify-center lg:justify-end">
            <PixelQuestMap className="w-full max-w-sm sm:max-w-md" />
          </div>
        </section>

        {/* BOTTOM SECTION: Three Pillar Quest Cards */}
        <section className="space-y-6 pt-8 border-t border-border">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="font-display font-bold text-2xl text-text">Explore the Realm Pillars</h2>
              <p className="text-xs text-text-muted mt-1">
                Engineered for speed, privacy, and frictionless open-source workflows.
              </p>
            </div>
            <span className="text-xs font-mono text-text-muted hidden sm:inline">
              100% Offline Capable
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Pillar 1: Maintainer Autopilot */}
            <QuestCard glow showStrip>
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-lg bg-surface-2 border border-border flex items-center justify-center text-brand">
                  <PixelIcon name="shield" size={20} />
                </div>
                <div>
                  <h3 className="font-display font-bold text-lg text-text">
                    Maintainer Autopilot
                  </h3>
                  <p className="text-xs text-text-muted mt-1 leading-relaxed">
                    Automate issue triage, calculate Maintainer Load Index, detect duplicates with pgvector cosine distance, and scan pull requests for spam.
                  </p>
                </div>
                <div className="pt-2 flex flex-wrap gap-1.5 font-mono text-[11px] text-text-muted">
                  <span className="px-2 py-0.5 rounded bg-surface-2 border border-border">AI Triage</span>
                  <span className="px-2 py-0.5 rounded bg-surface-2 border border-border">Spam Shield</span>
                </div>
              </div>
            </QuestCard>

            {/* Pillar 2: Local-First AI */}
            <QuestCard glow showStrip>
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-lg bg-surface-2 border border-border flex items-center justify-center text-mint">
                  <PixelIcon name="lock" size={20} />
                </div>
                <div>
                  <h3 className="font-display font-bold text-lg text-text">
                    Local-First Privacy
                  </h3>
                  <p className="text-xs text-text-muted mt-1 leading-relaxed">
                    Zero tokens or code leave your machine. Runs with Ollama (Gemma 3, Llama 3.2) and local pgvector embeddings. Transparent AI audit log with one-click undo.
                  </p>
                </div>
                <div className="pt-2 flex flex-wrap gap-1.5 font-mono text-[11px] text-text-muted">
                  <span className="px-2 py-0.5 rounded bg-surface-2 border border-border">100% Local</span>
                  <span className="px-2 py-0.5 rounded bg-surface-2 border border-border">Audit Trail</span>
                </div>
              </div>
            </QuestCard>

            {/* Pillar 3: Newcomer Launchpad */}
            <QuestCard glow showStrip>
              <div className="space-y-3">
                <div className="w-10 h-10 rounded-lg bg-surface-2 border border-border flex items-center justify-center text-amber">
                  <PixelIcon name="compass" size={20} />
                </div>
                <div>
                  <h3 className="font-display font-bold text-lg text-text">
                    Newcomer Launchpad
                  </h3>
                  <p className="text-xs text-text-muted mt-1 leading-relaxed">
                    Interactive Living Codebase Map, Ask the Repo assistant with verified citations, Day-1 Tour with quizzes, and Issue Forge contributor briefs.
                  </p>
                </div>
                <div className="pt-2 flex flex-wrap gap-1.5 font-mono text-[11px] text-text-muted">
                  <span className="px-2 py-0.5 rounded bg-surface-2 border border-border">Living Map</span>
                  <span className="px-2 py-0.5 rounded bg-surface-2 border border-border">Day-1 Tour</span>
                </div>
              </div>
            </QuestCard>
          </div>
        </section>
      </div>

      {/* GitHub Personal Access Token Dialog */}
      <Dialog open={tokenDialogOpen} onOpenChange={setTokenDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>GitHub Personal Access Token</DialogTitle>
            <DialogDescription>
              Provide an optional GitHub fine-grained token with Issues and Pull Requests write access to allow autonomous labeling and reviews.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label className="text-xs font-mono text-text-muted block">
                Personal Access Token (classic or fine-grained)
              </label>
              <input
                type="password"
                value={githubToken}
                onChange={(e) => setGithubToken(e.target.value)}
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                className="w-full h-10 px-3 rounded-lg border border-border bg-surface-2 text-sm text-text font-mono focus:outline-none focus:ring-2 focus:ring-brand"
              />
            </div>

            <div className="p-3 rounded-lg bg-surface-2 border border-border text-xs text-text-muted space-y-1">
              <p className="font-medium text-text">Security Guarantee:</p>
              <p>
                Tokens are encrypted at rest with Fernet using your local APP_SECRET_KEY. They are never sent to Ollama or leaked in client bundles.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="secondary"
              onClick={() => {
                setGithubToken('');
                setTokenDialogOpen(false);
              }}
            >
              Clear
            </Button>
            <Button
              variant="primary"
              onClick={() => {
                setTokenDialogOpen(false);
                showToast.success('Token configured for session.');
              }}
            >
              Save Token
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
