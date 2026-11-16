"""CLI and PyGame entrypoint for Task 2: Tank Battle Adversarial Search."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# Ensure direct script execution resolves task2 imports from the repository root.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from task2.agents.agent_loader import AgentLoader
from task2.agents.base_agent import BaseAgent
from task2.core.constants import MAX_TURNS
from task2.core.game_engine import GameEngine
from task2.experiments.maps import load_game_state


def _resolve_agent_class(name: str, registry: dict[str, type[BaseAgent]]) -> type[BaseAgent]:
    """Match an agent class name case-insensitively (with or without 'Agent' suffix)."""
    if name in registry:
        return registry[name]
    lowered = name.strip().lower()
    for key, cls in registry.items():
        if key.lower() == lowered or key.lower().removesuffix("agent") == lowered:
            return cls
    available = ", ".join(sorted(registry.keys()))
    raise ValueError(f"Unknown agent '{name}'. Available agents: {available}")


def run_headless_match(
    p1_name: str,
    p2_name: str,
    map_spec: str,
    depth: int,
    max_turns: int = MAX_TURNS,
) -> int:
    """Execute one headless match and print turn summary and winner."""
    registry = AgentLoader.get_all_agent_classes()
    p1_cls = _resolve_agent_class(p1_name, registry)
    p2_cls = _resolve_agent_class(p2_name, registry)

    state = load_game_state(map_spec, max_turns=max_turns)
    try:
        p1 = p1_cls(player_id=1, depth=depth)
    except TypeError:
        p1 = p1_cls(player_id=1)
    try:
        p2 = p2_cls(player_id=2, depth=depth)
    except TypeError:
        p2 = p2_cls(player_id=2)

    print(
        f"Starting headless match on '{map_spec}' (depth={depth}, max_turns={max_turns}): "
        f"P1={p1.name} vs P2={p2.name}"
    )

    while not state.is_terminal():
        active = p1 if state.current_turn == 1 else p2
        action = AgentLoader.safe_get_action(active, state)
        state = GameEngine.apply_action(state, action)

    winner = state.get_winner()
    winner_str = (
        f"Player 1 ({p1.name})"
        if winner == 1
        else (f"Player 2 ({p2.name})" if winner == 2 else "Draw")
    )

    print(f"Match finished in {state.turn_count} turns | Winner: {winner_str}")
    print(
        f"  P1 Final -> Tank HP: {state.tanks[1].hp}/{state.tanks[1].max_hp}, "
        f"Base HP: {state.bases[1].hp}/{state.bases[1].max_hp}, "
        f"Avg Time: {p1.avg_time_ms:.2f} ms/move, "
        f"Nodes: {p1.total_nodes_explored}, Pruned: {p1.pruned_branches}"
    )
    print(
        f"  P2 Final -> Tank HP: {state.tanks[2].hp}/{state.tanks[2].max_hp}, "
        f"Base HP: {state.bases[2].hp}/{state.bases[2].max_hp}, "
        f"Avg Time: {p2.avg_time_ms:.2f} ms/move, "
        f"Nodes: {p2.total_nodes_explored}, Pruned: {p2.pruned_branches}"
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser for GUI, headless match, and benchmark modes."""
    parser = argparse.ArgumentParser(
        description="Tank Battle AI (Task 2: Adversarial Search)"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--headless",
        action="store_true",
        help="Run a headless AI-vs-AI match in the terminal.",
    )
    mode.add_argument(
        "--benchmark",
        action="store_true",
        help="Run the 4-configuration benchmark and save CSV + PNG charts.",
    )
    parser.add_argument(
        "--p1",
        default="HeuristicAlphaBetaAgent",
        help="Player 1 agent class name (default: HeuristicAlphaBetaAgent).",
    )
    parser.add_argument(
        "--p2",
        default="MinimaxAgent",
        help="Player 2 agent class name (default: MinimaxAgent).",
    )
    parser.add_argument(
        "--map",
        default="map1_open.txt",
        help="Scenario name, map filename, or path (default: map1_open.txt).",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Search depth in plies (default: 3).",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=MAX_TURNS,
        help=f"Maximum turns before draw (default: {MAX_TURNS}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and dispatch to GUI, headless match, or benchmark."""
    args = build_parser().parse_args(argv)

    if args.benchmark:
        from task2.experiments.benchmark import run_benchmark

        df = run_benchmark()
        print(df.to_string(index=False))
        return 0

    if args.headless:
        return run_headless_match(
            p1_name=args.p1,
            p2_name=args.p2,
            map_spec=args.map,
            depth=args.depth,
            max_turns=args.max_turns,
        )

    from task2.ui.renderer import TankBattleApp

    TankBattleApp().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
