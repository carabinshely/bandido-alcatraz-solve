"""Cleanroom reference tests using invented physical catalogs and histories only.

No real cohort observation is loaded, reconstructed, scored or executed here.
"""
from dataclasses import replace
from random import Random
from types import SimpleNamespace

import pytest

from bandido_alcatraz.board import Board, VisibleCell
from bandido_alcatraz.game import CollectedEquipment, GameState, PlayerObservation
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction as D, Material
from bandido_alcatraz.moves import Action, Move, placement_moves
from bandido_alcatraz.quota_reserve_closure_reference import (
    QuotaReserveClosureReference, ReferenceInputError,
)
from bandido_alcatraz.setup import SOLO_EASY
from bandido_alcatraz.worker32.evidence import observation as observation_wire


def invented_card(name, edges=(D.WEST, D.EAST), *, material=None, water=False, exit=False):
    return CardDefinition(name, (CellSpec(0, 0, frozenset(edges), water),), material, exit)


def invented_catalog(*, rain_edges=(D.WEST,), rain_water=False, plain_edges=(D.WEST, D.EAST)):
    rain = [invented_card(f'invented-rain-{i}', rain_edges, material=Material.RAINCOAT,
                          water=rain_water) for i in range(12)]
    ropes = [invented_card(f'invented-rope-{i}', material=Material.ROPE) for i in range(8)]
    plain = [invented_card(f'invented-plain-{i}', plain_edges) for i in range(48)]
    exit_card = invented_card('invented-exit', (D.WEST,), exit=True)
    start = CardDefinition('invented-start', (
        CellSpec(0, 0, frozenset((D.NORTH, D.EAST, D.SOUTH, D.WEST))),
        CellSpec(1, 0, frozenset((D.NORTH, D.EAST, D.WEST))),
    ))
    return SimpleNamespace(cards=tuple([*rain, *ropes, *plain, exit_card]),
                           rain=rain, ropes=ropes, plain=plain, exit=exit_card, start=start)


def checker(catalog):
    return QuotaReserveClosureReference(catalog=catalog.cards, start_card=catalog.start,
                                       exit_card=catalog.exit)


def invented_observation(catalog, hand=None, *, board=None, collected=(), set_aside=0, exit_seen=False):
    if board is None:
        board = Board()
        board.seed(catalog.start)
    raincoats = sum(entry.material is Material.RAINCOAT for entry in collected)
    ropes = sum(entry.material is Material.ROPE for entry in collected)
    hand = list(hand if hand is not None else [catalog.rain[0]])
    remaining = 69 - (len(board.placements)-1 + len(collected)) - set_aside
    occupied = {entry.card_id for entry in collected} | {entry.card_id for entry in board.placements}
    for filler in catalog.plain:
        if len(hand) >= min(6, remaining):
            break
        if filler.card_id not in occupied and filler not in hand:
            hand.append(filler)
    hand = tuple(hand)
    exit_placed = any(p.card_id == catalog.exit.card_id for p in board.placements)
    return PlayerObservation(board, hand, raincoats, ropes, exit_placed,
        exit_seen or exit_placed or catalog.exit in hand,
        len(board.placements)-1 + len(collected), set_aside,
        tuple(collected), SOLO_EASY)


def corridor(catalog, cards):
    board = Board()
    board.seed(catalog.start)
    for index, card in enumerate(cards):
        board.place(card, (index+2, 0))
    return board


class CountChoice(Random):
    def __init__(self, seed=13):
        super().__init__(seed)
        self.calls = 0
        self.tiers = []

    def choice(self, seq):
        self.calls += 1
        self.tiers.append(tuple(seq))
        return super().choice(seq)


def test_reference_invented_catalog_and_start_are_distinct():
    catalog = invented_catalog()
    ref = checker(catalog)
    supply = ref._public_validation(invented_observation(catalog))
    assert supply['raincoat'] == dict(quota=3, collected=0, total=12, placed=0,
                                     deficit=3, available=12, own_hand=1)
    with pytest.raises(ReferenceInputError, match='START'):
        QuotaReserveClosureReference(catalog=catalog.cards, start_card=catalog.rain[0],
                                     exit_card=catalog.exit)
    with pytest.raises(ReferenceInputError, match='duplicate'):
        QuotaReserveClosureReference(catalog=(*catalog.cards[:-1], catalog.cards[0]),
                                     start_card=catalog.start, exit_card=catalog.exit)


