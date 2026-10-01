from random import Random

from bandido_alcatraz.board import Board
from bandido_alcatraz.game import GameState
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action
from bandido_alcatraz.policies import (
    CombinedV2Policy,
    CombinedV3Policy,
    BoundedMergeV4Policy,
    DiscardExcessV2Policy,
    GeometryAwareV1Policy,
    GreedyV0Policy,
    MergeAwareV3Policy,
    VisibleRepairReserveV5Policy,
    WaterFirstV2Policy,
    WaterSpaceV3Policy,
)


def card(
    card_id: str,
    edges: set[Direction],
    *,
    material: Material | None = None,
    is_exit: bool = False,
) -> CardDefinition:
    return CardDefinition(
        card_id,
        (CellSpec(0, 0, frozenset(edges)),),
        material,
        is_exit,
    )


def state_with_one_open(hand: list[CardDefinition], *, coats: int = 0, ropes: int = 0):
    board = Board()
    board.seed(card("start", {Direction.EAST}))
    return GameState(
        board=board,
        draw_pile=[],
        hand=hand,
        raincoats=coats,
        ropes=ropes,
    )


def test_greedy_collects_still_needed_equipment() -> None:
    state = state_with_one_open(
        [
            card("end", {Direction.WEST}),
            card(
                "coat",
                {Direction.WEST},
                material=Material.RAINCOAT,
            ),
        ],
        coats=2,
        ropes=2,
    )

    move = GreedyV0Policy().choose(state, Random(1))

    assert move is not None
    assert move.action is Action.COLLECT
    assert state.hand[move.hand_index].material is Material.RAINCOAT


def test_greedy_avoids_closing_last_tunnel_without_exit() -> None:
    state = state_with_one_open(
        [
            card("end", {Direction.WEST}),
            card("straight", {Direction.WEST, Direction.EAST}),
        ],
        coats=3,
        ropes=2,
    )

    move = GreedyV0Policy().choose(state, Random(1))

    assert move is not None
    assert move.action is Action.PLACE
    assert state.hand[move.hand_index].card_id == "straight"


def test_greedy_prefers_winning_exit() -> None:
    state = state_with_one_open(
        [card("exit", {Direction.WEST}, is_exit=True)],
        coats=3,
        ropes=2,
    )

    move = GreedyV0Policy().choose(state, Random(1))
    assert move is not None

    state.apply(move)
    assert state.won


def test_geometry_aware_collects_higher_degree_equipment_first() -> None:
    state = state_with_one_open(
        [
            card(
                "closure-rope",
                {Direction.WEST},
                material=Material.ROPE,
            ),
            card(
                "branch-rope",
                {
                    Direction.WEST,
                    Direction.NORTH,
                    Direction.SOUTH,
                },
                material=Material.ROPE,
            ),
        ],
        coats=3,
        ropes=1,
    )

    move = GeometryAwareV1Policy().choose(state, Random(1))

    assert move is not None
    assert move.action is Action.COLLECT
    assert state.hand[move.hand_index].card_id == "branch-rope"


def test_geometry_aware_defers_one_port_collection_when_safe_move_exists() -> None:
    state = state_with_one_open(
        [
            card(
                "closure-rope",
                {Direction.WEST},
                material=Material.ROPE,
            ),
            card(
                "straight",
                {Direction.WEST, Direction.EAST},
            ),
        ],
        coats=3,
        ropes=1,
    )

    move = GeometryAwareV1Policy().choose(state, Random(1))

    assert move is not None
    assert move.action is Action.PLACE
    assert state.hand[move.hand_index].card_id == "straight"


def test_geometry_aware_still_collects_one_port_when_alternative_seals_board() -> None:
    state = state_with_one_open(
        [
            card(
                "closure-rope",
                {Direction.WEST},
                material=Material.ROPE,
            ),
        ],
        coats=3,
        ropes=1,
    )

    move = GeometryAwareV1Policy().choose(state, Random(1))

    assert move is not None
    assert move.action is Action.COLLECT


