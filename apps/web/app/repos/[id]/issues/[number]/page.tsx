'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function IssueDetailPage() {
  const params = useParams();
  const repoId = String(params.id || '');
  const issueNum = String(params.number || '');

  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title={`Issue #${issueNum} Detail`}
          description="Detailed AI analysis card, duplicate candidates, and maintainer reply draft."
          actionLabel="Back to Triage Inbox"
          actionHref={`/repos/${repoId}/issues`}
          pipState="idle"
        />
      </div>
    </AppShell>
  );
}
