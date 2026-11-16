"""Evaluation functions and tactical move ordering for Tank Battle agents."""

from __future__ import annotations

import heapq
import math
from functools import lru_cache

from task2.core.actions import ACTION_TO_DIRECTION, Action, Direction
from task2.core.constants import BULLET_SPEED
from task2.core.entities import Base, Tank
from task2.core.game_state import GameState

W_TANK_HP: float = 150.0
W_BASE_HP: float = 220.0
W_LINE_OF_SIGHT: float = 60.0
W_POSITIONAL: float = 15.0
W_BULLET_DANGER: float = 120.0


def _axis_wall_penalty(
    state: GameState,
    x: int,
    y: int,
    tx: int,
    ty: int,
    weights: tuple[tuple[int, float], ...],
) -> float:
    """Penalize walls along the primary Manhattan axis from (x, y) toward (tx, ty)."""
    dx, dy = tx - x, ty - y
    if abs(dy) >= abs(dx) and dy != 0:
        pdx, pdy = 0, (1 if dy > 0 else -1)
    elif dx != 0:
        pdx, pdy = (1 if dx > 0 else -1), 0
    else:
        return 0.0
    penalty = 0.0
    for step, weight in weights:
        wall_hp = state.walls.get((x + pdx * step, y + pdy * step))
        if wall_hp is not None:
            penalty += weight * float(wall_hp)
    return penalty


def _basic_side_score(
    state: GameState,
    tank: Tank,
    my_base: Base,
    opp_tank: Tank,
    opp_base: Base,
    player_id: int,
    opp_id: int,
) -> float:
    """Compute one side's spatial, defense, firing-lane danger, and aiming contribution."""
    d_opp_base = abs(tank.x - opp_base.x) + abs(tank.y - opp_base.y)
    score = -2.5 * float(d_opp_base)

    # Firing-lane danger penalties prevent 3-ply horizon blindness near 1-HP threats
    # while keeping full-HP advances (>2.5 step gain) unblocked.
    opp_turn_next = state.current_turn == opp_id
    if _is_in_firing_lane(state, opp_tank, tank.pos, BULLET_SPEED):
        if tank.hp == 1:
            score -= 500.0 if opp_turn_next else 35.0
        elif tank.hp == 2:
            score -= 15.0 if opp_turn_next else 5.0
        else:
            score -= 1.8 if opp_turn_next else 0.6
    if _is_in_firing_lane(state, opp_tank, my_base.pos, BULLET_SPEED):
        score -= 90.0 if opp_turn_next else 45.0

    # Wall-aware base-defense intercept and tactical alignment when enemy nears own base.
    d_tanks = abs(tank.x - opp_tank.x) + abs(tank.y - opp_tank.y)
    opp_to_my_base = abs(opp_tank.x - my_base.x) + abs(opp_tank.y - my_base.y)
    if opp_to_my_base <= 5:
        urgency = float(6 - opp_to_my_base) / 5.0
        w_tanks = weighted_grid_distance(state, tank.pos, opp_tank.pos)
        score -= 2.0 * urgency * float(w_tanks)
        if tank.x == opp_tank.x or tank.y == opp_tank.y:
            tdx, tdy = tank.direction.value
            if (opp_tank.x - tank.x) * tdx + (opp_tank.y - tank.y) * tdy > 0:
                score += 1.5 * urgency
    if d_tanks <= 5:
        score -= _axis_wall_penalty(
            state, tank.x, tank.y, opp_tank.x, opp_tank.y, ((1, 0.45), (2, 0.30), (3, 0.22))
        )

    # Bounded wall-breach progress along primary axis toward enemy base (sum <= 1.95 < 2.5).
    dx_b = opp_base.x - tank.x
    dy_b = opp_base.y - tank.y
    score -= _axis_wall_penalty(
        state, tank.x, tank.y, opp_base.x, opp_base.y, ((1, 0.65), (2, 0.45), (3, 0.25))
    )

    # Reward breaching protective walls around enemy base (using cached walls_key).
    shield_hp = 0
    for (wx, wy), hp in state.walls_key():
        if abs(wx - opp_base.x) + abs(wy - opp_base.y) <= 2:
            shield_hp += hp
    score -= 0.7 * float(shield_hp)

    # Aiming micro-bonus along current barrel ray within BULLET_SPEED.
    hit_kind, hit_pos, _ = _trace_first_hit(
        state, tank.x, tank.y, tank.direction, BULLET_SPEED
    )
    if hit_kind == f"tank_{opp_id}" or hit_kind == f"base_{opp_id}":
        score += 3.5
    elif hit_kind == f"base_{player_id}":
        score -= 4.0
    elif hit_kind == "wall" and hit_pos is not None:
        wx, wy = hit_pos
        toward_enemy = (
            (wx - tank.x) * dx_b + (wy - tank.y) * dy_b > 0
            or (wx - tank.x) * (opp_tank.x - tank.x) + (wy - tank.y) * (opp_tank.y - tank.y) > 0
        )
        if toward_enemy:
            # Stay below smallest step wall weight (0.22) so clearing walls always beats staying.
            score += 0.2

    # Mild facing alignment toward enemy base or tank.
    fdx, fdy = tank.direction.value
    if (
        dx_b * fdx + dy_b * fdy > 0
        or (opp_tank.x - tank.x) * fdx + (opp_tank.y - tank.y) * fdy > 0
    ):
        score += 0.8

    return score


