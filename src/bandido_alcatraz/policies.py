from __future__ import annotations

from random import Random
from typing import Protocol

from .game import GameState
from .model import CardDefinition
from .moves import Move
from .strategy import (
    PolicyWeights,
    WeightedGreedyPolicy,
    clone_state,
    is_unsafe_capacity_kill_without_visible_repair_reserve,
    move_features,
    score_features,
    standalone_exit_legal_move_count,
)


class Policy(Protocol):
    def choose(self, state: GameState, rng: Random) -> Move | None: ...


class RandomLegalPolicy:
    def choose(self, state: GameState, rng: Random) -> Move | None:
        moves = state.legal_moves()
        if not moves:
            return None
        return rng.choice(moves)


class MinOpenTunnelsPolicy:
    """One-step greedy baseline: choose the move leaving fewest open tunnels."""

    def choose(self, state: GameState, rng: Random) -> Move | None:
        moves = state.legal_moves()
        if not moves:
            return None

        scored: list[tuple[int, Move]] = []
        for move in moves:
            clone = clone_state(state)
            clone.apply(move, validate=False)
            scored.append((clone.board.open_tunnels, move))

        best = min(score for score, _ in scored)
        candidates = [move for score, move in scored if score == best]
        return rng.choice(candidates)


class GreedyV0Policy(WeightedGreedyPolicy):
    """Named baseline using the default stage-aware strategy weights."""



class GeometryAwareV1Policy(WeightedGreedyPolicy):
    """Preserve scarce one-port equipment cards for tunnel closure when possible."""

    def __init__(self) -> None:
        super().__init__(
            PolicyWeights(
                collect_degree_one=-12_000,
            )
        )



class DiscardExcessV2Policy(WeightedGreedyPolicy):
    """Use excess equipment collection to discard geometrically bad cards."""

    def __init__(self) -> None:
        super().__init__(
            PolicyWeights(
                collect_excess=0,
            )
        )


class WaterFirstV2Policy(WeightedGreedyPolicy):
    """Take an available exact water-cover move before ordinary local gains."""

    def __init__(self) -> None:
        super().__init__(
            PolicyWeights(
                delta_visible_water=20_000,
            )
        )


class CombinedV2Policy(WeightedGreedyPolicy):
    """Combine excess-equipment discard with strong water-cover priority."""

    def __init__(self) -> None:
        super().__init__(
            PolicyWeights(
                collect_excess=0,
                delta_visible_water=20_000,
            )
        )



class MergeAwareV3Policy(WeightedGreedyPolicy):
    """Combined V2 plus future same-cell merge opportunity preservation."""

    def __init__(self) -> None:
        super().__init__(
            PolicyWeights(
                collect_excess=0,
                delta_visible_water=20_000,
                delta_merge_opportunities=500,
            )
        )


class WaterSpaceV3Policy(WeightedGreedyPolicy):
    """Combined V2 plus protection against obstructing visible water."""

    def __init__(self) -> None:
        super().__init__(
            PolicyWeights(
                collect_excess=0,
                delta_visible_water=20_000,
                delta_water_obstruction=1_000,
                new_trapped_water=-100_000,
            )
        )


class CombinedV3Policy(WeightedGreedyPolicy):
    """Combine V2 with merge opportunity and water-space preservation."""

    def __init__(self) -> None:
        super().__init__(
            PolicyWeights(
                collect_excess=0,
                delta_visible_water=20_000,
                delta_merge_opportunities=500,
                delta_water_obstruction=1_000,
                new_trapped_water=-100_000,
            )
        )



class BoundedMergeV4Policy(WeightedGreedyPolicy):
    """V2 water-space policy plus bounded merge-bank setup reward."""

    def __init__(self, setup_weight: int = 500) -> None:
        super().__init__(
            PolicyWeights(
                collect_excess=0,
                delta_visible_water=20_000,
                delta_water_obstruction=1_000,
                new_trapped_water=-100_000,
                bounded_merge_setup_gain=setup_weight,
            )
        )


class VisibleRepairReserveV5Policy(BoundedMergeV4Policy):
    """V4-250 with a preregistered visible-repair-reserve safety tier."""

    def __init__(self, *, exit_card: CardDefinition) -> None:
        if not exit_card.is_exit:
            raise ValueError("exit_card must be the canonical EXIT card")
        super().__init__(setup_weight=250)
        self.exit_card = exit_card

    def choose(self, state: GameState, rng: Random) -> Move | None:
        moves = state.legal_moves()
        if not moves:
            return None

        if state.exit_placed or state.exit_seen:
            return super().choose(state, rng)

        if standalone_exit_legal_move_count(state.board, self.exit_card) <= 0:
            return super().choose(state, rng)

        normal_moves = [
            move
            for move in moves
            if not is_unsafe_capacity_kill_without_visible_repair_reserve(
                state,
                move,
                self.exit_card,
            )
        ]
        if not normal_moves:
            return super().choose(state, rng)

        scored = [
            (score_features(move_features(state, move), self.weights), move)
            for move in normal_moves
        ]
        best = max(score for score, _ in scored)
        candidates = [move for score, move in scored if score == best]
        return rng.choice(candidates)