@pytest.mark.parametrize('change', [
    lambda c, o: replace(o, hand=(replace(c.rain[0], card_id='unknown'),)),
    lambda c, o: replace(o, hand=(c.rain[0], c.rain[0])),
    lambda c, o: replace(o, hand=(replace(c.rain[0], material=Material.ROPE),)),
    lambda c, o: replace(o, hand=(replace(c.rain[0], cells=c.ropes[0].cells),)),
    lambda c, o: replace(o, raincoats=1),
    lambda c, o: replace(o, raincoats=True),
    lambda c, o: replace(o, turns=1),
    lambda c, o: replace(o, exit_placed=True),
    lambda c, o: replace(o, hand=(c.exit,), exit_seen=False),
    lambda c, o: replace(o, hand=()),
])
def test_reference_rejects_malformed_public_identity_or_counts(change):
    catalog = invented_catalog()
    with pytest.raises(ReferenceInputError):
        checker(catalog)._public_validation(change(catalog, invented_observation(catalog)))


def test_reference_does_not_accept_real_state_private_api():
    catalog = invented_catalog()
    obs = invented_observation(catalog)
    state = GameState(board=obs.board, hand=list(obs.hand), draw_pile=[], setup=SOLO_EASY)
    with pytest.raises(ReferenceInputError, match='detached'):
        checker(catalog)._public_validation(state)


def test_reference_collection_identity_history_is_checked():
    catalog = invented_catalog()
    entries = (CollectedEquipment(catalog.rain[0], 1), CollectedEquipment(catalog.ropes[0], 2))
    obs = invented_observation(catalog, [catalog.rain[1]], collected=entries)
    assert checker(catalog)._public_validation(obs)['raincoat']['available'] == 11
    for bad in [replace(obs, hand=(catalog.rain[0],)),
                replace(obs, collected_equipment=(entries[0], entries[0])),
                replace(obs, collected_equipment=tuple(reversed(entries))),
                replace(obs, collected_equipment=(replace(entries[0], turn=0), entries[1])),
                replace(obs, collected_equipment=(replace(entries[0], player_index=1), entries[1]))]:
        with pytest.raises(ReferenceInputError):
            checker(catalog)._public_validation(bad)


def test_reference_counts_material_in_covered_physical_history():
    catalog = invented_catalog(rain_edges=(D.WEST, D.EAST), rain_water=True)
    board = corridor(catalog, [catalog.rain[0]])
    board.place(catalog.plain[0], (2, 0))
    obs = invented_observation(catalog, [catalog.rain[1]], board=board)
    supply = checker(catalog)._public_validation(obs)
    assert board.placements[-1].covered_placement_index == 1
    assert supply['raincoat']['placed'] == 1
    assert supply['raincoat']['available'] == 11
    # Geometry can look identical after a cover but deleting the covered physical
    # identity is still rejected by replay and covered-placement provenance.
    from bandido_alcatraz.board import _PlacementHistoryNode
    bad = board.clone()
    bad._placement_tail = _PlacementHistoryNode(board.placements[-1],
        _PlacementHistoryNode(board.placements[0], None))
    with pytest.raises(ReferenceInputError):
        checker(catalog)._public_validation(replace(obs, board=bad))


def test_reference_rejects_visible_geometry_and_history_tampering():
    catalog = invented_catalog()
    obs = invented_observation(catalog)
    changed = obs.board.clone()
    changed._cells[(100, 100)] = VisibleCell(frozenset())
    with pytest.raises(ReferenceInputError, match='geometry'):
        checker(catalog)._public_validation(replace(obs, board=changed))
    from bandido_alcatraz.board import _PlacementHistoryNode
    changed = obs.board.clone()
    changed._placement_tail = _PlacementHistoryNode(replace(changed.placements[0], card_id='unknown'), None)
    with pytest.raises(ReferenceInputError, match='history'):
        checker(catalog)._public_validation(replace(obs, board=changed))


def test_reference_supply_infeasible_is_not_input_failure():
    catalog = invented_catalog(rain_edges=(D.WEST, D.EAST))
    board = corridor(catalog, catalog.rain[:10])
    supply = checker(catalog)._public_validation(invented_observation(catalog, [catalog.rain[10]], board=board))
    assert supply['raincoat']['available'] == 2 < supply['raincoat']['deficit']


