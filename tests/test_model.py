from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material


def test_rotation_normalizes_two_cell_card() -> None:
    card = CardDefinition(
        "sample",
        (
            CellSpec(0, 0, frozenset({Direction.WEST, Direction.EAST})),
            CellSpec(1, 0, frozenset({Direction.WEST, Direction.NORTH}), water=True),
        ),
        Material.ROPE,
    )

    rotated = card.rotated(1)

    assert {(cell.x, cell.y) for cell in rotated.cells} == {(0, 0), (0, 1)}
    assert rotated.material is Material.ROPE
    assert rotated.has_water


def test_duplicate_cell_coordinates_are_rejected() -> None:
    try:
        CardDefinition(
            "bad",
            (
                CellSpec(0, 0, frozenset()),
                CellSpec(0, 0, frozenset()),
            ),
        )
    except ValueError as exc:
        assert "unique coordinates" in str(exc)
    else:
        raise AssertionError("expected ValueError")
