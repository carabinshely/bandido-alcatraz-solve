# Real-deck policy pilot V4

V4 replaces the pathological raw merge-opportunity reward from V3 with a
bounded setup bank derived from the winning seed-24 trace.

Definition:

- merge bank = `min(merge_opportunities, 6)`;
- bank is active only while `open_tunnels <= 10`;
- policy is rewarded only for **positive increases** in that bank;
- consuming merge opportunities later has no negative merge-bank score.

The policy otherwise keeps the V3 water-space protections and V2
excess-equipment discard behavior.

Pilot design:

- training seeds: 0-29;
- setup weights: 250, 500, 1000;
- choose by wins first, then compact end-state diagnostics;
- held-out seeds: 100-129;
- compare selected V4 to `water_space_v3`, raw `combined_v3`, and
  `combined_v2`.

This is a pilot, not the final win-rate estimate.
