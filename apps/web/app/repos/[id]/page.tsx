'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { RepoDetail, IssueListResponse, PRListResponse, AuditListResponse } from '@/lib/schemas';
import { AppShell } from '@/components/layout/AppShell';
import { IndexingView } from '@/components/indexing/IndexingView';
import { LanguageBar } from '@/components/repo/LanguageBar';
import { SignatureStrip } from '@/components/brand/SignatureStrip';
import { QuestCard } from '@/components/ui/QuestCard';
import { Button } from '@/components/ui/Button';
import { StatusChip } from '@/components/ui/StatusChip';
import { EmptyState } from '@/components/states/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  Star,
  ExternalLink,
  Bot,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  AlertCircle,
  RotateCcw,
} from 'lucide-react';

export default function RepoDetailPage() {
  const params = useParams();
  const repoId = String(params.id || '');

  // 1. Fetch Repository Details
  const {
    data: repo,
    isLoading: isRepoLoading,
    error: repoError,
    refetch: refetchRepo,
  } = useQuery<RepoDetail>({
    queryKey: ['repo', repoId],
    queryFn: () => api.get<RepoDetail>(`/repos/${repoId}`),
    enabled: Boolean(repoId),
    staleTime: 5000,
  });

  // 2. Fetch Live Issues Count for Maintainer Autopilot
  const { data: issuesData } = useQuery<IssueListResponse>({
    queryKey: ['repo-issues', repoId],
    queryFn: () => api.get<IssueListResponse>(`/repos/${repoId}/issues?page_size=1`),
    enabled: Boolean(repo?.status === 'ready'),
    staleTime: 15000,
  });

  // 3. Fetch Live PRs for Maintainer Autopilot
  const { data: prsData } = useQuery<PRListResponse>({
    queryKey: ['repo-prs', repoId],
    queryFn: () => api.get<PRListResponse>(`/repos/${repoId}/prs`),
    enabled: Boolean(repo?.status === 'ready'),
    staleTime: 15000,
  });

  // 4. Fetch Recent Audit Entries
  const { data: auditData } = useQuery<AuditListResponse>({
    queryKey: ['repo-audit', repoId],
    queryFn: () => api.get<AuditListResponse>(`/audit?repo_id=${repoId}&page=1`),
    enabled: Boolean(repo?.status === 'ready'),
    staleTime: 10000,
  });

  // Loading Skeleton State
  if (isRepoLoading) {
    return (
      <AppShell>
        <div className="max-w-6xl mx-auto py-8 space-y-6">
          <div className="space-y-2">
            <Skeleton className="h-8 w-64" />
            <Skeleton className="h-4 w-96" />
          </div>
          <Skeleton className="h-12 w-full" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Skeleton className="h-56 w-full" />
            <Skeleton className="h-56 w-full" />
            <Skeleton className="h-56 w-full" />
          </div>
        </div>
      </AppShell>
    );
  }

  // Error State
  if (repoError || !repo) {
    return (
      <AppShell>
        <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
          <div className="p-3 bg-flame/10 text-flame rounded-full inline-flex border border-flame/30">
            <AlertCircle className="w-8 h-8" />
          </div>
          <h2 className="font-display font-bold text-xl text-text">
            Repository Not Found
          </h2>
          <p className="text-xs text-text-muted">
            The requested repository could not be located in local storage.
          </p>
          <div className="pt-2 flex justify-center gap-3">
            <Button variant="secondary" onClick={() => refetchRepo()} className="gap-2">
              <RotateCcw className="w-4 h-4" />
              <span>Retry</span>
            </Button>
            <Link href="/repos">
              <Button variant="primary">Back to Repositories</Button>
            </Link>
          </div>
        </div>
      </AppShell>
    );
  }

  // If Status is NOT READY (e.g. queued, fetching, chunking, embedding, summarizing, or failed):
  // Render hero moment M2 Indexing View!
  if (repo.status !== 'ready') {
    return (
      <AppShell>
        <IndexingView repo={repo} onComplete={() => refetchRepo()} />
      </AppShell>
    );
  }

  // Repository Overview Screen (Status is Ready)
  const totalIssues = issuesData?.total ?? 0;
  const openPrs = (prsData || []).filter((p) => p.state === 'open').length;
  const spamPrs = (prsData || []).filter((p) => (p.spam_assessment?.spam_score || 0) >= 70).length;

  return (
    <AppShell>
      <div className="max-w-6xl mx-auto py-6 space-y-10">
        {/* TOP HEADER: Repo Name, Stars, External Link, Language Bar */}
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="font-display font-extrabold text-2xl sm:text-3xl text-text tracking-tight">
                  {repo.full_name}
                </h1>
                <StatusChip variant="mint" label="Ready" />
                <SignatureStrip variant="divider" size={5} />
              </div>
              {repo.description && (
                <p className="text-xs text-text-muted max-w-2xl leading-relaxed">
                  {repo.description}
                </p>
              )}
            </div>

            {/* Quick Actions & Stars */}
            <div className="flex items-center gap-3 shrink-0">
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-surface-2/80 rounded-lg border border-border text-xs font-mono font-medium text-text">
                <Star className="w-3.5 h-3.5 text-amber fill-amber" />
                <span>{repo.stars.toLocaleString()}</span>
              </div>
              <a
                href={`https://github.com/${repo.full_name}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-surface-2 hover:bg-surface-3 rounded-lg border border-border text-xs font-mono text-text transition-colors"
              >
                <span>GitHub</span>
                <ExternalLink className="w-3 h-3 text-text-muted" />
              </a>
            </div>
          </div>

          {/* Animated Language Bar */}
          {repo.languages && Object.keys(repo.languages).length > 0 && (
            <div className="pt-2">
              <LanguageBar languages={repo.languages} />
            </div>
          )}
        </div>

        {/* MIDDLE SECTION: Three Pillar Quest Cards */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs uppercase font-bold text-text-muted tracking-wider">
              Core Autopilot Pillars
            </span>
            <span className="text-xs font-mono text-text-muted">
              {repo.file_count} files indexed
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Pillar 1: Maintainer Autopilot */}
            <QuestCard showStrip={true} glow={true} className="flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-brand/10 text-brand">
                      <Bot className="w-4 h-4" />
                    </div>
                    <h3 className="font-display font-bold text-base text-text">
                      Maintainer Autopilot
                    </h3>
                  </div>
                  <span className="font-mono text-xs font-bold text-brand bg-brand/10 px-2 py-0.5 rounded">
                    F2 · F3
                  </span>
                </div>

                <p className="text-xs text-text-muted leading-relaxed">
                  Automate issue triage classification, duplicate detection, and structured pull request reviews.
                </p>

                {/* Live Counts */}
                <div className="grid grid-cols-3 gap-2 py-2 border-y border-border/60 font-mono text-center">
                  <div className="bg-surface-2/60 p-2 rounded">
                    <span className="text-xs font-bold text-text block">{totalIssues}</span>
                    <span className="text-[10px] text-text-muted">Issues</span>
                  </div>
                  <div className="bg-surface-2/60 p-2 rounded">
                    <span className="text-xs font-bold text-sky block">{openPrs}</span>
                    <span className="text-[10px] text-text-muted">Open PRs</span>
                  </div>
                  <div className="bg-surface-2/60 p-2 rounded">
                    <span className="text-xs font-bold text-rose block">{spamPrs}</span>
                    <span className="text-[10px] text-text-muted">Spam</span>
                  </div>
                </div>
              </div>

              {/* Links */}
              <div className="pt-4 flex flex-col gap-1.5 font-mono text-xs">
                <Link
                  href={`/repos/${repo.id}/issues`}
                  className="flex items-center justify-between p-1.5 rounded hover:bg-surface-2 text-text-muted hover:text-text transition-colors"
                >
                  <span>Triage Inbox</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <Link
                  href={`/repos/${repo.id}/prs`}
                  className="flex items-center justify-between p-1.5 rounded hover:bg-surface-2 text-text-muted hover:text-text transition-colors"
                >
                  <span>PR Review Bot</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <Link
                  href={`/repos/${repo.id}/spam`}
                  className="flex items-center justify-between p-1.5 rounded hover:bg-surface-2 text-text-muted hover:text-text transition-colors"
                >
                  <span>Spam Shield</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </QuestCard>

            {/* Pillar 2: Local-First Privacy */}
            <QuestCard showStrip={true} glow={true} className="flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-mint/10 text-mint">
                      <ShieldCheck className="w-4 h-4" />
                    </div>
                    <h3 className="font-display font-bold text-base text-text">
                      Local-First Privacy
                    </h3>
                  </div>
                  <span className="font-mono text-xs font-bold text-mint bg-mint/10 px-2 py-0.5 rounded">
                    100% Local
                  </span>
                </div>

                <p className="text-xs text-text-muted leading-relaxed">
                  AST code chunking stored in pgvector with local embeddings. Zero token egress to third-party clouds.
                </p>

                {/* Live Stats */}
                <div className="grid grid-cols-2 gap-2 py-2 border-y border-border/60 font-mono text-center">
                  <div className="bg-surface-2/60 p-2 rounded">
                    <span className="text-xs font-bold text-mint block">pgvector</span>
                    <span className="text-[10px] text-text-muted">Storage</span>
                  </div>
                  <div className="bg-surface-2/60 p-2 rounded">
                    <span className="text-xs font-bold text-text block">{repo.file_count}</span>
                    <span className="text-[10px] text-text-muted">Files Ingested</span>
                  </div>
                </div>
              </div>

              {/* Links */}
              <div className="pt-4 flex flex-col gap-1.5 font-mono text-xs">
                <Link
                  href={`/repos/${repo.id}/explore`}
                  className="flex items-center justify-between p-1.5 rounded hover:bg-surface-2 text-text-muted hover:text-text transition-colors"
                >
                  <span>Architecture Explorer</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <Link
                  href="/models"
                  className="flex items-center justify-between p-1.5 rounded hover:bg-surface-2 text-text-muted hover:text-text transition-colors"
                >
                  <span>Model Lab & Benchmarks</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </QuestCard>

            {/* Pillar 3: Newcomer Launchpad */}
            <QuestCard showStrip={true} glow={true} className="flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-sky/10 text-sky">
                      <Sparkles className="w-4 h-4" />
                    </div>
                    <h3 className="font-display font-bold text-base text-text">
                      Newcomer Launchpad
                    </h3>
                  </div>
                  <span className="font-mono text-xs font-bold text-sky bg-sky/10 px-2 py-0.5 rounded">
                    F7 · F8
                  </span>
                </div>

                <p className="text-xs text-text-muted leading-relaxed">
                  Interactive Day-1 Tour with quizzes, skill matching, and AI-rewritten issue briefs for contributors.
                </p>

                {/* Launchpad Status */}
                <div className="grid grid-cols-2 gap-2 py-2 border-y border-border/60 font-mono text-center">
                  <div className="bg-surface-2/60 p-2 rounded">
                    <span className="text-xs font-bold text-sky block">Day-1 Tour</span>
                    <span className="text-[10px] text-text-muted">Onboarding</span>
                  </div>
                  <div className="bg-surface-2/60 p-2 rounded">
                    <span className="text-xs font-bold text-text block">Issue Forge</span>
                    <span className="text-[10px] text-text-muted">Skill Match</span>
                  </div>
                </div>
              </div>

              {/* Links */}
              <div className="pt-4 flex flex-col gap-1.5 font-mono text-xs">
                <Link
                  href={`/repos/${repo.id}/onboarding`}
                  className="flex items-center justify-between p-1.5 rounded hover:bg-surface-2 text-text-muted hover:text-text transition-colors"
                >
                  <span>Day-1 Tour</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <Link
                  href={`/repos/${repo.id}/launchpad`}
                  className="flex items-center justify-between p-1.5 rounded hover:bg-surface-2 text-text-muted hover:text-text transition-colors"
                >
                  <span>Good First Issue Forge</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <Link
                  href={`/repos/${repo.id}/ask`}
                  className="flex items-center justify-between p-1.5 rounded hover:bg-surface-2 text-text-muted hover:text-text transition-colors"
                >
                  <span>Ask the Repo</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </QuestCard>
          </div>
        </section>

        {/* BOTTOM SECTION: Health Summary & Recent Audit Entries */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Health Summary Area (Shows EmptyState until F11 Health feature is created) */}
          <div className="lg:col-span-5 space-y-4">
            <span className="font-mono text-xs uppercase font-bold text-text-muted tracking-wider block">
              Maintainer Health Summary
            </span>
            <div className="p-6 bg-surface-1 border border-border rounded-2xl h-full flex flex-col justify-center">
              <EmptyState
                title="Maintainer Health Dashboard"
                description="Load index metrics, weekly AI digests, and response trends will unlock as triage decisions and PR reviews are conducted."
                actionLabel="Inspect Health Hub"
                actionHref={`/repos/${repo.id}/health`}
                pipState="thinking"
              />
            </div>
          </div>

          {/* Recent Audit Entries */}
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs uppercase font-bold text-text-muted tracking-wider">
                Recent AI Actions & Audit Log
              </span>
              <Link
                href="/audit"
                className="text-xs font-mono text-brand hover:underline flex items-center gap-1"
              >
                <span>Full Log</span>
                <ArrowRight className="w-3 h-3" />
              </Link>
            </div>

            <div className="bg-surface-1 border border-border rounded-2xl p-4 overflow-hidden">
              {auditData?.items && auditData.items.length > 0 ? (
                <div className="divide-y divide-border/60">
                  {auditData.items.slice(0, 5).map((item) => (
                    <div
                      key={item.id}
                      className="py-3 first:pt-0 last:pb-0 flex items-center justify-between gap-4 font-mono text-xs"
                    >
                      <div className="space-y-0.5 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-text capitalize">
                            {item.feature}
                          </span>
                          <span className="text-[11px] text-text-muted">
                            ({item.action})
                          </span>
                        </div>
                        <div className="text-[11px] text-text-muted truncate">
                          {item.model ? `Model: ${item.model}` : 'Local Pipeline'}
                          {item.latency_ms ? ` · ${item.latency_ms}ms` : ''}
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <StatusChip
                          variant={item.outcome === 'ok' ? 'mint' : 'rose'}
                          label={item.outcome}
                        />
                        <span className="text-[10px] text-text-muted hidden sm:inline">
                          {new Date(item.ts).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-8 text-center text-xs text-text-muted font-mono">
                  No AI actions recorded yet. Ingest issues or PRs to generate audit records.
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
