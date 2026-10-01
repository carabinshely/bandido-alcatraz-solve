"""Worker31 pre-outcome fixtures: synthetic cards only, never research games."""

from copy import deepcopy
from dataclasses import fields, replace
from hashlib import sha256
import json
import os
from pathlib import Path
from random import Random
import subprocess
import sys

import pytest

from bandido_alcatraz.board import Board
import bandido_alcatraz.equipment_opportunity as candidate
from bandido_alcatraz.equipment_opportunity import (
    EquipmentOpportunityTiePolicy,
    canonical_digest,
    move_record,
    public_observation_record,
    rng_state_digest,
)
from bandido_alcatraz.game import CollectedEquipment, GameState, PlayerObservation
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.setup import GameSetup
import bandido_alcatraz.strategy as strategy


def card(card_id, edges=(Direction.WEST, Direction.EAST), *, material=None, is_exit=False):
    return CardDefinition(card_id, (CellSpec(0, 0, frozenset(edges)),), material, is_exit)


def state_with(hand, *, raincoats=0, ropes=0, exits=(Direction.EAST,), draw=()):
    board = Board()
    board.seed(card("synthetic-start", exits))
    return GameState(board, list(draw), list(hand), raincoats=raincoats, ropes=ropes,
                     setup=GameSetup(hand_size=6))


class ChoiceRecorder(Random):
    def __init__(self, seed):
        super().__init__(seed)
        self.choices = []

    def choice(self, seq):
        self.choices.append(tuple(seq))
        return super().choice(seq)


def expected_primary(observation):
    weights = BoundedMergeV4Policy(setup_weight=250).weights
    scored = [(strategy.score_features(strategy.move_features(observation, move), weights), move)
              for move in observation.legal_moves()]
    score = max((score for score, _ in scored), default=None)
    return score, [move for value, move in scored if value == score], scored


def assert_baseline_equivalence(observation, seed):
    baseline_rng, candidate_rng = ChoiceRecorder(seed), ChoiceRecorder(seed)
    baseline = BoundedMergeV4Policy(setup_weight=250)
    policy = EquipmentOpportunityTiePolicy()
    before = candidate_rng.getstate()
    expected = baseline.choose(observation, baseline_rng)
    assert policy.choose(observation, candidate_rng) == expected
    assert baseline_rng.choices == candidate_rng.choices
    assert baseline_rng.getstate() == candidate_rng.getstate()
    assert len(candidate_rng.choices) == (0 if expected is None else 1)
    assert policy.last_audit["rng_before_sha256"] == canonical_digest(before)
    assert policy.last_audit["rng_after_sha256"] == rng_state_digest(candidate_rng)
    return policy


def inject_scores(monkeypatch, observation, scores):
    """Exercise tier algebra with controlled synthetic scores, no real deck."""
    moves = observation.legal_moves()
    assert len(moves) == len(scores)
    by_move = dict(zip(moves, scores))
    assert len(by_move) == len(moves)
    feature_calls, score_calls = [], []

    def features(state, move):
        assert state is observation
        feature_calls.append(move)
        return move

    def score(move, weights):
        assert weights == BoundedMergeV4Policy(setup_weight=250).weights
        score_calls.append(move)
        return by_move[move]

    # Patch both routes so the equivalence oracle remains the actual unchanged
    # WeightedGreedyPolicy selection routine, using the same synthetic scores.
    for module in (candidate, strategy):
        monkeypatch.setattr(module, "move_features", features)
        monkeypatch.setattr(module, "score_features", score)
    return moves, feature_calls, score_calls


def test_exact_read_only_v4_250_weights_and_strict_observation_api():
    policy = EquipmentOpportunityTiePolicy()
    assert policy.weights == BoundedMergeV4Policy(setup_weight=250).weights
    with pytest.raises(AttributeError):
        policy.weights = replace(policy.weights, collect_needed=0)
    state = state_with([card("rope", material=Material.ROPE)])
    for invalid in (state, None, object()):
        rng = ChoiceRecorder(101)
        before = rng.getstate()
        with pytest.raises(TypeError, match="detached PlayerObservation"):
            policy.choose(invalid, rng)
        assert rng.getstate() == before and not rng.choices
        assert policy.last_audit is None


