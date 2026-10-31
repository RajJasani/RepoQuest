'use client';

import React, { useEffect, useState } from 'react';
import { useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';

export interface CountUpProps {
  to: number;
  from?: number;
  duration?: number; // in seconds
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
  formatter?: (val: number) => string;
}

export function CountUp({
  to,
  from = 0,
  duration = 0.6,
  decimals = 0,
  prefix = '',
  suffix = '',
  className,
  formatter,
}: CountUpProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const [count, setCount] = useState(isStill ? to : from);

  useEffect(() => {
    if (isStill) {
      setCount(to);
      return;
    }

    let startTime: number | null = null;
    let animFrame: number;

    const easeOutQuad = (t: number) => t * (2 - t);

    const step = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / (duration * 1000), 1);
      const easedProgress = easeOutQuad(progress);
      const current = from + (to - from) * easedProgress;

      setCount(current);

      if (progress < 1) {
        animFrame = requestAnimationFrame(step);
      } else {
        setCount(to);
      }
    };

    animFrame = requestAnimationFrame(step);

    return () => {
      cancelAnimationFrame(animFrame);
    };
  }, [from, to, duration, isStill]);

  const displayValue = formatter
    ? formatter(count)
    : `${prefix}${count.toFixed(decimals)}${suffix}`;

  return (
    <span className={className} role="text" aria-label={`${prefix}${to}${suffix}`}>
      {displayValue}
    </span>
  );
}

export default CountUp;
