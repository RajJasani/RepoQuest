'use client';

import React, { useState, useRef } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { PixelIcon } from '@/components/brand/PixelIcon';
import { cn } from '@/lib/utils';
import { AlertCircle } from 'lucide-react';

export const GITHUB_REPO_REGEX =
  /^https:\/\/github\.com\/[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+\/?$/;

export interface ScanBeamInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: (validUrl: string) => void;
  disabled?: boolean;
  className?: string;
  errorMessage?: string | null;
  setErrorMessage?: (msg: string | null) => void;
}

export function ScanBeamInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
  className,
  errorMessage: externalError,
  setErrorMessage: setExternalError,
}: ScanBeamInputProps) {
  const [internalError, setInternalError] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);
  const [isShaking, setIsShaking] = useState(false);
  const [scanActive, setScanActive] = useState(false);

  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const inputRef = useRef<HTMLInputElement>(null);

  const errorMessage = externalError !== undefined ? externalError : internalError;
  const setErrorMessage = setExternalError || setInternalError;

  const handleFocus = () => {
    setIsFocused(true);
    if (!isStill) {
      setScanActive(true);
      setTimeout(() => setScanActive(false), 600);
    }
  };

  const handleBlur = () => {
    setIsFocused(false);
  };

  const validateAndSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const trimmed = value.trim();

    if (!trimmed) {
      triggerError('Please enter a GitHub repository URL.');
      return;
    }

    if (!GITHUB_REPO_REGEX.test(trimmed)) {
      triggerError(
        'Please enter a valid GitHub repository URL (e.g. https://github.com/owner/repo)'
      );
      return;
    }

    setErrorMessage(null);
    onSubmit?.(trimmed);
  };

  const triggerError = (msg: string) => {
    setErrorMessage(msg);
    if (!isStill) {
      setIsShaking(true);
      setTimeout(() => setIsShaking(false), 360);
    }
    inputRef.current?.focus();
  };

  return (
    <div className={cn('w-full flex flex-col space-y-2', className)}>
      <motion.div
        animate={
          isShaking && !isStill
            ? { x: [0, -6, 6, -6, 6, 0] }
            : { x: 0 }
        }
        transition={{ duration: 0.36 }}
        className={cn(
          'relative flex items-center h-14 rounded-xl border bg-surface-1/90 backdrop-blur-md transition-all duration-200 overflow-hidden shadow-sm',
          errorMessage
            ? 'border-rose ring-1 ring-rose/50'
            : isFocused
            ? 'border-brand ring-2 ring-brand/30 ring-offset-2 ring-offset-bg'
            : 'border-border hover:border-text-muted/60'
        )}
      >
        {/* Left icon badge */}
        <div className="pl-4 pr-3 flex items-center justify-center text-text-muted">
          <PixelIcon name="compass" size={20} className={isFocused ? 'text-brand' : 'text-text-muted'} />
        </div>

        {/* Input field */}
        <input
          ref={inputRef}
          type="url"
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            if (errorMessage) setErrorMessage(null);
          }}
          onFocus={handleFocus}
          onBlur={handleBlur}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              validateAndSubmit();
            }
          }}
          disabled={disabled}
          placeholder="Paste a GitHub repo URL to start your quest"
          className="flex-1 h-full bg-transparent text-sm md:text-base text-text placeholder:text-text-muted/70 focus:outline-none pr-4 font-sans"
        />

        {/* Scan beam on focus (A3) */}
        {scanActive && !isStill && (
          <span
            className="absolute top-0 bottom-0 w-24 bg-gradient-to-r from-transparent via-sky/40 to-transparent pointer-events-none"
            style={{
              animation: 'scanBeam 600ms linear forwards',
            }}
            aria-hidden="true"
          />
        )}
      </motion.div>

      {/* Rose error message */}
      {errorMessage && (
        <div
          role="alert"
          className="flex items-center gap-1.5 text-xs text-rose font-medium pl-1 animate-in fade-in slide-in-from-top-1"
        >
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Global CSS for scanBeam if not already present */}
      <style jsx global>{`
        @keyframes scanBeam {
          from {
            left: -30%;
          }
          to {
            left: 130%;
          }
        }
      `}</style>
    </div>
  );
}

export default ScanBeamInput;

