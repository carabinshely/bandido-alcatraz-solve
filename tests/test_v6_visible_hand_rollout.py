from __future__ import annotations

import inspect

import pytest

from bandido_alcatraz.board import Board
from bandido_alcatraz.game import GameState
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.policies import (
    BoundedMergeV4Policy,
    VisibleHandTwoActionV6Policy,
    VisibleRepairReserveV5Policy,
)
from bandido_alcatraz.strategy import (
    best_two_action_first_moves,
    move_features,
    move_features_no_draw,
    preview_move_without_draw,
    score_move_no_draw,
    two_action_sequence_score,
)


V4_WEIGHTS = BoundedMergeV4Policy(setup_weight=250).weights


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


def blocked(card_id: str) -> CardDefinition:
    return card(card_id, set())


def one_open_state(
    hand: list[CardDefinition],
    *,
    coats: int = 0,
    ropes: int = 0,
    draw_pile=None,
) -> GameState:
    board = Board()
    board.seed(card("start", {Direction.EAST}))
    return GameState(
        board=board,
        draw_pile=[] if draw_pile is None else draw_pile,
        hand=hand,
        raincoats=coats,
        ropes=ropes,
    )


def one_open_place(state: GameState, hand_index: int = 0) -> Move:
    return next(
        move
        for move in state.legal_moves()
        if move.action is Action.PLACE and move.hand_index == hand_index
    )


def collect_move(state: GameState, hand_index: int) -> Move:
    return next(
        move
        for move in state.legal_moves()
        if move.action is Action.COLLECT and move.hand_index == hand_index
    )


class UnreadableDrawPile:
    def _fail(self, *args, **kwargs):
        raise AssertionError("hidden draw pile was accessed")

    __iter__ = _fail
    __len__ = _fail
    __getitem__ = _fail
    __bool__ = _fail
    pop = _fail
    copy = _fail


class CountingRng:
    def __init__(self) -> None:
        self.choice_calls = 0
        self.choice_inputs: list[tuple[Move, ...]] = []

    def choice(self, values):
        self.choice_calls += 1
        snapshot = tuple(values)
        self.choice_inputs.append(snapshot)
        return snapshot[0]


def test_no_draw_preview_does_not_touch_hidden_draw_sentinel() -> None:
    state = one_open_state(
        [card("end", {Direction.WEST}), blocked("a"), blocked("b")],
    )
    state.draw_pile = UnreadableDrawPile()
    move = one_open_place(state)

    preview = preview_move_without_draw(state, move)

    assert preview.successor.board.open_tunnels == 0
    assert preview.successor.draw_pile == []
    assert [item.card.card_id for item in preview.retained_visible_cards] == ["a", "b"]


def test_no_draw_feature_scoring_does_not_touch_hidden_draw_sentinel() -> None:
    state = one_open_state(
        [card("end", {Direction.WEST}), blocked("a"), blocked("b")],
    )
    state.draw_pile = UnreadableDrawPile()
    move = one_open_place(state)

    features = move_features_no_draw(state, move)
    score = score_move_no_draw(state, move, V4_WEIGHTS)

    assert features.delta_open_tunnels == 1
    assert score == sum(
        getattr(features, field) * getattr(V4_WEIGHTS, field)
        for field in features.__dataclass_fields__
    )


def test_v6_choose_does_not_touch_hidden_draw_sentinel() -> None:
    state = one_open_state(
        [card("end", {Direction.WEST}), blocked("a"), blocked("b")],
    )
    state.draw_pile = UnreadableDrawPile()
    rng = CountingRng()

    move = VisibleHandTwoActionV6Policy().choose(state, rng)

    assert move == one_open_place(state)
    assert rng.choice_calls == 1


@pytest.mark.parametrize(
    ("consumed_index", "expected_original_indexes", "expected_ids"),
    [
        (0, [1, 2], ["b", "c"]),
        (1, [0, 2], ["a", "c"]),
        (2, [0, 1], ["a", "b"]),
    ],
)
def test_no_draw_preview_remaps_all_original_hand_indexes(
    consumed_index: int,
    expected_original_indexes: list[int],
    expected_ids: list[str],
) -> None:
    hand = [
        card("a", set(), material=Material.RAINCOAT),
        card("b", set(), material=Material.ROPE),
        card("c", set(), material=Material.RAINCOAT),
    ]
    state = one_open_state(hand, coats=3, ropes=2)
    move = collect_move(state, consumed_index)

    preview = preview_move_without_draw(state, move)

    assert [item.original_hand_index for item in preview.retained_visible_cards] == (
        expected_original_indexes
    )
    assert [item.preview_hand_index for item in preview.retained_visible_cards] == [0, 1]
    assert [item.card.card_id for item in preview.retained_visible_cards] == expected_ids
    assert [item.card_id for item in preview.successor.hand] == expected_ids


