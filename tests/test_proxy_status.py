from pathlib import Path

import pytest

from bandido_alcatraz.proxy_data import (
    compile_proxy_deck,
    load_proxy,
    proxy_status,
)


ROOT = Path(__file__).parents[1]


def test_current_proxy_status_is_explicit() -> None:
    data = load_proxy(ROOT / "data" / "proxy-bandido-covid-v0.json")
    status = proxy_status(data)

    assert status.total_slots == 32
    assert status.transcribed_slots == 10
    assert status.remaining_slots == 22
    assert status.end_slots == 10
    assert status.transcribed_end_slots == 10
    assert status.basic_slots == 22
    assert status.transcribed_basic_slots == 0
    assert not status.complete_geometry


def test_incomplete_proxy_cannot_be_compiled_as_a_deck() -> None:
    data = load_proxy(ROOT / "data" / "proxy-bandido-covid-v0.json")

    with pytest.raises(ValueError, match="10/32 slots transcribed"):
        compile_proxy_deck(data)
