# RepoQuest Design PRD: Pixel Cartography

**Companion to:** the RepoQuest Product Requirements Document. This document replaces the visual and motion parts of its §13.3. Routes, components, behaviors and APIs stay exactly as specified there.

**Event:** Devf8rge × Hacktoberfest 2026, Bengaluru · Theme 01: AI for Open Source · **Build target:** Google Antigravity

**Design goal:** an interface that judges remember in the first 10 seconds and trust in the next 5 minutes: premium and precise like a top developer tool, with a pixel-art map-and-quest personality that makes newcomers want to explore.

---

## 0. How to Use This Document (Instructions for the Antigravity Agent)

1. Build the **design tokens first** (§4 to §6, §15.2), then the motion presets (§7, §15.3), then the shared components (§10), then the screens (§11).
2. Never hardcode colors, sizes, durations or easings. Always use the tokens defined here.
3. Every animation listed with priority **P0** must ship. **P1** ships if time allows. **P2** is stretch. Never start P1 or P2 motion before every P0 motion works and passes §13 (accessibility) and §14 (performance).
4. Every animation must respect `prefers-reduced-motion` and the in-app **Calm mode** switch (§7.4).
5. Approved additions to the frontend stack: `framer-motion`, `canvas-confetti`, and fonts through `next/font/google` (self-hosted at build time so the app works fully offline). No other UI or animation libraries.
6. Build a hidden `/design` page (kitchen sink) that shows every token, component and state. It is the fastest way to check consistency before the demo.

---

## 1. Design Vision

**RepoQuest should feel like unrolling a living map of a codebase: as precise and calm as a premium developer tool, with just enough play to make a first-time contributor feel like an explorer instead of a beginner.**

**One-line design pitch for judges:** *Linear’s precision meets a cartographer’s map table, with a pixel companion called Pip who makes open source feel like a quest.*

### 1.1 Design Principles

| # | Principle | What it means in practice |
| --- | --- | --- |
| 1 | **Clarity before charm** | Every playful element sits on top of a clear, readable, fast interface. Maintainer screens stay calm; newcomer screens get the most personality. |
| 2 | **Motion with meaning** | Animation explains something: what is loading, what changed, what is connected, what succeeded. No decoration without a job. |
| 3 | **Trust is visible** | The local-first promise is always on screen (privacy badge, audit trail, offline proof) and has its own signature animation. |
| 4 | **One hero per screen** | Each screen has exactly one memorable moment. Everything else is quiet so that moment lands. |
| 5 | **Accessible by default** | Contrast, keyboard use, screen readers and reduced motion are design requirements, not polish. |

### 1.2 Audience Tone Map

| Surface | Personality dial | Why |
| --- | --- | --- |
| Landing, Setup, Day-1 Tour, Launchpad, Ask | **High play** (Pip, quest language, XP, celebrations) | Newcomers need encouragement |
| Issues, PRs, Spam Shield, Health, Audit | **Low play** (precise, dense, calm, subtle motion only) | Maintainers need speed and trust |
| Model Lab | **Medium play** (race visualization) | Memorable demo moment backed by real data |

---

## 2. Brand Identity

### 2.1 Name, Tagline and Voice

- **Name meaning:** every repository is a realm to explore, every contribution is a quest.
- **Tagline:** *Help maintainers keep up. Help newcomers get started.*
- **Voice:** warm, direct, confident, never childish. Short sentences. Verbs first. Humor is allowed in empty states and celebrations only, never in errors that block work.

| Moment | Microcopy |
| --- | --- |
| Landing input placeholder | Paste a GitHub repo URL to start your quest |
| Indexing start | Pip is charting the map. This stays on your machine. |
| Indexing done | Map ready: 214 files, 1,386 chunks. |
| Empty triage inbox | Inbox zero. Even the bots are impressed. |
| Quest complete | Quest complete. +50 XP |
| Ollama not found | Pip cannot find the local model. Let’s fix that together. |
| Error with retry | Something went wrong on our side. Your data is safe. Try again. |
| Spam flagged | Looks low-effort. Here is why, and a polite reply you can send. |

### 2.2 Logo

- **Icon:** a rounded-square badge containing a pixel compass rose built on an 8 by 8 grid; the north point is Amber, the other points Sky, the center square Rose.
- **Wordmark:** “RepoQuest” in Bricolage Grotesque ExtraBold, tight tracking, with the **Signature Strip** (four square pixels in Sky, Amber, Rose and Flame) as the dot after the wordmark and as a recurring divider across the product.
- **Variants:** full color on dark, full color on cream, single color (ink or white), and an icon-only favicon.

### 2.3 Mascot: Pip, the Pixel Cartographer

Pip is a small pixel robot with an amber antenna (a nod to the theme slide). Pip appears in indexing, empty states, errors, onboarding and celebrations, and never blocks work. Pip is drawn as SVG rectangles on a 14 by 12 grid with `shape-rendering: crispEdges` so it stays razor sharp at any size.

**Pixel map (use exactly):** `.` empty, `B` body (Sky), `W` eye white, `K` ink, `A` amber.

```text
......AA......
......KK......
..BBBBBBBBBB..
.BBBBBBBBBBBB.
BBBWWBBBBWWBBB
BBBWKBBBBKWBBB
BBBWWBBBBWWBBB
BBBBBBBBBBBBBB
.BKKKKKKKKKKB.
.BKAKAKAKAKKB.
..BBBBBBBBBB..
...BB....BB...
```

| Pip state | Where it appears | Behavior (details in §9) |
| --- | --- | --- |
| Idle | Landing, empty states | Blinks every 4 s, antenna bobs gently |
| Thinking | Ask the Repo, triage running | Eyes scan left and right, antenna tip pulses |
| Exploring | Indexing | Walks with a lantern, lights the path |
| Success | Task done, quest complete | Jumps, antenna spark, pixel confetti |
| Error | Failures | Antenna droops, eyes become small crosses, one gentle wobble |
| Sleeping | Backend or Ollama offline | Eyes closed, floating pixel Zs |

### 2.4 Where We Use Quest Language (and Where We Do Not)

Quest words appear only where they add warmth and never rename core developer concepts.

| Area | Plain term stays | Quest flavor allowed |
| --- | --- | --- |
| Issues and PRs | Issue, Pull request, Label, Review | None in labels or buttons; flavor only in empty and success messages |
| Newcomer tools | Good first issue | **Starter Quest** (card title), **First Quest** (Day-1 Tour), XP, badges, streaks |
| Navigation | Explore, Ask, Issues, PRs | None |

