"""Scenario map discovery and GameState loading helpers."""

from __future__ import annotations

from pathlib import Path

from task2.core.constants import MAX_TURNS
from task2.core.game_state import GameState

SCENARIO_FILES: dict[str, str] = {
    "Map 1 - Open": "map1_open.txt",
    "Map 2 - Tactical": "map2_tactical.txt",
    "Map 3 - Endgame": "map3_endgame.txt",
}


def get_maps_dir() -> Path:
    """Return the cross-platform Path to the built-in task2 maps directory."""
    return Path(__file__).resolve().parent.parent / "maps"


def load_scenario_maps() -> dict[str, Path]:
    """Return the three standardized benchmark scenario names mapped to file paths."""
    maps_dir = get_maps_dir()
    return {name: maps_dir / filename for name, filename in SCENARIO_FILES.items()}


def list_available_maps() -> dict[str, Path]:
    """Return all available .txt maps in the maps directory with readable labels."""
    maps_dir = get_maps_dir()
    scenarios = load_scenario_maps()
    ordered: dict[str, Path] = {
        name: path for name, path in scenarios.items() if path.exists()
    }
    known_files = {path.resolve() for path in ordered.values()}

    if maps_dir.exists():
        for path in sorted(maps_dir.glob("*.txt")):
            if path.resolve() not in known_files:
                label = path.stem.replace("_", " ").title()
                ordered[label] = path
    return ordered


def resolve_map_path(name_or_path: str | Path) -> Path:
    """Resolve a scenario name, filename, or direct path into an existing map Path."""
    if isinstance(name_or_path, Path):
        if name_or_path.exists():
            return name_or_path
        candidate = get_maps_dir() / name_or_path.name
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"Map file not found: {name_or_path}")

    raw = str(name_or_path).strip()
    scenarios = load_scenario_maps()
    if raw in scenarios and scenarios[raw].exists():
        return scenarios[raw]

    direct = Path(raw)
    if direct.exists():
        return direct

    maps_dir = get_maps_dir()
    for candidate_name in (raw, f"{raw}.txt"):
        candidate = maps_dir / candidate_name
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"Map '{name_or_path}' not found in {maps_dir}")


def load_game_state(
    name_or_path: str | Path,
    max_turns: int = MAX_TURNS,
) -> GameState:
    """Load a GameState from a scenario name, map filename, or file path."""
    path = resolve_map_path(name_or_path)
    return GameState.from_file(path, max_turns=max_turns)
