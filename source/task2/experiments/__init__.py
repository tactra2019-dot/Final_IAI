"""Headless experiment runners, scenario map loaders, and benchmark charts."""

from __future__ import annotations

import importlib

from source.task2.experiments.maps import (
    get_maps_dir,
    list_available_maps,
    load_game_state,
    load_scenario_maps,
)

__all__ = [
    "get_maps_dir",
    "list_available_maps",
    "load_game_state",
    "load_scenario_maps",
    "run_benchmark",
]


def __getattr__(name: str):
    if name == "run_benchmark":
        return importlib.import_module("source.task2.experiments.benchmark").run_benchmark
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