---

## 3. Design Language: Pixel Cartography

Five recurring motifs make RepoQuest instantly recognizable.

1. **Contour lines:** thin, low-contrast topographic lines as the background of hero areas and empty states. They drift very slowly (§8).
2. **Pixel grid:** a faint 8 px dot grid behind canvases; pixel-art icons, badges and Pip; hover states that reveal the grid.
3. **Notched cards (“Quest Cards”):** cards with two diagonal-cut corners (top-left and bottom-right, 10 px) used for the main object on each screen. Normal cards use plain rounded corners so the notch stays special.
4. **Signature Strip:** the four-pixel color strip (Sky, Amber, Rose, Flame) used as divider, loader and progress cap.
5. **Compass motion:** needles, gauges and map markers always rotate or settle with a small overshoot, like a real instrument.

**Two themes, one identity**

| Theme | Name | Feel |
| --- | --- | --- |
| Dark (default) | **Dusk** | Premium night-map: deep ink background, glass panels, glowing accents, aurora gradient on key moments |
| Light | **Parchment** | Warm cream paper with thick ink borders and hard offset shadows, directly echoing the Devf8rge theme slide style |

---

## 4. Color System

### 4.1 Core Palette

| Token | Dusk (dark) | Parchment (light) | Use |
| --- | --- | --- | --- |
| `--bg` | `#0A0D1A` | `#F3F1EA` | App background |
| `--surface-1` | `#10152A` | `#FBFAF6` | Cards, sidebar |
| `--surface-2` | `#171E3A` | `#FFFFFF` | Raised cards, popovers |
| `--surface-3` | `#1F2848` | `#ECE9DF` | Hover, inputs |
| `--border` | `#2A3560` | `#1B1A17` | Lines and outlines |
| `--text` | `#EDF1FF` | `#1B1A17` | Primary text |
| `--text-muted` | `#9AA6CF` | `#555A63` | Secondary text |
| `--brand` | `#6C8CFF` | `#2748D8` | Primary actions, links, focus |
| `--brand-2` | `#9B6CFF` | `#6B3FD6` | Gradient partner, AI moments |
| `--sky` | `#7EB6F0` | `#3F86D6` | Info, Pip body, P2 severity |
| `--amber` | `#FFB81C` | `#D98A00` | XP, highlights, P1 severity |
| `--rose` | `#F57C7C` | `#D84F58` | Warm accent, warnings |
| `--flame` | `#FF3B1F` | `#D42A10` | Danger, P0 severity |
| `--mint` | `#2DD4A7` | `#0E9F78` | Success, local-privacy badge |

All text and interactive colors must reach WCAG AA contrast (4.5:1 for body text, 3:1 for large text and UI outlines). Verify every pair with a contrast checker; adjust the lightness of a token, never ship a failing pair.

### 4.2 Gradients and Effects

| Name | Definition | Use |
| --- | --- | --- |
| **Aurora** | `linear-gradient(120deg, var(--brand) 0%, var(--brand-2) 45%, var(--rose) 100%)` | Hero headline highlight, primary CTA, celebration moments |
| **Summit glow** | `radial-gradient(circle at 50% 0%, rgba(255,184,28,0.18), transparent 60%)` | Behind the hero and the Day-1 Tour start |
| **Glass** | Dusk: background `rgba(23,30,58,0.6)`, `backdrop-filter: blur(14px) saturate(140%)`, 1 px border `rgba(255,255,255,0.08)` | Sticky top bar, drawers, popovers |
| **Grid dots** | `radial-gradient(circle, var(--border) 1px, transparent 1px)` at 8 px spacing, 40 percent opacity | Canvas backgrounds |

### 4.3 Semantic and Data Colors

| Meaning | Color | Notes |
| --- | --- | --- |
| Severity P0 / P1 / P2 / P3 | Flame / Amber / Sky / Slate `#7C86A8` | Always paired with a text label and an icon, never color alone |
| Risk low / medium / high | Mint / Amber / Flame | Same rule |
| Spam score 0 to 39 / 40 to 69 / 70 to 100 | Mint / Amber / Flame | Gradient bar plus the number |
| Local privacy badge | Mint when local, Amber when remote | Matches the product PRD behavior |
| Chart series (in order) | Sky, Amber, Rose, Mint, Violet `#9B6CFF`, Slate | Colorblind-safe check required; add patterns or direct labels where series touch |

---

## 5. Typography

| Role | Font | Weights | Notes |
| --- | --- | --- | --- |
| Display and headings | **Bricolage Grotesque** | 700, 800 | Distinctive, premium; used for hero and section titles |
| Interface and body | **Inter** | 400, 500, 600 | Highest legibility for dense data |
| Code, metadata, numbers | **JetBrains Mono** | 400, 500 | Tabular numbers for metrics and counters |
| Pixel labels | **Silkscreen** | 400 | Only for badges, XP, level names and the “PIXEL” accents; uppercase, never below 12 px, never for sentences |

All fonts load through `next/font/google` so they are self-hosted at build time and need no network at runtime. Provide fallbacks: `system-ui, sans-serif` and `ui-monospace, monospace`.

| Style | Size / line height | Weight and tracking | Use |
| --- | --- | --- | --- |
| Display XL | 72 / 72 px | 800, -2% | Landing headline (desktop) |
| Display L | 48 / 52 px | 800, -1.5% | Section heroes |
| H1 | 32 / 40 px | 700, -1% | Page titles |
| H2 | 24 / 32 px | 700 | Section titles |
| H3 | 18 / 28 px | 600 (Inter) | Card titles |
| Body | 15 / 24 px | 400 | Default text (14 px in dense tables) |
| Small | 13 / 20 px | 400 or 500 | Metadata |
| Code | 13 / 20 px | 400 (JetBrains Mono) | Code, diffs, file paths |
| Pixel label | 12 / 16 px | 400, +8% caps | Badges, XP |

On screens narrower than 640 px, scale Display XL to 40 px and Display L to 32 px.

---

## 6. Spacing, Shape, Elevation, Icons and Imagery

