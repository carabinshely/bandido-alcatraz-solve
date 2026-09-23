from bandido_alcatraz.fixtures import synthetic_deck, synthetic_start
from bandido_alcatraz.policies import MinOpenTunnelsPolicy, RandomLegalPolicy
from bandido_alcatraz.simulate import run_many


def test_random_simulation_is_reproducible_for_same_seed_set() -> None:
    kwargs = dict(
        start_card=synthetic_start(),
        deck=synthetic_deck(),
        hand_size=3,
        policy=RandomLegalPolicy(),
        seeds=range(20),
    )

    assert run_many(**kwargs) == run_many(**kwargs)


def test_min_open_tunnels_policy_runs_end_to_end() -> None:
    summary = run_many(
        start_card=synthetic_start(),
        deck=synthetic_deck(),
        hand_size=3,
        policy=MinOpenTunnelsPolicy(),
        seeds=range(10),
    )

    assert summary.games == 10
    assert 0.0 <= summary.win_rate <= 1.0
    assert summary.wins + sum(summary.failure_reasons.values()) == summary.games
