"""Worker31: unchanged V4-250 with a collection-only opportunity tie break.

The policy scores the one canonical legal list once. Audit records are detached
JSON values and are never read by selection; they contain no hidden game zones.
"""

from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from random import Random

from .game import PlayerObservation
from .model import CardDefinition
from .moves import Action, Move
from .policies import BoundedMergeV4Policy
from .strategy import PolicyWeights, move_features, score_features


_V4_250_WEIGHTS = BoundedMergeV4Policy(setup_weight=250).weights


def canonical_digest(value: object) -> str:
    """Hash sorted compact UTF-8 JSON followed by exactly one newline."""
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ) + "\n"
    return sha256(encoded.encode("utf-8")).hexdigest()


def rng_state_digest(rng: Random) -> str:
    """Reading Random state does not consume randomness."""
    return canonical_digest(rng.getstate())


def move_record(move: Move | None) -> dict | None:
    if move is None:
        return None
    return {
        "action": move.action.value,
        "hand_index": move.hand_index,
        "origin": None if move.origin is None else list(move.origin),
        "quarter_turns": move.quarter_turns,
    }


def _card_record(card: CardDefinition) -> dict:
    return {
        "card_id": card.card_id,
        "material": None if card.material is None else card.material.value,
        "is_exit": card.is_exit,
        "cells": [
            {
                "x": cell.x,
                "y": cell.y,
                "tunnel_edges": sorted(edge.value for edge in cell.tunnel_edges),
                "water": cell.water,
            }
            for cell in card.cells
        ],
    }


def public_observation_record(observation: PlayerObservation) -> dict:
    """Serialize only the detached, public observation, without enumeration."""
    if type(observation) is not PlayerObservation:
        raise TypeError("expected a detached PlayerObservation")
    return {
        "board": {
            "cells": [
                {
                    "x": coord[0],
                    "y": coord[1],
                    "tunnel_edges": sorted(edge.value for edge in cell.tunnel_edges),
                    "water": cell.water,
                }
                for coord, cell in sorted(observation.board.cells.items())
            ],
            "placements": [asdict(item) for item in observation.board.placements],
        },
        "hand": [_card_record(card) for card in observation.hand],
        "raincoats": observation.raincoats,
        "ropes": observation.ropes,
        "exit_placed": observation.exit_placed,
        "exit_seen": observation.exit_seen,
        "turns": observation.turns,
        "set_aside_unplayable": observation.set_aside_unplayable,
        "collected_equipment": [
            {
                "card": _card_record(item.card),
                "turn": item.turn,
                "player_index": item.player_index,
            }
            for item in observation.collected_equipment
        ],
        "setup": asdict(observation.setup),
        "player_index": observation.player_index,
    }


class EquipmentOpportunityTiePolicy:
    """Collect the weakest placement opportunity only within an all-COLLECT tier.

    ``last_audit`` is replaced after each call, including no-move decisions.
    The caller supplies a decision ordinal, which is distinct from action turns
    when the engine refreshes an unplayable hand. No audit field affects choices.
    """

    __slots__ = ("last_audit",)

    def __init__(self) -> None:
        self.last_audit: dict | None = None

    @property
    def weights(self) -> PolicyWeights:
        return _V4_250_WEIGHTS

    def choose(self, state: PlayerObservation, rng: Random) -> Move | None:
        if type(state) is not PlayerObservation:
            raise TypeError("expected a detached PlayerObservation")

        moves = state.legal_moves()
        scored = [
            (score_features(move_features(state, move), self.weights), move)
            for move in moves
        ]
        primary_score = max((score for score, _ in scored), default=None)
        primary = [move for score, move in scored if score == primary_score]
        narrowed = primary
        eligible = bool(primary) and all(move.action is Action.COLLECT for move in primary)
        opportunities: list[dict] = []

        if eligible:
            # The maximum is empty for cards without a legal PLACE. None is
            # ordered explicitly below all integers, even arbitrarily negative
            # ones; it is not a numeric sentinel or a new scoring threshold.
            best_placement: dict[int, int] = {}
            for score, move in scored:
                if move.action is Action.PLACE:
                    previous = best_placement.get(move.hand_index)
                    if previous is None or score > previous:
                        best_placement[move.hand_index] = score
            keys = [
                (move.hand_index in best_placement, best_placement.get(move.hand_index, 0))
                for move in primary
            ]
            weakest = min(keys)
            narrowed = [move for move, key in zip(primary, keys) if key == weakest]
            opportunities = [
                {
                    "hand_index": move.hand_index,
                    "card_id": state.hand[move.hand_index].card_id,
                    "opportunity_score": best_placement.get(move.hand_index),
                }
                for move in primary
            ]

        # All diagnostics use data already available, never another legal-move
        # pass, simulation, scoring pass or preliminary baseline choice.
        primary_records = [move_record(move) for move in primary]
        narrowed_records = [move_record(move) for move in narrowed]
        audit = {
            "public_observation_sha256": canonical_digest(public_observation_record(state)),
            "legal_move_count": len(moves),
            "primary_tier": primary_records,
            "primary_tier_sha256": canonical_digest(primary_records),
            "primary_score": primary_score,
            "eligible_collect_tier": eligible,
            "collection_opportunities": opportunities,
            "opportunity_null_is_lowest": True,
            "narrowed_tier": narrowed_records,
            "narrowed_tier_sha256": canonical_digest(narrowed_records),
            "narrowed_tier_count": len(narrowed),
            "strict_narrowing": len(narrowed) < len(primary),
        }
        audit["rng_before_sha256"] = rng_state_digest(rng)
        chosen = rng.choice(narrowed) if narrowed else None
        audit["rng_after_sha256"] = rng_state_digest(rng)
        audit["chosen_move"] = move_record(chosen)
        self.last_audit = audit
        return chosen
