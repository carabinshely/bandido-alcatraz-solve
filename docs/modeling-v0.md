# Modeling v0

## Principle

Start with the smallest rules model supported by the published rules. Do not add restrictions unless an authoritative rule explicitly requires them.

## Equipment win condition

For the initial simulator, the equipment condition is:

- raincoats >= 3
- ropes >= 2

Collecting additional raincoats or ropes does not by itself prevent a win.

This deliberately avoids an invented upper-bound or exact-count constraint. If an authoritative rule later explicitly says that excess equipment is illegal or prevents victory, the ruleset will be versioned and changed with a regression test.

## Scope discipline

The first engine should model only what is required to determine legal moves and victory/loss. Strategy heuristics, optimization, communication modeling, and other refinements come later.
