"""Synthetic regressions for Issue31; no research/deck-population execution."""

from dataclasses import fields
from random import Random

import pytest

from bandido_alcatraz.board import Board
from bandido_alcatraz.export_svg import FinalBoardExport, FinalStateCapturePolicy
from bandido_alcatraz.game import CollectedEquipment, GameState
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action, Move, legal_moves, placement_moves
from bandido_alcatraz.policies import BoundedMergeV4Policy, RandomLegalPolicy, VisibleHandTwoActionV6Policy
from bandido_alcatraz.rules import RULESET_ID, GameStatus, can_collect, is_victory
from bandido_alcatraz.setup import GameSetup
from bandido_alcatraz.simulate import play_game
from bandido_alcatraz.strategy import move_features, move_features_no_draw, preview_move_without_draw, two_action_sequence_score


def card(card_id, material=None, *, blocked=False, is_exit=False):
    edges = set() if blocked else {Direction.WEST, Direction.EAST}
    return CardDefinition(card_id, (CellSpec(0, 0, frozenset(edges)),), material, is_exit)


def state_with(hand, *, raincoats=0, ropes=0, draw=(), hand_size=3):
    board = Board()
    board.seed(CardDefinition("start", (CellSpec(0, 0, frozenset({Direction.EAST})),)))
    return GameState(board, list(draw), list(hand), raincoats=raincoats, ropes=ropes,
                     setup=GameSetup(hand_size=hand_size))


def snapshot(state):
    """All mutable zones/flags plus container identity and hand-zone aliasing."""
    return {
        field.name: (
            (state.board.cells, state.board.placements) if field.name == "board"
            else tuple(tuple(hand) for hand in state.private_hands) if field.name == "private_hands"
            else tuple(getattr(state, field.name)) if isinstance(getattr(state, field.name), list)
            else getattr(state, field.name)
        )
        for field in fields(state)
    }, (id(state.board), id(state.hand), id(state.draw_pile),
        id(state.private_hands), tuple(map(id, state.private_hands)))


@pytest.mark.parametrize("raincoats", range(5))
@pytest.mark.parametrize("ropes", range(4))
def test_collection_boundaries_are_independent_and_identical_for_state_and_observation(raincoats, ropes):
    hand = [card("coat", Material.RAINCOAT), card("rope", Material.ROPE), card("ordinary")]
    state = state_with(hand, raincoats=raincoats, ropes=ropes)
    moves = state.legal_moves()
    assert moves == state.observation().legal_moves()
    assert can_collect(Material.RAINCOAT, raincoats=raincoats, ropes=ropes) == (raincoats < 3)
    assert can_collect(Material.ROPE, raincoats=raincoats, ropes=ropes) == (ropes < 2)
    assert not can_collect(None, raincoats=raincoats, ropes=ropes)
    assert (Move(Action.COLLECT, 0) in moves) == (raincoats < 3)
    assert (Move(Action.COLLECT, 1) in moves) == (ropes < 2)
    assert Move(Action.COLLECT, 2) not in moves
    # Quota room permits collection; it never forces it instead of placement.
    for hand_index in range(len(hand)):
        assert any(m.action is Action.PLACE and m.hand_index == hand_index for m in moves)
    # Only remove unavailable COLLECTs: preserve every placement and relative
    # order, including the interleaved order of different hand indexes.
    original_order = legal_moves(state.board, tuple(hand), raincoats=0, ropes=0)
    expected = [m for m in original_order if m.action is Action.PLACE or
                (m.hand_index == 0 and raincoats < 3) or (m.hand_index == 1 and ropes < 2)]
    assert moves == expected
    assert [m for m in moves if m.action is Action.PLACE] == placement_moves(state.board, tuple(hand))


def test_inventory_is_required_and_geometry_api_never_implies_collect_permission():
    equipment = card("coat", Material.RAINCOAT)
    state = state_with([equipment])
    with pytest.raises(TypeError):
        legal_moves(state.board, (equipment,))
    assert placement_moves(state.board, (equipment,))
    assert all(m.action is Action.PLACE for m in placement_moves(state.board, (equipment,)))


def test_quota_filter_preserves_frozen_interleaved_move_order():
    state = state_with([card("coat", Material.RAINCOAT), card("rope", Material.ROPE), card("ordinary")])
    placements = [Move(Action.PLACE, i, origin=(1, 0)) for i in range(3)]
    assert state.legal_moves() == [Move(Action.COLLECT, 0), placements[0],
                                   Move(Action.COLLECT, 1), placements[1], placements[2]]
    state.raincoats = 3
    assert state.legal_moves() == [placements[0], Move(Action.COLLECT, 1), placements[1], placements[2]]
    state.ropes = 2
    assert state.legal_moves() == placements


