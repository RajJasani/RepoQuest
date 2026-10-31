'use client';

import React from 'react';
import { cn } from '@/lib/utils';

export type PixelIconName =
  | 'compass'
  | 'flag'
  | 'shield'
  | 'cracked-shield'
  | 'cracked_shield'
  | 'scroll'
  | 'lantern'
  | 'key'
  | 'spark'
  | 'crown'
  | 'lock';

export interface PixelIconProps extends React.SVGProps<SVGSVGElement> {
  name: PixelIconName;
  size?: number | string;
  mono?: boolean;
  className?: string;
  ariaLabel?: string;
}

// 16x16 pixel grids
// Key:
// . = empty / transparent
// # = primary text/border (currentColor or var(--text))
// A = Amber (var(--amber))
// S = Sky (var(--sky))
// R = Rose (var(--rose))
// M = Mint (var(--mint))
// W = Highlight / surface (var(--surface-1))
// D = Border / outline (var(--border))

const ICON_GRIDS: Record<string, string[]> = {
  compass: [
    '....########....',
    '..##...AA...##..',
    '.##....AA....##.',
    '.##...AAAA...##.',
    '#....AA##SS....#',
    '#...AA####SS...#',
    '#..AA######SS..#',
    '#.AA########SS.#',
    '#.SS########AA.#',
    '#..SS######AA..#',
    '#...SS####AA...#',
    '#....SS##AA....#',
    '.##...SSSS...##.',
    '.##....SS....##.',
    '..##...SS...##..',
    '....########....',
  ],
  flag: [
    '..##............',
    '.####...........',
    '..##............',
    '..##..AAAAAAAA..',
    '..##..AAAAAAAAA.',
    '..##..AAAAAAAAAA',
    '..##..AAAAAAAAA.',
    '..##..AAAAAAAA..',
    '..##..##........',
    '..##............',
    '..##............',
    '..##............',
    '..##............',
    '..##............',
    '.####...........',
    '######..........',
  ],
  shield: [
    '.##############.',
    '.##############.',
    '.##SSSS##SSSS##.',
    '.##SSSS##SSSS##.',
    '.##SSSS##SSSS##.',
    '.##SSSS##SSSS##.',
    '.##############.',
    '.##AAAA##AAAA##.',
    '.##AAAA##AAAA##.',
    '.##AAAA##AAAA##.',
    '..##AAA##AAA##..',
    '...##AA##AA##...',
    '....##A##A##....',
    '.....######.....',
    '......####......',
    '.......##.......',
  ],
  'cracked-shield': [
    '.##############.',
    '.##############.',
    '.##SSSS##SSSS##.',
    '.##SSSS.##SSS##.',
    '.##SSS...#SSS##.',
    '.##SSSS...SSS##.',
    '.########..####.',
    '.##AAAA#..AAA##.',
    '.##AAA...AAAA##.',
    '.##AA..#AAAAA##.',
    '..##A..##AAA##..',
    '...##...#AA##...',
    '....##A..#A##...',
    '.....##.###.....',
    '......####......',
    '.......##.......',
  ],
  scroll: [
    '.############...',
    '##WWWWWWWWWW##..',
    '#WWAAAAAAAAAWW#.',
    '#WWAAAAAAAAAWW#.',
    '##WAA#####AAAW##',
    '.##AAAAAAAAAA##.',
    '.##AA######AA##.',
    '.##AAAAAAAAAA##.',
    '.##AA####AAAA##.',
    '.##AAAAAAAAAA##.',
    '.##AA######AA##.',
    '.##AAAAAAAAAA##.',
    '##WAA#####AAAW##',
    '#WWAAAAAAAAAWW#.',
    '##WWWWWWWWWW##..',
    '.############...',
  ],
  lantern: [
    '......####......',
    '.....##..##.....',
    '......####......',
    '....########....',
    '...##########...',
    '...##......##...',
    '...##.AAAA.##...',
    '...##.AAAA.##...',
    '...##.AMMA.##...',
    '...##.AMMA.##...',
    '...##.AAAA.##...',
    '...##......##...',
    '...##########...',
    '....########....',
    '.....######.....',
    '....########....',
  ],
  key: [
    '.....######.....',
    '...##########...',
    '..####....####..',
    '..###......###..',
    '..###......###..',
    '..####....####..',
    '...##########...',
    '.....######.....',
    '.......##.......',
    '.......##.......',
    '.......####.....',
    '.......##.......',
    '.......####.....',
    '.......######...',
    '.......##.......',
    '.......##.......',
  ],
  spark: [
    '.......##.......',
    '.......##.......',
    '......####......',
    '.....##AA##.....',
    '.....##AA##.....',
    '...###AAAA###...',
    '.######AA######.',
    '##AAAAAAAAAAAA##',
    '##AAAAAAAAAAAA##',
    '.######AA######.',
    '...###AAAA###...',
    '.....##AA##.....',
    '.....##AA##.....',
    '......####......',
    '.......##.......',
    '.......##.......',
  ],
  crown: [
    '................',
    '.......##.......',
    '.##...####...##.',
    '####..####..####',
    '.##....##....##.',
    '.##...AAAA...##.',
    '.##..AAAAAA..##.',
    '.##.AAAAAAAA.##.',
    '.##############.',
    '.##############.',
    '.##A########A##.',
    '.##ARRA#SSAARA#.',
    '.##ARRA#SSAARA#.',
    '.##A########A##.',
    '.##############.',
    '................',
  ],
  lock: [
    '.....######.....',
    '...##......##...',
    '..##........##..',
    '..##........##..',
    '..##........##..',
    '..##........##..',
    '.##############.',
    '.##############.',
    '.##....##....##.',
    '.##...####...##.',
    '.##...####...##.',
    '.##....##....##.',
    '.##....##....##.',
    '.##...####...##.',
    '.##############.',
    '.##############.',
  ],
};

// Alias cracked_shield
ICON_GRIDS['cracked_shield'] = ICON_GRIDS['cracked-shield'];

export function PixelIcon({
  name,
  size = 16,
  mono = false,
  className,
  ariaLabel,
  ...props
}: PixelIconProps) {
  const normalizedName = name === 'cracked_shield' ? 'cracked-shield' : name;
  const grid = ICON_GRIDS[normalizedName] || ICON_GRIDS.compass;

  const getColor = (c: string) => {
    if (mono) return 'currentColor';
    switch (c) {
      case '#':
        return 'currentColor';
      case 'A':
        return 'var(--amber)';
      case 'S':
        return 'var(--sky)';
      case 'R':
        return 'var(--rose)';
      case 'M':
        return 'var(--mint)';
      case 'W':
        return 'var(--surface-1)';
      case 'D':
        return 'var(--border)';
      default:
        return 'transparent';
    }
  };

  const label = ariaLabel || `${normalizedName} pixel icon`;

  return (
    <svg
      viewBox="0 0 16 16"
      width={size}
      height={size}
      shapeRendering="crispEdges"
      className={cn('inline-block flex-shrink-0 align-middle', className)}
      role="img"
      aria-label={label}
      {...props}
    >
      {grid.flatMap((row, y) =>
        row.split('').map((char, x) =>
          char === '.' ? null : (
            <rect
              key={`${x}-${y}`}
              x={x}
              y={y}
              width={1}
              height={1}
              fill={getColor(char)}
            />
          )
        )
      )}
    </svg>
  );
}
