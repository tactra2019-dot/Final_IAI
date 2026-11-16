"""Sample external plugin agent demonstrating the BaseAgent contract."""

from __future__ import annotations

from source.task2.agents.base_agent import BaseAgent
from source.task2.agents.heuristics import (
    _is_in_firing_lane,
    _trace_first_hit,
    is_cell_passable,
    weighted_grid_distance,
)
from source.task2.core.actions import ACTION_TO_DIRECTION, Action
from source.task2.core.constants import BULLET_SPEED
from source.task2.core.game_state import GameState


class GreedyShooterAgent(BaseAgent):
    """Lightweight rule-based external opponent that prioritizes aligned shots and dodging."""

    def __init__(
        self,
        player_id: int,
        depth: int = 1,
        name: str = "GreedyShooterAgent",
    ) -> None:
        super().__init__(player_id=player_id, depth=max(1, depth), name=name)

    def get_action(self, state: GameState) -> Action:
        """Choose immediate greedy tactical action with wall-aware distance and dodging."""
        start_time = self._begin_search()
        self.nodes_explored = 1

        if state.is_terminal():
            self._end_search(start_time, 1)
            return Action.STAY

        opp_id = 3 - self.player_id
        tank = state.tanks[self.player_id]
        opp_tank = state.tanks[opp_id]
        opp_base = state.bases[opp_id]

        # 1. Fire immediately if aligned with enemy tank or enemy base within 3 cells.
        hit_kind, hit_pos, _ = _trace_first_hit(
            state, tank.x, tank.y, tank.direction, BULLET_SPEED
        )
        if hit_kind in (f"tank_{opp_id}", f"base_{opp_id}"):
            self._end_search(start_time, 1)
            return Action.FIRE

        # 2. Pick closer target via wall-aware shortest path and score candidates.
        in_danger = _is_in_firing_lane(state, opp_tank, tank.pos, BULLET_SPEED)
        d_base_w = weighted_grid_distance(state, tank.pos, opp_base.pos)
        d_tank_w = weighted_grid_distance(state, tank.pos, opp_tank.pos)
        target = opp_base if d_base_w < d_tank_w else opp_tank
        cur_dist = min(d_base_w, d_tank_w)

        best_action = Action.STAY
        best_score = -40.0 if in_danger else -5.0

        # Score shooting a wall directly ahead when safe, favoring 1-HP walls toward target.
        if hit_kind == "wall" and hit_pos is not None:
            wall_hp = state.walls.get(hit_pos, 3)
            toward_target = (
                (hit_pos[0] - tank.x) * (target.x - tank.x)
                + (hit_pos[1] - tank.y) * (target.y - tank.y)
                > 0
            )
            if in_danger:
                fire_score = -25.0
            elif toward_target:
                fire_score = 4.5 if wall_hp == 1 else (2.0 if wall_hp == 2 else 1.5)
            else:
                fire_score = 0.5
            if fire_score > best_score:
                best_score = fire_score
                best_action = Action.FIRE

        for action, direction in ACTION_TO_DIRECTION.items():
            nx = tank.x + direction.dx
            ny = tank.y + direction.dy
            if not is_cell_passable(state, nx, ny):
                # Pure same-direction wall/edge slam is a no-op; keep strictly below STAY.
                if tank.direction == direction:
                    score = -90.0
                else:
                    turn_hit, _, _ = _trace_first_hit(
                        state, tank.x, tank.y, direction, BULLET_SPEED
                    )
                    if turn_hit in (f"tank_{opp_id}", f"base_{opp_id}"):
                        score = 15.0
                    elif (
                        turn_hit == "wall"
                        and not in_danger
                        and (target.x - tank.x) * direction.dx
                        + (target.y - tank.y) * direction.dy
                        > 0
                    ):
                        score = 2.0
                    else:
                        score = -30.0
            else:
                next_dist = weighted_grid_distance(state, (nx, ny), target.pos)
                next_base_w = weighted_grid_distance(state, (nx, ny), opp_base.pos)
                # Secondary base pull breaks symmetric detour ties around brick pockets.
                score = 2.5 * float(cur_dist - next_dist) + 0.1 * float(d_base_w - next_base_w)
                if in_danger and not _is_in_firing_lane(
                    state, opp_tank, (nx, ny), BULLET_SPEED
                ):
                    score += 40.0
                elif not in_danger and _is_in_firing_lane(
                    state, opp_tank, (nx, ny), BULLET_SPEED
                ):
                    score -= 30.0

            if score > best_score:
                best_score = score
                best_action = action

        self._end_search(start_time, 1)
        return best_action
