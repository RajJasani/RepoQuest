'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { SignatureStrip } from './SignatureStrip';

export interface LogoProps {
  variant?: 'full' | 'icon' | 'wordmark';
  mono?: boolean;
  size?: 'sm' | 'md' | 'lg' | number;
  className?: string;
  showTagline?: boolean;
}

// 8 by 8 pixel compass rose grid
// A = Amber (North point), S = Sky (Other points), R = Rose (Center), . = empty
const COMPASS_8X8 = [
  '...AA...',
  '...AA...',
  '..AAAA..',
  'SSRRRRSS',
  'SSRRRRSS',
  '..SSSS..',
  '...SS...',
  '...SS...',
];

export function CompassIcon({
  size = 32,
  mono = false,
  className,
}: {
  size?: number;
  mono?: boolean;
  className?: string;
}) {
  const getColor = (c: string) => {
    if (mono) return 'currentColor';
    if (c === 'A') return 'var(--amber)';
    if (c === 'R') return 'var(--rose)';
    if (c === 'S') return 'var(--sky)';
    return 'transparent';
  };

  return (
    <svg
      viewBox="0 0 12 12"
      width={size}
      height={size}
      shapeRendering="crispEdges"
      className={cn('inline-block flex-shrink-0', className)}
      role="img"
      aria-label="RepoQuest Compass Badge"
    >
      {/* Badge container background with rounded corners */}
      <rect
        x="0"
        y="0"
        width="12"
        height="12"
        rx="2.5"
        fill={mono ? 'transparent' : 'var(--surface-1)'}
        stroke={mono ? 'currentColor' : 'var(--border)'}
        strokeWidth="0.75"
      />
      {/* 8x8 Compass Rose centered with (x+2, y+2) offset */}
      {COMPASS_8X8.flatMap((row, y) =>
        row.split('').map((char, x) =>
          char === '.' ? null : (
            <rect
              key={`${x}-${y}`}
              x={x + 2}
              y={y + 2}
              width={1}
              height={1}
              fill={getColor(char)}
            />
          )
        )
      )}
    </svg>
  );
}

export function Logo({
  variant = 'full',
  mono = false,
  size = 'md',
  className,
  showTagline = false,
}: LogoProps) {
  const pixelSizes = {
    sm: 24,
    md: 32,
    lg: 44,
  };
  const iconPx = typeof size === 'number' ? size : pixelSizes[size];

  const textSizes = {
    sm: 'text-lg',
    md: 'text-2xl',
    lg: 'text-3xl',
  };
  const textSizeClass = typeof size === 'number' ? 'text-2xl' : textSizes[size];

  const iconElement = <CompassIcon size={iconPx} mono={mono} />;

  if (variant === 'icon') {
    return iconElement;
  }

  const wordmarkElement = (
    <div className="inline-flex items-baseline gap-1">
      <span
        className={cn(
          'font-display font-extrabold tracking-tight',
          textSizeClass,
          mono ? 'text-current' : 'text-text'
        )}
      >
        RepoQuest
      </span>
      {/* Signature Strip as the dot after the wordmark */}
      <span className="inline-flex items-center ml-0.5 self-center pb-0.5">
        <SignatureStrip variant="divider" size={typeof size === 'number' ? 4 : size === 'sm' ? 3 : size === 'lg' ? 5 : 4} />
      </span>
    </div>
  );

  if (variant === 'wordmark') {
    return (
      <div className={cn('inline-flex flex-col', className)}>
        {wordmarkElement}
        {showTagline && (
          <span className="text-xs text-text-muted font-sans -mt-0.5">
            Help maintainers keep up. Help newcomers get started.
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={cn('inline-flex items-center gap-2.5', className)}>
      {iconElement}
      <div className="flex flex-col">
        {wordmarkElement}
        {showTagline && (
          <span className="text-xs text-text-muted font-sans -mt-0.5">
            Help maintainers keep up. Help newcomers get started.
          </span>
        )}
      </div>
    </div>
  );
}
