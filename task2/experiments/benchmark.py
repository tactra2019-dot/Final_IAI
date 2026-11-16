"""Headless benchmark suite comparing the 4 adversarial search configurations."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from task2.agents.alphabeta_agent import AlphaBetaAgent
from task2.agents.base_agent import BaseAgent
from task2.agents.heuristic_ab_agent import HeuristicAlphaBetaAgent
from task2.agents.heuristic_mm_agent import HeuristicMinimaxAgent
from task2.agents.minimax_agent import MinimaxAgent
from task2.core.game_engine import GameEngine
from task2.experiments.maps import load_game_state, load_scenario_maps

ALGORITHM_CONFIGS: list[tuple[str, type[BaseAgent]]] = [
    ("Minimax", MinimaxAgent),
    ("Alpha-Beta", AlphaBetaAgent),
    ("Heuristic Minimax", HeuristicMinimaxAgent),
    ("Heuristic Alpha-Beta", HeuristicAlphaBetaAgent),
]

ALGO_COLORS: dict[str, str] = {
    "Minimax": "#E11D48",
    "Alpha-Beta": "#F59E0B",
    "Heuristic Minimax": "#2563EB",
    "Heuristic Alpha-Beta": "#10B981",
}

RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _play_match(
    scenario_name: str,
    algo_name: str,
    agent_cls: type[BaseAgent],
    depth: int,
    max_turns: int,
    opponent_depth: int = 2,
) -> dict[str, object]:
    """Run one headless match with P1=agent_cls(depth) vs P2=AlphaBetaAgent(opponent_depth)."""
    state = load_game_state(scenario_name, max_turns=max_turns)
    p1_agent = agent_cls(player_id=1, depth=depth)
    p2_agent = AlphaBetaAgent(player_id=2, depth=opponent_depth)

    while not state.is_terminal():
        active_agent = p1_agent if state.current_turn == 1 else p2_agent
        action = active_agent.get_action(state.clone())
        state = GameEngine.apply_action(state, action)

    winner_code = state.get_winner()
    if winner_code == 1:
        winner_label = "P1"
        win_flag = 1
    elif winner_code == 2:
        winner_label = "P2"
        win_flag = 0
    else:
        winner_label = "Draw"
        win_flag = 0

    moves = max(1, p1_agent.move_count)
    return {
        "Scenario": scenario_name,
        "Algorithm": algo_name,
        "Depth": depth,
        "Winner": winner_label,
        "Turns": state.turn_count,
        "Avg_Time_ms": round(float(p1_agent.avg_time_ms), 3),
        "Total_Nodes": int(p1_agent.total_nodes_explored),
        "Pruned_Branches": int(p1_agent.pruned_branches),
        "Nodes_Per_Move": round(p1_agent.total_nodes_explored / moves, 1),
        "Win_Flag": win_flag,
    }


def _configure_plot_style() -> None:
    """Apply clean matplotlib defaults for high-DPI paper-ready figures."""
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "#F8FAFC",
            "axes.edgecolor": "#CBD5E1",
            "axes.grid": True,
            "grid.color": "#E2E8F0",
            "grid.linestyle": "--",
            "grid.linewidth": 0.7,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.labelsize": 10,
        }
    )


def _annotate_bars(
    ax: plt.Axes,
    bars,
    labels: list[str],
    fontsize: float = 8.0,
    tilt_long: bool = False,
) -> None:
    """Attach centered value labels above Matplotlib bars."""
    for bar, text in zip(bars, labels):
        ax.annotate(
            text,
            xy=(bar.get_x() + bar.get_width() / 2.0, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=fontsize,
            rotation=25 if (tilt_long and len(text) > 5) else 0,
        )


def _plot_grouped_bars(
    ax: plt.Axes,
    df_sub: pd.DataFrame,
    scenarios: list[str],
    algos: list[str],
    value_col: str,
    ylabel: str,
    title: str,
    logy: bool = False,
    fmt: str = "{:.1f}",
) -> None:
    """Draw grouped scenario bars across algorithms with crisp numeric annotations."""
    x_positions = list(range(len(scenarios)))
    n_algos = len(algos)
    bar_width = 0.76 / max(1, n_algos)

    for idx, algo in enumerate(algos):
        offset = (idx - (n_algos - 1) / 2.0) * bar_width
        xs = [x + offset for x in x_positions]
        ys = []
        for scen in scenarios:
            match = df_sub[(df_sub["Scenario"] == scen) & (df_sub["Algorithm"] == algo)]
            ys.append(float(match[value_col].iloc[0]) if not match.empty else 0.0)

        bars = ax.bar(
            xs,
            ys,
            width=bar_width * 0.92,
            label=algo,
            color=ALGO_COLORS.get(algo, "#64748B"),
            edgecolor="#0F172A",
            linewidth=0.5,
            zorder=3,
        )
        valid_pairs = [(b, fmt.format(v)) for b, v in zip(bars, ys) if not (logy and v <= 0)]
        if valid_pairs:
            _annotate_bars(
                ax,
                [p[0] for p in valid_pairs],
                [p[1] for p in valid_pairs],
                fontsize=7.5,
                tilt_long=True,
            )

    if logy:
        ax.set_yscale("log")
    ax.set_xticks(x_positions)
    ax.set_xticklabels([s.replace(" - ", "\n") for s in scenarios])
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_axisbelow(True)


def _save_time_chart(df: pd.DataFrame, output_path: Path) -> None:
    """Generate time_comparison.png (Depth 3 all configs + Depth 3 vs 4 scaling)."""
    scenarios = list(df["Scenario"].drop_duplicates())
    d3 = df[df["Depth"] == 3]
    algos_d3 = [name for name, _ in ALGORITHM_CONFIGS]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.4))
    _plot_grouped_bars(
        ax1,
        d3,
        scenarios,
        algos_d3,
        value_col="Avg_Time_ms",
        ylabel="Avg Execution Time per Move (ms)",
        title="Execution Time at Depth = 3 (All 4 Configurations)",
        fmt="{:.2f}",
    )
    max_t = float(d3["Avg_Time_ms"].max()) if not d3.empty else 10.0
    ax1.set_ylim(0, max_t * 1.32)
    ax1.legend(frameon=True, fontsize=8.5, loc="upper left", ncol=2)

    scale_algos = ["Alpha-Beta", "Heuristic Alpha-Beta"]
    depths = sorted(df[df["Algorithm"].isin(scale_algos)]["Depth"].unique())
    x_pos = list(range(len(depths)))
    width = 0.34
    max_scale = 0.0
    for idx, algo in enumerate(scale_algos):
        offset = (idx - 0.5) * width
        means = [
            float(df[(df["Algorithm"] == algo) & (df["Depth"] == d)]["Avg_Time_ms"].mean())
            for d in depths
        ]
        max_scale = max(max_scale, max(means, default=0.0))
        bars = ax2.bar(
            [x + offset for x in x_pos],
            means,
            width=width * 0.9,
            label=algo,
            color=ALGO_COLORS[algo],
            edgecolor="#0F172A",
            linewidth=0.5,
            zorder=3,
        )
        _annotate_bars(ax2, bars, [f"{v:.2f} ms" for v in means], fontsize=8.5)
    ax2.set_ylim(0, max(1.0, max_scale * 1.25))
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels([f"Depth {d}" for d in depths])
    ax2.set_ylabel("Mean Time per Move Across Maps (ms)")
    ax2.set_title("Depth Scaling: Alpha-Beta vs Heuristic Alpha-Beta")
    ax2.legend(frameon=True, fontsize=8.5, loc="upper left")
    ax2.set_axisbelow(True)

    fig.suptitle("Tank Battle AI: Search Execution Time Comparison", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _save_nodes_chart(df: pd.DataFrame, output_path: Path) -> None:
    """Generate nodes_comparison.png (log-scale nodes/move + total vs pruned branches)."""
    scenarios = list(df["Scenario"].drop_duplicates())
    d3 = df[df["Depth"] == 3]
    algos_d3 = [name for name, _ in ALGORITHM_CONFIGS]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.4))
    _plot_grouped_bars(
        ax1,
        d3,
        scenarios,
        algos_d3,
        value_col="Nodes_Per_Move",
        ylabel="Nodes Explored per Move (log scale)",
        title="Search Space per Move at Depth = 3",
        logy=True,
        fmt="{:.0f}",
    )
    max_n = float(d3["Nodes_Per_Move"].max()) if not d3.empty else 300.0
    ax1.set_ylim(20, max_n * 2.8)
    ax1.legend(frameon=True, fontsize=8.5, loc="upper center", ncol=2)

    x_pos = list(range(len(algos_d3)))
    total_means = [float(d3[d3["Algorithm"] == a]["Total_Nodes"].mean()) for a in algos_d3]
    pruned_means = [float(d3[d3["Algorithm"] == a]["Pruned_Branches"].mean()) for a in algos_d3]
    width = 0.36

    b1 = ax2.bar(
        [x - width / 2 for x in x_pos],
        total_means,
        width=width,
        label="Mean Total Nodes Explored",
        color="#3B82F6",
        edgecolor="#0F172A",
        linewidth=0.5,
        zorder=3,
    )
    b2 = ax2.bar(
        [x + width / 2 for x in x_pos],
        pruned_means,
        width=width,
        label="Mean Pruned Branches",
        color="#10B981",
        edgecolor="#0F172A",
        linewidth=0.5,
        zorder=3,
    )
    _annotate_bars(
        ax2,
        list(b1) + list(b2),
        [f"{v:,.0f}" for v in total_means + pruned_means],
        fontsize=8.0,
    )
    max_tot = max(total_means + pruned_means, default=1000.0)
    ax2.set_ylim(0, max_tot * 1.22)
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels([a.replace(" ", "\n") for a in algos_d3])
    ax2.set_ylabel("Mean Count per Match")
    ax2.set_title("Explored Nodes vs Pruned Branches (Depth = 3)")
    ax2.legend(frameon=True, fontsize=8.5, loc="upper right")
    ax2.set_axisbelow(True)

    fig.suptitle("Tank Battle AI: Node Exploration & Pruning Efficiency", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _save_winrate_turns_chart(df: pd.DataFrame, output_path: Path) -> None:
    """Generate winrate_turns.png (Turns to finish & Win Rate across configurations)."""
    scenarios = list(df["Scenario"].drop_duplicates())
    d3 = df[df["Depth"] == 3]
    algos_d3 = [name for name, _ in ALGORITHM_CONFIGS]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 5.4))
    _plot_grouped_bars(
        ax1,
        d3,
        scenarios,
        algos_d3,
        value_col="Turns",
        ylabel="Total Match Turns",
        title="Match Length by Scenario (Depth = 3)",
        fmt="{:.0f}",
    )
    max_turns = float(d3["Turns"].max()) if not d3.empty else 80.0
    ax1.set_ylim(0, max_turns * 1.32)
    ax1.legend(frameon=True, fontsize=8.5, loc="upper center", ncol=2)

    labels: list[str] = []
    win_rates: list[float] = []
    colors: list[str] = []
    counts_text: list[str] = []

    for depth in sorted(df["Depth"].unique()):
        sub = df[df["Depth"] == depth]
        for algo, _ in ALGORITHM_CONFIGS:
            algo_rows = sub[sub["Algorithm"] == algo]
            if algo_rows.empty:
                continue
            wins = int(algo_rows["Win_Flag"].sum())
            total = len(algo_rows)
            wrapped_algo = algo.replace(" ", "\n")
            labels.append(f"{wrapped_algo}\n(d={depth})")
            win_rates.append(100.0 * wins / total)
            colors.append(ALGO_COLORS[algo])
            counts_text.append(f"{wins}/{total}")

    x_pos = list(range(len(labels)))
    bars = ax2.bar(
        x_pos,
        win_rates,
        width=0.56,
        color=colors,
        edgecolor="#0F172A",
        linewidth=0.6,
        zorder=3,
    )
    _annotate_bars(
        ax2,
        bars,
        [f"{rate:.0f}% ({c_txt})" for rate, c_txt in zip(win_rates, counts_text)],
        fontsize=8.5,
    )
    ax2.set_ylim(0, 118)
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(labels, fontsize=8)
    ax2.set_ylabel("P1 Win Rate (%)")
    ax2.set_title("P1 Win Rate vs Standardized Opponent (Alpha-Beta d=2)")
    ax2.set_axisbelow(True)

    fig.suptitle("Tank Battle AI: Match Duration & Tactical Win Rate", fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def run_benchmark(
    output_dir: Path | None = None,
    max_turns: int = 80,
) -> pd.DataFrame:
    """Execute the full headless benchmark, write CSV, and generate 3 PNG charts."""
    results_dir = output_dir if output_dir is not None else RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)

    scenarios = load_scenario_maps()
    rows: list[dict[str, object]] = []

    # Depth 3: Fair comparison across all 4 algorithm configurations
    for scenario_name in scenarios:
        for algo_name, agent_cls in ALGORITHM_CONFIGS:
            rows.append(
                _play_match(
                    scenario_name=scenario_name,
                    algo_name=algo_name,
                    agent_cls=agent_cls,
                    depth=3,
                    max_turns=max_turns,
                )
            )

    # Depth 4: Scaling comparison for Alpha-Beta vs Heuristic Alpha-Beta
    for scenario_name in scenarios:
        for algo_name, agent_cls in (
            ("Alpha-Beta", AlphaBetaAgent),
            ("Heuristic Alpha-Beta", HeuristicAlphaBetaAgent),
        ):
            rows.append(
                _play_match(
                    scenario_name=scenario_name,
                    algo_name=algo_name,
                    agent_cls=agent_cls,
                    depth=4,
                    max_turns=max_turns,
                )
            )

    df = pd.DataFrame(rows)
    csv_path = results_dir / "benchmark_results.csv"
    df.to_csv(csv_path, index=False)

    _configure_plot_style()
    _save_time_chart(df, results_dir / "time_comparison.png")
    _save_nodes_chart(df, results_dir / "nodes_comparison.png")
    _save_winrate_turns_chart(df, results_dir / "winrate_turns.png")

    return df


if __name__ == "__main__":
    summary_df = run_benchmark()
    print(summary_df.to_string(index=False))
