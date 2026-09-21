from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class AggregateFacts:
    ordinary_cards: int
    water_cards: int
    rope_cards: int
    raincoat_cards: int
    start_tiles: int
    exit_cards: int


@dataclass(frozen=True, slots=True)
class DeckObservations:
    format_version: int
    game: str
    complete: bool
    aggregate_facts: AggregateFacts
    observations: tuple[dict[str, Any], ...]
    card_types: tuple[dict[str, Any], ...]


def load_deck_observations(path: str | Path) -> DeckObservations:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    errors = validate_deck_observations(raw)
    if errors:
        raise ValueError("; ".join(errors))

    facts = raw["aggregate_facts"]
    return DeckObservations(
        format_version=raw["format_version"],
        game=raw["game"],
        complete=raw["complete"],
        aggregate_facts=AggregateFacts(**facts),
        observations=tuple(raw["observations"]),
        card_types=tuple(raw["card_types"]),
    )


def validate_deck_observations(raw: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if raw.get("format_version") != 1:
        errors.append("format_version must be 1")
    if raw.get("game") != "Bandido Alcatraz":
        errors.append("game must be 'Bandido Alcatraz'")
    if not isinstance(raw.get("complete"), bool):
        errors.append("complete must be boolean")

    facts = raw.get("aggregate_facts")
    expected = {
        "ordinary_cards": 68,
        "water_cards": 4,
        "rope_cards": 8,
        "raincoat_cards": 12,
        "start_tiles": 1,
        "exit_cards": 1,
    }
    if not isinstance(facts, dict):
        errors.append("aggregate_facts must be an object")
    else:
        for field, value in expected.items():
            if facts.get(field) != value:
                errors.append(f"{field} must be {value}")

    observations = raw.get("observations")
    if not isinstance(observations, list):
        errors.append("observations must be a list")
    else:
        seen_ids: set[str] = set()
        for index, observation in enumerate(observations):
            if not isinstance(observation, dict):
                errors.append(f"observations[{index}] must be an object")
                continue
            observation_id = observation.get("id")
            if not isinstance(observation_id, str) or not observation_id:
                errors.append(f"observations[{index}].id must be non-empty")
            elif observation_id in seen_ids:
                errors.append(f"duplicate observation id: {observation_id}")
            else:
                seen_ids.add(observation_id)
            source = observation.get("source")
            if not isinstance(source, str) or not source.startswith("https://"):
                errors.append(f"observations[{index}].source must be an https URL")

    card_types = raw.get("card_types")
    if not isinstance(card_types, list):
        errors.append("card_types must be a list")
        card_types = []

    if raw.get("complete") is True:
        multiplicities: list[int] = []
        for index, card_type in enumerate(card_types):
            if not isinstance(card_type, dict):
                errors.append(f"card_types[{index}] must be an object")
                continue
            multiplicity = card_type.get("multiplicity")
            if not isinstance(multiplicity, int) or isinstance(multiplicity, bool) or multiplicity <= 0:
                errors.append(
                    f"card_types[{index}].multiplicity must be a positive integer "
                    "when complete=true"
                )
            else:
                multiplicities.append(multiplicity)
        if sum(multiplicities) != expected["ordinary_cards"]:
            errors.append(
                "complete catalog multiplicities must sum to 68 ordinary cards"
            )

    return errors