@pytest.mark.parametrize("raincoats", range(4))
@pytest.mark.parametrize("ropes", range(3))
def test_both_materials_and_quota_boundaries_preserve_legal_choices(raincoats, ropes):
    observation = state_with([
        card("coat", material=Material.RAINCOAT),
        card("rope", material=Material.ROPE),
        card("ordinary"),
    ], raincoats=raincoats, ropes=ropes).observation()
    policy = assert_baseline_equivalence(observation, 103)
    legal = observation.legal_moves()
    assert (Move(Action.COLLECT, 0) in legal) == (raincoats < 3)
    assert (Move(Action.COLLECT, 1) in legal) == (ropes < 2)
    assert all(any(m.action is Action.PLACE and m.hand_index == i for m in legal) for i in range(3))
    assert policy.last_audit["legal_move_count"] == len(legal)


@pytest.mark.parametrize("material", list(Material))
@pytest.mark.parametrize("seed", [0, 1, 11, 97])
def test_unequal_collection_opportunity_uses_unchanged_real_feature_scores(material, seed):
    observation = state_with([
        card("valuable-straight", material=material),
        card("losing-closure", (Direction.WEST,), material=material),
    ]).observation()
    primary_score, primary, scored = expected_primary(observation)
    assert primary == [Move(Action.COLLECT, 0), Move(Action.COLLECT, 1)]
    assert primary_score == 10_000
    opportunities = {
        i: max(value for value, move in scored if move.action is Action.PLACE and move.hand_index == i)
        for i in (0, 1)
    }
    assert opportunities == {0: 0, 1: -999_900}
    rng = ChoiceRecorder(seed)
    expected_rng = Random(seed)
    expected = expected_rng.choice([primary[1]])
    policy = EquipmentOpportunityTiePolicy()
    assert policy.choose(observation, rng) == expected
    assert rng.choices == [(primary[1],)]
    assert rng.getstate() == expected_rng.getstate()
    assert policy.last_audit["strict_narrowing"]
    assert policy.last_audit["collection_opportunities"] == [
        {"hand_index": i, "card_id": observation.hand[i].card_id, "opportunity_score": opportunities[i]}
        for i in (0, 1)
    ]


@pytest.mark.parametrize("seed", [0, 1, 2, 17, 43])
def test_equal_opportunities_preserve_canonical_order_and_baseline_rng(seed):
    observation = state_with([
        card("z-first", material=Material.ROPE),
        card("a-second", material=Material.RAINCOAT),
        card("middle-third", material=Material.ROPE),
    ]).observation()
    policy = assert_baseline_equivalence(observation, seed)
    assert policy.last_audit["eligible_collect_tier"]
    assert not policy.last_audit["strict_narrowing"]
    assert [item["hand_index"] for item in policy.last_audit["narrowed_tier"]] == [0, 1, 2]


@pytest.mark.parametrize("material", list(Material))
def test_empty_placement_maximum_is_lower_than_negative_scores_and_keeps_tied_order(material):
    observation = state_with([
        card("negative-place", (Direction.WEST,), material=material),
        card("z-no-place", (), material=material),
        card("a-no-place", (), material=material),
    ]).observation()
    rng = ChoiceRecorder(109)
    policy = EquipmentOpportunityTiePolicy()
    policy.choose(observation, rng)
    assert rng.choices == [(Move(Action.COLLECT, 1), Move(Action.COLLECT, 2))]
    assert [entry["opportunity_score"] for entry in policy.last_audit["collection_opportunities"]] == [-999_900, None, None]
    assert policy.last_audit["opportunity_null_is_lowest"] is True
    assert json.loads(json.dumps(policy.last_audit))["collection_opportunities"][1]["opportunity_score"] is None


