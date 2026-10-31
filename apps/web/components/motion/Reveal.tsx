'use client';

import React, { type ReactNode } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { ease } from '@/lib/motion';

export interface RevealProps {
  children: ReactNode;
  delay?: number;
  direction?: 'up' | 'down' | 'left' | 'right' | 'none';
  duration?: number;
  className?: string;
}

export function Reveal({
  children,
  delay = 0,
  direction = 'up',
  duration = 0.24,
  className,
}: RevealProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  if (isStill) {
    return <div className={className}>{children}</div>;
  }

  const offset = 12;
  const initialTransform = {
    up: { y: offset, x: 0 },
    down: { y: -offset, x: 0 },
    left: { x: offset, y: 0 },
    right: { x: -offset, y: 0 },
    none: { x: 0, y: 0 },
  }[direction];

  return (
    <motion.div
      initial={{ opacity: 0, ...initialTransform }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{
        duration,
        delay,
        ease: ease.out,
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export default Reveal;
