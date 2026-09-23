from __future__ import annotations

from .model import CardDefinition, CellSpec, Direction, Material


def _single(
    card_id: str,
    edges: set[Direction],
    *,
    material: Material | None = None,
    water: bool = False,
    is_exit: bool = False,
) -> CardDefinition:
    return CardDefinition(
        card_id,
        (CellSpec(0, 0, frozenset(edges), water=water),),
        material,
        is_exit,
    )


def synthetic_start() -> CardDefinition:
    return _single("synthetic-start", {Direction.EAST, Direction.WEST})


def synthetic_deck() -> list[CardDefinition]:
    """Small non-authoritative deck for engine/simulation tests only."""
    cards: list[CardDefinition] = []

    for i in range(8):
        cards.append(_single(f"straight-{i}", {Direction.EAST, Direction.WEST}))
    for i in range(6):
        cards.append(_single(f"end-{i}", {Direction.WEST}))
    for i in range(4):
        cards.append(
            _single(
                f"raincoat-{i}",
                {Direction.EAST, Direction.WEST},
                material=Material.RAINCOAT,
            )
        )
    for i in range(3):
        cards.append(
            _single(
                f"rope-{i}",
                {Direction.EAST, Direction.WEST},
                material=Material.ROPE,
            )
        )

    cards.append(
        _single(
            "exit",
            {Direction.WEST},
            is_exit=True,
        )
    )
    return cards