def test_empty_maximum_is_not_a_finite_numeric_sentinel(monkeypatch):
    observation = state_with([
        card("any-negative", material=Material.ROPE),
        card("unplaceable", (), material=Material.ROPE),
    ]).observation()
    inject_scores(monkeypatch, observation, [10_000, -(10 ** 100), 10_000])
    policy, rng = EquipmentOpportunityTiePolicy(), ChoiceRecorder(113)
    assert policy.choose(observation, rng) == Move(Action.COLLECT, 1)
    assert policy.last_audit["collection_opportunities"][0]["opportunity_score"] == -(10 ** 100)


def test_use_maximum_of_all_same_card_placements_then_lowest_card_maximum(monkeypatch):
    observation = state_with([
        card("two-placements-a", material=Material.ROPE),
        card("two-placements-b", material=Material.RAINCOAT),
    ], exits=(Direction.EAST, Direction.NORTH)).observation()
    moves, features, scores = inject_scores(monkeypatch, observation, [1000, -50, 100, 1000, -10, -5])
    policy, rng = EquipmentOpportunityTiePolicy(), ChoiceRecorder(127)
    assert policy.choose(observation, rng) == Move(Action.COLLECT, 1)
    assert [entry["opportunity_score"] for entry in policy.last_audit["collection_opportunities"]] == [100, -5]
    assert features == scores == moves


def test_opportunity_grouping_uses_hand_index_not_card_identity(monkeypatch):
    repeated = card("same-definition", material=Material.ROPE)
    observation = state_with([repeated, repeated]).observation()
    inject_scores(monkeypatch, observation, [10_000, -20, 10_000, -10])
    policy = EquipmentOpportunityTiePolicy()
    assert policy.choose(observation, Random(131)) == Move(Action.COLLECT, 0)
    assert [entry["opportunity_score"] for entry in policy.last_audit["collection_opportunities"]] == [-20, -10]


@pytest.mark.parametrize("score_values", [
    [10_000, 10_000, 10_000, 0],  # Mixed COLLECT/PLACE tier must not narrow.
    [10_000, 20_000, 10_000, 20_000],  # PLACE-only tie.
    [10_000, 20_000, 10_000, 0],  # Singleton PLACE.
    [10_000, -5, 0, -1],  # Singleton COLLECT.
])
@pytest.mark.parametrize("seed", [0, 1, 2, 3, 139])
def test_noneligible_mixed_place_only_singleton_match_baseline_exactly(monkeypatch, score_values, seed):
    observation = state_with([
        card("a", material=Material.ROPE), card("b", material=Material.ROPE),
    ]).observation()
    inject_scores(monkeypatch, observation, score_values)
    policy = assert_baseline_equivalence(observation, seed)
    assert not policy.last_audit["strict_narrowing"]
    if any(move["action"] == "place" for move in policy.last_audit["primary_tier"]):
        assert not policy.last_audit["eligible_collect_tier"]
        assert policy.last_audit["collection_opportunities"] == []


@pytest.mark.parametrize("hand", [
    [card("single-coat", material=Material.RAINCOAT)],
    [card("single-place")],
    [card("place-a"), card("place-b")],
    [card("winning-exit", (Direction.WEST,), is_exit=True)],
    [],
    [card("blocked", ())],
])
def test_unpatched_features_match_baseline_outside_collection_ties(hand):
    observation = state_with(hand, raincoats=3, ropes=2).observation()
    assert_baseline_equivalence(observation, 149)


def test_single_collect_still_calls_rng_choice_once():
    observation = state_with([card("only-collect", (), material=Material.ROPE)]).observation()
    policy = assert_baseline_equivalence(observation, 151)
    assert policy.last_audit["narrowed_tier_count"] == 1
    assert policy.last_audit["primary_score"] == 10_000


