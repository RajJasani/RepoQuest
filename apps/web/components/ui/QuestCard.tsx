'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { SignatureStrip } from '@/components/brand/SignatureStrip';

export interface QuestCardProps extends React.HTMLAttributes<HTMLDivElement> {
  showStrip?: boolean;
  glow?: boolean;
  children?: React.ReactNode;
}

export const QuestCard = React.forwardRef<HTMLDivElement, QuestCardProps>(
  (
    {
      className,
      showStrip = true,
      glow = false,
      children,
      ...props
    },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={cn(
          'relative group isolate transition-all duration-200',
          className
        )}
        {...props}
      >
        {/* Parchment Hard Shadow Layer (rendered via underlying notched pseudo-element) */}
        <div
          className="absolute inset-0 translate-x-1 translate-y-1 bg-border pointer-events-none -z-10 quest-card hidden dark:hidden [html[data-theme='parchment']_&]:block"
          aria-hidden="true"
        />

        {/* Summit Glow Layer */}
        {glow && (
          <div
            className="absolute -inset-1 rounded-xl bg-gradient-to-r from-brand/20 via-brand-2/20 to-rose/20 blur-md pointer-events-none -z-10 opacity-70 group-hover:opacity-100 transition-opacity duration-300"
            aria-hidden="true"
          />
        )}

        {/* Outer Wrapper providing the 1px border that survives clip-path */}
        <div className="quest-card bg-border p-[1px] w-full h-full relative">
          {/* Inner Surface with the same clip-path */}
          <div className="quest-card bg-surface-1 text-text w-full h-full p-6 relative overflow-hidden flex flex-col justify-between">
            {/* Signature Strip on Top Edge */}
            {showStrip && (
              <div className="absolute top-0 left-6 right-6 flex items-center justify-between">
                <SignatureStrip variant="cap" size={5} />
              </div>
            )}

            <div className={cn(showStrip && 'pt-2')}>{children}</div>
          </div>
        </div>
      </div>
    );
  }
);

QuestCard.displayName = 'QuestCard';
export default QuestCard;
