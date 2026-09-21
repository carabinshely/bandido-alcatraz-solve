# Bandido Alcatraz Solver

A reproducible simulator and strategy-search project for **Bandido: Alcatraz**.

## Goal

Model the game rules and exact deck faithfully, establish reproducible baseline simulations, then search for strategies that maximize win probability.

## Source of truth and persistence

Git is the canonical source of truth for:

- formalized rules and modeling decisions;
- the abstract deck specification (card geometry/counts, not artwork);
- simulator and strategy code;
- experiment manifests;
- compact aggregate experiment results.

Large raw simulation traces, caches, generated databases, and card photographs are not committed.

Every published experiment result must identify at least:

- ruleset version;
- deck version/hash;
- strategy/policy version and parameters;
- random seed range or deterministic seed set;
- game count;
- simulator commit SHA.

## Development rule

The initial repository bootstrap was committed directly to `main` because the repository was empty. Subsequent changes use branches and pull requests.

## CI

Repository validation runs on the local Runner Fleet route:

```yaml
runs-on: [self-hosted, Linux, X64, bandido-alcatraz-ci]
```

The repository has no GitHub-hosted fallback. The current workload is secret-free Python validation on the shared private `BronerBooks-CI` environment using a repository-scoped runner registration.

## Current phase

**Phase 1 — exact physical deck transcription.**

Implemented:

- generic rotatable two-half-cell card geometry;
- board placement and tunnel/earth edge matching;
- water-half covering rules;
- material collection and minimal victory model;
- deterministic deck/hand/turn engine for three-card play;
- legal-move generation;
- reproducible seeded simulation;
- baseline policies;
- parameterized strategy features/weights;
- leakage-safe weight search with held-out seeds;
- paired strategy evaluation and Wilson confidence intervals;
- synthetic smoke/strategy experiments;
- proxy-data completeness guards;
- complete physical photo-slot inventory for the photographed Alcatraz set;
- confirmed aggregate physical inventory:
  - 68 ordinary cards,
  - 1 standalone EXIT card,
  - 1 double-sided START card;
- confirmed material/water counts:
  - 12 raincoat,
  - 8 rope,
  - 4 water;
- confirmed START easy geometry (5 exits);
- confirmed START normal geometry (6 exits);
- confirmed EXIT straight top-to-bottom geometry;
- owner-photo geometry compiler for ordinary-card transcription.

Still deliberately incomplete:

- exact geometry of all 68 ordinary Alcatraz cards;
- canonical grouping/multiplicity derived from those 68 physical slots;
- full real-deck Monte Carlo results;
- optimized strategy conclusions for the actual Alcatraz deck.

The original Bandido/COVID data remains a proxy/reference only. It must not fill gaps in the Alcatraz deck.

See [photo transcription contract](docs/photo-transcription.md) and [statistical evaluation plan](docs/statistics.md).
