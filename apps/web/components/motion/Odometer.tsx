'use client';

import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { cn } from '@/lib/utils';
import { ease } from '@/lib/motion';

export interface OdometerProps {
  value: number | string;
  className?: string;
  digitClassName?: string;
}

const DIGITS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];

function OdometerDigit({
  char,
  isStill,
  digitClassName,
}: {
  char: string;
  isStill: boolean;
  digitClassName?: string;
}) {
  const digit = parseInt(char, 10);

  if (isNaN(digit)) {
    return <span className={cn('inline-block', digitClassName)}>{char}</span>;
  }

  if (isStill) {
    return <span className={cn('inline-block', digitClassName)}>{char}</span>;
  }

  return (
    <span
      className={cn(
        'relative inline-block overflow-hidden h-[1.2em] leading-[1.2em] align-top select-none',
        digitClassName
      )}
      style={{ width: '0.62em' }}
    >
      <motion.span
        className="flex flex-col absolute top-0 left-0 right-0"
        initial={{ y: 0 }}
        animate={{ y: `-${digit * 10}%` }}
        transition={{ duration: 0.6, ease: ease.out }}
      >
        {DIGITS.map((d) => (
          <span
            key={d}
            className="h-[1.2em] flex items-center justify-center font-mono"
          >
            {d}
          </span>
        ))}
      </motion.span>
      {/* Ghost spacer to hold layout height */}
      <span className="invisible">0</span>
    </span>
  );
}

export function Odometer({ value, className, digitClassName }: OdometerProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const characters = String(value).split('');

  return (
    <span
      className={cn('inline-flex items-baseline font-mono select-none', className)}
      role="text"
      aria-label={String(value)}
    >
      {characters.map((char, index) => (
        <OdometerDigit
          key={`${index}-${char}`}
          char={char}
          isStill={isStill}
          digitClassName={digitClassName}
        />
      ))}
    </span>
  );
}

export default Odometer;
