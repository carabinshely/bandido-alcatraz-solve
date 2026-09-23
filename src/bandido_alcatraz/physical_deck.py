from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .deck_data import load_deck_observations
from .model import CardDefinition, Material
from .photo_geometry import PhotoGeometry, card_from_photo_geometry


@dataclass(frozen=True, slots=True)
class RealDeck:
    ordinary_cards: tuple[CardDefinition, ...]
    exit_card: CardDefinition
    start_easy: CardDefinition
    start_normal: CardDefinition

    def draw_deck(self) -> list[CardDefinition]:
        return [*self.ordinary_cards, self.exit_card]


def load_real_deck(data_dir: str | Path) -> RealDeck:
    root = Path(data_dir)
    deck = json.loads((root / "deck-v1.json").read_text(encoding="utf-8"))

    if not deck["status"]["ordinary_card_inventory_complete"]:
        raise ValueError("ordinary card inventory is incomplete")
    if not deck["status"]["ordinary_placement_geometry_complete"]:
        raise ValueError("ordinary placement geometry is incomplete")
    if not deck["status"]["exact_water_half_overlay_compatibility_complete"]:
        raise ValueError("water overlay compatibility is incomplete")

    instances = deck["instances"]
    if len(instances) != 68:
        raise ValueError(f"expected 68 ordinary cards, got {len(instances)}")

    ordinary: list[CardDefinition] = []
    for item in instances:
        material = (
            Material(item["material"])
            if item["material"] is not None
            else None
        )
        ordinary.append(
            card_from_photo_geometry(
                item["card_id"],
                geometry=PhotoGeometry(
                    frozenset(item["external_ports"]),
                    bool(item["internal_bridge"]),
                ),
                material=material,
                water_half=item["water_half"],
            )
        )

    observations = load_deck_observations(root / "deck-observations-v0.json")
    if observations.exit_geometry is None:
        raise ValueError("EXIT geometry is missing")
    if observations.start_easy_geometry is None:
        raise ValueError("easy START geometry is missing")
    if observations.start_normal_geometry is None:
        raise ValueError("normal START geometry is missing")

    return RealDeck(
        ordinary_cards=tuple(ordinary),
        exit_card=observations.exit_geometry.definition(),
        start_easy=observations.start_easy_geometry.definition(),
        start_normal=observations.start_normal_geometry.definition(),
    )