- **Spacing scale (4 px base):** 4, 8, 12, 16, 24, 32, 48, 64, 96. Page gutters 24 px (desktop), 16 px (mobile). Card padding 20 px (dense: 16 px).
- **Radius:** sm 6, md 10, lg 16, xl 24, pill 999. Quest Card notch: 10 px, built with `clip-path`.
- **Elevation in Dusk:** no heavy shadows. Use a 1 px border, a subtle inner top highlight (`inset 0 1px 0 rgba(255,255,255,0.05)`) and a soft brand-tinted glow only on the focused or active object.
- **Elevation in Parchment:** 2 px ink border and a hard offset shadow `4px 4px 0 var(--border)`; pressed state moves the card by 2 px and shrinks the shadow to 2 px.
- **Icons:** Lucide at 1.75 px stroke, 20 px default. Plus a custom **pixel icon set** (16 by 16 grid, SVG sprite) for compass, flag, shield, scroll, lantern, key, spark, crown and lock; used on badges, empty states and celebrations.
- **Illustration style:** pixel-art maps and landscapes built from SVG rectangles and CSS, never raster images, so everything stays sharp, tiny and offline. Landscapes use Sky, Amber and Rose on Dusk and ink-outlined blocks on Parchment.
- **Imagery rule:** no stock photos. Real product UI, pixel art and data visualizations only.

---

## 7. Motion System

**Motion in RepoQuest explains the product: it shows what is loading, what is connected, what changed and what succeeded.** Animation is built with `framer-motion` plus plain CSS keyframes for ambient loops.

### 7.1 Principles

1. **Purposeful:** every animation answers a question (what is happening, where did that go, is it done).
2. **Fast:** UI feedback 90 to 240 ms, screen choreographies up to 900 ms, celebrations up to 1.6 s. Nothing makes the user wait for motion to finish.
3. **Interruptible:** any animation can be cut short by the next user action without glitches.
4. **Physical:** springs with a small overshoot for objects (cards, gauges, needles), eased curves for fades and slides.
5. **Quiet by default:** maintainer screens use subtle motion; the big moments are reserved for landing, indexing, the Day-1 Tour and the Model Lab.

### 7.2 Motion Tokens

| Token | Value | Use |
| --- | --- | --- |
| `--dur-instant` | 90 ms | Hover color, press |
| `--dur-fast` | 150 ms | Tooltips, chips, toggles |
| `--dur-base` | 240 ms | Cards, tabs, drawers |
| `--dur-slow` | 400 ms | Panel reveals, graph edges |
| `--dur-epic` | 800 ms | Hero entrances, stamps |
| `--ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` | Entrances (default) |
| `--ease-in-out` | `cubic-bezier(0.65, 0, 0.35, 1)` | Moves between positions |
| `--ease-in` | `cubic-bezier(0.7, 0, 0.84, 0)` | Exits |
| Spring **snappy** | stiffness 260, damping 24 | Buttons, chips, list items |
| Spring **gentle** | stiffness 140, damping 20 | Cards, drawers, layout changes |
| Spring **bouncy** | stiffness 380, damping 16 | Stamps, badges, Pip jumps, gauge needles |
| Stagger | 40 ms per item, max 12 items | Lists and grids (beyond 12, animate in groups) |

### 7.3 Technical Rules

- Animate only `transform`, `opacity`, `filter` (small blur values), `clip-path`, and SVG `stroke-dashoffset`. Never animate `width`, `height`, `top` or `left`.
- Use `layout` and `layoutId` from Framer Motion for tab underlines, list reordering and shared element transitions.
- At most **3 attention-grabbing animations** at the same time on screen. Ambient loops must be low contrast.
- Ambient loops pause when the tab is hidden (`document.visibilityState`) or the element is off screen (`useInView`).
- Exit animations are shorter than entrances (about 60 percent of the duration).
- Heavy visuals (contour background, particles) are lazy loaded and capped at 60 fps with a graceful fallback to a static version.

### 7.4 Reduced Motion and Calm Mode

Wrap the app in `<MotionConfig reducedMotion='user'>` and also read a persisted **Calm mode** setting (Settings page and a toggle in the top bar menu). Calm mode applies everything below even when the OS setting is off.

| Normal motion | Reduced or Calm replacement |
| --- | --- |
| Parallax, drifting contour lines | Static contour image |
| Staggered entrances, slides | Simple 120 ms fade |
| Confetti, particles, sparks | None; show the end state (badge, check mark) |
| Pip animations | Static pose for the state |
| Streaming word fade-in | Text appears immediately |
| Gauge needle spring, count-up numbers | Final value shown instantly |

Safety: no element flashes more than 3 times per second and no large area flickers.

---

## 8. Signature Animations

### 8.1 Animation Inventory

