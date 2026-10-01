from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT, ROOT / "src"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

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


V7_HISTORICAL_CHECKOUT = "f26781b87451ceb49069c29276d60e03b18ba0d7"


def _historical_v7_error() -> RuntimeError:
    return RuntimeError(
        "Historical V7 used v0-threshold-equipment and cannot be reconstructed "
        "with the current canonical exact-equipment rules. No games were run "
        "and no SVGs were written. Use a separate pinned historical checkout: "
        f"git worktree add ../bandido-v7 {V7_HISTORICAL_CHECKOUT}; "
        "then run that checkout's scripts/export_final_boards.py --experiment V7 "
        "--output-dir artifacts/v7-final-boards. Its source/provenance checks "
        "must remain enabled. Historical collected-card identities were not "
        "persisted and cannot be inferred from counters."
    )


def _final_records_sha256(rows: list[dict[str, object]]) -> str:
    canonical = json.dumps(
        sorted(rows, key=lambda row: int(row["seed"])),
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _load_and_validate_v7_metadata() -> tuple[dict[str, object], dict[str, object]]:
    """The old source validator is intentionally unavailable under new rules."""
    raise _historical_v7_error()


def export_v7(
    output_dir: str | Path,
    *,
    workers: int = 4,
) -> dict[str, object]:
    """Reject historical replay before loading a policy, deck, or RNG."""
    if workers <= 0:
        raise ValueError("workers must be positive")
    raise _historical_v7_error()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export final Bandido: Alcatraz boards as standalone SVG files."
    )
    parser.add_argument(
        "--experiment",
        required=True,
        help="Historical experiment (V7 requires the pinned pre-migration checkout).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="Local directory for SVG files and manifest.json.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Historical compatibility option; replay is disabled in this checkout.",
    )
    args = parser.parse_args()

    if args.experiment.upper() != "V7":
        parser.error("only the V7 named reconstruction is currently supported")

    try:
        manifest = export_v7(args.output_dir, workers=args.workers)
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))
    print(
        f"Wrote {manifest['game_count']} SVGs "
        f"({manifest['wins']} wins, {manifest['losses']} losses) "
        f"to {args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
