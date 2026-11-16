"""High-contrast dark tactical palette, layout geometry, and shared glyphs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from task2.core.actions import Direction
from task2.core.constants import GRID_HEIGHT, GRID_WIDTH

if TYPE_CHECKING:
    import pygame

# Expanded layout geometry (zero clipping of row/col headers & border HP bars)
CELL_SIZE = 48
BOARD_WIDTH = GRID_WIDTH * CELL_SIZE   # 624
BOARD_HEIGHT = GRID_HEIGHT * CELL_SIZE # 624
BOARD_X = 36
BOARD_Y = 42
SIDEBAR_X = 682
SIDEBAR_WIDTH = 414
WINDOW_WIDTH = 1120
WINDOW_HEIGHT = 690
FPS = 60

# Warm Tabletop Light Surface Hierarchy
BG_CANVAS = (246, 243, 236)     # #F6F3EC
BG_DARK = BG_CANVAS             # Compatibility alias
SURFACE_PANEL = (255, 255, 255) # #FFFFFF
SURFACE_CARD = (255, 255, 255)  # #FFFFFF
SURFACE_INSET = (237, 232, 221) # #EDE8DD
SURFACE_ELEVATED = SURFACE_INSET
SURFACE_HOVER = (224, 217, 203) # #E0D9CB

GRID_EVEN = (242, 239, 231)     # #F2EFE7
GRID_ODD = (231, 226, 214)      # #E7E2D6
GRID_LINE = (212, 206, 193)     # #D4CEC1
BORDER_SUBTLE = (214, 208, 196) # #D6D0C4
BORDER_LIGHT = (175, 167, 154)  # #AFA79A

# Player 1 (Royal Blue / MAX)
P1_PRIMARY = (29, 78, 216)      # #1D4ED8
P1_DARK = (30, 58, 138)         # #1E3A8A
P1_TRACK = (41, 37, 36)         # #292524
P1_GLOW = (37, 99, 235)         # #2563EB
P1_TILE_TINT = (224, 234, 255)  # #E0EAFF
LASER_P1 = P1_PRIMARY
HALO_P1 = P1_PRIMARY

# Player 2 (Brick Red / MIN)
P2_PRIMARY = (194, 59, 43)      # #C23B2B
P2_DARK = (140, 37, 24)         # #8C2518
P2_TRACK = (41, 37, 36)         # #292524
P2_GLOW = (220, 76, 58)         # #DC4C3A
P2_TILE_TINT = (252, 230, 226)  # #FCE6E2
LASER_P2 = P2_PRIMARY
HALO_P2 = P2_PRIMARY

# Map Entities
WALL_HP3 = (180, 83, 9)         # #B45309
WALL_HP2 = (217, 119, 6)        # #D97706
WALL_HP1 = (234, 179, 8)        # #EAB308
WALL_MORTAR = (246, 238, 224)   # #F6EEE0
WALL_CRACK = (92, 43, 18)       # #5C2B12

BASE_P1 = (154, 66, 6)          # #9A4206
BASE_P1_DARK = (30, 58, 138)    # #1E3A8A
BASE_P2 = (154, 66, 6)          # #9A4206
BASE_P2_DARK = (140, 37, 24)    # #8C2518

# Projectiles, FX & Interactive Toolbar
BULLET_TRAIL = (234, 88, 12)    # #EA580C
IMPACT_ORANGE = (194, 65, 12)   # #C2410C
IMPACT_CORE = (254, 240, 138)   # #FEF08A
EVAL_BAR_BG = (226, 220, 207)   # #E2DCCF
BTN_BG = (237, 232, 221)        # #EDE8DD
BTN_HOVER = (224, 217, 203)     # #E0D9CB
BTN_ACTIVE = (29, 78, 216)      # #1D4ED8

# Typography & Status Colors
TEXT_PRIMARY = (30, 29, 26)     # #1E1D1A
TEXT_SECONDARY = (79, 75, 66)   # #4F4B42
TEXT_MUTED = (107, 101, 91)     # #6B655B
TEXT_DARK = (30, 29, 26)        # #1E1D1A
TEXT_ON_ACCENT = (255, 255, 255)# #FFFFFF

STATUS_GOOD = (21, 128, 61)     # #15803D
STATUS_WARN = (180, 83, 9)      # #B45309
STATUS_DANGER = (185, 28, 28)   # #B91C1C


def hp_color(ratio: float) -> tuple[int, int, int]:
    """Return green/amber/red based on remaining HP ratio."""
    if ratio > 0.55:
        return STATUS_GOOD
    if ratio > 0.25:
        return STATUS_WARN
    return STATUS_DANGER


def player_palette(player_id: int) -> tuple[tuple[int, int, int], ...]:
    """Return (primary, dark, track, glow, laser, halo) colors for player_id."""
    if player_id == 1:
        return (P1_PRIMARY, P1_DARK, P1_TRACK, P1_GLOW, LASER_P1, HALO_P1)
    return (P2_PRIMARY, P2_DARK, P2_TRACK, P2_GLOW, LASER_P2, HALO_P2)


def draw_base_shield(
    pygame_mod: "pygame",
    surface: "pygame.Surface",
    cx: int,
    cy: int,
    player_id: int,
    radius: int,
    label_font: "pygame.font.Font | None" = None,
) -> None:
    """Draw a shield-shaped base icon shared by the arena and menu preview."""
    team = P1_PRIMARY if player_id == 1 else P2_PRIMARY
    rim = P1_DARK if player_id == 1 else P2_DARK
    crest = (245, 196, 81)

    w = radius
    top = int(radius * 0.95)
    mid = int(radius * 0.12)
    bot = int(radius * 0.95)
    shield = [
        (cx - int(w * 0.88), cy - top),
        (cx + int(w * 0.88), cy - top),
        (cx + w, cy - mid),
        (cx, cy + bot),
        (cx - w, cy - mid),
    ]
    pygame_mod.draw.polygon(surface, team, shield)
    pygame_mod.draw.polygon(surface, rim, shield, width=max(2, radius // 6))
    pygame_mod.draw.circle(surface, crest, (cx, cy - max(2, radius // 3)), max(2, radius // 4))
    if label_font is not None:
        lbl = label_font.render(f"B{player_id}", True, TEXT_ON_ACCENT)
        surface.blit(lbl, lbl.get_rect(center=(cx, cy + max(1, radius // 5))))


def draw_tank_body(
    pygame_mod: "pygame",
    surface: "pygame.Surface",
    cx: int,
    cy: int,
    player_id: int,
    direction: Direction,
    cell_size: int,
    label_font: "pygame.font.Font | None" = None,
) -> None:
    """Draw directional tank treads, hull, turret, and barrel scaled to cell_size."""
    primary, dark, track, glow, _, _ = player_palette(player_id)
    scale = cell_size / 48.0
    vertical = direction in (Direction.UP, Direction.DOWN)

    tread_thick = max(3, int(6 * scale))
    tread_len = max(10, int(24 * scale))
    tread_off = max(5, int(9 * scale))
    hull_w = max(8, int(18 * scale))
    hull_h = max(10, int(22 * scale))

    if vertical:
        pygame_mod.draw.rect(
            surface, track, pygame_mod.Rect(cx - tread_off - tread_thick, cy - tread_len // 2, tread_thick, tread_len),
            border_radius=2,
        )
        pygame_mod.draw.rect(
            surface, track, pygame_mod.Rect(cx + tread_off, cy - tread_len // 2, tread_thick, tread_len),
            border_radius=2,
        )
        hull = pygame_mod.Rect(cx - hull_w // 2, cy - hull_h // 2, hull_w, hull_h)
    else:
        pygame_mod.draw.rect(
            surface, track, pygame_mod.Rect(cx - tread_len // 2, cy - tread_off - tread_thick, tread_len, tread_thick),
            border_radius=2,
        )
        pygame_mod.draw.rect(
            surface, track, pygame_mod.Rect(cx - tread_len // 2, cy + tread_off, tread_len, tread_thick),
            border_radius=2,
        )
        hull = pygame_mod.Rect(cx - hull_h // 2, cy - hull_w // 2, hull_h, hull_w)

    pygame_mod.draw.rect(surface, dark, hull, border_radius=max(2, int(4 * scale)))
    pygame_mod.draw.rect(surface, primary, hull.inflate(-2, -2), border_radius=max(2, int(3 * scale)))

    barrel_len = max(8, int(15 * scale))
    barrel_w = max(2, int(4 * scale))
    dx, dy = direction.value
    barrel_end = (cx + dx * barrel_len, cy + dy * barrel_len)
    pygame_mod.draw.line(surface, dark, (cx, cy), barrel_end, barrel_w)
    pygame_mod.draw.circle(surface, dark, barrel_end, max(2, int(2.5 * scale)))

    turret_r = max(4, int(7 * scale))
    pygame_mod.draw.circle(surface, dark, (cx, cy), turret_r + 1)
    pygame_mod.draw.circle(surface, primary, (cx, cy), turret_r)
    if label_font is not None:
        tag = label_font.render(str(player_id), True, TEXT_ON_ACCENT)
        surface.blit(tag, tag.get_rect(center=(cx, cy)))


@dataclass(frozen=True)
class ThemeFonts:
    """Loaded PyGame font suite initialized lazily in GUI mode."""

    title: "pygame.font.Font"
    heading: "pygame.font.Font"
    body: "pygame.font.Font"
    body_bold: "pygame.font.Font"
    small: "pygame.font.Font"
    tiny: "pygame.font.Font"
    mono: "pygame.font.Font"
    mono_bold: "pygame.font.Font"


def load_fonts(pygame_module: "pygame") -> ThemeFonts:
    """Create cross-platform fonts after pygame.init() has been called."""
    sans_candidates = "segoeui,arial,helveticaneue,dejavusans"
    mono_candidates = "consolas,menlo,monaco,dejavusansmono"
    return ThemeFonts(
        title=pygame_module.font.SysFont(sans_candidates, 24, bold=True),
        heading=pygame_module.font.SysFont(sans_candidates, 16, bold=True),
        body=pygame_module.font.SysFont(sans_candidates, 14),
        body_bold=pygame_module.font.SysFont(sans_candidates, 14, bold=True),
        small=pygame_module.font.SysFont(sans_candidates, 12),
        tiny=pygame_module.font.SysFont(sans_candidates, 11, bold=True),
        mono=pygame_module.font.SysFont(mono_candidates, 13),
        mono_bold=pygame_module.font.SysFont(mono_candidates, 13, bold=True),
    )
