'use client';

import dynamic from 'next/dynamic';
import React from 'react';
import { Skeleton } from '@/components/ui/Skeleton';
import type { ModuleGraphProps } from './ModuleGraphInternal';

export type { ModuleGraphProps };

export const ModuleGraph = dynamic<ModuleGraphProps>(
  () => import('./ModuleGraphInternal').then((mod) => mod.ModuleGraphInternal),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex flex-col items-center justify-center p-6 bg-surface-1/40">
        <div className="w-full h-full border border-border/60 rounded-2xl flex flex-col items-center justify-center gap-3">
          <Skeleton className="w-48 h-6 rounded-lg" />
          <Skeleton className="w-72 h-4 rounded-lg" />
          <div className="flex gap-4 mt-6">
            <Skeleton className="w-40 h-16 rounded-xl" />
            <Skeleton className="w-40 h-16 rounded-xl" />
            <Skeleton className="w-40 h-16 rounded-xl" />
          </div>
        </div>
      </div>
    ),
  }
);

export default ModuleGraph;

