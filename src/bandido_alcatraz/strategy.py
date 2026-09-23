from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .board import Board
from .game import GameState
from .model import CardDefinition, Material
from .moves import Action, Move, legal_moves
from .rules import is_equipment_ready


@dataclass(frozen=True, slots=True)
class MoveFeatures:
    collect_needed: int = 0
    collect_excess: int = 0
    collect_degree_one: int = 0
    wins: int = 0
    closes_last_without_win: int = 0
    delta_open_tunnels: int = 0
    delta_visible_water: int = 0
    delta_merge_opportunities: int = 0
    delta_water_obstruction: int = 0
    new_trapped_water: int = 0
    bounded_merge_setup_gain: int = 0
    places_exit_ready: int = 0
    places_exit_early: int = 0


@dataclass(frozen=True, slots=True)
class PolicyWeights:
    collect_needed: int = 10_000
    collect_excess: int = -500
    collect_degree_one: int = 0
    wins: int = 1_000_000
    closes_last_without_win: int = -1_000_000
    delta_open_tunnels: int = 100
    delta_visible_water: int = 5
    delta_merge_opportunities: int = 0
    delta_water_obstruction: int = 0
    new_trapped_water: int = 0
    bounded_merge_setup_gain: int = 0
    places_exit_ready: int = 5_000
    places_exit_early: int = -5_000


@dataclass(frozen=True, slots=True)
class RetainedVisibleCard:
    hand_index: int
    card: CardDefinition


@dataclass(frozen=True, slots=True)
class PlacementPreview:
    resulting_board: Board
    retained_visible_cards: tuple[RetainedVisibleCard, ...]


def standalone_exit_legal_move_count(
    board: Board,
    exit_card: CardDefinition,
) -> int:
    """Return canonical standalone EXIT placement capacity without mutation."""
    return len(legal_moves(board, (exit_card,)))


def preview_ordinary_non_exit_placement_without_draw(
    state: GameState,
    move: Move,
) -> PlacementPreview:
    """Preview one legal ordinary non-EXIT placement without drawing."""
    if move.action is not Action.PLACE:
        raise ValueError("preview requires an ordinary placement move")
    if move.hand_index < 0 or move.hand_index >= len(state.hand):
        raise IndexError("hand_index out of range")
    if len(state.hand) != 3:
        raise ValueError("visible-repair preview requires a 3-card hand")
    if move not in state.legal_moves():
        raise ValueError("preview requires a currently legal move")

    card = state.hand[move.hand_index]
    if card.is_exit:
        raise ValueError("preview requires a non-EXIT card")
    if move.origin is None:
        raise ValueError("placement move requires an origin")

    resulting_board = state.board.clone()
    resulting_board.place(card, move.origin, move.quarter_turns)
    retained = tuple(
        RetainedVisibleCard(hand_index=index, card=retained_card)
        for index, retained_card in enumerate(state.hand)
        if index != move.hand_index
    )
    return PlacementPreview(
        resulting_board=resulting_board,
        retained_visible_cards=retained,
    )


def has_visible_exit_repair_reserve(
    resulting_board: Board,
    retained_visible_cards: tuple[RetainedVisibleCard, ...],
    exit_card: CardDefinition,
) -> bool:
    """Return whether one retained visible card can restore EXIT capacity."""
    for retained in retained_visible_cards:
        card = retained.card
        if card.is_exit:
            continue

        for move in legal_moves(resulting_board, (card,)):
            if move.action is not Action.PLACE:
                continue
            assert move.origin is not None
            repair_board = resulting_board.clone()
            repair_board.place(card, move.origin, move.quarter_turns)
            if standalone_exit_legal_move_count(repair_board, exit_card) > 0:
                return True

    return False


