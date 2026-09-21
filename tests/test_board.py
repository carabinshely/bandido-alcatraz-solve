from bandido_alcatraz.board import Board
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction


def single(card_id: str, edges: set[Direction], *, water: bool = False) -> CardDefinition:
    return CardDefinition(card_id, (CellSpec(0, 0, frozenset(edges), water=water),))


def test_place_requires_tunnel_to_tunnel_match() -> None:
    board = Board()
    board.seed(single("start", {Direction.EAST}))

    good = single("good", {Direction.WEST})
    bad = single("bad", {Direction.NORTH})

    assert board.can_place(good, (1, 0))
    assert not board.can_place(bad, (1, 0))

    board.place(good, (1, 0))
    assert board.open_tunnels == 0


def test_open_tunnels_counts_unconnected_edges() -> None:
    board = Board()
    board.seed(single("start", {Direction.EAST, Direction.NORTH}))
    assert board.open_tunnels == 2

    board.place(single("end", {Direction.WEST}), (1, 0))
    assert board.open_tunnels == 1


def test_water_half_can_be_covered_only_with_exact_edge_pattern() -> None:
    board = Board()
    board.seed(single("water", {Direction.EAST, Direction.WEST}, water=True))

    exact_cover = CardDefinition(
        "cover",
        (
            CellSpec(0, 0, frozenset({Direction.EAST, Direction.WEST})),
            CellSpec(1, 0, frozenset({Direction.WEST})),
        ),
    )
    wrong_cover = CardDefinition(
        "wrong",
        (
            CellSpec(0, 0, frozenset({Direction.NORTH})),
            CellSpec(1, 0, frozenset({Direction.WEST})),
        ),
    )

    assert board.can_place(exact_cover, (0, 0))
    assert not board.can_place(wrong_cover, (0, 0))

    board.place(exact_cover, (0, 0))
    assert board.visible_water_cells == 0
    assert board.open_tunnels == 1


def test_non_water_cell_cannot_be_overlapped() -> None:
    board = Board()
    board.seed(single("start", {Direction.EAST}))
    assert not board.can_place(single("x", {Direction.EAST}), (0, 0))