def test_discard_excess_weights_cannot_enable_illegal_excess_collection() -> None:
    state = state_with_one_open(
        [
            card(
                "excess-branch-coat",
                {
                    Direction.WEST,
                    Direction.NORTH,
                    Direction.SOUTH,
                },
                material=Material.RAINCOAT,
            ),
            card(
                "straight",
                {Direction.WEST, Direction.EAST},
            ),
        ],
        coats=3,
        ropes=2,
    )

    policy = DiscardExcessV2Policy()
    # Keep the historic policy weights, but legality now removes excess COLLECT.
    assert policy.weights.collect_excess == 0
    assert all(move.action is Action.PLACE for move in state.legal_moves())
    move = policy.choose(state, Random(1))

    assert move is not None
    assert move in state.legal_moves()
    assert move.action is Action.PLACE
    assert state.hand[move.hand_index].card_id == "straight"


def test_discard_excess_still_places_useful_closure_equipment() -> None:
    board = Board()
    board.seed(
        card(
            "start",
            {Direction.EAST, Direction.NORTH},
        )
    )
    state = GameState(
        board=board,
        draw_pile=[],
        hand=[
            card(
                "excess-end-coat",
                {Direction.WEST},
                material=Material.RAINCOAT,
            ),
            card(
                "straight",
                {Direction.WEST, Direction.EAST},
            ),
        ],
        raincoats=3,
        ropes=2,
    )

    move = DiscardExcessV2Policy().choose(state, Random(1))

    assert move is not None
    assert move.action is Action.PLACE
    assert state.hand[move.hand_index].card_id == "excess-end-coat"


def test_v2_policy_weights_are_isolated() -> None:
    discard = DiscardExcessV2Policy().weights
    water = WaterFirstV2Policy().weights
    combined = CombinedV2Policy().weights
    base = GreedyV0Policy().weights

    assert discard.collect_excess == 0
    assert discard.delta_visible_water == base.delta_visible_water

    assert water.collect_excess == base.collect_excess
    assert water.delta_visible_water == 20_000

    assert combined.collect_excess == 0
    assert combined.delta_visible_water == 20_000


def test_v3_policy_weights_are_isolated_from_combined_v2() -> None:
    v2 = CombinedV2Policy().weights
    merge = MergeAwareV3Policy().weights
    water_space = WaterSpaceV3Policy().weights
    combined = CombinedV3Policy().weights

    assert merge.collect_excess == v2.collect_excess
    assert merge.delta_visible_water == v2.delta_visible_water
    assert merge.delta_merge_opportunities == 500
    assert merge.delta_water_obstruction == 0
    assert merge.new_trapped_water == 0

    assert water_space.delta_merge_opportunities == 0
    assert water_space.delta_water_obstruction == 1_000
    assert water_space.new_trapped_water == -100_000

    assert combined.delta_merge_opportunities == 500
    assert combined.delta_water_obstruction == 1_000
    assert combined.new_trapped_water == -100_000


def test_bounded_merge_v4_only_adds_bounded_setup_reward() -> None:
    base = WaterSpaceV3Policy().weights
    v4 = BoundedMergeV4Policy(setup_weight=500).weights

    assert v4.collect_excess == base.collect_excess
    assert v4.delta_visible_water == base.delta_visible_water
    assert v4.delta_water_obstruction == base.delta_water_obstruction
    assert v4.new_trapped_water == base.new_trapped_water
    assert v4.delta_merge_opportunities == 0
    assert v4.bounded_merge_setup_gain == 500


def synthetic_exit_card() -> CardDefinition:
    return CardDefinition(
        "exit",
        (
            CellSpec(
                0,
                0,
                frozenset({Direction.NORTH, Direction.SOUTH}),
            ),
            CellSpec(0, 1, frozenset({Direction.NORTH})),
        ),
        is_exit=True,
    )


def capacity_killer_card() -> CardDefinition:
    return CardDefinition(
        "capacity-killer",
        (
            CellSpec(0, 0, frozenset({Direction.NORTH})),
            CellSpec(1, 0, frozenset({Direction.NORTH})),
        ),
    )


def visible_repair_card() -> CardDefinition:
    return card(
        "repair",
        {Direction.NORTH, Direction.EAST, Direction.SOUTH},
    )


def blocked_card(card_id: str = "blocked") -> CardDefinition:
    return card(card_id, set())