def assert_feature_equivalence(
    state: GameState,
    move: Move,
):
    legacy = move_features(state, move)
    pure = move_features_no_draw(state, move)
    assert pure == legacy
    return pure


def test_feature_equivalence_needed_and_excess_collect() -> None:
    needed_state = one_open_state(
        [card("coat", set(), material=Material.RAINCOAT)],
        coats=2,
        ropes=2,
    )
    needed = assert_feature_equivalence(
        needed_state,
        collect_move(needed_state, 0),
    )
    assert needed.collect_needed == 1
    assert needed.collect_excess == 0

    excess_state = one_open_state(
        [card("rope", set(), material=Material.ROPE)],
        coats=3,
        ropes=2,
    )
    excess = assert_feature_equivalence(
        excess_state,
        collect_move(excess_state, 0),
    )
    assert excess.collect_needed == 0
    assert excess.collect_excess == 1


def test_feature_equivalence_water_reduction() -> None:
    board = Board()
    board.seed(card("water", {Direction.EAST, Direction.WEST}, water=True))
    cover = CardDefinition(
        "cover",
        (
            CellSpec(0, 0, frozenset({Direction.EAST, Direction.WEST})),
            CellSpec(1, 0, frozenset({Direction.WEST})),
        ),
    )
    state = GameState(board=board, draw_pile=[blocked("hidden")], hand=[cover])
    move = next(
        move
        for move in state.legal_moves()
        if move.action is Action.PLACE and move.origin == (0, 0)
    )

    features = assert_feature_equivalence(state, move)

    assert features.delta_visible_water == 1


def test_feature_equivalence_water_obstruction_trap_and_close() -> None:
    board = Board()
    board.seed(
        CardDefinition(
            "almost-trapped-water",
            (
                CellSpec(0, 0, frozenset({Direction.EAST}), water=True),
                CellSpec(0, -1, frozenset()),
                CellSpec(0, 1, frozenset()),
                CellSpec(-1, 0, frozenset()),
            ),
        )
    )
    state = GameState(
        board=board,
        draw_pile=[blocked("hidden")],
        hand=[card("east-closure", {Direction.WEST})],
    )
    move = next(move for move in state.legal_moves() if move.action is Action.PLACE)

    features = assert_feature_equivalence(state, move)

    assert features.delta_open_tunnels == 1
    assert features.delta_water_obstruction == -1
    assert features.new_trapped_water == 1
    assert features.closes_last_without_win == 1


def test_feature_equivalence_bounded_merge_setup_gain() -> None:
    board = Board()
    board.seed(card("two-open", {Direction.NORTH, Direction.EAST}))
    setup = CardDefinition(
        "merge-setup",
        (
            CellSpec(0, 0, frozenset({Direction.SOUTH, Direction.EAST})),
            CellSpec(1, 0, frozenset({Direction.WEST, Direction.SOUTH})),
        ),
    )
    state = GameState(
        board=board,
        draw_pile=[blocked("hidden")],
        hand=[setup],
    )
    move = next(
        move
        for move in state.legal_moves()
        if move.action is Action.PLACE and move.origin == (0, -1)
    )

    features = assert_feature_equivalence(state, move)

    assert features.bounded_merge_setup_gain == 1


def test_feature_equivalence_exit_ready_win() -> None:
    exit_card = card("exit-ready", {Direction.WEST}, is_exit=True)
    state = one_open_state(
        [exit_card],
        coats=3,
        ropes=2,
        draw_pile=[blocked("hidden")],
    )
    move = one_open_place(state)

    features = assert_feature_equivalence(state, move)

    assert features.places_exit_ready == 1
    assert features.places_exit_early == 0
    assert features.wins == 1
    assert features.closes_last_without_win == 0


def test_feature_equivalence_exit_early_close_without_win() -> None:
    exit_card = card("exit-early", {Direction.WEST}, is_exit=True)
    state = one_open_state(
        [exit_card],
        coats=2,
        ropes=2,
        draw_pile=[blocked("hidden")],
    )
    move = one_open_place(state)

    features = assert_feature_equivalence(state, move)

    assert features.places_exit_ready == 0
    assert features.places_exit_early == 1
    assert features.wins == 0
    assert features.closes_last_without_win == 1


def hidden_variant_state(hidden: CardDefinition) -> GameState:
    return one_open_state(
        [
            card("coat", set(), material=Material.RAINCOAT),
            card("straight", {Direction.WEST, Direction.EAST}),
            blocked("blocked"),
        ],
        coats=2,
        ropes=2,
        draw_pile=[hidden],
    )


