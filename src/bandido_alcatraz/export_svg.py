from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from random import Random

from .board import Board
from .game import GameState
from .moves import Move
from .policies import Policy
from .render_svg import write_board_svg


class FinalStateCapturePolicy:
    """Transparent policy wrapper retaining the live final GameState reference."""

    def __init__(self, inner: Policy) -> None:
        self.inner = inner
        self.last_state: GameState | None = None

    def choose(self, state: GameState, rng: Random) -> Move | None:
        self.last_state = state
        return self.inner.choose(state, rng)

    @property
    def board(self) -> Board:
        if self.last_state is None:
            raise RuntimeError("game terminated before the policy observed a state")
        return self.last_state.board


@dataclass(frozen=True, slots=True)
class FinalBoardExport:
    game_index: int
    board: Board
    won: bool
    turns: int
    seed: int | None = None
    reason: str | None = None


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
            "final_open_tunnels": record.board.open_tunnels,
            "final_visible_water": record.board.visible_water_cells,
        }
        write_board_svg(
            record.board,
            destination / filename,
            metadata=metadata,
        )
        games.append(
            {
                "filename": filename,
                "game_index": record.game_index,
                "seed": record.seed,
                "won": record.won,
                "turns": record.turns,
                "reason": record.reason,
                "final_open_tunnels": record.board.open_tunnels,
                "final_visible_water": record.board.visible_water_cells,
                "placement_count": len(record.board.placements),
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
