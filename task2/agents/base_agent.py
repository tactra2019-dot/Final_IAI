"""Abstract base agent and shared search metrics tracking."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from task2.core.actions import Action
from task2.core.game_state import GameState


class BaseAgent(ABC):
    """Abstract base class for all Tank Battle AI agents and external plugins."""

    def __init__(
        self,
        player_id: int,
        depth: int = 3,
        name: str = "BaseAgent",
    ) -> None:
        if player_id not in (1, 2):
            raise ValueError(f"player_id must be 1 or 2, got {player_id!r}")
        if depth < 1:
            raise ValueError(f"depth must be >= 1, got {depth!r}")
        self.player_id: int = player_id
        self.depth: int = depth
        self.name: str = name
        self.nodes_explored: int = 0
        self.total_nodes_explored: int = 0
        self.max_depth_reached: int = 0
        self.last_time_ms: float = 0.0
        self.total_time_ms: float = 0.0
        self.move_count: int = 0
        self.pruned_branches: int = 0

    @abstractmethod
    def get_action(self, state: GameState) -> Action:
        """Choose an Action for the current player given a GameState."""

    def reset_stats(self) -> None:
        """Reset all per-move and cumulative search performance counters."""
        self.nodes_explored = 0
        self.total_nodes_explored = 0
        self.max_depth_reached = 0
        self.last_time_ms = 0.0
        self.total_time_ms = 0.0
        self.move_count = 0
        self.pruned_branches = 0

    @property
    def avg_time_ms(self) -> float:
        """Return average decision latency per move in milliseconds."""
        return self.total_time_ms / self.move_count if self.move_count > 0 else 0.0

    def _begin_search(self) -> float:
        """Reset per-move node counter and return high-resolution start timestamp."""
        self.nodes_explored = 0
        return time.perf_counter()

    def _end_search(self, start_time: float, depth_reached: int = 0) -> None:
        """Record elapsed decision time, node totals, move count, and depth."""
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        self.last_time_ms = elapsed_ms
        self.total_time_ms += elapsed_ms
        self.total_nodes_explored += self.nodes_explored
        self.move_count += 1
        if depth_reached > self.max_depth_reached:
            self.max_depth_reached = depth_reached

    def get_metrics(self) -> dict[str, object]:
        """Return structured telemetry metrics for UI and benchmark reporting."""
        nodes_per_move = (
            self.total_nodes_explored / self.move_count if self.move_count > 0 else 0.0
        )
        return {
            "name": self.name,
            "player_id": self.player_id,
            "depth": self.depth,
            "nodes_explored": self.nodes_explored,
            "total_nodes_explored": self.total_nodes_explored,
            "nodes_per_move": nodes_per_move,
            "max_depth_reached": self.max_depth_reached,
            "last_time_ms": self.last_time_ms,
            "total_time_ms": self.total_time_ms,
            "avg_time_ms": self.avg_time_ms,
            "move_count": self.move_count,
            "pruned_branches": self.pruned_branches,
        }