def test_reference_refresh_stock_uses_public_counts_not_hidden_cards():
    catalog = invented_catalog(rain_edges=(D.WEST, D.EAST))
    board = corridor(catalog, [*catalog.rain[:10], *catalog.ropes[:6], *catalog.plain[:43]])
    hand = [*catalog.rain[10:], *catalog.ropes[6:]]
    # A completed short refresh has emptied the draw pile. Only public counts
    # and own cards are used: no identities of the six face-down cards exist here.
    short = invented_observation(catalog, hand, board=board, set_aside=6)
    supply = checker(catalog)._public_validation(short)
    assert supply['raincoat']['available'] == supply['raincoat']['own_hand'] == 2
    assert supply['rope']['available'] == supply['rope']['own_hand'] == 2
    ordinary = invented_observation(catalog, hand, board=board)
    assert checker(catalog)._public_validation(ordinary) == supply
    with pytest.raises(ReferenceInputError, match='physical|public'):
        checker(catalog)._public_validation(replace(short, set_aside_unplayable=5))
    with pytest.raises(ReferenceInputError, match='physical'):
        checker(catalog)._public_validation(replace(short, hand=tuple(hand[:-1])))


def test_reference_true_collect_crossover_and_exact_rng_tier_order():
    catalog = invented_catalog()
    obs = invented_observation(catalog)
    before = observation_wire(obs)
    rng = CountChoice()
    picked, science, cost = checker(catalog).evaluate(obs, rng)
    assert science['schema'] == 'worker35-scientific-v1'
    assert science['flags'] == dict(reserve_filter_active=False,
        reserve_primary_tier_changed=False, closure_branch_selected=True,
        true_original_all_collect_crossover=True, reserve_filter_mediated_change=False)
    assert [science['roots'][i]['move']['action'] for i in science['tiers']['T0']] == ['collect']
    assert science['tiers']['C'] == science['tiers']['final']
    assert picked.action is Action.PLACE and picked.hand_index == 0
    assert rng.calls == 1 and rng.tiers[0] == tuple(obs.legal_moves()[i] for i in science['tiers']['final'])
    assert observation_wire(obs) == before
    assert science['input_before'] == science['input_after']
    assert science['rng_before'] != science['rng_after']
    guard_previews = sum(guard['after'] is not None for guard in science['guards'])
    placements = sum(root['move']['action'] == 'place' for root in science['roots'])
    exits = sum(guard['exit_legal_count'] is not None for guard in science['guards'])
    assert cost == dict(legal_enumerations=1+placements+guard_previews+exits,
                       previews=placements+guard_previews, exit_geometry_checks=exits,
                       roots=len(science['roots']))
    fresh = Random()
    fresh.setstate(Random(13).getstate())
    expected = fresh.choice(list(rng.tiers[0]))
    assert picked == expected and rng.getstate() == fresh.getstate()


@pytest.mark.parametrize('placed_count', [9, 10])
def test_reference_reserve_boundary_and_infeasible_supply(placed_count):
    catalog = invented_catalog(rain_edges=(D.WEST, D.EAST))
    board = corridor(catalog, catalog.rain[:placed_count])
    obs = invented_observation(catalog, [catalog.rain[placed_count]], board=board)
    picked, science, _ = checker(catalog).evaluate(obs, CountChoice())
    assert science['flags']['reserve_filter_active']
    protected = [i for i, root in enumerate(science['roots'])
                 if root['move']['action'] == 'place' and root['move']['hand_index'] == 0]
    assert protected and all(i not in science['tiers']['F'] for i in protected)
    assert all(science['guards'][i]['reason'] == 'reserve_filtered' for i in protected)
    assert picked.action is Action.COLLECT


def test_reference_quota_met_material_is_never_reserved_or_overridden():
    catalog = invented_catalog()
    collected = tuple(CollectedEquipment(catalog.rain[i], i+1) for i in range(3))
    obs = invented_observation(catalog, [catalog.rain[3]], collected=collected)
    picked, science, _ = checker(catalog).evaluate(obs, CountChoice())
    assert picked.action is Action.PLACE
    assert not science['flags']['reserve_filter_active']
    assert not science['flags']['closure_branch_selected']
    assert science['tiers']['T0'] == science['tiers']['T'] == science['tiers']['final']
    assert all(guard['reason'] == 'branch_not_active' for guard in science['guards'])


