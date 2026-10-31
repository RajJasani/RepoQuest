'use client';

import React, { useEffect, useState, useCallback, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '@/lib/api';
import { streamSse, SseProgressEvent } from '@/lib/sse';
import { RepoDetail, TreeNode, TreeNodesListSchema } from '@/lib/schemas';
import { FogOfWarMap } from './FogOfWarMap';
import { StageStepper, IndexingStage } from './StageStepper';
import { LogDrawer, LogEntry } from './LogDrawer';
import { Button } from '@/components/ui/Button';
import { SignatureStrip } from '@/components/brand/SignatureStrip';
import { showToast } from '@/components/ui/Toast';
import { Compass, MessageSquareCode, LayoutDashboard, ArrowRight } from 'lucide-react';

interface IndexingViewProps {
  repo: RepoDetail;
  onComplete?: () => void;
  className?: string;
}

export function IndexingView({ repo, onComplete, className }: IndexingViewProps) {
  const router = useRouter();
  const queryClient = useQueryClient();

  // Progress states initialized with repo data for instant resume on refresh
  const [stage, setStage] = useState<IndexingStage>(
    (repo.status as IndexingStage) || 'queued'
  );
  const [percent, setPercent] = useState<number>(repo.progress || 0);
  const [message, setMessage] = useState<string>(
    repo.error || (repo.status === 'ready' ? 'Indexing completed successfully' : 'Initializing pipeline...')
  );
  const [error, setError] = useState<string | null>(repo.error || null);
  const [isDone, setIsDone] = useState<boolean>(repo.status === 'ready');
  const [isRetrying, setIsRetrying] = useState<boolean>(false);

  // Streaming log lines
  const [logs, setLogs] = useState<LogEntry[]>(() => [
    {
      id: 'init-1',
      time: new Date().toLocaleTimeString(),
      text: `Connecting to pipeline for ${repo.full_name}...`,
      type: 'info',
    },
    ...(repo.progress > 0
      ? [
          {
            id: 'init-2',
            time: new Date().toLocaleTimeString(),
            text: `Resuming active session at ${repo.progress}% (${repo.status})`,
            type: 'info' as const,
          },
        ]
      : []),
  ]);

  // Track files/chunks metrics for Odometer counters
  const [filesScanned, setFilesScanned] = useState<number>(repo.file_count || 0);
  const [chunksEmbedded, setChunksEmbedded] = useState<number>(0);

  // Fetch repository tree for Fog of War regions
  const { data: treeNodes } = useQuery<TreeNode[]>({
    queryKey: ['repo-tree', repo.id],
    queryFn: async () => {
      try {
        const raw = await api.get<unknown>(`/repos/${repo.id}/tree`);
        if (Array.isArray(raw)) {
          return TreeNodesListSchema.parse(raw);
        }
        if (typeof raw === 'object' && raw !== null && 'tree' in raw) {
          return TreeNodesListSchema.parse((raw as { tree: unknown }).tree);
        }
        return [];
      } catch {
        return [];
      }
    },
    staleTime: 60 * 1000,
  });

  const appendLog = useCallback((text: string, type: LogEntry['type'] = 'info') => {
    setLogs((prev) => [
      ...prev.slice(-99), // keep last 100 entries
      {
        id: `${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        time: new Date().toLocaleTimeString(),
        text,
        type,
      },
    ]);
  }, []);

  // SSE Subscription reference for cleanup
  const abortControllerRef = useRef<AbortController | null>(null);

  const startSseStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const ac = new AbortController();
    abortControllerRef.current = ac;

    streamSse(`/repos/${repo.id}/progress`, {
      signal: ac.signal,
      onProgress: (data: SseProgressEvent) => {
        if (data.stage) {
          const nextStage = data.stage as IndexingStage;
          setStage(nextStage);
          if (nextStage === 'chunking') {
            setFilesScanned((prev) => Math.max(prev, 12));
          } else if (nextStage === 'embedding') {
            setChunksEmbedded((prev) => Math.max(prev, 36));
          }
        }
        if (typeof data.percent === 'number') {
          setPercent(data.percent);
        }
        if (data.message) {
          setMessage(data.message);
          appendLog(data.message, 'file');
        }
      },
      onError: (err) => {
        setStage('failed');
        setError(err.message || 'Indexing failed');
        appendLog(`Error: ${err.message}`, 'error');
        showToast.error(`Indexing failed: ${err.message}`);
      },
      onDone: () => {
        setStage('ready');
        setPercent(100);
        setIsDone(true);
        appendLog('Indexing completed successfully! Ready for exploration.', 'success');
        showToast.success('Repository indexing complete!');
        queryClient.invalidateQueries({ queryKey: ['repo', repo.id] });
        queryClient.invalidateQueries({ queryKey: ['repos'] });
        queryClient.invalidateQueries({ queryKey: ['repo-tree', repo.id] });
        if (onComplete) onComplete();
      },
    }).catch((err) => {
      if (ac.signal.aborted) return;
      setStage('failed');
      setError(err instanceof Error ? err.message : 'Connection closed');
      appendLog(`Connection lost: ${err instanceof Error ? err.message : String(err)}`, 'error');
    });
  }, [repo.id, appendLog, onComplete, queryClient]);

  // Connect SSE on mount if not already terminal ready
  useEffect(() => {
    if (repo.status === 'ready') {
      setIsDone(true);
      setPercent(100);
      setStage('ready');
      return;
    }

    startSseStream();

    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [repo.status, startSseStream]);

  // Retry Handler
  const handleRetry = async () => {
    setIsRetrying(true);
    setError(null);
    setStage('queued');
    setPercent(0);
    appendLog('Submitting re-indexing quest...', 'info');

    try {
      await api.post(`/repos/${repo.id}/reindex`);
      showToast.info('Re-indexing initiated...');
      queryClient.invalidateQueries({ queryKey: ['repo', repo.id] });
      startSseStream();
    } catch (err: unknown) {
      const msg = err instanceof ApiError ? err.message : 'Failed to reindex';
      setError(msg);
      setStage('failed');
      showToast.error(msg);
      appendLog(`Retry failed: ${msg}`, 'error');
    } finally {
      setIsRetrying(false);
    }
  };

  const isReady = stage === 'ready' || isDone;
  const isFailed = stage === 'failed';

  return (
    <div className={`space-y-6 max-w-6xl mx-auto py-2 ${className || ''}`}>
      {/* Title & Signature Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-display font-extrabold text-2xl text-text">
              {repo.full_name}
            </span>
            <SignatureStrip variant="divider" size={5} />
          </div>
          <p className="text-xs font-mono text-text-muted">
            {isReady
              ? 'Repository terrain completely unmasked and indexed into pgvector'
              : 'Unfurling the Fog of War as assets are chunked and embedded'}
          </p>
        </div>

        {/* Completion Action Buttons (Appear when ready) */}
        {isReady && (
          <div className="flex flex-wrap items-center gap-2.5 animate-fadeIn">
            <Link href={`/repos/${repo.id}/explore`}>
              <Button variant="primary" className="gap-2 shadow-sm">
                <Compass className="w-4 h-4" />
                <span>Explore Architecture</span>
              </Button>
            </Link>
            <Link href={`/repos/${repo.id}/ask`}>
              <Button variant="secondary" className="gap-2">
                <MessageSquareCode className="w-4 h-4" />
                <span>Ask the Repo</span>
              </Button>
            </Link>
            <Button
              variant="ghost"
              onClick={() => {
                queryClient.invalidateQueries({ queryKey: ['repo', repo.id] });
                router.refresh();
              }}
              className="gap-2"
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Overview</span>
            </Button>
          </div>
        )}
      </div>

      {/* Signature Strip Full-Width Line (fills completely at 100%) */}
      <div className="relative w-full h-1 bg-surface-2 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-sky via-amber to-mint transition-all duration-500"
          style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
        />
      </div>

      {/* HERO MOMENT M2: Fog of War Canvas */}
      <FogOfWarMap
        tree={treeNodes}
        percent={percent}
        stage={stage}
        isReady={isReady}
        isFailed={isFailed}
        error={error}
        onRetry={handleRetry}
        isRetrying={isRetrying}
      />

      {/* Pipeline Stage Stepper */}
      <StageStepper
        currentStage={stage}
        percent={percent}
        message={message}
        filesScanned={filesScanned}
        chunksEmbedded={chunksEmbedded}
      />

      {/* Streaming Log Drawer */}
      <LogDrawer logs={logs} isStreaming={!isReady && !isFailed} />

      {/* Completion Next Steps Card */}
      {isReady && (
        <div className="p-5 rounded-2xl bg-surface-1 border border-mint/30 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm animate-fadeIn">
          <div>
            <span className="font-display font-bold text-base text-mint block">
              Cartography Complete!
            </span>
            <p className="text-xs text-text-muted mt-0.5">
              All files, AST code chunks, and vector embeddings are ready. Start exploring or querying the codebase.
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <Link href={`/repos/${repo.id}/explore`}>
              <Button variant="primary" className="gap-2">
                <span>View Architecture Map</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
