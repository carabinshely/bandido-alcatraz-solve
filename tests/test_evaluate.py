import pytest

from bandido_alcatraz.evaluate import (
    evaluate_policies,
    wilson_interval_95,
)
from bandido_alcatraz.fixtures import synthetic_deck, synthetic_start
from bandido_alcatraz.policies import GreedyV0Policy, RandomLegalPolicy


def test_wilson_interval_contains_observed_rate() -> None:
    interval = wilson_interval_95(50, 100)

    assert interval.low < 0.5 < interval.high
    assert 0.0 <= interval.low <= interval.high <= 1.0


def test_wilson_interval_handles_extremes() -> None:
    none = wilson_interval_95(0, 100)
    all_wins = wilson_interval_95(100, 100)

    assert none.low == 0.0
    assert none.high > 0.0
    assert all_wins.high == 1.0
    assert all_wins.low < 1.0


def test_wilson_rejects_invalid_counts() -> None:
    with pytest.raises(ValueError):
        wilson_interval_95(1, 0)
    with pytest.raises(ValueError):
        wilson_interval_95(11, 10)


def test_paired_evaluation_uses_same_seed_count() -> None:
    suite = evaluate_policies(
        start_card=synthetic_start(),
        deck=synthetic_deck(),
        hand_size=3,
        policies={
            "random": RandomLegalPolicy(),
            "greedy": GreedyV0Policy(),
        },
        seeds=range(20),
    )

    assert suite.policies["random"].games == 20
    assert suite.policies["greedy"].games == 20

    comparison = suite.paired["random__vs__greedy"]
    assert (
        comparison.a_only_wins
        + comparison.b_only_wins
        + comparison.both_win
        + comparison.both_lose
        == 20
    )
