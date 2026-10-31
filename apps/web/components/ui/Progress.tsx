'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { SignatureStrip } from '@/components/brand/SignatureStrip';
import { useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number; // 0 to 100
  indeterminate?: boolean;
  showCap?: boolean;
  height?: number | string;
}

export function Progress({
  value = 0,
  indeterminate = false,
  showCap = true,
  height = 8,
  className,
  ...props
}: ProgressProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const clampedValue = Math.min(Math.max(value, 0), 100);

  if (indeterminate) {
    return (
      <div
        className={cn(
          'w-full bg-surface-2 rounded-full overflow-hidden relative flex items-center justify-center p-1',
          className
        )}
        style={{ height }}
        role="progressbar"
        aria-label="Loading in progress"
        {...props}
      >
        <SignatureStrip variant="loader" size={typeof height === 'number' ? height - 2 : 6} />
      </div>
    );
  }

  return (
    <div
      className={cn(
        'w-full bg-surface-2 rounded-full overflow-hidden relative border border-border/40',
        className
      )}
      style={{ height }}
      role="progressbar"
      aria-valuenow={clampedValue}
      aria-valuemin={0}
      aria-valuemax={100}
      {...props}
    >
      {/* Progress Track Fill */}
      <div
        className="h-full bg-gradient-to-r from-sky via-amber to-rose relative rounded-full transition-all"
        style={{
          width: `${clampedValue}%`,
          transitionDuration: isStill ? '0ms' : '300ms',
        }}
      >
        {/* Leading Edge Signature Strip Cap */}
        {showCap && clampedValue > 4 && clampedValue < 98 && (
          <div className="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 z-10">
            <SignatureStrip variant="cap" size={typeof height === 'number' ? Math.max(height - 2, 4) : 4} />
          </div>
        )}
      </div>
    </div>
  );
}

export default Progress;