| ID | Where | Animation | Trigger | Timing | Priority |
| --- | --- | --- | --- | --- | --- |
| A1 | Landing | **Map Unfurl:** contour lines fade in and drift, headline words rise in sequence, Aurora sweeps across the second line | Page load | 800 ms intro, drift 40 s loop | P0 |
| A2 | Landing | Pixel quest map assembles tile by tile; Pip walks in and plants a flag on the summit | After A1 | 1.2 s | P0 |
| A3 | Landing | URL field **scan beam:** a light line sweeps the border once on focus | Input focus | 600 ms | P0 |
| A4 | Landing | CTA shimmer: a diagonal highlight passes over the button every 6 s; button lifts 2 px on hover | Idle, hover | 900 ms | P1 |
| A5 | Landing | Pip eyes follow the cursor within a 4 px range | Pointer move | Real time | P1 |
| A6 | Setup | Status dots turn from pulsing red to green with a small ripple | Check result | 300 ms | P0 |
| A7 | Indexing | **Fog of War:** the map starts covered by dark tiles that dissolve as files are indexed; Pip walks with a lantern along the revealed edge | Progress events | Continuous | P0 |
| A8 | Indexing | Stage stepper: the active stage glows, the finished stage plays a check draw; counters use a rolling odometer | Stage change | 300 ms | P0 |
| A9 | Privacy badge | Lock closes with a click and a mint ripple; on switching to a remote model it opens and turns amber | Provider change | 400 ms | P0 |
| A10 | Explore | **Living Map:** nodes pop in with a stagger spring, edges draw themselves along their paths | Graph load | 1.0 s total | P0 |
| A11 | Explore | Hover a node: it glows, neighbors and edges stay bright, everything else dims to 35 percent | Hover | 150 ms | P0 |
| A12 | Explore | **Start Here trail:** a dotted glowing path with a moving pixel travels through the recommended first modules | Button click | 1.5 s | P1 |
| A13 | Ask | Streaming answer: each word fades up 4 px; citation chips fly from the text into the Sources panel | Token events | 120 ms per word | P0 |
| A14 | Ask | Thinking state: Pip with a magnifier and a shimmer skeleton for the first tokens | Request start | Loop until first token | P0 |
| A15 | Triage | New issue slides into the list from the top with a soft highlight that fades after 2 s | New item | 300 ms | P0 |
| A16 | Triage | **Analysis reveal:** type, severity, labels, duplicates (similarity bars fill), reply draft appear in sequence | Analysis done | 700 ms total | P0 |
| A17 | Triage | **Approve Stamp:** a pixel stamp reading APPROVED slams onto the card with a squash, then the card collapses out of the list | Approve click | 600 ms | P0 |
| A18 | PR Review | Diff scan line moves down the file while the review streams; each inline comment marker pulses once when it appears | Streaming | Continuous, 500 ms pulse | P0 |
| A19 | PR Review | Risk meter needle swings with overshoot; the verdict stamp lands | Review done | 700 ms | P1 |
| A20 | Spam Shield | **Radar sweep** passes over the list; flagged PRs get a cracked-shield badge and slide to the top | Scan | 1.2 s | P1 |
| A21 | Day-1 Tour | Winding quest path draws itself; completing a step plants a flag, fills the XP bar and bursts pixel confetti | Step complete | 900 ms | P0 |
| A22 | Day-1 Tour | **Badge unlock:** badge flips in with a 3D tilt and a one-time shine sweep | Path complete | 1.2 s | P1 |
| A23 | Launchpad | Forge sparks fly from the vague issue as the brief assembles line by line; match meter fills | Forge click | 1.0 s | P1 |
| A24 | Model Lab | **Model Race:** horizontal bars race like a leaderboard while the benchmark runs, ranks swap with layout animation, the winner gets a crown pop | Benchmark progress | Real time | P0 |
| A25 | Health | Load gauge needle springs to the value; sparklines draw left to right; the digest types in | Page load, generate | 900 ms | P1 |
| A26 | Global | Page transitions: 200 ms crossfade plus 8 px rise; shared layout for tabs | Navigation | 200 ms | P0 |
| A27 | Global | Toasts slide in with a spring; undo toasts show a draining progress line | Action | 240 ms | P0 |
| A28 | Global | Command palette (Ctrl or Cmd + K) scales in from 96 percent with a blur backdrop | Shortcut | 240 ms | P1 |
| A29 | Global | Skeleton shimmer on every loading block | Loading | 1.4 s loop | P0 |
| A30 | Global | Pip easter egg: Konami code makes Pip dance for 3 seconds | Key sequence | 3 s | P2 |

### 8.2 The Six Signature Moments (choreography)

These are the moments judges will remember. Build and polish them before anything else in §8.1 marked P1 or P2.

**M1. Map Unfurl (landing, A1 to A3)**

1. 0 ms: background fades from `--bg` to the Summit glow; contour lines fade in at 0 to 12 percent opacity.
2. 150 ms: headline words rise 16 px and fade in, 60 ms apart; the second line receives the Aurora gradient, which sweeps left to right over 800 ms.
3. 500 ms: URL field and buttons rise with the snappy spring; status dots fade in.
4. 700 ms: the quest map tiles appear in a diagonal wave (each tile 24 ms apart); Pip walks in from the left in pixel steps and plants the amber flag on the summit with a small bounce.
5. Idle: contours drift slowly, Pip blinks, the flag waves in 2 frames.

**M2. Fog of War Indexing (A7, A8)**

1. The map canvas shows a dark tile grid covering the realm silhouette (the repo’s folders become regions).
2. For every batch of indexed files, tiles in the matching region dissolve (opacity to 0, 300 ms, staggered by 10 ms) and reveal pixel terrain tinted by the region’s language color.
3. Pip walks along the reveal boundary carrying a lantern; the glow radius pulses with the embedding speed.
4. The stepper below ticks through Fetch, Chunk, Embed, Summarize; the counters roll like an odometer.
5. At 100 percent: the remaining fog clears in one wave, Pip jumps, the Signature Strip fills, a mint check draws and the screen offers Explore and Ask buttons.

**M3. Living Map (Explore, A10 to A12)**

1. Nodes spring in from 80 percent scale, 40 ms apart, ordered by distance from the entry point.
2. Edges draw with `stroke-dashoffset` over 400 ms after their two nodes appear.
3. On hover, the focused node glows with the brand color; connected nodes and edges stay at full brightness, others drop to 35 percent.
4. Clicking Start Here sends a glowing pixel along a dotted trail through the recommended modules and opens the first one in the drawer.

**M4. Approve Stamp (Triage, A16, A17)**

1. Analysis sections reveal top to bottom, 100 ms apart; similarity bars fill from 0 to their values over 500 ms.
2. On Approve, the card compresses slightly, a pixel stamp (APPROVED, Mint, rotated -8 degrees) drops from 140 percent to 100 percent scale with the bouncy spring and a 4 px screen nudge.
3. After 500 ms the card collapses (height via layout animation) and the list closes the gap; an undo toast with a draining line appears.

**M5. Model Race (Model Lab, A24)**

1. Each selected model gets a lane with its name, size and a bar.
2. The bar length follows live progress (samples completed); lanes reorder by accuracy so far using layout animation.
3. A small speedometer per lane shows tokens per second with a spring needle.
4. When all finish, the best lane gets a crown that pops in with the bouncy spring and a short Aurora outline pulse; a summary sentence fades in (Gemma was 12 percent more accurate; Llama was 1.8 times faster). The numbers come from real results only.

**M6. Quest Complete (Day-1 Tour, A21, A22)**

1. Quiz answers give instant feedback: correct choices pulse mint and the card tilts 1 degree; wrong choices shake once (3 cycles, 4 px) and reveal the explanation.
2. On Mark complete: a flag plants on the path checkpoint, the XP bar fills with an overshoot, and `canvas-confetti` fires a short burst using pixel-square shapes in the four signature colors (disabled under reduced motion).
3. At the final step: the badge card flips in with a 3D tilt and a one-time shine; Pip celebrates; a summary shows XP earned and the next Starter Quest.

---

## 9. Pip Behavior Specification

Pip is a React component with a `state` prop (`idle`, `thinking`, `exploring`, `success`, `error`, `sleeping`) and a `size` prop. The body is the SVG pixel map from §2.3; animation is applied per group (antenna, eyes, body, legs, accessories).

