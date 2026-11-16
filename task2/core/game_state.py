"""Immutable-friendly GameState representation and ASCII map parser."""

from __future__ import annotations

from pathlib import Path

from task2.core.actions import ALL_ACTIONS, Action, Direction
from task2.core.constants import (
    BASE_INITIAL_HP,
    GRID_HEIGHT,
    GRID_WIDTH,
    MAX_TURNS,
    TANK_INITIAL_HP,
    UTILITY_DRAW,
    UTILITY_LOSS,
    UTILITY_WIN,
    WALL_INITIAL_HP,
    WEAK_WALL_INITIAL_HP,
)
from task2.core.entities import Base, Bullet, Tank

_VALID_MAP_CHARS = frozenset({".", "W", "w", "1", "2", "A", "B"})


class GameState:
    """Lightweight representation of a Tank Battle game state."""

    def __init__(
        self,
        tanks: dict[int, Tank],
        bases: dict[int, Base],
        walls: dict[tuple[int, int], int] | None = None,
        bullets: list[Bullet] | None = None,
        width: int = GRID_WIDTH,
        height: int = GRID_HEIGHT,
        current_turn: int = 1,
        turn_count: int = 0,
        max_turns: int = MAX_TURNS,
        last_action: Action | None = None,
        last_bullet_path: list[tuple[int, int]] | None = None,
        last_hit_pos: tuple[int, int] | None = None,
        last_hit_kind: str | None = None,
        _walls_key: tuple[tuple[tuple[int, int], int], ...] | None = None,
    ) -> None:
        self.width: int = width
        self.height: int = height
        self.tanks: dict[int, Tank] = tanks
        self.bases: dict[int, Base] = bases
        self.walls: dict[tuple[int, int], int] = walls if walls is not None else {}
        self.bullets: list[Bullet] = bullets if bullets is not None else []
        self.current_turn: int = current_turn
        self.turn_count: int = turn_count
        self.max_turns: int = max_turns
        self.last_action: Action | None = last_action
        self.last_bullet_path: list[tuple[int, int]] = (
            last_bullet_path if last_bullet_path is not None else []
        )
        self.last_hit_pos: tuple[int, int] | None = last_hit_pos
        self.last_hit_kind: str | None = last_hit_kind
        self._walls_key: tuple[tuple[tuple[int, int], int], ...] | None = _walls_key

    def in_bounds(self, x: int, y: int) -> bool:
        """Return True if (x, y) lies inside the grid."""
        return 0 <= x < self.width and 0 <= y < self.height

    def walls_key(self) -> tuple[tuple[tuple[int, int], int], ...]:
        """Return a cached sorted representation of walls for hashing and path lookups."""
        if self._walls_key is None:
            self._walls_key = tuple(sorted(self.walls.items()))
        return self._walls_key

    def clone(self) -> GameState:
        """Return an independent fast copy without copy.deepcopy()."""
        return GameState(
            tanks={pid: tank.clone() for pid, tank in self.tanks.items()},
            bases={pid: base.clone() for pid, base in self.bases.items()},
            walls=self.walls.copy(),
            bullets=[b.clone() for b in self.bullets] if self.bullets else [],
            width=self.width,
            height=self.height,
            current_turn=self.current_turn,
            turn_count=self.turn_count,
            max_turns=self.max_turns,
            last_action=self.last_action,
            last_bullet_path=self.last_bullet_path.copy() if self.last_bullet_path else [],
            last_hit_pos=self.last_hit_pos,
            last_hit_kind=self.last_hit_kind,
            _walls_key=self._walls_key,
        )

    def get_legal_actions(self, player_id: int | None = None) -> list[Action]:
        """Return all 6 actions if non-terminal, or [] on terminal states."""
        if self.is_terminal():
            return []
        return list(ALL_ACTIONS)

    def is_terminal(self) -> bool:
        """Return True if any tank/base is destroyed or turn limit is reached."""
        t1 = self.tanks.get(1)
        t2 = self.tanks.get(2)
        b1 = self.bases.get(1)
        b2 = self.bases.get(2)
        if (
            t1 is None
            or not t1.is_alive()
            or t2 is None
            or not t2.is_alive()
            or b1 is None
            or not b1.is_alive()
            or b2 is None
            or not b2.is_alive()
        ):
            return True
        return self.turn_count >= self.max_turns

    def get_winner(self) -> int | None:
        """Return 1 or 2 for winner, 0 for draw/mutual loss, or None if ongoing."""
        t1 = self.tanks.get(1)
        t2 = self.tanks.get(2)
        b1 = self.bases.get(1)
        b2 = self.bases.get(2)

        p1_alive = t1 is not None and t1.is_alive() and b1 is not None and b1.is_alive()
        p2_alive = t2 is not None and t2.is_alive() and b2 is not None and b2.is_alive()

        if p1_alive and not p2_alive:
            return 1
        if p2_alive and not p1_alive:
            return 2
        if not p1_alive and not p2_alive:
            return 0
        if self.turn_count >= self.max_turns:
            return 0
        return None

    def get_utility(self, max_player_id: int) -> float:
        """Return terminal utility adjusted by turn_count to prefer faster wins."""
        if max_player_id not in (1, 2):
            raise ValueError(f"max_player_id must be 1 or 2, got {max_player_id!r}")
        opp_id = 3 - max_player_id
        winner = self.get_winner()
        if winner == max_player_id:
            return UTILITY_WIN - float(self.turn_count)
        if winner == opp_id:
            return UTILITY_LOSS + float(self.turn_count)
        return UTILITY_DRAW

    def state_key(self) -> tuple:
        """Return an immutable hashable key uniquely identifying board state and turn."""
        t1 = self.tanks.get(1)
        t2 = self.tanks.get(2)
        b1 = self.bases.get(1)
        b2 = self.bases.get(2)
        return (
            (t1.x, t1.y, t1.direction.value, t1.hp) if t1 is not None else None,
            (t2.x, t2.y, t2.direction.value, t2.hp) if t2 is not None else None,
            b1.hp if b1 is not None else None,
            b2.hp if b2 is not None else None,
            self.walls_key(),
            self.current_turn,
        )

    @classmethod
    def from_text(cls, text: str, max_turns: int = MAX_TURNS) -> GameState:
        """Parse and validate a 13x13 ASCII map string into a GameState."""
        if not isinstance(text, str):
            raise ValueError("Map text must be a string.")
        if max_turns < 1:
            raise ValueError(f"max_turns must be >= 1, got {max_turns}")

        raw = text.strip("\r\n")
        if not raw:
            raise ValueError("Map text cannot be empty.")

        lines = [line.strip() for line in raw.splitlines()]
        if len(lines) != GRID_HEIGHT:
            raise ValueError(f"Expected {GRID_HEIGHT} map rows, got {len(lines)}.")

        tanks: dict[int, Tank] = {}
        bases: dict[int, Base] = {}
        walls: dict[tuple[int, int], int] = {}

        for y, line in enumerate(lines):
            if len(line) != GRID_WIDTH:
                raise ValueError(
                    f"Map row {y} must have length {GRID_WIDTH}, got {len(line)}."
                )
            for x, ch in enumerate(line):
                if ch not in _VALID_MAP_CHARS:
                    raise ValueError(f"Invalid map character {ch!r} at ({x}, {y}).")
                if ch == "W":
                    walls[(x, y)] = WALL_INITIAL_HP
                elif ch == "w":
                    walls[(x, y)] = WEAK_WALL_INITIAL_HP
                elif ch == "1":
                    if 1 in tanks:
                        raise ValueError("Duplicate Tank 1 ('1') in map.")
                    tanks[1] = Tank(
                        x=x,
                        y=y,
                        player_id=1,
                        direction=Direction.DOWN,
                        hp=TANK_INITIAL_HP,
                        max_hp=TANK_INITIAL_HP,
                    )
                elif ch == "2":
                    if 2 in tanks:
                        raise ValueError("Duplicate Tank 2 ('2') in map.")
                    tanks[2] = Tank(
                        x=x,
                        y=y,
                        player_id=2,
                        direction=Direction.UP,
                        hp=TANK_INITIAL_HP,
                        max_hp=TANK_INITIAL_HP,
                    )
                elif ch == "A":
                    if 1 in bases:
                        raise ValueError("Duplicate Base 1 ('A') in map.")
                    bases[1] = Base(
                        x=x,
                        y=y,
                        player_id=1,
                        hp=BASE_INITIAL_HP,
                        max_hp=BASE_INITIAL_HP,
                    )
                elif ch == "B":
                    if 2 in bases:
                        raise ValueError("Duplicate Base 2 ('B') in map.")
                    bases[2] = Base(
                        x=x,
                        y=y,
                        player_id=2,
                        hp=BASE_INITIAL_HP,
                        max_hp=BASE_INITIAL_HP,
                    )

        missing: list[str] = []
        if 1 not in tanks:
            missing.append("1")
        if 2 not in tanks:
            missing.append("2")
        if 1 not in bases:
            missing.append("A")
        if 2 not in bases:
            missing.append("B")
        if missing:
            raise ValueError(f"Map is missing required entities: {', '.join(missing)}.")

        return cls(
            tanks=tanks,
            bases=bases,
            walls=walls,
            bullets=[],
            width=GRID_WIDTH,
            height=GRID_HEIGHT,
            current_turn=1,
            turn_count=0,
            max_turns=max_turns,
        )

    @classmethod
    def from_file(cls, path: str | Path, max_turns: int = MAX_TURNS) -> GameState:
        """Load and validate a map file from disk using pathlib.Path."""
        file_path = Path(path)
        if not file_path.is_file():
            raise FileNotFoundError(f"Map file not found: {file_path}")
        content = file_path.read_text(encoding="utf-8")
        return cls.from_text(content, max_turns=max_turns)

    def to_ascii(self) -> str:
        """Render current grid state back to a 13x13 ASCII string for debugging."""
        grid = [["." for _ in range(self.width)] for _ in range(self.height)]
        for (wx, wy), hp in self.walls.items():
            if self.in_bounds(wx, wy):
                grid[wy][wx] = "W" if hp > 1 else "w"
        for pid, symbol in ((1, "A"), (2, "B")):
            base = self.bases.get(pid)
            if base is not None and base.is_alive():
                grid[base.y][base.x] = symbol
        for pid, symbol in ((1, "1"), (2, "2")):
            tank = self.tanks.get(pid)
            if tank is not None and tank.is_alive():
                grid[tank.y][tank.x] = symbol
        return "\n".join("".join(row) for row in grid)

    def __str__(self) -> str:
        return (
            f"GameState(turn={self.turn_count}/{self.max_turns}, "
            f"current_turn=P{self.current_turn})\n{self.to_ascii()}"
        )
