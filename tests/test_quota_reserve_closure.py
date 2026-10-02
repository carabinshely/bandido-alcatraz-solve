"""Invented synthetic inventories only; no real deck, cohort, seed or game run."""
from dataclasses import replace
from random import Random
import sys

import pytest

from bandido_alcatraz import moves as canonical_moves, strategy
from bandido_alcatraz.board import Board, VisibleCell
from bandido_alcatraz.game import CollectedEquipment, GameState, PlayerObservation
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.policies import BoundedMergeV4Policy
from bandido_alcatraz.quota_reserve_closure import (
    IntegrityError, OperationLimits, QuotaReserveClosurePolicy, ResourceExceeded,
)
from bandido_alcatraz.setup import SOLO_EASY, GameSetup
from bandido_alcatraz.worker32.evidence import canonical, move, observation, sha

N, E, S, W = Direction.NORTH, Direction.EAST, Direction.SOUTH, Direction.WEST


def card(identity, edges=(), material=None, *, water=False, exit=False):
    return CardDefinition(identity, (CellSpec(0, 0, frozenset(edges), water),), material, exit)


def inventory(*, coat_edges=(W,), rope_edges=(W,), wet_coat=False, exit_edges=(W,), overrides=()):
    """Five-exit two-cell START and 69 physically distinct invented deck cards."""
    start = CardDefinition("start_easy", (
        CellSpec(0, 0, frozenset((W, N, E))),
        CellSpec(1, 0, frozenset((W, N, E, S))),
    ))
    cards = [card(f"coat-{i}", coat_edges, Material.RAINCOAT, water=wet_coat) for i in range(12)]
    cards += [card(f"rope-{i}", rope_edges, Material.ROPE) for i in range(8)]
    cards += [card(f"ordinary-{i}") for i in range(48)]
    exit_card = card("exit", exit_edges, exit=True)
    cards.append(exit_card)
    by_id = {c.card_id: c for c in cards}
    by_id.update({c.card_id: c for c in overrides})
    catalog = tuple(by_id.values())
    policy = QuotaReserveClosurePolicy(catalog=catalog, start_card=start, exit_card=by_id["exit"])
    return policy, by_id, start


def fixture(*, hand_ids=("coat-0",), placements=(), collected=(), set_aside=0, **kwargs):
    policy, cards, start = inventory(**kwargs)
    board = Board(); board.seed(start)
    for identity, origin, rotation in placements:
        board.place(cards[identity], origin, rotation)
    equipment = tuple(CollectedEquipment(cards[identity], turn) for identity, turn in collected)
    used = {p.card_id for p in board.placements} | {e.card_id for e in equipment} | set(hand_ids)
    hand_ids = tuple(hand_ids) + tuple(c.card_id for c in cards.values()
                                      if c.card_id.startswith("ordinary-") and c.card_id not in used)[:6-len(hand_ids)]
    obs = PlayerObservation(board, tuple(cards[c] for c in hand_ids),
                            sum(e.material is Material.RAINCOAT for e in equipment),
                            sum(e.material is Material.ROPE for e in equipment),
                            any(p.card_id == "exit" for p in board.placements),
                            "exit" in hand_ids or any(p.card_id == "exit" for p in board.placements),
                            len(placements) + len(equipment), set_aside, equipment, SOLO_EASY)
    return policy, obs, cards


class CountingRandom(Random):
    def __init__(self, seed=11):
        super().__init__(seed)
        self.calls = []

    def choice(self, values):
        self.calls.append(tuple(values))
        return super().choice(values)


