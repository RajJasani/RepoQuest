'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function HealthPage() {
  const params = useParams();
  const repoId = String(params.id || '');

  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title={`Maintainer Health (${repoId})`}
          description="LoadGauge index, 8-week responsiveness sparklines, and weekly Markdown digest generator."
          actionLabel="View Model Lab"
          actionHref="/models"
          pipState="idle"
        />
      </div>
    </AppShell>
  );
}
