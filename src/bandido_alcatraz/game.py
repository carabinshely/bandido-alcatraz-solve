from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from .board import Board
from .model import CardDefinition, Material
from .moves import Action, Move, legal_moves
from .rules import GameStatus, is_victory


@dataclass(slots=True)
class GameState:
    board: Board
    draw_pile: list[CardDefinition]
    hand: list[CardDefinition]
    raincoats: int = 0
    ropes: int = 0
    exit_placed: bool = False
    turns: int = 0
    discarded_unplayable: int = 0

    @classmethod
    def new(
        cls,
        *,
        start_card: CardDefinition,
        deck: list[CardDefinition],
        hand_size: int,
        rng: Random,
    ) -> "GameState":
        if hand_size <= 0:
            raise ValueError("hand_size must be positive")
        draw_pile = list(deck)
        rng.shuffle(draw_pile)
        hand: list[CardDefinition] = []
        for _ in range(min(hand_size, len(draw_pile))):
            hand.append(draw_pile.pop())

        board = Board()
        board.seed(start_card)
        return cls(board=board, draw_pile=draw_pile, hand=hand)

    @property
    def status(self) -> GameStatus:
        return GameStatus(
            raincoats=self.raincoats,
            ropes=self.ropes,
            open_tunnels=self.board.open_tunnels,
            visible_water_cells=self.board.visible_water_cells,
            exit_placed=self.exit_placed,
        )

    @property
    def won(self) -> bool:
        return is_victory(self.status)

    @property
    def exhausted(self) -> bool:
        return not self.hand and not self.draw_pile and not self.won

    def legal_moves(self) -> list[Move]:
        return legal_moves(self.board, tuple(self.hand))

    def apply(self, move: Move) -> None:
        if move.hand_index < 0 or move.hand_index >= len(self.hand):
            raise IndexError("hand_index out of range")

        legal = self.legal_moves()
        if move not in legal:
            raise ValueError("illegal move")

        card = self.hand.pop(move.hand_index)
        if move.action is Action.COLLECT:
            if card.material is Material.RAINCOAT:
                self.raincoats += 1
            elif card.material is Material.ROPE:
                self.ropes += 1
            else:
                raise ValueError("collect move requires material card")
        else:
            assert move.origin is not None
            self.board.place(card, move.origin, move.quarter_turns)

        self.turns += 1
        self._draw_one()

    def recycle_unplayable_hand(self) -> bool:
        """Project-v0 fallback for a hand with no legal moves.

        Return the current hand to the bottom of the draw pile, preserving
        deterministic ordering, then draw the same number of cards.
        """
        if self.legal_moves():
            return False
        if not self.hand or not self.draw_pile:
            return False

        count = len(self.hand)
        self.draw_pile = list(self.hand) + self.draw_pile
        self.hand.clear()
        self.discarded_unplayable += count
        for _ in range(min(count, len(self.draw_pile))):
            self.hand.append(self.draw_pile.pop())
        return True

    def _draw_one(self) -> None:
        if self.draw_pile:
            self.hand.append(self.draw_pile.pop())