def test_true_original_collect_crossover_exact_scores_order_rng_and_cost():
    policy, obs, _ = fixture()
    before = canonical(observation(obs)); rng = CountingRandom()
    legal = obs.legal_moves()
    expected_scores = [strategy.score_move_no_draw(obs, m, BoundedMergeV4Policy(250).weights) for m in legal]
    selected, audit, costs = policy.evaluate(obs, rng)
    assert audit["roots"] == [dict(move=move(m), score=s) for m, s in zip(legal, expected_scores)]
    assert audit["tiers"]["T0"] == audit["tiers"]["T"] == [0]
    assert selected.action is Action.PLACE
    assert audit["flags"] == dict(reserve_filter_active=False, reserve_primary_tier_changed=False,
                                  closure_branch_selected=True, true_original_all_collect_crossover=True,
                                  reserve_filter_mediated_change=False)
    assert audit["tiers"]["C"] == list(range(1, len(legal)))
    replay = Random(11)
    expected = replay.choice([legal[i] for i in audit["tiers"]["final"]])
    assert selected == expected and rng.getstate() == replay.getstate()
    assert rng.calls == [tuple(legal[i] for i in audit["tiers"]["final"])]
    assert audit["rng_before"] == sha(Random(11).getstate())
    assert audit["rng_after"] == sha(rng.getstate())
    p = sum(m.action is Action.PLACE for m in legal)
    assert costs == dict(legal_enumerations=1+3*p, previews=2*p, exit_geometry_checks=p, roots=len(legal))
    assert canonical(observation(obs)) == before


@pytest.mark.parametrize("spent,expected_available", [(8, 4), (9, 3), (10, 2)])
def test_reserve_boundary_and_physically_valid_infeasibility(spent, expected_available):
    overrides = [card(f"coat-{i}", (E, W), Material.RAINCOAT) for i in range(spent)]
    placements = [(f"coat-{i}", (i+2, 0), 0) for i in range(spent)]
    policy, obs, _ = fixture(hand_ids=(f"coat-{spent}",), overrides=overrides, placements=placements)
    selected, audit, _ = policy.evaluate(obs, CountingRandom())
    assert audit["supply"]["raincoat"]["available"] == expected_available
    if expected_available <= 3:
        assert selected.action is Action.COLLECT
        assert audit["tiers"]["F"] == [0]
        assert audit["flags"]["reserve_filter_active"]
        assert all(g["reason"] == "reserve_filtered" for g in audit["guards"][1:])
    else:
        assert selected.action is Action.PLACE
        assert audit["flags"]["true_original_all_collect_crossover"]


def test_covered_material_identity_is_still_spent_supply():
    overrides = [card(f"coat-{i}", (E, W), Material.RAINCOAT, water=(i == 0)) for i in range(9)]
    overrides += [card("ordinary-47", (E, W))]
    placements = [("coat-0", (2, 0), 0), ("ordinary-47", (2, 0), 0)]
    placements += [(f"coat-{i}", (i+2, 0), 0) for i in range(1, 9)]
    policy, obs, _ = fixture(hand_ids=("coat-9",), overrides=overrides, placements=placements)
    _, audit, _ = policy.evaluate(obs, CountingRandom())
    assert obs.board.placements[2].covered_placement_index == 1
    assert audit["supply"]["raincoat"]["placed"] == 9
    assert audit["supply"]["raincoat"]["available"] == 3
    assert audit["flags"]["reserve_filter_active"]


def test_quota_met_material_placement_is_not_reserve_filtered():
    policy, obs, _ = fixture(collected=(("coat-0", 1), ("coat-1", 2), ("coat-2", 3)),
                             hand_ids=("coat-3",))
    selected, audit, _ = policy.evaluate(obs, CountingRandom())
    assert selected.action is Action.PLACE
    assert audit["supply"]["raincoat"]["deficit"] == 0
    assert not audit["flags"]["reserve_filter_active"]
    assert audit["tiers"]["C"] == []
    assert all(g == dict(eligible=False, reason="branch_not_active", after=None, exit_legal_count=None)
               for g in audit["guards"])


def test_final_required_copy_with_two_already_collected():
    overrides = [card(f"coat-{i}", (E, W), Material.RAINCOAT) for i in range(9)]
    placements = [(f"coat-{i}", (i+2, 0), 0) for i in range(9)]
    policy, obs, _ = fixture(overrides=overrides, placements=placements,
                             collected=(("coat-9", 10), ("coat-10", 11)), hand_ids=("coat-11",))
    selected, audit, _ = policy.evaluate(obs, CountingRandom())
    assert selected.action is Action.COLLECT
    assert audit["supply"]["raincoat"]["available"] == audit["supply"]["raincoat"]["deficit"] == 1


