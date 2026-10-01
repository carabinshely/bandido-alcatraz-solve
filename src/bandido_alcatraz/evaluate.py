from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Mapping

from .model import CardDefinition
from .setup import GameSetup
from .policies import Policy
from .simulate import GameResult, play_game


@dataclass(frozen=True, slots=True)
class WilsonInterval:
    low: float
    high: float


@dataclass(frozen=True, slots=True)
class PolicyEvaluation:
    games: int
    wins: int
    win_rate: float
    interval_95: WilsonInterval


@dataclass(frozen=True, slots=True)
class PairedComparison:
    games: int
    a_only_wins: int
    b_only_wins: int
    both_win: int
    both_lose: int


@dataclass(frozen=True, slots=True)
class EvaluationSuite:
    policies: dict[str, PolicyEvaluation]
    paired: dict[str, PairedComparison]


def wilson_interval_95(wins: int, games: int) -> WilsonInterval:
    if games <= 0:
        raise ValueError("games must be positive")
    if wins < 0 or wins > games:
        raise ValueError("wins must be between 0 and games")

    z = 1.959963984540054
    p = wins / games
    denominator = 1 + (z * z) / games
    center = (p + (z * z) / (2 * games)) / denominator
    half = (
        z
        * sqrt((p * (1 - p) / games) + (z * z) / (4 * games * games))
        / denominator
    )
    low = 0.0 if wins == 0 else max(0.0, center - half)
    high = 1.0 if wins == games else min(1.0, center + half)
    return WilsonInterval(low=low, high=high)


def evaluate_policies(
    *,
    start_card: CardDefinition,
    deck: list[CardDefinition],
    hand_size: int,
    policies: Mapping[str, Policy],
    seeds: range,
    setup: GameSetup | None = None,
) -> EvaluationSuite:
    names = list(policies)
    if not names:
        raise ValueError("at least one policy is required")
    if not seeds:
        raise ValueError("seed set must be non-empty")

    results: dict[str, list[GameResult]] = {}
    for name, policy in policies.items():
        results[name] = [
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

    evaluations: dict[str, PolicyEvaluation] = {}
    for name in names:
        games = len(results[name])
        wins = sum(result.won for result in results[name])
        evaluations[name] = PolicyEvaluation(
            games=games,
            wins=wins,
            win_rate=wins / games,
            interval_95=wilson_interval_95(wins, games),
        )

    paired: dict[str, PairedComparison] = {}
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            a_results = results[a]
            b_results = results[b]
            a_only = b_only = both_win = both_lose = 0
            for a_result, b_result in zip(a_results, b_results, strict=True):
                if a_result.won and b_result.won:
                    both_win += 1
                elif a_result.won:
                    a_only += 1
                elif b_result.won:
                    b_only += 1
                else:
                    both_lose += 1

            paired[f"{a}__vs__{b}"] = PairedComparison(
                games=len(a_results),
                a_only_wins=a_only,
                b_only_wins=b_only,
                both_win=both_win,
                both_lose=both_lose,
            )

    return EvaluationSuite(policies=evaluations, paired=paired)
