'use client';

import React, { useMemo } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { cn } from '@/lib/utils';
import { Pip } from '@/components/brand/Pip';
import { getLanguageColor } from '@/lib/languages';
import { TreeNode } from '@/lib/schemas';
import { IndexingStage } from './StageStepper';
import { Button } from '@/components/ui/Button';
import { AlertCircle, RotateCcw, Compass, MapPin } from 'lucide-react';
import { ContourBackground } from '@/components/brand/ContourBackground';

interface Region {
  id: string;
  name: string;
  language: string;
  color: string;
  startIndex: number;
  endIndex: number;
}

interface FogOfWarMapProps {
  tree?: TreeNode[];
  percent: number;
  stage: IndexingStage;
  isReady?: boolean;
  isFailed?: boolean;
  error?: string | null;
  onRetry?: () => void;
  isRetrying?: boolean;
  className?: string;
}

const TOTAL_COLS = 12;
const TOTAL_ROWS = 7;
const TOTAL_TILES = TOTAL_COLS * TOTAL_ROWS; // 84 tiles

export function FogOfWarMap({
  tree,
  percent,
  stage,
  isReady = false,
  isFailed = false,
  error,
  onRetry,
  isRetrying = false,
  className,
}: FogOfWarMapProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  // Build or derive realm regions from repo folders
  const regions: Region[] = useMemo(() => {
    // If tree has directory nodes, extract top-level folders
    const dirs = (tree || []).filter((n) => n.type === 'directory');
    if (dirs.length >= 2) {
      const sliceSize = Math.floor(TOTAL_TILES / dirs.length);
      return dirs.slice(0, 6).map((dir, idx) => {
        // Find a representative language inside this directory's children
        const childLang = dir.children?.find((c) => c.language)?.language || 'TypeScript';
        return {
          id: dir.path || dir.name,
          name: dir.name,
          language: childLang,
          color: getLanguageColor(childLang),
          startIndex: idx * sliceSize,
          endIndex: idx === dirs.length - 1 ? TOTAL_TILES : (idx + 1) * sliceSize,
        };
      });
    }

    // Default synthesized realm regions if tree is fetching or small
    const defaults = [
      { name: 'core', lang: 'Python' },
      { name: 'api', lang: 'TypeScript' },
      { name: 'services', lang: 'Python' },
      { name: 'components', lang: 'TypeScript' },
      { name: 'tests', lang: 'Python' },
      { name: 'docs', lang: 'Markdown' },
    ];
    const sliceSize = Math.floor(TOTAL_TILES / defaults.length);
    return defaults.map((d, idx) => ({
      id: d.name,
      name: d.name,
      language: d.lang,
      color: getLanguageColor(d.lang),
      startIndex: idx * sliceSize,
      endIndex: idx === defaults.length - 1 ? TOTAL_TILES : (idx + 1) * sliceSize,
    }));
  }, [tree]);

  // Associate each tile index with a region
  const tiles = useMemo(() => {
    return Array.from({ length: TOTAL_TILES }).map((_, index) => {
      const region = regions.find((r) => index >= r.startIndex && index < r.endIndex) || regions[0];
      return {
        index,
        region,
        x: index % TOTAL_COLS,
        y: Math.floor(index / TOTAL_COLS),
      };
    });
  }, [regions]);

  // Pip position along revealed terrain boundary
  const effectivePercent = isReady ? 100 : Math.min(100, Math.max(0, percent));
  const pipLeftPercent = Math.min(90, Math.max(6, effectivePercent * 0.9 + 5));
  const pipTopPercent = 45 + Math.sin((effectivePercent / 100) * Math.PI * 2) * 15;

  // Determine Pip state
  const pipState = isReady
    ? 'success'
    : isFailed
    ? 'error'
    : stage === 'queued'
    ? 'idle'
    : 'exploring';

  return (
    <div
      className={cn(
        'relative w-full h-[58vh] min-h-[380px] max-h-[560px] rounded-2xl border border-border bg-surface-1 overflow-hidden select-none flex flex-col items-center justify-center isolate',
        className
      )}
    >
      {/* Background ambient contour terrain */}
      <ContourBackground opacity={0.08} />

      {/* Map Header Overlay */}
      <div className="absolute top-4 left-5 right-5 z-20 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-2.5 bg-surface-1/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-border/80">
          <Compass className="w-4 h-4 text-brand" />
          <span className="font-mono text-xs font-semibold text-text">
            Cartographer Grid
          </span>
          <span className="font-mono text-[11px] text-text-muted">
            (M2 Fog of War)
          </span>
        </div>

        {/* Region badges legend */}
        <div className="hidden lg:flex items-center gap-2 bg-surface-1/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-border/80">
          {regions.slice(0, 5).map((r) => (
            <div key={r.id} className="flex items-center gap-1.5 text-[11px] font-mono text-text-muted">
              <span
                className="w-2 h-2 rounded-[1px]"
                style={{ backgroundColor: r.color }}
              />
              <span className="truncate max-w-[80px]">{r.name}</span>
            </div>
          ))}
        </div>
      </div>

      {/* TILE GRID (Revealed Terrain + Dissolving Fog Layer) */}
      <div
        className="w-full h-full grid p-4 gap-1.5 z-10"
        style={{
          gridTemplateColumns: `repeat(${TOTAL_COLS}, minmax(0, 1fr))`,
          gridTemplateRows: `repeat(${TOTAL_ROWS}, minmax(0, 1fr))`,
        }}
      >
        {tiles.map((tile) => {
          const threshold = (tile.index / TOTAL_TILES) * 100;
          const isRevealed = effectivePercent >= threshold || isReady;

          return (
            <div
              key={tile.index}
              className="relative rounded-md overflow-hidden transition-all duration-300"
              style={{
                backgroundColor: isRevealed
                  ? `${tile.region.color}18`
                  : 'transparent',
                borderColor: isRevealed
                  ? `${tile.region.color}35`
                  : 'var(--border)',
                borderWidth: 1,
              }}
            >
              {/* Revealed Terrain Texture */}
              {isRevealed && (
                <div className="absolute inset-0 flex flex-col items-center justify-center p-1 pointer-events-none opacity-80">
                  {/* Show region label on the center tile of each region */}
                  {tile.index === Math.floor((tile.region.startIndex + tile.region.endIndex) / 2) && (
                    <span
                      className="font-mono text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded shadow-sm bg-surface-1/90 border border-border text-text truncate max-w-full"
                    >
                      {tile.region.name}
                    </span>
                  )}
                  {/* Subtle pixel grid dot */}
                  <span
                    className="w-1 h-1 rounded-[0.5px] opacity-40 mt-auto"
                    style={{ backgroundColor: tile.region.color }}
                  />
                </div>
              )}

              {/* FOG OF WAR OVERLAY TILE (Dissolves as progress arrives) */}
              <motion.div
                className="absolute inset-0 bg-surface-3/95 backdrop-blur-[1px] border border-border/40 pointer-events-none flex items-center justify-center"
                initial={false}
                animate={{
                  opacity: isRevealed ? 0 : 0.95,
                  scale: isRevealed ? 0.92 : 1,
                }}
                transition={{
                  duration: isStill ? 0 : 0.35,
                  ease: 'easeOut',
                }}
              >
                {/* Obscured fog pixel dots */}
                <div className="w-1.5 h-1.5 rounded-[0.5px] bg-border/60" />
              </motion.div>
            </div>
          );
        })}
      </div>

      {/* PIP EXPLORING WITH LANTERN (Moves along the reveal boundary) */}
      <motion.div
        className="absolute z-20 pointer-events-none transform -translate-x-1/2 -translate-y-1/2"
        initial={false}
        animate={{
          left: `${pipLeftPercent}%`,
          top: `${pipTopPercent}%`,
        }}
        transition={{
          duration: isStill ? 0 : 0.6,
          ease: 'easeInOut',
        }}
      >
        {/* Pulsing Lantern Glow */}
        {!isStill && pipState === 'exploring' && (
          <motion.div
            className="absolute -inset-4 rounded-full bg-amber/35 blur-md pointer-events-none"
            animate={{
              scale: [1, 1.35, 1],
              opacity: [0.4, 0.75, 0.4],
            }}
            transition={{
              duration: 1.2,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        )}

        {/* Pip Component */}
        <div className="relative">
          <Pip state={pipState} size={58} />
          {/* Position label indicator */}
          <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 whitespace-nowrap bg-surface-1/90 border border-border px-2 py-0.5 rounded text-[10px] font-mono text-text-muted shadow-sm">
            {isReady ? 'Peak Reached!' : `${Math.round(effectivePercent)}% Unfurled`}
          </div>
        </div>
      </motion.div>

      {/* FAILURE OVERLAY STATE */}
      {isFailed && (
        <div className="absolute inset-0 z-30 bg-bg/80 backdrop-blur-sm flex flex-col items-center justify-center p-6 text-center">
          <div className="p-3 bg-flame/15 rounded-full text-flame mb-3 border border-flame/30">
            <AlertCircle className="w-8 h-8" />
          </div>
          <h3 className="font-display font-bold text-lg text-text">
            Indexing Encountered an Issue
          </h3>
          <p className="text-xs text-text-muted mt-1 mb-5 max-w-md">
            {error || 'An unexpected error occurred during repository ingestion. Please check connection and retry.'}
          </p>
          {onRetry && (
            <Button
              variant="primary"
              onClick={onRetry}
              loading={isRetrying}
              className="gap-2 shadow-sm"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Retry Indexing</span>
            </Button>
          )}
        </div>
      )}

      {/* SUCCESS SUMMIT FLAGPIN (When ready) */}
      {isReady && (
        <motion.div
          className="absolute top-1/2 right-12 z-20 pointer-events-none -translate-y-1/2"
          initial={isStill ? { scale: 1 } : { scale: 0, rotate: -15 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 380, damping: 16 }}
        >
          <div className="flex items-center gap-2 bg-mint/15 border border-mint/40 text-mint px-3.5 py-2 rounded-xl backdrop-blur-md shadow-md">
            <MapPin className="w-4 h-4 text-mint" />
            <span className="font-display font-bold text-xs">
              Summit Claimed
            </span>
          </div>
        </motion.div>
      )}
    </div>
  );
}
