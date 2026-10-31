'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function PRDetailPage() {
  const params = useParams();
  const repoId = String(params.id || '');
  const prNum = String(params.number || '');

  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title={`Pull Request #${prNum} Review`}
          description="Unified diff review, line comments, secret verification, and newcomer explainer."
          actionLabel="Back to PRs List"
          actionHref={`/repos/${repoId}/prs`}
          pipState="idle"
        />
      </div>
    </AppShell>
  );
}