| State | Animation details |
| --- | --- |
| Idle | Blink: eyes scale Y to 0.1 for 120 ms at random intervals of 3.5 to 5.5 s. Antenna rotates ±6 degrees over 2.4 s. Body breathes 2 px up and down over 3 s using stepped easing (`steps(2)`) to keep the pixel feel. |
| Thinking | Pupils move one grid cell left and right every 500 ms (stepped). Antenna tip alternates Amber and white every 600 ms. A small three-dot indicator appears above the head. |
| Exploring | Legs alternate every 200 ms (two-frame walk). Body bounces 1 px per step. A lantern accessory glows; glow radius pulses between 14 and 20 px. |
| Success | Crouch (80 ms), jump 12 px with the bouncy spring, six amber pixels burst outward for 600 ms, antenna spark. Returns to Idle. |
| Error | Antenna rotates 35 degrees (droop). Pupils swap to small crosses. One horizontal shake of ±3 px, 3 cycles in 360 ms, played once. Holds the pose. |
| Sleeping | Eyes become horizontal lines. Three pixel Zs float up and fade over 2.4 s, staggered. Breathing slows to 4 s. |

Interactions: eyes follow the cursor on the landing page (P1); clicking Pip makes a small hop and shows a one-line tip (P2). Pip never covers content, never blocks a click and is hidden when Calm mode is on only if it is purely decorative (status Pips in errors and empty states stay as static poses).

---

## 10. Component Specifications

| Component | Visual spec | States and motion |
| --- | --- | --- |
| **Button primary** | Aurora gradient fill, white text, 10 px radius, 40 px height (44 px on touch) | Hover lifts 2 px and brightens; press scales to 0.97; loading shows the Signature Strip loader; shimmer every 6 s (P1) |
| **Button secondary / ghost** | Surface-2 fill with border, or transparent with text color | Hover surface-3; focus ring 2 px `--brand` with 2 px offset |
| **Button danger** | Flame fill | Confirmation dialog for destructive actions |
| **URL input (hero)** | Large 56 px field, glass fill, pixel-grid left icon | Scan beam on focus (A3); invalid state shakes once and shows a Rose message |
| **Card** | Surface-1, 16 px radius, 1 px border | Hover raises border brightness; list entrance uses fade and rise |
| **Quest Card** | Card with 10 px notched corners, a Signature Strip on the top edge, optional Summit glow | Used for the main object per screen; subtle corner pulse on new data |
| **Chips and pills** | `StatusChip`, `SeverityPill` (color, icon and label), `CitationChip` (mono, file and lines) | Citation chip flies to the Sources panel; status chip cross-fades on change |
| **PrivacyBadge** | Mint pill with pixel lock icon and the text 100% local | Lock animation A9; popover with model and URL appears with the gentle spring |
| **Sidebar** | 248 px, three groups with pixel icons, active item has a brand bar and soft glow | Active indicator slides with `layoutId`; collapses to 64 px icons below 1024 px |
| **Top bar** | Glass, sticky, 56 px; repo switcher, language, privacy badge, theme and Calm toggles | Hides on scroll down and returns on scroll up (200 ms) |
| **Tabs** | Text tabs with a sliding underline | Underline moves with a shared layout spring |
| **Dialog and Drawer** | Glass panel over a blurred, darkened backdrop | Dialog scales from 96 percent; drawer slides 24 px with the gentle spring; focus is trapped |
| **Toast** | Surface-2, left color bar by type | Slide in with spring; undo toast has a draining line; stack of 3 max |
| **Command palette** | Centered 560 px glass panel | Scale-in; results stagger 20 ms; arrow-key highlight slides |
| **Skeleton** | Surface-3 blocks with a diagonal shimmer | 1.4 s loop; replaced by content with a 150 ms cross-fade |
| **Progress** | Signature Strip loader: four pixels fill left to right in Sky, Amber, Rose, Flame | Indeterminate version cycles the pixels in sequence |
| **CodeViewer and DiffView** | JetBrains Mono 13 px, line numbers, theme-aware syntax colors (Dusk uses Sky, Amber, Rose, Mint on ink) | Jump-to-line scrolls and flashes the range with an Amber highlight that fades over 1.2 s |
| **ModuleGraph node** | 160 by 64 px rounded node, language color dot, file count in mono | Entrance and hover per M3; selected node gets an Aurora outline |
| **ChatStream** | User bubbles in surface-3, answers on the page without bubbles for readability; Sources panel on the right | Word fade-in; Stop button morphs from the Send button |
| **QuizCard** | Option rows with a pixel radio; explanation expands below | Feedback per M6; focus order follows options |
| **MetricCard and Sparkline** | Large mono number, small label, delta chip | Number counts up over 600 ms; sparkline draws in 700 ms |
| **LoadGauge** | Semicircle gauge with three color zones (Mint, Amber, Flame) and a compass needle | Needle spring (bouncy); tooltip shows the formula |
| **XPBar and BadgeCard** | Pixel-bordered bar with a Silkscreen level label; badge cards as small notched cards with a pixel icon | XP fill with overshoot; badge unlock per M6 |
| **ModelBenchmarkChart** | Racing lanes while running, grouped bars when done (accuracy, JSON validity, latency) | Layout-animated reordering; bars grow from zero over 500 ms |

---

## 11. Screen Designs

Each screen keeps the layout rules of the product PRD (§13) and adds the visual composition and hero moment below.

### 11.1 Landing and Connect (`/`) — hero moment: M1

```text
+----------------------------------------------------------------------+
| [RepoQuest ::::]                Docs   Demo   GitHub     [lock 100% local] |
|                                                                      |
|   ... contour lines drifting ...                                     |
|                                                                      |
|   Help maintainers keep up.                     +-----------------+  |
|   Help newcomers get started.  (Aurora)         |   Quest map     |  |
|                                                 |  pixel realm,   |  |
|   +-------------------------------+ [Start]     |  Pip + flag     |  |
|   | Paste a GitHub repo URL ...   | [Demo Mode] +-----------------+  |
|   +-------------------------------+                                  |
|   o Backend   o Database   o Ollama                                  |
|                                                                      |
|   :::: Maintainer Autopilot  |  Local-First AI  |  Newcomer Launchpad |
+----------------------------------------------------------------------+
```

The three pillars at the bottom are Quest Cards that tilt 2 degrees toward the cursor on hover (P1). The Try Demo Mode button has an outlined style with a pixel play icon so it is clearly the safe, instant path.

