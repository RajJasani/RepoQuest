'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  shimmer?: boolean;
}

export function Skeleton({
  className,
  shimmer = true,
  ...props
}: SkeletonProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  return (
    <div
      className={cn(
        'rounded-md bg-surface-3 relative overflow-hidden',
        shimmer && !isStill && 'skeleton-shimmer',
        className
      )}
      style={
        shimmer && !isStill
          ? {
              backgroundImage:
                'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0) 100%)',
              backgroundSize: '200% 100%',
              animation: 'shimmer 1.4s infinite linear',
            }
          : undefined
      }
      aria-hidden="true"
      {...props}
    />
  );
}

export default Skeleton;
