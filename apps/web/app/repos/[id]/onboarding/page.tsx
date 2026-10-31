'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function OnboardingPage() {
  const params = useParams();
  const repoId = String(params.id || '');

  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title="Day-1 Tour (Newcomer Onboarding)"
          description="Curated beginner quest steps, hands-on quizzes, and XP achievements."
          actionLabel="Generate Tour Path"
          actionHref={`/repos/${repoId}/launchpad`}
          pipState="exploring"
        />
      </div>
    </AppShell>
  );
}