def test_reference_singleton_collect_and_genuinely_empty_legal_rng():
    catalog = invented_catalog(rain_edges=(), plain_edges=())
    ref = checker(catalog)
    singleton_rng = CountChoice()
    selected, science, cost = ref.evaluate(invented_observation(catalog), singleton_rng)
    assert selected == Move(Action.COLLECT, 0)
    assert singleton_rng.calls == 1 and science['tiers']['final'] == [0]
    assert cost == dict(legal_enumerations=1, previews=0, exit_geometry_checks=0, roots=1)
    empty_rng = CountChoice()
    empty = invented_observation(catalog, catalog.plain[:6])
    before = empty_rng.getstate()
    selected, science, cost = ref.evaluate(empty, empty_rng)
    assert selected is None and empty_rng.calls == 0 and empty_rng.getstate() == before
    assert all(not tier for tier in science['tiers'].values())
    assert science['roots'] == science['guards'] == []
    assert science['chosen'] is science['chosen_index'] is None
    assert science['rng_before'] == science['rng_after']
    assert not any(science['flags'].values())
    assert cost == dict(legal_enumerations=1, previews=0, exit_geometry_checks=0, roots=0)


def test_reference_closed_tunnel_override_is_forbidden_and_terminal_input_rejected():
    catalog = invented_catalog(plain_edges=(D.WEST,))
    board = Board()
    board.seed(catalog.start)
    for card in catalog.plain[:4]:
        root = placement_moves(board, (card,))[0]
        board.place(card, root.origin, root.quarter_turns)
    assert board.open_tunnels == 1
    obs = invented_observation(catalog, board=board)
    selected, science, _ = checker(catalog).evaluate(obs, CountChoice())
    assert selected.action is Action.COLLECT
    assert science['tiers']['C'] == []
    assert any(guard['reason'] == 'closed_tunnels' for guard in science['guards'])
    last = placement_moves(board, (catalog.plain[4],))[0]
    board.place(catalog.plain[4], last.origin, last.quarter_turns)
    terminal = invented_observation(catalog, board=board)
    with pytest.raises(ReferenceInputError, match='terminal'):
        checker(catalog).evaluate(terminal, CountChoice())


def test_reference_water_and_exit_guard_native_geometry():
    wet = invented_catalog(rain_water=True)
    _, science, _ = checker(wet).evaluate(invented_observation(wet), CountChoice())
    assert any(g['reason'] == 'visible_water_increased' for g in science['guards'])
    assert science['tiers']['C'] == []
    blocked = invented_catalog()
    blocked.exit = invented_card('invented-exit', (), exit=True)
    blocked.cards = (*blocked.cards[:-1], blocked.exit)
    _, science, _ = checker(blocked).evaluate(invented_observation(blocked), CountChoice())
    assert any(g['reason'] == 'no_exit_capacity' and g['exit_legal_count'] == 0
               for g in science['guards'])
    assert science['tiers']['C'] == []


def test_reference_mixed_primary_tier_never_runs_closure(monkeypatch):
    from bandido_alcatraz import strategy
    catalog = invented_catalog()
    # Isolated synthetic branch fixture: tied immediate scores, never a weight
    # change or candidate run. Real canonical-score assertions appear above.
    monkeypatch.setattr(strategy, 'score_move_no_draw', lambda *args: 10000)
    selected, science, _ = checker(catalog).evaluate(invented_observation(catalog), CountChoice())
    assert any(science['roots'][i]['move']['action'] == 'place' for i in science['tiers']['T'])
    assert any(science['roots'][i]['move']['action'] == 'collect' for i in science['tiers']['T'])
    assert science['tiers']['T0'] == science['tiers']['T'] == science['tiers']['final']
    assert science['tiers']['C'] == []
    assert all(g['reason'] == 'branch_not_active' for g in science['guards'])


