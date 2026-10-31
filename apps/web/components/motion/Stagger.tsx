'use client';

import React, { type ReactNode } from 'react';
import { motion, useReducedMotion, type Variants } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { ease } from '@/lib/motion';

export interface StaggerProps {
  children: ReactNode;
  gap?: number;
  delayChildren?: number;
  className?: string;
}

export function Stagger({
  children,
  gap = 0.04,
  delayChildren = 0.05,
  className,
}: StaggerProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  if (isStill) {
    return <div className={className}>{children}</div>;
  }

  const containerVariants: Variants = {
    hidden: {},
    show: {
      transition: {
        staggerChildren: gap,
        delayChildren,
      },
    },
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="show"
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  if (isStill) {
    return <div className={className}>{children}</div>;
  }

  const itemVariants: Variants = {
    hidden: { opacity: 0, y: 8 },
    show: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.2, ease: ease.out },
    },
  };

  return (
    <motion.div variants={itemVariants} className={className}>
      {children}
    </motion.div>
  );
}

export default Stagger;
