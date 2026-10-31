'use client';

import React, { useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { cn } from '@/lib/utils';
import { spring } from '@/lib/motion';
import { X } from 'lucide-react';

export interface DrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  position?: 'right' | 'bottom';
  children: React.ReactNode;
}

interface DrawerContextValue {
  open: boolean;
  onClose: () => void;
}

const DrawerContext = React.createContext<DrawerContextValue | null>(null);

export function Drawer({
  open,
  onOpenChange,
  position = 'right',
  children,
}: DrawerProps) {
  const onClose = useCallback(() => onOpenChange(false), [onOpenChange]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [open, onClose]);

  return (
    <DrawerContext.Provider value={{ open, onClose }}>
      <AnimatePresence>
        {open && <DrawerPortal position={position}>{children}</DrawerPortal>}
      </AnimatePresence>
    </DrawerContext.Provider>
  );
}

function DrawerPortal({
  position,
  children,
}: {
  position: 'right' | 'bottom';
  children: React.ReactNode;
}) {
  const ctx = React.useContext(DrawerContext);
  if (!ctx) throw new Error('DrawerPortal must be used within Drawer');

  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (contentRef.current) {
      const focusable = contentRef.current.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      focusable?.focus();
    }
  }, []);

  const slideInitial =
    position === 'right' ? { x: 24, opacity: 0 } : { y: 24, opacity: 0 };
  const slideAnimate =
    position === 'right' ? { x: 0, opacity: 1 } : { y: 0, opacity: 1 };

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: isStill ? 0 : 0.15 }}
        onClick={ctx.onClose}
        className="fixed inset-0 bg-black/60 backdrop-blur-sm"
        aria-hidden="true"
      />

      {/* Drawer Surface */}
      <motion.div
        ref={contentRef}
        role="dialog"
        aria-modal="true"
        initial={isStill ? { opacity: 0 } : slideInitial}
        animate={slideAnimate}
        exit={isStill ? { opacity: 0 } : slideInitial}
        transition={isStill ? { duration: 0 } : spring.gentle}
        className={cn(
          'relative z-50 bg-surface-1 text-text border-border shadow-2xl p-6 flex flex-col',
          position === 'right' &&
            'ml-auto h-full w-full max-w-md border-l',
          position === 'bottom' &&
            'mt-auto w-full max-h-[85vh] rounded-t-[20px] border-t'
        )}
      >
        <button
          type="button"
          onClick={ctx.onClose}
          className="absolute right-4 top-4 rounded-md p-1.5 text-text-muted hover:text-text hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          aria-label="Close drawer"
        >
          <X className="w-4 h-4" />
        </button>
        {children}
      </motion.div>
    </div>
  );
}

export function DrawerHeader({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('flex flex-col space-y-1.5 mb-6', className)} {...props}>
      {children}
    </div>
  );
}

export function DrawerTitle({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2
      className={cn('font-display font-bold text-xl text-text leading-none tracking-tight', className)}
      {...props}
    >
      {children}
    </h2>
  );
}

export function DrawerDescription({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn('text-sm text-text-muted', className)} {...props}>
      {children}
    </p>
  );
}

export function DrawerContent({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn('flex-1 overflow-y-auto', className)} {...props}>
      {children}
    </div>
  );
}

export function DrawerFooter({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex items-center justify-end gap-3 pt-4 border-t border-border mt-auto', className)}
      {...props}
    >
      {children}
    </div>
  );
}

export default Drawer;
