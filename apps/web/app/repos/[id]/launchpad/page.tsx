'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function LaunchpadPage() {
  const params = useParams();
  const repoId = String(params.id || '');

  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title="Newcomer Launchpad"
          description="Skill Match and Issue Forge: transforming vague issues into concrete contributor briefs."
          actionLabel="Match My Skills"
          actionHref={`/repos/${repoId}/health`}
          pipState="idle"
        />
      </div>
    </AppShell>
  );
}
