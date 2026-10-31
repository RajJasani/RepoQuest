'use client';

import React from 'react';
import { AppShell } from '@/components/layout/AppShell';
import { EmptyState } from '@/components/states/EmptyState';
import { Button } from '@/components/ui/Button';
import Link from 'next/link';

export default function HomePage() {
  return (
    <AppShell>
      <div className="py-12 max-w-xl mx-auto space-y-6">
        <EmptyState
          title="RepoQuest"
          description="Help maintainers keep up. Help newcomers get started. 100% offline local-first AI assistant for open source repositories."
          actionComponent={
            <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
              <Link href="/repos">
                <Button variant="primary">Explore Repositories</Button>
              </Link>
              <Link href="/setup">
                <Button variant="secondary">Setup Wizard</Button>
              </Link>
              <Link href="/design">
                <Button variant="ghost">Design System</Button>
              </Link>
            </div>
          }
          pipState="idle"
        />
      </div>
    </AppShell>
  );
}
