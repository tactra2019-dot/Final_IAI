"""Glucose3 adapter; CNF generation is deliberately timed separately."""

from dataclasses import dataclass
from time import perf_counter

from task1.models.board import Board
from task1.models.cnf import CNFModel


@dataclass(frozen=True)
class SATResult:
    n: int
    satisfiable: bool
    queens: tuple[tuple[int, int], ...]
    valid: bool
    solver_seconds: float


class Glucose3Solver:
    def solve(self, model: CNFModel) -> SATResult:
        try:
            from pysat.solvers import Glucose3
        except ImportError as exc:
            raise RuntimeError("PySAT is missing. Install task1/requirements.txt") from exc

        start = perf_counter()
        with Glucose3(bootstrap_with=model.clauses) as solver:
            satisfiable = solver.solve()
            assignment = solver.get_model() if satisfiable else None
        elapsed = perf_counter() - start
        if not satisfiable:
            return SATResult(model.n, False, (), False, elapsed)
        if assignment is None:
            raise RuntimeError("Glucose3 reported SAT without a model")
        positive = {literal for literal in assignment if literal > 0}
        queens = tuple(
            (row, col)
            for row in range(model.n)
            for col in range(model.n)
            if row * model.n + col + 1 in positive
        )
        valid = Board.validate(model.n, queens)
        if not valid:
            raise RuntimeError("Glucose3 returned an invalid N-Queens assignment")
        return SATResult(model.n, True, queens, valid, elapsed)
