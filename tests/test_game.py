from random import Random

import pytest

from bandido_alcatraz.board import Board
from bandido_alcatraz.game import GameState
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action


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


def board_with_east_exit() -> Board:
    board = Board()
    board.seed(card("start", {Direction.EAST}))
    return board


def test_collect_consumes_card_and_increments_material() -> None:
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[],
        hand=[card("coat", {Direction.WEST}, material=Material.RAINCOAT)],
    )
    collect = next(move for move in state.legal_moves() if move.action is Action.COLLECT)

    state.apply(collect)

    assert state.raincoats == 1
    assert state.hand == []


def test_exit_placement_can_complete_victory() -> None:
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[],
        hand=[card("exit", {Direction.WEST}, is_exit=True)],
        raincoats=3,
        ropes=2,
    )
    place_exit = next(move for move in state.legal_moves() if move.action is Action.PLACE)

    state.apply(place_exit)

    assert state.exit_placed
    assert state.board.open_tunnels == 0
    assert state.won


def test_three_card_unplayable_hand_is_refreshed() -> None:
    blocked = card("blocked", set())
    playable = card("playable", {Direction.WEST})
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[
            playable,
            playable,
            playable,
            playable,
        ],
        hand=[blocked, blocked, blocked],
    )

    assert state.refresh_unplayable_hand()

    assert len(state.hand) == 3
    assert all(item.card_id == "playable" for item in state.hand)
    assert len(state.draw_pile) == 4


def test_refresh_stops_when_all_remaining_cards_are_unplayable() -> None:
    blocked = card("blocked", set())
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[blocked, blocked, blocked, blocked],
        hand=[blocked, blocked, blocked],
    )
    original_hand = list(state.hand)
    original_draw_pile = list(state.draw_pile)

    assert not state.refresh_unplayable_hand()

    assert state.hand == original_hand
    assert state.draw_pile == original_draw_pile


def test_short_draw_pile_sets_old_unplayable_hand_aside() -> None:
    blocked = card("blocked", set())
    playable = card("playable", {Direction.WEST})
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[playable, playable],
        hand=[blocked, blocked, blocked],
    )

    assert state.refresh_unplayable_hand()

    assert len(state.hand) == 2
    assert not state.draw_pile
    assert state.set_aside_unplayable == 3


def test_prevalidated_apply_matches_default_apply() -> None:
    first = GameState(
        board=board_with_east_exit(),
        draw_pile=[],
        hand=[card("end", {Direction.WEST})],
    )
    second = GameState(
        board=board_with_east_exit(),
        draw_pile=[],
        hand=[card("end", {Direction.WEST})],
    )

    move = next(
        move for move in first.legal_moves()
        if move.action is Action.PLACE
    )
    first.apply(move)
    second.apply(move, validate=False)

    assert first.status == second.status
    assert first.turns == second.turns == 1


def test_new_initial_hand_without_exit_is_not_seen() -> None:
    ordinary = card("ordinary", {Direction.WEST})
    state = GameState.new(
        start_card=card("start", {Direction.EAST}),
        deck=[ordinary],
        hand_size=3,
        rng=Random(1),
    )

    assert not state.exit_seen


def test_new_initial_hand_with_exit_is_seen() -> None:
    exit_card = card("exit", {Direction.WEST}, is_exit=True)
    state = GameState.new(
        start_card=card("start", {Direction.EAST}),
        deck=[exit_card],
        hand_size=3,
        rng=Random(1),
    )

    assert state.exit_seen
    assert not state.exit_placed


def test_non_exit_draw_does_not_set_exit_seen() -> None:
    coat = card("coat", {Direction.WEST}, material=Material.RAINCOAT)
    ordinary = card("ordinary", {Direction.WEST})
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[ordinary],
        hand=[coat],
    )
    collect = next(move for move in state.legal_moves() if move.action is Action.COLLECT)

    state.apply(collect)

    assert not state.exit_seen
    assert state.hand == [ordinary]


def test_exit_draw_sets_exit_seen() -> None:
    coat = card("coat", {Direction.WEST}, material=Material.RAINCOAT)
    exit_card = card("exit", {Direction.WEST}, is_exit=True)
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[exit_card],
        hand=[coat],
    )
    collect = next(move for move in state.legal_moves() if move.action is Action.COLLECT)

    state.apply(collect)

    assert state.exit_seen
    assert state.hand == [exit_card]


def test_long_refresh_without_exit_keeps_exit_unseen() -> None:
    blocked = card("blocked", set())
    playable = card("playable", {Direction.WEST})
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[playable, playable, playable, playable],
        hand=[blocked, blocked, blocked],
    )

    assert state.refresh_unplayable_hand()

    assert not state.exit_seen
    assert all(not item.is_exit for item in state.hand)


def test_short_refresh_revealing_exit_sets_exit_seen() -> None:
    blocked = card("blocked", set())
    playable = card("playable", {Direction.WEST})
    exit_card = card("exit", {Direction.WEST}, is_exit=True)
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[playable, exit_card],
        hand=[blocked, blocked, blocked],
    )

    assert state.refresh_unplayable_hand()

    assert state.exit_seen
    assert exit_card in state.hand


def test_exit_seen_is_monotonic_across_later_non_exit_draw() -> None:
    coat = card("coat", {Direction.WEST}, material=Material.RAINCOAT)
    ordinary = card("ordinary", {Direction.WEST})
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[ordinary],
        hand=[coat],
        exit_seen=True,
    )
    collect = next(move for move in state.legal_moves() if move.action is Action.COLLECT)

    state.apply(collect)

    assert state.exit_seen


def test_exit_seen_is_monotonic_across_later_refresh() -> None:
    blocked = card("blocked", set())
    playable = card("playable", {Direction.WEST})
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[playable, playable],
        hand=[blocked, blocked, blocked],
        exit_seen=True,
    )

    assert state.refresh_unplayable_hand()

    assert state.exit_seen


def test_exit_placement_preserves_exit_seen() -> None:
    exit_card = card("exit", {Direction.WEST}, is_exit=True)
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[],
        hand=[exit_card],
        raincoats=3,
        ropes=2,
    )
    assert state.exit_seen
    place_exit = next(move for move in state.legal_moves() if move.action is Action.PLACE)

    state.apply(place_exit)

    assert state.exit_placed
    assert state.exit_seen


def test_direct_visible_exit_is_promoted_to_seen() -> None:
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[],
        hand=[card("exit", {Direction.WEST}, is_exit=True)],
        exit_seen=False,
    )

    assert state.exit_seen


def test_direct_placed_exit_is_promoted_to_seen() -> None:
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[],
        hand=[],
        exit_placed=True,
        exit_seen=False,
    )

    assert state.exit_seen


def test_hidden_exit_in_draw_pile_does_not_set_exit_seen() -> None:
    exit_card = card("exit", {Direction.WEST}, is_exit=True)
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[exit_card],
        hand=[card("ordinary", {Direction.WEST})],
    )

    assert not state.exit_seen


def test_exit_seen_cannot_be_reset_directly() -> None:
    state = GameState(
        board=board_with_east_exit(),
        draw_pile=[],
        hand=[],
        exit_seen=True,
    )

    with pytest.raises(ValueError, match="exit_seen is monotonic"):
        state.exit_seen = False

    assert state.exit_seen
