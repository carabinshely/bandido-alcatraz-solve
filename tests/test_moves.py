from bandido_alcatraz.board import Board
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action, legal_moves


def card(card_id: str, edges: set[Direction], *, material: Material | None = None):
    return CardDefinition(
        card_id,
        (CellSpec(0, 0, frozenset(edges)),),
        material,
    )


def test_legal_moves_include_collect_and_place_for_equipment_card() -> None:
    board = Board()
    board.seed(card("start", {Direction.EAST}))
    equipment = card(
        "rope",
        {Direction.WEST},
        material=Material.ROPE,
    )

    moves = legal_moves(board, (equipment,))

    assert any(move.action is Action.COLLECT for move in moves)
    assert any(
        move.action is Action.PLACE and move.origin == (1, 0)
        for move in moves
    )


def test_symmetric_rotations_do_not_duplicate_same_placement() -> None:
    board = Board()
    board.seed(card("start", {Direction.EAST}))
    dead_end = card("end", {Direction.WEST})

    moves = legal_moves(board, (dead_end,))
    placements = [move for move in moves if move.action is Action.PLACE]

    assert len(placements) == 1
    assert placements[0].origin == (1, 0)
