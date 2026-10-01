from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from itertools import product
from typing import Iterable, Mapping

from .model import CardDefinition
from .setup import GameSetup
from .simulate import SimulationSummary, run_many
from .strategy import PolicyWeights, WeightedGreedyPolicy


@dataclass(frozen=True, slots=True)
class TrainingCandidate:
    weights: PolicyWeights
    summary: SimulationSummary


@dataclass(frozen=True, slots=True)
class WeightSearchResult:
    candidates_evaluated: int
    best_weights: PolicyWeights
    training_summary: SimulationSummary
    evaluation_summary: SimulationSummary


def weight_grid(
    *,
    base: PolicyWeights | None = None,
    values: Mapping[str, Iterable[int]],
) -> list[PolicyWeights]:
    base = base or PolicyWeights()
    known = set(PolicyWeights.__dataclass_fields__)
    unknown = set(values) - known
    if unknown:
        raise ValueError(f"unknown weight fields: {sorted(unknown)}")
    if not values:
        return [base]

    fields = list(values)
    options = [tuple(values[field]) for field in fields]
    if any(not option for option in options):
        raise ValueError("every weight-grid field must have at least one value")

    candidates: list[PolicyWeights] = []
    seen: set[tuple[tuple[str, int], ...]] = set()
    for combination in product(*options):
        updates = dict(zip(fields, combination, strict=True))
        candidate = replace(base, **updates)
        fingerprint = tuple(sorted(asdict(candidate).items()))
        if fingerprint not in seen:
            seen.add(fingerprint)
            candidates.append(candidate)
    return candidates


def search_weights(
    *,
    start_card: CardDefinition,
    deck: list[CardDefinition],
    hand_size: int,
    candidates: Iterable[PolicyWeights],
    training_seeds: range,
    evaluation_seeds: range,
    setup: GameSetup | None = None,
) -> WeightSearchResult:
    candidate_list = list(candidates)
    if not candidate_list:
        raise ValueError("at least one weight candidate is required")
    if not training_seeds or not evaluation_seeds:
        raise ValueError("training and evaluation seed sets must be non-empty")
    if set(training_seeds).intersection(evaluation_seeds):
        raise ValueError("training and evaluation seeds must be disjoint")

    trained: list[TrainingCandidate] = []
    for weights in candidate_list:
        summary = run_many(
            start_card=start_card,
            deck=deck,
            hand_size=hand_size,
            policy=WeightedGreedyPolicy(weights),
            seeds=training_seeds,
            setup=setup,
        )
        trained.append(TrainingCandidate(weights=weights, summary=summary))

    # Optimize only the requested objective: number of wins on identical seeds.
    # Ties are stable and keep the first candidate rather than introducing a
    # hidden secondary objective.
    best = max(trained, key=lambda item: item.summary.wins)

    evaluation = run_many(
        start_card=start_card,
        deck=deck,
        hand_size=hand_size,
        policy=WeightedGreedyPolicy(best.weights),
        seeds=evaluation_seeds,
        setup=setup,
    )
    return WeightSearchResult(
        candidates_evaluated=len(trained),
        best_weights=best.weights,
        training_summary=best.summary,
        evaluation_summary=evaluation,
    )
