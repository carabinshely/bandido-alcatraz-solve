from bandido_alcatraz.rules import GameStatus, is_equipment_ready, is_victory


def test_equipment_exact_rejects_overcollection() -> None:
    assert is_equipment_ready(3, 2)
    assert not is_equipment_ready(4, 2)
    assert not is_equipment_ready(3, 3)


def test_victory_requires_exit_closed_tunnels_no_water_and_equipment() -> None:
    assert is_victory(GameStatus(3, 2, 0, 0, True))
    assert not is_victory(GameStatus(3, 2, 1, 0, True))
    assert not is_victory(GameStatus(3, 2, 0, 1, True))
    assert not is_victory(GameStatus(3, 2, 0, 0, False))
    assert not is_victory(GameStatus(2, 2, 0, 0, True))
