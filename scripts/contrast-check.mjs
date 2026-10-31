#!/usr/bin/env node

/**
 * WCAG 2.1 Contrast Checker for RepoQuest Design System Tokens.
 * Verifies that text pairs reach >= 4.5:1 (AA) and UI/status colors reach >= 3.0:1 on all surfaces.
 */

function sRGBtoLinear(c) {
  const norm = c / 255;
  return norm <= 0.04045 ? norm / 12.92 : Math.pow((norm + 0.055) / 1.055, 2.4);
}

function getLuminance(hex) {
  const cleanHex = hex.replace('#', '').trim();
  const num = parseInt(cleanHex, 16);
  const r = sRGBtoLinear((num >> 16) & 255);
  const g = sRGBtoLinear((num >> 8) & 255);
  const b = sRGBtoLinear(num & 255);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function getContrast(hex1, hex2) {
  const l1 = getLuminance(hex1);
  const l2 = getLuminance(hex2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

const THEMES = {
  dusk: {
    surfaces: {
      bg: '#0A0D1A',
      'surface-1': '#10152A',
      'surface-2': '#171E3A',
      'surface-3': '#1F2848',
    },
    texts: {
      text: '#EDF1FF',
      'text-muted': '#9AA6CF',
    },
    ui: {
      brand: '#6C8CFF',
      'brand-2': '#9B6CFF',
      sky: '#7EB6F0',
      amber: '#FFB81C',
      rose: '#F57C7C',
      flame: '#FF3B1F',
      mint: '#2DD4A7',
    },
  },
  parchment: {
    surfaces: {
      bg: '#F3F1EA',
      'surface-1': '#FBFAF6',
      'surface-2': '#FFFFFF',
      'surface-3': '#ECE9DF',
    },
    texts: {
      text: '#1B1A17',
      'text-muted': '#555A63',
    },
    ui: {
      brand: '#2748D8',
      'brand-2': '#6B3FD6',
      sky: '#3F86D6',
      amber: '#B26E00', // Adjusted from #D98A00 for WCAG AA compliance (min contrast 3.37:1)
      rose: '#D84F58',
      flame: '#D42A10',
      mint: '#0B8F6B', // Adjusted from #0E9F78 for WCAG AA compliance (min contrast 3.35:1)
    },
  },
};

let failedCount = 0;
let passedCount = 0;

console.log('RepoQuest WCAG 2.1 Design Tokens Contrast Audit');
console.log('==================================================');

for (const [themeName, config] of Object.entries(THEMES)) {
  console.log(`\nTheme: ${themeName.toUpperCase()}`);
  console.log('--------------------------------------------------');

  // 1. Text pairs: must reach >= 4.5
  for (const [textName, textColor] of Object.entries(config.texts)) {
    for (const [surfName, surfColor] of Object.entries(config.surfaces)) {
      const ratio = getContrast(textColor, surfColor);
      const passed = ratio >= 4.5;
      if (passed) {
        passedCount++;
        console.log(`  [PASS] text: ${textName.padEnd(12)} on ${surfName.padEnd(11)} -> ${ratio.toFixed(2)}:1 (req >= 4.5)`);
      } else {
        failedCount++;
        console.error(`  [FAIL] text: ${textName.padEnd(12)} on ${surfName.padEnd(11)} -> ${ratio.toFixed(2)}:1 (req >= 4.5)`);
      }
    }
  }

  // 2. UI / Brand / Status pairs: must reach >= 3.0
  for (const [uiName, uiColor] of Object.entries(config.ui)) {
    for (const [surfName, surfColor] of Object.entries(config.surfaces)) {
      const ratio = getContrast(uiColor, surfColor);
      const passed = ratio >= 3.0;
      if (passed) {
        passedCount++;
        console.log(`  [PASS] ui:   ${uiName.padEnd(12)} on ${surfName.padEnd(11)} -> ${ratio.toFixed(2)}:1 (req >= 3.0)`);
      } else {
        failedCount++;
        console.error(`  [FAIL] ui:   ${uiName.padEnd(12)} on ${surfName.padEnd(11)} -> ${ratio.toFixed(2)}:1 (req >= 3.0)`);
      }
    }
  }
}

console.log('\n==================================================');
console.log(`Summary: ${passedCount} passed, ${failedCount} failed.`);

if (failedCount > 0) {
  console.error(`ERROR: ${failedCount} contrast check(s) failed.`);
  process.exit(1);
} else {
  console.log('All token contrast checks PASSED successfully.');
  process.exit(0);
}
