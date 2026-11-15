"""Backtracking controller exposing a lazy, observable event stream."""

from dataclasses import dataclass
from time import perf_counter

from .callback import SolverEvent
from .heuristics import (
    order_domain_values_lcv,
    select_unassigned_variable_mrv_degree,
)
from .propagation import enforce_gac


@dataclass
class SolverStats:
    """Search counters. Parameters: assignments, backtracks, pruned,
    elapsed.

    Returns: a mutable search-statistics instance.
    """

    assignments: int = 0
    backtracks: int = 0
    pruned: int = 0
    elapsed: float = 0.0


class CSPSolver:
    """Control CSP search. Parameters: model board and optional observer.

    Returns: an independent search controller instance.
    """

    def __init__(self, board, callback=None):
        """Initialize search. Parameters: board, callback. Returns: None."""
        self.board = board
        self.callback = callback
        self.stats = SolverStats()
        self.running = False

    def _snapshot(self):
        """Capture reversible state. Parameters: none. Returns: state
        mapping.
        """
        return {v: (v.value, v.domain.copy())
                for v in self.board.variables.values()}

    def _restore(self, snapshot):
        """Restore a branch. Parameters: saved mapping. Returns: event
        generator.
        """
        for variable, (value, domain) in snapshot.items():
            if variable.value != value or variable.domain != domain:
                variable.value = value
                variable.restore(domain - variable.domain)
                variable.domain.intersection_update(domain)
                yield SolverEvent(
                    'restore', (variable.row, variable.col), value)

    def backtrack(self):
        """Search recursively. Parameters: none. Returns: event
        generator/bool.
        """
        variable = select_unassigned_variable_mrv_degree(self.board)
        if variable is None:
            return self.board.is_solved()
        snapshot = self._snapshot()
        for digit in order_domain_values_lcv(self.board, variable):
            variable.value = digit
            variable.domain = {digit}
            self.stats.assignments += 1
            yield SolverEvent('assign', (variable.row, variable.col), digit)
            consistent = yield from enforce_gac(
                self.board, self.board.memberships[variable])
            if consistent and (yield from self.backtrack()):
                return True
            self.stats.backtracks += 1
            yield SolverEvent('backtrack', (variable.row, variable.col), digit)
            yield from self._restore(snapshot)
        return False

    def events(self):
        """Run once lazily. Parameters: none. Returns: observable event
        iterator.

        Closing this iterator or an observer exception restores the
        input state. Unsolvable runs also restore it; successful runs
        retain the solution.
        """
        if self.running:
            raise RuntimeError('Solver already running.')
        self.running = True
        self.stats = SolverStats()
        initial = self._snapshot()
        solved = False
        try:
            def search():
                """Compose GAC/search. Parameters: none. Returns: event
                stream.
                """
                consistent = yield from enforce_gac(self.board)
                success = consistent and (yield from self.backtrack())
                if not success:
                    yield from self._restore(initial)
                return success

            stream = search()
            while True:
                tick = perf_counter()
                try:
                    event = next(stream)
                except StopIteration as result:
                    self.stats.elapsed += perf_counter() - tick
                    solved = bool(result.value)
                    break
                self.stats.elapsed += perf_counter() - tick
                self.stats.pruned += len(event.removed)
                if self.callback:
                    self.callback.on_event(event)
                yield event
            event = SolverEvent('solved' if solved else 'unsatisfiable')
            if self.callback:
                self.callback.on_event(event)
            yield event
        finally:
            if not solved:
                for variable, (value, domain) in initial.items():
                    variable.value, variable.domain = value, domain.copy()
            self.running = False

    def solve(self):
        """Consume search without UI. Parameters: none. Returns: solution
        bool.
        """
        for _ in self.events():
            pass
        return self.board.is_solved()
