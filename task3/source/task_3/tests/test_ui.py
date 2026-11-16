"""Exercise real Pygame rendering and controls through the SDL dummy driver."""

import os
from pathlib import Path
import unittest

import pygame

from models.board import KakuroBoard
from solver.callback import SolverEvent
from ui.visualizer import KakuroVisualizer


os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'


class VisualizerTests(unittest.TestCase):
    """Check input, live state, and drawing. Parameters: unittest defaults.

    Returns: a unittest test-case instance.
    """

    def test_controls_render_and_completion(self):
        """Exercise UI lifecycle. Parameters: none. Returns: None."""
        path = (Path(__file__).resolve().parents[1]
                / 'test_cases' / 'board_9x9.json')
        view = KakuroVisualizer(KakuroBoard.from_json(path))
        try:
            view.draw()
            self.assertTrue(view.paused)
            view.handle_event(pygame.event.Event(
                pygame.KEYDOWN, key=pygame.K_n))
            self.assertEqual(view.event.kind, 'prune')
            view.draw()
            view.handle_event(pygame.event.Event(
                pygame.KEYDOWN, key=pygame.K_SPACE))
            self.assertFalse(view.paused)
            view.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=view.slider.midright))
            self.assertEqual(view.delay_ms, 500)
            view.handle_event(pygame.event.Event(
                pygame.MOUSEMOTION, pos=view.slider.midleft))
            self.assertEqual(view.delay_ms, 0)
            view.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONUP, button=1))
            for _ in range(2000):
                if view.finished:
                    break
                view.advance()
            self.assertTrue(view.finished)
            self.assertTrue(view.board.is_solved())
            view.draw()
            view.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=view.reset_rect.center))
            self.assertTrue(view.paused)
            self.assertFalse(view.finished)
            view.handle_event(pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=view.step_rect.center))
            self.assertEqual(view.event.kind, 'prune')
            view.on_event(SolverEvent('backtrack', (1, 2), 5))
            view.draw()
            self.assertFalse(view.handle_event(
                pygame.event.Event(pygame.QUIT)))
        finally:
            view.stream.close()
            pygame.quit()


if __name__ == '__main__':
    unittest.main()
