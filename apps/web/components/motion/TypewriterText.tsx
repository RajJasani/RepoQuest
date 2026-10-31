'use client';

import React, { useEffect, useState } from 'react';
import { useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';

export interface TypewriterTextProps {
  text: string;
  speedMs?: number;
  mode?: 'word' | 'char';
  cursor?: boolean;
  className?: string;
  onComplete?: () => void;
}

export function TypewriterText({
  text,
  speedMs = 40,
  mode = 'word',
  cursor = true,
  className,
  onComplete,
}: TypewriterTextProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const [displayedIndex, setDisplayedIndex] = useState(isStill ? text.length : 0);
  const [isFinished, setIsFinished] = useState(isStill);

  useEffect(() => {
    if (isStill) {
      setDisplayedIndex(text.length);
      setIsFinished(true);
      onComplete?.();
      return;
    }

    setDisplayedIndex(0);
    setIsFinished(false);

    const tokens = mode === 'word' ? text.split(/(\s+)/) : text.split('');
    let currentIndex = 0;

    const interval = setInterval(() => {
      currentIndex += 1;
      setDisplayedIndex(currentIndex);

      if (currentIndex >= tokens.length) {
        clearInterval(interval);
        setIsFinished(true);
        onComplete?.();
      }
    }, speedMs);

    return () => clearInterval(interval);
  }, [text, speedMs, mode, isStill, onComplete]);

  let currentText = text;
  if (!isStill && !isFinished) {
    const tokens = mode === 'word' ? text.split(/(\s+)/) : text.split('');
    currentText = tokens.slice(0, displayedIndex).join('');
  }

  return (
    <span className={className}>
      {currentText}
      {!isFinished && cursor && !isStill && (
        <span
          className="inline-block w-2 h-4 ml-0.5 align-middle bg-brand animate-pulse"
          aria-hidden="true"
        />
      )}
    </span>
  );
}

export default TypewriterText;
