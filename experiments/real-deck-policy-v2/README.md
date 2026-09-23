# Real-deck policy diagnostics v2

This experiment compares three isolated changes against `greedy_v0` on the
same 50 photographed-deck seeds.

- `discard_excess_v2`: only changes excess-equipment collection from a
  penalty (-500) to neutral (0), allowing collection to discard a branching
  equipment card when placing it would increase open tunnels.
- `water_first_v2`: only raises the score for removing one visible water
  half from 5 to 20,000.
- `combined_v2`: applies both changes.

Because earlier real-deck policies produced zero wins, the experiment also
records diagnostic surrogate outcomes:

- mean open tunnels;
- games ending with <=5 open tunnels;
- cleared-water count;
- mean visible-water count;
- equipment-ready count;
- EXIT-placement count;
- games where EXIT + equipment + water are all ready.

The final objective remains wins; surrogate metrics are used only to choose
the next hypothesis while wins remain sparse.
