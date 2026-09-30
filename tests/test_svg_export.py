import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from bandido_alcatraz.board import Board, PlacementKind
from bandido_alcatraz.export_svg import (
    FinalBoardExport,
    FinalStateCapturePolicy,
    export_final_boards,
)
from bandido_alcatraz.model import CardDefinition, CellSpec, Direction
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.render_svg import render_board_svg
from bandido_alcatraz.simulate import play_game
from scripts.export_final_boards import (
    _final_records_sha256,
    _load_and_validate_v7_metadata,
    export_v7,
)
from scripts.run_worker26 import ImmediateTieV7Policy, final_record

ROOT = Path(__file__).resolve().parents[1]


def single(
    card_id: str,
    edges: set[Direction],
    *,
    water: bool = False,
    is_exit: bool = False,
) -> CardDefinition:
    return CardDefinition(
        card_id,
        (CellSpec(0, 0, frozenset(edges), water=water),),
        is_exit=is_exit,
    )


def markers(root: ET.Element, name: str) -> list[ET.Element]:
    return [
        element
        for element in root.iter()
        if element.attrib.get("data-marker") == name
    ]


def test_placement_history_captures_start_and_rotated_card_boundary() -> None:
    board = Board()
    board.seed(single("start", {Direction.EAST}))

    rotated = CardDefinition(
        "rotated",
        (
            CellSpec(0, 0, frozenset({Direction.SOUTH})),
            CellSpec(
                0,
                1,
                frozenset({Direction.NORTH, Direction.SOUTH}),
            ),
        ),
    )
    board.place(rotated, (1, 0), quarter_turns=1)

    start, placed = board.placements
    assert start.kind is PlacementKind.START
    assert start.placement_index == 0
    assert start.card_id == "start"
    assert start.cells == ((0, 0),)

    assert placed.kind is PlacementKind.ORDINARY
    assert placed.placement_index == 1
    assert placed.card_id == "rotated"
    assert placed.origin == (1, 0)
    assert placed.quarter_turns == 1
    assert placed.cells == ((1, 0), (2, 0))
    assert not placed.overlaps


def test_exit_placement_is_classified_and_clone_history_is_independent() -> None:
    board = Board()
    board.seed(single("start", {Direction.EAST, Direction.NORTH}))
    clone = board.clone()

    clone.place(single("exit", {Direction.WEST}, is_exit=True), (1, 0))

    assert len(board.placements) == 1
    assert len(clone.placements) == 2
    assert clone.placements[-1].kind is PlacementKind.EXIT
    assert clone.placements[-1].card_id == "exit"
    assert board.open_tunnels == 2
    assert clone.open_tunnels == 1


def test_water_overlay_records_covered_physical_placement() -> None:
    board = Board()
    board.seed(
        single(
            "water-start",
            {Direction.EAST, Direction.WEST},
            water=True,
        )
    )
    cover = CardDefinition(
        "cover",
        (
            CellSpec(
                0,
                0,
                frozenset({Direction.EAST, Direction.WEST}),
            ),
            CellSpec(1, 0, frozenset({Direction.WEST})),
        ),
    )

    board.place(cover, (0, 0))

    placement = board.placements[-1]
    assert placement.overlaps == ((0, 0),)
    assert placement.covered_placement_index == 0
    assert board.visible_water_cells == 0

    root = ET.fromstring(render_board_svg(board))
    overlay = markers(root, "water-overlap")
    assert len(overlay) == 1
    assert overlay[0].attrib["data-covered-placement-index"] == "0"


def test_svg_is_valid_and_marks_water_open_ends_dead_ends_and_card_boundary() -> None:
    board = Board()
    board.seed(
        CardDefinition(
            "start",
            (
                CellSpec(
                    0,
                    0,
                    frozenset({Direction.EAST}),
                    water=True,
                ),
                CellSpec(
                    1,
                    0,
                    frozenset({Direction.WEST, Direction.NORTH}),
                ),
            ),
        )
    )

    svg = render_board_svg(
        board,
        metadata={
            "experiment": "T",
            "game_index": 1,
            "seed": 7,
            "outcome": "loss",
            "turns": 3,
        },
    )
    root = ET.fromstring(svg)

    assert root.attrib["data-renderer"] == "bandido-alcatraz-final-board-v1"
    assert root.attrib["data-open-tunnels"] == "1"
    assert root.attrib["data-visible-water"] == "1"
    assert len(markers(root, "visible-water")) == 1
    assert len(markers(root, "open-end")) == 1
    assert len(markers(root, "dead-end")) == 1

    boundaries = [
        element
        for element in root.iter()
        if element.attrib.get("data-role") == "card-boundary"
    ]
    placements = [
        element
        for element in root.iter()
        if element.attrib.get("data-kind") == "start"
    ]
    assert len(boundaries) == 1
    assert len(placements) == 1
    assert placements[0].attrib["data-quarter-turns"] == "0"
    assert "START r0" in svg
    assert '"experiment":"T"' in svg


def test_svg_marks_exit_and_rotation_metadata() -> None:
    board = Board()
    board.seed(single("start", {Direction.EAST}))
    board.place(
        single("exit", {Direction.WEST}, is_exit=True),
        (1, 0),
        quarter_turns=0,
    )

    svg = render_board_svg(board)
    root = ET.fromstring(svg)
    exits = [
        element
        for element in root.iter()
        if element.attrib.get("data-kind") == "exit"
    ]
    assert len(exits) == 1
    assert exits[0].attrib["data-card-id"] == "exit"
    assert exits[0].attrib["data-quarter-turns"] == "0"
    assert "EXIT r0" in svg


