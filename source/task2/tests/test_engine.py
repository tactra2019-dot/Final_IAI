"""Comprehensive unit, edge, invalid-input, and performance tests for Task 2."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

# Ensure project root is importable regardless of pytest invocation directory.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from source.task2.agents import (
    AgentLoader,
    AlphaBetaAgent,
    BaseAgent,
    HeuristicAlphaBetaAgent,
    HeuristicMinimaxAgent,
    MinimaxAgent,
)
from source.task2.core.actions import ALL_ACTIONS, Action, Direction
from source.task2.core.constants import (
    BASE_INITIAL_HP,
    BULLET_DAMAGE,
    BULLET_SPEED,
    GRID_HEIGHT,
    GRID_WIDTH,
    MAX_TURNS,
    TANK_INITIAL_HP,
    UTILITY_DRAW,
    UTILITY_LOSS,
    UTILITY_WIN,
    WALL_INITIAL_HP,
)
from source.task2.core.game_engine import GameEngine
from source.task2.core.game_state import GameState


def make_grid(
    p1: tuple[int, int] = (2, 2),
    p2: tuple[int, int] = (10, 10),
    base1: tuple[int, int] = (6, 0),
    base2: tuple[int, int] = (6, 12),
    walls: dict[tuple[int, int], str] | None = None,
) -> str:
    """Build a valid 13x13 ASCII board string from (x, y) coordinates."""
    grid = [["." for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    if walls:
        for (wx, wy), ch in walls.items():
            grid[wy][wx] = ch
    grid[base1[1]][base1[0]] = "A"
    grid[base2[1]][base2[0]] = "B"
    grid[p1[1]][p1[0]] = "1"
    grid[p2[1]][p2[0]] = "2"
    return "\n".join("".join(row) for row in grid)


def make_state(
    p1: tuple[int, int] = (2, 2),
    p2: tuple[int, int] = (10, 10),
    base1: tuple[int, int] = (6, 0),
    base2: tuple[int, int] = (6, 12),
    walls: dict[tuple[int, int], str] | None = None,
    max_turns: int = MAX_TURNS,
) -> GameState:
    """Create a GameState from coordinates without depending on __init__ kwargs."""
    return GameState.from_text(
        make_grid(p1=p1, p2=p2, base1=base1, base2=base2, walls=walls),
        max_turns=max_turns,
    )


# ---------------------------------------------------------------------------
# 1. Normal Cases
# ---------------------------------------------------------------------------


class TestNormalCases:
    """Verify standard movement, facing alignment, firing, turn switching, and maps."""

    @pytest.mark.parametrize(
        "action,expected_dir,dx,dy",
        [
            (Action.MOVE_UP, Direction.UP, 0, -1),
            (Action.MOVE_DOWN, Direction.DOWN, 0, 1),
            (Action.MOVE_LEFT, Direction.LEFT, -1, 0),
            (Action.MOVE_RIGHT, Direction.RIGHT, 1, 0),
        ],
    )
    def test_movement_four_directions_and_gun_alignment(
        self, action: Action, expected_dir: Direction, dx: int, dy: int
    ) -> None:
        state = make_state(p1=(5, 5), p2=(10, 10))
        next_state = GameEngine.apply_action(state, action)

        assert next_state.tanks[1].pos == (5 + dx, 5 + dy)
        assert next_state.tanks[1].direction == expected_dir
        assert next_state.last_action == action
        # Original state must not be mutated.
        assert state.tanks[1].pos == (5, 5)
        assert state.turn_count == 0

    @pytest.mark.parametrize("distance", [1, 2, 3])
    def test_fire_hits_target_within_range_one_to_three(self, distance: int) -> None:
        state = make_state(p1=(4, 4), p2=(4, 4 + distance))
        state.tanks[1].direction = Direction.DOWN

        next_state = GameEngine.apply_action(state, Action.FIRE)

        assert next_state.tanks[2].hp == TANK_INITIAL_HP - BULLET_DAMAGE
        assert next_state.last_hit_pos == (4, 4 + distance)
        assert len(next_state.last_bullet_path) == distance
        assert next_state.last_bullet_path[-1] == (4, 4 + distance)

    def test_alternating_turns_and_stay(self) -> None:
        state = make_state()
        assert state.current_turn == 1
        assert state.turn_count == 0

        s1 = GameEngine.apply_action(state, Action.STAY)
        assert s1.current_turn == 2
        assert s1.turn_count == 1
        assert s1.tanks[1].pos == state.tanks[1].pos

        s2 = GameEngine.apply_action(s1, Action.MOVE_UP)
        assert s2.current_turn == 1
        assert s2.turn_count == 2
        assert s2.tanks[2].pos == (10, 9)
        assert s2.tanks[2].direction == Direction.UP

    def test_builtin_maps_load_cleanly(self) -> None:
        maps_dir = PROJECT_ROOT / "source" / "task2" / "maps"
        map_files = sorted(maps_dir.glob("*.txt"))
        assert len(map_files) >= 3

        for map_path in map_files:
            state = GameState.from_file(map_path)
            assert state.width == GRID_WIDTH
            assert state.height == GRID_HEIGHT
            assert state.tanks[1].hp == TANK_INITIAL_HP
            assert state.tanks[2].hp == TANK_INITIAL_HP
            assert state.bases[1].hp == BASE_INITIAL_HP
            assert state.bases[2].hp == BASE_INITIAL_HP


# ---------------------------------------------------------------------------
# 2. Boundary Cases
# ---------------------------------------------------------------------------


class TestBoundaryCases:
    """Verify board edges, max bullet travel 3, MAX_TURNS=200 draw, and wall removal."""

    def test_borders_top_left_and_bottom_right_block_movement(self) -> None:
        state = make_state(p1=(0, 0), p2=(12, 12))

        s_up = GameEngine.apply_action(state, Action.MOVE_UP)
        assert s_up.tanks[1].pos == (0, 0)
        assert s_up.tanks[1].direction == Direction.UP

        s_left = GameEngine.apply_action(state, Action.MOVE_LEFT)
        assert s_left.tanks[1].pos == (0, 0)
        assert s_left.tanks[1].direction == Direction.LEFT

        # Switch to P2 at (12, 12)
        state_p2 = s_up.clone()
        s_down = GameEngine.apply_action(state_p2, Action.MOVE_DOWN)
        assert s_down.tanks[2].pos == (12, 12)
        assert s_down.tanks[2].direction == Direction.DOWN

        s_right = GameEngine.apply_action(state_p2, Action.MOVE_RIGHT)
        assert s_right.tanks[2].pos == (12, 12)
        assert s_right.tanks[2].direction == Direction.RIGHT

    def test_bullet_stops_at_board_boundary_without_error(self) -> None:
        state = make_state(p1=(0, 0), p2=(10, 10))
        state.tanks[1].direction = Direction.LEFT

        next_state = GameEngine.apply_action(state, Action.FIRE)
        assert next_state.last_bullet_path == []
        assert next_state.last_hit_pos is None

    def test_bullet_travels_max_three_cells_and_misses_fourth(self) -> None:
        state = make_state(p1=(2, 5), p2=(6, 5))
        state.tanks[1].direction = Direction.RIGHT

        next_state = GameEngine.apply_action(state, Action.FIRE)

        assert len(next_state.last_bullet_path) == BULLET_SPEED
        assert next_state.last_bullet_path == [(3, 5), (4, 5), (5, 5)]
        assert next_state.last_hit_pos is None
        assert next_state.tanks[2].hp == TANK_INITIAL_HP

    def test_max_turns_triggers_draw_terminal_state(self) -> None:
        state = make_state()
        state.turn_count = MAX_TURNS - 1

        terminal = GameEngine.apply_action(state, Action.STAY)
        assert terminal.turn_count == MAX_TURNS
        assert terminal.is_terminal() is True
        assert terminal.get_winner() == 0
        assert terminal.get_utility(1) == UTILITY_DRAW
        assert terminal.get_utility(2) == UTILITY_DRAW
        assert terminal.get_legal_actions() == []

        # Applying action on already terminal state returns clone without mutating turn_count.
        after = GameEngine.apply_action(terminal, Action.FIRE)
        assert after.turn_count == MAX_TURNS
        assert after is not terminal

    def test_wall_destruction_removes_wall_and_opens_passage(self) -> None:
        state = make_state(p1=(5, 5), p2=(10, 10), walls={(6, 5): "W"})
        assert state.walls[(6, 5)] == WALL_INITIAL_HP
        state.tanks[1].direction = Direction.RIGHT

        # Hit wall 3 times with P1 (interleaved with P2 STAY).
        cur = state
        for expected_hp in (2, 1, 0):
            cur = GameEngine.apply_action(cur, Action.FIRE)
            if expected_hp > 0:
                assert cur.walls[(6, 5)] == expected_hp
            else:
                assert (6, 5) not in cur.walls
            cur = GameEngine.apply_action(cur, Action.STAY)

        # Now P1 can move into (6, 5).
        moved = GameEngine.apply_action(cur, Action.MOVE_RIGHT)
        assert moved.tanks[1].pos == (6, 5)


# ---------------------------------------------------------------------------
# 3. Edge Cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Verify collision stopping, rotation when blocked, simultaneous death, and AB equivalence."""

    def test_bullet_stops_on_first_entity_and_spares_behind(self) -> None:
        # P1 at (2,5) firing RIGHT toward wall at (3,5) with P2 at (4,5) behind it.
        state = make_state(p1=(2, 5), p2=(4, 5), walls={(3, 5): "W"})
        state.tanks[1].direction = Direction.RIGHT

        s1 = GameEngine.apply_action(state, Action.FIRE)
        assert s1.walls[(3, 5)] == WALL_INITIAL_HP - 1
        assert s1.tanks[2].hp == TANK_INITIAL_HP
        assert s1.last_hit_pos == (3, 5)
        assert s1.last_bullet_path == [(3, 5)]

        # Also check P2 tank shielding Base 2 behind it.
        state2 = make_state(p1=(6, 4), p2=(6, 5), base2=(6, 6))
        state2.tanks[1].direction = Direction.DOWN
        s2 = GameEngine.apply_action(state2, Action.FIRE)
        assert s2.tanks[2].hp == TANK_INITIAL_HP - 1
        assert s2.bases[2].hp == BASE_INITIAL_HP
        assert s2.last_hit_pos == (6, 5)
        assert s2.last_bullet_path == [(6, 5)]

    def test_blocked_movement_still_rotates_barrel(self) -> None:
        state = make_state(p1=(5, 5), p2=(10, 10), walls={(6, 5): "W"})
        assert state.tanks[1].direction == Direction.DOWN

        next_state = GameEngine.apply_action(state, Action.MOVE_RIGHT)
        assert next_state.tanks[1].pos == (5, 5)
        assert next_state.tanks[1].direction == Direction.RIGHT
        assert next_state.turn_count == 1
        assert next_state.current_turn == 2

    def test_blocked_by_tank_and_base_still_rotates(self) -> None:
        state = make_state(p1=(5, 5), p2=(5, 4), base1=(5, 6))
        state.tanks[1].direction = Direction.LEFT

        s_tank_block = GameEngine.apply_action(state, Action.MOVE_UP)
        assert s_tank_block.tanks[1].pos == (5, 5)
        assert s_tank_block.tanks[1].direction == Direction.UP

        s_base_block = GameEngine.apply_action(state, Action.MOVE_DOWN)
        assert s_base_block.tanks[1].pos == (5, 5)
        assert s_base_block.tanks[1].direction == Direction.DOWN

    def test_low_hp_and_simultaneous_destruction_terminal_states(self) -> None:
        # P2 tank HP reaches 0 -> P1 wins
        state = make_state(p1=(5, 5), p2=(5, 6))
        state.tanks[1].direction = Direction.DOWN
        state.tanks[2].hp = 1

        s_win = GameEngine.apply_action(state, Action.FIRE)
        assert s_win.is_terminal() is True
        assert s_win.get_winner() == 1
        assert s_win.get_utility(1) == UTILITY_WIN - s_win.turn_count
        assert s_win.get_utility(2) == UTILITY_LOSS + s_win.turn_count

        # P2 base reaches 0 HP -> P1 wins even if P2 tank has full HP
        state_base = make_state(p1=(6, 11), p2=(10, 10), base2=(6, 12))
        state_base.tanks[1].direction = Direction.DOWN
        state_base.bases[2].hp = 1
        s_base_win = GameEngine.apply_action(state_base, Action.FIRE)
        assert s_base_win.is_terminal() is True
        assert s_base_win.get_winner() == 1

        # Simultaneous dead entities -> Draw (winner == 0)
        simul = make_state()
        simul.tanks[1].hp = 0
        simul.tanks[2].hp = 0
        assert simul.is_terminal() is True
        assert simul.get_winner() == 0
        assert simul.get_utility(1) == UTILITY_DRAW

    def test_minimax_and_alphabeta_same_action_with_fewer_nodes(self) -> None:
        state = make_state(p1=(5, 5), p2=(5, 7), walls={(4, 6): "W", (6, 6): "W"})
        state.tanks[1].direction = Direction.DOWN

        mm = MinimaxAgent(player_id=1, depth=2)
        ab = AlphaBetaAgent(player_id=1, depth=2)

        mm_action = mm.get_action(state)
        ab_action = ab.get_action(state)

        assert mm_action in ALL_ACTIONS
        assert ab_action == mm_action
        assert ab.nodes_explored <= mm.nodes_explored
        assert ab.pruned_branches >= 0