def test_reference_reserve_filter_mediated_attribution(monkeypatch):
    from bandido_alcatraz import strategy
    catalog = invented_catalog(rain_edges=(D.WEST, D.EAST))
    # Nine spent raincoats leave exactly the three still required; the rope
    # endpoint has surplus and can independently close one of five tunnels.
    catalog.ropes[0] = replace(catalog.ropes[0], cells=(CellSpec(0, 0, frozenset((D.WEST,))),))
    catalog.cards = tuple([*catalog.rain, *catalog.ropes, *catalog.plain, catalog.exit])
    board = corridor(catalog, catalog.rain[:9])
    obs = invented_observation(catalog, [catalog.rain[9], catalog.ropes[0]], board=board)
    def controlled_score(obs, action, weights):
        return 20000 if action.action is Action.PLACE and action.hand_index == 0 else (10000 if action.action is Action.COLLECT else 100)
    monkeypatch.setattr(strategy, 'score_move_no_draw', controlled_score)
    selected, science, _ = checker(catalog).evaluate(obs, CountChoice())
    assert selected.action is Action.PLACE and selected.hand_index == 1
    assert science['flags'] == dict(reserve_filter_active=True,
        reserve_primary_tier_changed=True, closure_branch_selected=True,
        true_original_all_collect_crossover=False, reserve_filter_mediated_change=True)


def test_reference_limits_fail_explicitly_and_restore_profile(monkeypatch):
    import sys
    from bandido_alcatraz.quota_reserve_closure_reference import OperationLimits, ResourceExceeded
    catalog = invented_catalog()
    obs = invented_observation(catalog)
    ref = checker(catalog)
    prior = sys.getprofile()
    observed = []
    def profiler(frame, event, arg):
        if event == 'call':
            observed.append(frame.f_code.co_name)
    sys.setprofile(profiler)
    try:
        rng = CountChoice()
        before = rng.getstate()
        with pytest.raises(ResourceExceeded, match='legal_enumerations'):
            ref.evaluate(obs, rng, limits=OperationLimits(legal_enumerations=0))
        assert sys.getprofile() is profiler
        assert rng.calls == 0 and rng.getstate() == before
        assert 'legal_moves' in observed
        ref.evaluate(obs, rng)
        assert sys.getprofile() is profiler
    finally:
        sys.setprofile(prior)
    for kwargs in [dict(previews=-1), dict(exit_geometry_checks=True), dict(legal_enumerations=1.5)]:
        with pytest.raises(ValueError):
            OperationLimits(**kwargs)


def test_reference_impossible_empty_filter_and_canonical_failure_are_explicit(monkeypatch):
    from bandido_alcatraz import strategy
    from bandido_alcatraz.quota_reserve_closure_reference import IntegrityError
    catalog = invented_catalog(rain_edges=(D.WEST, D.EAST))
    board = corridor(catalog, catalog.rain[:9])
    obs = invented_observation(catalog, [catalog.rain[9]], board=board)
    place = next(action for action in obs.legal_moves() if action.action is Action.PLACE and action.hand_index == 0)
    monkeypatch.setattr(PlayerObservation, 'legal_moves', lambda self: [place])
    with pytest.raises(IntegrityError, match='emptied'):
        checker(catalog).evaluate(obs, CountChoice())
    def fail(*args):
        raise RuntimeError('deliberate synthetic primitive failure')
    monkeypatch.setattr(strategy, 'score_move_no_draw', fail)
    rng = CountChoice()
    with pytest.raises(RuntimeError, match='deliberate'):
        checker(catalog).evaluate(obs, rng)
    assert rng.calls == 0


def test_reference_obstruction_guard_uses_visible_existing_water():
    catalog = invented_catalog()
    catalog.start = replace(catalog.start, cells=(replace(catalog.start.cells[0], water=True),
                                                  catalog.start.cells[1]))
    _, science, _ = checker(catalog).evaluate(invented_observation(catalog), CountChoice())
    rejected = [guard for guard in science['guards'] if guard['reason'] == 'water_obstruction_increased']
    assert rejected and all(guard['exit_legal_count'] is None for guard in rejected)
    assert all(guard['after'][1] == 1 for guard in rejected)


