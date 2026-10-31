'use client';

import { useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { cn } from '@/lib/utils';

export type SignatureStripVariant = 'divider' | 'loader' | 'cap';

interface SignatureStripProps {
  variant?: SignatureStripVariant;
  className?: string;
  size?: number; // size per pixel square, default 4 or 6 depending on variant
}

const COLORS = [
  'var(--sky)',
  'var(--amber)',
  'var(--rose)',
  'var(--flame)',
];

export function SignatureStrip({
  variant = 'divider',
  className,
  size,
}: SignatureStripProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStatic = Boolean(reduce) || calm;

  if (variant === 'cap') {
    return (
      <div
        className={cn('grid grid-cols-4 w-full h-1', className)}
        role="presentation"
        aria-hidden="true"
      >
        {COLORS.map((c, i) => (
          <div key={i} style={{ backgroundColor: c }} className="h-full w-full" />
        ))}
      </div>
    );
  }

  if (variant === 'loader') {
    return (
      <div
        className={cn('inline-flex items-center gap-1.5', className)}
        role="status"
        aria-label="Loading..."
      >
        {COLORS.map((c, i) => (
          <div
            key={i}
            className={cn(
              'w-2 h-2 rounded-[1px] transition-transform',
              !isStatic && 'animate-pulse'
            )}
            style={{
              backgroundColor: c,
              animationDelay: isStatic ? undefined : `${i * 150}ms`,
              animationDuration: isStatic ? undefined : '900ms',
            }}
          />
        ))}
      </div>
    );
  }

  // Default: divider
  const pixelSize = size ?? 4;
  return (
    <div
      className={cn('inline-flex items-center gap-1', className)}
      role="separator"
      aria-hidden="true"
    >
      {COLORS.map((c, i) => (
        <div
          key={i}
          style={{
            backgroundColor: c,
            width: pixelSize,
            height: pixelSize,
          }}
          className="rounded-[0.5px]"
        />
      ))}
    </div>
  );
}
