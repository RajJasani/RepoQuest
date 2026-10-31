'use client';

import React, { useState, useMemo, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { useSettings } from '@/lib/settings-context';
import { api, ApiError } from '@/lib/api';
import {
  IssueDetail,
  IssueListResponse,
  IssueListResponseSchema,
  RepoDetail,
  RepoDetailSchema,
} from '@/lib/schemas';
import { AppShell } from '@/components/layout/AppShell';
import { QuestCard } from '@/components/ui/QuestCard';
import { Button } from '@/components/ui/Button';
import { StatusChip, StatusVariant } from '@/components/ui/StatusChip';
import { SeverityPill, SeverityLevel } from '@/components/ui/SeverityPill';
import { Stamp } from '@/components/motion/Stamp';
import { Pip } from '@/components/brand/Pip';
import { Skeleton } from '@/components/ui/Skeleton';
import { showToast } from '@/components/ui/Toast';
import { ease } from '@/lib/motion';
import {
  Search,
  RotateCcw,
  Copy,
  Check,
  Edit2,
  XCircle,
  CopyCheck,
  CheckCircle2,
  Sparkles,
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  FileQuestion,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface TriageInboxProps {
  repoId: string;
  initialIssueNumber?: number;
}

interface DuplicatesListProps {
  duplicates?: { number: number; similarity?: number; reason?: string }[];
  isStill: boolean;
}

function DuplicatesList({ duplicates, isStill }: DuplicatesListProps): React.JSX.Element | null {
  if (!duplicates || duplicates.length === 0) return null;

  return (
    <div className="space-y-2">
      <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted font-bold block">
        Duplicate Candidates (Vector Search)
      </span>
      <div className="space-y-2">
        {duplicates.map((dup, dIdx) => {
          const score = Number(dup.similarity || 0);
          const pct = Math.round(score * 100);

          return (
            <div
              key={dIdx}
              className="p-2.5 rounded-lg bg-surface-2/60 border border-border/60 space-y-1.5 font-mono text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-brand">#{dup.number}</span>
                <span className="text-[11px] text-text-muted">{pct}% similarity</span>
              </div>

              {/* Filling Similarity Bar */}
              <div className="h-1.5 w-full bg-surface-3 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-amber"
                  initial={isStill ? { width: `${pct}%` } : { width: '0%' }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.5, ease: ease.out }}
                />
              </div>

              {dup.reason && (
                <p className="text-[11px] text-text-muted font-sans leading-relaxed">
                  {dup.reason}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
export function TriageInbox({ repoId, initialIssueNumber }: TriageInboxProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { settings } = useSettings();

  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  // Filter & Search States
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Issue & Active Triage States
  const [selectedNumber, setSelectedNumber] = useState<number | null>(initialIssueNumber || null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isTriaging, setIsTriaging] = useState(false);
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [simulatedRequest, setSimulatedRequest] = useState<unknown | null>(null);

  // Editable reply draft & labels
  const [editableReply, setEditableReply] = useState<string>('');
  const [isEditingReply, setIsEditingReply] = useState(false);

  // M4 Approval choreography states
  const [stampActive, setStampActive] = useState(false);
  const [isNudging, setIsNudging] = useState(false);
  const [isCardCollapsed, setIsCardCollapsed] = useState(false);

  // 1. Fetch Repository Details
  const { data: repo } = useQuery<RepoDetail>({
    queryKey: ['repo', repoId],
    queryFn: async () => {
      const res = await api.get<unknown>(`/repos/${repoId}`);
      return RepoDetailSchema.parse(res);
    },
    enabled: Boolean(repoId),
  });

  // 2. Fetch Issues List
  const {
    data: issuesData,
    isLoading: isIssuesLoading,
        refetch: refetchIssues,
  } = useQuery<IssueListResponse>({
    queryKey: ['issues', repoId],
    queryFn: async () => {
      const res = await api.get<unknown>(`/repos/${repoId}/issues?page_size=100`);
      return IssueListResponseSchema.parse(res);
    },
    enabled: Boolean(repoId),
  });

  const issuesList = useMemo(() => issuesData?.items || [], [issuesData?.items]);

  // Filter issues
  const filteredIssues = useMemo(() => {
    return issuesList.filter((iss) => {
      // Status filter
      if (statusFilter !== 'all' && iss.triage_status !== statusFilter) {
        return false;
      }
      // Type filter
      if (typeFilter !== 'all' && iss.analysis?.type !== typeFilter) {
        return false;
      }
      // Severity filter
      if (severityFilter !== 'all' && iss.analysis?.severity !== severityFilter) {
        return false;
      }
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = iss.title.toLowerCase().includes(q);
        const matchBody = (iss.body || '').toLowerCase().includes(q);
        const matchNum = String(iss.number).includes(q);
        return matchTitle || matchBody || matchNum;
      }
      return true;
    });
  }, [issuesList, statusFilter, typeFilter, severityFilter, searchQuery]);

  // Set default selected issue if none selected
  useEffect(() => {
    if (selectedNumber === null && filteredIssues.length > 0) {
      setSelectedNumber(filteredIssues[0].number);
    }
  }, [filteredIssues, selectedNumber]);

  // Active Issue
  const activeIssue = useMemo(() => {
    return issuesList.find((i) => i.number === selectedNumber) || filteredIssues[0] || null;
  }, [issuesList, selectedNumber, filteredIssues]);

  // Sync draft reply with active issue analysis
  useEffect(() => {
    if (activeIssue?.analysis?.suggested_reply) {
      setEditableReply(activeIssue.analysis.suggested_reply);
    } else {
      setEditableReply('');
    }
    setIsEditingReply(false);
    setStampActive(false);
    setIsCardCollapsed(false);
    setSimulatedRequest(null);
  }, [activeIssue?.id, activeIssue?.analysis?.suggested_reply]);

  // Check write token & demo status
  const isDemoRepo = repo?.owner === 'demo' || repo?.full_name?.startsWith('demo/');
  const hasWriteToken = Boolean(settings?.has_github_token) || isDemoRepo;

  // Poll for triage completion when a triage job is started
  const pollTriageResult = useCallback(
    async (issueId: string) => {
      let attempts = 0;
      const maxAttempts = 20;

      while (attempts < maxAttempts) {
        await new Promise((r) => setTimeout(r, 1500));
        try {
          const updated = await api.get<IssueDetail>(`/issues/${issueId}`);
          if (updated && updated.analysis) {
            queryClient.setQueryData<IssueListResponse>(['issues', repoId], (old) => {
              if (!old) return old;
              return {
                ...old,
                items: old.items.map((it) => (it.id === issueId ? updated : it)),
              };
            });
            setIsTriaging(false);
            showToast.success(`Triage analysis completed for #${updated.number}`);
            return;
          }
        } catch {
          // Continue polling
        }
        attempts += 1;
      }

      setIsTriaging(false);
      showToast.warning('Triage processing is taking longer than expected. Please check back.');
    },
    [repoId, queryClient]
  );

  // Sync Issues from GitHub Handler
  const handleSyncIssues = async () => {
    setIsSyncing(true);
    try {
      const res = await api.post<{ synced_issues: number }>(`/repos/${repoId}/issues/sync`);
      showToast.success(`Synced ${res.synced_issues || 0} issues from repository`);
      refetchIssues();
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to sync issues';
      showToast.error(msg);
    } finally {
      setIsSyncing(false);
    }
  };

  // Re-run AI Triage on Active Issue
  const handleRerunTriage = async () => {
    if (!activeIssue) return;
    setIsTriaging(true);

    try {
      await api.post(`/issues/${activeIssue.id}/triage`);
      showToast.info(`Triage job enqueued for #${activeIssue.number}...`);
      pollTriageResult(activeIssue.id);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to enqueue triage';
      showToast.error(msg);
      setIsTriaging(false);
    }
  };

  // Reject Triage Handler
  const handleReject = async () => {
    if (!activeIssue) return;
    setIsRejecting(true);

    // Optimistic update
    const prevStatus = activeIssue.triage_status;
    queryClient.setQueryData<IssueListResponse>(['issues', repoId], (old) => {
      if (!old) return old;
      return {
        ...old,
        items: old.items.map((it) =>
          it.id === activeIssue.id ? { ...it, triage_status: 'rejected' } : it
        ),
      };
    });

    try {
      await api.post(`/issues/${activeIssue.id}/reject`);
      showToast.info(`Recommendation rejected for #${activeIssue.number}`);
    } catch (err: unknown) {
      // Rollback
      queryClient.setQueryData<IssueListResponse>(['issues', repoId], (old) => {
        if (!old) return old;
        return {
          ...old,
          items: old.items.map((it) =>
            it.id === activeIssue.id ? { ...it, triage_status: prevStatus } : it
          ),
        };
      });
      const msg = err instanceof ApiError ? err.message : 'Failed to reject triage';
      showToast.error(msg);
    } finally {
      setIsRejecting(false);
    }
  };

  // Approve Triage Handler (M4: Stamp, Nudge, Card Collapse, Undo Toast)
  const handleApprove = async () => {
    if (!activeIssue) return;
    setIsApproving(true);

    const prevIssue = { ...activeIssue };
    const targetId = activeIssue.id;
    const targetNum = activeIssue.number;
    const finalLabels = activeIssue.analysis?.labels || [];
    const finalComment = editableReply.trim();

    // 1. M4 Stamp drops with bouncy spring and card compresses
    setStampActive(true);
    if (!isStill) {
      setIsNudging(true);
      setTimeout(() => setIsNudging(false), 300);
    }

    // 2. Card collapses after 500ms
    setTimeout(() => {
      setIsCardCollapsed(true);
    }, 500);

    // 3. Optimistic UI update
    queryClient.setQueryData<IssueListResponse>(['issues', repoId], (old) => {
      if (!old) return old;
      return {
        ...old,
        items: old.items.map((it) =>
          it.id === targetId
            ? {
                ...it,
                triage_status: isDemoRepo ? 'applied' : 'approved',
                labels: finalLabels,
              }
            : it
        ),
      };
    });

    try {
      const res = await api.post<{
        status: string;
        labels: string[];
        comment: string;
        simulated?: boolean;
        request?: unknown;
      }>(`/issues/${targetId}/approve`, {
        labels: finalLabels,
        comment: finalComment,
        post_to_github: hasWriteToken,
      });

      if (res.simulated) {
        setSimulatedRequest(res.request);
      }

      // Show Undo Toast with draining progress line
      showToast.undo(
        `Approved triage for #${targetNum}`,
        async () => {
          // Revert locally
          queryClient.setQueryData<IssueListResponse>(['issues', repoId], (old) => {
            if (!old) return old;
            return {
              ...old,
              items: old.items.map((it) => (it.id === targetId ? prevIssue : it)),
            };
          });
          setIsCardCollapsed(false);
          setStampActive(false);
          showToast.info(`Reverted approval for #${targetNum}`);
        },
        5000
      );
    } catch (err: unknown) {
      // Rollback on failure
      queryClient.setQueryData<IssueListResponse>(['issues', repoId], (old) => {
        if (!old) return old;
        return {
          ...old,
          items: old.items.map((it) => (it.id === targetId ? prevIssue : it)),
        };
      });
      setIsCardCollapsed(false);
      setStampActive(false);
      const msg = err instanceof ApiError ? err.message : 'Approval failed';
      showToast.error(msg);
    } finally {
      setIsApproving(false);
    }
  };

  const copyCommentToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    showToast.success('Suggested reply copied to clipboard');
  };

  const getTriageStatusVariant = (st: string): StatusVariant => {
    switch (st) {
      case 'applied':
        return 'mint';
      case 'approved':
        return 'sky';
      case 'suggested':
        return 'amber';
      case 'rejected':
        return 'rose';
      default:
        return 'neutral';
    }
  };

  return (
    <AppShell className="p-0 overflow-hidden flex flex-col h-[calc(100vh-3.5rem)]">
      {/* TOP HEADER: Filters & Sync Actions */}
      <header className="h-14 border-b border-border bg-surface-1/95 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between gap-4 shrink-0 z-10">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-display font-bold text-sm text-text">Triage Inbox</span>
            {repo && (
              <span className="font-mono text-xs text-text-muted hidden sm:inline">
                ({repo.full_name})
              </span>
            )}
          </div>

          {/* Search Box */}
          <div className="relative flex items-center">
            <Search className="w-3.5 h-3.5 text-text-muted absolute left-2.5 pointer-events-none" />
            <input
              type="text"
              placeholder="Filter issues..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-36 sm:w-48 pl-8 pr-2.5 py-1 text-xs font-mono bg-surface-2 border border-border rounded-lg text-text placeholder:text-text-muted/60 focus:outline-none focus:ring-1 focus:ring-brand"
            />
          </div>
        </div>

        {/* Filter Dropdowns & Sync Button */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2 py-1 text-xs font-mono bg-surface-2 border border-border rounded-lg text-text focus:outline-none focus:ring-1 focus:ring-brand cursor-pointer"
          >
            <option value="all">All Status</option>
            <option value="untriaged">Untriaged</option>
            <option value="suggested">Suggested</option>
            <option value="approved">Approved</option>
            <option value="applied">Applied</option>
          </select>

          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-2 py-1 text-xs font-mono bg-surface-2 border border-border rounded-lg text-text focus:outline-none focus:ring-1 focus:ring-brand cursor-pointer hidden md:block"
          >
            <option value="all">All Types</option>
            <option value="bug">Bug</option>
            <option value="feature">Feature</option>
            <option value="question">Question</option>
            <option value="docs">Docs</option>
            <option value="chore">Chore</option>
            <option value="spam">Spam</option>
          </select>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-2 py-1 text-xs font-mono bg-surface-2 border border-border rounded-lg text-text focus:outline-none focus:ring-1 focus:ring-brand cursor-pointer hidden md:block"
          >
            <option value="all">All Severity</option>
            <option value="P0">P0 Critical</option>
            <option value="P1">P1 High</option>
            <option value="P2">P2 Medium</option>
            <option value="P3">P3 Low</option>
          </select>

          {/* Sync Issues Button */}
          <Button
            variant="secondary"
            onClick={handleSyncIssues}
            loading={isSyncing}
            className="gap-1.5 text-xs h-8"
            title="Sync open issues from GitHub"
          >
            <RefreshCw className={cn('w-3.5 h-3.5', isSyncing && 'animate-spin')} />
            <span className="hidden sm:inline">Sync Issues</span>
          </Button>
        </div>
      </header>

      {/* SPLIT VIEW BODY */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 min-h-0 overflow-hidden divide-y lg:divide-y-0 lg:divide-x divide-border">
        {/* LEFT COLUMN: 48px Dense List Rows (40% on desktop) */}
        <section
          className="lg:col-span-5 h-full overflow-y-auto bg-surface-1/40 flex flex-col"
          aria-label="Issues list"
        >
          {isIssuesLoading ? (
            <div className="p-4 space-y-2">
              <Skeleton className="h-12 w-full rounded-xl" />
              <Skeleton className="h-12 w-full rounded-xl" />
              <Skeleton className="h-12 w-full rounded-xl" />
              <Skeleton className="h-12 w-full rounded-xl" />
            </div>
          ) : filteredIssues.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-4 font-mono text-xs">
              <Pip state="idle" size={64} />
              <div>
                <p className="font-display font-bold text-sm text-text">
                  Inbox zero. Even the bots are impressed.
                </p>
                <p className="text-text-muted mt-1 text-[11px] font-sans">
                  No issues matching the active filters or awaiting maintainer triage.
                </p>
              </div>
            </div>
          ) : (
            <div className="divide-y divide-border/60">
              {filteredIssues.map((iss) => {
                const isSelected = activeIssue?.id === iss.id;
                const hasDuplicates = (iss.analysis?.duplicates || []).length > 0;
                const severity = (iss.analysis?.severity as SeverityLevel) || 'P2';

                return (
                  // A15: New issue slides into the list with soft highlight
                  <motion.div
                    key={iss.id}
                    initial={isStill ? false : { y: -16, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ duration: 0.3, ease: ease.out }}
                    onClick={() => {
                      setSelectedNumber(iss.number);
                      router.replace(`/repos/${repoId}/issues/${iss.number}`, { scroll: false });
                    }}
                    className={cn(
                      'h-12 px-3 sm:px-4 flex items-center justify-between gap-3 text-xs cursor-pointer select-none transition-colors border-l-2',
                      isSelected
                        ? 'bg-surface-2 border-brand font-medium'
                        : 'border-transparent hover:bg-surface-2/50 text-text-muted'
                    )}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      {/* Issue Number & Severity Pill */}
                      <span className="font-mono text-xs text-text-muted shrink-0">
                        #{iss.number}
                      </span>
                      <SeverityPill level={severity} className="shrink-0" />

                      {/* Title */}
                      <span className="truncate text-text font-sans text-xs">
                        {iss.title}
                      </span>

                      {/* Duplicate Icon */}
                      {hasDuplicates && (
                        <span
                          className="shrink-0 text-amber"
                          title={`${iss.analysis?.duplicates.length} duplicate candidates found`}
                        >
                          <CopyCheck className="w-3.5 h-3.5" />
                        </span>
                      )}
                    </div>

                    {/* Status Chip */}
                    <StatusChip
                      variant={getTriageStatusVariant(iss.triage_status)}
                      label={iss.triage_status}
                      className="shrink-0"
                    />
                  </motion.div>
                );
              })}
            </div>
          )}
        </section>

        {/* RIGHT COLUMN: Selected Issue & AI Analysis Quest Card (60% on desktop) */}
        <section
          className={cn(
            'lg:col-span-7 h-full overflow-y-auto p-4 sm:p-6 space-y-6 bg-surface-1',
            isNudging && 'translate-x-1 transition-transform duration-75'
          )}
          aria-label="Triage Analysis"
        >
          {activeIssue ? (
            <div className="space-y-6 max-w-3xl mx-auto">
              {/* Issue Header */}
              <div className="space-y-2 border-b border-border pb-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-base font-bold text-brand">
                      #{activeIssue.number}
                    </span>
                    <h2 className="font-display font-bold text-lg sm:text-xl text-text">
                      {activeIssue.title}
                    </h2>
                  </div>

                  <a
                    href={activeIssue.html_url || `https://github.com/${repo?.full_name}/issues/${activeIssue.number}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-text-muted hover:text-text text-xs font-mono inline-flex items-center gap-1 shrink-0"
                  >
                    <span>GitHub</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-text-muted">
                  <span>Author: @{activeIssue.author || 'contributor'}</span>
                  <span>·</span>
                  <StatusChip
                    variant={getTriageStatusVariant(activeIssue.triage_status)}
                    label={activeIssue.triage_status}
                  />
                  {activeIssue.analysis?.type && (
                    <span className="px-2 py-0.5 rounded bg-surface-2 border border-border uppercase text-[10px] font-bold text-text">
                      {activeIssue.analysis.type}
                    </span>
                  )}
                </div>
              </div>

              {/* Issue Original Body */}
              <div className="space-y-1.5">
                <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted font-bold block">
                  Original Issue Description
                </span>
                <div className="p-4 rounded-xl bg-surface-2/50 border border-border/80 text-xs text-text font-sans leading-relaxed whitespace-pre-wrap max-h-48 overflow-y-auto">
                  {activeIssue.body || 'No description provided.'}
                </div>
              </div>

              {/* AI ANALYSIS QUEST CARD (Hero moment M4: A16 sequence reveal) */}
              <AnimatePresence>
                {!isCardCollapsed && (
                  <motion.div
                    layout
                    initial={{ opacity: 1, scale: 1 }}
                    animate={{
                      scale: stampActive ? 0.98 : 1,
                      opacity: 1,
                    }}
                    exit={{
                      height: 0,
                      opacity: 0,
                      transition: { duration: 0.35, ease: ease.in },
                    }}
                    className="relative"
                  >
                    {/* M4 APPROVED STAMP OVERLAY */}
                    {stampActive && (
                      <div className="absolute inset-0 z-30 flex items-center justify-center pointer-events-none">
                        <Stamp text="APPROVED" variant="mint" />
                      </div>
                    )}

                    <QuestCard
                      showStrip={true}
                      glow={true}
                      className={cn(
                        'transition-transform duration-200',
                        stampActive && 'opacity-90 blur-[0.5px]'
                      )}
                    >
                      <div className="space-y-5">
                        {/* Analysis Card Header: Type, Severity, Labels */}
                        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
                          <div className="flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-brand" />
                            <h3 className="font-display font-bold text-sm text-text">
                              AI Triage Assessment
                            </h3>
                          </div>

                          <div className="flex items-center gap-2">
                            {activeIssue.analysis?.severity && (
                              <SeverityPill
                                level={activeIssue.analysis.severity as SeverityLevel}
                                showFullLabel
                              />
                            )}
                            {activeIssue.analysis?.confidence !== undefined && (
                              <span className="font-mono text-xs text-text-muted px-2 py-0.5 rounded bg-surface-2 border border-border">
                                Confidence: {Math.round((activeIssue.analysis.confidence || 0) * 100)}%
                              </span>
                            )}
                          </div>
                        </div>

                        {(() => {
                          if (isTriaging) {
                            return (
                              <div className="py-12 flex flex-col items-center justify-center space-y-4 text-center">
                                <Pip state="thinking" size={72} />
                                <p className="font-mono text-xs text-text-muted">
                                  Evaluating issue context, duplicate vectors, and repository labels...
                                </p>
                              </div>
                            );
                          }
                          const analysis = activeIssue.analysis;
                          if (!analysis) {
                            return (
                              <div className="py-8 flex flex-col items-center justify-center text-center space-y-3 font-mono text-xs">
                                <FileQuestion className="w-8 h-8 text-text-muted/40" />
                                <p className="text-text-muted">
                                  This issue has not yet been analyzed by the autonomous triage pipeline.
                                </p>
                                <Button
                                  variant="primary"
                                  onClick={handleRerunTriage}
                                  loading={isTriaging}
                                  className="gap-2 text-xs"
                                >
                                  <Sparkles className="w-3.5 h-3.5" />
                                  <span>Run AI Triage</span>
                                </Button>
                              </div>
                            );
                          }
                          return (
                          <>
                            {/* Summary */}
                            <div className="space-y-1">
                              <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted font-bold block">
                                Summary
                              </span>
                              <p className="text-xs text-text font-sans leading-relaxed">
                                {analysis.summary || 'Summary unavailable.'}
                              </p>
                            </div>

                            {/* Label Chips */}
                            {Boolean(analysis.labels && analysis.labels.length > 0) ? (
                              <div className="space-y-1.5">
                                <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted font-bold block">
                                  Recommended Labels
                                </span>
                                <div className="flex flex-wrap gap-1.5">
                                  {analysis.labels.map((lbl) => (
                                    <span
                                      key={lbl}
                                      className="px-2 py-0.5 rounded-md font-mono text-xs bg-brand/10 text-brand border border-brand/30"
                                    >
                                      {lbl}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            ) : null}

                            {/* Missing Info List */}
                            {Boolean(analysis.missing_info && analysis.missing_info.length > 0) ? (
                                <div className="space-y-1.5 p-3 rounded-xl bg-amber/10 border border-amber/20 font-mono text-xs">
                                  <div className="flex items-center gap-1.5 font-bold text-amber">
                                    <AlertTriangle className="w-3.5 h-3.5" />
                                    <span>Missing Reproduction Context</span>
                                  </div>
                                  <ul className="list-disc list-inside space-y-0.5 text-text-muted text-[11px]">
                                    {analysis.missing_info.map((item, idx) => (
                                      <li key={idx}>{item}</li>
                                    ))}
                                  </ul>
                                </div>
                              ) : null}

                            {/* Duplicate Candidates with Similarity Bars (Fill over 500ms) */}
                            <DuplicatesList duplicates={analysis.duplicates} isStill={isStill} />

                            {/* Good First Issue Meter */}
                            {analysis.good_first_issue_score !== undefined && analysis.good_first_issue_score !== null ? (
                              <div className="space-y-1 font-mono text-xs">
                                <div className="flex items-center justify-between">
                                  <span className="text-text-muted">Good First Issue Score:</span>
                                  <span className="font-bold text-mint">
                                    {analysis.good_first_issue_score}/100
                                  </span>
                                </div>
                                <div className="h-1.5 w-full bg-surface-3 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-mint"
                                    style={{
                                      width: `${analysis.good_first_issue_score}%`,
                                    }}
                                  />
                                </div>
                              </div>
                            ) : null}

                            {/* Suggested Reply (Editable Draft) */}
                            <div className="space-y-1.5">
                              <div className="flex items-center justify-between">
                                <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted font-bold">
                                  Suggested Reply Draft
                                </span>
                                <Button
                                  variant="ghost"
                                  onClick={() => setIsEditingReply(!isEditingReply)}
                                  className="h-6 px-2 text-[11px] font-mono gap-1 text-text-muted hover:text-text"
                                >
                                  <Edit2 className="w-3 h-3" />
                                  <span>{isEditingReply ? 'Done' : 'Edit'}</span>
                                </Button>
                              </div>

                              <textarea
                                value={editableReply}
                                onChange={(e) => setEditableReply(e.target.value)}
                                disabled={!isEditingReply}
                                rows={4}
                                className={cn(
                                  'w-full p-3 rounded-xl font-sans text-xs text-text border leading-relaxed focus:outline-none transition-colors',
                                  isEditingReply
                                    ? 'bg-surface-2 border-brand ring-1 ring-brand'
                                    : 'bg-surface-2/40 border-border/80'
                                )}
                              />

                              {/* Warning: Comments cannot be un-posted */}
                              <p className="text-[11px] font-mono text-text-muted/70 italic">
                                Note: Comments cannot be un-posted automatically once submitted to GitHub.
                              </p>
                            </div>

                            {/* Action Buttons: Approve, Copy, Edit, Reject, Re-run */}
                            <div className="pt-2 flex flex-wrap items-center gap-2">
                              {/* Primary Action: Approve (or Copy Comment if no write token) */}
                              {hasWriteToken ? (
                                <Button
                                  variant="primary"
                                  onClick={handleApprove}
                                  loading={isApproving}
                                  disabled={stampActive}
                                  className="gap-1.5 text-xs shadow-sm"
                                >
                                  <Check className="w-4 h-4" />
                                  <span>{isDemoRepo ? 'Approve (demo)' : 'Approve and post'}</span>
                                </Button>
                              ) : (
                                <Button
                                  variant="primary"
                                  onClick={() => copyCommentToClipboard(editableReply)}
                                  className="gap-1.5 text-xs shadow-sm"
                                >
                                  <Copy className="w-4 h-4" />
                                  <span>Copy comment</span>
                                </Button>
                              )}

                              {/* Secondary Copy Comment */}
                              <Button
                                variant="secondary"
                                onClick={() => copyCommentToClipboard(editableReply)}
                                className="gap-1.5 text-xs"
                              >
                                <Copy className="w-3.5 h-3.5" />
                                <span>Copy comment</span>
                              </Button>

                              {/* Reject */}
                              <Button
                                variant="ghost"
                                onClick={handleReject}
                                loading={isRejecting}
                                className="gap-1.5 text-xs text-text-muted hover:text-rose hover:bg-rose/10"
                              >
                                <XCircle className="w-3.5 h-3.5" />
                                <span>Reject</span>
                              </Button>

                              {/* Re-run Triage */}
                              <Button
                                variant="ghost"
                                onClick={handleRerunTriage}
                                loading={isTriaging}
                                className="gap-1.5 text-xs text-text-muted hover:text-text ml-auto font-mono"
                                title="Re-run AI Triage pipeline"
                              >
                                <RotateCcw className="w-3.5 h-3.5" />
                                <span>Re-run</span>
                              </Button>
                            </div>

                            {/* Simulated Demo Request Display */}
                            {simulatedRequest && (
                              <div className="mt-3 p-3 rounded-xl bg-surface-2 border border-mint/30 space-y-1 font-mono text-[11px]">
                                <span className="font-bold text-mint flex items-center gap-1">
                                  <CheckCircle2 className="w-3.5 h-3.5" />
                                  <span>Simulated GitHub Request:</span>
                                </span>
                                <pre className="overflow-x-auto text-text-muted whitespace-pre-wrap">
                                  {JSON.stringify(simulatedRequest, null, 2)}
                                </pre>
                              </div>
                            )}

                            {/* Card Footer: Model and Prompt Version */}
                            <div className="pt-3 border-t border-border/40 flex items-center justify-between text-[11px] font-mono text-text-muted/60">
                              <span>Model: {analysis.model || 'gemma3:4b'}</span>
                              <span>Prompt: {analysis.prompt_version || 'v1'}</span>
                            </div>
                          </>
                          );
                        })()}
                      </div>
                    </QuestCard>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-2 font-mono text-xs text-text-muted">
              <p>Select an issue from the left inbox to inspect triage assessment.</p>
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}

export default TriageInbox;
