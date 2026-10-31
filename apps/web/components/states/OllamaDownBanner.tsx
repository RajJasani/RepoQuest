'use client';

import React from 'react';
import Link from 'next/link';
import { AlertTriangle, ArrowRight } from 'lucide-react';
import { useSettings } from '@/lib/settings-context';
import { cn } from '@/lib/utils';

export function OllamaDownBanner({ className }: { className?: string }) {
  const { isOllamaDown, isBackendOffline } = useSettings();

  // If backend is completely offline, let the OfflineBanner take precedence
  if (isBackendOffline || !isOllamaDown) return null;

  return (
    <div
      role="alert"
      className={cn(
        'w-full bg-amber/15 border-b border-amber/30 px-4 py-2.5 text-xs text-text flex items-center justify-between gap-3 select-none',
        className
      )}
    >
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-amber flex-shrink-0" />
        <span className="font-semibold text-amber">Ollama service unavailable:</span>
        <span className="text-text-muted">
          LLM provider is not responding. Ensure Ollama is running locally.
        </span>
      </div>

      <Link
        href="/setup"
        className="inline-flex items-center gap-1 font-medium text-amber hover:underline whitespace-nowrap"
      >
        <span>Open Setup Wizard</span>
        <ArrowRight className="w-3.5 h-3.5" />
      </Link>
    </div>
  );
}

export default OllamaDownBanner;