def basic_evaluate(state: GameState, max_player_id: int) -> float:
    """Evaluate terminal utility or HP difference with lightweight spatial/aiming gradient."""
    if state.is_terminal():
        return state.get_utility(max_player_id)

    opp_id = 3 - max_player_id
    my_tank = state.tanks[max_player_id]
    opp_tank = state.tanks[opp_id]
    my_base = state.bases[max_player_id]
    opp_base = state.bases[opp_id]

    hp_score = (
        W_TANK_HP * float(my_tank.hp - opp_tank.hp)
        + W_BASE_HP * float(my_base.hp - opp_base.hp)
    )
    my_pos = _basic_side_score(
        state, my_tank, my_base, opp_tank, opp_base, max_player_id, opp_id
    )
    opp_pos = _basic_side_score(
        state, opp_tank, opp_base, my_tank, my_base, opp_id, max_player_id
    )
    return hp_score + (my_pos - opp_pos)


def _trace_first_hit(
    state: GameState,
    x: int,
    y: int,
    direction: Direction,
    max_steps: int,
) -> tuple[str | None, tuple[int, int] | None, int]:
    """Trace a ray cell-by-cell and return (hit_kind, pos, step_distance)."""
    dx, dy = direction.value
    cx, cy = x, y
    for step in range(1, max_steps + 1):
        cx += dx
        cy += dy
        if not state.in_bounds(cx, cy):
            break
        if (cx, cy) in state.walls:
            return ("wall", (cx, cy), step)
        for pid, tank in state.tanks.items():
            if tank.is_alive() and tank.x == cx and tank.y == cy:
                return (f"tank_{pid}", (cx, cy), step)
        for pid, base in state.bases.items():
            if base.is_alive() and base.x == cx and base.y == cy:
                return (f"base_{pid}", (cx, cy), step)
    return (None, None, 0)


def _is_in_firing_lane(
    state: GameState,
    shooter: Tank,
    target_pos: tuple[int, int],
    max_range: int = BULLET_SPEED,
) -> bool:
    """Return True if shooter can hit target_pos unobstructed along shooter.direction."""
    dx, dy = shooter.direction.value
    cx, cy = shooter.x, shooter.y
    for _ in range(max_range):
        cx += dx
        cy += dy
        if not state.in_bounds(cx, cy):
            return False
        if (cx, cy) == target_pos:
            return True
        if (cx, cy) in state.walls:
            return False
        for tank in state.tanks.values():
            if tank.is_alive() and (tank.x, tank.y) == (cx, cy):
                return False
        for base in state.bases.values():
            if base.is_alive() and (base.x, base.y) == (cx, cy):
                return False
    return False