def test_hidden_replacement_identity_does_not_change_features_scores_or_candidates() -> None:
    ordinary_state = hidden_variant_state(blocked("ordinary-hidden"))
    exit_state = hidden_variant_state(
        card("hidden-exit", {Direction.WEST}, is_exit=True)
    )
    ordinary_first = collect_move(ordinary_state, 0)
    exit_first = collect_move(exit_state, 0)

    assert move_features_no_draw(ordinary_state, ordinary_first) == (
        move_features_no_draw(exit_state, exit_first)
    )
    assert two_action_sequence_score(ordinary_state, ordinary_first, V4_WEIGHTS) == (
        two_action_sequence_score(exit_state, exit_first, V4_WEIGHTS)
    )
    assert best_two_action_first_moves(ordinary_state, V4_WEIGHTS) == (
        best_two_action_first_moves(exit_state, V4_WEIGHTS)
    )


def test_preview_place_collect_and_exit_first_action_semantics() -> None:
    place_state = one_open_state(
        [card("straight", {Direction.WEST, Direction.EAST}), blocked("a"), blocked("b")]
    )
    place = one_open_place(place_state)
    place_preview = preview_move_without_draw(place_state, place)
    assert place_preview.successor.board.open_tunnels == 1
    assert place_preview.successor.turns == place_state.turns + 1

    collect_state = one_open_state(
        [
            card("coat", set(), material=Material.RAINCOAT),
            card("rope", set(), material=Material.ROPE),
            blocked("x"),
        ],
        coats=2,
        ropes=1,
    )
    coat_preview = preview_move_without_draw(
        collect_state,
        collect_move(collect_state, 0),
    )
    rope_preview = preview_move_without_draw(
        collect_state,
        collect_move(collect_state, 1),
    )
    assert coat_preview.successor.raincoats == 3
    assert coat_preview.successor.ropes == 1
    assert rope_preview.successor.raincoats == 2
    assert rope_preview.successor.ropes == 2

    exit_state = one_open_state(
        [card("exit", {Direction.WEST}, is_exit=True), blocked("a"), blocked("b")],
        coats=3,
        ropes=2,
    )
    exit_preview = preview_move_without_draw(exit_state, one_open_place(exit_state))
    assert exit_preview.successor.exit_placed
    assert exit_preview.successor.exit_seen
    assert exit_preview.successor.won


def test_first_collect_can_switch_retained_exit_from_early_to_ready() -> None:
    coat = card("coat", set(), material=Material.RAINCOAT)
    exit_card = card("exit", {Direction.WEST}, is_exit=True)
    state = one_open_state(
        [coat, exit_card, blocked("x")],
        coats=2,
        ropes=2,
    )
    exit_before = one_open_place(state, 1)
    before_features = move_features_no_draw(state, exit_before)
    assert before_features.places_exit_early == 1

    preview = preview_move_without_draw(state, collect_move(state, 0))
    exit_after = one_open_place(preview.successor, 0)
    after_features = move_features_no_draw(preview.successor, exit_after)

    assert after_features.places_exit_ready == 1
    assert after_features.places_exit_early == 0


def test_terminal_first_action_win_uses_only_score1() -> None:
    state = one_open_state(
        [
            card("exit", {Direction.WEST}, is_exit=True),
            card("rope", set(), material=Material.ROPE),
            card("coat", set(), material=Material.RAINCOAT),
        ],
        coats=3,
        ropes=2,
    )
    move = one_open_place(state, 0)

    assert two_action_sequence_score(state, move, V4_WEIGHTS) == (
        score_move_no_draw(state, move, V4_WEIGHTS)
    )


def test_terminal_first_action_close_without_win_uses_only_score1() -> None:
    state = one_open_state(
        [
            card("end", {Direction.WEST}),
            card("rope", set(), material=Material.ROPE),
            card("coat", set(), material=Material.RAINCOAT),
        ],
        coats=3,
        ropes=2,
    )
    move = one_open_place(state, 0)

    assert two_action_sequence_score(state, move, V4_WEIGHTS) == (
        score_move_no_draw(state, move, V4_WEIGHTS)
    )


def test_no_legal_retained_second_action_uses_only_score1() -> None:
    state = one_open_state(
        [
            card("coat", set(), material=Material.RAINCOAT),
            blocked("a"),
            blocked("b"),
        ],
        coats=3,
        ropes=2,
    )
    first = collect_move(state, 0)
    preview = preview_move_without_draw(state, first)

    assert preview.successor.legal_moves() == []
    assert two_action_sequence_score(state, first, V4_WEIGHTS) == (
        score_move_no_draw(state, first, V4_WEIGHTS)
    )


