'use client';

import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';

export interface StampProps {
  text?: string;
  variant?: 'mint' | 'flame' | 'amber' | 'brand';
  className?: string;
  active?: boolean;
}

export function Stamp({
  text = 'APPROVED',
  variant = 'mint',
  className,
  active = true,
}: StampProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const colorStyles = {
    mint: 'border-mint text-mint bg-mint/10',
    flame: 'border-flame text-flame bg-flame/10',
    amber: 'border-amber text-amber bg-amber/10',
    brand: 'border-brand text-brand bg-brand/10',
  }[variant];

  const baseClasses = cn(
    'inline-block px-3 py-1 font-pixel uppercase tracking-widest text-xs sm:text-sm font-bold border-2 rounded select-none shadow-sm',
    colorStyles,
    className
  );

  if (!active) return null;

  if (isStill) {
    return (
      <div
        className={baseClasses}
        style={{ transform: 'rotate(-8deg)' }}
        role="status"
        aria-label={text}
      >
        {text}
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 1.4, rotate: -8 }}
      animate={{ opacity: 1, scale: 1, rotate: -8 }}
      transition={spring.bouncy}
      className={baseClasses}
      role="status"
      aria-label={text}
    >
      {text}
    </motion.div>
  );
}

export default Stamp;
