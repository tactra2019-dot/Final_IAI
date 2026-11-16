# Tasks: Warm Tabletop Light UI Redesign

**Input**: Design documents from `task2/specs/001-warm-tabletop-ui/`
**Prerequisites**: `plan.md`, `spec.md`

## Phase 1: Foundational Design Tokens (`theme.py`)

**Goal**: Replace the dark slate/neon palette with the verified Warm Tabletop light palette while keeping every exported symbol name and signature compatible.

- [x] T001 [US1] Replace dark navy/neon RGB constants with Warm Tabletop palette tokens (`#F6F3EC`, `#FFFFFF`, `#EDE8DD`, `#1D4ED8`, `#C23B2B`, `#1E1D1A`..`#6B655B`, `TEXT_ON_ACCENT`, `P1_TILE_TINT`, `P2_TILE_TINT`, light-friendly wall/bullet/status colors) in `task2/ui/theme.py`
- [x] T002 [US1] Update `player_palette`, `hp_color`, `draw_base_shield`, and `draw_tank_body` for crisp light-mode contrast and white turret/base numerals in `task2/ui/theme.py`

**Checkpoint**: Importing `task2.ui.theme` succeeds cleanly with zero PyGame side effects.

---

## Phase 2: Setup Menu Redesign (`menu.py`)

**Goal**: Deliver bright flat cards (`border_radius=4`), humanized English labels, readable overlays, and zero AI-template strips on `SetupMenu`.

- [x] T003 [US3] Rewrite `AGENT_DESCRIPTIONS`, `collect_agent_options` tags (`Built-in` / `Plugin` / `Human`), header text (`Tank Battle`), and status/depth copy to concise natural English in `task2/ui/menu.py`
- [x] T004 [US3] Update `_draw_selector_card`, `_draw_swap_button`, `_draw_depth_card`, `_draw_preview_panel`, `_draw_action_buttons`, and `_draw` modal overlay to use crisp flat `border_radius=4` light cards without left accent bars in `task2/ui/menu.py` (preserving `_rects["btn_swap"]`, focus highlights, and default P1/P2 selection)

**Checkpoint**: `SetupMenu` renders cleanly onto `1120x690` offscreen surface and passes swap/click interactions.

---

## Phase 3: Arena Board & Telemetry Sidebar (`renderer.py`)

**Goal**: Remove sci-fi lasers and pulsing halos, add static active-tile highlighting, tune bullet/impact/popup legibility for cream tiles, and modernize sidebar cards and wording.

- [x] T005 [US2] Remove `_draw_aiming_lasers` and `_draw_active_halo`, replacing them with clean static `_draw_active_tile_cue` (team tile tint + `2px` square border) in `task2/ui/renderer.py`
- [x] T006 [US2] Update `_draw_walls`, `_draw_hp_bar`, `_draw_bullet_fx`, and `_draw_popups` for high contrast on warm light tiles (including solid pill backdrop/border on wall HP badge and `-1 HP` floating popup) in `task2/ui/renderer.py`
- [x] T007 [US3] Update `_draw_match_card`, `_draw_eval_bar`, `_draw_player_card`, `_draw_log_card`, `_draw_controls_card`, and `TankBattleApp` caption (`Tank Battle`) to crisp flat `border_radius=4` cards and concise humanized English copy in `task2/ui/renderer.py` (preserving all 6 `toolbar_rects` keys)

**Checkpoint**: Live `GameRenderer` frame displays bright tabletop arena, clean bullet FX, and uncluttered sidebar.

---

## Phase 4: Verification & Visual Inspection

- [x] T008 Run `python -m py_compile` on `task2/ui/theme.py`, `task2/ui/menu.py`, `task2/ui/renderer.py`
- [x] T009 Run `pytest task2/tests/test_engine.py -v` and confirm all 39 tests pass with zero skipped assertions
- [x] T010 Render offscreen PNG screenshots (`menu` and `match` with bullet FX + popup) via `SDL_VIDEODRIVER=dummy` to scratch directory and inspect visually with `read_file` for brightness, contrast, spacing, and text clipping; fix any visual defect before finishing

## Dependencies & Execution Order

- `T001`–`T002` (`theme.py`) block `T003`–`T007` because `menu.py` and `renderer.py` use updated palette tokens like `TEXT_ON_ACCENT` and tile tints.
- `T003`–`T004` (`menu.py`) and `T005`–`T007` (`renderer.py`) can be implemented independently once `theme.py` is ready.
- `T008`–`T010` execute sequentially after all code edits complete.
