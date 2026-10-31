'use client';

import React from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function SettingsPage() {
  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title="Repository & Model Settings"
          description="Configure local Ollama endpoint, default models, triage mode, and encrypted GitHub tokens."
          actionLabel="View Design System (/design)"
          actionHref="/design"
          pipState="idle"
        />
      </div>
    </AppShell>
  );
}
