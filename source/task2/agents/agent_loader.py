"""Dynamic agent plugin loader with fault-tolerant execution sandbox."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
import threading
from pathlib import Path

from source.task2.agents.alphabeta_agent import AlphaBetaAgent
from source.task2.agents.base_agent import BaseAgent
from source.task2.agents.heuristic_ab_agent import HeuristicAlphaBetaAgent
from source.task2.agents.heuristic_mm_agent import HeuristicMinimaxAgent
from source.task2.agents.minimax_agent import MinimaxAgent
from source.task2.core.actions import Action
from source.task2.core.constants import EXTERNAL_AGENT_TIMEOUT_SEC
from source.task2.core.game_state import GameState


class AgentLoader:
    """Discovers built-in and external BaseAgent plugins and executes them safely."""

    @staticmethod
    def get_builtin_agents() -> dict[str, type[BaseAgent]]:
        """Return mapping of built-in agent class names to their classes."""
        return {
            "MinimaxAgent": MinimaxAgent,
            "AlphaBetaAgent": AlphaBetaAgent,
            "HeuristicMinimaxAgent": HeuristicMinimaxAgent,
            "HeuristicAlphaBetaAgent": HeuristicAlphaBetaAgent,
        }

    @staticmethod
    def discover_external_agents(
        external_dir: str | Path | None = None,
    ) -> dict[str, type[BaseAgent]]:
        """Dynamically scan external_dir for .py modules defining BaseAgent subclasses."""
        target_dir = (
            Path(external_dir)
            if external_dir is not None
            else Path(__file__).resolve().parent / "external"
        )
        if not target_dir.is_dir():
            return {}

        importlib.invalidate_caches()
        discovered: dict[str, type[BaseAgent]] = {}

        for py_file in sorted(target_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue

            module_name = f"source.task2.agents.external.{py_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, py_file)
            if spec is None or spec.loader is None:
                continue

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
            except Exception:
                sys.modules.pop(module_name, None)
                continue

            for obj in vars(module).values():
                if (
                    isinstance(obj, type)
                    and issubclass(obj, BaseAgent)
                    and obj is not BaseAgent
                    and not inspect.isabstract(obj)
                    and obj.__module__ == module.__name__
                ):
                    key = obj.__name__
                    if key in discovered:
                        key = f"{obj.__name__}_{py_file.stem}"
                    discovered[key] = obj

        return discovered

    @staticmethod
    def get_all_agent_classes(
        external_dir: str | Path | None = None,
    ) -> dict[str, type[BaseAgent]]:
        """Return merged mapping of all built-in and discovered external agent classes."""
        classes = AgentLoader.get_builtin_agents()
        external = AgentLoader.discover_external_agents(external_dir=external_dir)
        for name, cls in external.items():
            key = name if name not in classes else f"{name}_external"
            classes[key] = cls
        return classes

    @staticmethod
    def safe_get_action(
        agent: object,
        state: GameState,
        timeout_sec: float = EXTERNAL_AGENT_TIMEOUT_SEC,
    ) -> Action:
        """Execute agent.get_action(state.clone()) with timeout and output validation."""
        if agent is None or not callable(getattr(agent, "get_action", None)):
            return Action.STAY
        if state.is_terminal():
            return Action.STAY

        try:
            state_copy = state.clone()
        except Exception:
            return Action.STAY

        effective_timeout = max(0.001, float(timeout_sec))
        result_box: list[object] = []
        error_box: list[BaseException] = []

        def _worker() -> None:
            try:
                result_box.append(agent.get_action(state_copy))  # type: ignore[attr-defined]
            except BaseException as exc:
                error_box.append(exc)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        thread.join(timeout=effective_timeout)

        if thread.is_alive() or error_box or not result_box:
            return Action.STAY

        raw_action = result_box[0]
        if isinstance(raw_action, Action):
            return raw_action
        if isinstance(raw_action, str):
            normalized = raw_action.strip().upper()
            try:
                return Action[normalized]
            except KeyError:
                return Action.STAY
        return Action.STAY
