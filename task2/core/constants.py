"""Game configuration and evaluation constants for Tank Battle."""

from __future__ import annotations

GRID_WIDTH: int = 13
GRID_HEIGHT: int = 13

TANK_INITIAL_HP: int = 6
BASE_INITIAL_HP: int = 9
WALL_INITIAL_HP: int = 3
WEAK_WALL_INITIAL_HP: int = 1

BULLET_SPEED: int = 3
BULLET_DAMAGE: int = 1

MAX_TURNS: int = 200

UTILITY_WIN: float = 10000.0
UTILITY_LOSS: float = -10000.0
UTILITY_DRAW: float = 0.0

EXTERNAL_AGENT_TIMEOUT_SEC: float = 2.0
