# Synthetic smoke experiment

This is **not** a Bandido: Alcatraz strategy result.

Purpose: exercise the complete deterministic simulation pipeline before the exact 68-card Alcatraz catalog is available.

The fixture is intentionally artificial. It exists only to verify that:

- the deck is shuffled from a seed;
- hands are dealt and replenished;
- legal moves are generated;
- material can be collected;
- EXIT can be placed;
- policies can choose moves;
- terminal states are classified;
- repeated seed sets produce repeatable aggregate results.

Run:

```bash
python scripts/run_synthetic_smoke.py
```

Do not compare its win rate to the real game.
