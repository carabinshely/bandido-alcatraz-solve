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


def test_discard_excess_prefers_collecting_branching_excess_equipment() -> None:
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

    move = DiscardExcessV2Policy().choose(state, Random(1))

    assert move is not None
    assert move.action is Action.COLLECT
    assert state.hand[move.hand_index].card_id == "excess-branch-coat"


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
