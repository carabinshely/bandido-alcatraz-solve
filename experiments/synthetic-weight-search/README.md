# Synthetic weight search

This experiment validates strategy-search plumbing only. It is **not** evidence
about the real Bandido: Alcatraz win rate or optimal strategy.

The search:

- generates a small grid of `PolicyWeights`;
- evaluates every candidate on the same training seeds;
- selects only by wins;
- evaluates the selected candidate on a disjoint held-out seed range;
- rejects overlapping training/evaluation seeds.

Run:

```bash
python scripts/run_synthetic_weight_search.py
```

The exact Alcatraz deck must replace the synthetic fixture before strategy
conclusions are drawn.
