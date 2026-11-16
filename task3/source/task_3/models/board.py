"""Validated JSON configuration and Kakuro constraint graph."""

import json
from pathlib import Path

from .constraint import SumConstraint
from .variable import Variable


class KakuroBoard:
    """Build a board. Parameters: rectangular grid of #, . or clue objects.

    Returns: a validated model and its variable/constraint graph.
    """

    def __init__(self, grid: list[list]) -> None:
        """Validate cells and build runs. Parameters: grid. Returns: None."""
        if (not grid or not grid[0]
                or any(len(r) != len(grid[0]) for r in grid)):
            raise ValueError('Board must be a nonempty rectangle.')
        self.grid = grid
        self.rows, self.cols = len(grid), len(grid[0])
        self.variables = {}
        self.constraints = []
        for row, cells in enumerate(grid):
            for col, cell in enumerate(cells):
                if cell == '.':
                    self.variables[row, col] = Variable(row, col)
                elif cell != '#':
                    if (not isinstance(cell, dict) or not cell
                            or set(cell) - {'across', 'down'}
                            or any(type(n) is not int or n <= 0
                                   for n in cell.values())):
                        raise ValueError(f'Invalid cell at {(row, col)}.')
        self.memberships = {v: [] for v in self.variables.values()}
        for row, cells in enumerate(grid):
            for col, cell in enumerate(cells):
                if not isinstance(cell, dict):
                    continue
                for direction, target in cell.items():
                    dr, dc = (0, 1) if direction == 'across' else (1, 0)
                    r, c = row + dr, col + dc
                    scope = []
                    while (r, c) in self.variables:
                        scope.append(self.variables[r, c])
                        r, c = r + dr, c + dc
                    n = len(scope)
                    if not 2 <= n <= 9:
                        raise ValueError(f'Invalid run at {(row, col)}.')
                    if not n * (n + 1) // 2 <= target <= n * (19 - n) // 2:
                        raise ValueError(f'Impossible clue at {(row, col)}.')
                    constraint = SumConstraint(target, scope, direction)
                    self.constraints.append(constraint)
                    for variable in scope:
                        self.memberships[variable].append(constraint)
        if not self.variables:
            raise ValueError('Board has no white cells.')
        for variable, runs in self.memberships.items():
            directions = {r.direction for r in runs}
            if len(runs) != 2 or directions != {'across', 'down'}:
                position = (variable.row, variable.col)
                raise ValueError(f'Cell {position} needs two clues.')
        self.neighbors = {
            v: {other for run in runs for other in run.scope if other is not v}
            for v, runs in self.memberships.items()
        }

    @classmethod
    def from_json(cls, path: str | Path) -> 'KakuroBoard':
        """Read a configuration. Parameters: JSON path. Returns: validated
        board.
        """
        with open(path, encoding='utf-8') as stream:
            return cls(json.load(stream)['grid'])

    def is_solved(self) -> bool:
        """Validate all cells and runs. Parameters: none. Returns: bool."""
        return (all(v.value in v.domain and v.value in range(1, 10)
                    for v in self.variables.values())
                and all(c.is_satisfied() for c in self.constraints))

    def reset(self) -> None:
        """Reset the CSP. Parameters: none. Returns: None."""
        for variable in self.variables.values():
            variable.value = None
            variable.domain = set(range(1, 10))
