# Tank Battle AI — Adversarial Search (Task 2)

Turn-based **13×13 Tank Battle** AI environment built for **Introduction to Artificial Intelligence (503043)** at Ton Duc Thang University. The project separates headless game simulation, adversarial search agents, and PyGame visualization so search algorithms run cleanly on CPU and support dynamic external student plugins.

## Project Structure

```text
source/
└── task2/
    ├── core/               # Headless 13x13 simulation engine, entities, actions, rules
    ├── agents/             # BaseAgent, 4 search configs, heuristics, AgentLoader
    │   └── external/       # Drop-in directory for external student agent plugins (.py)
    ├── maps/               # 13x13 ASCII scenario maps (open, tactical, endgame)
    ├── ui/                 # PyGame dark tactical menu, renderer, theme
    ├── experiments/        # Headless benchmark runner, CSV metrics, 300-DPI PNG charts
    ├── tests/              # Pytest suite (normal, boundary, edge, invalid, performance)
    └── main.py             # Unified CLI & PyGame entrypoint
```

## Setup & Installation

Python **3.10+** is required.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## How to Run

### 1. Interactive PyGame GUI

Launch the tactical setup menu and battlefield viewer:

```bash
python -m source.task2.main
```

*(You can also run `python source/task2/main.py` directly from the repository root.)*

**Menu Controls:**
- Select **Map Scenario**, **Player 1 Agent**, **Player 2 Agent** (AI, external plugins, or `Human (Keyboard)`), and **Search Depth (`1–4`)** — with a live 1-line strategy description per agent and 13×13 map preview showing tank barrels & base shields.
- Click **SWAP P1 <-> P2** (or press `S` / `Tab`) to quickly swap the P1 and P2 agents.
- Click **RELOAD PLUGINS** (or press `R`) to re-scan `source/task2/agents/external/` at runtime.
- Click **RUN BENCHMARK** to execute the full benchmark suite directly from the menu.
- Click **START MATCH** (or press `Enter`) to begin.

**In-Match Controls & HUD:**
- Battlefield HUD includes `0–12` coordinate headers, pulsing active-turn tank halo, 3-cell aiming laser & target crosshair, floating `-1 HP` damage popups, live **Tactical Eval Gauge** (`P1` vs `P2`), and color-coded combat log.
- Click the bottom toolbar buttons or use keyboard shortcuts:
  - `SPACE` / `P`: Pause or resume AI playback
  - `N`: Step 1 turn (pauses and advances 1 turn)
  - `[` / `]`: Slow down / speed up AI playback
  - `R`: Restart current match
  - `M` / `ESC`: Return to setup menu
- **Human Mode:** `Arrow Keys` or `WASD` to move/rotate, `F` / `SPACE` / `Enter` to fire, `X` to stay

### 2. Headless Match (CLI)

Run an AI-vs-AI match in the terminal with default settings (`HeuristicAlphaBetaAgent` vs `MinimaxAgent` on `map1_open.txt` at `depth=3`):

```bash
python -m source.task2.main --headless
```

Customize players, map, or depth:

```bash
python -m source.task2.main --headless --p1 HeuristicAlphaBetaAgent --p2 AlphaBetaAgent --map map2_tactical.txt --depth 3
```

### 3. Headless Benchmark & Charts

Compare all 4 algorithm configurations (**Minimax**, **Alpha-Beta**, **Heuristic Minimax**, **Heuristic Alpha-Beta**) across all 3 scenarios (`map1_open.txt`, `map2_tactical.txt`, `map3_endgame.txt`):

```bash
python -m source.task2.main --benchmark
```

Or run the experiment module directly:

```bash
python -m source.task2.experiments.benchmark
```

Generated artifacts are saved to `source/task2/experiments/results/`:
- `benchmark_results.csv`
- `time_comparison.png`
- `nodes_comparison.png`
- `winrate_turns.png`

### 4. Unit Tests (Pytest)

```bash
pytest source/task2/tests/test_engine.py -v
```

## Integrating External Student Agents (Plugin Guide)

Other student groups can compete against built-in agents without modifying core code:

1. Create a `.py` file inside `source/task2/agents/external/` (for example, `my_group_agent.py`).
2. Define a class inheriting `BaseAgent` and implement `get_action(self, state: GameState) -> Action`.
3. Keep the constructor compatible with `(self, player_id: int, depth: int = 3, name: str = "...")`.

### Minimal Example (`source/task2/agents/external/my_group_agent.py`)

```python
from source.task2.agents.base_agent import BaseAgent
from source.task2.core.actions import Action
from source.task2.core.game_engine import GameEngine
from source.task2.core.game_state import GameState


class MyGroupAgent(BaseAgent):
    """Custom adversarial search agent plugin."""

    def __init__(
        self,
        player_id: int,
        depth: int = 3,
        name: str = "MyGroupAgent",
    ) -> None:
        super().__init__(player_id=player_id, depth=depth, name=name)

    def get_action(self, state: GameState) -> Action:
        # Each player gets a cloned GameState; simulate transitions via GameEngine.
        legal_actions = state.get_legal_actions(self.player_id)
        if not legal_actions:
            return Action.STAY
        # Replace with your search/evaluation logic:
        for action in legal_actions:
            next_state = GameEngine.apply_action(state, action)
            if next_state.get_winner() == self.player_id:
                return action
        return Action.FIRE
```

### Plugin Safety Rules
- `AgentLoader.safe_get_action(agent, state)` passes a cloned `GameState` to `get_action`, preventing accidental state corruption.
- Exceptions or responses exceeding `EXTERNAL_AGENT_TIMEOUT_SEC` (2.0s) automatically fall back to `Action.STAY` so matches continue safely.
- Click **RELOAD PLUGINS** in the PyGame menu (or pass `--p1 MyGroupAgent` in `--headless` mode) to load your agent immediately.