@pytest.mark.parametrize("validate", [False, True])
@pytest.mark.parametrize("material,raincoats,ropes", [
    (Material.RAINCOAT, 3, 0), (Material.RAINCOAT, 4, 2),
    (Material.ROPE, 0, 2), (Material.ROPE, 3, 3), (None, 0, 0),
])
def test_illegal_collection_rejects_atomically_before_any_draw_or_history_change(validate, material, raincoats, ropes):
    hidden_exit = card("hidden-exit", is_exit=True)
    state = state_with([card("rejected", material), card("retained")],
                       raincoats=raincoats, ropes=ropes, draw=[hidden_exit])
    state.turns = 7
    state.collected_equipment = (CollectedEquipment(card("old-coat", Material.RAINCOAT), 2),)
    state.face_down_set_aside = (card("private-discard", blocked=True),)
    state.set_aside_unplayable = 1
    rng = Random(71)
    before, rng_before = snapshot(state), rng.getstate()
    with pytest.raises(ValueError, match="illegal collect"):
        state.apply(Move(Action.COLLECT, 0), validate=validate)
    assert snapshot(state) == before
    assert rng.getstate() == rng_before
    assert state.private_hands[0] is state.hand
    assert not state.exit_seen


@pytest.mark.parametrize("material,raincoats,ropes", [(Material.RAINCOAT, 3, 2), (Material.ROPE, 3, 2)])
@pytest.mark.parametrize("validate", [False, True])
def test_equipment_placement_stays_legal_after_its_quota_is_filled(material, raincoats, ropes, validate):
    equipment = card("place-me", material)
    state = state_with([equipment], raincoats=raincoats, ropes=ropes)
    move = state.legal_moves()[0]
    assert move.action is Action.PLACE
    state.apply(move, validate=validate)
    assert state.board.placements[-1].card_id == equipment.card_id
    assert (state.raincoats, state.ropes) == (raincoats, ropes)
    assert not state.collected_equipment


@pytest.mark.parametrize("material,counts", [(Material.RAINCOAT, (2, 1)), (Material.ROPE, (2, 1))])
def test_successor_removes_newly_excess_collect_but_keeps_other_material_and_placement(material, counts):
    other = Material.ROPE if material is Material.RAINCOAT else Material.RAINCOAT
    state = state_with([card("first", material), card("same", material), card("other", other)],
                       raincoats=counts[0], ropes=counts[1], draw=[card("secret")])
    before = snapshot(state)
    first = Move(Action.COLLECT, 0)
    preview = preview_move_without_draw(state.observation(), first)
    successor = preview.successor
    assert snapshot(state) == before
    assert not successor.draw_pile
    assert [c.card_id for c in successor.hand] == ["same", "other"]
    assert Move(Action.COLLECT, 0) not in successor.legal_moves()
    assert Move(Action.COLLECT, 1) in successor.legal_moves()
    assert any(m.action is Action.PLACE and m.hand_index == 0 for m in successor.legal_moves())
    for feature_fn in (move_features, move_features_no_draw):
        with pytest.raises(ValueError, match="illegal collect"):
            feature_fn(successor, Move(Action.COLLECT, 0))
    with pytest.raises(ValueError, match="currently legal"):
        preview_move_without_draw(successor, Move(Action.COLLECT, 0))
    # A move chosen before the quota changed cannot bypass the guard.
    state.apply(first)
    with pytest.raises(ValueError, match="illegal collect"):
        state.apply(Move(Action.COLLECT, 0), validate=False)


@pytest.mark.parametrize("feature_fn", [move_features, move_features_no_draw])
def test_collection_feature_fast_path_checks_quota_without_geometry_or_hidden_zones(feature_fn, monkeypatch):
    state = state_with([card("coat", Material.RAINCOAT)], raincoats=2, ropes=2)

    def forbidden(*args, **kwargs):
        raise AssertionError("collection feature fast path enumerated geometry")

    class PrivateZone:
        __iter__ = __len__ = __bool__ = __getitem__ = forbidden

    monkeypatch.setattr(GameState, "legal_moves", forbidden)
    monkeypatch.setattr(state.board, "candidate_origins", forbidden)
    state.draw_pile = PrivateZone()
    state.face_down_set_aside = PrivateZone()
    features = feature_fn(state, Move(Action.COLLECT, 0))
    assert features.collect_needed == 1 and features.collect_excess == 0
    state.raincoats = 3
    with pytest.raises(ValueError, match="illegal collect"):
        feature_fn(state, Move(Action.COLLECT, 0))


@pytest.mark.parametrize("material,counts", [(Material.RAINCOAT, (2, 2)), (Material.ROPE, (3, 1))])
def test_second_action_cannot_collect_same_material_after_first_fills_quota(material, counts):
    state = state_with([card("a", material, blocked=True), card("b", material, blocked=True)],
                       raincoats=counts[0], ropes=counts[1])
    first = Move(Action.COLLECT, 0)
    weights = BoundedMergeV4Policy(setup_weight=250).weights
    successor = preview_move_without_draw(state, first).successor
    assert successor.legal_moves() == []
    assert two_action_sequence_score(state, first, weights) == weights.collect_needed


