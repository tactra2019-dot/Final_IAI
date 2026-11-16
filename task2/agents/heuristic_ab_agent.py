"""Config 4: Heuristic Alpha-Beta search with move ordering and transposition table."""

from __future__ import annotations

import math

from task2.agents.base_agent import BaseAgent
from task2.agents.heuristics import order_moves, tactical_evaluate
from task2.core.actions import Action
from task2.core.game_engine import GameEngine
from task2.core.game_state import GameState


class HeuristicAlphaBetaAgent(BaseAgent):
    """Optimized Alpha-Beta agent with tactical eval, move ordering, and TT."""

    def __init__(
        self,
        player_id: int,
        depth: int = 3,
        name: str = "HeuristicAlphaBetaAgent",
    ) -> None:
        super().__init__(player_id=player_id, depth=depth, name=name)
        self.transposition_table: dict[tuple, tuple[float, str, Action | None]] = {}
        self._run_max_depth: int = 0

    def reset_stats(self) -> None:
        """Reset search metrics and clear cached transposition entries."""
        super().reset_stats()
        self.transposition_table.clear()

    def get_action(self, state: GameState) -> Action:
        """Select optimal tactical action using Alpha-Beta, move ordering, and TT."""
        start_time = self._begin_search()
        self._run_max_depth = 0
        # Clear TT per move so turn_count-dependent terminal utilities stay exact.
        self.transposition_table.clear()

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
        """Recursively search with Alpha-Beta bounds, TT lookup, and move ordering."""
        self.nodes_explored += 1
        if ply > self._run_max_depth:
            self._run_max_depth = ply

        if depth == 0 or state.is_terminal():
            return tactical_evaluate(state, self.player_id), None

        orig_alpha = alpha
        orig_beta = beta
        tt_key = (state.state_key(), depth, maximizing)
        entry = self.transposition_table.get(tt_key)
        tt_best_action: Action | None = None

        if entry is not None:
            cached_val, flag, tt_best_action = entry
            if flag == "EXACT":
                return cached_val, tt_best_action
            if flag == "LOWER":
                alpha = max(alpha, cached_val)
            elif flag == "UPPER":
                beta = min(beta, cached_val)
            if alpha >= beta:
                self.pruned_branches += 1
                return cached_val, tt_best_action

        legal_actions = state.get_legal_actions()
        if not legal_actions:
            return tactical_evaluate(state, self.player_id), None

        actions = order_moves(state, legal_actions, state.current_turn)
        if tt_best_action is not None and tt_best_action in actions:
            actions.remove(tt_best_action)
            actions.insert(0, tt_best_action)

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
        else:
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

        if best_val <= orig_alpha:
            flag = "UPPER"
        elif best_val >= orig_beta:
            flag = "LOWER"
        else:
            flag = "EXACT"
        self.transposition_table[tt_key] = (best_val, flag, best_action)
        return best_val, best_action