### 11.2 Setup Wizard (`/setup`)

Three steps (Install Ollama, Pull models, Test connection) as a vertical checklist with copy buttons for each command. Pip in Sleeping state changes to Idle when the connection test passes (A6).

### 11.3 Repository Overview (`/repos/[id]`)

Top: repo name, stars, language bar (colored segments animate to their widths), the Signature Strip. Middle: three Quest Cards for the pillars (Maintainer Autopilot, Local-First AI, Newcomer Launchpad) with live counts. Bottom: health summary and recent audit entries.

### 11.4 Indexing View — hero moment: M2

Full-width map canvas (about 60 percent of the viewport height) with the Fog of War, the stage stepper beneath, and a small log drawer that streams file names in mono.

### 11.5 Explore (`/repos/[id]/explore`) — hero moment: M3

Full-height graph on the grid-dot background, search and minimap in the corners, right drawer for the module. A Start Here button sits top left. A list view toggle provides the accessible alternative.

### 11.6 Ask (`/repos/[id]/ask`)

Two columns: conversation (left, 60 percent) and Sources (right, 40 percent). Starter questions appear as pill chips under Pip in Idle state; after the first message Pip moves to the corner and only shows when thinking.

### 11.7 Triage Inbox (`/repos/[id]/issues`) — hero moment: M4

```text
+---------+-----------------------------------------------------------+
| Sidebar | Filters: [All] [Untriaged] [Suggested] ...      [search]  |
|         +----------------+------------------------------------------+
|         | #482 P1  *     | #482 Crash on empty config     [Re-run]  |
|         | #481 P2  *     | issue body ...                           |
|         | #480 dup [=]   | +-- AI Analysis (Quest Card) -----------+|
|         | ...            | | Type bug   Severity P1   Labels ...   ||
|         |                | | Duplicates #310 [#######-] 0.91       ||
|         |                | | Reply draft (editable)  Confidence .84||
|         |                | | [Approve and post] [Copy] [Edit] [Reject]|
+---------+----------------+------------------------------------------+
```

List rows are dense (48 px) with severity pills and a duplicate icon. Calm visuals: only A15, A16, A17 animate here.

### 11.8 PR Review (`/repos/[id]/prs/[number]`)

Header with risk meter and verdict stamp; tabs below. The diff uses Dusk ink backgrounds with soft red and green line tints; inline comment markers are small Amber pixel flags that expand into comment cards.

### 11.9 Spam Shield (`/repos/[id]/spam`)

Table-style board sorted by score. Each row shows a gradient score bar, a cracked-shield icon above 70, the top three reasons as chips, and a Copy polite reply button. The radar sweep (A20) plays when a scan starts.

### 11.10 Day-1 Tour (`/repos/[id]/onboarding`) — hero moment: M6

A winding pixel trail on the left with numbered checkpoints; the current step card on the right. XP bar and level name (Scout, Ranger, Pathfinder, Cartographer) sit in the header. Language selector next to the title.

### 11.11 Launchpad (`/repos/[id]/launchpad`)

Skill chips on top, ranked Starter Quest cards with a circular match meter, and a Forge drawer (A23) that shows the brief with a Copy as comment button.

### 11.12 Model Lab (`/models`) — hero moment: M5

Installed-model cards on top, benchmark setup in the middle, the Model Race canvas and results table below. A calm Parchment-style summary card states the recommendation.

### 11.13 Health (`/repos/[id]/health`)

Metric cards row, LoadGauge (A25), 8-week sparklines, and the digest panel with a typewriter preview and Copy and Download buttons.

### 11.14 Audit and Settings

Audit: dense table with feature, action, model, outcome and an Undo button (the removed row slides out). Settings: grouped cards; the Calm mode switch and theme switch show an instant live preview.

---

## 12. Responsive Behavior

| Breakpoint | Width | Layout changes |
| --- | --- | --- |
| `sm` | 640 px | Single column; display type scales down (§5) |
| `md` | 768 px | Hero quest map appears beside the headline; two-column cards |
| `lg` | 1024 px | Sidebar expands to full width (below this it is a 64 px icon rail) |
| `xl` | 1280 px | Triage and Ask use full split layouts |
| `2xl` | 1536 px | Content max width 1440 px, centered; canvases grow |

- **Mobile (below 768 px):** the sidebar becomes a bottom navigation bar with five items plus a More sheet. Triage and PR lists open the detail as a full-screen sheet with a back button. The graph defaults to the list view with a toggle to the map (pinch to zoom, two-finger pan).
- **Touch:** minimum target size 44 by 44 px; hover effects have tap equivalents; no hover-only information.
- **Motion on small screens:** Pip shrinks to 64 px, particles are capped at 20, parallax is off.
- **Safe areas:** respect device insets for the bottom bar and sticky headers.

---

## 13. Accessibility Requirements

| Area | Requirement |
| --- | --- |
| Contrast | WCAG AA for text and UI components in both themes; severity and risk always carry a text label and an icon |
| Keyboard | Everything reachable and operable by keyboard; visible 2 px focus ring in `--brand`; logical tab order; `Esc` closes dialogs and drawers; Ctrl or Cmd + K opens the palette |
| Screen readers | Semantic landmarks (`nav`, `main`, `aside`); icon buttons have `aria-label`; the streaming answer sits in an `aria-live='polite'` region that updates per sentence, not per word; decorative art uses `aria-hidden='true'`; Pip in an error or empty state has `role='img'` and a label such as Pip is waiting for Ollama |
| Graph | Every graph has a keyboard-navigable list alternative with the same data; node selection is operable with arrow keys and Enter |
| Language | Set the `lang` attribute (`hi`, `kn`, `ta`) on translated explanation blocks so screen readers pronounce them correctly; Indic text uses a font stack with proper script support (Noto Sans Devanagari, Noto Sans Kannada, Noto Sans Tamil, bundled for offline use) |
| Motion | §7.4 in full; Calm mode available everywhere; no flashing content |
| Forms | Visible labels, inline error messages tied with `aria-describedby`, errors never rely on color alone |
| Zoom and text size | Layout works at 200 percent zoom without horizontal scrolling (except code and diff areas, which scroll inside their container) |

---

## 14. Performance Budgets for Design and Motion

