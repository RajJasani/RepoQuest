'use client';

import React from 'react';
import { BaseEdge, EdgeProps, getBezierPath } from '@xyflow/react';
import { motion, useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';

export interface ModuleEdgeData {
  weight?: number;
  isDimmed?: boolean;
  isHighlighted?: boolean;
  [key: string]: unknown;
}

export function ModuleEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
  data,
}: EdgeProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStill = Boolean(reduce) || calm;

  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const edgeData = data as ModuleEdgeData | undefined;
  const weight = edgeData?.weight || 1;
  const strokeWidth = Math.min(4, Math.max(1.5, weight * 0.8));
  const isDimmed = edgeData?.isDimmed || false;
  const isHighlighted = edgeData?.isHighlighted || false;

  const strokeColor = isHighlighted
    ? 'var(--amber)'
    : 'var(--brand)';

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          ...style,
          strokeWidth,
          stroke: strokeColor,
          opacity: isDimmed ? 0.25 : 0.65,
          transition: 'opacity 0.2s ease, stroke 0.2s ease',
        }}
      />
      {/* Animated SVG draw path with stroke-dashoffset */}
      {!isStill && !isDimmed && (
        <motion.path
          d={edgePath}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
          style={{ opacity: 0.8 }}
        />
      )}
    </>
  );
}

export default ModuleEdgeComponent;

