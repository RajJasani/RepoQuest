'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function PRsListPage() {
  const params = useParams();
  const repoId = String(params.id || '');

  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title="Pull Requests & Reviews"
          description="File-by-file code reviews with diff line citations and spam scoring."
          actionLabel="Sync Open Pull Requests"
          actionHref={`/repos/${repoId}/spam`}
          pipState="idle"
        />
      </div>
    </AppShell>
  );
}
