from random import Random

from bandido_alcatraz.board import Board
from bandido_alcatraz.game import GameState
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action
from bandido_alcatraz.strategy import (
    PolicyWeights,
    WeightedGreedyPolicy,
    move_features,
    score_features,
)


def card(
    card_id: str,
    edges: set[Direction],
    *,
    material: Material | None = None,
    is_exit: bool = False,
    water: bool = False,
) -> CardDefinition:
    return CardDefinition(
        card_id,
        (CellSpec(0, 0, frozenset(edges), water=water),),
        material,
        is_exit,
    )


def state_with_one_open(
    hand: list[CardDefinition], *, coats: int = 0, ropes: int = 0
) -> GameState:
    board = Board()
    board.seed(card("start", {Direction.EAST}))
    return GameState(
        board=board,
        draw_pile=[],
        hand=hand,
        raincoats=coats,
        ropes=ropes,
    )


def test_move_features_detect_needed_equipment() -> None:
    state = state_with_one_open(
        [card("coat", {Direction.WEST}, material=Material.RAINCOAT)],
        coats=2,
        ropes=2,
    )
    move = next(move for move in state.legal_moves() if move.action is Action.COLLECT)

    features = move_features(state, move)

    assert features.collect_needed == 1
    assert features.collect_excess == 0


def test_move_features_detect_premature_seal() -> None:
    state = state_with_one_open([card("end", {Direction.WEST})], coats=3, ropes=2)
    move = next(move for move in state.legal_moves() if move.action is Action.PLACE)

    features = move_features(state, move)

    assert features.closes_last_without_win == 1
    assert features.delta_open_tunnels == 1


def test_water_reduction_has_positive_default_value() -> None:
    board = Board()
    board.seed(card("water", {Direction.EAST, Direction.WEST}, water=True))
    cover = CardDefinition(
        "cover",
        (
            CellSpec(0, 0, frozenset({Direction.EAST, Direction.WEST})),
            CellSpec(1, 0, frozenset({Direction.WEST})),
        ),
    )
    state = GameState(board=board, draw_pile=[], hand=[cover])
    move = next(
        move
        for move in state.legal_moves()
        if move.action is Action.PLACE and move.origin == (0, 0)
    )

    features = move_features(state, move)

    assert features.delta_visible_water == 1
    assert PolicyWeights().delta_visible_water > 0
    assert score_features(features, PolicyWeights()) > 0


def test_default_weighted_policy_prefers_winning_exit() -> None:
    state = state_with_one_open(
        [
            card("exit", {Direction.WEST}, is_exit=True),
            card("straight", {Direction.WEST, Direction.EAST}),
        ],
        coats=3,
        ropes=2,
    )

    move = WeightedGreedyPolicy().choose(state, Random(1))

    assert move is not None
    assert state.hand[move.hand_index].is_exit


def test_weights_can_change_choice_without_changing_rules() -> None:
    state = state_with_one_open(
        [
            card("coat", {Direction.WEST}, material=Material.RAINCOAT),
            card("straight", {Direction.WEST, Direction.EAST}),
        ],
        coats=2,
        ropes=2,
    )

    default_move = WeightedGreedyPolicy().choose(state, Random(1))
    no_collect_move = WeightedGreedyPolicy(
        PolicyWeights(collect_needed=-10_000)
    ).choose(state, Random(1))

    assert default_move is not None
    assert no_collect_move is not None
    assert default_move.action is Action.COLLECT
    assert no_collect_move.action is Action.PLACE
