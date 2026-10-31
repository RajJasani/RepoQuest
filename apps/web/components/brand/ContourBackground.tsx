'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';
import { cn } from '@/lib/utils';

// 24 hand-tuned topographic wavy closed contour paths spanning a 2400x1400 canvas
// Designed to mimic ancient elevation maps and topographic quest terrain
const CONTOUR_PATHS: string[] = [
  // Ridge 1 (North-West highland loops, 8 nested elevation rings)
  'M 420 180 C 480 150, 560 160, 620 200 C 670 235, 680 300, 650 350 C 615 405, 520 420, 450 400 C 390 380, 350 320, 360 260 C 370 210, 390 195, 420 180 Z',
  'M 390 150 C 470 110, 580 120, 660 170 C 720 215, 730 300, 700 370 C 660 440, 550 460, 460 440 C 370 415, 320 340, 330 260 C 340 190, 360 170, 390 150 Z',
  'M 360 120 C 460 70, 600 80, 700 140 C 770 190, 780 300, 750 390 C 700 480, 570 500, 460 480 C 350 450, 290 360, 300 260 C 310 170, 330 140, 360 120 Z',
  'M 330 90 C 450 30, 620 40, 740 110 C 820 165, 830 300, 800 410 C 740 520, 590 540, 460 520 C 330 490, 260 380, 270 260 C 280 150, 300 110, 330 90 Z',
  'M 300 60 C 440 -10, 640 0, 780 80 C 870 140, 880 300, 850 430 C 780 560, 610 580, 460 560 C 310 530, 230 400, 240 260 C 250 130, 270 80, 300 60 Z',
  'M 270 30 C 430 -50, 660 -40, 820 50 C 920 115, 930 300, 900 450 C 820 600, 630 620, 460 600 C 290 570, 200 420, 210 260 C 220 110, 240 50, 270 30 Z',
  'M 240 0 C 420 -90, 680 -80, 860 20 C 970 90, 980 300, 950 470 C 860 640, 650 660, 460 640 C 270 610, 170 440, 180 260 C 190 90, 210 20, 240 0 Z',
  'M 210 -30 C 410 -130, 700 -120, 900 -10 C 1020 65, 1030 300, 1000 490 C 900 680, 670 700, 460 680 C 250 650, 140 460, 150 260 C 160 70, 180 -10, 210 -30 Z',

  // Ridge 2 (South-East summit loops, 8 nested elevation rings)
  'M 1600 780 C 1660 740, 1750 760, 1800 810 C 1850 860, 1840 930, 1790 980 C 1730 1030, 1620 1030, 1570 980 C 1520 930, 1530 840, 1600 780 Z',
  'M 1570 740 C 1650 690, 1780 720, 1840 780 C 1900 845, 1890 950, 1830 1015 C 1750 1080, 1600 1070, 1530 1010 C 1470 945, 1480 830, 1570 740 Z',
  'M 1540 700 C 1640 640, 1810 680, 1880 750 C 1950 830, 1940 970, 1870 1050 C 1770 1130, 1580 1110, 1490 1040 C 1420 960, 1430 820, 1540 700 Z',
  'M 1510 660 C 1630 590, 1840 640, 1920 720 C 2000 815, 1990 990, 1910 1085 C 1790 1180, 1560 1150, 1450 1070 C 1370 975, 1380 810, 1510 660 Z',
  'M 1480 620 C 1620 540, 1870 600, 1960 690 C 2050 800, 2040 1010, 1950 1120 C 1810 1230, 1540 1190, 1410 1100 C 1320 990, 1330 800, 1480 620 Z',
  'M 1450 580 C 1610 490, 1900 560, 2000 660 C 2100 785, 2090 1030, 1990 1155 C 1830 1280, 1520 1230, 1370 1130 C 1270 1005, 1280 790, 1450 580 Z',
  'M 1420 540 C 1600 440, 1930 520, 2040 630 C 2150 770, 2140 1050, 2030 1190 C 1850 1330, 1500 1270, 1330 1160 C 1220 1020, 1230 780, 1420 540 Z',
  'M 1390 500 C 1590 390, 1960 480, 2080 600 C 2200 755, 2190 1070, 2070 1225 C 1870 1380, 1480 1310, 1290 1190 C 1170 1035, 1180 770, 1390 500 Z',

  // Ridge 3 (Central / North-East terrace loops, 8 nested elevation rings)
  'M 1150 250 C 1220 220, 1310 240, 1360 290 C 1410 340, 1400 420, 1340 470 C 1270 520, 1160 510, 1100 460 C 1050 410, 1070 300, 1150 250 Z',
  'M 1110 210 C 1200 170, 1340 190, 1410 250 C 1480 315, 1470 435, 1390 495 C 1300 560, 1140 550, 1060 490 C 990 430, 1010 280, 1110 210 Z',
  'M 1070 170 C 1180 120, 1370 140, 1460 210 C 1550 290, 1540 450, 1440 520 C 1330 600, 1120 590, 1020 520 C 930 450, 950 260, 1070 170 Z',
  'M 1030 130 C 1160 70, 1400 90, 1510 170 C 1620 265, 1610 465, 1490 545 C 1360 640, 1100 630, 980 550 C 870 470, 890 240, 1030 130 Z',
  'M 990 90 C 1140 20, 1430 40, 1560 130 C 1690 240, 1680 480, 1540 570 C 1390 680, 1080 670, 940 580 C 810 490, 830 220, 990 90 Z',
  'M 950 50 C 1120 -30, 1460 -10, 1610 90 C 1760 215, 1750 495, 1590 595 C 1420 720, 1060 710, 900 610 C 750 510, 770 200, 950 50 Z',
  'M 910 10 C 1100 -80, 1490 -60, 1660 50 C 1830 190, 1820 510, 1640 620 C 1450 760, 1040 750, 860 640 C 690 530, 710 180, 910 10 Z',
  'M 870 -30 C 1080 -130, 1520 -110, 1710 10 C 1900 165, 1890 525, 1690 645 C 1480 800, 1020 790, 820 670 C 630 550, 650 160, 870 -30 Z',
];

