'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { FileCode2 } from 'lucide-react';

export interface CitationChipProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  path: string;
  lines?: string | [number, number];
  index?: number;
}

export const CitationChip = React.forwardRef<HTMLButtonElement, CitationChipProps>(
  ({ path, lines, index, className, onClick, ...props }, ref) => {
    const fileName = path.split('/').pop() || path;
    const linesFormatted = lines
      ? Array.isArray(lines)
        ? `L${lines[0]}-${lines[1]}`
        : lines.startsWith('L') || lines.startsWith(':')
        ? lines
        : `:${lines}`
      : '';

    return (
      <button
        ref={ref}
        type="button"
        onClick={onClick}
        className={cn(
          'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md font-mono text-xs border border-border bg-surface-2 text-text',
          'hover:bg-surface-3 hover:border-brand/50 hover:text-brand transition-all duration-150',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
          className
        )}
        title={`${path}${linesFormatted}`}
        {...props}
      >
        {index !== undefined && (
          <span className="text-[10px] font-bold text-amber bg-amber/10 px-1 rounded">
            [{index}]
          </span>
        )}
        <FileCode2 className="w-3 h-3 text-text-muted" aria-hidden="true" />
        <span className="truncate max-w-[160px] font-medium">{fileName}</span>
        {linesFormatted && (
          <span className="text-text-muted text-[11px]">{linesFormatted}</span>
        )}
      </button>
    );
  }
);

CitationChip.displayName = 'CitationChip';
export default CitationChip;
