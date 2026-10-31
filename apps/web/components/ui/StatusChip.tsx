'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';

export type StatusVariant = 'mint' | 'sky' | 'amber' | 'flame' | 'rose' | 'neutral';

export interface StatusChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: StatusVariant;
  pulse?: boolean;
  label?: string;
  children?: React.ReactNode;
}

export function StatusChip({
  variant = 'neutral',
  pulse = false,
  label,
  children,
  className,
  ...props
}: StatusChipProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const variantStyles: Record<StatusVariant, { bg: string; text: string; dot: string; border: string }> = {
    mint: {
      bg: 'bg-mint/10',
      text: 'text-mint',
      dot: 'bg-mint',
      border: 'border-mint/30',
    },
    sky: {
      bg: 'bg-sky/10',
      text: 'text-sky',
      dot: 'bg-sky',
      border: 'border-sky/30',
    },
    amber: {
      bg: 'bg-amber/10',
      text: 'text-amber',
      dot: 'bg-amber',
      border: 'border-amber/30',
    },
    flame: {
      bg: 'bg-flame/10',
      text: 'text-flame',
      dot: 'bg-flame',
      border: 'border-flame/30',
    },
    rose: {
      bg: 'bg-rose/10',
      text: 'text-rose',
      dot: 'bg-rose',
      border: 'border-rose/30',
    },
    neutral: {
      bg: 'bg-surface-2',
      text: 'text-text-muted',
      dot: 'bg-text-muted',
      border: 'border-border',
    },
  };

  const style = variantStyles[variant];
  const content = label || children;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border select-none transition-colors duration-150',
        style.bg,
        style.text,
        style.border,
        className
      )}
      role="status"
      {...props}
    >
      <span className="relative flex h-2 w-2">
        {pulse && !isStill && (
          <span
            className={cn(
              'animate-ping absolute inline-flex h-full w-full rounded-full opacity-75',
              style.dot
            )}
          />
        )}
        <span
          className={cn('relative inline-flex rounded-full h-2 w-2', style.dot)}
        />
      </span>
      <span>{content}</span>
    </span>
  );
}

export default StatusChip;
