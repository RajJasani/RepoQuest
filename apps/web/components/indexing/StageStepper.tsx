'use client';

import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { cn } from '@/lib/utils';
import { Odometer } from '@/components/motion/Odometer';
import { FileCode, Layers, Cpu, Sparkles } from 'lucide-react';

export type IndexingStage = 'queued' | 'fetching' | 'chunking' | 'embedding' | 'summarizing' | 'ready' | 'failed';

interface StageStepperProps {
  currentStage: IndexingStage;
  percent: number;
  message?: string;
  filesScanned?: number;
  chunksEmbedded?: number;
  className?: string;
}

const STAGES = [
  { id: 'fetch', label: 'Fetch', icon: FileCode, match: ['queued', 'fetching'] },
  { id: 'chunk', label: 'Chunk', icon: Layers, match: ['chunking'] },
  { id: 'embed', label: 'Embed', icon: Cpu, match: ['embedding'] },
  { id: 'summarize', label: 'Summarize', icon: Sparkles, match: ['summarizing'] },
] as const;

function getStageIndex(stage: IndexingStage): number {
  switch (stage) {
    case 'queued':
    case 'fetching':
      return 0;
    case 'chunking':
      return 1;
    case 'embedding':
      return 2;
    case 'summarizing':
      return 3;
    case 'ready':
      return 4; // all done
    case 'failed':
      return -1;
    default:
      return 0;
  }
}

export function StageStepper({
  currentStage,
  percent,
  message,
  filesScanned = 0,
  chunksEmbedded = 0,
  className,
}: StageStepperProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const activeIndex = getStageIndex(currentStage);

  return (
    <div
      className={cn(
        'w-full bg-surface-1 border border-border rounded-2xl p-5 space-y-4 shadow-sm',
        className
      )}
    >
      {/* Top row: Status message & rolling Odometer percentage */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border/60">
        <div>
          <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted font-bold block mb-1">
            Pipeline Progression
          </span>
          <p className="text-sm font-medium text-text truncate max-w-md">
            {message || (currentStage === 'ready' ? 'Repository indexing complete' : 'Processing repository assets...')}
          </p>
        </div>

        {/* Rolling Odometer counter */}
        <div className="flex items-center gap-4 self-start sm:self-center">
          <div className="flex items-baseline gap-1 bg-surface-2/80 px-3.5 py-1.5 rounded-lg border border-border/80">
            <span className="font-mono font-bold text-lg text-brand">
              <Odometer value={Math.min(100, Math.max(0, Math.round(percent)))} />
            </span>
            <span className="font-mono text-xs font-semibold text-text-muted">%</span>
          </div>

          {/* Auxiliary metrics: files / chunks */}
          <div className="hidden md:flex items-center gap-3 text-xs font-mono text-text-muted">
            <div className="px-2.5 py-1 bg-surface-2/40 rounded border border-border/50">
              <span className="text-text font-semibold">
                <Odometer value={filesScanned} />
              </span>{' '}
              files
            </div>
            <div className="px-2.5 py-1 bg-surface-2/40 rounded border border-border/50">
              <span className="text-text font-semibold">
                <Odometer value={chunksEmbedded} />
              </span>{' '}
              chunks
            </div>
          </div>
        </div>
      </div>

      {/* Stepper Stage Nodes */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-1">
        {STAGES.map((step, idx) => {
          const isDone = activeIndex > idx || currentStage === 'ready';
          const isActive = activeIndex === idx && currentStage !== 'ready';
          const isFailed = currentStage === 'failed' && activeIndex === idx;
          const StepIcon = step.icon;

          return (
            <div
              key={step.id}
              className={cn(
                'relative flex items-center gap-3 p-3 rounded-xl border transition-all duration-300',
                isActive &&
                  'bg-brand/10 border-brand/40 shadow-[0_0_12px_rgba(245,165,36,0.25)] ring-1 ring-brand/30',
                isDone && 'bg-mint/10 border-mint/30',
                isFailed && 'bg-flame/10 border-flame/40',
                !isActive && !isDone && !isFailed && 'bg-surface-2/40 border-border/60 opacity-60'
              )}
            >
              {/* Icon badge or Checkmark */}
              <div
                className={cn(
                  'w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors',
                  isActive && 'bg-brand/20 text-brand',
                  isDone && 'bg-mint/20 text-mint',
                  isFailed && 'bg-flame/20 text-flame',
                  !isActive && !isDone && !isFailed && 'bg-surface-3 text-text-muted'
                )}
              >
                {isDone ? (
                  // Animated check draw
                  <svg
                    className="w-4 h-4 text-mint"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <motion.path
                      d="M20 6L9 17l-5-5"
                      initial={isStill ? { pathLength: 1 } : { pathLength: 0 }}
                      animate={{ pathLength: 1 }}
                      transition={{ duration: 0.4, ease: 'easeOut' }}
                    />
                  </svg>
                ) : (
                  <StepIcon className="w-4 h-4" />
                )}
              </div>

              {/* Label & Status */}
              <div className="min-w-0">
                <span className="font-display font-bold text-xs block text-text truncate">
                  {step.label}
                </span>
                <span className="font-mono text-[10px] text-text-muted capitalize">
                  {isDone ? 'Completed' : isActive ? 'Active...' : isFailed ? 'Failed' : 'Pending'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
