"""Config 2: Pure Alpha-Beta Pruning agent using basic HP evaluation."""

from __future__ import annotations

import math

from source.task2.agents.base_agent import BaseAgent
from source.task2.agents.heuristics import basic_evaluate, ordered_actions_basic
from source.task2.core.actions import Action
from source.task2.core.game_engine import GameEngine
from source.task2.core.game_state import GameState


class AlphaBetaAgent(BaseAgent):
    """Alpha-Beta search with identical move ordering and eval to MinimaxAgent."""

    def __init__(
        self,
        player_id: int,
        depth: int = 3,
        name: str = "AlphaBetaAgent",
    ) -> None:
        super().__init__(player_id=player_id, depth=depth, name=name)
        self._run_max_depth: int = 0

    def get_action(self, state: GameState) -> Action:
        """Select optimal action via Alpha-Beta pruning over fixed ALL_ACTIONS order."""
        start_time = self._begin_search()
        self._run_max_depth = 0

        if state.is_terminal():
            self._end_search(start_time, 0)
            return Action.STAY

        maximizing = state.current_turn == self.player_id
        _, best_action = self._alphabeta(
            state,
            self.depth,
            -math.inf,
            math.inf,
            maximizing,
            ply=0,
        )
        self._end_search(start_time, self._run_max_depth)
        return best_action if best_action is not None else Action.STAY

    def _alphabeta(
        self,
        state: GameState,
        depth: int,
        alpha: float,
        beta: float,
        maximizing: bool,
        ply: int,
    ) -> tuple[float, Action | None]:
        """Recursively compute Alpha-Beta pruned Minimax value and best action."""
        self.nodes_explored += 1
        if ply > self._run_max_depth:
            self._run_max_depth = ply

        if depth == 0 or state.is_terminal():
            return basic_evaluate(state, self.player_id), None

        actions = ordered_actions_basic(state)
        if not actions:
            return basic_evaluate(state, self.player_id), None

        best_action = actions[0]
        total_actions = len(actions)

        if maximizing:
            best_val = -math.inf
            for idx, action in enumerate(actions):
                child = GameEngine.apply_action(state, action)
                val, _ = self._alphabeta(child, depth - 1, alpha, beta, False, ply + 1)
                if val > best_val:
                    best_val = val
                    best_action = action
                if best_val > alpha:
                    alpha = best_val
                if beta <= alpha:
                    remaining = total_actions - 1 - idx
                    if remaining > 0:
                        self.pruned_branches += remaining
                    break
            return best_val, best_action

        best_val = math.inf
        for idx, action in enumerate(actions):
            child = GameEngine.apply_action(state, action)
            val, _ = self._alphabeta(child, depth - 1, alpha, beta, True, ply + 1)
            if val < best_val:
                best_val = val
                best_action = action
            if best_val < beta:
                beta = best_val
            if beta <= alpha:
                remaining = total_actions - 1 - idx
                if remaining > 0:
                    self.pruned_branches += remaining
                break
        return best_val, best_action
