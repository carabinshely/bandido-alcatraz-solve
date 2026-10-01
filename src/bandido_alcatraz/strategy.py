from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .board import Board
from .game import GameState, PlayerObservation
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


@dataclass(frozen=True, slots=True)
class NoDrawRetainedCard:
    original_hand_index: int
    preview_hand_index: int
    card: CardDefinition


@dataclass(frozen=True, slots=True)
class NoDrawMovePreview:
    successor: GameState
    retained_visible_cards: tuple[NoDrawRetainedCard, ...]


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


def preview_move_without_draw(
    state: GameState,
    move: Move,
) -> NoDrawMovePreview:
    """Apply one legal visible move to a sanitized state without hidden draw access."""
    if move.hand_index < 0 or move.hand_index >= len(state.hand):
        raise IndexError("hand_index out of range")
    if move not in state.legal_moves():
        raise ValueError("preview requires a currently legal move")

    retained = tuple(
        NoDrawRetainedCard(
            original_hand_index=original_index,
            preview_hand_index=preview_index,
            card=retained_card,
        )
        for preview_index, (original_index, retained_card) in enumerate(
            (item for item in enumerate(state.hand) if item[0] != move.hand_index)
        )
    )

    successor = GameState(
        board=state.board.clone(),
        draw_pile=[],
        hand=list(state.hand),
        raincoats=state.raincoats,
        ropes=state.ropes,
        exit_placed=state.exit_placed,
        exit_seen=state.exit_seen,
        turns=state.turns,
        set_aside_unplayable=state.set_aside_unplayable,
        collected_equipment=state.collected_equipment,
        setup=state.setup,
        player_index=state.player_index,
    )
    successor.apply(move, validate=False)

    if tuple(successor.hand) != tuple(item.card for item in retained):
        raise AssertionError("no-draw preview retained-card mapping mismatch")

    return NoDrawMovePreview(
        successor=successor,
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


def move_features_no_draw(state: GameState, move: Move) -> MoveFeatures:
    """Return exact current V4 move features without reading the hidden draw pile."""
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

    before_open = state.board.open_tunnels
    before_water = state.board.visible_water_cells
    before_merge = state.board.merge_opportunities
    before_obstruction = state.board.water_obstruction
    before_trapped = state.board.trapped_water_cells
    before_bounded_merge = _bounded_merge_bank(state.board)
    successor = preview_move_without_draw(state, move).successor

    equipment_ready_before = is_equipment_ready(state.raincoats, state.ropes)
    return MoveFeatures(
        wins=int(successor.won),
        closes_last_without_win=int(
            successor.board.open_tunnels == 0 and not successor.won
        ),
        delta_open_tunnels=before_open - successor.board.open_tunnels,
        delta_visible_water=before_water - successor.board.visible_water_cells,
        delta_merge_opportunities=(
            successor.board.merge_opportunities - before_merge
        ),
        delta_water_obstruction=(
            before_obstruction - successor.board.water_obstruction
        ),
        new_trapped_water=max(
            0,
            successor.board.trapped_water_cells - before_trapped,
        ),
        bounded_merge_setup_gain=max(
            0,
            _bounded_merge_bank(successor.board) - before_bounded_merge,
        ),
        places_exit_ready=int(card.is_exit and equipment_ready_before),
        places_exit_early=int(card.is_exit and not equipment_ready_before),
    )


def score_features(features: MoveFeatures, weights: PolicyWeights) -> int:
    return sum(
        getattr(features, field) * getattr(weights, field)
        for field in MoveFeatures.__dataclass_fields__
    )


def score_move_no_draw(
    state: GameState,
    move: Move,
    weights: PolicyWeights,
) -> int:
    """Score one move with unchanged V4 features/weights and no hidden draw access."""
    return score_features(move_features_no_draw(state, move), weights)


def two_action_sequence_score(
    state: GameState,
    first_move: Move,
    weights: PolicyWeights,
) -> int:
    """Score one current move plus the best retained-visible second action."""
    score1 = score_move_no_draw(state, first_move, weights)
    successor = preview_move_without_draw(state, first_move).successor

    if successor.won or successor.board.open_tunnels == 0:
        return score1

    second_moves = successor.legal_moves()
    if not second_moves:
        return score1

    return score1 + max(
        score_move_no_draw(successor, second_move, weights)
        for second_move in second_moves
    )


def best_two_action_first_moves(
    state: GameState,
    weights: PolicyWeights,
) -> list[Move]:
    """Return tied best current moves in existing legal-move order."""
    first_moves = state.legal_moves()
    if not first_moves:
        return []

    scored = [
        (two_action_sequence_score(state, move, weights), move)
        for move in first_moves
    ]
    best = max(score for score, _ in scored)
    return [move for score, move in scored if score == best]


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
        draw_pile=[] if isinstance(state, PlayerObservation) else list(state.draw_pile),
        hand=list(state.hand),
        raincoats=state.raincoats,
        ropes=state.ropes,
        exit_placed=state.exit_placed,
        exit_seen=state.exit_seen,
        turns=state.turns,
        set_aside_unplayable=state.set_aside_unplayable,
        face_down_set_aside=() if isinstance(state, PlayerObservation) else state.face_down_set_aside,
        collected_equipment=state.collected_equipment,
        setup=state.setup,
        player_index=state.player_index,
    )



def _bounded_merge_bank(board) -> int:
    """Compact merge potential seen in the winning seed-24 trace.

    Reward setup only while the board stays within a bounded open-end budget.
    The cap also prevents raw merge count from being increased without limit.
    """
    if board.open_tunnels > 10:
        return 0
    return min(board.merge_opportunities, 6)
