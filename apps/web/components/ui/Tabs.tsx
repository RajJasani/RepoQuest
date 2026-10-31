'use client';

import React, { createContext, useContext, useId } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { cn } from '@/lib/utils';
import { spring } from '@/lib/motion';

interface TabsContextValue {
  value: string;
  onValueChange: (val: string) => void;
  tabGroupId: string;
}

const TabsContext = createContext<TabsContextValue | null>(null);

export interface TabsProps {
  value: string;
  onValueChange: (val: string) => void;
  children: React.ReactNode;
  className?: string;
}

export function Tabs({ value, onValueChange, children, className }: TabsProps) {
  const tabGroupId = useId();
  return (
    <TabsContext.Provider value={{ value, onValueChange, tabGroupId }}>
      <div className={cn('w-full', className)}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={cn(
        'flex items-center gap-6 border-b border-border text-sm font-medium',
        className
      )}
    >
      {children}
    </div>
  );
}

export function TabsTrigger({
  value,
  children,
  disabled = false,
  className,
}: {
  value: string;
  children: React.ReactNode;
  disabled?: boolean;
  className?: string;
}) {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error('TabsTrigger must be used within Tabs');

  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const isSelected = ctx.value === value;

  return (
    <button
      type="button"
      role="tab"
      aria-selected={isSelected}
      disabled={disabled}
      onClick={() => ctx.onValueChange(value)}
      className={cn(
        'relative pb-3 pt-2 text-sm font-medium transition-colors select-none',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-bg rounded-t',
        isSelected ? 'text-brand font-semibold' : 'text-text-muted hover:text-text',
        disabled && 'opacity-50 pointer-events-none',
        className
      )}
    >
      <span>{children}</span>

      {/* layoutId sliding underline */}
      {isSelected && (
        <motion.div
          layoutId={isStill ? undefined : `tab-underline-${ctx.tabGroupId}`}
          className="absolute bottom-0 left-0 right-0 h-0.5 bg-brand"
          transition={isStill ? { duration: 0 } : spring.gentle}
        />
      )}
    </button>
  );
}

export function TabsContent({
  value,
  children,
  className,
}: {
  value: string;
  children: React.ReactNode;
  className?: string;
}) {
  const ctx = useContext(TabsContext);
  if (!ctx) throw new Error('TabsContent must be used within Tabs');

  if (ctx.value !== value) return null;

  return (
    <div
      role="tabpanel"
      className={cn('pt-4 focus-visible:outline-none', className)}
    >
      {children}
    </div>
  );
}

export default Tabs;
