from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from collections.abc import Iterator

from .board import Board, Coord
from .model import CardDefinition
from .rules import can_collect


class Action(StrEnum):
    PLACE = "place"
    COLLECT = "collect"


@dataclass(frozen=True, slots=True)
class Move:
    action: Action
    hand_index: int
    origin: Coord | None = None
    quarter_turns: int = 0


def legal_moves(
    board: Board,
    hand: tuple[CardDefinition, ...],
    *,
    raincoats: int,
    ropes: int,
) -> list[Move]:
    """Canonical actions in hand order, with inventory required for COLLECT."""
    moves: list[Move] = []

    for hand_index, card in enumerate(hand):
        if can_collect(card.material, raincoats=raincoats, ropes=ropes):
            moves.append(Move(Action.COLLECT, hand_index))
        moves.extend(_placement_moves_for_card(board, card, hand_index))

    return moves


def placement_moves(board: Board, hand: tuple[CardDefinition, ...]) -> list[Move]:
    """Inventory-free geometry API: only PLACE, in canonical relative order."""
    return [
        move
        for hand_index, card in enumerate(hand)
        for move in _placement_moves_for_card(board, card, hand_index)
    ]


def _placement_moves_for_card(
    board: Board, card: CardDefinition, hand_index: int,
) -> Iterator[Move]:
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
                yield Move(
                    Action.PLACE,
                    hand_index,
                    origin=origin,
                    quarter_turns=quarter_turns,
                )
