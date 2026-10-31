'use client';

import React from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function ReposPage() {
  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title="Repositories"
          description="View and manage all indexed local repositories, indexing progress, and status."
          actionLabel="Index New Repository"
          actionHref="/"
          pipState="idle"
        />
      </div>
    </AppShell>
  );
}
