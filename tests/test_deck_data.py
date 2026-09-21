import json
from pathlib import Path

import pytest

from bandido_alcatraz.deck_data import (
    load_deck_observations,
    validate_deck_observations,
)


ROOT = Path(__file__).parents[1]


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


def test_incomplete_catalog_does_not_require_guessed_multiplicity() -> None:
    raw = json.loads(
        (ROOT / "data" / "deck-observations-v0.json").read_text()
    )
    raw["card_types"] = [{"id": "observed-shape", "multiplicity": None}]

    assert validate_deck_observations(raw) == []


def test_complete_catalog_requires_total_68() -> None:
    raw = json.loads(
        (ROOT / "data" / "deck-observations-v0.json").read_text()
    )
    raw["complete"] = True
    raw["card_types"] = [{"id": "shape", "multiplicity": 67}]

    errors = validate_deck_observations(raw)

    assert "complete catalog multiplicities must sum to 68 ordinary cards" in errors


def test_duplicate_observation_ids_are_rejected() -> None:
    raw = json.loads(
        (ROOT / "data" / "deck-observations-v0.json").read_text()
    )
    raw["observations"].append(dict(raw["observations"][0]))

    errors = validate_deck_observations(raw)

    assert any("duplicate observation id" in error for error in errors)
