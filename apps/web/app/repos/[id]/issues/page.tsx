'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function IssuesInboxPage() {
  const params = useParams();
  const repoId = String(params.id || '');

  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title="Triage Inbox"
          description="Autonomous issue triage with duplicate vector similarity and suggested replies."
          actionLabel="Sync Issues from GitHub"
          actionHref={`/repos/${repoId}/prs`}
          pipState="idle"
        />
      </div>
    </AppShell>
  );
}