def is_unsafe_capacity_kill_without_visible_repair_reserve(
    state: GameState,
    move: Move,
    exit_card: CardDefinition,
) -> bool:
    """Classify the exact Worker #10 no-draw capacity-kill property."""
    if move.action is not Action.PLACE:
        return False
    if move.hand_index < 0 or move.hand_index >= len(state.hand):
        raise IndexError("hand_index out of range")

    card = state.hand[move.hand_index]
    if card.is_exit:
        return False

    if standalone_exit_legal_move_count(state.board, exit_card) <= 0:
        return False

    preview = preview_ordinary_non_exit_placement_without_draw(state, move)
    if (
        standalone_exit_legal_move_count(
            preview.resulting_board,
            exit_card,
        )
        > 0
    ):
        return False

    return not has_visible_exit_repair_reserve(
        preview.resulting_board,
        preview.retained_visible_cards,
        exit_card,
    )


def move_features(state: GameState, move: Move) -> MoveFeatures:
    card = state.hand[move.hand_index]

    if move.action is Action.COLLECT:
        needed = (
            card.material is Material.RAINCOAT and state.raincoats < 3
        ) or (
            card.material is Material.ROPE and state.ropes < 2
        )
        return MoveFeatures(
            collect_needed=int(needed),
            collect_excess=int(not needed),
            collect_degree_one=int(needed and card.external_tunnel_count == 1),
        )

    clone = clone_state(state)
    before_open = state.board.open_tunnels
    before_water = state.board.visible_water_cells
    before_merge = state.board.merge_opportunities
    before_obstruction = state.board.water_obstruction
    before_trapped = state.board.trapped_water_cells
    before_bounded_merge = _bounded_merge_bank(state.board)
    clone.apply(move, validate=False)

    equipment_ready_before = is_equipment_ready(state.raincoats, state.ropes)
    return MoveFeatures(
        wins=int(clone.won),
        closes_last_without_win=int(
            clone.board.open_tunnels == 0 and not clone.won
        ),
        delta_open_tunnels=before_open - clone.board.open_tunnels,
        delta_visible_water=before_water - clone.board.visible_water_cells,
        delta_merge_opportunities=(
            clone.board.merge_opportunities - before_merge
        ),
        delta_water_obstruction=(
            before_obstruction - clone.board.water_obstruction
        ),
        new_trapped_water=max(
            0,
            clone.board.trapped_water_cells - before_trapped,
        ),
        bounded_merge_setup_gain=max(
            0,
            _bounded_merge_bank(clone.board) - before_bounded_merge,
        ),
        places_exit_ready=int(card.is_exit and equipment_ready_before),
        places_exit_early=int(card.is_exit and not equipment_ready_before),
    )


def score_features(features: MoveFeatures, weights: PolicyWeights) -> int:
    return sum(
        getattr(features, field) * getattr(weights, field)
        for field in MoveFeatures.__dataclass_fields__
    )


class WeightedGreedyPolicy:
    def __init__(self, weights: PolicyWeights | None = None) -> None:
        self.weights = weights or PolicyWeights()

    def choose(self, state: GameState, rng: Random) -> Move | None:
        moves = state.legal_moves()
        if not moves:
            return None

        scored = [
            (score_features(move_features(state, move), self.weights), move)
            for move in moves
        ]
        best = max(score for score, _ in scored)
        candidates = [move for score, move in scored if score == best]
        return rng.choice(candidates)


def clone_state(state: GameState) -> GameState:
    return GameState(
        board=state.board.clone(),
        draw_pile=list(state.draw_pile),
        hand=list(state.hand),
        raincoats=state.raincoats,
        ropes=state.ropes,
        exit_placed=state.exit_placed,
        exit_seen=state.exit_seen,
        turns=state.turns,
        set_aside_unplayable=state.set_aside_unplayable,
    )



def _bounded_merge_bank(board) -> int:
    """Compact merge potential seen in the winning seed-24 trace.

    Reward setup only while the board stays within a bounded open-end budget.
    The cap also prevents raw merge count from being increased without limit.
    """
    if board.open_tunnels > 10:
        return 0
    return min(board.merge_opportunities, 6)
