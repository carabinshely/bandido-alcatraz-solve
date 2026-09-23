from __future__ import annotations

from dataclasses import dataclass

from .model import CardDefinition, Material


@dataclass(frozen=True, slots=True)
class PublishedDeckFacts:
    total_cards: int = 68
    water_cards: int = 4
    rope_cards: int = 8
    raincoat_cards: int = 12


PUBLISHED_DECK_FACTS = PublishedDeckFacts()


def validate_complete_catalog(cards: list[CardDefinition]) -> list[str]:
    """Return aggregate mismatches for a candidate complete 68-card catalog."""
    facts = PUBLISHED_DECK_FACTS
    errors: list[str] = []

    if len(cards) != facts.total_cards:
        errors.append(f"expected {facts.total_cards} cards, got {len(cards)}")

    water = sum(card.has_water for card in cards)
    ropes = sum(card.material is Material.ROPE for card in cards)
    raincoats = sum(card.material is Material.RAINCOAT for card in cards)

    for label, actual, expected in (
        ("water", water, facts.water_cards),
        ("rope", ropes, facts.rope_cards),
        ("raincoat", raincoats, facts.raincoat_cards),
    ):
        if actual != expected:
            errors.append(f"expected {expected} {label} cards, got {actual}")

    return errors
