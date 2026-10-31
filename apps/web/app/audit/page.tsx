'use client';

import React from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function AuditPage() {
  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title="AI Audit Log & Undo"
          description="Complete transparent audit trail of all AI prompts, latency, token counts, and reversible actions."
          actionLabel="View Settings"
          actionHref="/settings"
          pipState="idle"
        />
      </div>
    </AppShell>
  );
}
