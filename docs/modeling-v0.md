# Modeling v0

## Principle

Start with the smallest useful model. Do not add restrictions that are not needed to explore strategy.

## Equipment win condition used by v0

The simulator v0 intentionally uses:

- raincoats >= 3
- ropes >= 2

Collecting additional raincoats or ropes does not by itself prevent a win.

### Source caveat

The Spanish Fractal rulebook says that by the end of the game the group must have gathered "exactamente 3 impermeables y 2 cuerdas".

For the first simulator we deliberately use the simpler threshold interpretation requested for this project. This is a known modeling choice, not a claim that the Spanish wording says "at least".

If later experiments show that excess equipment can materially affect policy, a strict-rule variant can be added and compared without changing the card/board model.

Official rulebook:
https://fractaljuegos.cl/wp-content/uploads/2026/04/BandidoAlcatraz_Rules_Fractal_WEB.pdf

## Scope discipline

The first engine models only what is required to determine legal moves and victory/loss. Strategy heuristics, optimization, communication modeling, and other refinements come later.