def test_sequence_can_use_second_place() -> None:
    state = one_open_state(
        [
            card("coat", set(), material=Material.RAINCOAT),
            card("straight", {Direction.WEST, Direction.EAST}),
            blocked("x"),
        ],
        coats=3,
        ropes=2,
    )
    first = collect_move(state, 0)
    preview = preview_move_without_draw(state, first)
    second_moves = preview.successor.legal_moves()

    assert second_moves
    assert all(move.action is Action.PLACE for move in second_moves)
    expected_second = max(
        score_move_no_draw(preview.successor, move, V4_WEIGHTS)
        for move in second_moves
    )
    assert two_action_sequence_score(state, first, V4_WEIGHTS) == (
        score_move_no_draw(state, first, V4_WEIGHTS) + expected_second
    )


def test_sequence_can_use_second_collect() -> None:
    state = one_open_state(
        [
            card("coat", set(), material=Material.RAINCOAT),
            card("rope", set(), material=Material.ROPE),
            blocked("x"),
        ],
        coats=3,
        ropes=1,
    )
    first = collect_move(state, 0)
    preview = preview_move_without_draw(state, first)
    second_moves = preview.successor.legal_moves()

    assert len(second_moves) == 1
    assert second_moves[0].action is Action.COLLECT
    assert preview.successor.hand[second_moves[0].hand_index].material is Material.ROPE
    assert two_action_sequence_score(state, first, V4_WEIGHTS) == (
        score_move_no_draw(state, first, V4_WEIGHTS)
        + score_move_no_draw(preview.successor, second_moves[0], V4_WEIGHTS)
    )


def test_sequence_can_use_second_exit_and_win() -> None:
    state = one_open_state(
        [
            card("coat", set(), material=Material.RAINCOAT),
            card("exit", {Direction.WEST}, is_exit=True),
            blocked("x"),
        ],
        coats=2,
        ropes=2,
    )
    first = collect_move(state, 0)
    preview = preview_move_without_draw(state, first)
    exit_move = next(
        move
        for move in preview.successor.legal_moves()
        if preview.successor.hand[move.hand_index].is_exit
    )
    second_features = move_features_no_draw(preview.successor, exit_move)

    assert second_features.places_exit_ready == 1
    assert second_features.wins == 1
    assert two_action_sequence_score(state, first, V4_WEIGHTS) == (
        score_move_no_draw(state, first, V4_WEIGHTS)
        + score_move_no_draw(preview.successor, exit_move, V4_WEIGHTS)
    )


def tied_collect_state() -> GameState:
    return one_open_state(
        [
            card("coat-a", set(), material=Material.RAINCOAT),
            card("coat-b", set(), material=Material.RAINCOAT),
            blocked("x"),
        ],
        coats=3,
        ropes=2,
    )


def test_rng_contract_is_exactly_one_final_choice() -> None:
    state = tied_collect_state()
    rng = CountingRng()
    policy = VisibleHandTwoActionV6Policy()

    expected_candidates = best_two_action_first_moves(state, policy.weights)
    selected = policy.choose(state, rng)

    assert rng.choice_calls == 1
    assert rng.choice_inputs == [tuple(expected_candidates)]
    assert selected == expected_candidates[0]


def test_rng_contract_no_legal_first_move_uses_zero_rng() -> None:
    board = Board()
    board.seed(blocked("sealed"))
    state = GameState(
        board=board,
        draw_pile=UnreadableDrawPile(),
        hand=[blocked("a"), blocked("b"), blocked("c")],
    )
    rng = CountingRng()

    assert VisibleHandTwoActionV6Policy().choose(state, rng) is None
    assert rng.choice_calls == 0


def test_tied_best_first_moves_preserve_existing_legal_order() -> None:
    state = tied_collect_state()
    legal = state.legal_moves()
    best = best_two_action_first_moves(state, V4_WEIGHTS)

    assert legal == [
        Move(Action.COLLECT, 0),
        Move(Action.COLLECT, 1),
    ]
    assert best == legal

    source = inspect.getsource(best_two_action_first_moves)
    assert "sorted(" not in source
    assert "set(" not in source


def test_v6_is_exact_v4_250_weighted_and_isolated_from_v5() -> None:
    v6 = VisibleHandTwoActionV6Policy()

    assert v6.weights == BoundedMergeV4Policy(setup_weight=250).weights
    assert issubclass(VisibleHandTwoActionV6Policy, BoundedMergeV4Policy)
    assert not issubclass(VisibleHandTwoActionV6Policy, VisibleRepairReserveV5Policy)

    source = inspect.getsource(VisibleHandTwoActionV6Policy)
    assert "is_unsafe_capacity_kill_without_visible_repair_reserve" not in source
    assert "exit_seen" not in source
