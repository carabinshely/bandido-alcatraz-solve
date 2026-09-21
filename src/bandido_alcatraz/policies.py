from __future__ import annotations

from random import Random
from typing import Protocol

from .game import GameState
from .moves import Move
from .strategy import PolicyWeights, WeightedGreedyPolicy, clone_state


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
