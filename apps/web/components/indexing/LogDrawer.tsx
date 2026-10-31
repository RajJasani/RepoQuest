'use client';

import React, { useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronUp, Terminal } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useCalmMode } from '@/lib/calm';
import { useReducedMotion } from 'framer-motion';

export interface LogEntry {
  id: string;
  time: string;
  text: string;
  type?: 'info' | 'file' | 'success' | 'warn' | 'error';
}

interface LogDrawerProps {
  logs: LogEntry[];
  isStreaming?: boolean;
  className?: string;
}

export function LogDrawer({ logs, isStreaming = false, className }: LogDrawerProps) {
  const [isOpen, setIsOpen] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  // Auto-scroll to bottom as new logs arrive
  useEffect(() => {
    if (isOpen && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, isOpen]);

  return (
    <div
      className={cn(
        'w-full rounded-xl border border-border bg-surface-1/90 backdrop-blur-md overflow-hidden transition-all duration-200',
        className
      )}
    >
      {/* Header bar */}
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full px-4 py-2.5 flex items-center justify-between bg-surface-2/60 hover:bg-surface-2 text-text transition-colors border-b border-border/50 text-left cursor-pointer"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          <Terminal className="w-3.5 h-3.5 text-text-muted" />
          <span className="font-mono text-xs font-semibold text-text">
            Indexing Stream
          </span>
          {isStreaming && (
            <span className="relative flex h-2 w-2 ml-1">
              {!isStill && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky opacity-75" />
              )}
              <span className="relative inline-flex rounded-full h-2 w-2 bg-sky" />
            </span>
          )}
          <span className="font-mono text-[11px] text-text-muted">
            ({logs.length} events)
          </span>
        </div>

        <div className="flex items-center gap-1.5 text-text-muted hover:text-text text-xs">
          <span className="font-mono text-[11px] hidden sm:inline">
            {isOpen ? 'Collapse' : 'Expand'}
          </span>
          {isOpen ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronUp className="w-4 h-4" />
          )}
        </div>
      </button>

      {/* Log lines container */}
      {isOpen && (
        <div
          ref={scrollRef}
          className="p-3 max-h-36 min-h-[5rem] overflow-y-auto font-mono text-xs space-y-1 select-text bg-bg/50"
        >
          {logs.length === 0 ? (
            <div className="text-text-muted/60 italic py-2">
              Waiting for indexer telemetry stream...
            </div>
          ) : (
            logs.map((log) => {
              const typeColor =
                log.type === 'error'
                  ? 'text-flame'
                  : log.type === 'warn'
                  ? 'text-amber'
                  : log.type === 'success'
                  ? 'text-mint'
                  : log.type === 'file'
                  ? 'text-sky'
                  : 'text-text-muted';

              return (
                <div
                  key={log.id}
                  className="flex items-start gap-2 leading-relaxed hover:bg-surface-2/40 px-1 py-0.5 rounded transition-colors"
                >
                  <span className="text-text-muted/50 text-[10px] shrink-0 pt-0.5">
                    {log.time}
                  </span>
                  <span className={cn('break-all', typeColor)}>{log.text}</span>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

