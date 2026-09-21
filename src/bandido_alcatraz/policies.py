from __future__ import annotations

from random import Random
from typing import Protocol

from .game import GameState
from .moves import Move


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
            clone = _clone_state(state)
            clone.apply(move)
            scored.append((clone.board.open_tunnels, move))

        best = min(score for score, _ in scored)
        candidates = [move for score, move in scored if score == best]
        return rng.choice(candidates)


def _clone_state(state: GameState) -> GameState:
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