export interface ContourBackgroundProps {
  className?: string;
  opacity?: number;
  strokeWidth?: number;
}

export function ContourBackground({
  className,
  opacity = 0.1,
  strokeWidth = 1,
}: ContourBackgroundProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const [isVisible, setIsVisible] = useState(true);
  const [isTabVisible, setIsTabVisible] = useState(true);

  // Pauses when tab is hidden
  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsTabVisible(document.visibilityState === 'visible');
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  // Pauses when off screen using IntersectionObserver
  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof IntersectionObserver === 'undefined') return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0 }
    );

    observer.observe(el);
    return () => {
      observer.disconnect();
    };
  }, []);

  const shouldAnimate = !reduce && !calm && isVisible && isTabVisible;

  return (
    <div
      ref={containerRef}
      className={cn(
        'pointer-events-none absolute inset-0 overflow-hidden select-none',
        className
      )}
      aria-hidden="true"
    >
      <div
        className="w-[200%] h-[200%] -top-1/4 -left-1/4 absolute"
        style={{
          animation: shouldAnimate ? 'drift 40s linear infinite' : 'none',
          willChange: shouldAnimate ? 'transform' : 'auto',
        }}
      >
        <svg
          viewBox="0 0 2400 1400"
          className="w-full h-full"
          fill="none"
          preserveAspectRatio="xMidYMid slice"
        >
          {CONTOUR_PATHS.map((pathD, idx) => (
            <path
              key={idx}
              d={pathD}
              stroke="var(--text-muted)"
              strokeWidth={strokeWidth}
              strokeOpacity={opacity}
              fill="none"
            />
          ))}
        </svg>
      </div>
    </div>
  );
}

export default ContourBackground;
