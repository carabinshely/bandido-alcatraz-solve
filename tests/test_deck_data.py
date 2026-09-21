import json
from pathlib import Path

from bandido_alcatraz.deck_data import (
    load_deck_observations,
    validate_deck_observations,
)


ROOT = Path(__file__).parents[1]


def _observed_card_type(*, multiplicity: int | None) -> dict:
    return {
        "id": "observed-shape",
        "multiplicity": multiplicity,
        "material": None,
        "cells": [
            {
                "x": 0,
                "y": 0,
                "tunnel_edges": ["E"],
                "water": False,
            },
            {
                "x": 1,
                "y": 0,
                "tunnel_edges": ["W"],
                "water": False,
            },
        ],
        "source": "https://example.test/source",
        "confidence": "observed",
    }


def _special_geometry() -> dict:
    return {
        "cells": [
            {
                "x": 0,
                "y": 0,
                "tunnel_edges": ["E", "W"],
                "water": False,
            }
        ],
        "source": "https://example.test/special",
        "confidence": "observed",
    }


def _raw() -> dict:
    return json.loads(
        (ROOT / "data" / "deck-observations-v0.json").read_text()
    )


def test_checked_in_observations_load() -> None:
    observations = load_deck_observations(
        ROOT / "data" / "deck-observations-v0.json"
    )

    assert observations.game == "Bandido Alcatraz"
    assert not observations.complete
    assert observations.aggregate_facts.ordinary_cards == 68
    assert observations.aggregate_facts.water_cards == 4
    assert observations.aggregate_facts.rope_cards == 8
    assert observations.aggregate_facts.raincoat_cards == 12
    assert observations.exit_geometry is None
    assert observations.start_easy_geometry is None
    assert observations.start_normal_geometry is None


def test_incomplete_catalog_does_not_require_guessed_multiplicity() -> None:
    raw = _raw()
    raw["card_types"] = [_observed_card_type(multiplicity=None)]

    assert validate_deck_observations(raw) == []


def test_card_type_parses_to_engine_definition(tmp_path: Path) -> None:
    raw = _raw()
    raw["card_types"] = [_observed_card_type(multiplicity=None)]
    path = tmp_path / "deck.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    observations = load_deck_observations(path)

    definition = observations.card_types[0].definition()
    assert definition.card_id == "observed-shape"
    assert len(definition.cells) == 2
    assert not definition.is_exit


def test_special_geometry_parses_exit_role(tmp_path: Path) -> None:
    raw = _raw()
    raw["special_geometry"]["exit"] = _special_geometry()
    path = tmp_path / "deck.json"
    path.write_text(json.dumps(raw), encoding="utf-8")

    observations = load_deck_observations(path)

    assert observations.exit_geometry is not None
    definition = observations.exit_geometry.definition()
    assert definition.card_id == "exit"
    assert definition.is_exit


def test_complete_catalog_requires_total_68() -> None:
    raw = _raw()
    raw["complete"] = True
    raw["card_types"] = [_observed_card_type(multiplicity=67)]
    raw["special_geometry"] = {
        "exit": _special_geometry(),
        "start_easy": _special_geometry(),
        "start_normal": _special_geometry(),
    }

    errors = validate_deck_observations(raw)

    assert "complete catalog multiplicities must sum to 68 ordinary cards" in errors


def test_complete_catalog_requires_all_special_geometry() -> None:
    raw = _raw()
    raw["complete"] = True
    raw["card_types"] = [_observed_card_type(multiplicity=68)]

    errors = validate_deck_observations(raw)

    assert (
        "complete catalog requires exit, start_easy, and start_normal geometry"
        in errors
    )


def test_special_geometry_rejects_card_only_fields() -> None:
    raw = _raw()
    geometry = _special_geometry()
    geometry["material"] = "rope"
    geometry["multiplicity"] = 1
    raw["special_geometry"]["exit"] = geometry

    errors = validate_deck_observations(raw)

    assert "special_geometry.exit.material is not allowed" in errors
    assert "special_geometry.exit.multiplicity is not allowed" in errors


def test_duplicate_observation_ids_are_rejected() -> None:
    raw = _raw()
    raw["observations"].append(dict(raw["observations"][0]))

    errors = validate_deck_observations(raw)

    assert any("duplicate observation id" in error for error in errors)


def test_owner_photo_provenance_is_allowed_without_committing_images() -> None:
    raw = _raw()
    raw["observations"].append(
        {
            "id": "owner-photo",
            "kind": "physical_deck_inventory",
            "claim": "Direct physical-deck observation.",
            "confidence": "direct-owner-evidence",
            "source": "owner-photo-set:2026-09-21",
        }
    )

    assert validate_deck_observations(raw) == []


def test_checked_in_physical_inventory_arithmetic() -> None:
    raw = _raw()
    facts = raw["aggregate_facts"]
    inventory = raw["derived_inventory"]

    assert inventory["non_start_draw_cards"] == (
        facts["ordinary_cards"] + facts["exit_cards"]
    ) == 69
    assert inventory["distinct_physical_cards_total"] == (
        facts["ordinary_cards"] + facts["exit_cards"] + facts["start_tiles"]
    ) == 70
    assert inventory["photographed_card_faces"] == (
        facts["ordinary_cards"]
        + facts["exit_cards"]
        + inventory["start_faces_photographed"]
    ) == 71
