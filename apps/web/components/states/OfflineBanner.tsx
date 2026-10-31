'use client';

import React from 'react';
import { AlertCircle, Terminal, RefreshCw } from 'lucide-react';
import { useSettings } from '@/lib/settings-context';
import { cn } from '@/lib/utils';

export function OfflineBanner({ className }: { className?: string }) {
  const { isBackendOffline, refetchHealth } = useSettings();

  if (!isBackendOffline) return null;

  return (
    <div
      role="alert"
      className={cn(
        'w-full bg-flame/15 border-b border-flame/30 px-4 py-2.5 text-xs text-text flex flex-wrap items-center justify-between gap-3 select-none',
        className
      )}
    >
      <div className="flex items-center gap-2">
        <AlertCircle className="w-4 h-4 text-flame flex-shrink-0" />
        <span className="font-semibold text-flame">Backend API is offline:</span>
        <span className="text-text-muted">
          Cannot reach local FastAPI service at localhost:8000.
        </span>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden sm:flex items-center gap-1.5 font-mono text-[11px] bg-surface-1/80 border border-border px-2 py-0.5 rounded text-text">
          <Terminal className="w-3 h-3 text-text-muted" />
          <span>cd apps/api && .venv/bin/uvicorn app.main:app --reload</span>
        </div>

        <button
          type="button"
          onClick={() => refetchHealth()}
          className="inline-flex items-center gap-1 font-sans font-medium text-flame hover:underline"
        >
          <RefreshCw className="w-3 h-3" />
          <span>Retry</span>
        </button>
      </div>
    </div>
  );
}

export default OfflineBanner;
