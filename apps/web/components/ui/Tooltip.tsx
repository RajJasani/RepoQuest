'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { cn } from '@/lib/utils';

export interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  side?: 'top' | 'bottom' | 'left' | 'right';
  className?: string;
  delayMs?: number;
}

export function Tooltip({
  content,
  children,
  side = 'top',
  className,
  delayMs = 200,
}: TooltipProps) {
  const [open, setOpen] = useState(false);
  const [timeoutId, setTimeoutId] = useState<NodeJS.Timeout | null>(null);

  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const show = () => {
    const id = setTimeout(() => setOpen(true), delayMs);
    setTimeoutId(id);
  };

  const hide = () => {
    if (timeoutId) clearTimeout(timeoutId);
    setOpen(false);
  };

  const positionStyles = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    left: 'right-full top-1/2 -translate-y-1/2 mr-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  }[side];

  const motionTransform = {
    top: { y: 4, x: '-50%' },
    bottom: { y: -4, x: '-50%' },
    left: { x: 4, y: '-50%' },
    right: { x: -4, y: '-50%' },
  }[side];

  return (
    <div
      className="relative inline-flex items-center"
      onMouseEnter={show}
      onMouseLeave={hide}
      onFocus={show}
      onBlur={hide}
    >
      {children}
      <AnimatePresence>
        {open && (
          <motion.div
            role="tooltip"
            initial={isStill ? { opacity: 0 } : { opacity: 0, ...motionTransform }}
            animate={{ opacity: 1, x: side === 'top' || side === 'bottom' ? '-50%' : 0, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: isStill ? 0 : 0.15 }}
            className={cn(
              'absolute z-50 px-2.5 py-1 text-xs font-medium rounded-md bg-surface-2 text-text border border-border shadow-md whitespace-nowrap pointer-events-none',
              positionStyles,
              className
            )}
          >
            {content}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default Tooltip;
