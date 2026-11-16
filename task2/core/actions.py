"""Movement directions and discrete actions for Tank Battle."""

from __future__ import annotations

from enum import Enum


class Direction(Enum):
    """Cardinal movement and firing directions represented as (dx, dy) offsets."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

    @property
    def dx(self) -> int:
        """Horizontal grid delta."""
        return self.value[0]

    @property
    def dy(self) -> int:
        """Vertical grid delta."""
        return self.value[1]


class Action(Enum):
    """Legal discrete actions available to a tank on its turn."""

    MOVE_UP = "MOVE_UP"
    MOVE_DOWN = "MOVE_DOWN"
    MOVE_LEFT = "MOVE_LEFT"
    MOVE_RIGHT = "MOVE_RIGHT"
    FIRE = "FIRE"
    STAY = "STAY"


ACTION_TO_DIRECTION: dict[Action, Direction] = {
    Action.MOVE_UP: Direction.UP,
    Action.MOVE_DOWN: Direction.DOWN,
    Action.MOVE_LEFT: Direction.LEFT,
    Action.MOVE_RIGHT: Direction.RIGHT,
}

ALL_ACTIONS: tuple[Action, ...] = (
    Action.MOVE_UP,
    Action.MOVE_DOWN,
    Action.MOVE_LEFT,
    Action.MOVE_RIGHT,
    Action.FIRE,
    Action.STAY,
)
