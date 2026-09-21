from __future__ import annotations

from random import Random
from typing import Protocol

from .game import GameState
from .model import Material
from .moves import Action, Move
from .rules import is_equipment_ready


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


class GreedyV0Policy:
    """Minimal stage-aware baseline.

    Priorities:
    1. Take still-needed equipment when available.
    2. Never close the final tunnel unless that move actually wins.
    3. Once equipment is ready, strongly prefer a winning EXIT placement.
    4. Otherwise reduce open tunnels without sealing the board.
    """

    def choose(self, state: GameState, rng: Random) -> Move | None:
        moves = state.legal_moves()
        if not moves:
            return None

        scored: list[tuple[int, Move]] = []
        before_open = state.board.open_tunnels
        equipment_ready_before = is_equipment_ready(state.raincoats, state.ropes)

        for move in moves:
            card = state.hand[move.hand_index]
            score = 0

            if move.action is Action.COLLECT:
                if (
                    card.material is Material.RAINCOAT
                    and state.raincoats < 3
                ) or (
                    card.material is Material.ROPE
                    and state.ropes < 2
                ):
                    score += 10_000
                else:
                    score -= 500
            else:
                clone = _clone_state(state)
                clone.apply(move)

                if clone.won:
                    score += 1_000_000
                elif clone.board.open_tunnels == 0:
                    score -= 1_000_000
                else:
                    score += 100 * (before_open - clone.board.open_tunnels)
                    score -= 5 * clone.board.visible_water_cells

                if card.is_exit:
                    score += 5_000 if equipment_ready_before else -5_000

            scored.append((score, move))

        best = max(score for score, _ in scored)
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