| Metric | Target |
| --- | --- |
| Largest contentful paint (landing, production build, localhost) | Under 2.5 s |
| Interaction response (click to visual feedback) | Under 100 ms |
| Animation frame rate on a mid-range laptop | 60 fps; never below 45 fps during signature moments |
| Landing route initial JavaScript | Under 200 KB gzipped, excluding the framework |
| Layout shift | CLS under 0.05 (reserve space for fonts, graph canvas and Pip) |
| Particles | At most 60 on desktop and 20 on mobile; confetti lasts 1.6 s maximum |

Rules: lazy load the graph, charts, confetti and contour background with `next/dynamic`; use `will-change` only during an animation and remove it afterwards; prefer CSS animations for ambient loops and Framer Motion for state-driven motion; if `navigator.hardwareConcurrency` is 4 or lower, start in **Calm lite** (particles off, contour static, Pip animations simplified) and show a one-time toast explaining how to turn full motion on. Test signature moments with the browser performance panel and 4x CPU throttling.

---

## 15. Implementation Guide for Antigravity

### 15.1 File Structure (additions to `apps/web`)

```text
apps/web/
├─ app/
│  ├─ design/page.tsx            # hidden kitchen-sink page
│  └─ globals.css                # tokens, themes, ambient keyframes
├─ components/
│  ├─ brand/                     # Logo, SignatureStrip, Pip, PixelIcon, ContourBackground
│  ├─ motion/                    # Reveal, Stagger, Stamp, CountUp, TypewriterText, Odometer
│  └─ ui/                        # shadcn components restyled with tokens, QuestCard
└─ lib/
   ├─ motion.ts                  # presets from §15.3
   └─ calm.tsx                   # CalmProvider and useCalmMode
```

### 15.2 Design Tokens (`globals.css`)

```css
:root,
:root[data-theme='dusk'] {
  --bg: #0A0D1A; --surface-1: #10152A; --surface-2: #171E3A; --surface-3: #1F2848;
  --border: #2A3560; --text: #EDF1FF; --text-muted: #9AA6CF;
  --brand: #6C8CFF; --brand-2: #9B6CFF;
  --sky: #7EB6F0; --amber: #FFB81C; --rose: #F57C7C; --flame: #FF3B1F; --mint: #2DD4A7;
  --shadow-card: 0 1px 0 rgba(255,255,255,0.05) inset;
  --aurora: linear-gradient(120deg, var(--brand) 0%, var(--brand-2) 45%, var(--rose) 100%);
}
:root[data-theme='parchment'] {
  --bg: #F3F1EA; --surface-1: #FBFAF6; --surface-2: #FFFFFF; --surface-3: #ECE9DF;
  --border: #1B1A17; --text: #1B1A17; --text-muted: #555A63;
  --brand: #2748D8; --brand-2: #6B3FD6;
  --sky: #3F86D6; --amber: #D98A00; --rose: #D84F58; --flame: #D42A10; --mint: #0E9F78;
  --shadow-card: 4px 4px 0 var(--border);
}
:root {
  --dur-instant: 90ms; --dur-fast: 150ms; --dur-base: 240ms; --dur-slow: 400ms; --dur-epic: 800ms;
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-in-out: cubic-bezier(0.65, 0, 0.35, 1);
  --ease-in: cubic-bezier(0.7, 0, 0.84, 0);
  --radius-sm: 6px; --radius-md: 10px; --radius-lg: 16px; --radius-xl: 24px;
}

.quest-card {
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
}

@keyframes drift { from { transform: translate3d(0, 0, 0); } to { transform: translate3d(-120px, -60px, 0); } }
@keyframes shimmer { from { background-position: -200% 0; } to { background-position: 200% 0; } }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
}
[data-calm='1'] *, [data-calm='1'] *::before, [data-calm='1'] *::after {
  animation: none !important; transition-duration: 0.01ms !important;
}
```

Because `clip-path` also clips borders and shadows, build the border of a Quest Card with a wrapper that has the same `clip-path`, a 1 px padding and the border color as its background, and place the card surface inside it. In Parchment, draw the hard shadow on the wrapper with a pseudo element offset by 4 px.

### 15.3 Motion Presets (`lib/motion.ts`)

```ts
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
```

Use `<MotionConfig reducedMotion='user'>` at the app root, wrap routes with `AnimatePresence mode='wait'` for page transitions (A26), and give list items `layout` so reordering and removal animate automatically.

### 15.4 Calm Mode (`lib/calm.tsx`)

```tsx
'use client';
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

const CalmCtx = createContext<{ calm: boolean; setCalm: (v: boolean) => void }>({
  calm: false,
  setCalm: () => {},
});

export function CalmProvider({ children }: { children: ReactNode }) {
  const [calm, setCalmState] = useState(false);
  useEffect(() => {
    let stored = false;
    try { stored = localStorage.getItem('rq-calm') === '1'; } catch {}
    setCalmState(stored);
    document.documentElement.dataset.calm = stored ? '1' : '0';
  }, []);
  const setCalm = (v: boolean) => {
    setCalmState(v);
    document.documentElement.dataset.calm = v ? '1' : '0';
    try { localStorage.setItem('rq-calm', v ? '1' : '0'); } catch {}
  };
  return <CalmCtx.Provider value={{ calm, setCalm }}>{children}</CalmCtx.Provider>;
}

export const useCalmMode = () => useContext(CalmCtx);
```

### 15.5 Pip Component (`components/brand/Pip.tsx`)

