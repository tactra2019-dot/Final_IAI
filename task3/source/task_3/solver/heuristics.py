"""Lecture 08 variable and value ordering heuristics."""


def select_unassigned_variable_mrv_degree(board):
    """Choose MRV, then maximum degree. Parameters: board. Returns: cell or
    None.
    """
    unassigned = [v for v in board.variables.values() if v.value is None]
    return min(unassigned, key=lambda v: (
        len(v.domain), -sum(n.value is None for n in board.neighbors[v]),
        v.row, v.col), default=None)


def order_domain_values_lcv(board, variable):
    """Order by fewest local deletions. Parameters: board, cell. Returns:
    digits.

    Exact supports in incident runs estimate the number of eliminated
    neighbor values; speculative evaluation never mutates the live model
    or emits events.
    """
    scores = []
    for digit in sorted(variable.domain):
        allowed = {n: n.domain.copy() for n in board.neighbors[variable]
                   if n.value is None}
        impossible = False
        for constraint in board.memberships[variable]:
            supports = constraint.filter_domain({variable: {digit}})
            impossible |= not supports[variable]
            for neighbor in constraint.scope:
                if neighbor in allowed:
                    allowed[neighbor] &= supports[neighbor]
        loss = sum(len(n.domain) - len(domain)
                   for n, domain in allowed.items())
        scores.append((impossible, loss, digit))
    return [digit for _, _, digit in sorted(scores)]
