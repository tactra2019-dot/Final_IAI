"""Core simulation engine symbols for Task 2."""

from __future__ import annotations

from source.task2.core.actions import ACTION_TO_DIRECTION, ALL_ACTIONS, Action, Direction
from source.task2.core.constants import (
    BASE_INITIAL_HP,
    BULLET_DAMAGE,
    BULLET_SPEED,
    EXTERNAL_AGENT_TIMEOUT_SEC,
    GRID_HEIGHT,
    GRID_WIDTH,
    MAX_TURNS,
    TANK_INITIAL_HP,
    UTILITY_DRAW,
    UTILITY_LOSS,
    UTILITY_WIN,
    WALL_INITIAL_HP,
)
from source.task2.core.entities import Base, Bullet, Entity, Tank, Wall
from source.task2.core.game_engine import GameEngine
from source.task2.core.game_state import GameState

__all__ = [
    "ACTION_TO_DIRECTION",
    "ALL_ACTIONS",
    "Action",
    "BASE_INITIAL_HP",
    "BULLET_DAMAGE",
    "BULLET_SPEED",
    "Base",
    "Bullet",
    "Direction",
    "EXTERNAL_AGENT_TIMEOUT_SEC",
    "Entity",
    "GRID_HEIGHT",
    "GRID_WIDTH",
    "GameEngine",
    "GameState",
    "MAX_TURNS",
    "TANK_INITIAL_HP",
    "Tank",
    "UTILITY_DRAW",
    "UTILITY_LOSS",
    "UTILITY_WIN",
    "WALL_INITIAL_HP",
    "Wall",
]
