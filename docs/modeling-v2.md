# Canonical exact-equipment model with quota-limited COLLECT

Ruleset ID: `v2-exact-equipment-quota-limited-collect-full-hand-refresh`.

Authority:
- [Issue #31 correction scope](https://github.com/carabinshely/bandido-alcatraz-solve/issues/31#issuecomment-5927025323)
- [Issue #2 owner authorization](https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5927093199)

This model supersedes [modeling-v1](modeling-v1.md). The owner-approved correction
limits equipment collection to its required quota. The former v1 claim that
COLLECT remained legal beyond quota is historical, not current rule authority.
This correction is a project modeling decision, not an additional publisher FAQ.

## Equipment legality and victory

For a card in the acting player's hand:

- A raincoat COLLECT is legal only while the public raincoat count is below 3.
- A rope COLLECT is legal only while the public rope count is below 2.
- A card with no equipment material has no COLLECT action.
- Reaching one material's quota does not block collecting the other material
  while its own count is below quota.
- At or above quota, the equipment card remains available for ordinary PLACE
  wherever board geometry permits. Quotas do not restrict PLACE.

Quota is permission only, never forced or priority COLLECT: below quota both
COLLECT and geometrically legal PLACE are available, the unchanged policy
weights and geometry determine the choice, and no automatic collection behavior
is added.

A successful COLLECT removes that card from tunnel play and adds one to the
corresponding public count and one immutable record to public collected history.
Collected cards cannot return to tunnel play. An illegal COLLECT must be
rejected before any state mutation, including when ordinary move validation is
bypassed; it must not remove a hand card, consume a turn, draw a replacement,
alter the board or change equipment counts/history.

Victory is unchanged: exactly 3 raincoats and 2 ropes, EXIT placed, no other open
tunnel, and no visible water. Readiness is equality, not a threshold. Fresh
legal games cannot collect past quota. Synthetic or historical states whose
counters are already over quota remain non-winning and cannot collect more of
that saturated material; the model does not silently clamp or repair counters.

Quota-aware legality applies consistently to game state, detached player
observations, no-draw successors and blocked-hand/draw-pile checks. If a hand has
only saturated equipment cards with no legal placement, COLLECT is not an
escape from being blocked. No-draw lookahead must update counts before finding
retained-card actions, so collecting the final needed item makes a second
same-material COLLECT illegal. Policies continue to choose among legal moves;
this correction adds no policy feature, weight or tuning.

The low-level `legal_moves(board, hand, *, raincoats, ropes)` API requires both
inventory counts explicitly. Board-only geometry analysis uses
`placement_moves(board, hand)`, which never emits COLLECT and preserves the
relative canonical PLACE order. EXIT-capacity and visible-repair helpers use
this placement-only API rather than assuming missing counts are zero.

## Unchanged setup, placement and refresh

Deck transcription, `data/deck-v1.json`, placement and rotation, tunnel/earth
matching, water covering, EXIT geometry, shuffle and deterministic legal-move
ordering conventions are unchanged. Removing an illegal COLLECT does not
remove or reorder the remaining legal PLACE candidates.

`GameSetup` keeps independent player-count, START-side, hand-size and
starting-player axes. Solo hand sizes are 3 or 6; multiplayer configuration
requires 3 per player. Initial research uses `GameSetup()` with one player,
five-exit START and a six-card hand. No empirical ordering between
six-exit/six-card and five-exit/three-card is assumed. Multiplayer setup and
separate private hands can be represented, but multiplayer execution remains
deferred to Issue #27 and fails explicitly before simulation. The quota
correction does not introduce multiplayer turns or communication policies.

The owner-selected solo refresh still replaces the **entire current hand**,
including a six-card hand. The short-pile boundary remains the current
replacement batch size. Refresh consumes no action/turn and no RNG. With more
than a batch remaining, return the old hand in existing order to the bottom and
draw replacements from the list end. With at most a batch remaining, take the
remaining pile in existing internal order and preserve the displaced hand in
the private face-down set-aside zone. These ordering conventions are engine
conventions, not publisher assertions. Refresh and exhaustion decisions now use
quota-aware legal actions; the replacement mechanics are unchanged.

Publisher source and interpretation context:
https://fractaljuegos.com/wp-content/uploads/2026/04/BandidoAlcatraz_Rules_Fractal_WEB.pdf
The general no-play rule refers to a three-card replacement, while solo offers
three- or six-card starting hands without an explicit replacement-batch
clarification. Full-hand refresh remains the owner's selected interpretation.

## Unchanged information and conservation boundaries

A detached `PlayerObservation` contains a cloned public board, own visible
hand, public equipment counts/history, setup and turn data. It contains no draw
pile, other players' private cards or private set-aside identities. Policies may
use public collected geometry; mutation of their observation cannot change the
real board. No-draw previews preserve this boundary and never acquire hidden
replacement cards.

Each successful COLLECT records `CollectedEquipment(card, turn, player_index)`
with the physical card identity/material and one-based action index. Fresh games
start with zero counts and empty history. Constructed test states may supply
counters without history; those counters do not reconstruct unknown identities.
A terminal observation hook continues to support final-board exports, including
a final-action collection.

The hidden draw pile, separate `private_hands`, public board placements, public
collected equipment and private `face_down_set_aside` remain distinct zones.
Observations expose only the set-aside count. `hand` remains the active-hand
compatibility alias. Solo `exit_seen` is own-player knowledge; nonexecuting
multiplayer observations must not expose another player's privately drawn EXIT
through the legacy solo-global flag. Quota enforcement does not change these
conservation or privacy contracts.

## Migration and baseline gate

- Preserve historical model documents, decision bodies, manifests, raw-artifact
  provenance and seed-ledger records. Add historical labels rather than
  rewriting old outcomes under the v2 identifier.
- Historical V1–V7 results used their original source/model and are not
  current-model performance evidence. Historical V7 reconstruction still
  requires source `f26781b87451ceb49069c29276d60e03b18ba0d7` and its provenance
  checks. The old Worker #28 protocol / PR #25 remains superseded with zero V8
  games.
- The Worker #29 / PR #30 run under v1 is a **superseded diagnostic**, not a valid
  baseline for v2. Keep its receipt and artifacts as historical evidence; do not
  relabel them or treat their outcome as a correction target.
- A corrected baseline may run only after the corrected model is reviewed and
  merged, with exact source commit, ruleset, deck, policy/parameters and setup
  frozen before compute. The permitted population is the **same already-spent
  400 seeds, `1000000` through `1000399` inclusive**. This is a rerun of a spent
  population, not fresh confirmation data; do not allocate new seeds or alter
  the historical seed ledger to make it look unspent.
- Keep model correction separate from strategy research. No policy tuning,
  seed-range expansion, new research games or favorable-result search is part
  of this correction. A corrected model makes no guarantee of wins or improved
  win rate; report the frozen rerun's actual result, including zero wins.

Routine regression checks may use synthetic fixtures and the already-spent real
smoke seeds 0–19. They are correctness checks, not a baseline or authorization to
run the spent-400 research population before the review/merge/freeze gate.
