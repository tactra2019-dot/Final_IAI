"""Config 3: Heuristic Minimax search without Alpha-Beta pruning."""

from __future__ import annotations

from task2.agents.heuristics import order_moves, tactical_evaluate
from task2.agents.minimax_agent import MinimaxAgent
from task2.core.actions import Action
from task2.core.game_state import GameState


class HeuristicMinimaxAgent(MinimaxAgent):
    """Minimax search enhanced with 5-component tactical heuristic evaluation."""

    def __init__(
        self,
        player_id: int,
        depth: int = 3,
        name: str = "HeuristicMinimaxAgent",
    ) -> None:
        super().__init__(player_id=player_id, depth=depth, name=name)

    def _evaluate(self, state: GameState) -> float:
        """Evaluate non-terminal and terminal states using tactical_evaluate."""
        return tactical_evaluate(state, self.player_id)

    def _get_actions(self, state: GameState) -> list[Action]:
        """Use the same tactical move ordering as HeuristicAlphaBetaAgent for parity."""
        return order_moves(state, state.get_legal_actions(), state.current_turn)
