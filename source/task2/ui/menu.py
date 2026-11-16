"""Interactive PyGame setup menu for map, agent, plugin, and depth selection."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from source.task2.agents.agent_loader import AgentLoader
from source.task2.agents.base_agent import BaseAgent
from source.task2.core.constants import GRID_HEIGHT, GRID_WIDTH
from source.task2.experiments.maps import list_available_maps, load_game_state
from source.task2.ui import theme

AGENT_DESCRIPTIONS: dict[str, str] = {
    "MinimaxAgent": "Standard minimax search without alpha-beta pruning",
    "AlphaBetaAgent": "Minimax with alpha-beta pruning for faster exact search",
    "HeuristicMinimaxAgent": "Minimax using line-of-sight and base defense scoring",
    "HeuristicAlphaBetaAgent": "Alpha-beta search with move ordering and state caching",
    "GreedyShooterAgent": "External agent focused on lined-up shots and dodging",
    "Human (Keyboard)": "Manual play: Arrows or WASD move, F or Space fire, X stay",
}


@dataclass(frozen=True)
class AgentOption:
    """Selectable player controller entry (built-in AI, external plugin, or Human)."""

    label: str
    agent_cls: type[BaseAgent] | None
    source_tag: str
    description: str


@dataclass
class MatchConfig:
    """User-selected match parameters returned by SetupMenu."""

    map_name: str
    map_path: Path
    p1_label: str
    p1_cls: type[BaseAgent] | None
    p2_label: str
    p2_cls: type[BaseAgent] | None
    depth: int


def _describe_agent(label: str, cls: type[BaseAgent] | None) -> str:
    if label in AGENT_DESCRIPTIONS:
        return AGENT_DESCRIPTIONS[label]
    if cls is not None and cls.__doc__:
        first_line = cls.__doc__.strip().splitlines()[0].strip()
        if first_line:
            return first_line[:74]
    return "Custom agent loaded from agents/external/"


def collect_agent_options() -> tuple[list[AgentOption], int, int]:
    """Scan built-in and external agents via AgentLoader and append Human mode."""
    builtins = AgentLoader.get_builtin_agents()
    externals = AgentLoader.discover_external_agents()

    preferred_order = (
        "MinimaxAgent",
        "AlphaBetaAgent",
        "HeuristicMinimaxAgent",
        "HeuristicAlphaBetaAgent",
    )
    options: list[AgentOption] = []
    seen_classes: set[type[BaseAgent]] = set()

    for key in preferred_order:
        if key in builtins:
            cls = builtins[key]
            options.append(AgentOption(key, cls, "Built-in", _describe_agent(key, cls)))
            seen_classes.add(cls)

    for key, cls in builtins.items():
        if cls not in seen_classes:
            options.append(AgentOption(key, cls, "Built-in", _describe_agent(key, cls)))
            seen_classes.add(cls)

    ext_count = 0
    for key, cls in externals.items():
        if cls not in seen_classes:
            options.append(AgentOption(key, cls, "Plugin", _describe_agent(key, cls)))
            seen_classes.add(cls)
            ext_count += 1

    options.append(
        AgentOption(
            "Human (Keyboard)",
            None,
            "Human",
            _describe_agent("Human (Keyboard)", None),
        )
    )
    return options, len(builtins), ext_count


class SetupMenu:
    """Mouse + keyboard setup screen for configuring Tank Battle matches."""

    DEPTH_OPTIONS = (1, 2, 3, 4)

    def __init__(
        self,
        screen: pygame.Surface,
        fonts: theme.ThemeFonts,
        clock: pygame.time.Clock,
    ) -> None:
        self.screen = screen
        self.fonts = fonts
        self.clock = clock

        self.maps: list[tuple[str, Path]] = []
        self.agent_options: list[AgentOption] = []
        self.builtin_count = 0
        self.external_count = 0

        self.map_idx = 0
        self.p1_idx = 0
        self.p2_idx = 0
        self.depth_idx = 2  # default depth = 3
        self.focus_row = 0  # 0: Map, 1: P1, 2: P2, 3: Depth, 4: Buttons
        self.focused_btn = 0  # 0: Start, 1: Reload, 2: Benchmark
        self.status_msg = "Choose a map, agents, and search depth to play."
        self.status_color = theme.TEXT_MUTED
        self.preview_state = None

        self._rects: dict[str, pygame.Rect] = {}
        self._refresh_catalog(preserve_names=False)

    def _refresh_catalog(self, preserve_names: bool = True) -> None:
        prev_map = self.maps[self.map_idx][0] if preserve_names and self.maps else None
        prev_p1 = (
            self.agent_options[self.p1_idx].label
            if preserve_names and self.agent_options
            else "HeuristicAlphaBetaAgent"
        )
        prev_p2 = (
            self.agent_options[self.p2_idx].label
            if preserve_names and self.agent_options
            else "HeuristicMinimaxAgent"
        )

        self.maps = list(list_available_maps().items())
        self.agent_options, self.builtin_count, self.external_count = collect_agent_options()

        self.map_idx = self._find_map_index(prev_map)
        self.p1_idx = self._find_agent_index(prev_p1, fallback=0)
        self.p2_idx = self._find_agent_index(prev_p2, fallback=0)
        self._load_preview()

    def _find_map_index(self, name: str | None) -> int:
        if name:
            for idx, (m_name, _) in enumerate(self.maps):
                if m_name == name:
                    return idx
        return 0

    def _find_agent_index(self, label: str | None, fallback: int = 0) -> int:
        if label:
            for idx, opt in enumerate(self.agent_options):
                if opt.label == label:
                    return idx
        return min(fallback, max(0, len(self.agent_options) - 1))

    def _load_preview(self) -> None:
        if not self.maps:
            self.preview_state = None
            return
        try:
            self.preview_state = load_game_state(self.maps[self.map_idx][1])
        except Exception as exc:
            self.preview_state = None
            self.status_msg = f"Map preview error: {exc}"
            self.status_color = theme.STATUS_DANGER

    def swap_players(self) -> None:
        """Swap Player 1 and Player 2 agent selections."""
        self.p1_idx, self.p2_idx = self.p2_idx, self.p1_idx
        p1_name = self.agent_options[self.p1_idx].label
        p2_name = self.agent_options[self.p2_idx].label
        self.status_msg = f"Swapped: P1 {p1_name}, P2 {p2_name}"
        self.status_color = theme.P1_PRIMARY

    def _cycle_row(self, row: int, delta: int) -> None:
        if row == 0 and self.maps:
            self.map_idx = (self.map_idx + delta) % len(self.maps)
            self._load_preview()
        elif row == 1 and self.agent_options:
            self.p1_idx = (self.p1_idx + delta) % len(self.agent_options)
        elif row == 2 and self.agent_options:
            self.p2_idx = (self.p2_idx + delta) % len(self.agent_options)
        elif row == 3:
            self.depth_idx = (self.depth_idx + delta) % len(self.DEPTH_OPTIONS)
        elif row == 4:
            self.focused_btn = (self.focused_btn + delta) % 3

    def _reload_plugins(self) -> None:
        self._refresh_catalog(preserve_names=True)
        self.status_msg = (
            f"Reloaded: {self.builtin_count} built-in, {self.external_count} custom."
        )
        self.status_color = theme.STATUS_GOOD

    def _run_benchmark_from_menu(self) -> None:
        self._draw(overlay_text="Running benchmark across 3 maps... Please wait.")
        pygame.display.flip()
        pygame.event.pump()
        try:
            from source.task2.experiments.benchmark import run_benchmark

            df = run_benchmark()
            self.status_msg = (
                f"Saved {len(df)} benchmark runs to source/task2/experiments/results/"
            )
            self.status_color = theme.STATUS_GOOD
        except Exception as exc:
            self.status_msg = f"Benchmark failed: {exc}"
            self.status_color = theme.STATUS_DANGER

    def _build_config(self) -> MatchConfig | None:
        if not self.maps or not self.agent_options:
            self.status_msg = "No valid maps or agents available."
            self.status_color = theme.STATUS_DANGER
            return None
        map_name, map_path = self.maps[self.map_idx]
        p1 = self.agent_options[self.p1_idx]
        p2 = self.agent_options[self.p2_idx]
        return MatchConfig(
            map_name=map_name,
            map_path=map_path,
            p1_label=p1.label,
            p1_cls=p1.agent_cls,
            p2_label=p2.label,
            p2_cls=p2.agent_cls,
            depth=self.DEPTH_OPTIONS[self.depth_idx],
        )

    def _draw_selector_card(
        self,
        rect: pygame.Rect,
        title: str,
        value_text: str,
        badge_text: str,
        accent: tuple[int, int, int],
        row_id: int,
        subtitle: str = "",
        title_color: tuple[int, int, int] | None = None,
    ) -> None:
        is_focused = self.focus_row == row_id
        border = accent if is_focused else theme.BORDER_SUBTLE
        pygame.draw.rect(self.screen, theme.SURFACE_CARD, rect, border_radius=4)
        pygame.draw.rect(self.screen, border, rect, width=2 if is_focused else 1, border_radius=4)

        title_surf = self.fonts.small.render(title, True, title_color or theme.TEXT_MUTED)
        self.screen.blit(title_surf, (rect.x + 14, rect.y + 8))

        btn_y = rect.y + 28
        prev_rect = pygame.Rect(rect.x + 14, btn_y, 34, 32)
        next_rect = pygame.Rect(rect.right - 48, btn_y, 34, 32)
        self._rects[f"row_{row_id}_prev"] = prev_rect
        self._rects[f"row_{row_id}_next"] = next_rect

        mouse_pos = pygame.mouse.get_pos()
        for btn_rect, arrow in ((prev_rect, "<"), (next_rect, ">")):
            bg = theme.BTN_HOVER if btn_rect.collidepoint(mouse_pos) else theme.BTN_BG
            pygame.draw.rect(self.screen, bg, btn_rect, border_radius=4)
            pygame.draw.rect(self.screen, theme.BORDER_LIGHT, btn_rect, width=1, border_radius=4)
            arr_surf = self.fonts.body_bold.render(arrow, True, theme.TEXT_PRIMARY)
            self.screen.blit(arr_surf, arr_surf.get_rect(center=btn_rect.center))

        val_surf = self.fonts.heading.render(value_text, True, theme.TEXT_PRIMARY)
        self.screen.blit(val_surf, (prev_rect.right + 12, btn_y + 6))

        if badge_text:
            badge_surf = self.fonts.small.render(badge_text, True, theme.TEXT_SECONDARY)
            pill = pygame.Rect(
                next_rect.x - badge_surf.get_width() - 22,
                btn_y + 5,
                badge_surf.get_width() + 12,
                22,
            )
            pygame.draw.rect(self.screen, theme.SURFACE_INSET, pill, border_radius=3)
            self.screen.blit(badge_surf, badge_surf.get_rect(center=pill.center))

        if subtitle:
            sub_surf = self.fonts.small.render(subtitle[:78], True, theme.TEXT_SECONDARY)
            self.screen.blit(sub_surf, (rect.x + 14, rect.bottom - 22))

    def _draw_swap_button(self, rect: pygame.Rect) -> None:
        self._rects["btn_swap"] = rect
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        bg = theme.BTN_HOVER if hovered else theme.SURFACE_CARD
        pygame.draw.rect(self.screen, bg, rect, border_radius=4)
        pygame.draw.rect(
            self.screen,
            theme.P1_PRIMARY if hovered else theme.BORDER_LIGHT,
            rect,
            width=1,
            border_radius=4,
        )
        lbl = self.fonts.small.render("Swap P1 / P2  (S)", True, theme.TEXT_PRIMARY)
        self.screen.blit(lbl, lbl.get_rect(center=rect.center))

    def _draw_depth_card(self, rect: pygame.Rect) -> None:
        is_focused = self.focus_row == 3
        border = theme.P1_PRIMARY if is_focused else theme.BORDER_SUBTLE
        pygame.draw.rect(self.screen, theme.SURFACE_CARD, rect, border_radius=4)
        pygame.draw.rect(self.screen, border, rect, width=2 if is_focused else 1, border_radius=4)

        title_surf = self.fonts.small.render("Search Depth", True, theme.TEXT_MUTED)
        self.screen.blit(title_surf, (rect.x + 14, rect.y + 8))

        pill_w = 78
        gap = 10
        start_x = rect.x + 14
        for idx, depth_val in enumerate(self.DEPTH_OPTIONS):
            pill = pygame.Rect(start_x + idx * (pill_w + gap), rect.y + 30, pill_w, 34)
            self._rects[f"depth_{idx}"] = pill
            selected = idx == self.depth_idx
            bg = theme.BTN_ACTIVE if selected else theme.BTN_BG
            fg = theme.TEXT_ON_ACCENT if selected else theme.TEXT_PRIMARY
            pygame.draw.rect(self.screen, bg, pill, border_radius=4)
            if not selected:
                pygame.draw.rect(self.screen, theme.BORDER_LIGHT, pill, width=1, border_radius=4)
            lbl = self.fonts.body_bold.render(f"Depth {depth_val}", True, fg)
            self.screen.blit(lbl, lbl.get_rect(center=pill.center))

        hint = (
            "Slower for plain Minimax"
            if self.DEPTH_OPTIONS[self.depth_idx] == 4
            else "Balanced speed on CPU"
        )
        hint_surf = self.fonts.small.render(hint, True, theme.TEXT_MUTED)
        self.screen.blit(hint_surf, (start_x + 4 * (pill_w + gap) + 10, rect.y + 40))

    def _draw_preview_panel(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, theme.SURFACE_CARD, rect, border_radius=4)
        pygame.draw.rect(self.screen, theme.BORDER_SUBTLE, rect, width=1, border_radius=4)

        hdr = self.fonts.heading.render("Map Preview (13x13)", True, theme.TEXT_PRIMARY)
        self.screen.blit(hdr, (rect.x + 16, rect.y + 12))
        pygame.draw.line(
            self.screen,
            theme.BORDER_SUBTLE,
            (rect.x + 14, rect.y + 38),
            (rect.right - 14, rect.y + 38),
            1,
        )

        cell = 24
        grid_px = GRID_WIDTH * cell  # 312
        gx = rect.x + (rect.width - grid_px) // 2
        gy = rect.y + 46

        pygame.draw.rect(
            self.screen,
            theme.BORDER_LIGHT,
            pygame.Rect(gx - 2, gy - 2, grid_px + 4, grid_px + 4),
            width=1,
        )

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                tile = pygame.Rect(gx + x * cell, gy + y * cell, cell, cell)
                bg = theme.GRID_EVEN if (x + y) % 2 == 0 else theme.GRID_ODD
                pygame.draw.rect(self.screen, bg, tile)

        if self.preview_state is not None:
            for (wx, wy), hp in self.preview_state.walls.items():
                w_color = (
                    theme.WALL_HP3
                    if hp >= 3
                    else (theme.WALL_HP2 if hp == 2 else theme.WALL_HP1)
                )
                w_rect = pygame.Rect(gx + wx * cell + 2, gy + wy * cell + 2, cell - 4, cell - 4)
                pygame.draw.rect(self.screen, w_color, w_rect, border_radius=2)

            for pid, base in self.preview_state.bases.items():
                bcx = gx + base.x * cell + cell // 2
                bcy = gy + base.y * cell + cell // 2
                theme.draw_base_shield(pygame, self.screen, bcx, bcy, pid, radius=9)

            for pid, tank in self.preview_state.tanks.items():
                tcx = gx + tank.x * cell + cell // 2
                tcy = gy + tank.y * cell + cell // 2
                theme.draw_tank_body(
                    pygame, self.screen, tcx, tcy, pid, tank.direction, cell_size=cell
                )

        legend_y = gy + grid_px + 12
        legend = "Blue: P1   Red: P2   Shields: Bases   Amber: Walls"
        leg_surf = self.fonts.small.render(legend, True, theme.TEXT_MUTED)
        self.screen.blit(leg_surf, (rect.x + 16, legend_y))

    def _draw_action_buttons(self) -> None:
        mouse_pos = pygame.mouse.get_pos()
        buttons = (
            ("start", "Start Match", theme.BTN_ACTIVE, theme.TEXT_ON_ACCENT, 224),
            ("reload", "Reload Plugins", theme.SURFACE_CARD, theme.TEXT_PRIMARY, 204),
            ("bench", "Run Benchmark", theme.SURFACE_CARD, theme.BASE_P1, 204),
        )
        x = 28
        y = 602
        h = 52
        for idx, (key, label, bg, fg, w) in enumerate(buttons):
            rect = pygame.Rect(x, y, w, h)
            self._rects[f"btn_{key}"] = rect
            hovered = rect.collidepoint(mouse_pos)
            focused = self.focus_row == 4 and self.focused_btn == idx
            fill = bg
            if hovered:
                fill = theme.P1_GLOW if key == "start" else theme.BTN_HOVER
            pygame.draw.rect(self.screen, fill, rect, border_radius=4)
            border_col = theme.TEXT_PRIMARY if focused else theme.BORDER_LIGHT
            if key != "start" or focused:
                pygame.draw.rect(
                    self.screen, border_col, rect, width=2 if focused else 1, border_radius=4
                )
            txt = self.fonts.heading.render(label, True, fg)
            self.screen.blit(txt, txt.get_rect(center=rect.center))
            x += w + 14

    def _draw(self, overlay_text: str | None = None) -> None:
        self._rects.clear()
        self.screen.fill(theme.BG_DARK)

        # Header
        title = self.fonts.title.render("Tank Battle", True, theme.TEXT_PRIMARY)
        sub = self.fonts.body.render(
            "13x13 turn-based board with built-in and custom agents",
            True,
            theme.TEXT_MUTED,
        )
        self.screen.blit(title, (28, 18))
        self.screen.blit(sub, (28, 48))
        pygame.draw.line(
            self.screen, theme.BORDER_SUBTLE, (28, 78), (theme.WINDOW_WIDTH - 28, 78), 1
        )

        # Left column selector cards
        map_label = self.maps[self.map_idx][0] if self.maps else "No maps found"
        map_file = self.maps[self.map_idx][1].name if self.maps else ""
        self._draw_selector_card(
            pygame.Rect(28, 92, 660, 76),
            "Map",
            map_label,
            map_file,
            theme.BASE_P1,
            row_id=0,
        )

        p1 = self.agent_options[self.p1_idx]
        self._draw_selector_card(
            pygame.Rect(28, 178, 660, 92),
            "Player 1  (Blue)",
            p1.label,
            p1.source_tag,
            theme.P1_PRIMARY,
            row_id=1,
            subtitle=p1.description,
            title_color=theme.P1_PRIMARY,
        )

        self._draw_swap_button(pygame.Rect(228, 276, 260, 28))

        p2 = self.agent_options[self.p2_idx]
        self._draw_selector_card(
            pygame.Rect(28, 310, 660, 92),
            "Player 2  (Red)",
            p2.label,
            p2.source_tag,
            theme.P2_PRIMARY,
            row_id=2,
            subtitle=p2.description,
            title_color=theme.P2_PRIMARY,
        )

        self._draw_depth_card(pygame.Rect(28, 412, 660, 76))

        # Status / Plugin Info Banner
        status_rect = pygame.Rect(28, 498, 660, 82)
        pygame.draw.rect(self.screen, theme.SURFACE_CARD, status_rect, border_radius=4)
        pygame.draw.rect(self.screen, theme.BORDER_SUBTLE, status_rect, width=1, border_radius=4)
        plug_info = self.fonts.small.render(
            f"Agents loaded: {self.builtin_count} built-in, {self.external_count} custom "
            "(source/task2/agents/external/)",
            True,
            theme.TEXT_SECONDARY,
        )
        self.screen.blit(plug_info, (status_rect.x + 14, status_rect.y + 14))
        st_surf = self.fonts.body.render(self.status_msg[:82], True, self.status_color)
        self.screen.blit(st_surf, (status_rect.x + 14, status_rect.y + 44))

        # Right preview column
        self._draw_preview_panel(pygame.Rect(710, 92, 382, 396))

        hint_rect = pygame.Rect(710, 498, 382, 82)
        pygame.draw.rect(self.screen, theme.SURFACE_CARD, hint_rect, border_radius=4)
        pygame.draw.rect(self.screen, theme.BORDER_SUBTLE, hint_rect, width=1, border_radius=4)
        h1 = self.fonts.small.render("Shortcuts", True, theme.TEXT_PRIMARY)
        h2 = self.fonts.small.render("Up / Down: choose row    Left / Right: cycle option", True, theme.TEXT_SECONDARY)
        h3 = self.fonts.small.render("S / Tab: swap    R: reload    Enter: start", True, theme.TEXT_SECONDARY)
        self.screen.blit(h1, (hint_rect.x + 14, hint_rect.y + 10))
        self.screen.blit(h2, (hint_rect.x + 14, hint_rect.y + 32))
        self.screen.blit(h3, (hint_rect.x + 14, hint_rect.y + 54))

        self._draw_action_buttons()

        if overlay_text:
            shade = pygame.Surface((theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT), pygame.SRCALPHA)
            shade.fill((246, 243, 236, 215))
            self.screen.blit(shade, (0, 0))
            box = pygame.Rect(260, 295, 600, 100)
            pygame.draw.rect(self.screen, theme.SURFACE_CARD, box, border_radius=4)
            pygame.draw.rect(self.screen, theme.P1_PRIMARY, box, width=2, border_radius=4)
            msg = self.fonts.heading.render(overlay_text, True, theme.TEXT_PRIMARY)
            self.screen.blit(msg, msg.get_rect(center=box.center))

    def _handle_click(self, pos: tuple[int, int]) -> tuple[bool, MatchConfig | None]:
        for row_id in (0, 1, 2):
            if self._rects.get(f"row_{row_id}_prev", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                self.focus_row = row_id
                self._cycle_row(row_id, -1)
                return False, None
            if self._rects.get(f"row_{row_id}_next", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                self.focus_row = row_id
                self._cycle_row(row_id, 1)
                return False, None

        for idx in range(len(self.DEPTH_OPTIONS)):
            if self._rects.get(f"depth_{idx}", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
                self.focus_row = 3
                self.depth_idx = idx
                return False, None

        if self._rects.get("btn_swap", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            self.swap_players()
            return False, None
        if self._rects.get("btn_start", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            cfg = self._build_config()
            return (cfg is not None), cfg
        if self._rects.get("btn_reload", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            self._reload_plugins()
            return False, None
        if self._rects.get("btn_bench", pygame.Rect(0, 0, 0, 0)).collidepoint(pos):
            self._run_benchmark_from_menu()
            return False, None

        return False, None

    def run(self) -> MatchConfig | None:
        """Run the setup menu event loop until Start Match or Quit."""
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    done, cfg = self._handle_click(event.pos)
                    if done:
                        return cfg
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key == pygame.K_UP:
                        self.focus_row = (self.focus_row - 1) % 5
                    elif event.key == pygame.K_DOWN:
                        self.focus_row = (self.focus_row + 1) % 5
                    elif event.key == pygame.K_LEFT:
                        self._cycle_row(self.focus_row, -1)
                    elif event.key == pygame.K_RIGHT:
                        self._cycle_row(self.focus_row, 1)
                    elif event.key in (pygame.K_s, pygame.K_TAB):
                        self.swap_players()
                    elif event.key == pygame.K_r:
                        self._reload_plugins()
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if self.focus_row == 4 and self.focused_btn == 1:
                            self._reload_plugins()
                        elif self.focus_row == 4 and self.focused_btn == 2:
                            self._run_benchmark_from_menu()
                        else:
                            cfg = self._build_config()
                            if cfg is not None:
                                return cfg

            self._draw()
            pygame.display.flip()
            self.clock.tick(theme.FPS)