def test_no_moves_scores_nothing_and_consumes_no_rng(monkeypatch):
    observation = state_with([card("excess-blocked", (), material=Material.ROPE)], ropes=2).observation()

    def forbidden(*args, **kwargs):
        raise AssertionError("no legal moves must not invoke scoring or choice")

    rng = Random(157)
    monkeypatch.setattr(rng, "choice", forbidden)
    monkeypatch.setattr(candidate, "move_features", forbidden)
    monkeypatch.setattr(candidate, "score_features", forbidden)
    before = rng.getstate()
    policy = EquipmentOpportunityTiePolicy()
    assert policy.choose(observation, rng) is None
    audit = policy.last_audit
    assert rng.getstate() == before
    assert audit["primary_score"] is None
    assert audit["primary_tier"] == audit["narrowed_tier"] == []
    assert audit["narrowed_tier_count"] == 0
    assert not audit["eligible_collect_tier"] and not audit["strict_narrowing"]
    assert audit["chosen_move"] is None
    assert audit["rng_before_sha256"] == audit["rng_after_sha256"]


def test_one_legal_enumeration_one_feature_score_and_preview_per_place(monkeypatch):
    observation = state_with([
        card("straight", material=Material.ROPE),
        card("closure", (Direction.WEST,), material=Material.ROPE),
        card("no-place", (), material=Material.RAINCOAT),
    ]).observation()
    legal = observation.legal_moves()
    counts = {"legal": 0, "clone": 0}
    feature_calls, score_calls = [], []
    original_legal = PlayerObservation.legal_moves
    original_features = candidate.move_features
    original_score = candidate.score_features
    original_clone = strategy.clone_state

    def enumerate_once(state):
        assert state is observation
        counts["legal"] += 1
        assert counts["legal"] == 1
        return original_legal(state)

    def features(state, move):
        assert state is observation
        feature_calls.append(move)
        return original_features(state, move)

    def score(features, weights):
        score_calls.append(features)
        return original_score(features, weights)

    def clone(state):
        assert state is observation
        counts["clone"] += 1
        return original_clone(state)

    monkeypatch.setattr(PlayerObservation, "legal_moves", enumerate_once)
    monkeypatch.setattr(candidate, "move_features", features)
    monkeypatch.setattr(candidate, "score_features", score)
    monkeypatch.setattr(strategy, "clone_state", clone)
    policy = EquipmentOpportunityTiePolicy()
    assert policy.choose(observation, Random(163)) == Move(Action.COLLECT, 2)
    # Reading/serializing diagnostics is passive, too.
    json.dumps(policy.last_audit)
    public_observation_record(observation)
    assert counts == {"legal": 1, "clone": sum(m.action is Action.PLACE for m in legal)}
    assert feature_calls == legal and len(score_calls) == len(legal)


def test_hidden_state_independence_observation_and_input_immutability():
    hand = [card("visible-straight", material=Material.ROPE),
            card("visible-closure", (Direction.WEST,), material=Material.ROPE)]
    a = state_with(hand, draw=[card("SECRET_DRAW_A", is_exit=True)])
    b = state_with(hand, draw=[card("SECRET_DRAW_B"), card("SECRET_DRAW_C")])
    a.face_down_set_aside = (card("SECRET_SET_ASIDE_A"),)
    b.face_down_set_aside = (card("SECRET_SET_ASIDE_B"),)
    a.set_aside_unplayable = b.set_aside_unplayable = 1
    a.collected_equipment = b.collected_equipment = (
        CollectedEquipment(card("public-collected", material=Material.RAINCOAT), 2),
    )
    a.turns = b.turns = 4
    a.raincoats = b.raincoats = 1
    observations = [a.observation(), b.observation()]
    before = [public_observation_record(obs) for obs in observations]
    assert before[0] == before[1]
    engine_before = [(state.board.cells, state.board.placements, tuple(state.hand),
                      tuple(state.draw_pile), state.face_down_set_aside) for state in (a, b)]
    policies = [EquipmentOpportunityTiePolicy(), EquipmentOpportunityTiePolicy()]
    choices = [policy.choose(obs, Random(167)) for policy, obs in zip(policies, observations)]
    assert choices[0] == choices[1]
    assert policies[0].last_audit == policies[1].last_audit
    assert [public_observation_record(obs) for obs in observations] == before
    assert [(state.board.cells, state.board.placements, tuple(state.hand),
             tuple(state.draw_pile), state.face_down_set_aside) for state in (a, b)] == engine_before
    assert observations[0].board is not a.board
    combined = json.dumps([before, policies[0].last_audit])
    assert "SECRET_" not in combined
    for name in ("draw_pile", "private_hands", "face_down_set_aside"):
        assert name not in combined and not hasattr(observations[0], name)