def test_empty_legal_is_engine_refresh_and_consumes_no_rng():
    policy, obs, _ = fixture(hand_ids=())
    rng = CountingRandom(); before = rng.getstate()
    selected, audit, costs = policy.evaluate(obs, rng)
    assert selected is None and not rng.calls and before == rng.getstate()
    assert audit["tiers"] == dict(T0=[], F=[], T=[], C=[], final=[])
    assert audit["roots"] == audit["guards"] == [] and audit["chosen_index"] is None
    assert audit["rng_before"] == audit["rng_after"]
    assert costs == dict(legal_enumerations=1, previews=0, exit_geometry_checks=0, roots=0)


def test_singleton_collect_still_calls_choice():
    policy, obs, _ = fixture(coat_edges=())
    rng = CountingRandom()
    selected, audit, _ = policy.evaluate(obs, rng)
    assert selected == Move(Action.COLLECT, 0)
    assert len(rng.calls) == 1 and len(rng.calls[0]) == 1
    assert audit["tiers"]["final"] == [0]


def test_ordinary_refresh_preserves_needed_supply():
    policy, obs, cards = fixture(hand_ids=())
    hand = list(obs.hand)
    draw = [c for c in cards.values() if c not in hand]
    state = GameState(obs.board.clone(), draw, hand, setup=SOLO_EASY)
    _, before, _ = policy.evaluate(state.observation(), CountingRandom())
    assert state.refresh_unplayable_hand()
    _, after, _ = policy.evaluate(state.observation(), CountingRandom())
    assert state.set_aside_unplayable == 0
    assert before["supply"]["raincoat"]["available"] == after["supply"]["raincoat"]["available"] == 12
    assert before["supply"]["rope"]["available"] == after["supply"]["rope"]["available"] == 8


def short_pile_fixture():
    overrides = [card(f"coat-{i}", (E, W), Material.RAINCOAT) for i in range(9)]
    overrides += [card(f"rope-{i}", (E, W), Material.ROPE) for i in range(6)]
    overrides += [card(f"ordinary-{i}", (E, W)) for i in range(42)]
    ids = [c.card_id for c in overrides]
    placements = [(identity, (i+2, 0), 0) for i, identity in enumerate(ids)]
    policy, obs, cards = fixture(hand_ids=tuple(f"ordinary-{i}" for i in range(42, 48)),
                               overrides=overrides, placements=placements)
    draw = [cards[f"coat-{i}"] for i in range(9, 12)]
    draw += [cards[f"rope-{i}"] for i in range(6, 8)] + [cards["exit"]]
    return policy, GameState(obs.board.clone(), draw, list(obs.hand), turns=obs.turns, setup=SOLO_EASY)


def test_short_pile_refresh_stock_equals_own_hand_and_detects_corruption():
    policy, state = short_pile_fixture()
    assert state.refresh_unplayable_hand() and not state.draw_pile
    obs = state.observation()
    _, audit, _ = policy.evaluate(obs, CountingRandom())
    assert obs.set_aside_unplayable == 6
    for material in ("raincoat", "rope"):
        s = audit["supply"][material]
        assert s["available"] == s["own_hand"] == s["deficit"]
    # The discarded identities are private, but public needed stock must still
    # equal own hand. Reusing a catalog identity absent from public history does
    # not conceal a missing needed copy from that public invariant.
    corrupted = replace(obs, hand=(policy.catalog["ordinary-43"],) + obs.hand[1:])
    with pytest.raises(IntegrityError, match="needed-material supply"):
        policy.evaluate(corrupted, CountingRandom())
    policy2, obs2, _ = fixture(set_aside=1)
    with pytest.raises(IntegrityError, match="short-pile"):
        policy2.evaluate(obs2, CountingRandom())


@pytest.mark.parametrize("set_aside", range(1, 6))
def test_partial_set_aside_count_is_unreachable_in_canonical_hand_six(set_aside):
    policy, obs, _ = fixture(set_aside=set_aside)
    rng = CountingRandom()
    with pytest.raises(IntegrityError, match="short-pile set-aside count"):
        policy.evaluate(obs, rng)
    assert not rng.calls


