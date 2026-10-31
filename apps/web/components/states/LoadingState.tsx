'use client';

import React from 'react';
import { Pip } from '@/components/brand/Pip';
import { Skeleton } from '@/components/ui/Skeleton';
import { cn } from '@/lib/utils';

export interface LoadingStateProps {
  message?: string;
  className?: string;
  showSkeletons?: boolean;
}

export function LoadingState({
  message = 'Loading repository data...',
  className,
  showSkeletons = true,
}: LoadingStateProps) {
  return (
    <div
      className={cn(
        'w-full p-8 flex flex-col items-center justify-center text-center space-y-6',
        className
      )}
      role="status"
      aria-live="polite"
    >
      <div className="flex flex-col items-center gap-3">
        <Pip state="thinking" size={80} />
        <p className="font-display font-medium text-sm text-text-muted mt-2">
          {message}
        </p>
      </div>

      {showSkeletons && (
        <div className="w-full max-w-md space-y-3 pt-2">
          <Skeleton className="h-4 w-3/4 mx-auto" />
          <Skeleton className="h-4 w-5/6 mx-auto" />
          <div className="grid grid-cols-3 gap-3 pt-2">
            <Skeleton className="h-16 rounded-lg" />
            <Skeleton className="h-16 rounded-lg" />
            <Skeleton className="h-16 rounded-lg" />
          </div>
        </div>
      )}
    </div>
  );
}

export default LoadingState;
