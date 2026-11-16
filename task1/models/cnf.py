"""Pairwise CNF encoding for N-Queens."""

from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class CNFModel:
    n: int
    clauses: list[list[int]]

    @property
    def variable_count(self) -> int:
        return self.n * self.n

    @property
    def clause_count(self) -> int:
        return len(self.clauses)


class NQueensCNF:
    def __init__(self, n: int) -> None:
        if isinstance(n, bool) or not isinstance(n, int) or n < 4:
            raise ValueError("N must be an integer >= 4")
        self.n = n

    def variable(self, row: int, col: int) -> int:
        if not (0 <= row < self.n and 0 <= col < self.n):
            raise ValueError("Cell coordinates are outside the board")
        return row * self.n + col + 1

    @staticmethod
    def theoretical_clause_count(n: int) -> int:
        if isinstance(n, bool) or not isinstance(n, int) or n < 4:
            raise ValueError("N must be an integer >= 4")
        return (5 * n**3 - 6 * n**2 + 4 * n) // 3

    def row_clauses(self) -> list[list[int]]:
        clauses: list[list[int]] = []
        for row in range(self.n):
            cells = [self.variable(row, col) for col in range(self.n)]
            clauses.append(cells)
            clauses.extend([-a, -b] for a, b in combinations(cells, 2))
        return clauses

    def column_clauses(self) -> list[list[int]]:
        return [
            [-self.variable(row_a, col), -self.variable(row_b, col)]
            for col in range(self.n)
            for row_a, row_b in combinations(range(self.n), 2)
        ]

    def diagonal_clauses(self) -> list[list[int]]:
        clauses: list[list[int]] = []
        for row_a in range(self.n):
            for row_b in range(row_a + 1, self.n):
                distance = row_b - row_a
                for col_a in range(self.n - distance):
                    clauses.append([
                        -self.variable(row_a, col_a),
                        -self.variable(row_b, col_a + distance),
                    ])
                for col_a in range(distance, self.n):
                    clauses.append([
                        -self.variable(row_a, col_a),
                        -self.variable(row_b, col_a - distance),
                    ])
        return clauses

    def build(self) -> CNFModel:
        clauses = self.row_clauses() + self.column_clauses() + self.diagonal_clauses()
        expected = self.theoretical_clause_count(self.n)
        if len(clauses) != expected:
            raise AssertionError(f"Expected {expected} clauses, generated {len(clauses)}")
        return CNFModel(self.n, clauses)
