# Task 1: N-Queens with CNF, Glucose3, and Min-Conflicts

Python 3 implementation of Task 1 for Introduction to Artificial Intelligence. The code separates the board model, SAT encoding and solver, local search, experiments, charts, and CLI. All measured results are generated at run time.

## Architecture

| Module | Main class | Responsibility |
| --- | --- | --- |
| `models/cnf.py` | `NQueensCNF`, `CNFModel` | Map cells to literals and generate pairwise CNF |
| `models/board.py` | `Board` | Independently validate and render solutions |
| `solvers/sat.py` | `Glucose3Solver` | Solve CNF, extract a model, and release solver resources |
| `solvers/min_conflicts.py` | `MinConflictsSolver` | Standard and improved local search |
| `benchmarks/runner.py` | `BenchmarkRunner` | Repeated timed trials and CSV/JSON export |
| `benchmarks/charts.py` | `BenchmarkCharts` | Six PNG plots from measured data |
| `main.py` | CLI functions | Interactive menu and scriptable subcommands |

Coordinates and list indexes are zero based. The SAT variable for row `i`, column `j` is `Q(i,j) = i*N + j + 1`, a positive PySAT literal. A negative literal means the cell is empty.

## Propositional model and CNF

For each row `i`:

- At least one queen: `Q(i,0) OR ... OR Q(i,N-1)` (one clause).
- At most one queen: `NOT Q(i,j) OR NOT Q(i,k)` for every `j < k`.

For each column `j`, add `NOT Q(i,j) OR NOT Q(k,j)` for every `i < k`. For each pair of distinct cells on the same diagonal, add the same negative pairwise clause. With one queen per row, at most one per column, and `N` rows, every valid assignment has exactly `N` queens and exactly one per column.

The clause count is

```text
N                      row at-least-one
+ N * C(N, 2)          row at-most-one
+ N * C(N, 2)          column at-most-one
+ 2 * sum(d=1..N-1) (N-d)^2   both diagonal directions
= (5N^3 - 6N^2 + 4N) / 3
```

For `N=4`, the model has `16` variables and `80` clauses. The generator checks its actual count against the formula; tests also detect duplicate clauses and validate representative satisfying and attacking assignments.

## Solvers

**Glucose3:** `Glucose3Solver` uses PySAT's `Glucose3(bootstrap_with=clauses)` context manager, calls `solve()`, extracts positive cell literals, and validates the resulting board independently. The `solver_seconds` interval includes solver construction, clause loading, solving, model extraction, and cleanup. CNF generation is measured separately. An UNSAT result has no queens and `valid=False`.

**Standard Min-Conflicts:** one queen per column. Randomly choose a conflicted column, then choose a row with the fewest attacks. Break ties randomly. The chosen row can be the current row, as in the standard algorithm. Stop on a zero-conflict board or after `max_steps` for each attempt. Up to `max_restarts` further initial boards are tried.

**Improved Min-Conflicts:** choose a column with the *largest* current number of attacks (Most-Conflicted Variable), breaking ties randomly. Row choice, restart policy, and limits are identical to Standard. Both variants use the same independently seeded initial board for each `(seed, restart)` pair; choice randomness follows its own stream. This isolates the variable-selection heuristic as far as practical, although the subsequent search paths naturally differ. The heuristic is a hypothesis, not a guaranteed speedup.

The algorithm maintains row and diagonal occupancy counts. Its `conflicts` value is the final number of attacking queen pairs; `cumulative_conflicts` sums the attacking pairs observed at every checked state, including restart states. A failed run returns no board and `success=False`. All reported successful boards pass `Board.validate`.

## Install

From the workspace root, use Python 3.10 or newer:

```bash
python -m venv .venv
```

Activate on Windows: `.venv\Scripts\activate`. Activate on macOS: `source .venv/bin/activate`. Then:

```bash
python -m pip install -r task1/requirements.txt
python -m pytest task1/tests -q
```

Use the same `python` executable for install, tests, and demo. PySAT distributes platform and Python-version-specific wheels. If installation fails on a particular Python version, use a Python version for which `python-sat` provides a wheel.

## Demo and benchmarks

Run from the workspace root:

```bash
python -m task1.main                  # interactive 0–7 menu
python -m task1.main stats 4
python -m task1.main sat 8
python -m task1.main standard 20 --max-steps 1000 --max-restarts 10 --seed 42
python -m task1.main improved 20 --max-steps 1000 --max-restarts 10 --seed 42
python -m task1.main sat-benchmark --sizes 4,5,6,8,10,12,16,20,30,50 --repeats 3
python -m task1.main compare --sizes 4,5,6,8,10,12,16,20,30,50 --trials 10 --seed 42
python -m task1.main export --sizes 4,5,6,8,10,12,16,20,30,50 --repeats 3 --trials 10 --seed 42
```

`export` runs both benchmarks, writes CSV/JSON, and creates all six PNG figures under `task1/results/`. Change the destination with `--out PATH`. The JSON files include configuration, platform, per-trial results, and summary statistics. CSV files have flattened summary columns. A single repetition has standard deviation zero by convention. Times are seconds from `time.perf_counter()`; mean, median, sample standard deviation, minimum, and maximum are computed from actual trials. `success_rate` uses all trials, including failures. Runtime and step summaries also use all trials, so compare success rates before interpreting speed. The six plots show clauses, Glucose3 time, each Min-Conflicts time, success rate, and average steps.

Use `python -m pytest task1/tests -q` to verify the encoding, independent validator, solvers, failure handling, exports, charts, and CLI input checks. To inspect a returned board, verify that each of its `N` rows and columns has exactly one `Q` and no two `Q` cells share a diagonal. This is also what the independent validator does.

## Experimental interpretation and limits

Benchmark times depend on processor, Python version, PySAT build, other system load, chosen seeds, and trial count. The experiments are reproducible by configuration and seed, but timing varies. Do not claim the improved heuristic wins unless its measured success rate and runtime support that claim on the tested sizes. Prefer more repetitions for reliable comparisons.

Pairwise CNF requires `O(N^3)` clauses and can become memory intensive for large `N`. Glucose3 can have highly variable search time. Min-Conflicts is incomplete with finite step and restart limits and can fail even though a solution exists. The benchmark only supports `N>=4` as required; it does not attempt to model the known `N=2,3` UNSAT cases. Very large boards also make ASCII rendering impractical.

For oral defense: explain why row at-least-one plus row at-most-one means exactly one; why column at-most-one then forces every column to be occupied; why both diagonal slopes are checked; how the clause formula is derived; why solver timing is separated from CNF timing; how the independent validator checks the returned model; how Min-Conflicts scores a move with occupancy counters; how Most-Conflicted Variable changes only variable selection; why paired seeds help comparison; and why success rate must accompany runtime.