def test_public_serialization_covers_every_observation_field_and_hash_is_canonical():
    observation = state_with([card("own-hand", material=Material.ROPE)]).observation()
    record = public_observation_record(observation)
    assert set(record) == {field.name for field in fields(PlayerObservation)}
    encoded = (json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    assert canonical_digest(record) == sha256(encoded).hexdigest()
    assert record["hand"][0]["cells"][0]["tunnel_edges"] == ["E", "W"]
    record["hand"][0]["card_id"] = "changed-copy"
    record["board"]["cells"].clear()
    assert observation.hand[0].card_id == "own-hand"
    assert observation.board.cells


def test_trace_reproducibility_digest_consistency_and_passive_state():
    observation = state_with([
        card("placeable", material=Material.ROPE),
        card("blocked-a", (), material=Material.ROPE),
        card("blocked-b", (), material=Material.RAINCOAT),
    ]).observation()
    policy = EquipmentOpportunityTiePolicy()
    first_move = policy.choose(observation, Random(173))
    first_audit = deepcopy(policy.last_audit)
    assert first_audit["public_observation_sha256"] == canonical_digest(public_observation_record(observation))
    assert first_audit["primary_tier_sha256"] == canonical_digest(first_audit["primary_tier"])
    assert first_audit["narrowed_tier_sha256"] == canonical_digest(first_audit["narrowed_tier"])
    assert first_audit["chosen_move"] == move_record(first_move)
    # Deliberately corrupt every passive field and make an unrelated call.
    policy.last_audit.clear()
    policy.last_audit["choose-this-hand-index"] = 0
    policy.choose(state_with([]).observation(), Random(179))
    assert policy.choose(observation, Random(173)) == first_move
    assert policy.last_audit == first_audit
    assert not {"ordinal", "timestamp", "seed", "run_id"}.intersection(first_audit)


def test_public_digest_changes_with_public_geometry_history_hand_and_setup():
    observation = state_with([card("visible", material=Material.ROPE)]).observation()
    original = canonical_digest(public_observation_record(observation))
    variants = [
        replace(observation, raincoats=1), replace(observation, ropes=1),
        replace(observation, exit_seen=True), replace(observation, turns=1),
        replace(observation, hand=(card("other", material=Material.ROPE),)),
        replace(observation, setup=GameSetup(hand_size=3)),
        replace(observation, collected_equipment=(CollectedEquipment(card("old", material=Material.ROPE), 1),)),
    ]
    changed_board = observation.board.clone()
    changed_board.place(card("on-board"), (1, 0))
    variants.append(replace(observation, board=changed_board))
    assert all(canonical_digest(public_observation_record(item)) != original for item in variants)


def test_trace_and_legal_order_are_identical_across_python_hash_seeds():
    script = """
import json
from random import Random
from bandido_alcatraz.board import Board
from bandido_alcatraz.game import GameState
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.equipment_opportunity import EquipmentOpportunityTiePolicy
def card(name, edges, material=None):
    return CardDefinition(name, (CellSpec(0, 0, frozenset(edges)),), material)
b = Board()
b.seed(card('start', {Direction.EAST, Direction.NORTH, Direction.SOUTH}))
hand = [card('z', {Direction.EAST, Direction.WEST}, Material.ROPE),
        card('a', set(), Material.ROPE), card('b', set(), Material.RAINCOAT)]
p = EquipmentOpportunityTiePolicy()
p.choose(GameState(b, [], hand).observation(), Random(181))
print(json.dumps(p.last_audit, sort_keys=True, separators=(',', ':')))
"""
    root = Path(__file__).resolve().parents[1]
    outputs = []
    for seed in ("0", "1", "97"):
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1")
        env["PYTHONPATH"] = str(root / "src")
        outputs.append(subprocess.check_output([sys.executable, "-c", script], cwd=root, env=env, text=True))
    assert outputs[0] == outputs[1] == outputs[2]
