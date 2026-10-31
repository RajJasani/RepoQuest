'use client';

import React from 'react';
import { Handle, Position } from '@xyflow/react';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { cn } from '@/lib/utils';
import { getLanguageColor } from '@/lib/languages';
import { spring } from '@/lib/motion';

export interface ModuleNodeData {
  id: string;
  name: string;
  path: string;
  language?: string;
  fileCount: number;
  entryPoints?: string[];
  distanceFromEntry?: number;
  isHovered?: boolean;
  isNeighbor?: boolean;
  isDimmed?: boolean;
  isHighlighted?: boolean;
  [key: string]: unknown;
}

export function ModuleNodeComponent({
  data,
  selected,
}: {
  data: ModuleNodeData;
  selected?: boolean;
}) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const langColor = getLanguageColor(data.language);
  const isEntryPoint = (data.entryPoints || []).length > 0;

  // Stagger entrance delay based on distance from entry point (40ms per step)
  const staggerDelay = isStill ? 0 : Math.min(0.6, (data.distanceFromEntry || 0) * 0.04);

  return (
    <motion.div
      initial={isStill ? { scale: 1, opacity: 1 } : { scale: 0.8, opacity: 0 }}
      animate={{
        scale: 1,
        opacity: data.isDimmed ? 0.35 : 1,
      }}
      transition={
        isStill
          ? { duration: 0 }
          : {
              delay: staggerDelay,
              type: 'spring',
              stiffness: spring.snappy.stiffness,
              damping: spring.snappy.damping,
            }
      }
      className={cn(
        'relative rounded-xl cursor-pointer select-none transition-all duration-200',
        // Selected node: Aurora outline
        selected && 'p-[2px] bg-gradient-to-r from-brand via-brand-2 to-rose shadow-[0_0_16px_rgba(108,140,255,0.4)]',
        // Highlighted (e.g. Start Here)
        !selected && data.isHighlighted && 'p-[2px] bg-gradient-to-r from-amber to-mint shadow-[0_0_12px_rgba(245,165,36,0.5)]',
        // Hover glow
        data.isHovered && !selected && 'ring-2 ring-brand shadow-[0_0_12px_rgba(108,140,255,0.3)]'
      )}
      style={{
        width: 160 + Math.min(24, Math.floor((data.fileCount || 0) / 5) * 4),
        height: 64,
      }}
    >
      {/* Target & Source Handles for Edge routing */}
      <Handle
        type="target"
        position={Position.Top}
        className="w-2 h-2 !bg-border border border-surface-1"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="w-2 h-2 !bg-brand border border-surface-1"
      />

      {/* Node Inner Container */}
      <div className="w-full h-full rounded-[10px] bg-surface-1 hover:bg-surface-2 border border-border px-3 py-2 flex flex-col justify-between overflow-hidden">
        {/* Top row: Language dot, title, entry badge */}
        <div className="flex items-center justify-between gap-1.5 min-w-0">
          <div className="flex items-center gap-1.5 min-w-0">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: langColor }}
              title={data.language || 'Module'}
            />
            <span className="font-display font-bold text-xs text-text truncate max-w-[95px]">
              {data.name}
            </span>
          </div>

          {isEntryPoint && (
            <span className="shrink-0 px-1 py-0.2 bg-mint/15 text-mint border border-mint/30 rounded text-[9px] font-mono font-bold uppercase">
              Entry
            </span>
          )}
        </div>

        {/* Bottom row: Path & File count in mono */}
        <div className="flex items-center justify-between font-mono text-[10px] text-text-muted/80 pt-1 border-t border-border/40">
          <span className="truncate max-w-[80px]" title={data.path}>
            {data.path === '.' ? 'root' : data.path}
          </span>
          <span className="shrink-0 text-text-muted font-semibold">
            {data.fileCount} {data.fileCount === 1 ? 'file' : 'files'}
          </span>
        </div>
      </div>
    </motion.div>
  );
}

export default ModuleNodeComponent;