@pytest.mark.parametrize("hand_size", [3, 6])
@pytest.mark.parametrize("replacement_count", [2, 3, 6, 7])
def test_excess_only_blocked_hand_refreshes_with_existing_order_and_conservation(hand_size, replacement_count):
    old = [card(f"coat-{i}", Material.RAINCOAT, blocked=True) for i in range(hand_size)]
    draw = [card(f"draw-{i}") for i in range(replacement_count)]
    state = state_with(old, raincoats=3, ropes=2, draw=draw, hand_size=hand_size)
    assert not state.legal_moves()
    assert state.refresh_unplayable_hand()
    short = replacement_count <= hand_size
    expected_hand = draw if short else list(reversed(draw[-hand_size:]))
    assert state.hand == expected_hand
    assert state.draw_pile == ([] if short else old + draw[:-hand_size])
    assert state.face_down_set_aside == (tuple(old) if short else ())
    assert state.set_aside_unplayable == (hand_size if short else 0)
    assert state.turns == 0 and not state.collected_equipment
    assert (state.raincoats, state.ropes) == (3, 2)
    all_zones = state.hand + state.draw_pile + list(state.face_down_set_aside)
    assert sorted(c.card_id for c in all_zones) == sorted(c.card_id for c in old + draw)
    assert state.private_hands[0] is state.hand
    observation = state.observation()
    assert observation.hand == tuple(expected_hand)
    for private_name in ("draw_pile", "private_hands", "face_down_set_aside"):
        assert not hasattr(observation, private_name)


@pytest.mark.parametrize("hand_size", [3, 6])
def test_remaining_pile_excess_does_not_prevent_deadlock_detection_or_leak_hidden_exit(hand_size):
    hand = [card(f"coat-{i}", Material.RAINCOAT, blocked=True) for i in range(hand_size)]
    draw = [card(f"rope-{i}", Material.ROPE, blocked=True) for i in range(hand_size)]
    draw += [card("unplayable-secret-exit", blocked=True, is_exit=True)]
    state = state_with(hand, raincoats=3, ropes=2, draw=draw, hand_size=hand_size)
    before = snapshot(state)
    assert not state.refresh_unplayable_hand()
    assert snapshot(state) == before and not state.exit_seen


def test_remaining_pile_needed_other_material_still_allows_refresh():
    hand = [card(f"coat-{i}", Material.RAINCOAT, blocked=True) for i in range(3)]
    draw = [card(f"rope-{i}", Material.ROPE, blocked=True) for i in range(4)]
    state = state_with(hand, raincoats=3, ropes=1, draw=draw)
    assert state.refresh_unplayable_hand()
    assert state.legal_moves() == [Move(Action.COLLECT, i) for i in range(3)]


def test_legal_excess_placement_prevents_refresh():
    state = state_with([card("coat", Material.RAINCOAT)], raincoats=3, ropes=2,
                       draw=[card("hidden")])
    before = snapshot(state)
    assert not state.refresh_unplayable_hand()
    assert snapshot(state) == before


@pytest.mark.parametrize("policy", [RandomLegalPolicy(), BoundedMergeV4Policy(setup_weight=250), VisibleHandTwoActionV6Policy()])
def test_excess_only_blocked_hand_has_no_policy_choice_and_consumes_no_rng(policy):
    state = state_with([card("coat", Material.RAINCOAT, blocked=True),
                        card("rope", Material.ROPE, blocked=True)], raincoats=3, ropes=2)
    rng = Random(19)
    before = rng.getstate()
    assert policy.choose(state.observation(), rng) is None
    assert rng.getstate() == before


def test_normal_engine_actions_never_overshoot_and_publish_new_ruleset_identity():
    class PreferCollection:
        def choose(self, observation, rng):
            assert observation.raincoats <= 3 and observation.ropes <= 2
            moves = observation.legal_moves()
            return next((m for m in moves if m.action is Action.COLLECT), moves[0] if moves else None)

    deck = [card(f"coat-{i}", Material.RAINCOAT) for i in range(5)]
    deck += [card(f"rope-{i}", Material.ROPE) for i in range(4)]
    capture = FinalStateCapturePolicy(PreferCollection())
    start = CardDefinition("start", (CellSpec(0, 0, frozenset({Direction.EAST})),))
    result = play_game(start_card=start, deck=deck, hand_size=6, policy=capture, seed=73)
    assert (result.raincoats, result.ropes) == (3, 2)
    assert len(capture.collected_equipment) == 5
    assert result.turns == len(deck) and result.reason == "deck_exhausted"
    assert RULESET_ID == "v2-exact-equipment-quota-limited-collect-full-hand-refresh"
    assert result.ruleset_id == RULESET_ID
    exported = FinalBoardExport.from_capture(game_index=1, capture=capture, result=result)
    assert exported.ruleset_id == RULESET_ID
    assert result.setup_id == "p1-easy-5-exit-hand6-first0-full-hand-refresh"


@pytest.mark.parametrize("raincoats,ropes,expected", [(3, 2, True), (4, 2, False), (3, 3, False), (2, 2, False)])
def test_exact_victory_defense_remains_unchanged_for_fabricated_inventories(raincoats, ropes, expected):
    assert is_victory(GameStatus(raincoats, ropes, 0, 0, True)) is expected
