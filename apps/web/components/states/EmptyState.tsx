'use client';

import React from 'react';
import Link from 'next/link';
import { Pip, PipState } from '@/components/brand/Pip';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

export interface EmptyStateProps {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  actionHref?: string;
  actionComponent?: React.ReactNode;
  pipState?: PipState;
  className?: string;
}

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  actionHref,
  actionComponent,
  pipState = 'idle',
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'w-full p-8 md:p-12 flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-4 rounded-xl border border-dashed border-border bg-surface-1/50',
        className
      )}
      role="region"
      aria-label={title}
    >
      <div className="h-28 flex items-center justify-center">
        <Pip state={pipState} size={84} />
      </div>

      <div className="space-y-1.5">
        <h3 className="font-display font-bold text-lg text-text">{title}</h3>
        {description && (
          <p className="text-sm text-text-muted leading-relaxed">
            {description}
          </p>
        )}
      </div>

      {actionComponent ? (
        <div className="pt-2">{actionComponent}</div>
      ) : actionHref && actionLabel ? (
        <div className="pt-2">
          <Link href={actionHref}>
            <Button variant="primary">{actionLabel}</Button>
          </Link>
        </div>
      ) : onAction && actionLabel ? (
        <div className="pt-2">
          <Button variant="primary" onClick={onAction}>
            {actionLabel}
          </Button>
        </div>
      ) : null}
    </div>
  );
}

export default EmptyState;
