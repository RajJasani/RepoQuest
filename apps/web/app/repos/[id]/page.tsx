'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function RepoOverviewPage() {
  const params = useParams();
  const repoId = String(params.id || '');

  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title={`Repository Overview (${repoId})`}
          description="Repository statistics, tech stack, quick links, and maintainer health summary."
          actionLabel="Explore Architecture Graph"
          actionHref={`/repos/${repoId}/explore`}
          pipState="idle"
        />
      </div>
    </AppShell>
  );
}
