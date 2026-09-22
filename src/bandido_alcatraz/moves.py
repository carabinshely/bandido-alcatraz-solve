from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .board import Board, Coord
from .model import CardDefinition, Material


class Action(StrEnum):
    PLACE = "place"
    COLLECT = "collect"


@dataclass(frozen=True, slots=True)
class Move:
    action: Action
    hand_index: int
    origin: Coord | None = None
    quarter_turns: int = 0


def legal_moves(board: Board, hand: tuple[CardDefinition, ...]) -> list[Move]:
    moves: list[Move] = []

    for hand_index, card in enumerate(hand):
        if card.material is not None:
            moves.append(Move(Action.COLLECT, hand_index))

        seen: set[tuple[tuple[tuple[int, int, tuple[str, ...], bool], ...], Coord]] = set()
        for quarter_turns in range(4):
            rotated = card.rotated(quarter_turns)
            fingerprint = tuple(
                (
                    cell.x,
                    cell.y,
                    tuple(sorted(edge.value for edge in cell.tunnel_edges)),
                    cell.water,
                )
                for cell in rotated.cells
            )
            for origin in sorted(board.candidate_origins(rotated)):
                key = (fingerprint, origin)
                if key in seen:
                    continue
                seen.add(key)
                if board.can_place(card, origin, quarter_turns):
                    moves.append(
                        Move(
                            Action.PLACE,
                            hand_index,
                            origin=origin,
                            quarter_turns=quarter_turns,
                        )
                    )

    return moves
