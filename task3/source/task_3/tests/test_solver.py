"""Independent correctness oracles and reversible-search regression tests."""

import itertools
from pathlib import Path
import random
from types import SimpleNamespace
import unittest

from models.board import KakuroBoard
from models.constraint import SumConstraint
from models.variable import Variable
from solver.backtracking import CSPSolver
from solver.heuristics import (
    order_domain_values_lcv,
    select_unassigned_variable_mrv_degree,
)


BOARD = Path(__file__).resolve().parents[1] / 'test_cases' / 'board_9x9.json'


class SolverTests(unittest.TestCase):
    """Check CSP semantics and search lifecycle. Parameters: unittest
    defaults.

    Returns: a unittest test-case instance.
    """

    def test_pdf_solution_independently(self):
        """Check all clue sums/distinctness. Parameters: none. Returns:
        None.
        """
        board = KakuroBoard.from_json(BOARD)
        self.assertEqual(len(board.variables), 48)
        self.assertEqual(len(board.constraints), 28)
        solver = CSPSolver(board)
        self.assertTrue(solver.solve())
        # Walk original clues independently instead of calling is_solved only.
        for row, cells in enumerate(board.grid):
            for col, cell in enumerate(cells):
                if not isinstance(cell, dict):
                    continue
                for direction, target in cell.items():
                    dr, dc = (0, 1) if direction == 'across' else (1, 0)
                    r, c, digits = row + dr, col + dc, []
                    while (r, c) in board.variables:
                        digit = board.variables[r, c].value
                        self.assertIn(digit, range(1, 10))
                        digits.append(digit)
                        r, c = r + dr, c + dc
                    self.assertEqual(sum(digits), target)
                    self.assertEqual(len(digits), len(set(digits)))

    def test_gac_against_exhaustive_oracle(self):
        """Compare supports to brute force. Parameters: none. Returns: None."""
        rng = random.Random(42)
        for length in (2, 3, 4):
            for _ in range(20):
                cells = [
                    Variable(0, i, domain=set(rng.sample(range(1, 10), 4)))
                    for i in range(length)
                ]
                target = rng.randint(3, 30)
                constraint = SumConstraint(target, cells, 'across')
                expected = {v: set() for v in cells}
                for digits in itertools.product(*(v.domain for v in cells)):
                    if len(set(digits)) == length and sum(digits) == target:
                        for variable, digit in zip(cells, digits):
                            expected[variable].add(digit)
                self.assertEqual(constraint.filter_domain(), expected)

    def test_heuristics_and_no_speculative_mutation(self):
        """Check MRV/Degree and LCV. Parameters: none. Returns: None."""
        a = Variable(0, 0, domain={1, 2})
        b = Variable(0, 1, domain={2, 3})
        c = Variable(0, 2, domain={1, 2, 3})
        run = SumConstraint(6, [a, b, c], 'across')
        board = SimpleNamespace(variables={0: a, 1: b, 2: c},
                                neighbors={a: {b, c}, b: {a}, c: {a}},
                                memberships={a: [run], b: [run], c: [run]})
        self.assertIs(select_unassigned_variable_mrv_degree(board), a)
        self.assertEqual(order_domain_values_lcv(board, a), [1, 2])
        self.assertEqual(a.domain, {1, 2})
        self.assertIsNone(a.value)
        c.domain = {1}
        self.assertIs(select_unassigned_variable_mrv_degree(board), c)

    def test_unsatisfiable_search_restores_every_branch(self):
        """Force real conflicts/backtracks. Parameters: none. Returns: None."""
        board = KakuroBoard([
            ['#', {'down': 15}, {'down': 15}, {'down': 16}],
            [{'across': 15}, '.', '.', '.'],
            [{'across': 15}, '.', '.', '.'],
            [{'across': 15}, '.', '.', '.'],
        ])
        kinds = set()
        solver = CSPSolver(board)
        for event in solver.events():
            kinds.add(event.kind)
            if event.kind == 'conflict':
                self.assertFalse(board.variables[event.position].domain)
            if event.kind == 'assign':
                variable = board.variables[event.position]
                self.assertEqual(variable.domain, {variable.value})
        self.assertTrue({'assign', 'prune', 'conflict', 'backtrack', 'restore',
                         'unsatisfiable'} <= kinds)
        self.assertGreater(solver.stats.backtracks, 0)
        for variable in board.variables.values():
            self.assertIsNone(variable.value)
            self.assertEqual(variable.domain, set(range(1, 10)))

    def test_cancel_and_callback_error_restore_state(self):
        """Verify interruption cleanup. Parameters: none. Returns: None."""
        board = KakuroBoard.from_json(BOARD)
        solver = CSPSolver(board)
        stream = solver.events()
        next(stream)
        stream.close()
        self.assertFalse(solver.running)
        self.assertTrue(all(v.domain == set(range(1, 10))
                            for v in board.variables.values()))

        class FailingObserver:
            """Simulate an observer failure. Parameters: none.

            Returns: a failing observer instance.
            """

            def on_event(self, event):
                """Raise deliberately. Parameters: event. Returns: never."""
                raise RuntimeError('observer failed')

        solver = CSPSolver(board, FailingObserver())
        with self.assertRaisesRegex(RuntimeError, 'observer failed'):
            solver.solve()
        self.assertFalse(solver.running)
        self.assertTrue(all(v.domain == set(range(1, 10))
                            for v in board.variables.values()))

    def test_repeatability(self):
        """Repeat solves on one model. Parameters: none. Returns: None."""
        board = KakuroBoard.from_json(BOARD)
        solutions = set()
        for _ in range(25):
            board.reset()
            self.assertTrue(CSPSolver(board).solve())
            solutions.add(tuple(v.value for v in board.variables.values()))
        self.assertEqual(len(solutions), 1)

    def test_invalid_configurations(self):
        """Reject malformed topology. Parameters: none. Returns: None."""
        for grid in ([], [['#'], ['#', '.']], [['.']],
                     [['#', {'down': 99}], [{'across': 3}, '.']],
                     [['#', {'sideways': 3}]]):
            with self.subTest(grid=grid), self.assertRaises(ValueError):
                KakuroBoard(grid)


if __name__ == '__main__':
    unittest.main()
