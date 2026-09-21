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

The initial repository bootstrap is committed directly to `main` because the repository was empty. Subsequent changes should be made through branches and pull requests.

## Current phase

**Phase 0 — exact model acquisition.**

Before optimizing strategy, encode and verify the official rules and the exact multiset/geometries of the physical deck.
