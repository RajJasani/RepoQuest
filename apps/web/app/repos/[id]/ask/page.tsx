'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function AskRepoPage() {
  const params = useParams();
  const repoId = String(params.id || '');

  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title="Ask the Repo"
          description="Local RAG assistant with cited code excerpts and newcomer/expert modes."
          actionLabel="Start New Conversation"
          actionHref={`/repos/${repoId}/issues`}
          pipState="thinking"
        />
      </div>
    </AppShell>
  );
}
