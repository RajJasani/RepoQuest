'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { AlertTriangle, AlertCircle, Info, Sparkles } from 'lucide-react';

export type SeverityLevel = 'P0' | 'P1' | 'P2' | 'P3' | 'good-first-issue';

export interface SeverityPillProps extends React.HTMLAttributes<HTMLSpanElement> {
  level: SeverityLevel;
  showFullLabel?: boolean;
}

export function SeverityPill({
  level,
  showFullLabel = false,
  className,
  ...props
}: SeverityPillProps) {
  const configs: Record<
    SeverityLevel,
    {
      label: string;
      fullLabel: string;
      colorClass: string;
      borderClass: string;
      icon: React.ReactNode;
    }
  > = {
    P0: {
      label: 'P0',
      fullLabel: 'P0 Critical',
      colorClass: 'bg-flame/15 text-flame',
      borderClass: 'border-flame/30',
      icon: <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />,
    },
    P1: {
      label: 'P1',
      fullLabel: 'P1 High',
      colorClass: 'bg-amber/15 text-amber',
      borderClass: 'border-amber/30',
      icon: <AlertCircle className="w-3.5 h-3.5" aria-hidden="true" />,
    },
    P2: {
      label: 'P2',
      fullLabel: 'P2 Medium',
      colorClass: 'bg-sky/15 text-sky',
      borderClass: 'border-sky/30',
      icon: <Info className="w-3.5 h-3.5" aria-hidden="true" />,
    },
    P3: {
      label: 'P3',
      fullLabel: 'P3 Low',
      colorClass: 'bg-mint/15 text-mint',
      borderClass: 'border-mint/30',
      icon: <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />,
    },
    'good-first-issue': {
      label: 'Good First Issue',
      fullLabel: 'Good First Issue',
      colorClass: 'bg-mint/15 text-mint',
      borderClass: 'border-mint/30',
      icon: <Sparkles className="w-3.5 h-3.5" aria-hidden="true" />,
    },
  };

  const cfg = configs[level] || configs.P2;
  const labelText = showFullLabel ? cfg.fullLabel : cfg.label;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-mono font-medium border select-none transition-colors',
        cfg.colorClass,
        cfg.borderClass,
        className
      )}
      role="status"
      aria-label={`Severity: ${cfg.fullLabel}`}
      {...props}
    >
      {cfg.icon}
      <span>{labelText}</span>
    </span>
  );
}

export default SeverityPill;
