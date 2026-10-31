'use client';

import React, { useEffect, useState } from 'react';
import { Toaster as SonnerToaster, toast } from 'sonner';
import { cn } from '@/lib/utils';
import { useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, RotateCcw } from 'lucide-react';

export function Toaster() {
  return (
    <SonnerToaster
      position="bottom-right"
      toastOptions={{
        unstyled: true,
        className: 'w-full',
      }}
    />
  );
}

export interface UndoToastProps {
  message: string;
  onUndo?: () => void;
  durationMs?: number;
  onDismiss?: () => void;
  className?: string;
}

export function UndoToast({
  message,
  onUndo,
  durationMs = 5000,
  onDismiss,
  className,
}: UndoToastProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const [drainingProgress, setDrainingProgress] = useState(1);

  useEffect(() => {
    if (isStill) return;

    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, 1 - elapsed / durationMs);
      setDrainingProgress(remaining);

      if (remaining <= 0) {
        clearInterval(interval);
        onDismiss?.();
      }
    }, 40);

    return () => clearInterval(interval);
  }, [durationMs, isStill, onDismiss]);

  return (
    <div
      role="status"
      className={cn(
        'relative overflow-hidden rounded-[12px] border border-border bg-surface-2 text-text shadow-lg p-4 min-w-[320px] flex items-center justify-between gap-4',
        className
      )}
    >
      {/* Left indicator stripe */}
      <div className="absolute left-0 top-0 bottom-0 w-1 bg-brand" />

      <div className="flex items-center gap-3 pl-1">
        <span className="text-sm font-medium">{message}</span>
      </div>

      {onUndo && (
        <button
          type="button"
          onClick={() => {
            onUndo();
            onDismiss?.();
          }}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-brand text-white hover:brightness-110 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>Undo</span>
        </button>
      )}

      {/* Draining Progress Line (animates scaleX from 1 to 0) */}
      {!isStill && (
        <div
          className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand origin-left"
          style={{
            transform: `scaleX(${drainingProgress})`,
            transition: 'transform 40ms linear',
          }}
          aria-hidden="true"
        />
      )}
    </div>
  );
}

export const showToast = {
  success: (message: string) => {
    toast.custom(() => (
      <div className="relative overflow-hidden rounded-[12px] border border-border bg-surface-2 text-text shadow-lg p-4 min-w-[300px] flex items-center gap-3">
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-mint" />
        <CheckCircle2 className="w-5 h-5 text-mint flex-shrink-0" />
        <span className="text-sm font-medium">{message}</span>
      </div>
    ));
  },
  error: (message: string) => {
    toast.custom(() => (
      <div className="relative overflow-hidden rounded-[12px] border border-border bg-surface-2 text-text shadow-lg p-4 min-w-[300px] flex items-center gap-3">
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-flame" />
        <AlertCircle className="w-5 h-5 text-flame flex-shrink-0" />
        <span className="text-sm font-medium">{message}</span>
      </div>
    ));
  },
  warning: (message: string) => {
    toast.custom(() => (
      <div className="relative overflow-hidden rounded-[12px] border border-border bg-surface-2 text-text shadow-lg p-4 min-w-[300px] flex items-center gap-3">
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-amber" />
        <AlertTriangle className="w-5 h-5 text-amber flex-shrink-0" />
        <span className="text-sm font-medium">{message}</span>
      </div>
    ));
  },
  info: (message: string) => {
    toast.custom(() => (
      <div className="relative overflow-hidden rounded-[12px] border border-border bg-surface-2 text-text shadow-lg p-4 min-w-[300px] flex items-center gap-3">
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-sky" />
        <Info className="w-5 h-5 text-sky flex-shrink-0" />
        <span className="text-sm font-medium">{message}</span>
      </div>
    ));
  },
  undo: (message: string, onUndo: () => void, durationMs = 5000) => {
    toast.custom(
      (t) => (
        <UndoToast
          message={message}
          onUndo={onUndo}
          durationMs={durationMs}
          onDismiss={() => toast.dismiss(t)}
        />
      ),
      { duration: durationMs }
    );
  },
};

export default Toaster;