# ---------------------------------------------------------------------------
# 4. Invalid Input Cases
# ---------------------------------------------------------------------------


class _CrashingAgent(BaseAgent):
    def get_action(self, state: GameState) -> Action:
        raise RuntimeError("Simulated external crash")


class _HangingAgent(BaseAgent):
    def get_action(self, state: GameState) -> Action:
        time.sleep(0.5)
        return Action.FIRE


class _MutatingInvalidAgent(BaseAgent):
    def get_action(self, state: GameState) -> Action:
        state.tanks[1].hp = 0
        state.walls.clear()
        return "NOT_AN_ACTION"  # type: ignore[return-value]


class TestInvalidInputCases:
    """Verify validation on apply_action, from_text, and AgentLoader.safe_get_action."""

    @pytest.mark.parametrize("bad_action", ["FIRE", None, 42, "MOVE_UP", object()])
    def test_apply_action_rejects_non_action(self, bad_action: object) -> None:
        state = make_state()
        with pytest.raises(ValueError):
            GameEngine.apply_action(state, bad_action)  # type: ignore[arg-type]

    def test_from_text_rejects_wrong_dimensions_or_chars(self) -> None:
        # Empty string
        with pytest.raises(ValueError):
            GameState.from_text("")

        # Too few rows (12 rows)
        lines = make_grid().splitlines()
        with pytest.raises(ValueError):
            GameState.from_text("\n".join(lines[:12]))

        # Wrong row width (12 chars on first row)
        bad_width = list(lines)
        bad_width[0] = bad_width[0][:12]
        with pytest.raises(ValueError):
            GameState.from_text("\n".join(bad_width))

        # Invalid character 'X'
        bad_char = make_grid().replace(".", "X", 1)
        with pytest.raises(ValueError):
            GameState.from_text(bad_char)

    @pytest.mark.parametrize("missing_symbol", ["1", "2", "A", "B"])
    def test_from_text_rejects_missing_required_entity(self, missing_symbol: str) -> None:
        bad_text = make_grid().replace(missing_symbol, ".", 1)
        with pytest.raises(ValueError):
            GameState.from_text(bad_text)

    def test_from_text_rejects_duplicate_required_entity(self) -> None:
        lines = [list(row) for row in make_grid().splitlines()]
        lines[1][1] = "1"
        with pytest.raises(ValueError):
            GameState.from_text("\n".join("".join(r) for r in lines))

    def test_agent_loader_handles_crashing_hanging_and_mutating_agents(self) -> None:
        state = make_state(walls={(4, 4): "W"})
        original_key = state.state_key()

        crasher = _CrashingAgent(player_id=1, depth=1)
        assert AgentLoader.safe_get_action(crasher, state, timeout_sec=0.5) == Action.STAY

        hanger = _HangingAgent(player_id=1, depth=1)
        t0 = time.perf_counter()
        action = AgentLoader.safe_get_action(hanger, state, timeout_sec=0.08)
        elapsed = time.perf_counter() - t0
        assert action == Action.STAY
        assert elapsed < 0.45

        mutator = _MutatingInvalidAgent(player_id=1, depth=1)
        assert AgentLoader.safe_get_action(mutator, state, timeout_sec=0.5) == Action.STAY
        # Original state must remain completely untouched.
        assert state.state_key() == original_key
        assert state.tanks[1].hp == TANK_INITIAL_HP
        assert (4, 4) in state.walls