```tsx
'use client';
import { motion, useReducedMotion, type TargetAndTransition } from 'framer-motion';
import { useCalmMode } from '@/lib/calm';

export type PipState = 'idle' | 'thinking' | 'exploring' | 'success' | 'error' | 'sleeping';

const MAP = [
  '......AA......',
  '......KK......',
  '..BBBBBBBBBB..',
  '.BBBBBBBBBBBB.',
  'BBBWWBBBBWWBBB',
  'BBBWKBBBBKWBBB',
  'BBBWWBBBBWWBBB',
  'BBBBBBBBBBBBBB',
  '.BKKKKKKKKKKB.',
  '.BKAKAKAKAKKB.',
  '..BBBBBBBBBB..',
  '...BB....BB...',
];

const FILL: Record<string, string> = {
  B: 'var(--sky)', W: '#F7FAFF', K: '#171A2B', A: 'var(--amber)',
};

const BODY: Record<PipState, TargetAndTransition> = {
  idle: { y: [0, -1, 0], transition: { duration: 3, repeat: Infinity, ease: 'easeInOut' } },
  thinking: { rotate: [0, -2, 2, 0], transition: { duration: 1.2, repeat: Infinity } },
  exploring: { y: [0, -1, 0], transition: { duration: 0.4, repeat: Infinity, ease: 'linear' } },
  success: { y: [0, -12, 0], transition: { duration: 0.6, times: [0, 0.45, 1], ease: 'easeOut' } },
  error: { x: [0, -3, 3, -3, 0], transition: { duration: 0.36 } },
  sleeping: { y: [0, -1, 0], transition: { duration: 4, repeat: Infinity, ease: 'easeInOut' } },
};

export function Pip({ state = 'idle', size = 96 }: { state?: PipState; size?: number }) {
  const reduce = useReducedMotion();
  const { calm } = useCalmMode();
  const still = Boolean(reduce) || calm;

  const rects = MAP.flatMap((row, y) =>
    [...row].map((c, x) =>
      c === '.' ? null : (
        <rect key={x + '-' + y} x={x} y={y} width={1} height={1} fill={FILL[c]} />
      ),
    ),
  );

  return (
    <motion.svg
      viewBox='0 0 14 12'
      width={size}
      height={(size * 12) / 14}
      shapeRendering='crispEdges'
      role='img'
      aria-label={'Pip is ' + state}
      animate={still ? undefined : BODY[state]}
    >
      {rects}
    </motion.svg>
  );
}
```

Extend this base as specified in §9: wrap the antenna rows and eye cells in their own `motion.g` groups for blinking, scanning and drooping; add the lantern, Zs and spark pixels as extra groups shown only in their states; swap the pupil cells for cross shapes in the error state.

### 15.6 Contour Background

`ContourBackground` renders one inline SVG (about 24 hand-tuned wavy closed paths with 1 px strokes at 8 to 12 percent opacity in `--text-muted`) twice the viewport size and moves it with the `drift` keyframes over 40 s, linear, infinite. It sits behind the hero with `pointer-events: none`, is loaded with `next/dynamic`, pauses when off screen and renders static in Calm mode.

### 15.7 Design Build Order

| Step | Deliverable | Done when |
| --- | --- | --- |
| D0 | Tokens, fonts, themes, Calm provider, `/design` page skeleton | Theme switch works; both themes pass a contrast check |
| D1 | Logo, Signature Strip, Pip with all six states, pixel icons | All Pip states visible on `/design` |
| D2 | Shared components from §10 and motion presets | Every component shows all states on `/design` |
| D3 | Hero moments M1 to M5 on their screens | Each runs at 60 fps with 4x CPU throttle in Calm lite and normal modes |
| D4 | Remaining P0 animations (§8.1), then M6 and P1 items | All P0 rows implemented |
| D5 | Responsive, accessibility and performance passes | §12 to §14 verified; QA checklist in §17 passed |

---

## 16. Asset Checklist (all built in code, no external files)

| Asset | Format | Notes |
| --- | --- | --- |
| Logo (icon, wordmark, mono, favicon) | Inline SVG | Pixel compass on an 8 by 8 grid |
| Signature Strip | SVG or four `div`s | Reused as divider, loader and progress cap |
| Pip sprite and accessories | SVG rects | Lantern, magnifier, flag, Zs, spark pixels |
| Pixel icon sprite (16 by 16) | SVG symbols | Compass, flag, shield, cracked shield, scroll, lantern, key, spark, crown, lock |
| Quest map art (landing and indexing) | SVG rects generated from the repo structure | Region colors come from language colors |
| Contour pattern | Inline SVG paths | See §15.6 |
| Open Graph image and README banner | PNG exported from the landing hero | Dusk theme with the hero headline and Pip |
| Badges (First Steps, Quiz Master, Bug Squasher, First PR Merged) | SVG | 64 px pixel art, notched frame |

---

## 17. Design QA, Demo Choreography and Acceptance

### 17.1 Design QA Checklist

| Check | Expected |
| --- | --- |
| Both themes on every screen | No unreadable text, no invisible borders, no broken gradients |
| Contrast audit | All text and UI pairs meet AA |
| Keyboard-only run of the demo path | Every step reachable with a visible focus ring |
| Reduced motion on (OS setting) and Calm mode on | No parallax, particles or looping motion; all information still present |
| Calm lite auto-detection | Starts correctly on a throttled machine; toast explains it |
| Offline run (Wi-Fi off) | Fonts, Pip, map art and all animations still work |
| 4x CPU throttle on M1 to M5 | Frame rate stays smooth; no jank during fog reveal or model race |
| Browser matrix | Latest Chrome, Edge, Firefox, Safari; `backdrop-filter` and `clip-path` fall back gracefully |
| Hindi, Kannada and Tamil text | No clipped glyphs, correct line height, correct font fallback |
| Resize from 360 px to 1920 px | Layouts adapt without overlap |
| Empty, loading and error states | Pip variants and skeletons present on every screen |

### 17.2 Ninety-Second Visual Demo Path (for the pitch)

1. **0 to 10 s:** landing loads with the Map Unfurl (M1); point to the privacy badge.
2. **10 to 30 s:** click Try Demo Mode; Fog of War indexing (M2) clears and Pip celebrates.
3. **30 to 50 s:** Explore: Living Map (M3); hover a module; click Start Here.
4. **50 to 65 s:** Triage: analysis reveal and the Approve Stamp (M4).
5. **65 to 80 s:** Model Lab: the Model Race (M5) with the winner crown.
6. **80 to 90 s:** Day-1 Tour: Quest Complete (M6), then flip to Parchment to show the second theme.

### 17.3 Acceptance Criteria

- The six signature moments (M1 to M6) run smoothly, are interruptible and have reduced-motion fallbacks.
- Both themes are complete; the theme and Calm mode choices persist across reloads.
- No screen violates §13 (accessibility) or the budgets in §14.
- The app looks and behaves the same offline as online.
- A first-time viewer can describe the product after 10 seconds on the landing page (the headline, the pillars and the Pip map must make the purpose obvious).

### 17.4 One-Paragraph Prompt to Start Antigravity on the Design

Paste this after the product PRD and this document: *Implement the RepoQuest design system exactly as specified in the Design PRD. Start with D0 in section 15.7: tokens, fonts, both themes, Calm mode and the /design page. Then continue step by step. Use only the approved libraries, never hardcode colors or timings, build every P0 animation before any P1 or P2 item, and verify accessibility and performance at each step.*
