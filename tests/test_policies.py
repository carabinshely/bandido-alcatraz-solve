from random import Random

from bandido_alcatraz.board import Board
from bandido_alcatraz.game import GameState
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action
from bandido_alcatraz.policies import GeometryAwareV1Policy, GreedyV0Policy


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