def state_with_two_open_for_v5(
    hand: list[CardDefinition],
    *,
    exit_seen: bool = False,
    exit_placed: bool = False,
    coats: int = 0,
    ropes: int = 0,
) -> GameState:
    board = Board()
    board.seed(card("start-two-open", {Direction.NORTH, Direction.EAST}))
    return GameState(
        board=board,
        draw_pile=[],
        hand=hand,
        raincoats=coats,
        ropes=ropes,
        exit_seen=exit_seen,
        exit_placed=exit_placed,
    )


def state_with_one_north_open_for_v5(
    hand: list[CardDefinition],
) -> GameState:
    board = Board()
    board.seed(card("start-one-open", {Direction.NORTH}))
    return GameState(
        board=board,
        draw_pile=[],
        hand=hand,
    )


def test_v5_lexicographically_excludes_higher_scoring_unsafe_move() -> None:
    exit_card = synthetic_exit_card()
    preserving = card("preserving", {Direction.NORTH})
    state = state_with_two_open_for_v5(
        [preserving, capacity_killer_card(), blocked_card()]
    )

    v4_move = BoundedMergeV4Policy(setup_weight=250).choose(
        state,
        Random(3),
    )
    v5_move = VisibleRepairReserveV5Policy(exit_card=exit_card).choose(
        state,
        Random(3),
    )

    assert v4_move is not None
    assert v5_move is not None
    assert state.hand[v4_move.hand_index].card_id == "capacity-killer"
    assert state.hand[v5_move.hand_index].card_id == "preserving"


def test_v5_preserves_v4_scoring_among_multiple_normal_moves() -> None:
    exit_card = synthetic_exit_card()
    higher = card("higher-normal", {Direction.NORTH})
    lower = visible_repair_card()
    state = state_with_two_open_for_v5(
        [higher, lower, blocked_card()]
    )

    v4_move = BoundedMergeV4Policy(setup_weight=250).choose(
        state,
        Random(5),
    )
    v5_move = VisibleRepairReserveV5Policy(exit_card=exit_card).choose(
        state,
        Random(5),
    )

    assert v5_move == v4_move
    assert v5_move is not None
    assert state.hand[v5_move.hand_index].card_id == "higher-normal"


def test_v5_preserves_existing_rng_tie_semantics_for_normal_moves() -> None:
    exit_card = synthetic_exit_card()
    state = state_with_two_open_for_v5(
        [
            card("normal-a", {Direction.NORTH}),
            card("normal-b", {Direction.NORTH}),
            blocked_card(),
        ]
    )

    v4_move = BoundedMergeV4Policy(setup_weight=250).choose(
        state,
        Random(17),
    )
    v5_move = VisibleRepairReserveV5Policy(exit_card=exit_card).choose(
        state,
        Random(17),
    )

    assert v5_move == v4_move


def test_v5_all_unsafe_moves_fall_back_to_full_v4_selection() -> None:
    exit_card = synthetic_exit_card()
    state = state_with_one_north_open_for_v5(
        [
            card("unsafe-a", {Direction.NORTH}),
            card("unsafe-b", {Direction.NORTH}),
            blocked_card(),
        ]
    )

    v4_move = BoundedMergeV4Policy(setup_weight=250).choose(
        state,
        Random(19),
    )
    v5_move = VisibleRepairReserveV5Policy(exit_card=exit_card).choose(
        state,
        Random(19),
    )

    assert v4_move is not None
    assert v5_move == v4_move


def test_v5_single_unsafe_move_falls_back_and_selects_it() -> None:
    exit_card = synthetic_exit_card()
    state = state_with_one_north_open_for_v5(
        [
            card("only-unsafe", {Direction.NORTH}),
            blocked_card("one"),
            blocked_card("two"),
        ]
    )

    v5_move = VisibleRepairReserveV5Policy(exit_card=exit_card).choose(
        state,
        Random(23),
    )

    assert v5_move is not None
    assert state.hand[v5_move.hand_index].card_id == "only-unsafe"


def test_v5_capacity_already_zero_is_v4_equivalent() -> None:
    exit_card = synthetic_exit_card()
    board = Board()
    board.seed(blocked_card("sealed-start"))
    collectable = card(
        "rope",
        set(),
        material=Material.ROPE,
    )
    state = GameState(
        board=board,
        draw_pile=[],
        hand=[collectable, blocked_card("one"), blocked_card("two")],
    )

    v4_move = BoundedMergeV4Policy(setup_weight=250).choose(
        state,
        Random(29),
    )
    v5_move = VisibleRepairReserveV5Policy(exit_card=exit_card).choose(
        state,
        Random(29),
    )

    assert v5_move == v4_move
    assert v5_move is not None
    assert v5_move.action is Action.COLLECT


