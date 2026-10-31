'use client';

import React from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';

export default function ModelsPage() {
  return (
    <AppShell>
      <div className="py-12">
        <EmptyState
          title="Local Model Lab"
          description="Benchmark installed Ollama models, run the live Model Race, and compare accuracy vs speed."
          actionLabel="Run Model Benchmark"
          actionHref="/audit"
          pipState="thinking"
        />
      </div>
    </AppShell>
  );
}
