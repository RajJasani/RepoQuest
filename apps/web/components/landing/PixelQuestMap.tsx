'use client';

import React, { useState, useEffect } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { Pip } from '@/components/brand/Pip';
import { PixelIcon } from '@/components/brand/PixelIcon';
import { spring } from '@/lib/motion';
import { cn } from '@/lib/utils';

// 10 wide by 8 high terrain tile grid
// Legend:
// . = Sky / Atmosphere (empty)
// S = Summit rock / snow (var(--surface-3) or highlight)
// G = Grassland / Forest (var(--mint) or muted green)
// M = Mountain slopes (var(--border) or slate)
// P = Path / Dirt trail (var(--amber) or warm earth)
// W = Water / River (var(--sky))
const MAP_GRID = [
  '....SSSS....',
  '...SSSSSS...',
  '..MMMSSSSS..',
  '..MMMMMMMM..',
  '.GGGPMMMMMG.',
  '.GGGPPMMGGG.',
  'GGGGPPPGGGGG',
  'WWWWPPPGGWWW',
];

const TILE_COLORS: Record<string, string> = {
  S: 'var(--surface-3)',
  M: 'var(--border)',
  G: 'var(--mint)',
  P: 'var(--amber)',
  W: 'var(--sky)',
};

export function PixelQuestMap({ className }: { className?: string }) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const [flagPlanted, setFlagPlanted] = useState(isStill);

  useEffect(() => {
    if (isStill) {
      setFlagPlanted(true);
      return;
    }
    // Flag plants after Pip walks to the summit (around 1200ms)
    const timer = setTimeout(() => {
      setFlagPlanted(true);
    }, 1200);
    return () => clearTimeout(timer);
  }, [isStill]);

  const rows = MAP_GRID.length;
  const cols = MAP_GRID[0].length;
  const tileSize = 20;

  return (
    <div
      className={cn(
        'relative rounded-xl border border-border bg-surface-1 p-4 shadow-card overflow-hidden select-none flex flex-col items-center justify-center',
        className
      )}
      role="img"
      aria-label="Interactive Pixel Quest Map Realm"
    >
      {/* Realm Canvas Grid */}
      <div
        className="relative"
        style={{
          width: cols * tileSize,
          height: rows * tileSize,
        }}
      >
        {MAP_GRID.map((row, y) =>
          row.split('').map((char, x) => {
            if (char === '.') return null;

            const color = TILE_COLORS[char] || 'var(--border)';
            // Diagonal wave delay: 24 ms apart based on (x + y)
            const delay = 0.7 + (x + y) * 0.024;

            return (
              <motion.div
                key={`${x}-${y}`}
                initial={isStill ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.6 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={
                  isStill
                    ? { duration: 0 }
                    : { duration: 0.25, delay, ease: 'easeOut' }
                }
                className="absolute rounded-[2px]"
                style={{
                  left: x * tileSize,
                  top: y * tileSize,
                  width: tileSize - 1.5,
                  height: tileSize - 1.5,
                  backgroundColor: color,
                  opacity: char === 'G' ? 0.35 : char === 'W' ? 0.45 : 0.7,
                }}
              />
            );
          })
        )}

        {/* Amber Flag planted on the Summit Peak (x=5, y=0) */}
        {flagPlanted && (
          <motion.div
            initial={isStill ? { scale: 1, y: 0 } : { scale: 0, y: -10 }}
            animate={{ scale: 1, y: 0 }}
            transition={isStill ? { duration: 0 } : spring.bouncy}
            className="absolute z-20"
            style={{
              left: 5 * tileSize - 2,
              top: 0,
            }}
          >
            <PixelIcon name="flag" size={18} className="text-amber" />
          </motion.div>
        )}

        {/* Pip walking from left edge toward the summit */}
        <motion.div
          initial={isStill ? { x: 0, opacity: 1 } : { x: -60, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          transition={
            isStill
              ? { duration: 0 }
              : {
                  duration: 1.1,
                  delay: 0.7,
                  ease: 'easeInOut',
                }
          }
          className="absolute z-20"
          style={{
            left: 3.5 * tileSize,
            top: 0.5 * tileSize,
          }}
        >
          <Pip state={flagPlanted ? 'idle' : 'exploring'} size={36} />
        </motion.div>
      </div>

      {/* Caption badge */}
      <div className="mt-3 flex items-center gap-2 text-[11px] font-mono text-text-muted">
        <span className="w-1.5 h-1.5 rounded-full bg-amber animate-pulse" />
        <span>Pixel Realm Summit: +50 XP</span>
      </div>
    </div>
  );
}

export default PixelQuestMap;

