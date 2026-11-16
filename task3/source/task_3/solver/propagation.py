"""Generalized arc consistency for n-ary Kakuro runs."""

from collections import deque

from .callback import SolverEvent


def enforce_gac(board, constraints=None):
    """Prune to a fixed point. Parameters: board, optional changed runs.

    Returns: generator of prune/conflict events; final return is consistency.
    Every removed digit lacks a complete sum-and-distinctness support.
    """
    queue = deque(board.constraints if constraints is None else constraints)
    pending = set(queue)
    while queue:
        constraint = queue.popleft()
        pending.remove(constraint)
        supports = constraint.filter_domain()
        for variable in constraint.scope:
            removed = variable.prune(variable.domain - supports[variable])
            if removed:
                yield SolverEvent('prune', (variable.row, variable.col),
                                  removed=tuple(sorted(removed)))
                if not variable.domain:
                    yield SolverEvent('conflict', (variable.row, variable.col))
                    return False
                for neighbor in board.memberships[variable]:
                    if neighbor is not constraint and neighbor not in pending:
                        queue.append(neighbor)
                        pending.add(neighbor)
    return True
