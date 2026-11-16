"""Config 1: Pure Minimax search agent using basic HP evaluation."""

from __future__ import annotations

import math

from source.task2.agents.base_agent import BaseAgent
from source.task2.agents.heuristics import basic_evaluate, ordered_actions_basic
from source.task2.core.actions import Action
from source.task2.core.game_engine import GameEngine
from source.task2.core.game_state import GameState


class MinimaxAgent(BaseAgent):
    """Pure Minimax adversarial search without Alpha-Beta pruning."""

    def __init__(
        self,
        player_id: int,
        depth: int = 3,
        name: str = "MinimaxAgent",
    ) -> None:
        super().__init__(player_id=player_id, depth=depth, name=name)
        self._run_max_depth: int = 0

    def _evaluate(self, state: GameState) -> float:
        """Evaluate leaf or terminal state (overridden by HeuristicMinimaxAgent)."""
        return basic_evaluate(state, self.player_id)

    def _get_actions(self, state: GameState) -> list[Action]:
        """Return ordered actions (overridden by HeuristicMinimaxAgent)."""
        return ordered_actions_basic(state)

    def get_action(self, state: GameState) -> Action:
        """Select optimal action via exhaustive fixed-depth Minimax search."""
        start_time = self._begin_search()
        self._run_max_depth = 0

        if state.is_terminal():
            self._end_search(start_time, 0)
            return Action.STAY

        maximizing = state.current_turn == self.player_id
        _, best_action = self._minimax(state, self.depth, maximizing, ply=0)
        self._end_search(start_time, self._run_max_depth)
        return best_action if best_action is not None else Action.STAY

    def _minimax(
        self,
        state: GameState,
        depth: int,
        maximizing: bool,
        ply: int,
    ) -> tuple[float, Action | None]:
        """Recursively compute exact Minimax value and best action."""
        self.nodes_explored += 1
        if ply > self._run_max_depth:
            self._run_max_depth = ply

        if depth == 0 or state.is_terminal():
            return self._evaluate(state), None

        actions = self._get_actions(state)
        if not actions:
            return self._evaluate(state), None

        best_action = actions[0]
        if maximizing:
            best_val = -math.inf
            for action in actions:
                child = GameEngine.apply_action(state, action)
                val, _ = self._minimax(child, depth - 1, False, ply + 1)
                if val > best_val:
                    best_val = val
                    best_action = action
            return best_val, best_action

        best_val = math.inf
        for action in actions:
            child = GameEngine.apply_action(state, action)
            val, _ = self._minimax(child, depth - 1, True, ply + 1)
            if val < best_val:
                best_val = val
                best_action = action
        return best_val, best_action
