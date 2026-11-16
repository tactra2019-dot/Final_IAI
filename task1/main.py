"""Command-line and interactive demo. Run with: python -m task1.main"""

import argparse
import sys
from pathlib import Path
from time import perf_counter

from task1.benchmarks.charts import BenchmarkCharts
from task1.benchmarks.runner import DEFAULT_SIZES, BenchmarkRunner
from task1.models.board import Board
from task1.models.cnf import NQueensCNF
from task1.solvers.min_conflicts import MinConflictsSolver
from task1.solvers.sat import Glucose3Solver

DEFAULT_OUTPUT = Path(__file__).parent / "results"


def sizes_arg(value: str) -> list[int]:
    try:
        sizes = [int(part.strip()) for part in value.split(",")]
        if not sizes or any(n < 4 for n in sizes) or len(set(sizes)) != len(sizes):
            raise ValueError
        return sizes
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use unique comma-separated integers >= 4") from exc


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Must be >= 1")
    return number


def nonnegative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("Must be >= 0")
    return number


def board_size(value: str) -> int:
    number = int(value)
    if number < 4:
        raise argparse.ArgumentTypeError("N must be >= 4")
    return number


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description="N-Queens SAT and Min-Conflicts demo")
    sub = cli.add_subparsers(dest="command")
    for name in ("sat", "standard", "improved", "stats"):
        command = sub.add_parser(name)
        command.add_argument("n", type=board_size)
        if name in ("standard", "improved"):
            command.add_argument("--max-steps", type=nonnegative_int, default=1000)
            command.add_argument("--max-restarts", type=nonnegative_int, default=10)
            command.add_argument("--seed", type=int, default=0)
    for name in ("sat-benchmark", "compare", "export"):
        command = sub.add_parser(name)
        command.add_argument("--sizes", type=sizes_arg, default=list(DEFAULT_SIZES))
        command.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
        command.add_argument("--repeats", type=positive_int, default=3)
        command.add_argument("--trials", type=positive_int, default=10)
        command.add_argument("--max-steps", type=nonnegative_int, default=1000)
        command.add_argument("--max-restarts", type=nonnegative_int, default=10)
        command.add_argument("--seed", type=int, default=0)
    return cli


def execute(args: argparse.Namespace) -> int:
    if args.command == "stats":
        model = NQueensCNF(args.n).build()
        print(f"N={args.n}; variables={model.variable_count}; clauses={model.clause_count}")
        print(f"Theoretical clauses={NQueensCNF.theoretical_clause_count(args.n)}")
    elif args.command == "sat":
        start = perf_counter()
        model = NQueensCNF(args.n).build()
        cnf_seconds = perf_counter() - start
        result = Glucose3Solver().solve(model)
        print(f"N={args.n}; status={'SAT' if result.satisfiable else 'UNSAT'}; valid={result.valid}")
        print(f"Variables={model.variable_count}; clauses={model.clause_count}")
        print(f"CNF={cnf_seconds:.6f}s; Glucose3={result.solver_seconds:.6f}s")
        if result.satisfiable:
            print(Board.render(args.n, result.queens))
    elif args.command in ("standard", "improved"):
        result = MinConflictsSolver(args.command).solve(
            args.n, max_steps=args.max_steps,
            max_restarts=args.max_restarts, seed=args.seed,
        )
        print(f"N={args.n}; success={result.success}; valid={Board.validate(args.n, result.queens) if result.success else False}")
        print(f"Steps={result.steps}; restarts={result.restarts}; final conflicts={result.conflicts}; cumulative conflicts={result.cumulative_conflicts}; time={result.runtime_seconds:.6f}s")
        if result.success:
            print(Board.render(args.n, result.queens))
    elif args.command in ("sat-benchmark", "compare", "export"):
        runner = BenchmarkRunner()
        sat = comparison = None
        if args.command in ("sat-benchmark", "export"):
            sat = runner.sat(args.sizes, args.repeats)
            for row in sat["summary"]:
                print(f"SAT N={row['n']}: {row['status']}, clauses={row['clauses']}, solver mean={row['solver_seconds']['mean']:.6f}s")
            print("Saved:", *runner.export(sat, args.out), sep="\n  ")
        if args.command in ("compare", "export"):
            comparison = runner.compare(args.sizes, args.trials, args.max_steps, args.max_restarts, args.seed)
            for row in comparison["summary"]:
                print(f"{row['variant']} N={row['n']}: success={row['success_rate']:.1%}, runtime mean={row['runtime_seconds']['mean']:.6f}s, steps mean={row['steps']['mean']:.1f}")
            print("Saved:", *runner.export(comparison, args.out), sep="\n  ")
        if sat and comparison:
            print("Charts:", *BenchmarkCharts.create(sat, comparison, args.out), sep="\n  ")
    else:
        raise ValueError("Unknown command")
    return 0


def interactive() -> int:
    menu = (
        "\n1. Glucose3 solve\n2. Standard Min-Conflicts\n3. Improved Min-Conflicts"
        "\n4. Glucose3 benchmark\n5. Compare Min-Conflicts\n6. CNF statistics"
        "\n7. Export results and charts\n0. Exit"
    )
    commands = {"1": "sat", "2": "standard", "3": "improved", "4": "sat-benchmark",
                "5": "compare", "6": "stats", "7": "export"}
    while True:
        print(menu)
        choice = input("Select: ").strip()
        if choice == "0":
            return 0
        if choice not in commands:
            print("Invalid option")
            continue
        command = commands[choice]
        try:
            if command in ("sat", "standard", "improved", "stats"):
                n = input("N (>=4): ").strip()
                argv = [command, n]
            else:
                values = input("Sizes (comma separated; Enter for defaults): ").strip()
                argv = [command] + (["--sizes", values] if values else [])
            execute(parser().parse_args(argv))
        except (ValueError, RuntimeError) as exc:
            print(f"Error: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    cli = parser()
    args = cli.parse_args(argv)
    if args.command is None:
        return interactive()
    try:
        return execute(args)
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