@pytest.mark.parametrize("change", [
    lambda o, c: replace(o, hand=(card("unknown", (W,)),) + o.hand[1:]),
    lambda o, c: replace(o, hand=(o.hand[0], o.hand[0]) + o.hand[2:]),
    lambda o, c: replace(o, hand=(replace(o.hand[0], material=Material.ROPE),) + o.hand[1:]),
    lambda o, c: replace(o, hand=(replace(o.hand[0], cells=(CellSpec(0, 0, frozenset((E, W))),)),) + o.hand[1:]),
    lambda o, c: replace(o, raincoats=1),
    lambda o, c: replace(o, raincoats=True),
    lambda o, c: replace(o, ropes=3),
    lambda o, c: replace(o, turns=1),
    lambda o, c: replace(o, player_index=True),
    lambda o, c: replace(o, exit_seen=1),
    lambda o, c: replace(o, exit_placed=True),
    lambda o, c: replace(o, setup=GameSetup(hand_size=3)),
    lambda o, c: replace(o, hand=o.hand[:1]),
    lambda o, c: replace(o, collected_equipment=[]),
])
def test_malformed_live_public_inputs_fail_without_rng(change):
    policy, obs, cards = fixture(); rng = CountingRandom()
    with pytest.raises(IntegrityError):
        policy.evaluate(change(obs, cards), rng)
    assert not rng.calls


def test_cross_zone_reuse_start_identity_history_and_visible_geometry():
    policy, obs, cards = fixture(hand_ids=("coat-0",), collected=(("coat-1", 1),))
    duplicate = replace(obs, collected_equipment=(CollectedEquipment(cards["coat-0"], 1),))
    with pytest.raises(IntegrityError, match="cross-zone"):
        policy.evaluate(duplicate, CountingRandom())
    bad_turn = replace(obs, collected_equipment=(CollectedEquipment(cards["coat-1"], True),))
    with pytest.raises(IntegrityError, match="chronology"):
        policy.evaluate(bad_turn, CountingRandom())
    bad_start = Board(); bad_start.seed(card("not-start", (E,)))
    with pytest.raises(IntegrityError, match="START"):
        policy.evaluate(replace(obs, board=bad_start), CountingRandom())
    corrupt = obs.board.clone(); corrupt._cells[(999, 999)] = VisibleCell(frozenset())
    with pytest.raises(IntegrityError, match="geometry/history"):
        policy.evaluate(replace(obs, board=corrupt), CountingRandom())
    with pytest.raises(IntegrityError, match="separate easy START"):
        QuotaReserveClosurePolicy(catalog=tuple(policy.catalog.values()),
                                  start_card=cards["coat-0"], exit_card=cards["exit"])


def test_duplicate_unknown_and_tampered_covered_placement_history():
    overrides = [card("coat-0", (E, W), Material.RAINCOAT, water=True),
                 card("ordinary-47", (E, W))]
    policy, obs, cards = fixture(hand_ids=("coat-1",), overrides=overrides,
                               placements=(("coat-0", (2, 0), 0), ("ordinary-47", (2, 0), 0)))
    duplicate = obs.board.clone(); duplicate.place(cards["coat-0"], (3, 0), 0)
    with pytest.raises(IntegrityError, match="cross-zone"):
        policy.evaluate(replace(obs, board=duplicate, turns=3), CountingRandom())
    unknown = obs.board.clone(); unknown.place(card("unknown", (E, W)), (3, 0), 0)
    with pytest.raises(IntegrityError, match="unknown placement"):
        policy.evaluate(replace(obs, board=unknown, turns=3), CountingRandom())
    corrupted = obs.board.clone()
    corrupted._placement_tail = replace(corrupted._placement_tail,
        placement=replace(corrupted.placements[-1], covered_placement_index=None))
    with pytest.raises(IntegrityError, match="covered history"):
        policy.evaluate(replace(obs, board=corrupted), CountingRandom())


