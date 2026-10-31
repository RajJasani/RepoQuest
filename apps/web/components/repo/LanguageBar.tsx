'use client';

import React, { useMemo } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { getLanguageColor } from '@/lib/languages';
import { cn } from '@/lib/utils';
import { ease } from '@/lib/motion';

interface LanguageBarProps {
  languages: Record<string, number | { bytes?: number; percentage?: number }>;
  className?: string;
}

export function LanguageBar({ languages, className }: LanguageBarProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  // Normalize language stats
  const items = useMemo(() => {
    const entries = Object.entries(languages || {});
    if (entries.length === 0) return [];

    let total = 0;
    const rawItems: { name: string; value: number }[] = [];

    for (const [name, val] of entries) {
      const num =
        typeof val === 'number'
          ? val
          : typeof val === 'object' && val !== null && 'bytes' in val
          ? Number(val.bytes || 0)
          : 0;
      if (num > 0) {
        total += num;
        rawItems.push({ name, value: num });
      }
    }

    if (total === 0) {
      // If values were percentages directly
      return entries.map(([name, val]) => ({
        name,
        percentage: typeof val === 'number' ? val : 0,
        color: getLanguageColor(name),
      }));
    }

    return rawItems
      .sort((a, b) => b.value - a.value)
      .map((item) => ({
        name: item.name,
        percentage: Number(((item.value / total) * 100).toFixed(1)),
        color: getLanguageColor(item.name),
      }));
  }, [languages]);

  if (items.length === 0) {
    return null;
  }

  return (
    <div className={cn('space-y-2.5 w-full', className)}>
      {/* Animated Multi-Segment Bar */}
      <div
        className="h-2.5 w-full rounded-full bg-surface-2 overflow-hidden flex"
        role="progressbar"
        aria-label="Language Breakdown"
      >
        {items.map((lang, idx) => (
          <motion.div
            key={lang.name}
            className="h-full first:rounded-l-full last:rounded-r-full"
            style={{ backgroundColor: lang.color }}
            initial={isStill ? { width: `${lang.percentage}%` } : { width: '0%' }}
            animate={{ width: `${lang.percentage}%` }}
            transition={{
              duration: 0.8,
              delay: isStill ? 0 : idx * 0.08,
              ease: ease.out,
            }}
            title={`${lang.name}: ${lang.percentage}%`}
          />
        ))}
      </div>

      {/* Language Breakdown Legend */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs font-mono">
        {items.map((lang) => (
          <div key={lang.name} className="flex items-center gap-1.5 text-text-muted">
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: lang.color }}
            />
            <span className="font-medium text-text">{lang.name}</span>
            <span className="text-[11px] text-text-muted/70">{lang.percentage}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

