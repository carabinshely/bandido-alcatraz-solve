from dataclasses import replace

import pytest

from bandido_alcatraz.fixtures import synthetic_deck, synthetic_start
from bandido_alcatraz.optimize import search_weights, weight_grid
from bandido_alcatraz.strategy import PolicyWeights


def test_weight_grid_changes_only_requested_fields() -> None:
    base = PolicyWeights()
    candidates = weight_grid(
        base=base,
        values={
            "collect_needed": [100, 200],
            "delta_open_tunnels": [5, 10],
        },
    )

    assert len(candidates) == 4
    assert {item.collect_needed for item in candidates} == {100, 200}
    assert {item.delta_open_tunnels for item in candidates} == {5, 10}
    assert all(item.wins == base.wins for item in candidates)


def test_weight_grid_rejects_unknown_fields() -> None:
    with pytest.raises(ValueError, match="unknown weight fields"):
        weight_grid(values={"not_a_feature": [1]})


def test_search_rejects_seed_leakage() -> None:
    with pytest.raises(ValueError, match="must be disjoint"):
        search_weights(
            start_card=synthetic_start(),
            deck=synthetic_deck(),
            hand_size=3,
            candidates=[PolicyWeights()],
            training_seeds=range(0, 5),
            evaluation_seeds=range(4, 8),
        )


def test_search_runs_training_then_held_out_evaluation() -> None:
    base = PolicyWeights()
    candidates = [
        base,
        replace(base, collect_needed=-10_000),
    ]

    result = search_weights(
        start_card=synthetic_start(),
        deck=synthetic_deck(),
        hand_size=3,
        candidates=candidates,
        training_seeds=range(0, 8),
        evaluation_seeds=range(100, 108),
    )

    assert result.candidates_evaluated == 2
    assert result.training_summary.games == 8
    assert result.evaluation_summary.games == 8
    assert result.best_weights in candidates
