"""Collect reproducible report metrics without editing the production solver."""

import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import sys
from time import perf_counter
import tracemalloc
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models.board import KakuroBoard
from models.constraint import SumConstraint
from solver.backtracking import CSPSolver
import solver.backtracking as search_module
from solver.propagation import enforce_gac


def validate(board):
    """Check clues independently. Parameters: board. Returns: solution bool."""
    for row, cells in enumerate(board.grid):
        for col, cell in enumerate(cells):
            if not isinstance(cell, dict):
                continue
            for direction, total in cell.items():
                dr, dc = (0, 1) if direction == 'across' else (1, 0)
                r, c, digits = row + dr, col + dc, []
                while (r, c) in board.variables:
                    digits.append(board.variables[r, c].value)
                    r, c = r + dr, c + dc
                if (any(type(d) is not int or not 1 <= d <= 9 for d in digits)
                        or len(set(digits)) != len(digits)
                        or sum(digits) != total):
                    return False
    return True


def summarize(values):
    """Summarize samples. Parameters: list of numbers. Returns: statistics."""
    ordered = sorted(values)
    return {'median': statistics.median(values),
            'mean': statistics.mean(values), 'min': min(values),
            'max': max(values), 'stdev': statistics.stdev(values),
            'p95_nearest_rank': ordered[(95 * len(values) + 99) // 100 - 1]}


def instrument(board):
    """Collect counters separately. Parameters: fresh board. Returns: dict."""
    counters = {'nodes': 0, 'max_depth': 0, 'max_assigned': 0, 'gac_calls': 0,
                'filters_gac': 0, 'filters_lcv': 0, 'events': {}}
    depth = -1
    phase = 'lcv'
    original_backtrack = CSPSolver.backtrack
    original_filter = SumConstraint.filter_domain

    def backtrack(instance):
        """Count recursion. Parameters: solver. Returns: wrapped stream."""
        nonlocal depth
        depth += 1
        counters['nodes'] += 1
        counters['max_depth'] = max(counters['max_depth'], depth)
        try:
            return (yield from original_backtrack(instance))
        finally:
            depth -= 1

    def gac(instance, constraints=None):
        """Track filter context. Parameters: board, runs. Returns: stream."""
        nonlocal phase
        counters['gac_calls'] += 1
        stream = enforce_gac(instance, constraints)
        while True:
            phase = 'gac'
            try:
                event = next(stream)
            except StopIteration as result:
                phase = 'lcv'
                return result.value
            phase = 'lcv'
            yield event

    def filter_domain(instance, overrides=None):
        """Count support calls. Parameters: run, overrides. Returns: supports."""
        counters['filters_' + phase] += 1
        return original_filter(instance, overrides)

    with (patch.object(CSPSolver, 'backtrack', backtrack),
          patch.object(SumConstraint, 'filter_domain', filter_domain),
          patch.object(search_module, 'enforce_gac', gac)):
        solver = CSPSolver(board)
        for event in solver.events():
            events = counters['events']
            events[event.kind] = events.get(event.kind, 0) + 1
            counters['max_assigned'] = max(
                counters['max_assigned'],
                sum(v.value is not None for v in board.variables.values()))
    counters.update(vars(solver.stats))
    counters.pop('elapsed')
    return counters


def measure(filename, repetitions):
    """Measure a fixture. Parameters: filename, run count. Returns: result."""
    path = ROOT / 'test_cases' / filename
    board = KakuroBoard.from_json(path)
    expected = filename == 'board_9x9.json'
    for _ in range(5):
        board.reset()
        CSPSolver(board).solve()
    durations, compute, correct = [], [], 0
    for _ in range(repetitions):
        board.reset()
        solver = CSPSolver(board)
        start = perf_counter()
        result = solver.solve()
        durations.append((perf_counter() - start) * 1000)
        compute.append(solver.stats.elapsed * 1000)
        if expected:
            correct += result and validate(board)
        else:
            correct += not result and all(v.value is None
                                         and v.domain == set(range(1, 10))
                                         for v in board.variables.values())
    peaks, retained = [], []
    for _ in range(20):
        board.reset()
        solver = CSPSolver(board)
        gc.collect()
        tracemalloc.start()
        solver.solve()
        _, peak = tracemalloc.get_traced_memory()
        gc.collect()
        current, _ = tracemalloc.get_traced_memory()
        peaks.append(peak)
        retained.append(current)
        tracemalloc.stop()
    board.reset()
    propagation = enforce_gac(board)
    initial_events = 0
    try:
        while True:
            next(propagation)
            initial_events += 1
    except StopIteration as end:
        initial_consistent = end.value
    initial = {'consistent': initial_consistent, 'events': initial_events,
               'singletons': sum(len(v.domain) == 1
                                 for v in board.variables.values()),
               'remaining_values': sum(len(v.domain)
                                       for v in board.variables.values())}
    board.reset()
    counts = instrument(board)
    degrees = [len(n) for n in board.neighbors.values()]
    return {'fixture': filename, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'variables': len(board.variables), 'constraints': len(board.constraints),
            'max_run': max(len(c.scope) for c in board.constraints),
            'max_degree': max(degrees), 'repetitions': repetitions,
            'expected_result': expected, 'correct': correct,
            'wall_ms': summarize(durations), 'wall_samples_ms': durations,
            'compute_ms': summarize(compute),
            'memory_runs': 20, 'peak_bytes': summarize(peaks),
            'post_gc_bytes': summarize(retained),
            'initial_gac': initial, 'counters': counts}


def main():
    """Write measurements. Parameters: none. Returns: None."""
    files = sorted((ROOT / 'models').glob('*.py'))
    files += sorted((ROOT / 'solver').glob('*.py'))
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    data = {'date_local': '2026-11-15', 'timezone': 'Asia/Saigon',
            'python': sys.version, 'platform': platform.platform(),
            'processor_identifier': os.environ.get('PROCESSOR_IDENTIFIER'),
            'logical_processors': os.cpu_count(), 'source_sha256': digest.hexdigest(),
            'warmup_runs': 5, 'cases': [measure('board_9x9.json', 100),
                                       measure('board_unsatisfiable.json', 50)]}
    output = ROOT / 'docs' / 'report_measurements.json'
    output.write_text(json.dumps(data, indent=2), encoding='utf-8')
    for case in data['cases']:
        print(case['fixture'], case['wall_ms'], case['counters'])


if __name__ == '__main__':
    main()
