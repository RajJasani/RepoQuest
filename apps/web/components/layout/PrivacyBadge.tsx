'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { useSettings } from '@/lib/settings-context';
import { PixelIcon } from '@/components/brand/PixelIcon';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { ShieldCheck, ShieldAlert, Cpu, Database, Server, X } from 'lucide-react';

export function PrivacyBadge({ className }: { className?: string }) {
  const { isLocalOnly, settings } = useSettings();
  const [open, setOpen] = useState(false);

  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const chatModel = settings?.chat_model || 'llama3.2';
  const embedModel = settings?.embed_model || 'nomic-embed-text';
  const baseUrl = settings?.ollama_base_url || 'http://localhost:11434';

  return (
    <div className={cn('relative inline-block', className)}>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-medium border select-none transition-all duration-200',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
          isLocalOnly
            ? 'bg-mint/15 text-mint border-mint/30 hover:bg-mint/20'
            : 'bg-amber/15 text-amber border-amber/30 hover:bg-amber/20'
        )}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <span className="relative flex items-center justify-center">
          {/* A9 lock icon */}
          <PixelIcon name="lock" size={14} className={isLocalOnly ? 'text-mint' : 'text-amber'} />
          {!isStill && isLocalOnly && (
            <span
              className="absolute -inset-1 rounded-full bg-mint/30 animate-ping opacity-40 pointer-events-none"
              style={{ animationDuration: '3s' }}
            />
          )}
        </span>
        <span className="font-semibold">
          {isLocalOnly ? '100% local' : 'Remote model'}
        </span>
      </button>

      {/* Popover showing model and base URL */}
      <AnimatePresence>
        {open && (
          <>
            {/* Backdrop click dismiss */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setOpen(false)}
              aria-hidden="true"
            />

            <motion.div
              initial={isStill ? { opacity: 0 } : { opacity: 0, scale: 0.95, y: -6 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={isStill ? { opacity: 0 } : { opacity: 0, scale: 0.95, y: -6 }}
              transition={isStill ? { duration: 0 } : spring.gentle}
              className="absolute right-0 top-full mt-2 z-50 w-72 rounded-[14px] border border-border bg-surface-2 p-4 text-text shadow-xl"
              role="dialog"
              aria-label="Privacy and Local AI Status"
            >
              <div className="flex items-center justify-between pb-3 border-b border-border mb-3">
                <div className="flex items-center gap-2">
                  {isLocalOnly ? (
                    <ShieldCheck className="w-4 h-4 text-mint" />
                  ) : (
                    <ShieldAlert className="w-4 h-4 text-amber" />
                  )}
                  <h4 className="font-display font-bold text-sm text-text">
                    {isLocalOnly ? 'Local AI Guarantee' : 'External Endpoint'}
                  </h4>
                </div>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="p-1 rounded-md text-text-muted hover:text-text hover:bg-surface-3"
                  aria-label="Close popover"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              <div className="space-y-2.5 text-xs">
                <div className="flex items-start gap-2">
                  <Cpu className="w-3.5 h-3.5 text-text-muted mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="text-text-muted block">Chat Model:</span>
                    <span className="font-mono text-text font-medium">{chatModel}</span>
                  </div>
                </div>

                <div className="flex items-start gap-2">
                  <Database className="w-3.5 h-3.5 text-text-muted mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="text-text-muted block">Embedding Model:</span>
                    <span className="font-mono text-text font-medium">{embedModel}</span>
                  </div>
                </div>

                <div className="flex items-start gap-2">
                  <Server className="w-3.5 h-3.5 text-text-muted mt-0.5 flex-shrink-0" />
                  <div className="min-w-0">
                    <span className="text-text-muted block">Provider Endpoint:</span>
                    <span className="font-mono text-text font-medium truncate block max-w-[200px]" title={baseUrl}>
                      {baseUrl}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-3.5 pt-3 border-t border-border/60">
                <p className="text-[11px] text-text-muted leading-relaxed">
                  {isLocalOnly
                    ? 'All issue triaging, code parsing, and embeddings run 100% on your machine. Zero code or tokens leave localhost.'
                    : 'The configured model endpoint points to an external server. Ensure you have proper authorization.'}
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}

export default PrivacyBadge;