def test_v5_exit_seen_is_v4_equivalent() -> None:
    exit_card = synthetic_exit_card()
    state = state_with_two_open_for_v5(
        [
            card("preserving", {Direction.NORTH}),
            capacity_killer_card(),
            blocked_card(),
        ],
        exit_seen=True,
    )

    v4_move = BoundedMergeV4Policy(setup_weight=250).choose(
        state,
        Random(31),
    )
    v5_move = VisibleRepairReserveV5Policy(exit_card=exit_card).choose(
        state,
        Random(31),
    )

    assert v5_move == v4_move


def test_v5_exit_placed_is_v4_equivalent() -> None:
    exit_card = synthetic_exit_card()
    state = state_with_two_open_for_v5(
        [
            card("preserving", {Direction.NORTH}),
            capacity_killer_card(),
            blocked_card(),
        ],
        exit_placed=True,
    )
    assert state.exit_seen

    v4_move = BoundedMergeV4Policy(setup_weight=250).choose(
        state,
        Random(37),
    )
    v5_move = VisibleRepairReserveV5Policy(exit_card=exit_card).choose(
        state,
        Random(37),
    )

    assert v5_move == v4_move


def test_v5_capacity_kill_with_visible_repair_reserve_remains_normal() -> None:
    exit_card = synthetic_exit_card()
    state = state_with_two_open_for_v5(
        [
            capacity_killer_card(),
            visible_repair_card(),
            blocked_card(),
        ]
    )

    v4_move = BoundedMergeV4Policy(setup_weight=250).choose(
        state,
        Random(41),
    )
    v5_move = VisibleRepairReserveV5Policy(exit_card=exit_card).choose(
        state,
        Random(41),
    )

    assert v5_move == v4_move
    assert v5_move is not None
    assert state.hand[v5_move.hand_index].card_id == "capacity-killer"


def test_v5_capacity_preserving_move_remains_normal() -> None:
    exit_card = synthetic_exit_card()
    state = state_with_two_open_for_v5(
        [
            card("preserving", {Direction.NORTH}),
            blocked_card("one"),
            blocked_card("two"),
        ]
    )

    v4_move = BoundedMergeV4Policy(setup_weight=250).choose(
        state,
        Random(43),
    )
    v5_move = VisibleRepairReserveV5Policy(exit_card=exit_card).choose(
        state,
        Random(43),
    )

    assert v5_move == v4_move
    assert v5_move is not None
    assert state.hand[v5_move.hand_index].card_id == "preserving"


def test_v5_collection_remains_normal() -> None:
    exit_card = synthetic_exit_card()
    rope = card(
        "needed-rope",
        set(),
        material=Material.ROPE,
    )
    state = state_with_two_open_for_v5(
        [rope, card("preserving", {Direction.NORTH}), blocked_card()],
        coats=3,
        ropes=1,
    )

    v5_move = VisibleRepairReserveV5Policy(exit_card=exit_card).choose(
        state,
        Random(47),
    )

    assert v5_move is not None
    assert v5_move.action is Action.COLLECT
    assert state.hand[v5_move.hand_index].card_id == "needed-rope"


def test_v5_exit_placement_remains_v4_equivalent() -> None:
    exit_card = synthetic_exit_card()
    state = state_with_one_north_open_for_v5(
        [exit_card, blocked_card("one"), blocked_card("two")]
    )
    state.raincoats = 3
    state.ropes = 2
    assert state.exit_seen

    v4_move = BoundedMergeV4Policy(setup_weight=250).choose(
        state,
        Random(53),
    )
    v5_move = VisibleRepairReserveV5Policy(exit_card=exit_card).choose(
        state,
        Random(53),
    )

    assert v5_move == v4_move
    assert v5_move is not None
    assert state.hand[v5_move.hand_index].is_exit


def test_v5_weights_are_exactly_v4_250_weights() -> None:
    exit_card = synthetic_exit_card()

    assert (
        VisibleRepairReserveV5Policy(exit_card=exit_card).weights
        == BoundedMergeV4Policy(setup_weight=250).weights
    )
