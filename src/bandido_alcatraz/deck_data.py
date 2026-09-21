from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .model import CardDefinition, CellSpec, Direction, Material


@dataclass(frozen=True, slots=True)
class AggregateFacts:
    ordinary_cards: int
    water_cards: int
    rope_cards: int
    raincoat_cards: int
    start_tiles: int
    exit_cards: int


@dataclass(frozen=True, slots=True)
class CatalogCardType:
    card_id: str
    multiplicity: int | None
    material: Material | None
    cells: tuple[CellSpec, ...]
    source: str
    confidence: str

    def definition(self) -> CardDefinition:
        return CardDefinition(
            card_id=self.card_id,
            cells=self.cells,
            material=self.material,
        )


@dataclass(frozen=True, slots=True)
class DeckObservations:
    format_version: int
    game: str
    complete: bool
    aggregate_facts: AggregateFacts
    observations: tuple[dict[str, Any], ...]
    card_types: tuple[CatalogCardType, ...]


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
        card_types=tuple(_parse_card_type(item) for item in raw["card_types"]),
    )


def _parse_card_type(raw: dict[str, Any]) -> CatalogCardType:
    material_value = raw.get("material")
    material = Material(material_value) if material_value is not None else None
    cells = tuple(
        CellSpec(
            x=cell["x"],
            y=cell["y"],
            tunnel_edges=frozenset(Direction(edge) for edge in cell["tunnel_edges"]),
            water=cell.get("water", False),
        )
        for cell in raw["cells"]
    )
    return CatalogCardType(
        card_id=raw["id"],
        multiplicity=raw.get("multiplicity"),
        material=material,
        cells=cells,
        source=raw["source"],
        confidence=raw["confidence"],
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

    card_ids: set[str] = set()
    multiplicities: list[int] = []
    for index, card_type in enumerate(card_types):
        prefix = f"card_types[{index}]"
        if not isinstance(card_type, dict):
            errors.append(f"{prefix} must be an object")
            continue

        card_id = card_type.get("id")
        if not isinstance(card_id, str) or not card_id:
            errors.append(f"{prefix}.id must be non-empty")
        elif card_id in card_ids:
            errors.append(f"duplicate card type id: {card_id}")
        else:
            card_ids.add(card_id)

        multiplicity = card_type.get("multiplicity")
        if multiplicity is not None and (
            not isinstance(multiplicity, int)
            or isinstance(multiplicity, bool)
            or multiplicity <= 0
        ):
            errors.append(f"{prefix}.multiplicity must be null or a positive integer")
        elif isinstance(multiplicity, int):
            multiplicities.append(multiplicity)

        material = card_type.get("material")
        if material not in (None, "raincoat", "rope"):
            errors.append(f"{prefix}.material must be null, raincoat, or rope")

        source = card_type.get("source")
        if not isinstance(source, str) or not source.startswith("https://"):
            errors.append(f"{prefix}.source must be an https URL")

        confidence = card_type.get("confidence")
        if confidence not in ("authoritative", "observed", "inferred", "proxy"):
            errors.append(
                f"{prefix}.confidence must be authoritative, observed, inferred, or proxy"
            )

        cells = card_type.get("cells")
        if not isinstance(cells, list) or not cells:
            errors.append(f"{prefix}.cells must be a non-empty list")
            continue

        coords: set[tuple[int, int]] = set()
        for cell_index, cell in enumerate(cells):
            cell_prefix = f"{prefix}.cells[{cell_index}]"
            if not isinstance(cell, dict):
                errors.append(f"{cell_prefix} must be an object")
                continue
            x, y = cell.get("x"), cell.get("y")
            if not isinstance(x, int) or isinstance(x, bool):
                errors.append(f"{cell_prefix}.x must be an integer")
            if not isinstance(y, int) or isinstance(y, bool):
                errors.append(f"{cell_prefix}.y must be an integer")
            if isinstance(x, int) and isinstance(y, int):
                coord = (x, y)
                if coord in coords:
                    errors.append(f"{prefix} has duplicate cell coordinate {coord}")
                coords.add(coord)

            edges = cell.get("tunnel_edges")
            if (
                not isinstance(edges, list)
                or any(edge not in ("N", "E", "S", "W") for edge in edges)
                or len(edges) != len(set(edges))
            ):
                errors.append(
                    f"{cell_prefix}.tunnel_edges must be unique N/E/S/W values"
                )
            if not isinstance(cell.get("water", False), bool):
                errors.append(f"{cell_prefix}.water must be boolean")

    if raw.get("complete") is True:
        if any(card_type.get("multiplicity") is None for card_type in card_types if isinstance(card_type, dict)):
            errors.append("complete catalog cannot contain null multiplicity")
        if sum(multiplicities) != expected["ordinary_cards"]:
            errors.append(
                "complete catalog multiplicities must sum to 68 ordinary cards"
            )

    return errors
