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
