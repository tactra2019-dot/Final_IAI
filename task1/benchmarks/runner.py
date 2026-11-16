"""Real measurements, per-trial records, and aggregate statistics."""

import csv
import json
import platform
import statistics
import sys
from pathlib import Path
from time import perf_counter
from typing import Any

from task1.models.cnf import NQueensCNF
from task1.solvers.min_conflicts import MinConflictsSolver
from task1.solvers.sat import Glucose3Solver

DEFAULT_SIZES = (4, 5, 6, 8, 10, 12, 16, 20, 30, 50)


def _stats(values: list[float]) -> dict[str, float]:
    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def _check_sizes(sizes: list[int] | tuple[int, ...]) -> None:
    if not sizes or any(isinstance(n, bool) or not isinstance(n, int) or n < 4 for n in sizes):
        raise ValueError("sizes must contain integers >= 4")
    if len(set(sizes)) != len(sizes):
        raise ValueError("sizes must not contain duplicates")


class BenchmarkRunner:
    def sat(self, sizes: list[int] | tuple[int, ...], repeats: int = 3) -> dict[str, Any]:
        _check_sizes(sizes)
        if isinstance(repeats, bool) or not isinstance(repeats, int) or repeats < 1:
            raise ValueError("repeats must be a positive integer")
        trials: list[dict[str, Any]] = []
        summary: list[dict[str, Any]] = []
        for n in sizes:
            rows: list[dict[str, Any]] = []
            for repeat in range(repeats):
                start = perf_counter()
                model = NQueensCNF(n).build()
                cnf_seconds = perf_counter() - start
                result = Glucose3Solver().solve(model)
                row = {
                    "n": n, "repeat": repeat, "variables": model.variable_count,
                    "clauses": model.clause_count, "cnf_seconds": cnf_seconds,
                    "solver_seconds": result.solver_seconds,
                    "total_seconds": cnf_seconds + result.solver_seconds,
                    "status": "SAT" if result.satisfiable else "UNSAT",
                    "valid": result.valid,
                }
                if result.satisfiable and not result.valid:
                    raise RuntimeError("Invalid SAT benchmark solution")
                rows.append(row)
                trials.append(row)
            summary.append({
                "n": n, "variables": rows[0]["variables"], "clauses": rows[0]["clauses"],
                "status": rows[0]["status"], "all_valid": all(row["valid"] for row in rows),
                "cnf_seconds": _stats([row["cnf_seconds"] for row in rows]),
                "solver_seconds": _stats([row["solver_seconds"] for row in rows]),
                "total_seconds": _stats([row["total_seconds"] for row in rows]),
            })
        return {"kind": "sat", "config": {"sizes": list(sizes), "repeats": repeats},
                "environment": self._environment(), "trials": trials, "summary": summary}

    def compare(
        self, sizes: list[int] | tuple[int, ...], trials_per_size: int = 10,
        max_steps: int = 1000, max_restarts: int = 10, seed: int = 0,
    ) -> dict[str, Any]:
        _check_sizes(sizes)
        if isinstance(trials_per_size, bool) or not isinstance(trials_per_size, int) or trials_per_size < 1:
            raise ValueError("trials_per_size must be a positive integer")
        records: list[dict[str, Any]] = []
        summary: list[dict[str, Any]] = []
        for n in sizes:
            for trial in range(trials_per_size):
                trial_seed = seed + trial
                for variant in ("standard", "improved"):
                    result = MinConflictsSolver(variant).solve(
                        n, max_steps=max_steps, max_restarts=max_restarts, seed=trial_seed
                    )
                    records.append({
                        "n": n, "trial": trial, "seed": trial_seed, "variant": variant,
                        "success": result.success, "runtime_seconds": result.runtime_seconds,
                        "steps": result.steps, "total_conflicts": result.cumulative_conflicts,
                        "final_conflicts": result.conflicts,
                        "restarts": result.restarts,
                    })
            for variant in ("standard", "improved"):
                rows = [row for row in records if row["n"] == n and row["variant"] == variant]
                summary.append({
                    "n": n, "variant": variant,
                    "success_rate": sum(row["success"] for row in rows) / len(rows),
                    "runtime_seconds": _stats([row["runtime_seconds"] for row in rows]),
                    "steps": _stats([row["steps"] for row in rows]),
                    "total_conflicts": _stats([row["total_conflicts"] for row in rows]),
                    "restarts": _stats([row["restarts"] for row in rows]),
                })
        return {
            "kind": "min_conflicts",
            "config": {"sizes": list(sizes), "trials_per_size": trials_per_size,
                       "max_steps": max_steps, "max_restarts": max_restarts, "seed": seed},
            "environment": self._environment(), "trials": records, "summary": summary,
        }

    @staticmethod
    def _environment() -> dict[str, str]:
        return {"python": sys.version.split()[0], "platform": platform.platform(),
                "processor": platform.processor()}

    @staticmethod
    def export(data: dict[str, Any], directory: Path) -> list[Path]:
        directory.mkdir(parents=True, exist_ok=True)
        kind = data["kind"]
        json_path = directory / f"{kind}.json"
        json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        paths = [json_path]
        for section in ("trials", "summary"):
            csv_path = directory / f"{kind}_{section}.csv"
            rows = data[section]
            flattened = [BenchmarkRunner._flatten(row) for row in rows]
            with csv_path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(flattened[0]))
                writer.writeheader()
                writer.writerows(flattened)
            paths.append(csv_path)
        return paths

    @staticmethod
    def _flatten(row: dict[str, Any]) -> dict[str, Any]:
        flat: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, dict):
                flat.update({f"{key}_{metric}": number for metric, number in value.items()})
            else:
                flat[key] = value
        return flat
