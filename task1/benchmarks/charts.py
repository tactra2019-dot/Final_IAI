"""Six PNG figures made only from measured benchmark data."""

from pathlib import Path
from typing import Any


class BenchmarkCharts:
    @staticmethod
    def create(sat: dict[str, Any], comparison: dict[str, Any], directory: Path) -> list[Path]:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        directory.mkdir(parents=True, exist_ok=True)
        sat_rows = sorted(sat["summary"], key=lambda row: row["n"])
        mc_rows = comparison["summary"]
        paths: list[Path] = []

        def draw(name: str, title: str, ylabel: str, series: list[tuple[str, list[int], list[float]]]) -> None:
            fig, ax = plt.subplots(figsize=(8, 5))
            for label, x, y in series:
                ax.plot(x, y, marker="x" if label == "Improved" else "o",
                        linestyle="--" if label == "Improved" else "-", label=label)
            ax.set(title=title, xlabel="Board size N", ylabel=ylabel)
            if name == "success_rate":
                ax.set_ylim(0, 105)
            ax.grid(True, alpha=0.3)
            ax.legend()
            fig.tight_layout()
            path = directory / f"{name}.png"
            fig.savefig(path, dpi=150)
            plt.close(fig)
            paths.append(path)

        def mc_series(metric: str, statistic: str = "mean") -> list[tuple[str, list[int], list[float]]]:
            series = []
            for variant in ("standard", "improved"):
                rows = sorted((row for row in mc_rows if row["variant"] == variant), key=lambda row: row["n"])
                series.append((variant.title(), [row["n"] for row in rows],
                               [row[metric][statistic] if statistic else row[metric] for row in rows]))
            return series

        draw("clauses", "CNF clause count", "Clauses (count)",
             [("Pairwise CNF", [r["n"] for r in sat_rows], [r["clauses"] for r in sat_rows])])
        draw("glucose3_time", "Glucose3 runtime", "Mean solver time (seconds)",
             [("Glucose3", [r["n"] for r in sat_rows], [r["solver_seconds"]["mean"] for r in sat_rows])])
        for variant in ("standard", "improved"):
            draw(f"{variant}_time", f"{variant.title()} Min-Conflicts runtime",
                 "Mean runtime (seconds)", [series for series in mc_series("runtime_seconds") if series[0].lower() == variant])
        draw("success_rate", "Min-Conflicts success rate", "Success rate (%)",
             [(label, x, [100 * value for value in y]) for label, x, y in mc_series("success_rate", "")])
        draw("steps", "Min-Conflicts search steps", "Mean steps (count)", mc_series("steps"))
        return paths
