"""Synthetic-only observability/export checks; no research games or real-deck seeds."""

import json
from dataclasses import replace
from pathlib import Path
from random import Random
import subprocess
import sys
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import pytest

from bandido_alcatraz.board import Board
from bandido_alcatraz.export_svg import (
    FinalBoardExport,
    FinalStateCapturePolicy,
    export_final_boards,
)
from bandido_alcatraz.game import CollectedEquipment, GameState
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction, Material
from bandido_alcatraz.moves import Action, Move
from bandido_alcatraz.render_svg import SVG_NS, render_board_svg
from bandido_alcatraz.simulate import play_game
from scripts.export_final_boards import V7_HISTORICAL_CHECKOUT, export_v7

ROOT = Path(__file__).resolve().parents[1]


def _card(card_id, edges, material=None):
    return CardDefinition(
        card_id, (CellSpec(0, 0, frozenset(edges)),), material=material,
    )


def _board():
    board = Board()
    board.seed(_card("synthetic-start", {Direction.EAST}))
    return board


def _equipment():
    return (
        CollectedEquipment(_card("raincoat<&1", {Direction.EAST}, Material.RAINCOAT), 1),
        CollectedEquipment(
            CardDefinition(
                "rope-bridge",
                (
                    CellSpec(0, 0, frozenset({Direction.WEST, Direction.EAST})),
                    CellSpec(1, 0, frozenset({Direction.WEST, Direction.SOUTH}), water=True),
                ),
                material=Material.ROPE,
            ),
            3,
            player_index=1,
        ),
        CollectedEquipment(
            _card("raincoat-cross", set(Direction), Material.RAINCOAT), 6,
        ),
    )


def _by_role(root, role):
    return [element for element in root.iter() if element.get("data-role") == role]


def test_svg_set_aside_area_preserves_identity_order_material_and_geometry():
    board = _board()
    history = _equipment()
    before = board.cells, board.placements
    svg = render_board_svg(board, collected_equipment=history)
    root = ET.fromstring(svg)
    area = root.find(f"{{{SVG_NS}}}g[@id='collected-equipment']")
    assert area is not None
    cards = [child for child in area if child.get("data-card-id")]
    assert [card.get("data-card-id") for card in cards] == [item.card_id for item in history]
    assert [card.get("data-material") for card in cards] == ["raincoat", "rope", "raincoat"]
    assert [card.get("data-collection-index") for card in cards] == ["1", "2", "3"]
    assert [card.get("data-turn") for card in cards] == ["1", "3", "6"]
    assert [card.get("data-player-index") for card in cards] == ["0", "1", "0"]
    assert len(_by_role(root, "equipment-geometry")) == 3
    geometries = _by_role(root, "equipment-geometry")
    assert [len(list(geometry.iter(f"{{{SVG_NS}}}line"))) for geometry in geometries] == [1, 4, 4]
    assert [len(list(geometry.iter(f"{{{SVG_NS}}}rect"))) for geometry in geometries] == [1, 2, 1]
    assert "Collected equipment / set-aside" in svg
    assert "definition orientation" in svg
    assert (board.cells, board.placements) == before
    # Equipment does not become placed board geometry or open-tunnel markers.
    placed = root.find(f"{{{SVG_NS}}}g[@id='card-placements']")
    assert [child.get("data-card-id") for child in placed] == ["synthetic-start"]
    assert root.get("data-open-tunnels") == "1"
    assert root.get("data-visible-water") == "0"
    assert root.get("data-collected-equipment-count") == "3"
    assert render_board_svg(board, collected_equipment=history) == svg


def test_svg_history_metadata_is_authoritative_and_handles_empty_equipment():
    board = _board()
    root = ET.fromstring(render_board_svg(
        board,
        collected_equipment=_equipment(),
        metadata={"collected_equipment": ["not-the-real-history"]},
    ))
    metadata = json.loads(root.find(f"{{{SVG_NS}}}metadata").text)
    assert metadata["collected_equipment"][0]["card_id"] == "raincoat<&1"
    assert metadata["collected_equipment"][1]["cells"][1]["water"] is True
    assert metadata["collected_equipment"][0]["cells"] != metadata["collected_equipment"][2]["cells"]
    empty_root = ET.fromstring(render_board_svg(board))
    assert empty_root.get("data-collected-equipment-count") == "0"
    assert _by_role(empty_root, "empty-equipment")[0].text == "No collected equipment"
    empty_metadata = json.loads(empty_root.find(f"{{{SVG_NS}}}metadata").text)
    assert empty_metadata["collected_equipment"] == []


def test_equipment_panel_wraps_without_overlapping_board_or_clipping():
    history = _equipment() * 4
    root = ET.fromstring(render_board_svg(_board(), collected_equipment=history))
    area = root.find(f"{{{SVG_NS}}}g[@id='collected-equipment']")
    cards = [child for child in area if child.get("data-card-id")]
    assert len(cards) == 12
    transforms = [tuple(map(int, card.get("transform")[10:-1].split())) for card in cards]
    assert len({y for _, y in transforms}) == 4
    assert min(y for _, y in transforms) > 58 + 30 + 48
    assert max(y for _, y in transforms) + 138 < int(root.get("height"))
    assert max(x for x, _ in transforms) + 228 < int(root.get("width"))