def _is_unobstructed_aligned(
    state: GameState,
    src: tuple[int, int],
    dst: tuple[int, int],
    max_range: int = BULLET_SPEED,
) -> bool:
    """Return True if src and dst share a row or column within max_range without intervening walls."""
    sx, sy = src
    tx, ty = dst
    if sx != tx and sy != ty:
        return False
    dist = abs(tx - sx) + abs(ty - sy)
    if dist < 1 or dist > max_range:
        return False
    step_dx = 0 if sx == tx else (1 if tx > sx else -1)
    step_dy = 0 if sy == ty else (1 if ty > sy else -1)
    cx, cy = sx + step_dx, sy + step_dy
    while (cx, cy) != (tx, ty):
        if (cx, cy) in state.walls:
            return False
        cx += step_dx
        cy += step_dy
    return True


def _line_of_sight_for_player(
    state: GameState,
    tank: Tank,
    opp_tank: Tank,
    opp_base: Base,
    player_id: int,
) -> float:
    """Compute offensive line-of-sight alignment score for one tank."""
    opp_id = 3 - player_id
    # Suppress phantom LoS when 1-HP tank is already in lethal line on opponent's turn.
    if (
        state.current_turn == opp_id
        and tank.hp == 1
        and _is_in_firing_lane(state, opp_tank, tank.pos, BULLET_SPEED)
    ):
        return 0.0

    score = 0.0

    # Immediate 3-cell firing ray along current barrel direction.
    hit_kind, _, _ = _trace_first_hit(
        state, tank.x, tank.y, tank.direction, BULLET_SPEED
    )
    if hit_kind == f"tank_{opp_id}":
        score += 1.4
    elif hit_kind == f"base_{opp_id}":
        score += 1.7

    # Unobstructed same-row/col alignment within 3-cell firing range.
    if _is_unobstructed_aligned(state, tank.pos, opp_base.pos, BULLET_SPEED):
        score += 0.70
    if _is_unobstructed_aligned(state, tank.pos, opp_tank.pos, BULLET_SPEED):
        score += 0.55

    # Mild bonus for aiming in the general direction of enemy targets (kept < 1 step gain).
    dx, dy = tank.direction.value
    to_tank_dot = (opp_tank.x - tank.x) * dx + (opp_tank.y - tank.y) * dy
    to_base_dot = (opp_base.x - tank.x) * dx + (opp_base.y - tank.y) * dy
    if to_tank_dot > 0 or to_base_dot > 0:
        score += 0.06

    return score


@lru_cache(maxsize=8192)
def _weighted_base_distance(
    walls_tuple: tuple[tuple[tuple[int, int], int], ...],
    width: int,
    height: int,
    start: tuple[int, int],
    goal: tuple[int, int],
    blocker_pos: tuple[int, int] | None,
) -> int:
    """Compute wall- and tank-aware shortest path cost from start to goal on the grid."""
    size = width * height
    grid = [1] * size
    for (wx, wy), hp in walls_tuple:
        if 0 <= wx < width and 0 <= wy < height:
            grid[wy * width + wx] = 1 + hp * 2
    if blocker_pos is not None:
        bx, by = blocker_pos
        if 0 <= bx < width and 0 <= by < height:
            grid[by * width + bx] += 12

    dist = [9999] * size
    s_idx = start[1] * width + start[0]
    g_idx = goal[1] * width + goal[0]
    dist[s_idx] = 0
    pq: list[tuple[int, int]] = [(0, s_idx)]

    while pq:
        d, idx = heapq.heappop(pq)
        if d > dist[idx]:
            continue
        if idx == g_idx:
            return d
        x = idx % width
        y = idx // width
        if x > 0:
            ni = idx - 1
            nd = d + grid[ni]
            if nd < dist[ni]:
                dist[ni] = nd
                heapq.heappush(pq, (nd, ni))
        if x + 1 < width:
            ni = idx + 1
            nd = d + grid[ni]
            if nd < dist[ni]:
                dist[ni] = nd
                heapq.heappush(pq, (nd, ni))
        if y > 0:
            ni = idx - width
            nd = d + grid[ni]
            if nd < dist[ni]:
                dist[ni] = nd
                heapq.heappush(pq, (nd, ni))
        if y + 1 < height:
            ni = idx + width
            nd = d + grid[ni]
            if nd < dist[ni]:
                dist[ni] = nd
                heapq.heappush(pq, (nd, ni))

    return dist[g_idx]


