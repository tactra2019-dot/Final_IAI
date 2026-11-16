"""Headless state transition engine for Tank Battle."""

from __future__ import annotations

from task2.core.actions import ACTION_TO_DIRECTION, Action
from task2.core.constants import BULLET_DAMAGE, BULLET_SPEED
from task2.core.entities import Bullet, Tank
from task2.core.game_state import GameState


class GameEngine:
    """Stateless transition engine enforcing movement and cell-by-cell bullet rules."""

    @staticmethod
    def apply_action(state: GameState, action: Action) -> GameState:
        """Validate action, transition state immutably via clone(), and switch turn."""
        if not isinstance(action, Action):
            raise ValueError(f"action must be an Action enum member, got {action!r}")

        if state.is_terminal():
            return state.clone()

        next_state = state.clone()
        next_state.last_action = action
        next_state.last_bullet_path = []
        next_state.last_hit_pos = None
        next_state.last_hit_kind = None

        player_id = next_state.current_turn
        tank = next_state.tanks.get(player_id)
        if tank is None or not tank.is_alive():
            return next_state

        direction = ACTION_TO_DIRECTION.get(action)
        if direction is not None:
            # Tank always updates facing direction even if movement is blocked.
            tank.direction = direction
            nx = tank.x + direction.dx
            ny = tank.y + direction.dy
            if GameEngine._is_cell_passable(next_state, nx, ny):
                tank.x = nx
                tank.y = ny
        elif action is Action.FIRE:
            GameEngine._process_bullet_fire(next_state, tank)
        elif action is Action.STAY:
            pass

        next_state.turn_count += 1
        next_state.current_turn = 3 - player_id
        return next_state

    @staticmethod
    def _is_cell_passable(state: GameState, x: int, y: int) -> bool:
        """Return True when (x, y) is inside bounds and free of walls, tanks, and bases."""
        if not state.in_bounds(x, y):
            return False
        if (x, y) in state.walls:
            return False
        for tank in state.tanks.values():
            if tank.is_alive() and tank.x == x and tank.y == y:
                return False
        for base in state.bases.values():
            if base.is_alive() and base.x == x and base.y == y:
                return False
        return True

    @staticmethod
    def _process_bullet_fire(state: GameState, tank: Tank) -> None:
        """Simulate bullet traveling up to 3 cells with cell-by-cell collision checks."""
        bullet = Bullet(
            x=tank.x,
            y=tank.y,
            direction=tank.direction,
            owner_id=tank.player_id,
            speed=BULLET_SPEED,
        )

        for _ in range(bullet.speed):
            bx, by = bullet.step_one_cell()
            if not state.in_bounds(bx, by):
                break

            state.last_bullet_path.append((bx, by))

            if (bx, by) in state.walls:
                state.walls[(bx, by)] -= BULLET_DAMAGE
                if state.walls[(bx, by)] <= 0:
                    del state.walls[(bx, by)]
                state._walls_key = None
                state.last_hit_pos = (bx, by)
                state.last_hit_kind = "wall"
                break

            hit_tank = False
            for target_tank in state.tanks.values():
                if target_tank.is_alive() and target_tank.x == bx and target_tank.y == by:
                    target_tank.take_damage(BULLET_DAMAGE)
                    state.last_hit_pos = (bx, by)
                    state.last_hit_kind = "tank"
                    hit_tank = True
                    break
            if hit_tank:
                break

            hit_base = False
            for base in state.bases.values():
                if base.is_alive() and base.x == bx and base.y == by:
                    base.take_damage(BULLET_DAMAGE)
                    state.last_hit_pos = (bx, by)
                    state.last_hit_kind = "base"
                    hit_base = True
                    break
            if hit_base:
                break
