"""PyGame tactical arena renderer and interactive TankBattleApp controller."""

from __future__ import annotations

import math
import os
import time
from collections import deque
from dataclasses import dataclass

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from source.task2.agents.agent_loader import AgentLoader
from source.task2.agents.base_agent import BaseAgent
from source.task2.agents.heuristics import tactical_evaluate
from source.task2.core.actions import Action
from source.task2.core.constants import (
    BASE_INITIAL_HP,
    GRID_HEIGHT,
    GRID_WIDTH,
    TANK_INITIAL_HP,
)
from source.task2.core.game_engine import GameEngine
from source.task2.core.game_state import GameState
from source.task2.ui import theme
from source.task2.ui.menu import MatchConfig, SetupMenu

POPUP_DURATION_MS = 650


@dataclass
class PlayerTelemetry:
    """Live per-player telemetry rendered in the sidebar cards."""

    name: str
    is_human: bool
    depth: int
    last_action: str = "-"
    last_time_ms: float = 0.0
    avg_time_ms: float = 0.0
    last_nodes: int = 0
    total_nodes: int = 0
    pruned_branches: int = 0


@dataclass(frozen=True)
class ActionLogEntry:
    """Structured combat log entry supporting color-coded hit badges."""

    turn_num: int
    player_id: int
    action_str: str
    hit_pos: tuple[int, int] | None = None
    hit_kind: str | None = None


@dataclass
class FloatingPopup:
    """Animated damage popup drifting upward and fading out over 650ms."""

    grid_x: int
    grid_y: int
    text: str = "-1 HP"
    color: tuple[int, int, int] = theme.IMPACT_ORANGE
    created_tick: int = 0


