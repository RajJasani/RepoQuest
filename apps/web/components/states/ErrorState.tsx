'use client';

import React from 'react';
import { Pip } from '@/components/brand/Pip';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { RotateCcw } from 'lucide-react';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  error?: Error | unknown;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = 'Something went wrong',
  message = 'Failed to load data from the local repository server.',
  error,
  onRetry,
  className,
}: ErrorStateProps) {
  const errorDetails =
    error instanceof Error
      ? error.stack || error.message
      : typeof error === 'object' && error !== null
      ? JSON.stringify(error, null, 2)
      : error ? String(error) : null;

  return (
    <div
      className={cn(
        'w-full p-8 md:p-12 flex flex-col items-center justify-center text-center max-w-lg mx-auto space-y-4 rounded-xl border border-flame/30 bg-flame/5',
        className
      )}
      role="alert"
    >
      <div className="h-28 flex items-center justify-center">
        <Pip state="error" size={84} />
      </div>

      <div className="space-y-1.5">
        <h3 className="font-display font-bold text-lg text-text">{title}</h3>
        <p className="text-sm text-text-muted leading-relaxed">{message}</p>
      </div>

      {onRetry && (
        <div className="pt-2">
          <Button variant="secondary" onClick={onRetry} className="gap-2">
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Retry Request</span>
          </Button>
        </div>
      )}

      {errorDetails && (
        <details className="w-full text-left mt-4 text-xs font-mono border border-border rounded-lg bg-surface-2 p-3 overflow-hidden">
          <summary className="cursor-pointer text-text-muted hover:text-text font-sans font-medium select-none">
            View technical details
          </summary>
          <pre className="mt-2 text-[11px] text-flame overflow-x-auto whitespace-pre-wrap p-2 bg-surface-1 rounded">
            {errorDetails}
          </pre>
        </details>
      )}
    </div>
  );
}

export default ErrorState;
