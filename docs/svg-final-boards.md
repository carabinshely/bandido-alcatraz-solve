# Static final-board SVG export

Issue #23 adds a deliberately small final-state inspection path. It does not
create a replay engine or graphical application. A simulation keeps enough
physical-card placement history to render the final board as a standalone SVG,
and the batch exporter writes one SVG per game plus a compact manifest.

## Placement-history model

`Board` remains the authority for legal placement and flattened visible-cell
state. In addition, it records one immutable `CardPlacement` for:

- the initial START placement;
- every later PLACE action, including EXIT.

COLLECT actions do not affect the physical board and are not recorded.

Each placement contains:

- `card_id`;
- `origin`;
- `quarter_turns`;
- `placement_index`;
- START / ordinary / EXIT classification;
- the absolute cells occupied by that physical card;
- overlap coordinates, when a legal water-half cover occurred;
- the placement index of the physical card under the covered cell, when known.

The history is stored as an immutable linked tail. `Board.clone()` shares the
existing tail and appends only to the clone's own successor tail. This keeps
policy lookahead/history cloning O(1) and does not add random-number-generator
calls or change legal-move ordering.

## SVG semantics

`src/bandido_alcatraz/render_svg.py` uses only the Python standard library.
The SVG is intentionally diagnostic rather than decorative.

The renderer shows:

| Visual marker | Meaning |
| --- | --- |
| black tunnel strokes | visible tunnel geometry |
| thin gray cell grid | visible flattened cells |
| black physical-card perimeter | ordinary card boundary |
| blue perimeter | START |
| orange perimeter | EXIT |
| `r0` .. `r3` label | card orientation in quarter turns |
| light-blue cell + `W` | visible water |
| red ring at tunnel edge | open tunnel end |
| black center dot on a one-port cell | dead-end cell |
| dashed purple overlap marker | legal water-cover / overlap placement |

The SVG also embeds machine-readable metadata for experiment, game index, seed,
outcome, turns, final open-tunnel count, final visible-water count, and
placement information.

## Generic batch API

For already-simulated final boards, construct `FinalBoardExport` records and
call:

```python
from bandido_alcatraz.export_svg import FinalBoardExport, export_final_boards

export_final_boards(
    records,
    "artifacts/final-boards",
    experiment="my-experiment",
    policy="my-policy",
)
```

Records are sorted by `game_index`. The exporter does not filter losses.
Stable filenames include game index, seed when present, and win/loss status.

## V7 historical reconstruction

The historical V7 experiment is **not directly renderable**: its durable raw
artifact stores final per-seed outcome records but no physical-card placement
traces.

It is, however, exactly reconstructable from durable provenance, so V7 uses
**deterministic re-simulation**.

Pinned V7 inputs:

- experiment:
  `worker26-v7-immediate-tie-spent-development-2026-09-30`;
- evaluated commit:
  `2e532c7e8a95397d586eb03cdfa840ea6a82e534`;
- policy: `ImmediateTieV7Policy`;
- seeds: `1000..1099`;
- game count: 100;
- hand size: 3;
- START: easy / 5 exits;
- ruleset: `v0-threshold-equipment`;
- deck: `data/deck-v1.json`;
- EXIT geometry: `data/deck-observations-v0.json`.

The export command first verifies every canonical source/data Git blob from the
V7 manifest except the intentionally observer-augmented `Board`. It separately
pins the exact accepted V7 candidate/harness blob and the exact reviewed
placement-history `Board` blob. It then runs all 100 games with the frozen V7
policy and compares the complete normalized final-record set against the
SHA-256 checksum derived from the durable 2026-09-30 receipt. It also verifies
the exact seven historical win seeds. Any source or result mismatch aborts
**before writing SVGs**.

This is stronger than silently assuming current code still reproduces V7.

## Local V7 command

Prerequisite from the repository root:

```bash
python -m pip install -e .
```

Then run:

```bash
python scripts/export_final_boards.py \
  --experiment V7 \
  --output-dir artifacts/v7-final-boards
```

Expected output directory:

```text
artifacts/v7-final-boards/
  001-seed-1000-loss.svg
  002-seed-1001-loss.svg
  ...
  009-seed-1008-win.svg
  ...
  100-seed-1099-loss.svg
  manifest.json
```

The folder contains all 100 games, wins and losses alike. Open any SVG directly
in a browser or file manager; no special viewer is required.

By default the replay uses four independent worker processes. Each seed gets a
fresh deck, policy, and random-number generator, and ordered `map()` collection
preserves deterministic output order. For serial debugging, add `--workers 1`.

## Historical and scope limitations

- Historical V7 has no persisted placement trace, so it is reconstructed rather
  than directly rendered.
- The named-experiment CLI currently exposes V7. The underlying renderer and
  batch exporter are generic.
- Output is final-state only: no animation and no move-by-move replay.
- SVGs are generated artifacts and belong in local artifact storage rather than
  Git unless a later research task explicitly decides to preserve a sample.
