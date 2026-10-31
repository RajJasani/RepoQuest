'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '@/lib/api';
import { ReposListResponse, ReposListResponseSchema, RepoSummary } from '@/lib/schemas';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';
import { Button } from '@/components/ui/Button';
import { StatusChip, StatusVariant } from '@/components/ui/StatusChip';
import { Skeleton } from '@/components/ui/Skeleton';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/Dialog';
import { showToast } from '@/components/ui/Toast';
import {
  GitBranch,
  Star,
  Trash2,
  Plus,
  Play,
  ArrowRight,
  Clock,
} from 'lucide-react';

export default function ReposPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  // Dialog State for Delete Confirmation
  const [deleteTarget, setDeleteTarget] = useState<RepoSummary | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isDemoLoading, setIsDemoLoading] = useState(false);

  // Fetch Repositories List
  const {
    data: repos,
    isLoading,
    error,
    refetch,
  } = useQuery<ReposListResponse>({
    queryKey: ['repos'],
    queryFn: async () => {
      const data = await api.get<unknown>('/repos');
      return ReposListResponseSchema.parse(data);
    },
    staleTime: 5000,
  });

  // Handle Delete Confirmation
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);

    try {
      await api.delete(`/repos/${deleteTarget.id}`);
      showToast.success(`Deleted repository: ${deleteTarget.full_name}`);
      queryClient.invalidateQueries({ queryKey: ['repos'] });
      setDeleteTarget(null);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to delete repository';
      showToast.error(msg);
    } finally {
      setIsDeleting(false);
    }
  };

  // Handle Try Demo Mode
  const handleTryDemo = async () => {
    setIsDemoLoading(true);
    try {
      showToast.info('Loading bundled TaskBoard fixture 100% offline...');
      const data = await api.post<{ repo_id: string; full_name?: string }>('/demo/load');
      showToast.success(`Demo loaded: ${data.full_name || 'demo/taskboard'}`);
      queryClient.invalidateQueries({ queryKey: ['repos'] });
      router.push(`/repos/${data.repo_id}`);
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to load demo repository';
      showToast.error(msg);
    } finally {
      setIsDemoLoading(false);
    }
  };

  const getStatusVariant = (status: string): StatusVariant => {
    switch (status) {
      case 'ready':
        return 'mint';
      case 'queued':
      case 'fetching':
      case 'chunking':
      case 'embedding':
      case 'summarizing':
        return 'amber';
      case 'failed':
        return 'flame';
      default:
        return 'neutral';
    }
  };

  return (
    <AppShell>
      <div className="max-w-6xl mx-auto py-6 space-y-8">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border/60 pb-6">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <h1 className="font-display font-extrabold text-2xl sm:text-3xl text-text">
                Repositories
              </h1>
              {repos && (
                <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-full bg-surface-2 border border-border text-text-muted">
                  {repos.length}
                </span>
              )}
            </div>
            <p className="text-xs text-text-muted font-mono">
              Local repository index, vector embeddings, and real-time ingestion status.
            </p>
          </div>

          {/* Action CTAs */}
          <div className="flex items-center gap-3">
            <Button
              variant="secondary"
              onClick={handleTryDemo}
              loading={isDemoLoading}
              className="gap-2 text-xs"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Try Demo Mode</span>
            </Button>
            <Link href="/">
              <Button variant="primary" className="gap-2 text-xs">
                <Plus className="w-4 h-4" />
                <span>Index New Repo</span>
              </Button>
            </Link>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <Skeleton className="h-48 w-full rounded-2xl" />
            <Skeleton className="h-48 w-full rounded-2xl" />
            <Skeleton className="h-48 w-full rounded-2xl" />
          </div>
        )}

        {/* Error State */}
        {error && !isLoading && (
          <div className="p-8 text-center bg-flame/10 border border-flame/30 rounded-2xl space-y-3">
            <p className="text-sm font-semibold text-flame">
              Failed to load repositories: {error instanceof Error ? error.message : 'Unknown error'}
            </p>
            <Button variant="secondary" onClick={() => refetch()}>
              Retry
            </Button>
          </div>
        )}

        {/* Empty State with Pip */}
        {!isLoading && !error && repos && repos.length === 0 && (
          <div className="py-12">
            <EmptyState
              title="No Repositories Indexed Yet"
              description="Connect an open source repository from GitHub, or load the bundled offline TaskBoard fixture to explore the triage bot, PR reviews, and living architecture map."
              actionLabel="Connect Repository"
              actionHref="/"
              pipState="idle"
            />
          </div>
        )}

        {/* Repositories Grid */}
        {!isLoading && !error && repos && repos.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {repos.map((repo) => {
              const isReady = repo.status === 'ready';
              const isFailed = repo.status === 'failed';
              const isInProgress = !isReady && !isFailed;

              return (
                <div
                  key={repo.id}
                  className="group relative flex flex-col justify-between p-5 bg-surface-1 hover:bg-surface-2/60 border border-border hover:border-brand/40 rounded-2xl transition-all duration-200 shadow-sm"
                >
                  <div className="space-y-3">
                    {/* Top Row: Title & Status Chip */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <Link
                          href={`/repos/${repo.id}`}
                          className="font-display font-bold text-base text-text hover:text-brand transition-colors block truncate"
                          title={repo.full_name}
                        >
                          {repo.full_name}
                        </Link>
                        <span className="font-mono text-[11px] text-text-muted flex items-center gap-1.5 mt-0.5">
                          <GitBranch className="w-3 h-3 text-text-muted/60" />
                          <span>{repo.default_branch || 'main'}</span>
                        </span>
                      </div>

                      <StatusChip
                        variant={getStatusVariant(repo.status)}
                        pulse={isInProgress}
                        label={
                          isInProgress
                            ? `${repo.status} (${repo.progress}%)`
                            : repo.status
                        }
                      />
                    </div>

                    {/* Description */}
                    <p className="text-xs text-text-muted line-clamp-2 leading-relaxed min-h-[2.25rem]">
                      {repo.description || 'No repository description provided.'}
                    </p>

                    {/* Metadata: Stars & Date */}
                    <div className="flex items-center gap-4 text-xs font-mono text-text-muted pt-2 border-t border-border/50">
                      <div className="flex items-center gap-1">
                        <Star className="w-3.5 h-3.5 text-amber fill-amber" />
                        <span>{repo.stars.toLocaleString()}</span>
                      </div>
                      <div className="flex items-center gap-1 text-[11px]">
                        <Clock className="w-3 h-3" />
                        <span>
                          {new Date(repo.last_indexed_at || repo.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Bottom Row Actions */}
                  <div className="pt-4 mt-3 border-t border-border/40 flex items-center justify-between">
                    <Link href={`/repos/${repo.id}`} className="w-full mr-2">
                      <Button
                        variant={isReady ? 'primary' : 'secondary'}
                        className="w-full text-xs justify-between gap-2"
                      >
                        <span>{isReady ? 'Open Quest' : 'View Ingestion'}</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Button>
                    </Link>

                    {/* Delete with Confirm Dialog */}
                    <Button
                      variant="ghost"
                      onClick={() => setDeleteTarget(repo)}
                      className="p-2 text-text-muted hover:text-flame hover:bg-flame/10"
                      title="Delete Repository"
                      aria-label={`Delete ${repo.full_name}`}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Repository</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete{' '}
              <strong className="text-text font-mono">
                {deleteTarget?.full_name}
              </strong>
              ? This action permanently removes all indexed source chunks, vector embeddings,
              triage analyses, and review reports from the local database.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter className="mt-6">
            <Button
              variant="secondary"
              onClick={() => setDeleteTarget(null)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              onClick={handleDeleteConfirm}
              loading={isDeleting}
            >
              Confirm Deletion
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AppShell>
  );
}
