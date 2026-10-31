'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { useSettings } from '@/lib/settings-context';
import { Logo } from '@/components/brand/Logo';
import { PixelIcon, PixelIconName } from '@/components/brand/PixelIcon';
import { cn } from '@/lib/utils';
import { spring } from '@/lib/motion';

interface NavItem {
  label: string;
  href: (repoId?: string) => string;
  icon: PixelIconName;
  matchPrefix?: string;
}

export function Sidebar({ className }: { className?: string }) {
  const pathname = usePathname();
  const { selectedRepoId, repos } = useSettings();
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  // Find effective repo id: from URL path /repos/[id] or settings selectedRepoId or first repo
  const pathParts = pathname.split('/');
  const urlRepoId = pathParts[1] === 'repos' && pathParts[2] && pathParts[2] !== 'new' ? pathParts[2] : null;
  const effectiveRepoId = urlRepoId || selectedRepoId || repos[0]?.id || 'demo';

  const maintainerItems: NavItem[] = [
    {
      label: 'Issues & Triage',
      href: (id) => `/repos/${id}/issues`,
      icon: 'flag',
      matchPrefix: '/issues',
    },
    {
      label: 'PR Review',
      href: (id) => `/repos/${id}/prs`,
      icon: 'shield',
      matchPrefix: '/prs',
    },
    {
      label: 'Spam Shield',
      href: (id) => `/repos/${id}/spam`,
      icon: 'cracked-shield',
      matchPrefix: '/spam',
    },
    {
      label: 'Maintainer Health',
      href: (id) => `/repos/${id}/health`,
      icon: 'scroll',
      matchPrefix: '/health',
    },
  ];

  const newcomerItems: NavItem[] = [
    {
      label: 'Explore Map',
      href: (id) => `/repos/${id}/explore`,
      icon: 'compass',
      matchPrefix: '/explore',
    },
    {
      label: 'Ask Repo',
      href: (id) => `/repos/${id}/ask`,
      icon: 'lantern',
      matchPrefix: '/ask',
    },
    {
      label: 'Day-1 Tour',
      href: (id) => `/repos/${id}/onboarding`,
      icon: 'key',
      matchPrefix: '/onboarding',
    },
    {
      label: 'Launchpad',
      href: (id) => `/repos/${id}/launchpad`,
      icon: 'spark',
      matchPrefix: '/launchpad',
    },
  ];

  const systemItems: NavItem[] = [
    {
      label: 'Model Lab',
      href: () => '/models',
      icon: 'crown',
      matchPrefix: '/models',
    },
    {
      label: 'Audit & Undo',
      href: () => '/audit',
      icon: 'lock',
      matchPrefix: '/audit',
    },
    {
      label: 'Settings',
      href: () => '/settings',
      icon: 'compass',
      matchPrefix: '/settings',
    },
  ];

  const renderGroup = (title: string, items: NavItem[]) => (
    <div className="space-y-1">
      <div className="px-3 pb-1 text-[11px] font-mono uppercase tracking-wider text-text-muted hidden lg:block select-none">
        {title}
      </div>
      <div className="space-y-1">
        {items.map((item) => {
          const itemHref = item.href(effectiveRepoId);
          const isActive =
            pathname === itemHref ||
            (item.matchPrefix && pathname.includes(item.matchPrefix));

          return (
            <Link
              key={item.label}
              href={itemHref}
              className={cn(
                'relative flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all group select-none',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
                isActive
                  ? 'text-brand font-semibold bg-surface-2/80 shadow-sm'
                  : 'text-text-muted hover:text-text hover:bg-surface-2/40'
              )}
              title={item.label}
            >
              {/* Active layoutId bar */}
              {isActive && (
                <motion.div
                  layoutId={isStill ? undefined : 'sidebar-active-indicator'}
                  className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-brand rounded-r"
                  transition={isStill ? { duration: 0 } : spring.gentle}
                />
              )}

              <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
                <PixelIcon
                  name={item.icon}
                  size={16}
                  className={cn(
                    'transition-transform duration-150 group-hover:scale-110',
                    isActive ? 'text-brand' : 'text-text-muted group-hover:text-text'
                  )}
                />
              </div>

              <span className="truncate hidden lg:inline-block">
                {item.label}
              </span>
            </Link>
          );
        })}
      </div>
    </div>
  );

  return (
    <aside
      className={cn(
        'h-screen sticky top-0 bg-surface-1 border-r border-border flex flex-col justify-between p-3 select-none z-30 transition-all duration-200',
        'w-16 lg:w-[248px]',
        className
      )}
      aria-label="Application Sidebar"
    >
      <div className="space-y-6">
        {/* Brand Header */}
        <div className="px-1 py-2 flex items-center justify-center lg:justify-start">
          <Link
            href="/"
            className="flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand rounded-md p-1"
          >
            <div className="hidden lg:block">
              <Logo variant="full" size="sm" />
            </div>
            <div className="lg:hidden">
              <Logo variant="icon" size={28} />
            </div>
          </Link>
        </div>

        {/* Navigation Groups */}
        <nav className="space-y-5">
          {renderGroup('Maintainer', maintainerItems)}
          {renderGroup('Newcomer', newcomerItems)}
          {renderGroup('System', systemItems)}
        </nav>
      </div>

      {/* Footer link to Repository List */}
      <div className="pt-3 border-t border-border/60">
        <Link
          href="/repos"
          className={cn(
            'flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs text-text-muted hover:text-text hover:bg-surface-2 transition-colors select-none',
            pathname === '/repos' && 'text-brand font-semibold bg-surface-2'
          )}
          title="All Repositories"
        >
          <PixelIcon name="scroll" size={16} />
          <span className="truncate hidden lg:inline-block">All Repositories</span>
        </Link>
      </div>
    </aside>
  );
}

export default Sidebar;