def test_batch_manifest_and_svg_carry_the_same_full_history(tmp_path):
    history = _equipment()
    record = FinalBoardExport(
        1, _board(), False, 7, seed=13, collected_equipment=history,
        ruleset_id="synthetic-rules", setup_id="synthetic-setup",
    )
    manifest = export_final_boards([record], tmp_path, experiment="synthetic", policy="fixture")
    game = manifest["games"][0]
    assert game["collected_equipment_count"] == 3
    svg_path = tmp_path / game["filename"]
    root = ET.parse(svg_path).getroot()
    metadata = json.loads(root.find(f"{{{SVG_NS}}}metadata").text)
    assert metadata["collected_equipment"] == game["collected_equipment"]
    assert metadata["ruleset_id"] == game["ruleset_id"] == record.ruleset_id
    assert metadata["setup_id"] == game["setup_id"] == record.setup_id
    assert [item["turn"] for item in game["collected_equipment"]] == [1, 3, 6]
    assert [item["player_index"] for item in game["collected_equipment"]] == [0, 1, 0]
    assert game["placement_count"] == 1
    assert json.loads((tmp_path / "manifest.json").read_text()) == manifest
    first_bytes = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    export_final_boards([record], tmp_path, experiment="synthetic", policy="fixture")
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == first_bytes


def test_capture_delegates_identical_choice_rng_and_terminal_hook():
    move = Move(Action.COLLECT, hand_index=0)

    class Inner:
        def choose(self, state, rng):
            self.observed = state
            self.random_value = rng.random()
            return move

        def on_game_finished(self, observation):
            self.final = observation

    inner = Inner()
    capture = FinalStateCapturePolicy(inner)
    observation = SimpleNamespace(board=_board(), collected_equipment=())
    rng, expected_rng = Random(123), Random(123)
    expected = expected_rng.random()
    assert capture.choose(observation, rng) is move
    assert inner.observed is observation
    assert inner.random_value == expected
    assert rng.getstate() == expected_rng.getstate()
    assert capture.final_observation is None
    terminal = GameState(board=_board(), draw_pile=[], hand=[], collected_equipment=_equipment()).observation()
    capture.on_game_finished(terminal)
    assert capture.final_observation is not terminal
    assert capture.last_state is capture.final_observation
    assert inner.final is not terminal and inner.final is not capture.final_observation
    assert inner.final.board is not capture.final_observation.board
    assert inner.final.board.cells == terminal.board.cells == capture.board.cells
    assert capture.collected_equipment == _equipment()
    assert rng.getstate() == expected_rng.getstate()


class _CollectPolicy:
    def __init__(self):
        self.observations = []
        self.draws = []

    def choose(self, state, rng):
        self.observations.append(state)
        self.draws.append(rng.random())
        return next((move for move in state.legal_moves() if move.action is Action.COLLECT), None)


@pytest.mark.parametrize("hand_size", [3, 6])
def test_terminal_capture_includes_last_collect_and_changes_no_outcome_or_rng(hand_size):
    cards = [item.card for item in _equipment()]
    if hand_size == 6:
        cards += [replace(card, card_id=f"{card.card_id}-copy") for card in cards]
    kwargs = dict(
        start_card=_card("start", {Direction.EAST}), deck=cards, hand_size=hand_size, seed=123,
    )
    ordinary = _CollectPolicy()
    plain_result = play_game(policy=ordinary, **kwargs)
    wrapped_inner = _CollectPolicy()
    capture = FinalStateCapturePolicy(wrapped_inner)
    wrapped_result = play_game(policy=capture, **kwargs)
    assert wrapped_result == plain_result
    assert wrapped_inner.draws == ordinary.draws
    assert len(capture.collected_equipment) == hand_size
    assert len(wrapped_inner.observations[-1].collected_equipment) == hand_size - 1
    assert capture.last_state.turns == hand_size
    assert not hasattr(capture.last_state, "draw_pile")
    assert {item.card_id for item in capture.collected_equipment} == {card.card_id for card in cards}
    record = FinalBoardExport.from_capture(game_index=1, capture=capture, result=wrapped_result, seed=123)
    assert record.collected_equipment == capture.collected_equipment
    assert record.ruleset_id == wrapped_result.ruleset_id
    assert record.setup_id == wrapped_result.setup_id
    assert record.turns == hand_size
    assert len(record.board.placements) == 1


def test_terminal_capture_works_when_game_ends_without_a_choice():
    capture = FinalStateCapturePolicy(_CollectPolicy())
    result = play_game(
        start_card=_card("closed-start", set()), deck=[], hand_size=3, policy=capture, seed=123,
    )
    assert capture.final_observation is not None
    assert capture.last_state.turns == 0
    assert capture.board.open_tunnels == 0
    assert capture.collected_equipment == ()
    assert FinalBoardExport.from_capture(game_index=1, capture=capture, result=result).turns == 0


def test_export_from_capture_rejects_missing_terminal_observation():
    capture = FinalStateCapturePolicy(_CollectPolicy())
    with pytest.raises(RuntimeError, match="no terminal observation"):
        FinalBoardExport.from_capture(game_index=1, capture=capture, result=SimpleNamespace())


def test_historical_v7_fails_before_output_without_reading_or_running_current_model(tmp_path):
    destination = tmp_path / "must-not-exist"
    with pytest.raises(RuntimeError, match=V7_HISTORICAL_CHECKOUT):
        export_v7(destination)
    assert not destination.exists()
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/export_final_boards.py"), "--experiment", "V7",
         "--output-dir", str(destination)],
        text=True, capture_output=True, check=False,
    )
    assert completed.returncode == 2
    assert V7_HISTORICAL_CHECKOUT in completed.stderr
    assert "No games were run" in completed.stderr
    assert "cannot be inferred from counters" in completed.stderr
    assert not destination.exists()
