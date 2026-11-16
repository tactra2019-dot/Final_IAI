# Feature Specification: Warm Tabletop Light UI Redesign

**Feature Branch**: `001-warm-tabletop-ui`  
**Created**: 2026-11-15  
**Status**: Clarified & Approved  
**Input**: User request: "Sửa lại phần UI sao cho không AI hóa quá, và làm sáng hơn" (with Warm Tabletop light palette, clean classic board cues, concise natural English copy, and crisp flat paper cards).

## Clarifications

### Session 2026-11-15 (via `/grill-me` & `/brainstorming`)

- **Palette & Brightness**: Warm Tabletop light palette — cream paper canvas `#F6F3EC`, white cards `#FFFFFF`, sand insets `#EDE8DD`, stone borders `#D6D0C4` / `#B5ADA0`, royal blue P1 `#1D4ED8`, brick red P2 `#C23B2B`, no neon colors or dark navy surfaces.
- **Board Visuals & FX**: Remove `_draw_aiming_lasers` (laser sight lines and crosshairs) and `_draw_active_halo` (pulsing circles and sci-fi corner brackets). Mark the active player's tank with a static 2px square tile outline and soft team tile tint. Keep clean bullet trajectory and hit ring when firing, plus crisp legible `-1 HP` damage popups.
- **UI Copy & Language**: Keep concise, natural English game labels without sci-fi/AI dashboard clichés (`Tank Battle`, `Map`, `Player 1`, `Player 2`, `Search Depth`, `Advantage`, `Move Log`, `Built-in` / `Plugin` / `Human`).
- **Card & Control Shape**: Crisp flat tabletop style (`border_radius=4`), 1px stone borders, horizontal dividers, and no repeated 4px vertical accent strips on every card.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Bright Warm Tabletop Color System & Readability (Priority: P1)

Players opening the setup screen or watching a live match see a bright, daylight-friendly cream-and-white interface with crisp dark ink text and unmistakable team colors instead of a dark navy neon dashboard.

**Why this priority**: Solves the user's primary ask ("làm sáng hơn") and eliminates the generic dark-slate/neon-cyan/pink AI aesthetic at the design-token root.

**Independent Test**: Render `SetupMenu` and `GameRenderer` offscreen (`SDL_VIDEODRIVER=dummy`) to PNG and verify light canvas luminance, readable text contrast (>= 4.5:1 for body/muted labels), white turret numerals on blue/red tanks, and zero neon glow layers.

**Acceptance Scenarios**:

1. **Given** the theme tokens in `task2/ui/theme.py`, **When** a menu or game frame renders, **Then** the outer background is `#F6F3EC`, panels are `#FFFFFF`, primary text is `#1E1D1A` (contrast >= 15:1), and muted labels are `#6B655B` (contrast >= 5:1).
2. **Given** P1 and P2 tanks and bases on the 13x13 board, **When** `draw_tank_body` and `draw_base_shield` execute, **Then** P1 renders in deep royal blue (`#1D4ED8`) and P2 in brick red (`#C23B2B`) with high-contrast white numerals (`#FFFFFF`).

---

### User Story 2 - Uncluttered Classic Board Cues (Priority: P1)

Observers and human players can immediately tell whose turn it is, where walls/bases stand, and where shots hit without sci-fi aiming lasers, pulsing radar rings, or corner targeting brackets cluttering the grid.

**Why this priority**: Directly removes the strongest "AI-generated game UI" visual artifacts on the battlefield while preserving full gameplay clarity.

**Independent Test**: Call `GameRenderer.draw(...)` on a mid-match `GameState` with `last_bullet_path` and `last_hit_pos`, verifying `_draw_aiming_lasers` and `_draw_active_halo` are absent, active tile border/tint highlights the current tank, and shot/hit feedback stays visible.

**Acceptance Scenarios**:

1. **Given** an active non-terminal match, **When** `GameRenderer.draw` renders the 13x13 board, **Then** only the active turn tank's tile receives a subtle team-tinted background and crisp 2px square border, with no laser beams or pulsing halos drawn.
2. **Given** a `FIRE` action producing `last_bullet_path` and `last_hit_pos`, **When** `GameRenderer.draw` renders FX and popups, **Then** the trajectory and impact burst use crisp high-contrast amber/terracotta tones (`#EA580C` / `#F59E0B`) and `-1 HP` floating tags remain legible over light tiles.

---

### User Story 3 - Humanized Setup Menu & Sidebar Cards (Priority: P2)

Players configuring matches or reading live telemetry see natural, concise tabletop copy and crisp 4px-radius flat cards rather than repetitive rounded boxes with left neon bars and buzzword titles.

