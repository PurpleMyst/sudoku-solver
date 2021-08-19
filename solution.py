import typing as t
from itertools import chain
from dataclasses import dataclass, field
from collections import ChainMap

import click


SIDE = 9
STEPS = 2
POPULATION_SIZE = 1000

ALL_NUMBERS = set(range(1, 10))

Board = t.List[int]
Point = t.Tuple[int, int]


def box_pos(px: int, py: int) -> t.Iterator[Point]:
    sx, sy = px // 3 * 3, py // 3 * 3
    for i in range(3):
        for j in range(3):
            yield (sx + j, sy + i)


def neighborhood(board: Board, px: int, py: int) -> t.Iterator[int]:
    for y in range(SIDE):
        yield board[y * SIDE + px]
    for x in range(SIDE):
        yield board[py * SIDE + x]
    for (x, y) in box_pos(px, py):
        yield board[y * SIDE + x]


def houses() -> t.Iterator[t.Sequence[Point]]:
    for by in range(0, SIDE, 3):
        for bx in range(0, SIDE, 3):
            yield list(box_pos(bx, by))

    for y in range(SIDE):
        yield [(x, y) for x in range(SIDE)]

    for x in range(SIDE):
        yield [(x, y) for y in range(SIDE)]


def possibilities(board: Board, px: int, py: int) -> t.Set[int]:
    return ALL_NUMBERS - set(neighborhood(board, px, py)) - {0}


@dataclass
class SolverStep:
    board: Board

    markups: t.Dict[Point, t.Set[int]] = field(init=False)

    def __post_init__(self) -> None:
        self.markups = {
            (x, y): set(possibilities(self.board, x, y))
            for y in range(SIDE)
            for x in range(SIDE)
            if self.board[y * SIDE + x] == 0
        }

    def update_markups(self, house: t.Iterable[Point]) -> None:
        p_sets: t.Dict[t.FrozenSet[int], t.Set[Point]] = {}

        for square in house:
            if square not in self.markups:
                continue

            markup = self.markups[square]
            mine = {square}

            for p_set, members in p_sets.items():
                if markup <= p_set:
                    members.add(square)
                elif markup >= p_set:
                    mine |= members

            p_sets.setdefault(frozenset(markup), mine)

        for p_set, members in p_sets.items():
            if len(p_set) != len(members):
                continue

            for square in house:
                if square not in self.markups:
                    continue
                markup = self.markups[square]
                if square not in members:
                    markup.difference_update(p_set)


def fill_in(board: Board) -> t.Dict[Point, int]:
    solver = SolverStep(board)
    results = {}

    for _ in range(STEPS):
        for house in houses():
            solver.update_markups(house)

    # ? Should we limit size to {2,3} as per the paper?
    for by in range(0, SIDE, 3):
        for bx in range(0, SIDE, 3):
            for y in range(SIDE):
                solver.update_markups(
                    chain(box_pos(bx, by), ((x, y) for x in range(SIDE)))
                )

            for x in range(SIDE):
                solver.update_markups(
                    chain(box_pos(bx, by), ((x, y) for y in range(SIDE)))
                )

    for house in houses():
        reverse_markups: t.Dict[int, t.Set[Point]] = {}

        for square in house:
            if square not in solver.markups:
                continue
            for num in solver.markups[square]:
                reverse_markups.setdefault(num, set()).add(square)

        results.update({v.pop(): k for k, v in reverse_markups.items() if len(v) == 1})

    results.update({k: v.pop() for k, v in solver.markups.items() if len(v) == 1})

    return results


def check_conflicts(board: Board) -> bool:
    for y in range(SIDE):
        for x in range(SIDE):
            i = y * SIDE + x
            board[i] = -board[i]
            if -board[i] in neighborhood(board, x, y):
                return False
            board[i] = -board[i]

    return True


def violation(board: Board) -> bool:
    for house in houses():
        encountered = set()

        for x, y in house:
            square = board[y * SIDE + x]
            if square == 0:
                continue
            if square in encountered:
                return True
            encountered.add(square)
    return False


def solve(board: Board) -> t.Tuple[Board, t.Dict[Point, int]]:
    changes: t.ChainMap[Point, int] = ChainMap({})
    stack: t.List[t.List[t.Tuple[Point, int]]] = []

    def next_branch() -> None:
        while True:
            # clear out previous changes
            for x, y in changes.maps[0]:
                board[y * SIDE + x] = 0
            t.cast(t.Dict[Point, int], changes.maps[0]).clear()

            # if we've run out of branches, go up one level
            if not stack[-1]:
                stack.pop()
                changes.maps.pop(0)
                continue

            (x, y), num = stack[-1].pop()
            board[y * SIDE + x] = changes[x, y] = num
            break

    while True:
        print("\x1b[0K", [len(item) for item in stack], sep="", end="\r")

        new = fill_in(board)

        if new:
            for (x, y), num in new.items():
                board[y * SIDE + x] = num
            changes.update(new)

            if violation(board):
                next_branch()

            continue

        if 0 not in board:
            return board, dict(changes)

        # if we've got no new squares, but also zeroes in the board, we've failed ot
        # reach a solution and must guess

        # construct all possible branches
        tos = []
        for point, numbers in sorted(
            SolverStep(board).markups.items(), key=lambda kv: len(kv[1])
        ):
            for num in numbers:
                tos.append((point, num))

        # add them to the stack and go to next branch
        stack.append(tos)
        changes.maps.insert(0, {})

        next_branch()


def load_board(s: str) -> Board:
    return list(map(int, s))


def print_board(board: Board, changes: t.Dict[Point, int]) -> None:
    for y in range(SIDE):
        for x in range(SIDE):
            col = board[y * SIDE + x]
            color = 30 + col
            if (x, y) in changes:
                print("\x1b[1;4m", end="")
            print(f"\x1b[{color}m{col}\x1b[0m", end=" ")
        print()


@click.command()
@click.argument("board", type=str)
def main(board: str) -> None:
    print_board(*solve(load_board(board)))


if __name__ == "__main__":
    main()
