'use client';

import React from 'react';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';
import { OfflineBanner } from '@/components/states/OfflineBanner';
import { OllamaDownBanner } from '@/components/states/OllamaDownBanner';
import { PageTransition } from './PageTransition';
import { cn } from '@/lib/utils';

export interface AppShellProps {
  children: React.ReactNode;
  showSidebar?: boolean;
  showTopBar?: boolean;
  className?: string;
}

export function AppShell({
  children,
  showSidebar = true,
  showTopBar = true,
  className,
}: AppShellProps) {
  return (
    <div className="min-h-screen bg-bg text-text flex flex-col">
      {/* Top System Banners */}
      <OfflineBanner />
      <OllamaDownBanner />

      <div className="flex-1 flex w-full">
        {/* Left Navigation Sidebar */}
        {showSidebar && <Sidebar />}

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col min-w-0">
          {showTopBar && <TopBar />}
          <main className={cn('flex-1 p-4 md:p-8 max-w-7xl w-full mx-auto', className)}>
            <PageTransition>{children}</PageTransition>
          </main>
        </div>
      </div>
    </div>
  );
}

export default AppShell;