def test_reference_trapped_water_guard_after_other_water_is_covered():
    catalog = invented_catalog()
    # Invented eight-cell START: two water cells each have three occupied
    # neighbors. The needed two-cell card covers the right water cell while
    # filling the left water cell's last neighbor. Total obstruction falls,
    # making the distinct trapped-water guard decisive.
    points = [(1, 1, (D.EAST,), True), (3, 1, (D.WEST,), True),
              (1, 0, (D.NORTH,), False), (1, 2, (D.SOUTH,), False),
              (0, 1, (D.WEST,), False), (3, 0, (), False),
              (3, 2, (), False), (4, 1, (), False)]
    catalog.start = CardDefinition('invented-start', tuple(
        CellSpec(x, y, frozenset(edges), water) for x, y, edges, water in points))
    catalog.rain[0] = replace(catalog.rain[0], cells=(
        CellSpec(0, 0, frozenset((D.WEST, D.EAST))),
        CellSpec(1, 0, frozenset((D.WEST,))),
    ))
    catalog.cards = tuple([*catalog.rain, *catalog.ropes, *catalog.plain, catalog.exit])
    obs = invented_observation(catalog)
    _, science, _ = checker(catalog).evaluate(obs, CountChoice())
    index = next(i for i, root in enumerate(science['roots'])
                 if root['move'] == dict(action='place', hand_index=0, origin=[2, 1], quarter_turns=0))
    assert science['guards'][index] == dict(eligible=False, reason='trapped_water_increased',
        after=[3, 1, 4, 1], exit_legal_count=None)


def test_reference_exit_already_placed_skips_capacity_lookup():
    catalog = invented_catalog()
    board = Board()
    board.seed(catalog.start)
    root = placement_moves(board, (catalog.exit,))[0]
    board.place(catalog.exit, root.origin, root.quarter_turns)
    obs = invented_observation(catalog, board=board)
    selected, science, cost = checker(catalog).evaluate(obs, CountChoice())
    assert selected.action is Action.PLACE
    assert science['flags']['closure_branch_selected']
    assert cost['exit_geometry_checks'] == 0
    assert all(guard['exit_legal_count'] is None for guard in science['guards'])


def test_reference_hidden_zone_changes_cannot_affect_public_decision():
    catalog = invented_catalog()
    obs = invented_observation(catalog)
    class ForbiddenHiddenZone:
        def __iter__(self):
            raise AssertionError('hidden cards must never be inspected')
        def __len__(self):
            raise AssertionError('hidden cards must never be counted')
        def __getitem__(self, item):
            raise AssertionError('hidden cards must never be read')
    state = GameState(board=obs.board, hand=list(obs.hand), draw_pile=[], setup=SOLO_EASY)
    first = checker(catalog).evaluate(state.observation(), Random(73))
    state.draw_pile = ForbiddenHiddenZone()
    state.face_down_set_aside = ForbiddenHiddenZone()
    second = checker(catalog).evaluate(state.observation(), Random(73))
    assert first == second


def test_reference_choose_is_stateless_and_equal_to_evaluate():
    catalog = invented_catalog()
    obs = invented_observation(catalog)
    ref = checker(catalog)
    first = ref.evaluate(obs, Random(731))
    assert ref.choose(obs, Random(731)) == first[0]
    assert ref.evaluate(obs, Random(731)) == first


def test_reference_every_operation_limit_can_fail_without_rng_consumption():
    from bandido_alcatraz.quota_reserve_closure_reference import OperationLimits, ResourceExceeded
    catalog = invented_catalog()
    for kwargs in [dict(previews=0), dict(exit_geometry_checks=0)]:
        rng = CountChoice()
        with pytest.raises(ResourceExceeded):
            checker(catalog).evaluate(invented_observation(catalog), rng, limits=OperationLimits(**kwargs))
        assert rng.calls == 0


def test_reference_invalid_rng_result_never_becomes_refresh():
    from bandido_alcatraz.quota_reserve_closure_reference import IntegrityError
    catalog = invented_catalog()
    class InvalidChoice(Random):
        def choice(self, options):
            return None
    with pytest.raises(IntegrityError, match='outside the final tier'):
        checker(catalog).evaluate(invented_observation(catalog), InvalidChoice(13))


def test_reference_native_profile_rejection_does_not_replace_active_hook(monkeypatch):
    from bandido_alcatraz import quota_reserve_closure_reference as reference
    native_profiler = object()
    replacements = []
    # Model CPython 3.11's native getprofile result without modifying pytest's
    # process-wide profiler or depending on the local Python minor version.
    isolated_sys = SimpleNamespace(getprofile=lambda: native_profiler,
                                   setprofile=replacements.append)
    monkeypatch.setattr(reference, 'sys', isolated_sys)
    catalog = invented_catalog()
    rng = CountChoice()
    before = rng.getstate()
    with pytest.raises(reference.IntegrityError, match='non-callable existing profile hook'):
        checker(catalog).evaluate(invented_observation(catalog), rng)
    assert replacements == []
    assert isolated_sys.getprofile() is native_profiler
    assert rng.calls == 0 and rng.getstate() == before


