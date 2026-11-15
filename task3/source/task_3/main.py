"""Launch Task 3 with Pygame or a dependency-free headless solver."""

import argparse
from pathlib import Path

from models.board import KakuroBoard
from solver.backtracking import CSPSolver


def main():
    """Parse CLI and launch controller. Parameters: CLI arguments. Returns:
    exit code.
    """
    parser = argparse.ArgumentParser(description='Task 3: Kakuro CSP')
    parser.add_argument('--board', type=Path, default=Path(__file__).parent
                        / 'test_cases' / 'board_9x9.json')
    parser.add_argument('--headless', action='store_true')
    parser.add_argument('--delay', type=int, default=70,
                        help='UI delay in ms (0-500)')
    args = parser.parse_args()
    try:
        board = KakuroBoard.from_json(args.board)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    if args.headless:
        solver = CSPSolver(board)
        solved = solver.solve()
        print('SOLVED' if solved else 'UNSATISFIABLE')
        for row in range(board.rows):
            print(' '.join(str(board.variables[row, col].value)
                           if (row, col) in board.variables else '#'
                           for col in range(board.cols)))
        print(solver.stats)
        return 0 if solved else 1
    from ui.visualizer import KakuroVisualizer

    KakuroVisualizer(board, args.delay).run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