class GameRenderer:
    """Draws the 13x13 tactical battlefield and right-hand telemetry sidebar."""

    TOOLBAR_BUTTONS: tuple[tuple[str, str], ...] = (
        ("pause", "Pause (Space)"),
        ("step", "Step +1 (N)"),
        ("speed_down", "Speed - ([)"),
        ("speed_up", "Speed + (])"),
        ("restart", "Restart (R)"),
        ("menu", "Menu (M)"),
    )

    def __init__(self, screen: pygame.Surface, fonts: theme.ThemeFonts) -> None:
        self.screen = screen
        self.fonts = fonts
        self.board_origin = (theme.BOARD_X, theme.BOARD_Y)
        self.toolbar_rects: dict[str, pygame.Rect] = {}
        self._eval_cache: tuple[int, int, int, float] | None = None

    def _cell_rect(self, gx: int, gy: int) -> pygame.Rect:
        ox, oy = self.board_origin
        return pygame.Rect(
            ox + gx * theme.CELL_SIZE,
            oy + gy * theme.CELL_SIZE,
            theme.CELL_SIZE,
            theme.CELL_SIZE,
        )

    def _draw_grid(self) -> None:
        ox, oy = self.board_origin
        frame = pygame.Rect(ox - 2, oy - 2, theme.BOARD_WIDTH + 4, theme.BOARD_HEIGHT + 4)
        pygame.draw.rect(self.screen, theme.BORDER_LIGHT, frame, width=2, border_radius=3)

        for x in range(GRID_WIDTH):
            col_lbl = self.fonts.tiny.render(str(x), True, theme.TEXT_MUTED)
            col_rect = col_lbl.get_rect(
                center=(ox + x * theme.CELL_SIZE + theme.CELL_SIZE // 2, oy - 14)
            )
            self.screen.blit(col_lbl, col_rect)

        for y in range(GRID_HEIGHT):
            row_lbl = self.fonts.tiny.render(str(y), True, theme.TEXT_MUTED)
            row_rect = row_lbl.get_rect(
                center=(ox - 16, oy + y * theme.CELL_SIZE + theme.CELL_SIZE // 2)
            )
            self.screen.blit(row_lbl, row_rect)
            for x in range(GRID_WIDTH):
                cell = self._cell_rect(x, y)
                fill = theme.GRID_EVEN if (x + y) % 2 == 0 else theme.GRID_ODD
                pygame.draw.rect(self.screen, fill, cell)
                pygame.draw.rect(self.screen, theme.GRID_LINE, cell, width=1)

    def _draw_walls(self, state: GameState) -> None:
        for (wx, wy), hp in state.walls.items():
            rect = self._cell_rect(wx, wy).inflate(-4, -4)
            base_col = (
                theme.WALL_HP3
                if hp >= 3
                else (theme.WALL_HP2 if hp == 2 else theme.WALL_HP1)
            )
            pygame.draw.rect(self.screen, base_col, rect, border_radius=4)
            pygame.draw.rect(self.screen, theme.WALL_MORTAR, rect, width=1, border_radius=4)

            mid_y = rect.y + rect.height // 2
            pygame.draw.line(self.screen, theme.WALL_MORTAR, (rect.x + 1, mid_y), (rect.right - 2, mid_y), 2)
            pygame.draw.line(
                self.screen,
                theme.WALL_MORTAR,
                (rect.x + rect.width // 2, rect.y + 1),
                (rect.x + rect.width // 2, mid_y),
                2,
            )
            pygame.draw.line(
                self.screen,
                theme.WALL_MORTAR,
                (rect.x + rect.width // 4, mid_y),
                (rect.x + rect.width // 4, rect.bottom - 2),
                2,
            )
            pygame.draw.line(
                self.screen,
                theme.WALL_MORTAR,
                (rect.x + 3 * rect.width // 4, mid_y),
                (rect.x + 3 * rect.width // 4, rect.bottom - 2),
                2,
            )

            if hp <= 2:
                pygame.draw.line(
                    self.screen, theme.WALL_CRACK, (rect.x + 6, rect.y + 6), (rect.x + 18, rect.y + 20), 2
                )
            if hp == 1:
                pygame.draw.line(
                    self.screen, theme.WALL_CRACK, (rect.right - 8, rect.y + 8), (rect.x + 16, rect.bottom - 8), 2
                )

            badge = pygame.Rect(rect.right - 14, rect.bottom - 14, 13, 13)
            pygame.draw.rect(self.screen, theme.SURFACE_CARD, badge, border_radius=2)
            pygame.draw.rect(self.screen, theme.WALL_CRACK, badge, width=1, border_radius=2)
            hp_txt = self.fonts.tiny.render(str(hp), True, theme.TEXT_PRIMARY)
            self.screen.blit(hp_txt, hp_txt.get_rect(center=badge.center))

    def _draw_hp_bar(
        self,
        rect: pygame.Rect,
        hp: int,
        max_hp: int,
        bg: tuple[int, int, int] = theme.EVAL_BAR_BG,
    ) -> None:
        ratio = max(0.0, min(1.0, hp / max(1, max_hp)))
        pygame.draw.rect(self.screen, bg, rect, border_radius=2)
        if ratio > 0:
            fill_w = max(2, int(rect.width * ratio))
            pygame.draw.rect(
                self.screen,
                theme.hp_color(ratio),
                pygame.Rect(rect.x, rect.y, fill_w, rect.height),
                border_radius=2,
            )
        pygame.draw.rect(self.screen, theme.BORDER_LIGHT, rect, width=1, border_radius=2)

    def _draw_bases(self, state: GameState) -> None:
        for pid, base in state.bases.items():
            cell = self._cell_rect(base.x, base.y)
            if not base.is_alive():
                pygame.draw.line(
                    self.screen, theme.STATUS_DANGER, (cell.x + 10, cell.y + 10), (cell.right - 10, cell.bottom - 10), 3
                )
                pygame.draw.line(
                    self.screen, theme.STATUS_DANGER, (cell.right - 10, cell.y + 10), (cell.x + 10, cell.bottom - 10), 3
                )
                continue

            theme.draw_base_shield(
                pygame,
                self.screen,
                cell.centerx,
                cell.centery - 4,
                pid,
                radius=14,
                label_font=self.fonts.tiny,
            )
            self._draw_hp_bar(
                pygame.Rect(cell.x + 5, cell.bottom - 7, cell.width - 10, 5),
                base.hp,
                base.max_hp or BASE_INITIAL_HP,
            )

    def _draw_active_tile_cue(self, cell: pygame.Rect, player_id: int) -> None:
        """Highlight the active turn tile with a clean static tint and square frame."""
        tint = theme.P1_TILE_TINT if player_id == 1 else theme.P2_TILE_TINT
        border_col = theme.P1_PRIMARY if player_id == 1 else theme.P2_PRIMARY
        inner = cell.inflate(-2, -2)
        pygame.draw.rect(self.screen, tint, inner)
        pygame.draw.rect(self.screen, border_col, inner, width=2)

    def _draw_tanks(self, state: GameState, now_tick: int) -> None:
        del now_tick  # Kept in signature for compatibility; active turn indicator is static.
        for pid, tank in state.tanks.items():
            cell = self._cell_rect(tank.x, tank.y)
            if not tank.is_alive():
                pygame.draw.circle(self.screen, theme.STATUS_DANGER, cell.center, 14, width=2)
                continue

            if pid == state.current_turn and not state.is_terminal():
                self._draw_active_tile_cue(cell, pid)

            theme.draw_tank_body(
                pygame,
                self.screen,
                cell.centerx,
                cell.centery + 3,
                pid,
                tank.direction,
                cell_size=theme.CELL_SIZE,
                label_font=self.fonts.tiny,
            )
            self._draw_hp_bar(
                pygame.Rect(cell.x + 5, cell.y + 2, cell.width - 10, 5),
                tank.hp,
                tank.max_hp or TANK_INITIAL_HP,
            )

    def _draw_bullet_fx(self, state: GameState, fx_intensity: float) -> None:
        if not state.last_bullet_path and state.last_hit_pos is None:
            return

        alpha_scale = max(0.35, min(1.0, fx_intensity))
        fx_layer = pygame.Surface((theme.BOARD_WIDTH, theme.BOARD_HEIGHT), pygame.SRCALPHA)
        ox, oy = self.board_origin

        if state.last_bullet_path:
            pts = [
                (
                    bx * theme.CELL_SIZE + theme.CELL_SIZE // 2,
                    by * theme.CELL_SIZE + theme.CELL_SIZE // 2,
                )
                for bx, by in state.last_bullet_path
            ]

            shooter_id = 3 - state.current_turn
            shooter = state.tanks.get(shooter_id)
            if shooter is not None and state.last_action == Action.FIRE:
                dx, dy = shooter.direction.value
                muzzle = (
                    shooter.x * theme.CELL_SIZE + theme.CELL_SIZE // 2 + dx * 18,
                    shooter.y * theme.CELL_SIZE + theme.CELL_SIZE // 2 + 3 + dy * 18,
                )
                pygame.draw.circle(
                    fx_layer, (*theme.BULLET_TRAIL, int(210 * alpha_scale)), muzzle, 4
                )

            if len(pts) >= 2:
                pygame.draw.line(
                    fx_layer, (*theme.BULLET_TRAIL, int(220 * alpha_scale)), pts[0], pts[-1], 3
                )
            for idx, pt in enumerate(pts):
                pygame.draw.circle(
                    fx_layer, (*theme.BULLET_TRAIL, int((170 + idx * 25) * alpha_scale)), pt, 4 + idx
                )
                pygame.draw.circle(fx_layer, (*theme.IMPACT_CORE, int(240 * alpha_scale)), pt, 2)

        if state.last_hit_pos is not None:
            hx, hy = state.last_hit_pos
            hpt = (
                hx * theme.CELL_SIZE + theme.CELL_SIZE // 2,
                hy * theme.CELL_SIZE + theme.CELL_SIZE // 2,
            )
            pygame.draw.circle(fx_layer, (*theme.IMPACT_ORANGE, int(210 * alpha_scale)), hpt, 14, width=2)
            pygame.draw.circle(fx_layer, (*theme.BULLET_TRAIL, int(230 * alpha_scale)), hpt, 8)
            pygame.draw.circle(fx_layer, (*theme.IMPACT_CORE, int(245 * alpha_scale)), hpt, 3)

        self.screen.blit(fx_layer, (ox, oy))

    def _draw_popups(self, popups: list[FloatingPopup], now_tick: int) -> None:
        ox, oy = self.board_origin
        for popup in popups:
            elapsed = max(0, now_tick - popup.created_tick)
            if elapsed > POPUP_DURATION_MS:
                continue
            progress = elapsed / POPUP_DURATION_MS
            alpha = int(255 * (1.0 - progress))
            px = ox + popup.grid_x * theme.CELL_SIZE + theme.CELL_SIZE // 2
            py = oy + popup.grid_y * theme.CELL_SIZE + 8 - int(progress * 24)

            txt_surf = self.fonts.mono_bold.render(popup.text, True, popup.color)
            bg_surf = pygame.Surface((txt_surf.get_width() + 10, txt_surf.get_height() + 4), pygame.SRCALPHA)
            bg_rect_local = bg_surf.get_rect()
            pygame.draw.rect(
                bg_surf, (*theme.SURFACE_CARD, int(235 * (1.0 - progress))), bg_rect_local, border_radius=3
            )
            pygame.draw.rect(
                bg_surf, (*popup.color, int(225 * (1.0 - progress))), bg_rect_local, width=1, border_radius=3
            )
            txt_surf.set_alpha(alpha)
            bg_rect = bg_surf.get_rect(center=(px, py))
            self.screen.blit(bg_surf, bg_rect)
            self.screen.blit(txt_surf, txt_surf.get_rect(center=(px, py)))

    def _draw_match_card(
        self,
        rect: pygame.Rect,
        state: GameState,
        paused: bool,
        map_name: str,
    ) -> None:
        pygame.draw.rect(self.screen, theme.SURFACE_CARD, rect, border_radius=4)
        pygame.draw.rect(self.screen, theme.BORDER_SUBTLE, rect, width=1, border_radius=4)

        turn_txt = self.fonts.heading.render(
            f"Turn {state.turn_count} / {state.max_turns}", True, theme.TEXT_PRIMARY
        )
        self.screen.blit(turn_txt, (rect.x + 14, rect.y + 10))
        map_surf = self.fonts.small.render(map_name, True, theme.TEXT_MUTED)
        self.screen.blit(map_surf, (rect.x + 14, rect.y + 30))

        if state.is_terminal():
            winner = state.get_winner()
            if winner == 1:
                badge_txt, badge_col = "P1 wins", theme.P1_PRIMARY
            elif winner == 2:
                badge_txt, badge_col = "P2 wins", theme.P2_PRIMARY
            else:
                badge_txt, badge_col = "Draw", theme.STATUS_WARN
        elif paused:
            badge_txt, badge_col = "Paused", theme.STATUS_WARN
        elif state.current_turn == 1:
            badge_txt, badge_col = "P1 turn", theme.P1_PRIMARY
        else:
            badge_txt, badge_col = "P2 turn", theme.P2_PRIMARY

        badge_surf = self.fonts.heading.render(badge_txt, True, badge_col)
        self.screen.blit(badge_surf, (rect.right - badge_surf.get_width() - 14, rect.y + 11))

        footer = (
            self._terminal_reason(state)
            if state.is_terminal()
            else (f"Last move: {state.last_action.value}" if state.last_action else "Match ready")
        )
        self.screen.blit(self.fonts.small.render(footer, True, theme.TEXT_SECONDARY), (rect.x + 14, rect.y + 48))

    @staticmethod
    def _terminal_reason(state: GameState) -> str:
        t1_alive = state.tanks[1].is_alive()
        t2_alive = state.tanks[2].is_alive()
        b1_alive = state.bases[1].is_alive()
        b2_alive = state.bases[2].is_alive()
        if not b2_alive and (t1_alive and b1_alive):
            return "P2 base destroyed"
        if not t2_alive and (t1_alive and b1_alive):
            return "P2 tank destroyed"
        if not b1_alive and (t2_alive and b2_alive):
            return "P1 base destroyed"
        if not t1_alive and (t2_alive and b2_alive):
            return "P1 tank destroyed"
        if state.turn_count >= state.max_turns:
            return f"Turn limit ({state.max_turns}) reached"
        return "Both sides eliminated"

    def _get_eval_score(self, state: GameState) -> float:
        key = (id(state), state.turn_count, state.current_turn)
        if self._eval_cache is not None and self._eval_cache[:3] == key:
            return self._eval_cache[3]
        try:
            score = float(tactical_evaluate(state, 1))
        except Exception:
            score = 0.0
        self._eval_cache = (*key, score)
        return score

    def _draw_eval_bar(self, rect: pygame.Rect, state: GameState, eval_score: float | None) -> None:
        score = eval_score if eval_score is not None else self._get_eval_score(state)
        p1_share = max(0.05, min(0.95, 0.5 + 0.45 * math.tanh(score / 600.0)))

        pygame.draw.rect(self.screen, theme.SURFACE_CARD, rect, border_radius=4)
        pygame.draw.rect(self.screen, theme.BORDER_SUBTLE, rect, width=1, border_radius=4)

        lbl = self.fonts.small.render("Advantage", True, theme.TEXT_MUTED)
        self.screen.blit(lbl, (rect.x + 14, rect.y + 6))

        if abs(score) < 1.0:
            score_txt, score_col = "Even", theme.TEXT_SECONDARY
        elif score > 0:
            score_txt, score_col = f"P1 +{score:.0f}", theme.P1_PRIMARY
        else:
            score_txt, score_col = f"P2 +{abs(score):.0f}", theme.P2_PRIMARY

        s_surf = self.fonts.mono_bold.render(score_txt, True, score_col)
        self.screen.blit(s_surf, (rect.right - s_surf.get_width() - 14, rect.y + 6))

        bar = pygame.Rect(rect.x + 14, rect.y + 25, rect.width - 28, 13)
        pygame.draw.rect(self.screen, theme.EVAL_BAR_BG, bar, border_radius=2)

        p1_w = max(2, int(bar.width * p1_share))
        p2_w = max(2, bar.width - p1_w)
        pygame.draw.rect(self.screen, theme.P1_PRIMARY, pygame.Rect(bar.x, bar.y, p1_w, bar.height))
        pygame.draw.rect(
            self.screen, theme.P2_PRIMARY, pygame.Rect(bar.x + p1_w, bar.y, p2_w, bar.height)
        )
        seam_x = bar.x + p1_w
        pygame.draw.line(self.screen, theme.TEXT_ON_ACCENT, (seam_x, bar.y), (seam_x, bar.bottom - 1), 2)
        mid_x = bar.x + bar.width // 2
        pygame.draw.line(self.screen, theme.BORDER_LIGHT, (mid_x, bar.y - 2), (mid_x, bar.bottom + 1), 1)
        pygame.draw.rect(self.screen, theme.BORDER_LIGHT, bar, width=1, border_radius=2)

    def _draw_player_card(
        self,
        rect: pygame.Rect,
        player_id: int,
        state: GameState,
        telemetry: PlayerTelemetry,
        is_active: bool,
    ) -> None:
        accent = theme.P1_PRIMARY if player_id == 1 else theme.P2_PRIMARY
        active_now = is_active and not state.is_terminal()
        border = accent if active_now else theme.BORDER_SUBTLE
        pygame.draw.rect(self.screen, theme.SURFACE_CARD, rect, border_radius=4)
        pygame.draw.rect(self.screen, border, rect, width=2 if active_now else 1, border_radius=4)

        role = "Human" if telemetry.is_human else f"d={telemetry.depth}"
        hdr = self.fonts.body_bold.render(
            f"P{player_id}: {telemetry.name[:24]} ({role})", True, accent
        )
        self.screen.blit(hdr, (rect.x + 14, rect.y + 8))

        tank = state.tanks[player_id]
        base = state.bases[player_id]

        self.screen.blit(
            self.fonts.small.render(f"Tank HP  {tank.hp}/{tank.max_hp}", True, theme.TEXT_SECONDARY),
            (rect.x + 14, rect.y + 32),
        )
        self._draw_hp_bar(
            pygame.Rect(rect.x + 106, rect.y + 35, rect.width - 122, 9),
            tank.hp,
            tank.max_hp or TANK_INITIAL_HP,
            bg=theme.SURFACE_ELEVATED,
        )

        self.screen.blit(
            self.fonts.small.render(f"Base HP  {base.hp}/{base.max_hp}", True, theme.TEXT_SECONDARY),
            (rect.x + 14, rect.y + 52),
        )
        self._draw_hp_bar(
            pygame.Rect(rect.x + 106, rect.y + 55, rect.width - 122, 9),
            base.hp,
            base.max_hp or BASE_INITIAL_HP,
            bg=theme.SURFACE_ELEVATED,
        )

        m1 = self.fonts.mono.render(
            f"Last: {telemetry.last_action:<10} Avg: {telemetry.avg_time_ms:.2f} ms",
            True,
            theme.TEXT_PRIMARY,
        )
        m2 = self.fonts.mono.render(
            f"Nodes: {telemetry.last_nodes:,} (Sum {telemetry.total_nodes:,}) | Pruned: {telemetry.pruned_branches:,}",
            True,
            theme.TEXT_MUTED,
        )
        self.screen.blit(m1, (rect.x + 14, rect.y + 73))
        self.screen.blit(m2, (rect.x + 14, rect.y + 93))

    def _draw_log_card(
        self,
        rect: pygame.Rect,
        action_log: list[ActionLogEntry | str],
    ) -> None:
        pygame.draw.rect(self.screen, theme.SURFACE_CARD, rect, border_radius=4)
        pygame.draw.rect(self.screen, theme.BORDER_SUBTLE, rect, width=1, border_radius=4)
        hdr = self.fonts.small.render("Move Log", True, theme.TEXT_PRIMARY)
        self.screen.blit(hdr, (rect.x + 14, rect.y + 7))
        pygame.draw.line(
            self.screen,
            theme.BORDER_SUBTLE,
            (rect.x + 12, rect.y + 24),
            (rect.right - 12, rect.y + 24),
            1,
        )

        y = rect.y + 30
        for entry in action_log[-5:]:
            if isinstance(entry, str):
                surf = self.fonts.mono.render(entry[:48], True, theme.TEXT_SECONDARY)
                self.screen.blit(surf, (rect.x + 14, y))
                y += 22
                continue

            x = rect.x + 14
            turn_s = self.fonts.mono.render(f"#{entry.turn_num:03d} ", True, theme.TEXT_MUTED)
            self.screen.blit(turn_s, (x, y))
            x += turn_s.get_width()

            p_col = theme.P1_PRIMARY if entry.player_id == 1 else theme.P2_PRIMARY
            p_s = self.fonts.mono_bold.render(f"P{entry.player_id} ", True, p_col)
            self.screen.blit(p_s, (x, y))
            x += p_s.get_width()

            act_s = self.fonts.mono.render(entry.action_str, True, theme.TEXT_PRIMARY)
            self.screen.blit(act_s, (x, y))
            x += act_s.get_width() + 6

            if entry.hit_pos is not None:
                badge_col = (
                    theme.STATUS_DANGER
                    if entry.hit_kind in ("tank", "base")
                    else theme.IMPACT_ORANGE
                )
                hit_lbl = self.fonts.tiny.render(
                    f"HIT ({entry.hit_pos[0]},{entry.hit_pos[1]}) -1 HP",
                    True,
                    theme.TEXT_ON_ACCENT,
                )
                pill = pygame.Rect(x, y, hit_lbl.get_width() + 10, 16)
                if pill.right <= rect.right - 8:
                    pygame.draw.rect(self.screen, badge_col, pill, border_radius=3)
                    self.screen.blit(hit_lbl, hit_lbl.get_rect(center=pill.center))
            y += 22

    def _draw_controls_card(
        self,
        rect: pygame.Rect,
        human_turn: bool,
        paused: bool,
        step_delay_ms: int,
    ) -> None:
        self.toolbar_rects.clear()
        pygame.draw.rect(self.screen, theme.SURFACE_CARD, rect, border_radius=4)
        pygame.draw.rect(self.screen, theme.BORDER_SUBTLE, rect, width=1, border_radius=4)

        top_lbl = (
            "Human turn: Arrows/WASD move | F/Space fire | X stay"
            if human_turn
            else f"Controls  (step {step_delay_ms} ms)"
        )
        top_col = theme.STATUS_GOOD if human_turn else theme.TEXT_MUTED
        self.screen.blit(self.fonts.small.render(top_lbl, True, top_col), (rect.x + 12, rect.y + 7))

        mouse_pos = pygame.mouse.get_pos()
        cols = 3
        gap_x = 8
        gap_y = 7
        btn_w = (rect.width - 24 - (cols - 1) * gap_x) // cols
        btn_h = 34
        start_x = rect.x + 12
        start_y = rect.y + 28

        for idx, (key, label) in enumerate(self.TOOLBAR_BUTTONS):
            r = idx // cols
            c = idx % cols
            bx = start_x + c * (btn_w + gap_x)
            by = start_y + r * (btn_h + gap_y)
            btn_rect = pygame.Rect(bx, by, btn_w, btn_h)
            self.toolbar_rects[key] = btn_rect

            display_label = ("Play (Space)" if paused else "Pause (Space)") if key == "pause" else label
            is_active = key == "pause" and paused
            hovered = btn_rect.collidepoint(mouse_pos)
            bg = theme.BTN_ACTIVE if is_active else (theme.BTN_HOVER if hovered else theme.BTN_BG)
            fg = theme.TEXT_ON_ACCENT if is_active else theme.TEXT_PRIMARY

            pygame.draw.rect(self.screen, bg, btn_rect, border_radius=4)
            pygame.draw.rect(self.screen, theme.BORDER_LIGHT, btn_rect, width=1, border_radius=4)
            lbl_surf = self.fonts.tiny.render(display_label, True, fg)
            self.screen.blit(lbl_surf, lbl_surf.get_rect(center=btn_rect.center))

    def draw(
        self,
        state: GameState,
        p1_tel: PlayerTelemetry,
        p2_tel: PlayerTelemetry,
        map_name: str,
        paused: bool,
        step_delay_ms: int,
        action_log: list[ActionLogEntry | str],
        fx_intensity: float,
        eval_score: float | None = None,
        popups: list[FloatingPopup] | None = None,
        now_tick: int | None = None,
    ) -> None:
        """Render one complete frame of the battlefield, FX, and telemetry sidebar."""
        tick = now_tick if now_tick is not None else pygame.time.get_ticks()
        self.screen.fill(theme.BG_DARK)

        self._draw_grid()
        self._draw_walls(state)
        self._draw_bases(state)
        self._draw_tanks(state, tick)
        self._draw_bullet_fx(state, fx_intensity)
        if popups:
            self._draw_popups(popups, tick)

        sx = theme.SIDEBAR_X
        sw = theme.SIDEBAR_WIDTH
        y = 20

        self._draw_match_card(pygame.Rect(sx, y, sw, 68), state, paused, map_name)
        y += 76

        self._draw_eval_bar(pygame.Rect(sx, y, sw, 48), state, eval_score)
        y += 56

        self._draw_player_card(
            pygame.Rect(sx, y, sw, 116),
            1,
            state,
            p1_tel,
            is_active=(state.current_turn == 1),
        )
        y += 124

        self._draw_player_card(
            pygame.Rect(sx, y, sw, 116),
            2,
            state,
            p2_tel,
            is_active=(state.current_turn == 2),
        )
        y += 124

        self._draw_log_card(pygame.Rect(sx, y, sw, 144), action_log)
        y += 152

        active_tel = p1_tel if state.current_turn == 1 else p2_tel
        human_turn = active_tel.is_human and not state.is_terminal()
        self._draw_controls_card(pygame.Rect(sx, y, sw, 114), human_turn, paused, step_delay_ms)


class TankBattleApp:
    """Top-level interactive PyGame application managing menu and live matches."""

    HUMAN_KEY_ACTIONS = {
        pygame.K_UP: Action.MOVE_UP,
        pygame.K_w: Action.MOVE_UP,
        pygame.K_DOWN: Action.MOVE_DOWN,
        pygame.K_s: Action.MOVE_DOWN,
        pygame.K_LEFT: Action.MOVE_LEFT,
        pygame.K_a: Action.MOVE_LEFT,
        pygame.K_RIGHT: Action.MOVE_RIGHT,
        pygame.K_d: Action.MOVE_RIGHT,
        pygame.K_f: Action.FIRE,
        pygame.K_RETURN: Action.FIRE,
        pygame.K_SPACE: Action.FIRE,
        pygame.K_x: Action.STAY,
    }

    def __init__(self, initial_config: MatchConfig | None = None) -> None:
        self.initial_config = initial_config

    @staticmethod
    def _instantiate_player(
        player_id: int,
        label: str,
        agent_cls: type[BaseAgent] | None,
        depth: int,
    ) -> tuple[BaseAgent | None, PlayerTelemetry]:
        if agent_cls is None:
            return None, PlayerTelemetry(name="Human", is_human=True, depth=0)
        try:
            agent = agent_cls(player_id=player_id, depth=depth)
        except TypeError:
            agent = agent_cls(player_id=player_id)
        return agent, PlayerTelemetry(
            name=getattr(agent, "name", label),
            is_human=False,
            depth=depth,
        )

    @staticmethod
    def _update_telemetry(
        telemetry: PlayerTelemetry,
        agent: BaseAgent | None,
        action: Action,
        elapsed_ms: float,
    ) -> None:
        telemetry.last_action = action.value
        if agent is None:
            telemetry.last_time_ms = elapsed_ms
            return
        telemetry.last_time_ms = float(getattr(agent, "last_time_ms", elapsed_ms))
        telemetry.avg_time_ms = float(getattr(agent, "avg_time_ms", elapsed_ms))
        telemetry.last_nodes = int(getattr(agent, "nodes_explored", 0))
        telemetry.total_nodes = int(getattr(agent, "total_nodes_explored", 0))
        telemetry.pruned_branches = int(getattr(agent, "pruned_branches", 0))

    @staticmethod
    def _popup_color(hit_kind: str | None) -> tuple[int, int, int]:
        if hit_kind == "tank":
            return theme.STATUS_DANGER
        if hit_kind == "base":
            return theme.BASE_P1
        return theme.IMPACT_ORANGE

    def _run_match(
        self,
        screen: pygame.Surface,
        fonts: theme.ThemeFonts,
        clock: pygame.time.Clock,
        renderer: GameRenderer,
        cfg: MatchConfig,
    ) -> str:
        """Execute a match loop; returns 'menu' or 'quit'."""
        state = GameState.from_file(cfg.map_path)
        p1_agent, p1_tel = self._instantiate_player(1, cfg.p1_label, cfg.p1_cls, cfg.depth)
        p2_agent, p2_tel = self._instantiate_player(2, cfg.p2_label, cfg.p2_cls, cfg.depth)

        paused = False
        step_once = False
        step_delay_ms = 220
        last_step_tick = pygame.time.get_ticks()
        last_fx_tick = 0
        human_action: Action | None = None
        action_log: deque[ActionLogEntry] = deque(maxlen=12)
        popups: list[FloatingPopup] = []
        eval_score = float(tactical_evaluate(state, 1))

        def _restart() -> None:
            nonlocal state, p1_agent, p1_tel, p2_agent, p2_tel
            nonlocal paused, step_once, last_step_tick, last_fx_tick, human_action, eval_score
            state = GameState.from_file(cfg.map_path)
            p1_agent, p1_tel = self._instantiate_player(1, cfg.p1_label, cfg.p1_cls, cfg.depth)
            p2_agent, p2_tel = self._instantiate_player(2, cfg.p2_label, cfg.p2_cls, cfg.depth)
            paused = False
            step_once = False
            last_step_tick = pygame.time.get_ticks()
            last_fx_tick = 0
            human_action = None
            action_log.clear()
            popups.clear()
            eval_score = float(tactical_evaluate(state, 1))

        while True:
            human_action = None

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return "quit"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for key, btn_rect in renderer.toolbar_rects.items():
                        if not btn_rect.collidepoint(event.pos):
                            continue
                        if key == "pause":
                            paused = not paused
                        elif key == "step" and not state.is_terminal():
                            paused = True
                            step_once = True
                        elif key == "speed_down":
                            step_delay_ms = min(1000, step_delay_ms + 60)
                        elif key == "speed_up":
                            step_delay_ms = max(40, step_delay_ms - 60)
                        elif key == "restart":
                            _restart()
                        elif key == "menu":
                            return "menu"
                        break
                elif event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_m):
                        return "menu"
                    if event.key == pygame.K_r:
                        _restart()
                        continue
                    if event.key == pygame.K_LEFTBRACKET:
                        step_delay_ms = min(1000, step_delay_ms + 60)
                    elif event.key == pygame.K_RIGHTBRACKET:
                        step_delay_ms = max(40, step_delay_ms - 60)
                    elif event.key == pygame.K_p:
                        paused = not paused
                    else:
                        current_agent = p1_agent if state.current_turn == 1 else p2_agent
                        if (
                            not state.is_terminal()
                            and current_agent is None
                            and event.key in self.HUMAN_KEY_ACTIONS
                        ):
                            human_action = self.HUMAN_KEY_ACTIONS[event.key]
                        elif event.key == pygame.K_SPACE:
                            paused = not paused
                        elif event.key == pygame.K_n and not state.is_terminal():
                            paused = True
                            step_once = True

            active_pid = state.current_turn
            active_agent = p1_agent if active_pid == 1 else p2_agent
            active_tel = p1_tel if active_pid == 1 else p2_tel
            now = pygame.time.get_ticks()
            chosen_action: Action | None = None
            elapsed_ms = 0.0

            if not state.is_terminal():
                if active_agent is None and human_action is not None:
                    chosen_action = human_action
                elif active_agent is not None:
                    should_step = step_once or (
                        not paused and (now - last_step_tick) >= step_delay_ms
                    )
                    if should_step:
                        t0 = time.perf_counter()
                        chosen_action = AgentLoader.safe_get_action(active_agent, state)
                        elapsed_ms = (time.perf_counter() - t0) * 1000.0
                        last_step_tick = pygame.time.get_ticks()
                        step_once = False

            if chosen_action is not None:
                state = GameEngine.apply_action(state, chosen_action)
                self._update_telemetry(active_tel, active_agent, chosen_action, elapsed_ms)
                eval_score = float(tactical_evaluate(state, 1))
                hit_kind = getattr(state, "last_hit_kind", None)

                action_log.append(
                    ActionLogEntry(
                        turn_num=state.turn_count,
                        player_id=active_pid,
                        action_str=chosen_action.value,
                        hit_pos=state.last_hit_pos,
                        hit_kind=hit_kind,
                    )
                )
                if state.last_bullet_path or state.last_hit_pos is not None:
                    last_fx_tick = pygame.time.get_ticks()
                if state.last_hit_pos is not None:
                    hx, hy = state.last_hit_pos
                    popups.append(
                        FloatingPopup(
                            grid_x=hx,
                            grid_y=hy,
                            text="-1 HP",
                            color=self._popup_color(hit_kind),
                            created_tick=pygame.time.get_ticks(),
                        )
                    )

            now = pygame.time.get_ticks()
            popups = [p for p in popups if (now - p.created_tick) <= POPUP_DURATION_MS]
            fx_elapsed = now - last_fx_tick
            fx_intensity = max(0.35, 1.0 - fx_elapsed / 400.0) if last_fx_tick else 0.5

            renderer.draw(
                state=state,
                p1_tel=p1_tel,
                p2_tel=p2_tel,
                map_name=cfg.map_name,
                paused=paused,
                step_delay_ms=step_delay_ms,
                action_log=list(action_log),
                fx_intensity=fx_intensity,
                eval_score=eval_score,
                popups=popups,
                now_tick=now,
            )
            pygame.display.flip()
            clock.tick(theme.FPS)

    def run(self) -> None:
        """Initialize PyGame display and loop between SetupMenu and matches."""
        pygame.init()
        try:
            pygame.display.set_caption("Tank Battle")
            screen = pygame.display.set_mode((theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT))
            fonts = theme.load_fonts(pygame)
            clock = pygame.time.Clock()
            renderer = GameRenderer(screen, fonts)

            pending_cfg = self.initial_config
            while True:
                cfg = pending_cfg
                pending_cfg = None
                if cfg is None:
                    cfg = SetupMenu(screen, fonts, clock).run()
                if cfg is None:
                    break
                outcome = self._run_match(screen, fonts, clock, renderer, cfg)
                if outcome == "quit":
                    break
        finally:
            pygame.quit()
