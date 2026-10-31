'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function SpamShieldPage() {
  const params = useParams();
  const repoId = String(params.id || '');

  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title="Spam & Slop Shield"
          description="Radar scan board detecting whitespace edits, typo farming, and generic AI pull requests."
          actionLabel="Run Spam Radar Scan"
          actionHref={`/repos/${repoId}/health`}
          pipState="idle"
        />
      </div>
    </AppShell>
  );
}