def is_cell_passable(state: GameState, x: int, y: int) -> bool:
    """Return True if (x, y) is in bounds and free of walls, alive tanks, and alive bases."""
    if not state.in_bounds(x, y) or (x, y) in state.walls:
        return False
    if any(t.is_alive() and t.pos == (x, y) for t in state.tanks.values()):
        return False
    return not any(b.is_alive() and b.pos == (x, y) for b in state.bases.values())


def weighted_grid_distance(
    state: GameState,
    start: tuple[int, int],
    goal: tuple[int, int],
    blocker_pos: tuple[int, int] | None = None,
) -> int:
    """Compute wall- and optional blocker-aware shortest path cost on the state grid."""
    return _weighted_base_distance(
        state.walls_key(), state.width, state.height, start, goal, blocker_pos
    )


def _positional_score_for_player(
    state: GameState,
    walls_tuple: tuple[tuple[tuple[int, int], int], ...],
    tank: Tank,
    my_base: Base,
    opp_tank: Tank,
    opp_base: Base,
    avoid_opp: bool,
) -> float:
    """Compute path-distance attack pressure, wall-breach progress, and base defense urgency."""
    d_base = weighted_grid_distance(
        state,
        tank.pos,
        opp_base.pos,
        opp_tank.pos if avoid_opp else None,
    )
    eu_b = math.hypot(tank.x - opp_base.x, tank.y - opp_base.y)
    d_tank = abs(tank.x - opp_tank.x) + abs(tank.y - opp_tank.y)

    # Blend enemy-base pressure with subordinate enemy-tank proximity.
    pos_score = (
        32.0 / (2.0 + float(d_base))
        - 0.40 * float(d_base)
        + 4.0 / (2.0 + eu_b)
        + 2.5 / (3.0 + float(d_tank))
    )

    # Smooth progress for weakening enemy base defensive perimeter (dist <= 2).
    shield_hp = 0
    for (wx, wy), hp in walls_tuple:
        if abs(wx - opp_base.x) + abs(wy - opp_base.y) <= 2:
            shield_hp += hp
    pos_score -= 0.22 * float(shield_hp)

    # Base-defense intercept urgency when enemy tank threatens own base (dist <= 5).
    opp_to_my_base = abs(opp_tank.x - my_base.x) + abs(opp_tank.y - my_base.y)
    if opp_to_my_base <= 5:
        my_to_opp_base = abs(tank.x - opp_base.x) + abs(tank.y - opp_base.y)
        my_to_my_base = abs(tank.x - my_base.x) + abs(tank.y - my_base.y)
        urgency = float(6 - opp_to_my_base) / 4.0
        if opp_to_my_base <= my_to_opp_base:
            urgency += 0.45

        aligned = 0.0
        if tank.x == opp_tank.x or tank.y == opp_tank.y:
            tdx, tdy = tank.direction.value
            if (opp_tank.x - tank.x) * tdx + (opp_tank.y - tank.y) * tdy > 0:
                aligned = 0.8

        blocking_lane = (
            tank.x == opp_tank.x == my_base.x
            and min(opp_tank.y, my_base.y) < tank.y < max(opp_tank.y, my_base.y)
        ) or (
            tank.y == opp_tank.y == my_base.y
            and min(opp_tank.x, my_base.x) < tank.x < max(opp_tank.x, my_base.x)
        )
        guard = 0.0
        if blocking_lane:
            guard = 1.8
        elif (
            my_to_my_base <= 2
            and my_to_my_base <= opp_to_my_base
            and my_to_my_base + d_tank <= opp_to_my_base + 2
        ):
            guard = 1.2
        elif my_to_my_base > opp_to_my_base:
            guard = -0.9

        pos_score += urgency * (
            18.0 / (2.0 + float(d_tank)) - 0.55 * float(d_tank) + aligned + guard
        )

    return pos_score


