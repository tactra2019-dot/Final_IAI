"""Domain entity classes for Tank Battle."""

from __future__ import annotations

from source.task2.core.actions import Direction
from source.task2.core.constants import (
    BASE_INITIAL_HP,
    BULLET_SPEED,
    TANK_INITIAL_HP,
    WALL_INITIAL_HP,
)


class Entity:
    """Base game entity with grid coordinates and hit points."""

    def __init__(self, x: int, y: int, hp: int, max_hp: int) -> None:
        self.x: int = x
        self.y: int = y
        self.hp: int = max(0, hp)
        self.max_hp: int = max(1, max_hp)

    def take_damage(self, amount: int = 1) -> None:
        """Reduce HP by amount, clamped to a minimum of zero."""
        if amount < 0:
            raise ValueError(f"Damage amount must be non-negative, got {amount}")
        self.hp = max(0, self.hp - amount)

    def is_alive(self) -> bool:
        """Return True when entity still has positive HP."""
        return self.hp > 0

    @property
    def pos(self) -> tuple[int, int]:
        """Current (x, y) grid position."""
        return (self.x, self.y)


class Tank(Entity):
    """Player-controlled tank with facing direction."""

    def __init__(
        self,
        x: int,
        y: int,
        player_id: int,
        direction: Direction = Direction.UP,
        hp: int = TANK_INITIAL_HP,
        max_hp: int = TANK_INITIAL_HP,
    ) -> None:
        super().__init__(x=x, y=y, hp=hp, max_hp=max_hp)
        self.player_id: int = player_id
        self.direction: Direction = direction

    def clone(self) -> Tank:
        """Return an independent fast copy of this tank."""
        return Tank(
            x=self.x,
            y=self.y,
            player_id=self.player_id,
            direction=self.direction,
            hp=self.hp,
            max_hp=self.max_hp,
        )


class Base(Entity):
    """Stationary player headquarters."""

    def __init__(
        self,
        x: int,
        y: int,
        player_id: int,
        hp: int = BASE_INITIAL_HP,
        max_hp: int = BASE_INITIAL_HP,
    ) -> None:
        super().__init__(x=x, y=y, hp=hp, max_hp=max_hp)
        self.player_id: int = player_id

    def clone(self) -> Base:
        """Return an independent fast copy of this base."""
        return Base(
            x=self.x,
            y=self.y,
            player_id=self.player_id,
            hp=self.hp,
            max_hp=self.max_hp,
        )


class Wall(Entity):
    """Destructible brick wall block."""

    def __init__(
        self,
        x: int,
        y: int,
        hp: int = WALL_INITIAL_HP,
        max_hp: int = WALL_INITIAL_HP,
    ) -> None:
        super().__init__(x=x, y=y, hp=hp, max_hp=max_hp)

    def clone(self) -> Wall:
        """Return an independent fast copy of this wall."""
        return Wall(
            x=self.x,
            y=self.y,
            hp=self.hp,
            max_hp=self.max_hp,
        )


class Bullet:
    """Projectile moving cell-by-cell along its firing direction."""

    def __init__(
        self,
        x: int,
        y: int,
        direction: Direction,
        owner_id: int,
        speed: int = BULLET_SPEED,
    ) -> None:
        self.x: int = x
        self.y: int = y
        self.direction: Direction = direction
        self.owner_id: int = owner_id
        self.speed: int = speed

    def step_one_cell(self) -> tuple[int, int]:
        """Advance bullet by one grid cell and return the new (x, y) position."""
        dx, dy = self.direction.value
        self.x += dx
        self.y += dy
        return (self.x, self.y)

    def clone(self) -> Bullet:
        """Return an independent fast copy of this bullet."""
        return Bullet(
            x=self.x,
            y=self.y,
            direction=self.direction,
            owner_id=self.owner_id,
            speed=self.speed,
        )
