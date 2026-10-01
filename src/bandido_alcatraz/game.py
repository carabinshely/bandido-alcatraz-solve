from __future__ import annotations

from dataclasses import dataclass, field
from random import Random

from .board import Board
from .model import CardDefinition, Material
from .moves import Action, Move, legal_moves
from .rules import GameStatus, is_victory
from .setup import GameSetup, StartSide


@dataclass(frozen=True, slots=True)
class CollectedEquipment:
    card: CardDefinition
    turn: int
    player_index: int = 0

    @property
    def card_id(self):
        return self.card.card_id

    @property
    def material(self):
        return self.card.material


@dataclass(frozen=True, slots=True)
class PlayerObservation:
    """Detached public state plus own hand. No draw pile or teammate hand API."""
    board: Board
    hand: tuple[CardDefinition, ...]
    raincoats: int
    ropes: int
    exit_placed: bool
    exit_seen: bool  # own-player knowledge only; current executor is solo
    turns: int
    set_aside_unplayable: int
    collected_equipment: tuple[CollectedEquipment, ...]
    setup: GameSetup
    player_index: int = 0

    @property
    def status(self):
        return GameStatus(self.raincoats, self.ropes, self.board.open_tunnels,
                          self.board.visible_water_cells, self.exit_placed)

    @property
    def won(self):
        return is_victory(self.status)

    def legal_moves(self):
        return legal_moves(self.board, self.hand)


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
    collected_equipment: tuple[CollectedEquipment, ...] = ()
    setup: GameSetup = GameSetup(hand_size=3)
    player_index: int = 0
    private_hands: list[list[CardDefinition]] = field(default_factory=list)
    face_down_set_aside: tuple[CardDefinition, ...] = ()

    def __setattr__(self, name: str, value: object) -> None:
        if name == "exit_seen" and value is False:
            try:
                already_seen = object.__getattribute__(self, "exit_seen")
            except AttributeError:
                already_seen = False
            if already_seen:
                raise ValueError("exit_seen is monotonic and cannot be reset")
        object.__setattr__(self, name, value)
        if name == 'hand':
            try:
                hands = object.__getattribute__(self, 'private_hands')
                index = object.__getattribute__(self, 'player_index')
            except AttributeError:
                return
            if hands:
                hands[index] = value

    def __post_init__(self) -> None:
        if not 0 <= self.player_index < self.setup.player_count:
            raise ValueError('player index outside setup')
        if not self.private_hands:
            if self.setup.player_count != 1:
                raise ValueError('multiplayer state requires separate private hands')
            self.private_hands = [self.hand]
        elif len(self.private_hands) != self.setup.player_count:
            raise ValueError('one private hand required per player')
        else:
            self.hand = self.private_hands[self.player_index]
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
        setup: GameSetup | None = None,
    ) -> "GameState":
        setup = setup or GameSetup(hand_size=hand_size)
        setup.require_supported_execution()
        if hand_size != setup.hand_size:
            raise ValueError('hand_size disagrees with setup')
        draw_pile = list(deck)
        rng.shuffle(draw_pile)
        hand: list[CardDefinition] = []
        for _ in range(min(hand_size, len(draw_pile))):
            hand.append(draw_pile.pop())

        board = Board()
        board.seed(start_card)
        # Preserve generic synthetic fixtures while binding photographed START
        # identity to the setup reported in research provenance.
        real_start_sides = {'start_easy': StartSide.EASY, 'start_normal': StartSide.NORMAL}
        if start_card.card_id in real_start_sides and real_start_sides[start_card.card_id] is not setup.start_side:
            raise ValueError('physical START card disagrees with setup')
        return cls(board=board, draw_pile=draw_pile, hand=hand, setup=setup)

    def observation(self, player_index: int | None = None) -> PlayerObservation:
        index = self.player_index if player_index is None else player_index
        if type(index) is not int or not 0 <= index < self.setup.player_count:
            raise ValueError('observation player outside setup')
        own_hand = self.private_hands[index]
        # Until multiplayer execution defines per-player knowledge history,
        # never project the solo global history flag into another player's view.
        own_exit_seen = (self.exit_seen if self.setup.player_count == 1 else
                         self.exit_placed or any(c.is_exit for c in own_hand))
        return PlayerObservation(self.board.clone(), tuple(own_hand), self.raincoats,
            self.ropes, self.exit_placed, own_exit_seen, self.turns,
            self.set_aside_unplayable, self.collected_equipment, self.setup, index)

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
        self.setup.require_supported_execution()
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
            self.collected_equipment += (CollectedEquipment(card, self.turns + 1, self.player_index),)
        else:
            assert move.origin is not None
            self.board.place(card, move.origin, move.quarter_turns)
            if card.is_exit:
                self.exit_placed = True
                self.exit_seen = True

        self.turns += 1
        self._draw_one()

    def refresh_unplayable_hand(self) -> bool:
        """Owner-selected whole-hand extension of the published refresh rule.

        Keep the historical deterministic short-pile list ordering. This is an
        engine convention, not a publisher claim. Refresh is not an action.
        """
        self.setup.require_supported_execution()
        if self.legal_moves():
            return False
        if not self.hand or not self.draw_pile:
            return False
        batch_size = len(self.hand)

        # With more than one replacement batch remaining, returning the same
        # three-card hand to the draw pile can otherwise rotate forever when
        # no remaining card is playable on the current board. Detect that
        # terminal state before cycling the hand.
        if len(self.draw_pile) > batch_size and not legal_moves(
            self.board, tuple(self.draw_pile)
        ):
            return False

        if len(self.draw_pile) <= batch_size:
            old_count = len(self.hand)
            self.face_down_set_aside += tuple(self.hand)
            self.hand = list(self.draw_pile)
            self.draw_pile.clear()
            self.set_aside_unplayable += old_count
            self._mark_visible_exit_seen()
            return True

        old_hand = list(self.hand)
        self.hand.clear()
        self.draw_pile = old_hand + self.draw_pile
        for _ in range(batch_size):
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
