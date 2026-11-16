"""Observer contract; this module has no Pygame dependency."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SolverEvent:
    """Immutable notice. Parameters: kind, position, value, removed.

    Returns: an event instance carrying a solver state change.
    """

    kind: str
    position: tuple[int, int] | None = None
    value: int | None = None
    removed: tuple[int, ...] = ()


class SolverCallback(Protocol):
    """Observer interface. Parameters: none.

    Returns: a contract implemented structurally by a view or logger.
    """

    def on_event(self, event: SolverEvent) -> None:
        """Observe current model. Parameters: event. Returns: None."""
        ...