def _bullet_danger_for_player(
    state: GameState,
    my_tank: Tank,
    my_base: Base,
    opp_tank: Tank,
    player_id: int,
) -> float:
    """Estimate immediate threat of taking a hit in the next enemy cycle."""
    opp_id = 3 - player_id
    danger = 0.0
    opp_turn_next = state.current_turn == opp_id

    if _is_in_firing_lane(state, opp_tank, my_tank.pos, BULLET_SPEED):
        if my_tank.hp == 1 and opp_turn_next:
            danger += 4.5
        else:
            danger += 1.0 if opp_turn_next else 0.45
    if _is_in_firing_lane(state, opp_tank, my_base.pos, BULLET_SPEED):
        danger += 1.65 if opp_turn_next else 0.85
    elif _is_unobstructed_aligned(state, opp_tank.pos, my_base.pos, BULLET_SPEED):
        danger += 0.45 if opp_turn_next else 0.30

    # Milder danger if enemy is within 3 cells on same row/col unobstructed.
    if danger == 0.0 and _is_unobstructed_aligned(
        state, opp_tank.pos, my_tank.pos, BULLET_SPEED
    ):
        danger += 0.55 if my_tank.hp == 1 else 0.25

    return danger


def tactical_evaluate(state: GameState, max_player_id: int) -> float:
    """Five-component tactical evaluation function for adversarial search."""
    if state.is_terminal():
        return state.get_utility(max_player_id)

    opp_id = 3 - max_player_id
    my_tank = state.tanks[max_player_id]
    opp_tank = state.tanks[opp_id]
    my_base = state.bases[max_player_id]
    opp_base = state.bases[opp_id]

    hp_tank_term = W_TANK_HP * float(my_tank.hp - opp_tank.hp)
    hp_base_term = W_BASE_HP * float(my_base.hp - opp_base.hp)

    my_los = _line_of_sight_for_player(state, my_tank, opp_tank, opp_base, max_player_id)
    opp_los = _line_of_sight_for_player(state, opp_tank, my_tank, my_base, opp_id)
    los_term = W_LINE_OF_SIGHT * (my_los - opp_los)

    walls_tuple = state.walls_key()
    my_pos = _positional_score_for_player(
        state, walls_tuple, my_tank, my_base, opp_tank, opp_base, avoid_opp=True
    )
    opp_pos = _positional_score_for_player(
        state, walls_tuple, opp_tank, opp_base, my_tank, my_base, avoid_opp=False
    )
    pos_term = W_POSITIONAL * (1.45 * my_pos - 0.55 * opp_pos)

    my_danger = _bullet_danger_for_player(state, my_tank, my_base, opp_tank, max_player_id)
    opp_danger = _bullet_danger_for_player(state, opp_tank, opp_base, my_tank, opp_id)
    danger_term = W_BULLET_DANGER * (my_danger - opp_danger)

    return hp_tank_term + hp_base_term + los_term + pos_term - danger_term


def ordered_actions_basic(state: GameState) -> list[Action]:
    """Keep ALL_ACTIONS order while demoting same-direction blocked no-op moves after STAY."""
    actions = state.get_legal_actions()
    if len(actions) <= 1:
        return actions

    tank = state.tanks[state.current_turn]
    active: list[Action] = []
    noops: list[Action] = []
    for action in actions:
        direction = ACTION_TO_DIRECTION.get(action)
        if (
            direction is not None
            and tank.direction == direction
            and not is_cell_passable(state, tank.x + direction.dx, tank.y + direction.dy)
        ):
            noops.append(action)
        else:
            active.append(action)
    return active + noops


