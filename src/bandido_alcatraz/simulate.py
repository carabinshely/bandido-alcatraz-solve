from __future__ import annotations

from dataclasses import dataclass
from random import Random

from .game import GameState
from .model import CardDefinition
from .policies import Policy
from .setup import GameSetup
from .rules import RULESET_ID


@dataclass(frozen=True, slots=True)
class GameResult:
    won: bool
    turns: int
    open_tunnels: int
    visible_water_cells: int
    raincoats: int
    ropes: int
    exit_placed: bool
    reason: str
    ruleset_id: str
    setup_id: str


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
    max_steps: int = 1000,
    setup: GameSetup | None = None,
) -> GameResult:
    setup = setup or GameSetup(hand_size=hand_size)
    setup.require_supported_execution()
    if setup.hand_size != hand_size:
        raise ValueError('hand_size disagrees with setup')

    rng = Random(seed)
    state = GameState.new(
        start_card=start_card,
        deck=deck,
        hand_size=hand_size,
        rng=rng,
        setup=setup,
    )

    def finish(reason):
        hook = getattr(policy, 'on_game_finished', None)
        if hook is not None:
            hook(state.observation())
        return _result(state, reason)

    for _ in range(max_steps):
        if state.won:
            return finish("win")

        if state.board.open_tunnels == 0:
            return finish("closed_tunnels_conditions_failed")

        if not state.hand and not state.draw_pile:
            return finish("deck_exhausted")

        move = policy.choose(state.observation(), rng)
        if move is None:
            if state.refresh_unplayable_hand():
                continue
            reason = "deck_exhausted" if state.exhausted else "no_legal_move"
            return finish(reason)

        state.apply(move)

    return finish("step_limit")


def run_many(
    *,
    start_card: CardDefinition,
    deck: list[CardDefinition],
    hand_size: int,
    policy: Policy,
    seeds: range,
    setup: GameSetup | None = None,
) -> SimulationSummary:
    results = [
        play_game(
            start_card=start_card,
            deck=deck,
            hand_size=hand_size,
            policy=policy,
            seed=seed,
            setup=setup,
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
        exit_placed=state.exit_placed,
        reason=reason,
        ruleset_id=RULESET_ID,
        setup_id=state.setup.setup_id,
    )