def test_reference_callable_profile_failure_restores_same_hook():
    import sys
    from bandido_alcatraz import moves
    prior = sys.getprofile()
    failures = []
    catalog = invented_catalog()
    obs = invented_observation(catalog)
    ref = checker(catalog)
    rng = CountChoice()
    def fails_once(frame, event, arg):
        if event == 'call' and frame.f_code is moves.legal_moves.__code__ and not failures:
            failures.append('forwarded')
            raise RuntimeError('synthetic prior profiler failure')
    sys.setprofile(fails_once)
    try:
        with pytest.raises(RuntimeError, match='synthetic prior profiler failure'):
            ref.evaluate(obs, rng)
        assert failures == ['forwarded']
        assert sys.getprofile() is fails_once
        assert rng.calls == 0
    finally:
        sys.setprofile(prior)


def test_reference_callable_failure_during_hook_install_restores_same_hook():
    import sys
    prior = sys.getprofile()
    catalog = invented_catalog()
    obs = invented_observation(catalog)
    ref = checker(catalog)
    rng = CountChoice()
    failures = []
    def fails_once_on_install(frame, event, arg):
        if (event == 'c_return' and arg is sys.setprofile
                and sys.getprofile() is not fails_once_on_install and not failures):
            failures.append('installation')
            raise RuntimeError('synthetic hook installation failure')
    sys.setprofile(fails_once_on_install)
    try:
        with pytest.raises(RuntimeError, match='synthetic hook installation failure'):
            ref.evaluate(obs, rng)
        assert failures == ['installation']
        assert sys.getprofile() is fails_once_on_install
        assert rng.calls == 0
    finally:
        sys.setprofile(prior)


def test_reference_real_native_cprofile_hook_is_preserved_when_exposed(monkeypatch):
    import cProfile
    import sys
    from bandido_alcatraz import quota_reserve_closure_reference as reference
    previous = sys.getprofile()
    if previous is not None:
        pytest.skip('real native-profiler regression requires an unused profile hook')
    catalog = invented_catalog()
    obs = invented_observation(catalog)
    ref = checker(catalog)
    rng = CountChoice()
    rng_before = rng.getstate()
    replacements = []
    def replace_hook(hook):
        replacements.append(hook)
        sys.setprofile(hook)
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        native = sys.getprofile()
        if native is None or callable(native):
            pytest.skip('this runtime does not expose cProfile as a non-callable profile hook')
        # The getter reads the actual active cProfile hook; only the reference's
        # setter is observed, leaving the process-wide sys module untouched.
        monkeypatch.setattr(reference, 'sys', SimpleNamespace(
            getprofile=sys.getprofile, setprofile=replace_hook))
        with pytest.raises(reference.IntegrityError, match='non-callable existing profile hook'):
            ref.evaluate(obs, rng)
        assert replacements == []
        assert sys.getprofile() is native
        assert rng.calls == 0 and rng.getstate() == rng_before
    finally:
        profiler.disable()
        # Also clean up if a regression installed another hook before failing.
        if sys.getprofile() is not previous:
            sys.setprofile(previous)


def test_reference_retained_entry_exception_restores_hook_before_traceback_cleanup():
    import sys
    previous = sys.getprofile()
    catalog = invented_catalog()
    obs = invented_observation(catalog)
    ref = checker(catalog)
    rng = CountChoice()
    problem = RuntimeError('synthetic retained context-entry failure')
    failures = []
    def prior(frame, event, arg):
        if (event == 'return' and frame.f_code.co_name == '__enter__'
                and sys.getprofile() is not prior and not failures):
            failures.append('context-entry-return')
            raise problem
    sys.setprofile(prior)
    try:
        with pytest.raises(RuntimeError) as retained:
            ref.evaluate(obs, rng)
        # Both references intentionally retain the exception and its traceback.
        # No generator cleanup via exception disposal or GC may be necessary.
        assert retained.value is problem
        assert problem.__traceback__ is not None
        assert failures == ['context-entry-return']
        assert sys.getprofile() is prior
        assert rng.calls == 0
    finally:
        sys.setprofile(previous)
