from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT, ROOT / "src"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from bandido_alcatraz.export_svg import FinalBoardExport, export_final_boards
from bandido_alcatraz.physical_deck import load_real_deck
from bandido_alcatraz.simulate import play_game
from scripts.run_worker26 import ImmediateTieV7Policy, final_record

V7_MANIFEST = (
    ROOT
    / "experiments"
    / "real-deck-policy-v7"
    / "immediate-tie-development-2026-09-30.manifest.json"
)
V7_EXPORT_PROVENANCE = (
    ROOT
    / "experiments"
    / "real-deck-policy-v7"
    / "svg-export-provenance-2026-09-30.json"
)


class RecordingPolicy:
    """Delegate policy decisions while retaining the live final GameState reference."""

    def __init__(self, inner: Any) -> None:
        self.inner = inner
        self.last_state = None

    def choose(self, state, rng):
        self.last_state = state
        return self.inner.choose(state, rng)


def _git_blob_sha(path: Path) -> str:
    content = path.read_bytes()
    header = f"blob {len(content)}\0".encode()
    return hashlib.sha1(header + content).hexdigest()


def _final_records_sha256(rows: list[dict[str, object]]) -> str:
    canonical = json.dumps(
        sorted(rows, key=lambda row: int(row["seed"])),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _load_and_validate_v7_metadata() -> tuple[dict[str, object], dict[str, object]]:
    manifest = json.loads(V7_MANIFEST.read_text(encoding="utf-8"))
    provenance = json.loads(V7_EXPORT_PROVENANCE.read_text(encoding="utf-8"))

    if manifest["experiment_id"] != provenance["experiment_id"]:
        raise RuntimeError("V7 experiment id does not match SVG export provenance")
    if manifest["evaluated_commit"] != provenance["evaluated_commit"]:
        raise RuntimeError("V7 evaluated commit does not match SVG export provenance")
    if manifest["seed_range_inclusive"] != provenance["seed_range_inclusive"]:
        raise RuntimeError("V7 seed range does not match SVG export provenance")
    if manifest["seed_count_per_policy"] != provenance["seed_count"]:
        raise RuntimeError("V7 seed count does not match SVG export provenance")

    fixed = manifest["fixed_configuration"]

    # Historical V7 is only an exact board reconstruction while every
    # simulation-relevant source remains frozen. The one intentional exception
    # is board.py: Issue #23 adds observer-only placement history, and that exact
    # reviewed observer blob is pinned separately.
    for relative_path, expected_blob in sorted(
        fixed["canonical_source_blobs"].items()
    ):
        if relative_path == "src/bandido_alcatraz/board.py":
            continue
        actual_blob = _git_blob_sha(ROOT / relative_path)
        if actual_blob != expected_blob:
            raise RuntimeError(
                "V7 canonical source drift: "
                f"{relative_path} expected {expected_blob}, got {actual_blob}"
            )

    candidate_path = ROOT / "scripts" / "run_worker26.py"
    if _git_blob_sha(candidate_path) != provenance["candidate_and_harness_blob"]:
        raise RuntimeError("V7 frozen candidate/harness source has drifted")

    observer_board_path = ROOT / "src" / "bandido_alcatraz" / "board.py"
    if _git_blob_sha(observer_board_path) != provenance["observer_board_blob"]:
        raise RuntimeError("V7 placement-history Board observer source has drifted")

    deck_path = ROOT / str(fixed["deck_file"])
    exit_path = ROOT / str(fixed["exit_geometry_file"])
    if _git_blob_sha(deck_path) != fixed["deck_blob"]:
        raise RuntimeError("V7 deck-v1.json no longer matches the evaluated Git blob")
    if _git_blob_sha(exit_path) != fixed["exit_geometry_blob"]:
        raise RuntimeError(
            "V7 deck-observations-v0.json no longer matches the evaluated Git blob"
        )

    candidate = fixed["candidate"]
    if candidate["class"] != "ImmediateTieV7Policy":
        raise RuntimeError("unexpected V7 candidate policy")
    return manifest, provenance


def _simulate_v7() -> tuple[
    list[FinalBoardExport],
    list[dict[str, object]],
    dict[str, object],
    dict[str, object],
]:
    manifest, provenance = _load_and_validate_v7_metadata()
    start_seed, end_seed = (int(value) for value in manifest["seed_range_inclusive"])
    seeds = range(start_seed, end_seed + 1)
    deck = load_real_deck(ROOT / "data")

    exports: list[FinalBoardExport] = []
    final_rows: list[dict[str, object]] = []
    for game_index, seed in enumerate(seeds, start=1):
        recorder = RecordingPolicy(ImmediateTieV7Policy())
        result = play_game(
            start_card=deck.start_easy,
            deck=deck.draw_deck(),
            hand_size=3,
            policy=recorder,
            seed=seed,
        )
        if recorder.last_state is None:
            raise RuntimeError(f"V7 seed {seed} terminated before policy observation")

        row = final_record(seed, result)
        final_rows.append(row)
        exports.append(
            FinalBoardExport(
                game_index=game_index,
                board=recorder.last_state.board,
                seed=seed,
                won=result.won,
                turns=result.turns,
                reason=result.reason,
            )
        )

    actual_hash = _final_records_sha256(final_rows)
    expected_hash = str(provenance["final_records_sha256"])
    if actual_hash != expected_hash:
        raise RuntimeError(
            "V7 deterministic re-simulation does not match the durable 2026-09-30 "
            f"receipt: expected {expected_hash}, got {actual_hash}. "
            "No SVGs were written."
        )

    actual_wins = [int(row["seed"]) for row in final_rows if bool(row["won"])]
    expected_wins = [int(seed) for seed in provenance["expected_win_seeds"]]
    if actual_wins != expected_wins:
        raise RuntimeError(
            f"V7 win-seed mismatch: expected {expected_wins}, got {actual_wins}"
        )

    return exports, final_rows, manifest, provenance


def export_v7(output_dir: str | Path) -> dict[str, object]:
    exports, final_rows, manifest, provenance = _simulate_v7()
    return export_final_boards(
        exports,
        output_dir,
        experiment="V7",
        policy="ImmediateTieV7Policy",
        provenance={
            "reconstruction": "deterministic-resimulation",
            "source_manifest": str(V7_MANIFEST.relative_to(ROOT)),
            "evaluated_commit": manifest["evaluated_commit"],
            "raw_receipt_drive_url": provenance["raw_receipt_drive_url"],
            "raw_receipt_sha256": provenance["raw_receipt_sha256"],
            "final_records_sha256": _final_records_sha256(final_rows),
            "final_records_checksum_verified": True,
            "seed_range_inclusive": manifest["seed_range_inclusive"],
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export final Bandido: Alcatraz boards as standalone SVG files."
    )
    parser.add_argument(
        "--experiment",
        required=True,
        help="Named experiment to reconstruct. Currently supported: V7.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Local directory for SVG files and manifest.json.",
    )
    args = parser.parse_args()

    if args.experiment.upper() != "V7":
        parser.error("only the V7 named reconstruction is currently supported")

    manifest = export_v7(args.output_dir)
    print(
        f"Wrote {manifest['game_count']} SVGs "
        f"({manifest['wins']} wins, {manifest['losses']} losses) "
        f"to {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