def test_impossible_filtered_empty_is_explicit_integrity_failure(monkeypatch):
    overrides = [card(f"coat-{i}", (E, W), Material.RAINCOAT) for i in range(9)]
    placements = [(f"coat-{i}", (i+2, 0), 0) for i in range(9)]
    policy, obs, _ = fixture(hand_ids=("coat-9",), overrides=overrides, placements=placements)
    actual = PlayerObservation.legal_moves
    monkeypatch.setattr(PlayerObservation, "legal_moves",
                        lambda o: [m for m in actual(o) if m.action is Action.PLACE])
    rng = CountingRandom()
    with pytest.raises(IntegrityError, match="empty policy-admissible"):
        policy.evaluate(obs, rng)
    assert not rng.calls


def test_corrupt_score_is_not_fallback_or_refresh(monkeypatch):
    policy, obs, _ = fixture()
    monkeypatch.setattr(strategy, "score_move_no_draw", lambda *args: float("nan"))
    rng = CountingRandom()
    with pytest.raises(IntegrityError, match="scores must be integers"):
        policy.evaluate(obs, rng)
    assert not rng.calls


def test_terminal_closure_is_rejected_and_override_never_closes_last():
    caps = [card(f"ordinary-{i}", (W,)) for i in range(5)]
    placements = [("ordinary-0", (-1, 0), 2), ("ordinary-1", (0, -1), 3),
                  ("ordinary-2", (1, -1), 3), ("ordinary-3", (1, 1), 1)]
    policy, live, _ = fixture(overrides=caps, placements=placements)
    selected, audit, _ = policy.evaluate(live, CountingRandom())
    assert live.board.open_tunnels == 1 and selected.action is Action.COLLECT
    assert any(g["reason"] == "closed_tunnels" for g in audit["guards"])
    policy, terminal, _ = fixture(overrides=caps, placements=placements + [("ordinary-4", (2, 0), 0)])
    with pytest.raises(IntegrityError, match="terminal"):
        policy.evaluate(terminal, CountingRandom())


def test_visible_water_and_exit_capacity_guards():
    policy, obs, _ = fixture(wet_coat=True)
    selected, audit, _ = policy.evaluate(obs, CountingRandom())
    assert selected.action is Action.COLLECT
    assert all(g["reason"] == "visible_water_increased" for g in audit["guards"][1:])
    assert all(g["exit_legal_count"] is None for g in audit["guards"])
    policy, obs, _ = fixture(exit_edges=())
    selected, audit, _ = policy.evaluate(obs, CountingRandom())
    assert selected.action is Action.COLLECT
    assert all(g["reason"] == "no_exit_capacity" and g["exit_legal_count"] == 0
               for g in audit["guards"][1:])


def test_water_obstruction_guard_with_unchanged_visible_water():
    wet = CardDefinition("ordinary-47", (
        CellSpec(0, 0, frozenset((W,))),
        CellSpec(0, 1, frozenset(), True),
    ))
    policy, obs, _ = fixture(hand_ids=tuple(f"coat-{i}" for i in range(6)),
                             overrides=(wet,), placements=(("ordinary-47", (2, 0), 0),))
    _, audit, _ = policy.evaluate(obs, CountingRandom())
    roots = [(r, g) for r, g in zip(audit["roots"], audit["guards"])
             if g["reason"] == "water_obstruction_increased"]
    assert roots
    for _, guard in roots:
        assert guard["after"][1] == obs.board.visible_water_cells
        assert guard["after"][2] > obs.board.water_obstruction
        assert guard["exit_legal_count"] is None


