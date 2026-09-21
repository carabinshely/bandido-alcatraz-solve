from __future__ import annotations

from dataclasses import dataclass
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
    set_aside_unplayable: int = 0

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

        if move not in self.legal_moves():
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
            if card.is_exit:
                self.exit_placed = True

        self.turns += 1
        self._draw_one()

    def refresh_unplayable_hand(self) -> bool:
        """Implement the documented 3-card no-play refresh.

        The published rule explicitly describes returning/drawing three cards.
        Six-card solo refresh semantics remain deliberately unmodeled.
        """
        if self.legal_moves():
            return False
        if not self.hand or not self.draw_pile:
            return False
        if len(self.hand) != 3:
            raise NotImplementedError(
                "no-play refresh for a hand other than 3 cards is not modeled yet"
            )

        if len(self.draw_pile) <= 3:
            old_count = len(self.hand)
            self.hand = list(self.draw_pile)
            self.draw_pile.clear()
            self.set_aside_unplayable += old_count
            return True

        old_hand = list(self.hand)
        self.hand.clear()
        self.draw_pile = old_hand + self.draw_pile
        for _ in range(3):
            self.hand.append(self.draw_pile.pop())
        return True

    def _draw_one(self) -> None:
        if self.draw_pile:
            self.hand.append(self.draw_pile.pop())
