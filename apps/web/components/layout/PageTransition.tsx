'use client';

import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { ease } from '@/lib/motion';

export function PageTransition({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  if (isStill) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.2, ease: ease.out }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export default PageTransition;
