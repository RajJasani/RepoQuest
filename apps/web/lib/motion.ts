import type { Variants, Transition } from 'framer-motion';

export const ease = {
  out: [0.16, 1, 0.3, 1],
  inOut: [0.65, 0, 0.35, 1],
  in: [0.7, 0, 0.84, 0],
} as const;

export const spring: Record<'snappy' | 'gentle' | 'bouncy', Transition> = {
  snappy: { type: 'spring', stiffness: 260, damping: 24 },
  gentle: { type: 'spring', stiffness: 140, damping: 20 },
  bouncy: { type: 'spring', stiffness: 380, damping: 16 },
};

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.24, ease: ease.out } },
  exit: { opacity: 0, y: 6, transition: { duration: 0.15, ease: ease.in } },
};

export const stagger = (gap = 0.04): Variants => ({
  hidden: {},
  show: { transition: { staggerChildren: gap, delayChildren: 0.05 } },
});

export const stamp: Variants = {
  hidden: { opacity: 0, scale: 1.4, rotate: -8 },
  show: { opacity: 1, scale: 1, rotate: -8, transition: spring.bouncy },
};

export const popIn: Variants = {
  hidden: { opacity: 0, scale: 0.8 },
  show: { opacity: 1, scale: 1, transition: spring.snappy },
};

