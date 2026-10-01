# Bandido Alcatraz Solver

A reproducible simulator and strategy-search project for **Bandido: Alcatraz**.

## Goal

Model the game rules and exact photographed deck faithfully, establish reproducible baseline simulations, then search for strategies that maximize win probability.

## Source of truth and persistence

Git is the canonical source of truth for rules/modeling decisions, the abstract photographed-deck specification, simulator/policy code, experiment definitions, and compact manifests/summaries.

Large raw simulation traces and diagnostic payloads are stored outside Git. See [docs/persistence.md](docs/persistence.md).

Every published experiment must identify its ruleset, deck, policy parameters, deterministic seeds, game count, simulator commit, and durable raw-artifact provenance when raw data exists.

## Development rule

Substantive changes use bounded branches and pull requests. Research is checkpointed into `main` instead of accumulating indefinitely on one branch.

## CI

Repository validation runs on:

```yaml
runs-on: [self-hosted, Linux, X64, bandido-alcatraz-ci]
```

There is no GitHub-hosted fallback.

## Current state

Implemented and validated:

- generic rotatable two-half-cell card geometry;
- exact owner-photo inventory and ordinary-card placement geometry;
- canonical real deck `data/deck-v1.json`;
- board placement and tunnel/earth matching;
- water-half covering;
- equipment/victory model;
- deterministic configurable three-/six-card solo deck/hand/turn engine;
- deterministic legal-move ordering across Python hash seeds;
- seeded simulation and policy framework;
- synthetic and real-deck smoke coverage;
- static final-board SVG rendering with physical-card placement history;
- public collected-equipment history and SVG set-aside thumbnails;
- strategy diagnostics through the current research track.

The canonical model is `v1-exact-equipment-full-hand-refresh`: exactly 3 raincoats and 2 ropes. Setup axes are independent; initial research uses five-exit START and six-card solo hand. Full-hand solo refresh is an owner-selected interpretation of ambiguous publisher wording. See [modeling-v1](docs/modeling-v1.md). Historical V1–V7 results remain tied to their old source/model and do not establish current-model performance.

The durable research/orchestration log is Issue #2.

## Final-board SVG export

See [docs/svg-final-boards.md](docs/svg-final-boards.md) for the placement-history
model, renderer legend, generic API, and V7 provenance checks.

Historical V7 export requires the original source, rather than the current exact-rule engine:

```bash
git checkout f26781b87451ceb49069c29276d60e03b18ba0d7
python -m pip install -e .
python scripts/export_final_boards.py \
  --experiment V7 \
  --output-dir artifacts/v7-final-boards
```

The command writes 100 standalone SVG files, including both wins and losses,
plus `manifest.json`. Historical V7 is reconstructed by exact deterministic
re-simulation and is rejected before output if its final records no longer
match the durable V7 receipt.

Current-model exports accept final public observations and include explicit collected equipment identities. Multiplayer setup validation is available; multiplayer execution and communication policies remain deferred to Issue #27.
