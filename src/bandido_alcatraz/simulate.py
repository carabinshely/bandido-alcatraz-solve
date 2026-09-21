from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .game import GameState
from .model import CardDefinition
from .policies import Policy


@dataclass(frozen=True, slots=True)
class GameResult:
    won: bool
    turns: int
    open_tunnels: int
    visible_water_cells: int
    raincoats: int
    ropes: int
    reason: str


@dataclass(frozen=True, slots=True)
class SimulationSummary:
    games: int
    wins: int
    win_rate: float
    mean_turns: float
    failure_reasons: dict[str, int]


def play_game(
    *,
    start_card: CardDefinition,
    deck: list[CardDefinition],
    hand_size: int,
    policy: Policy,
    seed: int,
    max_turns: int = 500,
) -> GameResult:
    if hand_size != 3:
        raise NotImplementedError(
            "v0 simulation supports 3-card hands until solo-easy refresh semantics are verified"
        )

    rng = Random(seed)
    state = GameState.new(
        start_card=start_card,
        deck=deck,
        hand_size=hand_size,
        rng=rng,
    )

    while state.turns < max_turns:
        if state.won:
            return _result(state, "win")

        if state.board.open_tunnels == 0:
            return _result(state, "closed_tunnels_conditions_failed")

        if not state.hand and not state.draw_pile:
            return _result(state, "deck_exhausted")

        move = policy.choose(state, rng)
        if move is None:
            if state.refresh_unplayable_hand():
                continue
            reason = "deck_exhausted" if state.exhausted else "no_legal_move"
            return _result(state, reason)

        state.apply(move)

    return _result(state, "turn_limit")


def run_many(
    *,
    start_card: CardDefinition,
    deck: list[CardDefinition],
    hand_size: int,
    policy: Policy,
    seeds: range,
) -> SimulationSummary:
    results = [
        play_game(
            start_card=start_card,
            deck=deck,
            hand_size=hand_size,
            policy=policy,
            seed=seed,
        )
        for seed in seeds
    ]
    wins = sum(result.won for result in results)
    failures: dict[str, int] = {}
    for result in results:
        if result.won:
            continue
        failures[result.reason] = failures.get(result.reason, 0) + 1

    return SimulationSummary(
        games=len(results),
        wins=wins,
        win_rate=(wins / len(results)) if results else 0.0,
        mean_turns=(sum(result.turns for result in results) / len(results)) if results else 0.0,
        failure_reasons=failures,
    )


def _result(state: GameState, reason: str) -> GameResult:
    return GameResult(
        won=state.won,
        turns=state.turns,
        open_tunnels=state.board.open_tunnels,
        visible_water_cells=state.board.visible_water_cells,
        raincoats=state.raincoats,
        ropes=state.ropes,
        reason=reason,
    )