# ---------------------------------------------------------------------------
# 5. Performance Cases
# ---------------------------------------------------------------------------


class TestPerformanceCases:
    """Verify fast clone() speed and real-time HeuristicAlphaBetaAgent latency."""

    def test_ten_thousand_clones_under_half_second(self) -> None:
        map2 = PROJECT_ROOT / "source" / "task2" / "maps" / "map2_tactical.txt"
        state = GameState.from_file(map2) if map2.exists() else make_state(walls={(4, 4): "W"})

        start = time.perf_counter()
        for _ in range(10_000):
            _ = state.clone()
        elapsed = time.perf_counter() - start

        assert elapsed < 0.5, f"10,000 clones took {elapsed:.3f}s (limit 0.5s)"

    def test_heuristic_alphabeta_depth3_under_150ms(self) -> None:
        map1 = PROJECT_ROOT / "source" / "task2" / "maps" / "map1_open.txt"
        state = GameState.from_file(map1) if map1.exists() else make_state(p1=(2, 6), p2=(10, 6))

        agent = HeuristicAlphaBetaAgent(player_id=1, depth=3)
        start = time.perf_counter()
        action = agent.get_action(state)
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        assert action in ALL_ACTIONS
        assert elapsed_ms < 150.0, f"HeuristicAlphaBeta depth=3 took {elapsed_ms:.1f}ms (limit 150ms)"

    def test_all_four_agent_configs_execute_and_track_metrics(self) -> None:
        state = make_state(p1=(4, 6), p2=(6, 6))
        for cls in (
            MinimaxAgent,
            AlphaBetaAgent,
            HeuristicMinimaxAgent,
            HeuristicAlphaBetaAgent,
        ):
            agent = cls(player_id=1, depth=2)
            act = agent.get_action(state)
            assert act in ALL_ACTIONS
            metrics = agent.get_metrics()
            assert metrics["move_count"] == 1
            assert metrics["total_nodes_explored"] >= 1


