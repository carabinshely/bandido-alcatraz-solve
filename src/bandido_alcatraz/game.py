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
    exit_seen: bool = False

    def __setattr__(self, name: str, value: object) -> None:
        if name == "exit_seen" and value is False:
            try:
                already_seen = object.__getattribute__(self, "exit_seen")
            except AttributeError:
                already_seen = False
            if already_seen:
                raise ValueError("exit_seen is monotonic and cannot be reset")
        object.__setattr__(self, name, value)

    def __post_init__(self) -> None:
        self._mark_visible_exit_seen()
        if self.exit_placed:
            self.exit_seen = True

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

    def apply(self, move: Move, *, validate: bool = True) -> None:
        if move.hand_index < 0 or move.hand_index >= len(self.hand):
            raise IndexError("hand_index out of range")

        if validate and move not in self.legal_moves():
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
                self.exit_seen = True

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

        # With more than one replacement batch remaining, returning the same
        # three-card hand to the draw pile can otherwise rotate forever when
        # no remaining card is playable on the current board. Detect that
        # terminal state before cycling the hand.
        if len(self.draw_pile) > 3 and not legal_moves(
            self.board, tuple(self.draw_pile)
        ):
            return False

        if len(self.draw_pile) <= 3:
            old_count = len(self.hand)
            self.hand = list(self.draw_pile)
            self.draw_pile.clear()
            self.set_aside_unplayable += old_count
            self._mark_visible_exit_seen()
            return True

        old_hand = list(self.hand)
        self.hand.clear()
        self.draw_pile = old_hand + self.draw_pile
        for _ in range(3):
            self.hand.append(self.draw_pile.pop())
        self._mark_visible_exit_seen()
        return True

    def _draw_one(self) -> None:
        if self.draw_pile:
            card = self.draw_pile.pop()
            self.hand.append(card)
            if card.is_exit:
                self.exit_seen = True

    def _mark_visible_exit_seen(self) -> None:
        if not self.exit_seen and any(card.is_exit for card in self.hand):
            self.exit_seen = True
