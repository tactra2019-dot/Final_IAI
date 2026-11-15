"""Pygame view and input controller driven by solver observer events."""

import pygame

from solver.backtracking import CSPSolver
from solver.callback import SolverEvent


class KakuroVisualizer:
    """Render the live CSP. Parameters: board model, optional initial delay.

    Returns: a Pygame view with an input controller and solver observer.
    """

    CELL = 68
    ORIGIN = (28, 82)
    COLORS = {'assign': (162, 224, 181), 'prune': (255, 211, 128),
              'conflict': (249, 143, 143), 'backtrack': (249, 143, 143),
              'restore': (190, 211, 248)}

    def __init__(self, board, delay_ms=70):
        """Initialize UI/controller. Parameters: board, delay. Returns:
        None.
        """
        pygame.init()
        self.board = board
        self.width = max(980, board.cols * self.CELL + 360)
        self.height = max(740, board.rows * self.CELL + 110)
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption('Kakuro | CSP - GAC / MRV / Degree / LCV')
        self.font = pygame.font.SysFont('consolas', 19)
        self.small = pygame.font.SysFont('consolas', 15)
        self.large = pygame.font.SysFont('consolas', 34, bold=True)
        self.title = pygame.font.SysFont('consolas', 27, bold=True)
        self.panel_x = self.ORIGIN[0] + board.cols * self.CELL + 28
        self.play_rect = pygame.Rect(self.panel_x, 130, 132, 40)
        self.step_rect = pygame.Rect(self.panel_x + 142, 130, 120, 40)
        self.reset_rect = pygame.Rect(self.panel_x, 182, 262, 38)
        self.slider = pygame.Rect(self.panel_x, 278, 250, 8)
        self.delay_ms = max(0, min(500, delay_ms))
        self.dragging = False
        self.paused = True
        self.finished = False
        self.last_tick = 0
        self.event = SolverEvent('ready')
        self.solver = CSPSolver(board, self)
        self.stream = self.solver.events()

    def on_event(self, event):
        """Receive observer notification. Parameters: event. Returns: None."""
        self.event = event
        if event.kind in {'solved', 'unsatisfiable'}:
            self.finished = True
            self.paused = True

    def advance(self):
        """Execute exactly one visible event. Parameters: none. Returns:
        None.
        """
        if not self.finished:
            try:
                next(self.stream)
            except StopIteration:
                self.finished = True

    def reset(self):
        """Cancel search and reset model. Parameters: none. Returns: None."""
        self.stream.close()
        self.board.reset()
        self.solver = CSPSolver(self.board, self)
        self.stream = self.solver.events()
        self.event = SolverEvent('ready')
        self.paused, self.finished = True, False

    def _set_speed(self, x):
        """Set delay from slider. Parameters: mouse x. Returns: None."""
        fraction = max(0, min(1, (x - self.slider.x) / self.slider.width))
        self.delay_ms = round(fraction * 500)

    def handle_event(self, event):
        """Handle controls. Parameters: Pygame input event. Returns: keep-
        running.
        """
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return False
            if event.key == pygame.K_SPACE and not self.finished:
                self.paused = not self.paused
            elif event.key == pygame.K_n:
                self.paused = True
                self.advance()
            elif event.key == pygame.K_r:
                self.reset()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.play_rect.collidepoint(event.pos) and not self.finished:
                self.paused = not self.paused
            elif self.step_rect.collidepoint(event.pos):
                self.paused = True
                self.advance()
            elif self.reset_rect.collidepoint(event.pos):
                self.reset()
            elif self.slider.inflate(20, 28).collidepoint(event.pos):
                self.dragging = True
                self._set_speed(event.pos[0])
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self._set_speed(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False
        return True

    def _text(self, text, position, font=None, color=(224, 232, 243)):
        """Draw a label. Parameters: text, position, font, color. Returns:
        None.
        """
        glyph = (font or self.font).render(str(text), True, color)
        self.screen.blit(glyph, position)

    def _draw_cell(self, row, col, cell):
        """Draw clues/value/domain. Parameters: row, col, cell. Returns:
        None.
        """
        x = self.ORIGIN[0] + col * self.CELL
        y = self.ORIGIN[1] + row * self.CELL
        rect = pygame.Rect(x, y, self.CELL, self.CELL)
        dark = (31, 42, 60)
        if cell == '.':
            color = (243, 246, 250)
            if self.event.position == (row, col):
                color = self.COLORS.get(self.event.kind, color)
            pygame.draw.rect(self.screen, color, rect)
            variable = self.board.variables[row, col]
            if variable.value is not None:
                glyph = self.large.render(str(variable.value), True, dark)
                self.screen.blit(glyph, glyph.get_rect(center=rect.center))
            else:
                for digit in sorted(variable.domain):
                    dx, dy = (digit - 1) % 3, (digit - 1) // 3
                    self._text(digit, (x + 10 + dx * 19, y + 5 + dy * 20),
                               self.small, (80, 98, 122))
                if not variable.domain:
                    self._text('!', (x + 26, y + 14),
                               self.large, (160, 20, 20))
        else:
            pygame.draw.rect(self.screen, (95, 109, 130), rect)
            pygame.draw.line(self.screen, dark,
                             rect.topleft, rect.bottomright, 2)
            if isinstance(cell, dict):
                if 'across' in cell:
                    glyph = self.font.render(str(cell['across']),
                                             True, (255, 255, 255))
                    self.screen.blit(
                        glyph, (rect.right - glyph.get_width() - 5, y + 5))
                if 'down' in cell:
                    self._text(cell['down'], (x + 5, rect.bottom - 25))
        pygame.draw.rect(self.screen, dark, rect, 2)

    def draw(self):
        """Render a complete frame. Parameters: none. Returns: None."""
        self.screen.fill((18, 26, 40))
        self._text('KAKURO / CONSTRAINT SATISFACTION', (28, 22), self.title)
        for row, cells in enumerate(self.board.grid):
            for col, cell in enumerate(cells):
                self._draw_cell(row, col, cell)
        x = self.panel_x
        self._text('GAC + Backtracking', (x, 86))
        buttons = ((self.play_rect, 'Play' if self.paused else 'Pause'),
                   (self.step_rect, 'Step'), (self.reset_rect, 'Reset'))
        for rect, label in buttons:
            pygame.draw.rect(self.screen, (47, 65, 91), rect, border_radius=6)
            glyph = self.font.render(label, True, (241, 246, 255))
            self.screen.blit(glyph, glyph.get_rect(center=rect.center))
        self._text(f'Delay: {self.delay_ms} ms', (x, 242))
        pygame.draw.rect(self.screen, (80, 100, 127), self.slider)
        pygame.draw.circle(self.screen, (97, 190, 240),
                           (self.slider.x + round(self.delay_ms / 500 * 250),
                            self.slider.centery), 9)
        self._text('Fast                       Slow', (x, 298), self.small)
        state = self.event.kind.upper()
        self._text(state, (x, 342), color=(125, 206, 249))
        if self.event.position:
            r, c = self.event.position
            self._text(f'Cell: row {r + 1}, col {c + 1}', (x, 372), self.small)
        if self.event.removed:
            self._text('Removed: ' + ','.join(map(str, self.event.removed)),
                       (x, 396), self.small)
        stats = self.solver.stats
        for index, line in enumerate((f'Assignments: {stats.assignments}',
                                      f'Backtracks:  {stats.backtracks}',
                                      f'Pruned:      {stats.pruned}',
                                      f'Compute: {stats.elapsed:.3f}s')):
            self._text(line, (x, 434 + index * 25), self.small)
        legend = (('assign', 'Assign / forward'), ('prune', 'GAC pruning'),
                  ('backtrack', 'Conflict / backtrack'),
                  ('restore', 'Restore domains'))
        for index, (kind, label) in enumerate(legend):
            y = 552 + index * 25
            pygame.draw.rect(self.screen, self.COLORS[kind], (x, y, 14, 14))
            self._text(label, (x + 23, y - 2), self.small)
        self._text('Space: Play/Pause | N: Step', (x, 665), self.small)
        self._text('R: Reset | Esc: Quit', (x, 688), self.small)
        pygame.display.flip()

    def run(self):
        """Run interactive application. Parameters: none. Returns: None."""
        clock = pygame.time.Clock()
        running = True
        try:
            while running:
                for event in pygame.event.get():
                    running = self.handle_event(event) and running
                now = pygame.time.get_ticks()
                if not self.paused and now - self.last_tick >= self.delay_ms:
                    self.advance()
                    self.last_tick = pygame.time.get_ticks()
                self.draw()
                clock.tick(60)
        finally:
            self.stream.close()
            pygame.quit()
