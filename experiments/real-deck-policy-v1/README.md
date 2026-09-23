# Real-deck policy comparison v1

This experiment uses the photographed Bandido: Alcatraz deck reconstructed in
`data/deck-v1.json`.

It compares exactly one policy change:

- `greedy_v0`: collect any still-needed equipment card immediately;
- `geometry_aware_v1`: penalize collecting a still-needed equipment card
  when that card has only one external tunnel port.

Both policies receive the same 100 shuffled-deck seeds.

The rules variant remains the project's intentionally simplified equipment
threshold interpretation:

- raincoats >= 3
- ropes >= 2

Therefore this experiment measures policy behavior on the real photographed
deck under the v0 rules variant. It is not yet a claim about the strict
Spanish `exactly 3 + exactly 2` interpretation.