def test_batch_export_is_stable_and_keeps_wins_and_losses(tmp_path: Path) -> None:
    win_board = Board()
    win_board.seed(single("start-win", {Direction.EAST}))
    loss_board = Board()
    loss_board.seed(single("start-loss", {Direction.NORTH}, water=True))

    manifest = export_final_boards(
        [
            FinalBoardExport(
                game_index=2,
                board=loss_board,
                seed=8,
                won=False,
                turns=11,
                reason="deck_exhausted",
            ),
            FinalBoardExport(
                game_index=1,
                board=win_board,
                seed=7,
                won=True,
                turns=4,
                reason="win",
            ),
        ],
        tmp_path,
        experiment="TEST",
        policy="synthetic",
    )

    assert manifest["game_count"] == 2
    assert manifest["wins"] == 1
    assert manifest["losses"] == 1
    assert [game["filename"] for game in manifest["games"]] == [
        "001-seed-7-win.svg",
        "002-seed-8-loss.svg",
    ]

    for filename in ("001-seed-7-win.svg", "002-seed-8-loss.svg"):
        ET.parse(tmp_path / filename)

    persisted = json.loads((tmp_path / "manifest.json").read_text())
    assert [game["game_index"] for game in persisted["games"]] == [1, 2]
    assert persisted["games"][1]["won"] is False


def test_final_record_checksum_is_order_independent_but_content_sensitive() -> None:
    rows = [
        {"seed": 2, "won": False, "turns": 10},
        {"seed": 1, "won": True, "turns": 5},
    ]
    assert _final_records_sha256(rows) == _final_records_sha256(list(reversed(rows)))

    changed = [dict(row) for row in rows]
    changed[0]["turns"] = 11
    assert _final_records_sha256(rows) != _final_records_sha256(changed)


def test_v7_metadata_is_exactly_pinned_without_running_the_batch() -> None:
    manifest, provenance = _load_and_validate_v7_metadata()

    assert manifest["evaluated_commit"] == "2e532c7e8a95397d586eb03cdfa840ea6a82e534"
    assert manifest["seed_range_inclusive"] == [1000, 1099]
    assert manifest["seed_count_per_policy"] == 100
    assert provenance["historical_reconstruction"] == "deterministic-resimulation"
    assert provenance["historical_placement_traces_persisted"] is False
    assert provenance["expected_win_seeds"] == [
        1008,
        1031,
        1047,
        1086,
        1088,
        1096,
        1097,
    ]
    assert (
        provenance["final_records_sha256"]
        == "d1921f03fa41d45140f482c4cb75ab414d09ce1de6f1a59081eecc2390d858da"
    )
    assert (
        provenance["candidate_and_harness_blob"]
        == "94bc4ba6472404e0d414890e3e0d86145c78117a"
    )
    assert (
        provenance["observer_board_blob"]
        == "e04e9255ecc9c8181ca49903dfb6501a67c8a482"
    )
    assert (
        provenance["raw_artifact_archive_sha256"]
        == "734f6a271271fa4338c443f75460dd26e3e148d16c937f90ceb88eb3dae5602e"
    )
    assert (
        provenance["receipt_json_sha256"]
        == "635064443ef9b27e01ff387c7a58917b85582f8d48592dc3ec2d2eae372f2e64"
    )


def test_v7_export_rejects_invalid_worker_count_before_simulation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="workers must be positive"):
        export_v7(tmp_path, workers=0)


def test_real_v7_win_and_water_loss_preserve_historical_outcomes_and_render() -> None:
    deck = load_real_deck(ROOT / "data")
    expected = {
        1008: {
            "equipment_ready": True,
            "exit_equipment_water_ready": True,
            "exit_placed": True,
            "final_open_tunnels": 0,
            "raincoats": 5,
            "reason": "win",
            "ropes": 6,
            "seed": 1008,
            "turns": 33,
            "visible_water": 0,
            "won": True,
        },
        1099: {
            "equipment_ready": True,
            "exit_equipment_water_ready": False,
            "exit_placed": True,
            "final_open_tunnels": 17,
            "raincoats": 5,
            "reason": "deck_exhausted",
            "ropes": 2,
            "seed": 1099,
            "turns": 69,
            "visible_water": 2,
            "won": False,
        },
    }

    seen_rotations: set[int] = set()
    for seed, expected_row in expected.items():
        recorder = FinalStateCapturePolicy(ImmediateTieV7Policy())
        result = play_game(
            start_card=deck.start_easy,
            deck=deck.draw_deck(),
            hand_size=3,
            policy=recorder,
            seed=seed,
        )

        assert final_record(seed, result) == expected_row
        assert recorder.last_state is not None
        board = recorder.last_state.board
        assert board.placements[0].kind is PlacementKind.START
        assert any(
            placement.kind is PlacementKind.EXIT
            for placement in board.placements
        )
        seen_rotations.update(
            placement.quarter_turns for placement in board.placements
        )

        root = ET.fromstring(
            render_board_svg(
                board,
                metadata={
                    "experiment": "V7",
                    "game_index": seed - 999,
                    "seed": seed,
                    "outcome": "win" if result.won else "loss",
                    "turns": result.turns,
                },
            )
        )
        assert root.attrib["data-open-tunnels"] == str(result.open_tunnels)
        assert root.attrib["data-visible-water"] == str(
            result.visible_water_cells
        )
        assert len(markers(root, "visible-water")) == result.visible_water_cells
        assert any(
            element.attrib.get("data-kind") == "exit"
            for element in root.iter()
        )

    assert len(seen_rotations) >= 2
