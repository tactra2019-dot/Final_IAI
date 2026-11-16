"""PyGame GUI package for Tank Battle (lazy imports for headless safety)."""

from __future__ import annotations

import importlib
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

__all__ = ["GameRenderer", "SetupMenu", "TankBattleApp", "theme"]


def __getattr__(name: str):
    if name == "theme":
        return importlib.import_module("task2.ui.theme")
    if name == "SetupMenu":
        return importlib.import_module("task2.ui.menu").SetupMenu
    if name in ("GameRenderer", "TankBattleApp"):
        return getattr(importlib.import_module("task2.ui.renderer"), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
