"""Combined n-ary Sum and All-Different constraints."""

from functools import lru_cache

from .variable import Variable


class SumConstraint:
    """Store a Kakuro run. Parameters: target_sum, scope, direction.

    Returns: a combined Sum and All-Different constraint instance.
    """

    def __init__(self, target_sum: int, scope: list[Variable],
                 direction: str) -> None:
        """Initialize a run. Parameters: sum, cells, direction. Returns:
        None.
        """
        self.target_sum = target_sum
        self.scope = scope
        self.direction = direction

    def is_satisfied(self) -> bool:
        """Check a complete run. Parameters: none. Returns: constraint
        truth.
        """
        values = [v.value for v in self.scope]
        return (None not in values and len(set(values)) == len(values)
                and sum(values) == self.target_sum)

    def filter_domain(self, overrides: dict | None = None) -> dict:
        """Compute exact GAC supports without changing variables.

        Parameters: optional variable-to-domain overrides for LCV probes.
        Returns: mapping of each variable to its supported digit set.
        A memoized support search enforces sum and distinctness together.
        Caches are local to this call and released afterwards.
        """
        overrides = overrides or {}
        domains = [
            tuple(sorted(overrides.get(v, v.domain)
                         & ({v.value} if v.value else set(range(1, 10)))))
            for v in self.scope
        ]
        supports = {v: set() for v in self.scope}
        size = len(domains)

        @lru_cache(maxsize=None)
        def feasible(index: int, used: int, remaining: int) -> bool:
            """Test a suffix. Parameters: index, digit mask, sum. Returns:
            bool.
            """
            if index == size:
                return remaining == 0
            available = [d for d in range(1, 10) if not used & (1 << d)]
            count = size - index
            if (len(available) < count or remaining < sum(available[:count])
                    or remaining > sum(available[-count:])):
                return False
            return any(not used & (1 << d)
                       and feasible(index + 1, used | (1 << d), remaining - d)
                       for d in domains[index])

        visited = set()

        def collect(index: int, used: int, remaining: int) -> None:
            """Collect supports. Parameters: suffix state. Returns: None."""
            state = (index, used, remaining)
            if index == size or state in visited:
                return
            visited.add(state)
            for digit in domains[index]:
                if (not used & (1 << digit)
                        and feasible(index + 1, used | (1 << digit),
                                     remaining - digit)):
                    supports[self.scope[index]].add(digit)
                    collect(index + 1, used | (1 << digit), remaining - digit)

        if feasible(0, 0, self.target_sum):
            collect(0, 0, self.target_sum)
        return supports