**Why this priority**: Completes the anti-AI polish across `menu.py` and `renderer.py` while keeping all keyboard shortcuts, mouse hitboxes, and pytest contracts intact.

**Independent Test**: Run `pytest task2/tests/test_engine.py -v` and inspect `menu` and `match` PNG captures to confirm clean text fit (no truncation overlap), natural headings, `btn_swap` click behavior, and `toolbar_rects` keys.

**Acceptance Scenarios**:

1. **Given** `SetupMenu` at `1120x690`, **When** rendered, **Then** header displays `"Tank Battle"`, selector titles use `"Map"`, `"Player 1"`, `"Player 2"`, `"Search Depth"`, buttons use `"Start Match"`, `"Reload Plugins"`, `"Run Benchmark"`, and clicking `btn_swap` still swaps P1 and P2 agents.
2. **Given** `GameRenderer` sidebar cards, **When** rendered, **Then** cards use `border_radius=4` with 1px `#D6D0C4` borders (active player card uses 2px team border), no repeated left color strips, concise headers (`Match`, `Advantage`, `Move Log`, `Controls`), and all 6 `toolbar_rects` keys remain clickable.

### Edge Cases

- **Headless safety**: Importing `task2.ui`, `task2.ui.theme`, `task2.ui.menu`, or `task2.ui.renderer` must NOT initialize PyGame display or call `pygame.init()`.
- **External plugins**: Unknown custom agent class names or long filenames must truncate cleanly inside selector and telemetry cards without overflowing card borders.
- **Popups on light checkerboard**: High-contrast popup pill fill + outline prevents pale yellow/orange text from washing out over `#EFECE3` floor tiles.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `task2/ui/theme.py` MUST define a Warm Tabletop light palette (`BG_CANVAS`/`BG_DARK`, `SURFACE_CARD`, `SURFACE_INSET`, `GRID_EVEN`, `GRID_ODD`, `P1_PRIMARY`, `P2_PRIMARY`, `WALL_HP3..1`, `TEXT_PRIMARY..TEXT_MUTED`, `TEXT_ON_ACCENT`) meeting WCAG AA (>= 4.5:1) for UI text.
- **FR-002**: `theme.draw_tank_body` and `theme.draw_base_shield` MUST use white numerals (`#FFFFFF`) on royal-blue / brick-red entities for clear contrast on light tiles.
- **FR-003**: `theme.player_palette(player_id)` MUST keep its 6-tuple return shape for compatibility with any caller while updating colors to the light palette.
- **FR-004**: `task2/ui/renderer.py` MUST remove aiming laser rays and pulsing sci-fi halos, replacing them with a static active-tile highlight (`2px` border + soft tint).
- **FR-005**: `task2/ui/renderer.py` MUST render crisp light-mode bullet tracers, impact rings, and legible `-1 HP` popups without glowing neon bloom.
- **FR-006**: `task2/ui/menu.py` and `task2/ui/renderer.py` MUST replace buzzword/AI-template copy (`// ADVERSARIAL SEARCH`, `[Built-in]`, `TACTICAL EVAL`, `COMBAT ACTION LOG`, etc.) and window caption with natural, concise English tabletop labels.
- **FR-007**: Cards and buttons across `menu.py` and `renderer.py` MUST use sharp flat geometry (`border_radius=4`), `1px` borders (2px on focused/active element), horizontal dividers where appropriate, and remove decorative 4px vertical left strips on cards.
- **FR-008**: All existing test and runtime contracts (`WINDOW_WIDTH=1120`, `WINDOW_HEIGHT=690`, `SetupMenu` default agents `HeuristicAlphaBetaAgent`/`HeuristicMinimaxAgent`, `menu._rects["btn_swap"]`, `renderer.toolbar_rects` 6 keys, headless import rule) MUST remain passing.

### Key Entities

- **Theme Palette Tokens (`theme.py`)**: Warm paper `#F6F3EC`, pure card white `#FFFFFF`, inset sand `#EDE8DD`, royal blue `#1D4ED8`, brick red `#C23B2B`, ink text `#1E1D1A` / `#4F4B42` / `#6B655B`.
- **Setup Screen (`SetupMenu`)**: Left configuration column + right 13x13 board preview + bottom action bar (`Start Match`, `Reload Plugins`, `Run Benchmark`).
- **Arena & Sidebar (`GameRenderer`, `TankBattleApp`)**: 13x13 grid (`624x624` at `(36, 42)`) + `414px` sidebar (`Match`, `Advantage`, P1/P2 cards, `Move Log`, `Controls`).
