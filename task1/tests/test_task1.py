"""Algorithm, encoding, export, and CLI checks."""

import csv
import json

import pytest

from task1.benchmarks.charts import BenchmarkCharts
from task1.benchmarks.runner import BenchmarkRunner
from task1.main import main
from task1.models.board import Board
from task1.models.cnf import CNFModel, NQueensCNF
from task1.solvers.min_conflicts import MinConflictsSolver
from task1.solvers.sat import Glucose3Solver


@pytest.mark.parametrize("n", [4, 5, 6, 8, 10])
def test_cnf_counts_uniqueness_and_mapping(n):
    encoder = NQueensCNF(n)
    model = encoder.build()
    assert model.variable_count == n * n
    assert model.clause_count == NQueensCNF.theoretical_clause_count(n)
    assert len({tuple(sorted(clause)) for clause in model.clauses}) == model.clause_count
    assert {encoder.variable(row, col) for row in range(n) for col in range(n)} == set(range(1, n * n + 1))


def test_n4_exact_counts():
    model = NQueensCNF(4).build()
    assert (model.variable_count, model.clause_count) == (16, 80)


def test_cnf_accepts_solution_and_rejects_attacks():
    n = 4
    model = NQueensCNF(n).build()

    def satisfies(queens):
        true_literals = {row * n + col + 1 for row, col in queens}
        return all(any((literal in true_literals) if literal > 0 else (-literal not in true_literals)
                       for literal in clause) for clause in model.clauses)

    assert satisfies([(1, 0), (3, 1), (0, 2), (2, 3)])
    for invalid in (
        [], [(0, 0), (0, 1), (2, 2), (3, 3)],
        [(0, 0), (1, 0), (2, 2), (3, 3)],
        [(0, 0), (1, 1), (2, 2), (3, 3)],
    ):
        assert not satisfies(invalid)


@pytest.mark.parametrize("n", [4, 5, 6, 8])
def test_glucose3_solution(n):
    pytest.importorskip("pysat")
    result = Glucose3Solver().solve(NQueensCNF(n).build())
    assert result.satisfiable and result.valid
    assert Board.validate(n, result.queens)


def test_glucose3_unsat_result():
    pytest.importorskip("pysat")
    result = Glucose3Solver().solve(CNFModel(4, [[1], [-1]]))
    assert not result.satisfiable
    assert not result.valid
    assert result.queens == ()


@pytest.mark.parametrize("queens", [
    [(0, 0), (0, 1), (2, 2), (3, 3)],
    [(0, 0), (1, 0), (2, 2), (3, 3)],
    [(0, 0), (1, 1), (2, 2), (3, 3)],
])
def test_validator_rejects_attacks(queens):
    assert not Board.validate(4, queens)


@pytest.mark.parametrize("variant", ["standard", "improved"])
@pytest.mark.parametrize("n", [4, 5, 6, 8])
def test_min_conflicts_success_is_valid(variant, n):
    result = MinConflictsSolver(variant).solve(n, max_steps=2000, max_restarts=10, seed=42)
    assert result.success
    assert Board.validate(n, result.queens)
    assert result.conflicts == 0


@pytest.mark.parametrize("variant", ["standard", "improved"])
def test_min_conflicts_failure_is_not_false_success(variant):
    result = MinConflictsSolver(variant).solve(8, max_steps=0, max_restarts=0, seed=0)
    assert not result.success
    assert not result.queens
    assert result.conflicts > 0


def test_comparison_uses_same_initial_state():
    assert MinConflictsSolver("standard").initial_rows(20, 7, 2) == MinConflictsSolver("improved").initial_rows(20, 7, 2)


def test_benchmark_exports_and_charts(tmp_path):
    runner = BenchmarkRunner()
    sat = runner.sat([4, 5], repeats=2)
    comparison = runner.compare([4, 5], trials_per_size=2, max_steps=200, max_restarts=3, seed=42)
    paths = runner.export(sat, tmp_path) + runner.export(comparison, tmp_path)
    assert all(path.is_file() for path in paths)
    assert len(list(csv.DictReader((tmp_path / "sat_trials.csv").open(encoding="utf-8")))) == 4
    assert json.loads((tmp_path / "min_conflicts.json").read_text(encoding="utf-8"))["kind"] == "min_conflicts"
    charts = BenchmarkCharts.create(sat, comparison, tmp_path)
    assert len(charts) == 6
    assert all(path.stat().st_size > 0 for path in charts)


@pytest.mark.parametrize("args", [["stats", "3"], ["sat", "abc"], ["compare", "--sizes", "4,3"], ["compare", "--trials", "0"]])
def test_invalid_cli_parameters_exit_cleanly(args):
    with pytest.raises(SystemExit) as exc:
        main(args)
    assert exc.value.code == 2


@pytest.mark.parametrize("n", [0, -1, 3, 4.0, True])
def test_invalid_board_size(n):
    with pytest.raises(ValueError):
        NQueensCNF(n)
