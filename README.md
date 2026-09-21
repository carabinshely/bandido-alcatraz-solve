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

## Current phase

**Phase 0 — model foundation + deck acquisition.**

Implemented now:

- generic rotatable card-cell geometry;
- aggregate validation for the published 68-card deck facts;
- minimal victory-condition model;
- generic board placement with tunnel/earth edge matching;
- half-card water covering with exact-pattern validation;
- tests for the above.

Still deliberately missing:

- the authoritative Alcatraz card multiset and per-geometry multiplicities;
- exact internal connectivity for every tunnel geometry;
- hand/deck turn engine;
- simulation policies and strategy search.

The engine is being built so that unknown deck details can be filled in later without redesigning the rules core.
