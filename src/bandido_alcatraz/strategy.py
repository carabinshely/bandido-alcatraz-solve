from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .game import GameState
from .model import Material
from .moves import Action, Move
from .rules import is_equipment_ready


@dataclass(frozen=True, slots=True)
class MoveFeatures:
    collect_needed: int = 0
    collect_excess: int = 0
    wins: int = 0
    closes_last_without_win: int = 0
    delta_open_tunnels: int = 0
    delta_visible_water: int = 0
    places_exit_ready: int = 0
    places_exit_early: int = 0


@dataclass(frozen=True, slots=True)
class PolicyWeights:
    collect_needed: int = 10_000
    collect_excess: int = -500
    wins: int = 1_000_000
    closes_last_without_win: int = -1_000_000
    delta_open_tunnels: int = 100
    delta_visible_water: int = -5
    places_exit_ready: int = 5_000
    places_exit_early: int = -5_000


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
        )

    clone = clone_state(state)
    before_open = state.board.open_tunnels
    before_water = state.board.visible_water_cells
    clone.apply(move)

    equipment_ready_before = is_equipment_ready(state.raincoats, state.ropes)
    return MoveFeatures(
        wins=int(clone.won),
        closes_last_without_win=int(
            clone.board.open_tunnels == 0 and not clone.won
        ),
        delta_open_tunnels=before_open - clone.board.open_tunnels,
        delta_visible_water=before_water - clone.board.visible_water_cells,
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
        turns=state.turns,
        set_aside_unplayable=state.set_aside_unplayable,
    )