def test_trapped_water_guard_can_bind_without_increased_total_obstruction():
    # An invented two-cell coat covers water V=(2,0), while its new lower cell
    # traps U=(1,1). Removing V's obstruction balances U's increase; the separate
    # trapped-water guard must still reject this otherwise useful closure.
    coat = CardDefinition("coat-0", (
        CellSpec(0, 0, frozenset((W, S))),
        CellSpec(0, 1, frozenset((N,))),
    ), Material.RAINCOAT)
    policy, obs, cards = fixture(hand_ids=tuple(f"coat-{i}" for i in range(6)), overrides=(coat,))
    start = CardDefinition("start_easy", (
        CellSpec(1, 0, frozenset((N, E))),
        CellSpec(2, 0, frozenset((W, S)), True),
        CellSpec(0, 1, frozenset((N, W, S))),
        CellSpec(1, 1, frozenset(), True),
        CellSpec(1, 2, frozenset()),
    ))
    policy = QuotaReserveClosurePolicy(catalog=tuple(cards.values()), start_card=start, exit_card=cards["exit"])
    board = Board(); board.seed(start); obs = replace(obs, board=board)
    _, audit, _ = policy.evaluate(obs, CountingRandom())
    index = next(i for i, r in enumerate(audit["roots"])
                 if r["move"] == move(Move(Action.PLACE, 0, (2, 0), 0)))
    assert audit["guards"][index] == dict(eligible=False, reason="trapped_water_increased",
                                         after=[4, 1, 4, 1], exit_legal_count=None)
    assert board.visible_water_cells == 2 and board.water_obstruction == 4


def test_placed_exit_skips_standalone_capacity_check():
    policy, obs, _ = fixture(exit_edges=(E, W), placements=(("exit", (2, 0), 0),))
    selected, audit, costs = policy.evaluate(obs, CountingRandom())
    assert selected.action is Action.PLACE and costs["exit_geometry_checks"] == 0
    assert all(g["exit_legal_count"] is None for g in audit["guards"])


def test_does_not_reduce_open_and_nonmaterial_guard_reasons():
    policy, obs, _ = fixture(coat_edges=(E, W), hand_ids=("coat-0", "exit"))
    selected, audit, _ = policy.evaluate(obs, CountingRandom())
    assert selected.action is Action.COLLECT
    assert {g["reason"] for g in audit["guards"]} == {"not_place", "not_reduced", "not_needed_material"}


def test_mixed_tier_skips_closure_and_ties_preserve_full_canonical_order(monkeypatch):
    """Isolate selector algebra using invented scores; other tests assert exact S4."""
    policy, obs, _ = fixture(hand_ids=("coat-0", "rope-0"))
    original = strategy.score_move_no_draw
    def tied_score(o, m, weights):
        original(o, m, weights)
        return 7
    monkeypatch.setattr(strategy, "score_move_no_draw", tied_score)
    _, audit, _ = policy.evaluate(obs, CountingRandom())
    all_indices = list(range(len(obs.legal_moves())))
    assert audit["tiers"] == dict(T0=all_indices, F=all_indices, T=all_indices, C=[], final=all_indices)
    assert all(g["reason"] == "branch_not_active" for g in audit["guards"])


def test_reserve_filter_mediated_change_is_not_original_collect_crossover(monkeypatch):
    overrides = [card(f"coat-{i}", (E, W), Material.RAINCOAT) for i in range(9)]
    placements = [(f"coat-{i}", (i+2, 0), 0) for i in range(9)]
    policy, obs, _ = fixture(hand_ids=("coat-9", "rope-0"), overrides=overrides, placements=placements)
    original = strategy.score_move_no_draw
    def ranked_score(o, m, weights):
        original(o, m, weights)
        return 20000 if m.hand_index == 0 and m.action is Action.PLACE else (
            10000 if m.action is Action.COLLECT else 100)
    monkeypatch.setattr(strategy, "score_move_no_draw", ranked_score)
    selected, audit, _ = policy.evaluate(obs, CountingRandom())
    assert selected.action is Action.PLACE and selected.hand_index == 1
    assert audit["flags"] == dict(reserve_filter_active=True, reserve_primary_tier_changed=True,
                                  closure_branch_selected=True, true_original_all_collect_crossover=False,
                                  reserve_filter_mediated_change=True)