class TestIntegrationAndPlugins:
    """Verify plugin discovery, scenario loader, and headless PyGame import safety."""

    def test_agent_loader_discovers_builtin_and_external_plugins(self) -> None:
        builtins = AgentLoader.get_builtin_agents()
        assert set(builtins.keys()) == {
            "MinimaxAgent",
            "AlphaBetaAgent",
            "HeuristicMinimaxAgent",
            "HeuristicAlphaBetaAgent",
        }
        externals = AgentLoader.discover_external_agents()
        assert "GreedyShooterAgent" in externals

        all_classes = AgentLoader.get_all_agent_classes()
        assert "GreedyShooterAgent" in all_classes

        ext_agent = all_classes["GreedyShooterAgent"](player_id=1, depth=1)
        state = make_state()
        assert AgentLoader.safe_get_action(ext_agent, state) in ALL_ACTIONS

    def test_scenario_maps_and_headless_ui_import_safety(self) -> None:
        import importlib
        import pygame

        from source.task2.experiments.maps import load_game_state, load_scenario_maps

        scenarios = load_scenario_maps()
        assert len(scenarios) == 3
        for name in scenarios:
            st = load_game_state(name)
            assert st.width == GRID_WIDTH and st.height == GRID_HEIGHT

        importlib.import_module("source.task2.ui")
        importlib.import_module("source.task2.ui.renderer")
        importlib.import_module("source.task2.main")
        assert pygame.get_init() is False

    def test_walls_key_caching_invalidation_and_last_hit_kind(self) -> None:
        state = make_state(
            p1=(4, 5),
            p2=(8, 5),
            base2=(6, 12),
            walls={(5, 5): "W", (3, 5): "w"},
        )
        cached_key = state.walls_key()
        assert state._walls_key is cached_key
        assert state.walls_key() is cached_key

        # clone() preserves cached _walls_key and non-wall actions keep it cached.
        cloned = state.clone()
        assert cloned._walls_key is cached_key
        s_stay = GameEngine.apply_action(state, Action.STAY)
        assert s_stay._walls_key is cached_key
        assert s_stay.last_hit_kind is None

        # Hitting a wall invalidates _walls_key and sets last_hit_kind="wall".
        s_p1 = s_stay.clone()
        s_p1.current_turn = 1
        s_p1.tanks[1].direction = Direction.RIGHT
        s_wall_dmg = GameEngine.apply_action(s_p1, Action.FIRE)
        assert s_wall_dmg.last_hit_pos == (5, 5)
        assert s_wall_dmg.last_hit_kind == "wall"
        assert s_wall_dmg._walls_key is None
        new_key = s_wall_dmg.walls_key()
        assert new_key != cached_key
        assert dict(new_key)[(5, 5)] == WALL_INITIAL_HP - 1

        # Destroying a 1-HP weak wall removes it from walls_key().
        s_left = s_wall_dmg.clone()
        s_left.current_turn = 1
        s_left.tanks[1].direction = Direction.LEFT
        s_wall_gone = GameEngine.apply_action(s_left, Action.FIRE)
        assert s_wall_gone.last_hit_pos == (3, 5)
        assert s_wall_gone.last_hit_kind == "wall"
        assert (3, 5) not in dict(s_wall_gone.walls_key())

        # Hitting a tank sets last_hit_kind="tank" without invalidating walls_key.
        s_tank_setup = make_state(p1=(4, 5), p2=(6, 5), walls={(1, 1): "W"})
        wk_tank = s_tank_setup.walls_key()
        s_tank_setup.tanks[1].direction = Direction.RIGHT
        s_tank_hit = GameEngine.apply_action(s_tank_setup, Action.FIRE)
        assert s_tank_hit.last_hit_pos == (6, 5)
        assert s_tank_hit.last_hit_kind == "tank"
        assert s_tank_hit._walls_key is wk_tank

        # Hitting a base sets last_hit_kind="base" without invalidating walls_key.
        s_base_setup = make_state(p1=(6, 10), p2=(1, 1), base2=(6, 12), walls={(2, 2): "W"})
        wk_base = s_base_setup.walls_key()
        s_base_setup.tanks[1].direction = Direction.DOWN
        s_base_hit = GameEngine.apply_action(s_base_setup, Action.FIRE)
        assert s_base_hit.last_hit_pos == (6, 12)
        assert s_base_hit.last_hit_kind == "base"
        assert s_base_hit._walls_key is wk_base

    def test_p2_agents_actively_move_and_do_not_idle_fire(self) -> None:
        from source.task2.experiments.maps import load_game_state

        for map_name in ("map1_open.txt", "map2_tactical.txt"):
            for cls in (
                MinimaxAgent,
                AlphaBetaAgent,
                HeuristicMinimaxAgent,
                HeuristicAlphaBetaAgent,
            ):
                state = load_game_state(map_name)
                spawn_pos = state.tanks[2].pos
                p2_agent = cls(player_id=2, depth=2)
                p2_actions: list[Action] = []

                # Play 6 plies (3 turns per player) with P1 holding position.
                for _ in range(6):
                    if state.is_terminal():
                        break
                    if state.current_turn == 1:
                        action = Action.STAY
                    else:
                        action = p2_agent.get_action(state)
                        p2_actions.append(action)
                    state = GameEngine.apply_action(state, action)

                assert state.tanks[2].pos != spawn_pos, (
                    f"{cls.__name__} as P2 stayed at {spawn_pos} on {map_name} "
                    f"(actions={p2_actions})"
                )
                assert any(a in (Action.MOVE_UP, Action.MOVE_DOWN, Action.MOVE_LEFT, Action.MOVE_RIGHT) for a in p2_actions)

    def test_offscreen_ui_menu_and_renderer_smoke(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import pygame

        from source.task2.experiments.maps import load_game_state
        from source.task2.ui import theme
        from source.task2.ui.menu import SetupMenu
        from source.task2.ui.renderer import (
            ActionLogEntry,
            FloatingPopup,
            GameRenderer,
            PlayerTelemetry,
        )

        monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
        pygame.init()
        try:
            screen = pygame.display.set_mode((theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT))
            fonts = theme.load_fonts(pygame)
            clock = pygame.time.Clock()

            menu = SetupMenu(screen, fonts, clock)
            assert menu.agent_options[menu.p1_idx].label == "HeuristicAlphaBetaAgent"
            assert menu.agent_options[menu.p2_idx].label == "HeuristicMinimaxAgent"

            menu._draw()
            assert "btn_swap" in menu._rects
            done, cfg = menu._handle_click(menu._rects["btn_swap"].center)
            assert done is False and cfg is None
            assert menu.agent_options[menu.p1_idx].label == "HeuristicMinimaxAgent"
            assert menu.agent_options[menu.p2_idx].label == "HeuristicAlphaBetaAgent"

            menu.swap_players()
            assert menu.agent_options[menu.p1_idx].label == "HeuristicAlphaBetaAgent"
            assert menu.agent_options[menu.p2_idx].label == "HeuristicMinimaxAgent"

            renderer = GameRenderer(screen, fonts)
            state = load_game_state("map1_open.txt")
            state.tanks[1].direction = Direction.DOWN
            state.last_bullet_path = [(6, 3), (6, 4), (6, 5)]
            state.last_hit_pos = (6, 5)
            state.last_hit_kind = "tank"

            p1_tel = PlayerTelemetry("HeuristicAlphaBetaAgent", False, 3, "FIRE", 3.5, 3.5, 65, 65, 30)
            p2_tel = PlayerTelemetry("HeuristicMinimaxAgent", False, 3, "MOVE_UP", 9.0, 9.0, 250, 250, 0)
            log = [ActionLogEntry(1, 1, "FIRE", (6, 5), "tank")]
            popups = [FloatingPopup(6, 5, "-1 HP", theme.STATUS_DANGER, created_tick=100)]

            renderer.draw(
                state=state,
                p1_tel=p1_tel,
                p2_tel=p2_tel,
                map_name="Map 1 - Open",
                paused=False,
                step_delay_ms=220,
                action_log=log,
                fx_intensity=0.9,
                popups=popups,
                now_tick=250,
            )
            assert set(renderer.toolbar_rects.keys()) == {
                "pause",
                "step",
                "speed_down",
                "speed_up",
                "restart",
                "menu",
            }
        finally:
            pygame.quit()
            assert pygame.get_init() is False

    @staticmethod
    def _run_recorded_match(
        map_name: str,
        p1_agent: BaseAgent,
        p2_agent: BaseAgent,
        max_turns: int = MAX_TURNS,
    ) -> tuple[GameState, dict[int, list[tuple[int, int]]], dict[int, int]]:
        from source.task2.core.actions import ACTION_TO_DIRECTION
        from source.task2.experiments.maps import load_game_state

        state = load_game_state(map_name)
        positions: dict[int, list[tuple[int, int]]] = {1: [], 2: []}
        same_dir_noops: dict[int, int] = {1: 0, 2: 0}

        for _ in range(max_turns):
            if state.is_terminal():
                break
            pid = state.current_turn
            action = (p1_agent if pid == 1 else p2_agent).get_action(state)
            pos_before = state.tanks[pid].pos
            dir_before = state.tanks[pid].direction
            state = GameEngine.apply_action(state, action)
            positions[pid].append(state.tanks[pid].pos)
            move_dir = ACTION_TO_DIRECTION.get(action)
            if move_dir == dir_before and state.tanks[pid].pos == pos_before:
                same_dir_noops[pid] += 1

        return state, positions, same_dir_noops

    def test_video_bug3_greedy_breaks_wall_and_finishes_map3(self) -> None:
        from source.task2.agents.external.sample_external_agent import GreedyShooterAgent

        state, positions, noops = self._run_recorded_match(
            "map3_endgame.txt", GreedyShooterAgent(1), GreedyShooterAgent(2)
        )
        assert state.turn_count < MAX_TURNS
        assert state.get_winner() != 0
        assert (6, 6) not in state.walls
        assert noops[1] == 0 and noops[2] == 0
        assert len(positions[1]) < MAX_TURNS // 2

    def test_video_bug2_greedy_escapes_pocket_stall_on_map2(self) -> None:
        from source.task2.agents.external.sample_external_agent import GreedyShooterAgent

        state, positions, noops = self._run_recorded_match(
            "map2_tactical.txt",
            GreedyShooterAgent(1),
            HeuristicAlphaBetaAgent(2, depth=3),
        )
        assert noops[1] == 0 and noops[2] == 0
        # Guard against sustained (4,1)<->(4,3) pocket stall oscillation.
        pocket = {(4, 1), (4, 2), (4, 3)}
        max_pocket_streak = 0
        streak = 0
        for pos in positions[1]:
            streak = streak + 1 if pos in pocket else 0
            max_pocket_streak = max(max_pocket_streak, streak)
        assert max_pocket_streak < 6

    def test_video_bug4_minimax_avoids_wall_slam_and_matches_alphabeta(self) -> None:
        from source.task2.agents.heuristics import ordered_actions_basic

        # Verify pure same-direction blocked moves are demoted strictly after Action.STAY.
        blocked_state = make_state(p1=(5, 2), walls={(5, 1): "W"})
        blocked_state.tanks[1].direction = Direction.UP
        ordered = ordered_actions_basic(blocked_state)
        assert ordered.index(Action.MOVE_UP) > ordered.index(Action.STAY)

        state, _, noops = self._run_recorded_match(
            "map2_tactical.txt",
            MinimaxAgent(1, depth=3),
            MinimaxAgent(2, depth=3),
        )
        assert state.is_terminal() or state.turn_count == MAX_TURNS
        assert noops[1] == 0 and noops[2] == 0

        # Basic Minimax and Alpha-Beta must pick identical actions on sample states.
        for map_name in ("map1_open.txt", "map2_tactical.txt", "map3_endgame.txt"):
            s = self._step_sample_state(map_name, steps=4)
            mm = MinimaxAgent(s.current_turn, depth=2)
            ab = AlphaBetaAgent(s.current_turn, depth=2)
            assert mm.get_action(s) == ab.get_action(s)

    def test_video_bug1_heuristic_defends_base_and_matches_parity(self) -> None:
        state, _, noops = self._run_recorded_match(
            "map1_open.txt",
            HeuristicAlphaBetaAgent(1, depth=3),
            HeuristicMinimaxAgent(2, depth=3),
        )
        assert noops[1] == 0 and noops[2] == 0
        assert state.bases[1].hp > 0 and state.get_winner() != 2

        for map_name in ("map1_open.txt", "map2_tactical.txt", "map3_endgame.txt"):
            s = self._step_sample_state(map_name, steps=6)
            hmm = HeuristicMinimaxAgent(s.current_turn, depth=2)
            hab = HeuristicAlphaBetaAgent(s.current_turn, depth=2)
            assert hmm.get_action(s) == hab.get_action(s)

    def test_headless_default_hab_vs_minimax_does_not_throw_base1(self) -> None:
        state, _, noops = self._run_recorded_match(
            "map1_open.txt",
            HeuristicAlphaBetaAgent(1, depth=3),
            MinimaxAgent(2, depth=3),
        )
        assert noops[1] == 0 and noops[2] == 0
        assert state.bases[1].hp > 0 and state.get_winner() != 2

    @staticmethod
    def _step_sample_state(map_name: str, steps: int) -> GameState:
        from source.task2.experiments.maps import load_game_state

        state = load_game_state(map_name)
        for _ in range(steps):
            if state.is_terminal():
                break
            agent = HeuristicAlphaBetaAgent(state.current_turn, depth=2)
            state = GameEngine.apply_action(state, agent.get_action(state))
        return state

