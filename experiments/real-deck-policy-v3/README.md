# Real-deck policy diagnostics v3

This experiment starts from `combined_v2`, the best diagnostic result from
v2, and adds board-geometry information that is visible to a player.

Policies:

- `combined_v2`: excess-equipment discard + strong water-cover priority.
- `merge_aware_v3`: additionally rewards moves that leave more open tunnel
  ends targeting the same empty cell, creating a future chance to join two
  open ends with one card.
- `water_space_v3`: additionally avoids occupying the remaining neighboring
  space around visible water and heavily penalizes creating a fully trapped
  water half.
- `combined_v3`: both spatial additions.

All policies use the same 50 real-deck seeds. No policy reads the hidden order
of the draw pile.
