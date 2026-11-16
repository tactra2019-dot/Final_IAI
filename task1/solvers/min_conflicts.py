"""Standard and most-conflicted-variable Min-Conflicts."""

from collections import Counter
from dataclasses import dataclass
from random import Random
from time import perf_counter
from typing import Literal

from task1.models.board import Board

Variant = Literal["standard", "improved"]


@dataclass(frozen=True)
class MinConflictsResult:
    n: int
    variant: Variant
    success: bool
    queens: tuple[tuple[int, int], ...]
    steps: int
    restarts: int
    conflicts: int
    cumulative_conflicts: int
    runtime_seconds: float
    seed: int


class MinConflictsSolver:
    def __init__(self, variant: Variant = "standard") -> None:
        if variant not in ("standard", "improved"):
            raise ValueError("Variant must be 'standard' or 'improved'")
        self.variant = variant

    @staticmethod
    def initial_rows(n: int, seed: int, restart: int) -> list[int]:
        """Independent RNG ensures both variants see identical restart boards."""
        rng = Random(f"{seed}:{restart}:initial")
        return [rng.randrange(n) for _ in range(n)]

    @staticmethod
    def _counters(rows: list[int]) -> tuple[Counter[int], Counter[int], Counter[int]]:
        row_counts = Counter(rows)
        down_counts = Counter(row - col for col, row in enumerate(rows))
        up_counts = Counter(row + col for col, row in enumerate(rows))
        return row_counts, down_counts, up_counts

    @staticmethod
    def _total_conflicts(counts: tuple[Counter[int], Counter[int], Counter[int]]) -> int:
        return sum(value * (value - 1) // 2 for counter in counts for value in counter.values())

    @staticmethod
    def _queen_conflicts(
        rows: list[int], col: int, counts: tuple[Counter[int], Counter[int], Counter[int]]
    ) -> int:
        row = rows[col]
        return counts[0][row] + counts[1][row - col] + counts[2][row + col] - 3

    @staticmethod
    def _candidate_conflicts(
        row: int, col: int, current_row: int,
        counts: tuple[Counter[int], Counter[int], Counter[int]],
    ) -> int:
        own = int(row == current_row)
        return (
            counts[0][row] + counts[1][row - col] + counts[2][row + col] - 3 * own
        )

    def solve(
        self, n: int, *, max_steps: int = 1000, max_restarts: int = 10, seed: int = 0
    ) -> MinConflictsResult:
        if isinstance(n, bool) or not isinstance(n, int) or n < 4:
            raise ValueError("N must be an integer >= 4")
        if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 0:
            raise ValueError("max_steps must be a nonnegative integer")
        if isinstance(max_restarts, bool) or not isinstance(max_restarts, int) or max_restarts < 0:
            raise ValueError("max_restarts must be a nonnegative integer")
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ValueError("seed must be an integer")

        start = perf_counter()
        moves = 0
        cumulative_conflicts = 0
        rng = Random(seed)
        for restart in range(max_restarts + 1):
            rows = self.initial_rows(n, seed, restart)
            counts = self._counters(rows)
            for step in range(max_steps + 1):
                total = self._total_conflicts(counts)
                cumulative_conflicts += total
                if total == 0:
                    queens = tuple((row, col) for col, row in enumerate(rows))
                    if not Board.validate(n, queens):
                        raise RuntimeError("Min-Conflicts reported an invalid solution")
                    return MinConflictsResult(
                        n, self.variant, True, queens, moves, restart, 0,
                        cumulative_conflicts, perf_counter() - start, seed,
                    )
                if step == max_steps:
                    break
                conflicted = [
                    (col, self._queen_conflicts(rows, col, counts)) for col in range(n)
                    if self._queen_conflicts(rows, col, counts) > 0
                ]
                if self.variant == "improved":
                    maximum = max(score for _, score in conflicted)
                    choices = [col for col, score in conflicted if score == maximum]
                else:
                    choices = [col for col, _ in conflicted]
                col = rng.choice(choices)
                current_row = rows[col]
                scores = [self._candidate_conflicts(row, col, current_row, counts) for row in range(n)]
                minimum = min(scores)
                row = rng.choice([candidate for candidate, score in enumerate(scores) if score == minimum])
                if row != current_row:
                    counts[0][current_row] -= 1
                    counts[1][current_row - col] -= 1
                    counts[2][current_row + col] -= 1
                    rows[col] = row
                    counts[0][row] += 1
                    counts[1][row - col] += 1
                    counts[2][row + col] += 1
                moves += 1
        return MinConflictsResult(
            n, self.variant, False, (), moves, max_restarts,
            self._total_conflicts(counts), cumulative_conflicts,
            perf_counter() - start, seed,
        )