def test_actual_physical_profile_counts_and_hook_restoration():
    policy, obs, _ = fixture()
    observed = dict(legal_enumerations=0, previews=0, exit_geometry_checks=0)
    codes = {canonical_moves.legal_moves.__code__: "legal_enumerations",
             canonical_moves.placement_moves.__code__: "legal_enumerations",
             strategy.preview_move_without_draw.__code__: "previews",
             strategy.standalone_exit_legal_move_count.__code__: "exit_geometry_checks"}
    def external_profile(frame, event, arg):
        if event == "call" and frame.f_code in codes:
            observed[codes[frame.f_code]] += 1
    prior = sys.getprofile()
    try:
        sys.setprofile(external_profile)
        _, _, costs = policy.evaluate(obs, CountingRandom())
        assert sys.getprofile() is external_profile
        assert observed == {k: costs[k] for k in observed}
        rng = CountingRandom()
        with pytest.raises(ResourceExceeded):
            policy.evaluate(obs, rng, limits=OperationLimits(previews=0))
        assert sys.getprofile() is external_profile and not rng.calls
    finally:
        sys.setprofile(prior)


@pytest.mark.parametrize("failure_event", ["installation", "return"])
def test_forwarded_hook_failure_during_installation_restores_original_hook(failure_event):
    policy, obs, _ = fixture(); rng = CountingRandom()
    original = sys.getprofile(); raised = False
    before = sha(observation(obs)); rng_before = rng.getstate()
    failure = RuntimeError("synthetic forwarded hook installation failure")
    def raising_prior(frame, event, arg):
        nonlocal raised
        target = ((failure_event == "installation" and event == "c_return" and arg is sys.setprofile)
                  or (failure_event == "return" and event == "return" and frame.f_code.co_name == "__enter__"))
        if not raised and target and sys.getprofile() is not raising_prior:
            raised = True
            raise failure
    try:
        sys.setprofile(raising_prior)
        with pytest.raises(RuntimeError) as caught:
            policy.evaluate(obs, rng)
        assert caught.value is failure and raised
        assert sys.getprofile() is raising_prior
        assert not rng.calls and rng.getstate() == rng_before
        assert sha(observation(obs)) == before
    finally:
        sys.setprofile(original)


def test_noncallable_native_profile_hook_is_preserved_on_explicit_rejection(monkeypatch):
    # CPython3.11 native profilers can expose a non-callable hook; newer Python
    # may use sys.monitoring instead. Model that interface without depending on
    # the ambient interpreter's profiling mechanism.
    policy, obs, _ = fixture(); native_hook = object(); rng = CountingRandom(); replacements = []
    monkeypatch.setattr(sys, "getprofile", lambda: native_hook)
    monkeypatch.setattr(sys, "setprofile", replacements.append)
    with pytest.raises(IntegrityError, match="native profile hook"):
        policy.evaluate(obs, rng)
    assert sys.getprofile() is native_hook and not replacements and not rng.calls


@pytest.mark.parametrize("limits", [OperationLimits(legal_enumerations=0), OperationLimits(previews=0),
                                     OperationLimits(exit_geometry_checks=0)])
def test_resource_overflow_is_explicit_no_rng_or_fallback_and_restores_hook(limits):
    policy, obs, _ = fixture(); rng = CountingRandom(); prior = sys.getprofile()
    with pytest.raises(ResourceExceeded):
        policy.evaluate(obs, rng, limits=limits)
    assert not rng.calls and sys.getprofile() is prior


def test_no_private_state_access_or_persistent_decision_state():
    policy, obs, cards = fixture()
    state = GameState(obs.board.clone(), [], list(obs.hand), setup=SOLO_EASY)
    class Poison:
        def __iter__(self): raise AssertionError("hidden zone accessed")
        def __len__(self): raise AssertionError("hidden zone accessed")
        def __bool__(self): raise AssertionError("hidden zone accessed")
    detached = state.observation()
    state.draw_pile = Poison(); state.face_down_set_aside = Poison()
    a = policy.evaluate(detached, CountingRandom())
    b = policy.evaluate(obs, CountingRandom())
    assert canonical(a[1]) == canonical(b[1]) and a[0] == b[0]
    with pytest.raises(IntegrityError, match="PlayerObservation"):
        policy.evaluate(state, CountingRandom())
    with pytest.raises(AttributeError):
        policy._exit_card = cards["coat-0"]
    with pytest.raises(TypeError):
        policy.catalog["coat-0"] = cards["rope-0"]
    policy.choose(fixture(hand_ids=())[1], CountingRandom())
    assert canonical(policy.evaluate(obs, CountingRandom())[1]) == canonical(a[1])
