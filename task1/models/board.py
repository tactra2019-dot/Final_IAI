"""Independent N-Queens solution validation and display."""

from collections.abc import Sequence


class Board:
    @staticmethod
    def validate(n: int, queens: Sequence[tuple[int, int]]) -> bool:
        if n < 1 or len(queens) != n:
            return False
        if any(not (0 <= row < n and 0 <= col < n) for row, col in queens):
            return False
        return all(
            len({key(row, col) for row, col in queens}) == n
            for key in (
                lambda row, col: row,
                lambda row, col: col,
                lambda row, col: row - col,
                lambda row, col: row + col,
            )
        )

    @staticmethod
    def render(n: int, queens: Sequence[tuple[int, int]]) -> str:
        if not Board.validate(n, queens):
            raise ValueError("Cannot render an invalid N-Queens solution")
        occupied = set(queens)
        return "\n".join(
            " ".join("Q" if (row, col) in occupied else "." for col in range(n))
            for row in range(n)
        )