def order_moves(
    state: GameState,
    actions: list[Action],
    player_id: int,
) -> list[Action]:
    """Order actions by tactical promise to maximize Alpha-Beta cutoff efficiency."""
    if len(actions) <= 1:
        return list(actions)

    opp_id = 3 - player_id
    tank = state.tanks[player_id]
    opp_tank = state.tanks[opp_id]
    opp_base = state.bases[opp_id]

    in_danger_now = _is_in_firing_lane(state, opp_tank, tank.pos, BULLET_SPEED)
    cur_dist = min(
        abs(tank.x - opp_tank.x) + abs(tank.y - opp_tank.y),
        abs(tank.x - opp_base.x) + abs(tank.y - opp_base.y),
    )

    scored: list[tuple[float, int, Action]] = []

    for idx, action in enumerate(actions):
        priority = 0.0
        if action is Action.FIRE:
            hit_kind, hit_pos, _ = _trace_first_hit(
                state, tank.x, tank.y, tank.direction, BULLET_SPEED
            )
            if hit_kind == f"tank_{opp_id}":
                priority = 120.0
            elif hit_kind == f"base_{opp_id}":
                priority = 110.0
            elif hit_kind == "wall" and hit_pos is not None:
                wx, wy = hit_pos
                toward_target = (
                    (wx - tank.x) * (opp_base.x - tank.x)
                    + (wy - tank.y) * (opp_base.y - tank.y)
                    > 0
                    or (wx - tank.x) * (opp_tank.x - tank.x)
                    + (wy - tank.y) * (opp_tank.y - tank.y)
                    > 0
                )
                wall_hp = state.walls.get(hit_pos, 3)
                if toward_target:
                    priority = 75.0 if wall_hp == 1 else 65.0
                else:
                    priority = 15.0
            elif hit_kind == f"base_{player_id}":
                priority = -100.0
            else:
                priority = -15.0

        elif action in ACTION_TO_DIRECTION:
            direction = ACTION_TO_DIRECTION[action]
            nx = tank.x + direction.dx
            ny = tank.y + direction.dy

            passable = is_cell_passable(state, nx, ny)
            if passable:
                new_dist = min(
                    abs(nx - opp_tank.x) + abs(ny - opp_tank.y),
                    abs(nx - opp_base.x) + abs(ny - opp_base.y),
                )
                priority = 35.0 if new_dist < cur_dist else 18.0
                if in_danger_now and not _is_in_firing_lane(
                    state, opp_tank, (nx, ny), BULLET_SPEED
                ):
                    priority += 60.0
                elif not in_danger_now and _is_in_firing_lane(
                    state, opp_tank, (nx, ny), BULLET_SPEED
                ):
                    priority -= 25.0
            elif tank.direction == direction:
                # Pure no-op wall/boundary slam: keep strictly below Action.STAY (-10/-5).
                priority = -50.0
            else:
                hit_after_turn, _, _ = _trace_first_hit(
                    state, tank.x, tank.y, direction, BULLET_SPEED
                )
                if hit_after_turn in (f"tank_{opp_id}", f"base_{opp_id}"):
                    priority = 55.0
                elif hit_after_turn == "wall":
                    priority = 30.0
                else:
                    priority = 2.0

            if (passable or tank.direction != direction) and (
                (opp_tank.x - tank.x) * direction.dx + (opp_tank.y - tank.y) * direction.dy
                > 0
                or (opp_base.x - tank.x) * direction.dx
                + (opp_base.y - tank.y) * direction.dy
                > 0
            ):
                priority += 5.0

        else:
            priority = -10.0 if in_danger_now else -5.0

        scored.append((priority, -idx, action))

    scored.sort(reverse=True)
    return [item[2] for item in scored]
