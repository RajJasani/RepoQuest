'use client';

import React from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function SetupPage() {
  return (
    <AppShell showSidebar={false}>
      <div className="py-12">
        <EmptyState
          title="First-Run Setup Wizard"
          description="Check Ollama status, view pull commands for local models, and test connections."
          actionLabel="Test Ollama Connection"
          actionHref="/"
          pipState="sleeping"
        />
      </div>
    </AppShell>
  );
}
