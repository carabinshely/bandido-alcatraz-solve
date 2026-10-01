from random import Random

from bandido_alcatraz.board import Board
from bandido_alcatraz.game import GameState
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action, Move, legal_moves
from bandido_alcatraz.strategy import (
    PolicyWeights,
    RetainedVisibleCard,
    WeightedGreedyPolicy,
    clone_state,
    has_visible_exit_repair_reserve,
    is_unsafe_capacity_kill_without_visible_repair_reserve,
    move_features,
    preview_ordinary_non_exit_placement_without_draw,
    score_features,
    standalone_exit_legal_move_count,
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


def test_water_on_water_overlap_is_not_scored_as_water_reduction() -> None:
    board = Board()
    board.seed(card("water", {Direction.EAST, Direction.WEST}, water=True))
    water_cover = CardDefinition(
        "water-cover",
        (
            CellSpec(
                0,
                0,
                frozenset({Direction.EAST, Direction.WEST}),
                water=True,
            ),
            CellSpec(1, 0, frozenset({Direction.WEST})),
        ),
    )
    state = GameState(board=board, draw_pile=[], hand=[water_cover])
    move = next(
        move
        for move in state.legal_moves()
        if move.action is Action.PLACE and move.origin == (0, 0)
    )

    features = move_features(state, move)

    assert features.delta_visible_water == 0


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


def test_spatial_features_default_to_zero_weight() -> None:
    weights = PolicyWeights()

    assert weights.delta_merge_opportunities == 0
    assert weights.delta_water_obstruction == 0
    assert weights.new_trapped_water == 0
    assert weights.bounded_merge_setup_gain == 0


def test_bounded_merge_bank_caps_and_disables_over_budget() -> None:
    from types import SimpleNamespace
    from bandido_alcatraz.strategy import _bounded_merge_bank

    assert _bounded_merge_bank(
        SimpleNamespace(open_tunnels=9, merge_opportunities=4)
    ) == 4
    assert _bounded_merge_bank(
        SimpleNamespace(open_tunnels=9, merge_opportunities=9)
    ) == 6
    assert _bounded_merge_bank(
        SimpleNamespace(open_tunnels=11, merge_opportunities=9)
    ) == 0


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


def board_with_two_open() -> Board:
    board = Board()
    board.seed(card("start-two-open", {Direction.NORTH, Direction.EAST}))
    return board


def capacity_killer_card() -> CardDefinition:
    return CardDefinition(
        "capacity-killer",
        (
            CellSpec(0, 0, frozenset({Direction.NORTH})),
            CellSpec(1, 0, frozenset({Direction.NORTH})),
        ),
    )


def visible_repair_card(
    *,
    card_id: str = "repair",
    material: Material | None = None,
) -> CardDefinition:
    return card(
        card_id,
        {Direction.NORTH, Direction.EAST, Direction.SOUTH},
        material=material,
    )


def blocked_card(card_id: str = "blocked") -> CardDefinition:
    return card(card_id, set())


def capacity_kill_move(hand_index: int = 0) -> Move:
    return Move(
        Action.PLACE,
        hand_index,
        origin=(0, -1),
        quarter_turns=2,
    )


def preview_after_capacity_kill(
    retained_one: CardDefinition,
    retained_two: CardDefinition,
):
    state = GameState(
        board=board_with_two_open(),
        draw_pile=[],
        hand=[capacity_killer_card(), retained_one, retained_two],
    )
    return preview_ordinary_non_exit_placement_without_draw(
        state,
        capacity_kill_move(),
    )


def test_clone_state_preserves_exit_seen_false_and_true() -> None:
    unseen = GameState(
        board=board_with_two_open(),
        draw_pile=[synthetic_exit_card()],
        hand=[blocked_card("a"), blocked_card("b"), blocked_card("c")],
    )
    seen = GameState(
        board=board_with_two_open(),
        draw_pile=[],
        hand=[blocked_card("d"), blocked_card("e"), blocked_card("f")],
        exit_seen=True,
    )

    unseen_clone = clone_state(unseen)
    seen_clone = clone_state(seen)

    assert not unseen_clone.exit_seen
    assert seen_clone.exit_seen
    assert unseen_clone.draw_pile == unseen.draw_pile
    assert seen_clone.hand == seen.hand


def test_standalone_exit_capacity_matches_canonical_legal_moves() -> None:
    board = board_with_two_open()
    exit_card = synthetic_exit_card()

    expected = len(legal_moves(board, (exit_card,), raincoats=3, ropes=2))
    actual = standalone_exit_legal_move_count(board, exit_card)

    assert expected == actual == 2


def test_standalone_exit_capacity_zero_case_does_not_mutate_board() -> None:
    exit_card = synthetic_exit_card()
    preview = preview_after_capacity_kill(
        blocked_card("one"),
        blocked_card("two"),
    )
    before = preview.resulting_board.cells

    actual = standalone_exit_legal_move_count(
        preview.resulting_board,
        exit_card,
    )

    assert actual == 0
    assert preview.resulting_board.cells == before


def test_no_draw_preview_applies_exact_origin_rotation_and_retains_identity() -> None:
    retained_one = blocked_card("retained-one")
    retained_two = blocked_card("retained-two")
    replacement = visible_repair_card(card_id="hidden-replacement")
    state = GameState(
        board=board_with_two_open(),
        draw_pile=[replacement],
        hand=[capacity_killer_card(), retained_one, retained_two],
    )
    move = capacity_kill_move()
    assert move in state.legal_moves()
    before_cells = state.board.cells
    before_hand = list(state.hand)
    before_draw = list(state.draw_pile)

    preview = preview_ordinary_non_exit_placement_without_draw(state, move)

    assert (0, -1) in preview.resulting_board.cells
    assert (1, -1) in preview.resulting_board.cells
    assert preview.resulting_board.cells[(0, -1)].tunnel_edges == frozenset(
        {Direction.SOUTH}
    )
    assert [item.hand_index for item in preview.retained_visible_cards] == [1, 2]
    assert preview.retained_visible_cards[0].card is retained_one
    assert preview.retained_visible_cards[1].card is retained_two
    assert all(
        item.card is not replacement
        for item in preview.retained_visible_cards
    )
    assert state.board.cells == before_cells
    assert state.hand == before_hand
    assert state.draw_pile == before_draw


def test_no_draw_preview_uses_canonical_water_cover_semantics() -> None:
    board = Board()
    board.seed(
        card(
            "water",
            {Direction.EAST, Direction.WEST},
            water=True,
        )
    )
    cover = CardDefinition(
        "cover",
        (
            CellSpec(0, 0, frozenset({Direction.EAST, Direction.WEST})),
            CellSpec(1, 0, frozenset({Direction.WEST})),
        ),
    )
    state = GameState(
        board=board,
        draw_pile=[],
        hand=[cover, blocked_card("one"), blocked_card("two")],
    )
    move = next(
        move
        for move in state.legal_moves()
        if move.action is Action.PLACE and move.origin == (0, 0)
    )
    before = state.board.cells

    preview = preview_ordinary_non_exit_placement_without_draw(state, move)

    assert state.board.visible_water_cells == 1
    assert preview.resulting_board.visible_water_cells == 0
    assert state.board.cells == before


def test_visible_repair_reserve_can_come_from_first_retained_card() -> None:
    exit_card = synthetic_exit_card()
    repair = visible_repair_card()
    preview = preview_after_capacity_kill(
        repair,
        blocked_card(),
    )

    assert has_visible_exit_repair_reserve(
        preview.resulting_board,
        preview.retained_visible_cards,
        exit_card,
    )


def test_visible_repair_reserve_can_come_from_second_retained_card() -> None:
    exit_card = synthetic_exit_card()
    repair = visible_repair_card()
    preview = preview_after_capacity_kill(
        blocked_card(),
        repair,
    )

    assert has_visible_exit_repair_reserve(
        preview.resulting_board,
        preview.retained_visible_cards,
        exit_card,
    )


def test_visible_repair_reserve_can_exist_in_both_retained_cards() -> None:
    exit_card = synthetic_exit_card()
    preview = preview_after_capacity_kill(
        visible_repair_card(card_id="repair-one"),
        visible_repair_card(card_id="repair-two"),
    )

    assert has_visible_exit_repair_reserve(
        preview.resulting_board,
        preview.retained_visible_cards,
        exit_card,
    )


def test_visible_repair_reserve_false_when_neither_card_can_place() -> None:
    exit_card = synthetic_exit_card()
    preview = preview_after_capacity_kill(
        blocked_card("one"),
        blocked_card("two"),
    )
    before = preview.resulting_board.cells

    assert not has_visible_exit_repair_reserve(
        preview.resulting_board,
        preview.retained_visible_cards,
        exit_card,
    )
    assert preview.resulting_board.cells == before


def test_repair_only_in_replacement_draw_is_not_visible_reserve() -> None:
    exit_card = synthetic_exit_card()
    repair = visible_repair_card()
    state = GameState(
        board=board_with_two_open(),
        draw_pile=[repair],
        hand=[
            capacity_killer_card(),
            blocked_card("one"),
            blocked_card("two"),
        ],
    )
    move = capacity_kill_move()
    preview = preview_ordinary_non_exit_placement_without_draw(state, move)
    hypothetical_retained = (
        RetainedVisibleCard(1, repair),
        RetainedVisibleCard(2, blocked_card("other")),
    )
    assert has_visible_exit_repair_reserve(
        preview.resulting_board,
        hypothetical_retained,
        exit_card,
    )

    assert is_unsafe_capacity_kill_without_visible_repair_reserve(
        state,
        move,
        exit_card,
    )


def test_repair_only_available_after_refresh_is_not_visible_reserve() -> None:
    exit_card = synthetic_exit_card()
    repair = visible_repair_card()
    state = GameState(
        board=board_with_two_open(),
        draw_pile=[
            blocked_card("future-one"),
            repair,
            blocked_card("future-two"),
            blocked_card("future-three"),
        ],
        hand=[
            capacity_killer_card(),
            blocked_card("one"),
            blocked_card("two"),
        ],
    )
    before_draw = list(state.draw_pile)
    preview = preview_ordinary_non_exit_placement_without_draw(
        state,
        capacity_kill_move(),
    )
    hypothetical_after_refresh = (
        RetainedVisibleCard(1, repair),
        RetainedVisibleCard(2, blocked_card("hypothetical")),
    )
    assert has_visible_exit_repair_reserve(
        preview.resulting_board,
        hypothetical_after_refresh,
        exit_card,
    )

    assert is_unsafe_capacity_kill_without_visible_repair_reserve(
        state,
        capacity_kill_move(),
        exit_card,
    )
    assert state.draw_pile == before_draw


def test_equipment_collection_cannot_count_as_repair() -> None:
    exit_card = synthetic_exit_card()
    collect_only = card(
        "collect-only",
        set(),
        material=Material.ROPE,
    )
    preview = preview_after_capacity_kill(
        collect_only,
        blocked_card(),
    )

    assert any(
        move.action is Action.COLLECT
        for move in legal_moves(preview.resulting_board, (collect_only,), raincoats=0, ropes=0)
    )
    assert not has_visible_exit_repair_reserve(
        preview.resulting_board,
        preview.retained_visible_cards,
        exit_card,
    )


def test_material_card_ordinary_placement_can_count_as_repair() -> None:
    exit_card = synthetic_exit_card()
    repair = visible_repair_card(material=Material.ROPE)
    preview = preview_after_capacity_kill(
        repair,
        blocked_card(),
    )

    assert has_visible_exit_repair_reserve(
        preview.resulting_board,
        preview.retained_visible_cards,
        exit_card,
    )


def test_retained_exit_is_skipped_as_repair() -> None:
    board = board_with_two_open()
    exit_card = synthetic_exit_card()
    assert standalone_exit_legal_move_count(board, exit_card) > 0

    retained = (
        RetainedVisibleCard(1, exit_card),
        RetainedVisibleCard(2, blocked_card()),
    )

    assert not has_visible_exit_repair_reserve(
        board,
        retained,
        exit_card,
    )


def test_unsafe_classifier_detects_positive_to_zero_without_reserve() -> None:
    exit_card = synthetic_exit_card()
    state = GameState(
        board=board_with_two_open(),
        draw_pile=[visible_repair_card(card_id="hidden")],
        hand=[
            capacity_killer_card(),
            blocked_card("one"),
            blocked_card("two"),
        ],
    )
    before_cells = state.board.cells
    before_hand = list(state.hand)
    before_draw = list(state.draw_pile)

    assert is_unsafe_capacity_kill_without_visible_repair_reserve(
        state,
        capacity_kill_move(),
        exit_card,
    )
    assert state.board.cells == before_cells
    assert state.hand == before_hand
    assert state.draw_pile == before_draw


def test_unsafe_classifier_keeps_zero_kill_normal_when_reserve_exists() -> None:
    exit_card = synthetic_exit_card()
    state = GameState(
        board=board_with_two_open(),
        draw_pile=[],
        hand=[
            capacity_killer_card(),
            visible_repair_card(),
            blocked_card(),
        ],
    )

    assert not is_unsafe_capacity_kill_without_visible_repair_reserve(
        state,
        capacity_kill_move(),
        exit_card,
    )


def test_unsafe_classifier_keeps_capacity_preserving_placement_normal() -> None:
    exit_card = synthetic_exit_card()
    preserving = card("preserving", {Direction.NORTH})
    state = GameState(
        board=board_with_two_open(),
        draw_pile=[],
        hand=[preserving, blocked_card("one"), blocked_card("two")],
    )
    move = Move(
        Action.PLACE,
        0,
        origin=(0, -1),
        quarter_turns=2,
    )
    assert move in state.legal_moves()

    assert not is_unsafe_capacity_kill_without_visible_repair_reserve(
        state,
        move,
        exit_card,
    )


def test_unsafe_classifier_is_normal_when_capacity_already_zero() -> None:
    exit_card = synthetic_exit_card()
    zero_preview = preview_after_capacity_kill(
        blocked_card("one"),
        blocked_card("two"),
    )
    repair = visible_repair_card()
    state = GameState(
        board=zero_preview.resulting_board,
        draw_pile=[],
        hand=[repair, blocked_card("a"), blocked_card("b")],
    )
    move = next(
        move
        for move in state.legal_moves()
        if move.action is Action.PLACE
    )
    assert standalone_exit_legal_move_count(state.board, exit_card) == 0

    assert not is_unsafe_capacity_kill_without_visible_repair_reserve(
        state,
        move,
        exit_card,
    )


def test_unsafe_classifier_keeps_collect_and_exit_placement_normal() -> None:
    exit_card = synthetic_exit_card()
    collect_card = card(
        "rope",
        {Direction.NORTH},
        material=Material.ROPE,
    )
    collect_state = GameState(
        board=board_with_two_open(),
        draw_pile=[],
        hand=[collect_card, blocked_card("one"), blocked_card("two")],
    )
    collect = next(
        move
        for move in collect_state.legal_moves()
        if move.action is Action.COLLECT
    )
    assert not is_unsafe_capacity_kill_without_visible_repair_reserve(
        collect_state,
        collect,
        exit_card,
    )

    exit_state = GameState(
        board=board_with_two_open(),
        draw_pile=[],
        hand=[exit_card, blocked_card("one"), blocked_card("two")],
    )
    place_exit = next(
        move
        for move in exit_state.legal_moves()
        if move.action is Action.PLACE and move.hand_index == 0
    )
    assert not is_unsafe_capacity_kill_without_visible_repair_reserve(
        exit_state,
        place_exit,
        exit_card,
    )


def test_visible_repair_safety_helpers_do_not_consume_rng() -> None:
    exit_card = synthetic_exit_card()
    state = GameState(
        board=board_with_two_open(),
        draw_pile=[visible_repair_card(card_id="hidden")],
        hand=[
            capacity_killer_card(),
            blocked_card("one"),
            blocked_card("two"),
        ],
    )
    rng = Random(67)
    rng_state = rng.getstate()

    assert standalone_exit_legal_move_count(state.board, exit_card) > 0
    preview = preview_ordinary_non_exit_placement_without_draw(
        state,
        capacity_kill_move(),
    )
    assert not has_visible_exit_repair_reserve(
        preview.resulting_board,
        preview.retained_visible_cards,
        exit_card,
    )
    assert is_unsafe_capacity_kill_without_visible_repair_reserve(
        state,
        capacity_kill_move(),
        exit_card,
    )

    assert rng.getstate() == rng_state
