# Implementation Plan: Warm Tabletop Light UI Redesign

**Branch**: `001-warm-tabletop-ui` | **Date**: 2026-11-15 | **Spec**: [spec.md](file:///c:/Users/d.phuoc/OneDrive/Desktop/TaiLieu/AI/Final-Term/specs/001-warm-tabletop-ui/spec.md)  
**Input**: `specs/001-warm-tabletop-ui/spec.md`

## Summary

Shift the PyGame Tank Battle interface from a dark neon dashboard aesthetic to a bright Warm Tabletop light theme (`#F6F3EC` cream paper, `#FFFFFF` flat cards, royal blue `#1D4ED8` P1, brick red `#C23B2B` P2), remove sci-fi lasers and pulsing halos from `GameRenderer`, tighten visual geometry to crisp `4px`-radius cards without repetitive left accent strips, and rewrite labels in clean, natural English while preserving all layout dimensions and pytest contracts.

## Technical Context

**Language/Version**: Python 3.x (workspace `.venv`)  
**Primary Dependencies**: `pygame`, `source.task2.core.*`, `source.task2.agents.*`, `source.task2.experiments.maps`  
**Storage**: N/A (read-only `.txt` maps)  
**Testing**: `pytest source/task2/tests/test_engine.py -v` + offscreen `SDL_VIDEODRIVER=dummy` PNG render inspection  
**Target Platform**: Windows / macOS desktop PyGame (`1120x690`) + headless CI (`SDL_VIDEODRIVER=dummy`)  
**Project Type**: Desktop PyGame UI inside `source/task2/ui/`  
**Performance Goals**: 60 FPS interactive rendering; < 5s full `test_engine.py` suite  
**Constraints**: Headless import safety (no `pygame.init()` / `set_mode()` at module import); preserve `WINDOW_WIDTH`, `WINDOW_HEIGHT`, `SetupMenu` defaults & `btn_swap`, `GameRenderer.toolbar_rects` 6 keys  
**Scale/Scope**: 3 source files modified (`theme.py`, `menu.py`, `renderer.py`)

## Constitution / Guardrail Check

*No `.specify/memory/constitution.md` exists in repository; applying active project rules:*
- **Headless safety**: `PYGAME_HIDE_SUPPORT_PROMPT=1`, lazy font/display creation preserved. PASS.
- **Minimal complete change (`/ponytail`)**: Only `source/task2/ui/{theme.py,menu.py,renderer.py}` modified; core/agents/tests untouched unless contract broken. PASS.
- **WCAG Contrast**: Light palette pairs verified >= 5.02:1 (`#1E1D1A` 15.2:1 on `#F6F3EC`, `#6B655B` 5.2:1 on `#F6F3EC`, `#FFFFFF` 6.7:1 on `#1D4ED8`). PASS.

## Phase 0 Research & Design Decisions

1. **Palette & Backward-Compatible Token Names (`theme.py`)**:
   - **Decision**: Keep all existing constant names (`BG_DARK`, `SURFACE_PANEL`, `SURFACE_CARD`, `SURFACE_ELEVATED`, etc.) so internal and test callers stay compatible, add `BG_CANVAS = (246, 243, 236)` / `TEXT_ON_ACCENT = (255, 255, 255)` / `P1_TILE_TINT` / `P2_TILE_TINT`, and alias `BG_DARK = BG_CANVAS` (used for screen background) while using dark ink `TEXT_DARK = (30, 29, 26)` only for dark typography/frames and white `TEXT_ON_ACCENT` on dark blue/red buttons and tank badges.
   - **Rationale**: Zero breakage for any external import referencing `theme.BG_DARK` or `theme.TEXT_DARK`.
2. **Classic Tabletop Board Cues (`renderer.py`)**:
   - **Decision**: Delete `_draw_aiming_lasers` and `_draw_active_halo` calls from rendering; introduce `_draw_active_tile_cue` drawing soft team tint + `2px` square border directly on the active tank cell. Keep `_draw_bullet_fx` with clean solid trajectory line/dots + crisp dark-rimmed impact ring.
   - **Rationale**: Eliminates sci-fi glow clutter while keeping turn ownership and shot impact immediately scannable.
3. **Humanized Copy & Flat Card Structure (`menu.py`, `renderer.py`)**:
   - **Decision**: Replace `// ADVERSARIAL SEARCH`, `[Built-in]`, `SWAP P1 <-> P2`, `TACTICAL EVAL (P1 vs P2)`, `COMBAT ACTION LOG`, and heavy vertical accent strips with crisp `border_radius=4` cards, subtle `1px` stone borders, clean divider lines, and concise tabletop wording (`Tank Battle`, `Map`, `Player 1`, `Player 2`, `Advantage`, `Move Log`, `Controls`). Keep button/pill `border_radius=4`.
   - **Rationale**: Directly removes "AI template" signature while maintaining crisp visual hierarchy.

## Project Structure

### Documentation (this feature)

```text
specs/001-warm-tabletop-ui/
├── spec.md
├── plan.md
└── tasks.md
```

### Source Code (repository root)

```text
source/task2/ui/
├── __init__.py    # Unchanged (lazy re-exports & headless safety)
├── theme.py       # Warm Tabletop color system, high-contrast entities
├── menu.py        # SetupMenu: flat paper layout, natural copy
└── renderer.py    # GameRenderer & TankBattleApp: active tile cue, clean FX, sidebar cards
```

## Contrast & Token Summary

| Token | Hex | Role |
|---|---|---|
| `BG_CANVAS` | `#F6F3EC` | Main cream paper window background |
| `SURFACE_CARD` | `#FFFFFF` | Card surface |
| `SURFACE_ELEVATED` | `#EDE8DD` | Secondary button / progress track inset |
| `BORDER_SUBTLE` | `#D6D0C4` | 1px card & divider hairline |
| `BORDER_LIGHT` | `#B5ADA0` | Grid border & interactive button outline |
| `GRID_EVEN` / `GRID_ODD` | `#EFECE3` / `#E4DFD2` | Warm tabletop 13x13 checkerboard |
| `P1_PRIMARY` | `#1D4ED8` | Royal blue (P1 tank, primary CTA, active focus) |
| `P2_PRIMARY` | `#C23B2B` | Brick red (P2 tank & bar) |
| `TEXT_PRIMARY` / `TEXT_SECONDARY` / `TEXT_MUTED` | `#1E1D1A` / `#4F4B42` / `#6B655B` | High-contrast charcoal/warm-grey ink |
| `TEXT_ON_ACCENT` | `#FFFFFF` | Labels on blue/red buttons, tank turret IDs |
