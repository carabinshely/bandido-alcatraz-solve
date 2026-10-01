# Static final-board SVG export

The final-state inspection path retains physical-card placement history and
collected-equipment history. The standard-library exporter writes one standalone
SVG per supplied final state plus a compact manifest. It does not run simulations
or consume seeds itself.

## Two independent histories

`Board` remains the authority for legal placement and visible-cell state. It
records an immutable `CardPlacement` for the initial START and every later PLACE
(including EXIT). Placement records contain physical card ID, origin, rotation,
placement index, classification, occupied cells, and any water-overlap provenance.
Its immutable linked tail is shared safely by `Board.clone()`.

`GameState.collected_equipment` separately retains a tuple of immutable
`CollectedEquipment` records, in collection order:

- `card`: the exact immutable `CardDefinition`, including its original geometry;
- `card_id` and `material`: properties of that definition;
- `turn`: the one-based action number at collection (refresh is not an action);
- `player_index`: the zero-based collecting player identity.

Collecting removes the card from the hand and does not place it on the board.
Canonical equipment counters remain maintained centrally by the engine; the
renderer never reconstructs identities from aggregate counters. The history is
shared public information in `PlayerObservation`. Observation and no-draw
lookahead preserve history without revealing hidden draw order or consuming RNG.
The current execution path remains solo; the player field accommodates future
multiplayer support without implying that support exists today.

## SVG semantics

`src/bandido_alcatraz/render_svg.py` shows the board and a separate
**Collected equipment / set-aside** area below it.

| Visual marker | Meaning |
| --- | --- |
| black tunnel strokes | visible board tunnel geometry |
| thin gray cell grid | visible flattened board cells |
| black physical-card perimeter | ordinary placed card boundary |
| blue perimeter | START |
| orange perimeter | EXIT |
| `r0` .. `r3` label | placed-card orientation in quarter turns |
| light-blue cell + `W` | visible board water |
| red ring at board tunnel edge | open tunnel end |
| black center dot on a one-port board cell | dead-end cell |
| dashed purple overlap marker | legal water-cover / overlap placement |
| green-tinted equipment tile | collected raincoat |
| orange-tinted equipment tile | collected rope |

Equipment tiles retain collection order even when raincoats and ropes alternate.
Each shows its material, physical card ID, collection number, action/turn number,
and player number (displayed one-based). A scaled schematic uses the actual card
cells, tunnel edges, and water at the original definition orientation; it is not
a placed-board rotation or a replay. Thumbnails remain outside the board's
visible-cell and placement groups and do not affect board water or tunnel counts.
The area explicitly says when no equipment was collected.

Each SVG's JSON metadata and each batch manifest game entry contains the same
`collected_equipment` array. Each entry includes `collection_index` (one-based),
`card_id`, `material`, `turn`, `player_index` (zero-based), and the full `cells`
geometry with sorted tunnel-edge labels. The machine-readable tile attributes
carry the same identity/order fields. Existing board metadata and stable
filenames are preserved.

## Current-model batch API

Wrap an already selected policy in `FinalStateCapturePolicy`. Its `choose` method
passes through the same observation and RNG to the policy. The simulator calls
`on_game_finished(observation)` on **every terminal path**, including games that
end without a policy choice. That terminal callback also forwards to the wrapped
policy when it defines the same hook.

A policy's last pre-action observation is a detached snapshot, not a live state
reference. In particular, it does not yet contain the final action's collected
card. Use `FinalBoardExport.from_capture()` after `play_game()` to avoid exporting
that stale snapshot; this helper requires the terminal callback to have run and
includes all retained equipment automatically. It also preserves the result's
`ruleset_id` and `setup_id` in the SVG and per-game manifest metadata. Direct
synthetic records may leave those two optional fields unset.

For an independently authorized current-model simulation:

```python
from bandido_alcatraz.export_svg import (
    FinalBoardExport,
    FinalStateCapturePolicy,
    export_final_boards,
)
from bandido_alcatraz.setup import GameSetup
from bandido_alcatraz.simulate import play_game

# real_deck, policy, and seed are selected by the caller's experiment setup.
setup = GameSetup()  # solo, easy START, six-card hand
capture = FinalStateCapturePolicy(policy)
result = play_game(
    start_card=real_deck.start_for_setup(setup),
    deck=real_deck.draw_deck(),
    hand_size=setup.hand_size,
    setup=setup,
    policy=capture,
    seed=seed,
)
record = FinalBoardExport.from_capture(
    game_index=1,
    capture=capture,
    result=result,
    seed=seed,
)
export_final_boards(
    [record],
    "artifacts/final-boards",
    experiment="my-current-model-experiment",
    policy=type(policy).__name__,
)
```

For callers with an existing final state, `FinalBoardExport` also accepts
`collected_equipment=state.collected_equipment` directly. Omitting it means an
empty supplied history; do not omit it when collected cards exist. The direct
renderer accepts the same keyword:

```python
svg = render_board_svg(
    state.board,
    collected_equipment=state.collected_equipment,
)
```

Records are sorted by `game_index`; losses are retained. Filenames include the
game index, seed when supplied, and win/loss status. These capture/export helpers
add no RNG calls or changes to legal-move order. Synthetic tests compare wrapped
and unwrapped runs, verify the final collection, and verify deterministic bytes.
They are observability checks, not a new performance baseline.

## Historical V1–V7 boundary

Historical V1–V7 final records did **not** persist collected physical card
identities. Counts alone cannot recover the identities or consumed tunnel
geometries. All historical manifests, ruleset labels, and outcome receipts remain
unchanged; they do not become evidence for the new exact-equipment model.

V7's durable raw artifact also lacks placed-card traces. Before this migration,
its final boards were reconstructed through source- and provenance-checked
re-simulation under `v0-threshold-equipment`. Running that policy under today's
exact 3-raincoat / 2-rope rules is not historical reconstruction.

The current `export_v7()` API and `--experiment V7` CLI therefore fail before
loading a policy, constructing a deck/RNG, simulating, or writing an output
directory. They provide the pinned historical checkout below. The current
repository does not introduce an old-rules runtime switch.

## Pinned historical V7 board export

For a separately authorized historical reconstruction, use the complete
pre-migration checkout that introduced the source-checked exporter:

```bash
git worktree add ../bandido-v7 f26781b87451ceb49069c29276d60e03b18ba0d7
cd ../bandido-v7
python scripts/export_final_boards.py \
  --experiment V7 \
  --output-dir artifacts/v7-final-boards
```

Use that checkout's interpreter environment/source. Do not copy its old policy
into the new engine, relax its source checks, or change historical manifests to
make a replay pass.

The pinned exporter verifies canonical source/data blobs, the accepted V7
candidate/harness, and the reviewed placement-history observer. It checks all
100 final records against the durable receipt checksum and the seven historical
win seeds before writing SVGs. Its evaluated simulation commit is
`2e532c7e8a95397d586eb03cdfa840ea6a82e534`; the later checkout above adds the
observer/export support without changing those frozen game semantics.

That old exporter only captures placed-board history. It does **not** implement
this migration's collected-card area. Recovering historical collected identities
would require a separately provenance-checked observer-only replay extension
under the frozen old model; this migration neither performs nor claims that
recovery. No real-deck research or confirmation seeds are run by its new tests.

## Scope

- Output is final-state only, without animation or move-by-move replay
- Generic current-model export is provided by the Python API
- Generated SVGs belong in local artifact storage, not Git, unless explicitly
  selected for preservation
