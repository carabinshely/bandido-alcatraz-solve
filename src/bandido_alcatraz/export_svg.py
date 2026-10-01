from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
import json
from pathlib import Path
from random import Random
from typing import TYPE_CHECKING

from .board import Board
from .game import CollectedEquipment, PlayerObservation
from .moves import Move
from .policies import Policy
from .rules import RULESET_ID
from .render_svg import collected_equipment_metadata, write_board_svg

if TYPE_CHECKING:
    from .simulate import GameResult


class FinalStateCapturePolicy:
    """Transparent policy wrapper retaining public, terminal observations.

    ``choose`` receives a detached observation, so the terminal callback is
    essential: the last pre-action observation is not the final game state.
    No hidden draw order or extra RNG consumption is introduced here.
    """

    def __init__(self, inner: Policy) -> None:
        self.inner = inner
        self.last_state: PlayerObservation | None = None
        self.final_observation: PlayerObservation | None = None

    def choose(self, state: PlayerObservation, rng: Random) -> Move | None:
        self.final_observation = None
        self.last_state = state
        return self.inner.choose(state, rng)

    def on_game_finished(self, observation: PlayerObservation) -> None:
        captured = replace(observation, board=observation.board.clone())
        self.last_state = captured
        self.final_observation = captured
        callback = getattr(self.inner, "on_game_finished", None)
        if callback is not None:
            callback(replace(observation, board=observation.board.clone()))

    @property
    def board(self) -> Board:
        if self.last_state is None:
            raise RuntimeError("game terminated before the policy observed a state")
        return self.last_state.board

    @property
    def collected_equipment(self) -> tuple[CollectedEquipment, ...]:
        if self.last_state is None:
            raise RuntimeError("game terminated before the policy observed a state")
        return self.last_state.collected_equipment


@dataclass(frozen=True, slots=True)
class FinalBoardExport:
    game_index: int
    board: Board
    won: bool
    turns: int
    seed: int | None = None
    reason: str | None = None
    collected_equipment: tuple[CollectedEquipment, ...] = ()
    ruleset_id: str | None = None
    setup_id: str | None = None

    @classmethod
    def from_capture(
        cls,
        *,
        game_index: int,
        capture: FinalStateCapturePolicy,
        result: GameResult,
        seed: int | None = None,
    ) -> FinalBoardExport:
        """Build a complete current-model record only after the terminal hook."""
        observation = capture.final_observation
        if observation is None:
            raise RuntimeError("no terminal observation has been captured")
        expected = {
            'won': observation.won, 'turns': observation.turns,
            'open_tunnels': observation.board.open_tunnels,
            'visible_water_cells': observation.board.visible_water_cells,
            'raincoats': observation.raincoats, 'ropes': observation.ropes,
            'exit_placed': observation.exit_placed, 'ruleset_id': RULESET_ID,
            'setup_id': observation.setup.setup_id,
        }
        for key, value in expected.items():
            if getattr(result, key) != value:
                raise ValueError(f'captured observation/result mismatch: {key}')
        return cls(
            game_index=game_index,
            board=observation.board.clone(),
            won=result.won,
            turns=result.turns,
            seed=seed,
            reason=result.reason,
            collected_equipment=observation.collected_equipment,
            ruleset_id=result.ruleset_id,
            setup_id=result.setup_id,
        )


def stable_svg_filename(record: FinalBoardExport) -> str:
    seed_part = f"-seed-{record.seed}" if record.seed is not None else ""
    outcome = "win" if record.won else "loss"
    return f"{record.game_index:03d}{seed_part}-{outcome}.svg"


def export_final_boards(
    records: Iterable[FinalBoardExport],
    output_dir: str | Path,
    *,
    experiment: str,
    policy: str,
    provenance: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Write one deterministic SVG per supplied final board plus manifest.json."""
    ordered = sorted(records, key=lambda record: record.game_index)
    indexes = [record.game_index for record in ordered]
    if len(indexes) != len(set(indexes)):
        raise ValueError("game_index values must be unique")

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    games: list[dict[str, object]] = []
    for record in ordered:
        filename = stable_svg_filename(record)
        metadata: dict[str, object] = {
            "experiment": experiment,
            "policy": policy,
            "game_index": record.game_index,
            "seed": record.seed,
            "outcome": "win" if record.won else "loss",
            "won": record.won,
            "turns": record.turns,
            "reason": record.reason,
            "ruleset_id": record.ruleset_id,
            "setup_id": record.setup_id,
            "final_open_tunnels": record.board.open_tunnels,
            "final_visible_water": record.board.visible_water_cells,
        }
        write_board_svg(
            record.board,
            destination / filename,
            metadata=metadata,
            collected_equipment=record.collected_equipment,
        )
        games.append(
            {
                "filename": filename,
                "game_index": record.game_index,
                "seed": record.seed,
                "won": record.won,
                "turns": record.turns,
                "reason": record.reason,
                "ruleset_id": record.ruleset_id,
                "setup_id": record.setup_id,
                "final_open_tunnels": record.board.open_tunnels,
                "final_visible_water": record.board.visible_water_cells,
                "placement_count": len(record.board.placements),
                "collected_equipment": collected_equipment_metadata(record.collected_equipment),
                "collected_equipment_count": len(record.collected_equipment),
            }
        )

    manifest: dict[str, object] = {
        "schema": "bandido-final-board-svg-batch-v1",
        "experiment": experiment,
        "policy": policy,
        "game_count": len(games),
        "wins": sum(bool(game["won"]) for game in games),
        "losses": sum(not bool(game["won"]) for game in games),
        "games": games,
    }
    if provenance:
        manifest["provenance"] = dict(provenance)

    (destination / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest
