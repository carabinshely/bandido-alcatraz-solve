# Owner-photo deck transcription

The physical Bandido: Alcatraz photographs supplied on 2026-09-21 are the
primary source for the exact Alcatraz deck reconstruction.

The image binaries stay outside Git. Each photographed position has a stable
slot ID in `data/owner-photo-inventory-v0.json`, for example:

`photo-3-r2-c5`

## Orientation

Cards are recorded in portrait orientation as photographed.

External ports:

| Port | Meaning |
| --- | --- |
| `T` | top edge |
| `B` | bottom edge |
| `LU` | left edge, upper half |
| `LL` | left edge, lower half |
| `RU` | right edge, upper half |
| `RL` | right edge, lower half |

`internal_bridge=true` means the tunnel crosses the boundary between the
upper and lower half-cells.

This representation maps directly to the simulator's two-cell
`CardDefinition`.

## Evidence layers

Keep three concepts separate:

1. **visual metadata** — role, rope/raincoat, water half, visible gate;
2. **geometry transcription** — external ports and internal bridge;
3. **canonical family grouping** — normalized geometry/multiplicity after every
   slot is transcribed.

A card may have verified visual metadata while its geometry remains null.
Do not infer missing geometry from original Bandido/proxy cards.

## Current direct observations

- 68 ordinary cards;
- 1 standalone EXIT card;
- one double-sided START card photographed on both faces;
- START easy: 5 exits;
- START normal: 6 exits;
- EXIT: straight top-to-bottom tunnel;
- 12 raincoat cards;
- 8 rope cards;
- 4 water cards;
- water split: two top-half and two bottom-half cards.

The remaining task is ordinary-card geometry transcription and canonical
grouping.
