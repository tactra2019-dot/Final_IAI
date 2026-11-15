"""Mutable CSP variables with reversible domains."""

from dataclasses import dataclass, field


@dataclass(eq=False)
class Variable:
    """Represent a white cell. Parameters: row, col, value, domain.

    Identity equality makes each cell a unique CSP variable.
    Returns: a variable instance with an independent mutable domain.
    """

    row: int
    col: int
    value: int | None = None
    domain: set[int] = field(default_factory=lambda: set(range(1, 10)))

    def prune(self, values: set[int]) -> set[int]:
        """Remove values. Parameters: candidate set. Returns: removed
        values.
        """
        removed = self.domain & values
        self.domain.difference_update(removed)
        return removed

    def restore(self, values: set[int]) -> None:
        """Restore pruned values. Parameters: removed set. Returns: None."""
        self.domain.update(values)
