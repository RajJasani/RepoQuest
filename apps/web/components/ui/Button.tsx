'use client';

import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { SignatureStrip } from '@/components/brand/SignatureStrip';
import { useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from './Dialog';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  shimmer?: boolean;
  confirmTitle?: string;
  confirmDescription?: string;
  dangerWithConfirm?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = 'primary',
      size = 'md',
      loading = false,
      disabled = false,
      shimmer = false,
      dangerWithConfirm = false,
      confirmTitle = 'Are you sure?',
      confirmDescription = 'This action cannot be undone.',
      onClick,
      children,
      ...props
    },
    ref
  ) => {
    const reduce = useReducedMotion();
    const { calm } = useCalmMode();
    const isStill = Boolean(reduce) || calm;
    const [confirmOpen, setConfirmOpen] = useState(false);

    const sizeClasses = {
      sm: 'h-8 px-3 text-xs',
      md: 'h-10 px-4 text-sm min-h-[40px]',
      lg: 'h-12 px-6 text-base min-h-[48px]',
    }[size];

    const variantClasses = {
      primary:
        'bg-gradient-to-r from-brand via-brand-2 to-rose text-white shadow-sm hover:brightness-110 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.97]',
      secondary:
        'bg-surface-2 text-text border border-border hover:bg-surface-3 active:scale-[0.97]',
      ghost:
        'bg-transparent text-text hover:bg-surface-3 active:scale-[0.97]',
      danger:
        'bg-flame text-white hover:brightness-110 active:scale-[0.97]',
    }[variant];

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      if (disabled || loading) return;
      if (variant === 'danger' && dangerWithConfirm) {
        e.preventDefault();
        setConfirmOpen(true);
        return;
      }
      onClick?.(e);
    };

    const handleConfirm = (e: React.MouseEvent<HTMLButtonElement>) => {
      setConfirmOpen(false);
      onClick?.(e);
    };

    return (
      <>
        <button
          ref={ref}
          disabled={disabled || loading}
          onClick={handleClick}
          className={cn(
            'relative inline-flex items-center justify-center font-medium rounded-[10px] select-none transition-all duration-150 overflow-hidden',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
            'disabled:opacity-50 disabled:pointer-events-none disabled:transform-none',
            sizeClasses,
            variantClasses,
            isStill && 'transform-none hover:transform-none active:transform-none',
            className
          )}
          {...props}
        >
          {/* Shimmer sweep effect */}
          {shimmer && !isStill && !disabled && !loading && (
            <span
              className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent pointer-events-none"
              style={{
                backgroundSize: '200% 100%',
                animation: 'shimmer 2.5s infinite linear',
              }}
              aria-hidden="true"
            />
          )}

          {loading ? (
            <span className="inline-flex items-center gap-2">
              <SignatureStrip variant="loader" size={6} />
              <span className="opacity-90">{children}</span>
            </span>
          ) : (
            children
          )}
        </button>

        {dangerWithConfirm && (
          <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{confirmTitle}</DialogTitle>
                <DialogDescription>{confirmDescription}</DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <button
                  type="button"
                  onClick={() => setConfirmOpen(false)}
                  className="px-4 py-2 text-sm rounded-[10px] border border-border bg-surface-2 text-text hover:bg-surface-3 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleConfirm}
                  className="px-4 py-2 text-sm rounded-[10px] bg-flame text-white hover:brightness-110 transition-colors"
                >
                  Confirm Delete
                </button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        )}
      </>
    );
  }
);

Button.displayName = 'Button';
export default Button;
