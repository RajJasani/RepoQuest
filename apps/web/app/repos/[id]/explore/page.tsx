'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function ExplorePage() {
  const params = useParams();
  const repoId = String(params.id || '');

  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title="Living Codebase Map"
          description="Interactive module architecture graph powered by AST and import parsing."
          actionLabel="Start Exploration"
          actionHref={`/repos/${repoId}/ask`}
          pipState="exploring"
        />
      </div>
    </AppShell>
  );
}
