'use client';

import React from 'react';
import { motion, useReducedMotion, type TargetAndTransition } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { cn } from '@/lib/utils';

export type PipState = 'idle' | 'thinking' | 'exploring' | 'success' | 'error' | 'sleeping';

export interface PipProps {
  state?: PipState;
  size?: number;
  className?: string;
}

// 14 wide by 12 tall base pixel map
// . = empty, B = body (Sky), W = eye white, K = ink, A = amber
const BASE_MAP = [
  '......AA......', // 0
  '......KK......', // 1
  '..BBBBBBBBBB..', // 2
  '.BBBBBBBBBBBB.', // 3
  'BBBWWBBBBWWBBB', // 4
  'BBBWKBBBBKWBBB', // 5
  'BBBWWBBBBWWBBB', // 6
  'BBBBBBBBBBBBBB', // 7
  '.BKKKKKKKKKKB.', // 8
  '.BKAKAKAKAKKB.', // 9
  '..BBBBBBBBBB..', // 10
  '...BB....BB...', // 11
];

export function Pip({ state = 'idle', size = 96, className }: PipProps) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const isStatic = Boolean(reduce) || calm;

  // Colors
  const sky = 'var(--sky)';
  const amber = 'var(--amber)';
  const ink = '#171A2B';
  const white = '#F7FAFF';

  // Body animation presets
  const bodyAnimations: Record<PipState, TargetAndTransition> = {
    idle: {
      y: [0, -1, 0],
      transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' },
    },
    thinking: {
      rotate: [0, -1.5, 1.5, 0],
      transition: { duration: 1.2, repeat: Infinity, ease: 'easeInOut' },
    },
    exploring: {
      y: [0, -1, 0],
      transition: { duration: 0.4, repeat: Infinity, ease: 'linear' },
    },
    success: {
      y: [0, 2, -10, 0],
      transition: { duration: 0.7, repeat: Infinity, repeatDelay: 2, ease: 'easeOut' },
    },
    error: {
      x: [0, -2, 2, -2, 0],
      transition: { duration: 0.36, times: [0, 0.25, 0.5, 0.75, 1] },
    },
    sleeping: {
      y: [0, -0.5, 0],
      transition: { duration: 4, repeat: Infinity, ease: 'easeInOut' },
    },
  };

  // Antenna animation presets
  const antennaAnimations: Record<PipState, TargetAndTransition> = {
    idle: {
      rotate: [0, 6, -6, 0],
      transition: { duration: 2.4, repeat: Infinity, ease: 'easeInOut' },
    },
    thinking: {
      rotate: [0, -3, 3, 0],
      transition: { duration: 0.6, repeat: Infinity },
    },
    exploring: {
      rotate: [0, 4, 0],
      transition: { duration: 0.4, repeat: Infinity },
    },
    success: {
      scale: [1, 1.2, 1],
      transition: { duration: 0.5, repeat: Infinity, repeatDelay: 2 },
    },
    error: {
      rotate: 32, // droop
      transition: { duration: 0.3 },
    },
    sleeping: {
      rotate: 15,
      transition: { duration: 0.5 },
    },
  };

  // Legs animation (exploring)
  const leftLegAnim: TargetAndTransition = {
    y: [0, -1, 0],
    transition: { duration: 0.4, repeat: Infinity, ease: 'linear' },
  };
  const rightLegAnim: TargetAndTransition = {
    y: [-1, 0, -1],
    transition: { duration: 0.4, repeat: Infinity, ease: 'linear' },
  };

  // Eyes animation (blinking or scanning)
  const eyesBlinkAnim: TargetAndTransition = {
    scaleY: [1, 1, 0.1, 1, 1],
    transition: {
      duration: 4,
      repeat: Infinity,
      times: [0, 0.9, 0.93, 0.96, 1],
    },
  };

  const pupilsScanAnim: TargetAndTransition = {
    x: [-0.6, 0.6, -0.6],
    transition: { duration: 1, repeat: Infinity, ease: 'easeInOut' },
  };

  // Separate pixels into semantic layers:
  // Head & Body (rows 2 to 10 except eyes)
  // Left eye: (x=3,4; y=4,5,6)
  // Right eye: (x=9,10; y=4,5,6)
  // Antenna: (x=6,7; y=0,1)
  // Legs: Left (x=3,4; y=11), Right (x=9,10; y=11)
  const bodyPixels: Array<{ x: number; y: number; fill: string }> = [];
  const leftEyePixels: Array<{ x: number; y: number; isPupil: boolean }> = [];
  const rightEyePixels: Array<{ x: number; y: number; isPupil: boolean }> = [];
  const antennaPixels: Array<{ x: number; y: number; isTip: boolean }> = [];
  const leftLegPixels: Array<{ x: number; y: number }> = [];
  const rightLegPixels: Array<{ x: number; y: number }> = [];

  BASE_MAP.forEach((row, y) => {
    row.split('').forEach((char, x) => {
      if (char === '.') return;

      // Antenna
      if (y <= 1 && (x === 6 || x === 7)) {
        antennaPixels.push({ x, y, isTip: y === 0 });
        return;
      }

      // Legs
      if (y === 11) {
        if (x === 3 || x === 4) leftLegPixels.push({ x, y });
        if (x === 9 || x === 10) rightLegPixels.push({ x, y });
        return;
      }

      // Left eye
      if ((y === 4 || y === 5 || y === 6) && (x === 3 || x === 4)) {
        leftEyePixels.push({ x, y, isPupil: x === 4 && y === 5 });
        return;
      }

      // Right eye
      if ((y === 4 || y === 5 || y === 6) && (x === 9 || x === 10)) {
        rightEyePixels.push({ x, y, isPupil: x === 10 && y === 5 });
        return;
      }

      // Body & Torso
      let fill = sky;
      if (char === 'K') fill = ink;
      if (char === 'A') fill = amber;
      bodyPixels.push({ x, y, fill });
    });
  });

  return (
    <svg
      viewBox="0 0 18 16"
      width={size}
      height={(size * 16) / 18}
      shapeRendering="crispEdges"
      className={cn('inline-block overflow-visible select-none', className)}
      role="img"
      aria-label={`Pip is ${state}`}
    >
      {/* Pip Main Body Group with offset (x+2, y+3) to give room for accessories */}
      <motion.g
        transform="translate(2, 3)"
        animate={isStatic ? undefined : bodyAnimations[state]}
      >
        {/* Torso & Head Background */}
        {bodyPixels.map((p) => (
          <rect key={`${p.x}-${p.y}`} x={p.x} y={p.y} width={1} height={1} fill={p.fill} />
        ))}

        {/* Antenna Group (pivoting around connection at (6.5, 2)) */}
        <motion.g
          style={{ transformOrigin: '6.5px 2px' }}
          animate={isStatic ? (state === 'error' ? { rotate: 32 } : state === 'sleeping' ? { rotate: 15 } : undefined) : antennaAnimations[state]}
        >
          {antennaPixels.map((p) => (
            <rect
              key={`ant-${p.x}-${p.y}`}
              x={p.x}
              y={p.y}
              width={1}
              height={1}
              fill={p.isTip ? amber : ink}
            />
          ))}
          {/* Antenna Spark Pixel (Success State) */}
          {state === 'success' && (
            <motion.rect
              x={6.5}
              y={-1.5}
              width={1}
              height={1}
              fill={amber}
              animate={isStatic ? undefined : { scale: [0.8, 1.4, 0.8], opacity: [0.6, 1, 0.6] }}
              transition={{ duration: 0.4, repeat: Infinity }}
            />
          )}
        </motion.g>

        {/* Eyes Group */}
        {state === 'error' ? (
          /* Error State: Cross pupils */
          <g>
            {/* Left Eye Cross */}
            <rect x={3} y={4} width={1} height={1} fill={ink} />
            <rect x={4} y={6} width={1} height={1} fill={ink} />
            <rect x={4} y={4} width={1} height={1} fill={ink} />
            <rect x={3} y={6} width={1} height={1} fill={ink} />
            <rect x={3.5} y={5} width={1} height={1} fill={ink} />
            {/* Right Eye Cross */}
            <rect x={9} y={4} width={1} height={1} fill={ink} />
            <rect x={10} y={6} width={1} height={1} fill={ink} />
            <rect x={10} y={4} width={1} height={1} fill={ink} />
            <rect x={9} y={6} width={1} height={1} fill={ink} />
            <rect x={9.5} y={5} width={1} height={1} fill={ink} />
          </g>
        ) : state === 'sleeping' ? (
          /* Sleeping State: Closed horizontal lines */
          <g>
            <rect x={3} y={5.5} width={2} height={0.8} fill={ink} />
            <rect x={9} y={5.5} width={2} height={0.8} fill={ink} />
          </g>
        ) : (
          /* Normal, Thinking, Exploring, Success Eyes */
          <motion.g
            style={{ transformOrigin: '7px 5px' }}
            animate={isStatic ? undefined : state === 'idle' ? eyesBlinkAnim : undefined}
          >
            {/* Eye whites */}
            {leftEyePixels.map((p) => (
              <rect key={`le-${p.x}-${p.y}`} x={p.x} y={p.y} width={1} height={1} fill={p.isPupil ? ink : white} />
            ))}
            {rightEyePixels.map((p) => (
              <rect key={`re-${p.x}-${p.y}`} x={p.x} y={p.y} width={1} height={1} fill={p.isPupil ? ink : white} />
            ))}

            {/* Thinking pupil scan override */}
            {state === 'thinking' && !isStatic && (
              <motion.g animate={pupilsScanAnim}>
                <rect x={3.8} y={5} width={1} height={1} fill={ink} />
                <rect x={9.8} y={5} width={1} height={1} fill={ink} />
              </motion.g>
            )}
          </motion.g>
        )}

        {/* Legs Groups */}
        <motion.g animate={state === 'exploring' && !isStatic ? leftLegAnim : undefined}>
          {leftLegPixels.map((p) => (
            <rect key={`ll-${p.x}-${p.y}`} x={p.x} y={p.y} width={1} height={1} fill={sky} />
          ))}
        </motion.g>
        <motion.g animate={state === 'exploring' && !isStatic ? rightLegAnim : undefined}>
          {rightLegPixels.map((p) => (
            <rect key={`rl-${p.x}-${p.y}`} x={p.x} y={p.y} width={1} height={1} fill={sky} />
          ))}
        </motion.g>

        {/* State-Only Accessory 1: Lantern (Exploring) */}
        {state === 'exploring' && (
          <g transform="translate(13.5, 6)">
            {/* Glow circle */}
            <motion.circle
              cx="1"
              cy="2.5"
              r="3.5"
              fill={amber}
              opacity="0.25"
              animate={isStatic ? undefined : { r: [3, 4.5, 3], opacity: [0.2, 0.4, 0.2] }}
              transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
            />
            {/* Lantern frame */}
            <rect x="0.5" y="0" width="1" height="0.6" fill={ink} />
            <rect x="0" y="0.6" width="2" height="3" rx="0.5" fill="var(--surface-1)" stroke={ink} strokeWidth="0.5" />
            <rect x="0.5" y="1.2" width="1" height="1.6" fill={amber} />
          </g>
        )}

        {/* State-Only Accessory 2: Thinking Indicator Dots */}
        {state === 'thinking' && (
          <g transform="translate(5, -2)">
            {[0, 1.8, 3.6].map((offset, i) => (
              <motion.rect
                key={`dot-${i}`}
                x={offset}
                y={0}
                width={1}
                height={1}
                fill={amber}
                animate={isStatic ? undefined : { opacity: [0.3, 1, 0.3], y: [0, -0.6, 0] }}
                transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.2 }}
              />
            ))}
          </g>
        )}

        {/* State-Only Accessory 3: Sleeping Floating Zs */}
        {state === 'sleeping' && (
          <g transform="translate(11.5, -1)">
            {/* Z 1 */}
            <motion.text
              x="0"
              y="0"
              fill={sky}
              fontSize="3.5"
              fontFamily="var(--font-pixel)"
              animate={isStatic ? undefined : { y: [0, -3], opacity: [0.9, 0], x: [0, 1] }}
              transition={{ duration: 2.2, repeat: Infinity, ease: 'easeOut' }}
            >
              Z
            </motion.text>
            {/* Z 2 */}
            <motion.text
              x="1.5"
              y="-1"
              fill={sky}
              fontSize="2.5"
              fontFamily="var(--font-pixel)"
              animate={isStatic ? undefined : { y: [0, -3.5], opacity: [0.8, 0], x: [1.5, 2.5] }}
              transition={{ duration: 2.4, repeat: Infinity, delay: 0.8, ease: 'easeOut' }}
            >
              z
            </motion.text>
          </g>
        )}

        {/* State-Only Accessory 4: Success Burst Spark Pixels */}
        {state === 'success' && (
          <g transform="translate(7, 4)">
            {[
              { x: -7, y: -4 },
              { x: 7, y: -4 },
              { x: -6, y: 3 },
              { x: 6, y: 3 },
              { x: 0, y: -8 },
              { x: 0, y: 7 },
            ].map((spark, i) => (
              <motion.rect
                key={`spark-${i}`}
                x={0}
                y={0}
                width={1}
                height={1}
                fill={amber}
                animate={isStatic ? undefined : {
                  x: [0, spark.x],
                  y: [0, spark.y],
                  opacity: [1, 0],
                  scale: [1, 0.6],
                }}
                transition={{ duration: 0.7, repeat: Infinity, repeatDelay: 2 }}
              />
            ))}
          </g>
        )}
      </motion.g>
    </svg>
  );
}
