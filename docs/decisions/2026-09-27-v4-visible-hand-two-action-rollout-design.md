# V4 visible-hand two-action no-draw rollout design

Date: 2026-09-27  
Worker: #20  
Status: design checkpoint only; no policy implementation or outcome evaluation

## Decision

Preregistered classification:

`v4_visible_hand_two_action_rollout_design_feasible`

The preregistered architecture can be specified entirely from the current visible decision state while preserving the existing `BoundedMergeV4Policy(setup_weight=250)` action reward. It requires no discount, horizon weight, terminal constant, learned feature, V5 filter, hidden replacement draw, mutable policy history, or rollout RNG.

The main implementation constraint is that the existing `move_features()` PLACE path calls `GameState.apply()`, and `GameState.apply()` performs a replacement draw. Although every V4-250 feature value is invariant to that draw, a conforming implementation must not access the hidden draw merely because the current helper happens to do so. The implementation therefore needs a pure no-draw action-preview/scoring seam that is feature-equivalent to the existing V4 reward.

This is an implementation seam, not a new reward convention.

## Authority and frozen baseline

Authoritative preregistration:

https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5859505130

Starting canonical main:

`6a571bbb0fd085ec11589c17541730207f3c3497`

Frozen policy:

`BoundedMergeV4Policy(setup_weight=250)`

Fixed model:

- `data/deck-v1.json`;
- EXIT geometry from `data/deck-observations-v0.json`;
- `v0-threshold-equipment`;
- raincoats >= 3;
- ropes >= 2;
- START easy / 5 exits;
- hand size 3;
- existing deterministic legal-move ordering;
- existing `exit_seen` lifecycle;
- no exact-equipment switch;
- no V5 safety tier.

No seed, trajectory, win-rate, or outcome data is used by this design diagnosis.

## Current V4-250 weights

The exact non-zero weights are:

| Feature | Weight |
| --- | ---: |
| `collect_needed` | 10,000 |
| `wins` | 1,000,000 |
| `closes_last_without_win` | -1,000,000 |
| `delta_open_tunnels` | 100 |
| `delta_visible_water` | 20,000 |
| `delta_water_obstruction` | 1,000 |
| `new_trapped_water` | -100,000 |
| `bounded_merge_setup_gain` | 250 |
| `places_exit_ready` | 5,000 |
| `places_exit_early` | -5,000 |

The exact zero-weight fields are:

- `collect_excess = 0`;
- `collect_degree_one = 0`;
- `delta_merge_opportunities = 0`.

They remain available as existing features but must not become scoring terms in this strategy.

## Candidate architecture

For each legal current first action `m1`:

1. compute the exact V4-250 reward `score1` without inspecting the hidden draw;
2. construct the exact visible no-draw successor of `m1`;
3. if `m1` creates a canonical terminal board state, stop that sequence and use `score1`;
4. otherwise enumerate every legal `m2` belonging only to the two cards retained from the pre-`m1` visible hand;
5. compute each `score2` with the same V4-250 reward on the no-draw successor;
6. if at least one retained-card second action exists, use:
   `sequence_score(m1) = score1 + max(score2)`;
7. if no retained-card second action exists, use:
   `sequence_score(m1) = score1`;
8. find all first actions with maximal sequence score;
9. perform exactly one `rng.choice(best_first_moves)`.

No second action is randomly selected. The rollout needs only the deterministic maximum second-action score.

Conceptually:

```text
visible current state
        |
        +-- m1_a --> no-draw successor A --> max V4 score over retained m2
        |
        +-- m1_b --> no-draw successor B --> max V4 score over retained m2
        |
        +-- ...
        |
        +--> compare score1 + best(score2)
                    |
                    +--> exactly one rng.choice among tied best m1
```

## Pure no-draw successor contract

A rollout successor is an evaluation state derived entirely from information already visible before `m1`.

It must contain:

- board after exactly `m1`;
- the two retained pre-action cards, in their preserved relative order;
- exact stable identity for each retained card;
- updated raincoat count;
- updated rope count;
- updated `exit_placed`;
- canonical visible `exit_seen` value implied without any replacement draw;
- action count / turn increment if retained for state fidelity;
- unchanged `set_aside_unplayable` if retained for state fidelity.

It must not contain or inspect:

- replacement-card identity;
- hidden `draw_pile` contents;
- refreshed cards;
- future actions;
- future outcome;
- policy history.

A preferred implementation representation is a dedicated evaluation-only structure, conceptually:

```text
NoDrawRolloutState
  board
  retained_cards: (
    RetainedCard(original_index, preview_index, card_id, card),
    RetainedCard(original_index, preview_index, card_id, card),
  )
  raincoats
  ropes
  exit_placed
  exit_seen
  turns
  set_aside_unplayable
```

The structure intentionally has no usable hidden draw pile.

An implementation may instead reuse a sanitized `GameState` only if the hidden draw is structurally unavailable and exact feature equivalence is unit-proven. Calling normal `GameState.apply()` on a state containing the real hidden draw is not conforming.

## Why existing PLACE scoring needs a pure seam

Current `move_features()` uses this pattern for PLACE:

1. clone the `GameState`;
2. call `clone.apply(move)`;
3. read board/status-derived fields from the clone.

Current `GameState.apply()` performs `_draw_one()`.

However, the replacement draw can mutate only:

- hand contents;
- and possibly `exit_seen`.

The V4 PLACE feature calculation after `apply()` reads:

- `clone.won`;
- board open tunnels;
- visible water;
- merge bank;
- water obstruction;
- trapped water;
- plus equipment readiness from the pre-action source state.

Canonical victory depends only on:

- raincoats;
- ropes;
- open tunnels;
- visible water;
- `exit_placed`.

It does not depend on hand contents or `exit_seen`.

Therefore every V4-250 PLACE feature is invariant to replacement-card identity. A pure no-draw evaluator can reproduce exactly the same `MoveFeatures` values without inspecting or consuming a hidden card.

For COLLECT, current `move_features()` already evaluates directly from the visible card and current equipment counters and performs no draw.

## First-action semantics

### PLACE

Given a currently legal `m1 = PLACE`:

- resolve the exact selected `CardDefinition` from the visible hand;
- clone the board;
- apply exactly the recorded `origin` and `quarter_turns` with canonical `Board.place()`;
- remove exactly the selected visible card from the retained-card set;
- keep raincoats and ropes unchanged;
- increment turn/action count once;
- do not draw;
- do not refresh.

Water-cover, tunnel adjacency, overlap, geometry, and rotation semantics remain exactly those enforced by `Board.place()`.

### COLLECT

Given a currently legal `m1 = COLLECT`:

- resolve the exact selected material card;
- remove it from the retained-card set;
- leave the board unchanged;
- increment raincoats by one for a raincoat;
- increment ropes by one for a rope;
- preserve `exit_placed`;
- preserve current visible `exit_seen`;
- increment turn/action count once;
- do not draw;
- do not refresh.

The updated equipment counters are visible state for second-step scoring. Therefore a first-step COLLECT can legitimately change whether a retained EXIT placement receives `places_exit_ready` or `places_exit_early`.

### EXIT PLACE

If the selected card is EXIT:

- apply its exact legal board placement;
- remove EXIT from the visible hand;
- set `exit_placed = True`;
- set `exit_seen = True`;
- keep equipment counters unchanged;
- increment turn/action count once;
- do not draw.

After the placement:

- if canonical victory is true, the sequence terminates;
- if open tunnels are zero without victory, the sequence terminates;
- otherwise the second retained-card step remains valid.

Placing EXIT is not itself an automatic end of the rollout when the resulting state is nonterminal.

## Terminal contract

### Win after `m1`

Stop after `m1`.

The ordinary V4 `wins` feature already supplies the canonical +1,000,000 reward. No second action and no extra terminal utility are added.

### Zero open tunnels without victory after `m1`

Stop after `m1`.

The ordinary V4 `closes_last_without_win` feature already supplies the canonical -1,000,000 penalty. No second action and no extra terminal constant are added.

### Empty retained hand

Under the fixed three-card model and one consumed first action, this is impossible: exactly two cards remain.

A future implementation should treat violation of this invariant as an error, not invent a fallback score.

### No legal retained-card second action

This is not reclassified as a real-game terminal state.

The bounded visible-hand rollout simply has no visible second contribution:

`sequence_score = score1`.

It must not refresh and must not inspect whether the hidden replacement card would have been playable.

### Win after `m2`

The ordinary second-step V4 reward includes `wins = 1`.

The rollout ends at its fixed two-action horizon; no further utility is added.

### Zero open tunnels without victory after `m2`

The ordinary second-step V4 reward includes `closes_last_without_win = 1`.

The rollout ends at its fixed horizon; no further utility is added.

No arbitrary terminal constants are required anywhere.

## Retained-card identity and hand indexing

Original hand indices cannot be used as second-step indices after one card is consumed.

The representation must preserve two notions separately:

- stable card identity and original visible-hand position for provenance;
- compact preview-hand index used by second-step `Move` values.

For each retained card record:

```text
original_hand_index
preview_hand_index
card_id
CardDefinition
```

The preview hand is constructed by preserving the original relative order and removing exactly `m1.hand_index`.

Example:

```text
original visible hand:  [A(index 0), B(index 1), C(index 2)]
consume B
retained identities:    [A(original 0), C(original 2)]
preview hand:           [A(preview 0),  C(preview 1)]
```

The repository's current photographed-deck data contains 68 ordinary cards and 68 unique ordinary `card_id` values. Stable identity therefore does not need to rely on equal-looking geometry.

A conforming implementation must still carry the exact `CardDefinition`, because legality and material/EXIT semantics belong to the actual card, not merely its display ID.

## Replacement-draw validity proof

The real game draws a replacement after `m1`, while this rollout intentionally does not know it.

A retained-card second action that is legal in the no-draw preview remains legal and available after the real replacement draw.

Reason:

1. `GameState.apply(m1)` mutates board/equipment/EXIT state first, then appends one replacement card.
2. `legal_moves(board, hand)` iterates each hand card independently.
3. Placement legality for a retained card depends on:
   - the board;
   - that card;
   - origin;
   - rotation.
4. COLLECT legality depends only on whether that retained card has material.
5. There is no rule in `legal_moves()` by which the presence of another hand card disables a retained-card move.
6. The replacement is appended after the retained cards.

Because the selected card is removed before the replacement is appended, retained cards occupy the same compacted positions they have in the two-card preview:

- consume original 0 -> originals 1,2 become positions 0,1;
- consume original 1 -> originals 0,2 become positions 0,1;
- consume original 2 -> originals 0,1 remain positions 0,1.

The explicit identity mapping remains authoritative; this index equivalence is supporting evidence, not something the design silently relies on.

The unknown replacement can add additional legal alternatives to the real next decision, including an alternative with a higher V4 score. The rollout intentionally ignores such alternatives because they are not visible at the current decision. That is the definition of visible-hand lookahead, not an assumption that the future hand is known.

If no retained second action exists but the unknown replacement would be playable, the rollout still uses `score1`; it does not claim that the real game would terminate.

## `exit_seen` and the unknown replacement

If the unknown replacement card is EXIT, real `GameState._draw_one()` would set `exit_seen = True`.

This does not block the V4 no-draw design.

On the exact current code:

- `legal_moves()` does not read `exit_seen`;
- `move_features()` does not read `exit_seen`;
- `BoundedMergeV4Policy` / `WeightedGreedyPolicy` do not read `exit_seen`;
- canonical victory does not read `exit_seen`;
- V5 does read `exit_seen`, but V5 is explicitly outside this design.

Therefore the real post-draw state and the no-draw rollout state may differ in `exit_seen` when the hidden replacement is EXIT, but that difference cannot affect V4 second-action legality or V4-250 score.

The no-draw preview must preserve the `exit_seen` value derivable from visible history only:

- if already true, keep true;
- if `m1` places EXIT, set true;
- otherwise leave it unchanged.

It must not inspect hidden replacement identity merely to emulate an irrelevant V4 state bit.

## V4 feature-composability audit

| Feature | V4-250 weight | Sequentially well-defined? | Additive meaning / path dependence | New convention required? |
| --- | ---: | :---: | --- | :---: |
| `collect_needed` | 10,000 | Yes | Evaluated against counters before each COLLECT. A first COLLECT can satisfy a threshold so a later same-material COLLECT is no longer needed. Each action receives exactly its ordinary V4 reward at the state where it occurs. | No |
| `collect_excess` | 0 | Yes | Existing classification may change after first COLLECT, but V4-250 gives it zero score. | No |
| `collect_degree_one` | 0 | Yes | Existing zero-weight feature; remains zero contribution. | No |
| `wins` | 1,000,000 | Yes | If `m1` wins, rollout terminates, so win reward cannot be double-counted. Otherwise a win at `m2` gets the ordinary V4 win reward. A two-step win also retains the ordinary reward earned by `m1`; this is exactly undiscounted sequential reward accumulation. | No |
| `closes_last_without_win` | -1,000,000 | Yes | If triggered at `m1`, rollout terminates. Otherwise it may trigger at `m2`. It cannot be counted twice. | No |
| `delta_open_tunnels` | 100 | Yes | Across two PLACE actions it telescopes: first before-minus-after plus second before-minus-after equals initial minus final. COLLECT contributes zero. | No |
| `delta_visible_water` | 20,000 | Yes | Across PLACE actions it telescopes in the same way. COLLECT contributes zero. | No |
| `delta_merge_opportunities` | 0 | Yes | Existing zero-weight field. It must remain non-scoring. | No |
| `delta_water_obstruction` | 1,000 | Yes | Across PLACE actions the signed difference telescopes. | No |
| `new_trapped_water` | -100,000 | Yes | Intentionally non-telescoping because V4 applies `max(0, newly_trapped)` per action. A later action that removes trapped water does not refund the earlier penalty. Summing two ordinary action rewards preserves that existing path-dependent semantics; it is not equivalent to scoring only net two-step trapped-water change. | No |
| `bounded_merge_setup_gain` | 250 | Yes | Intentionally positive-only and state-gated/capped. It is non-telescoping. If step 1 loses merge bank and step 2 restores it, step 2 can receive ordinary V4 positive setup reward even when final bank equals the initial bank. This is existing per-action V4 semantics applied twice, not a new net-horizon feature. | No |
| `places_exit_ready` | 5,000 | Yes | Readiness is evaluated immediately before the EXIT action. A first COLLECT may make equipment ready, correctly changing a retained EXIT's second-step reward. If EXIT is `m1`, only first-step reward fires. | No |
| `places_exit_early` | -5,000 | Yes | Same state-local logic as `places_exit_ready`; a first COLLECT can change which EXIT feature applies at step 2. | No |

### Composability conclusion

Several V4 features are deliberately non-telescoping, especially:

- `new_trapped_water`;
- `bounded_merge_setup_gain`.

That does not require a new convention because the preregistered sequence value is explicitly the sum of two ordinary action rewards, not a newly defined net-state reward.

The rollout therefore changes decision policy by adding one visible action of lookahead, but it does not change any individual V4 feature definition or weight.

## First-score and second-score equivalence contract

For both `m1` and `m2`, the scorer must produce exactly:

`score_features(existing_V4_MoveFeatures, V4_250_weights)`

without hidden-draw access.

A later implementation must prove that its pure no-draw feature evaluator matches current V4-250 `move_features()` for the same visible state and legal move.

It must not silently redefine:

- victory;
- equipment readiness;
- bounded merge bank;
- water obstruction;
- trapped water;
- EXIT-ready/early timing;
- board legality.

This equivalence belongs in implementation tests, not in this design-only PR.

## RNG contract

A conforming implementation is fully deterministic until the final current action is selected.

Required:

- zero RNG calls while enumerating first actions;
- zero RNG calls while constructing no-draw successors;
- zero RNG calls while enumerating retained-card second actions;
- zero RNG calls to choose among tied second actions;
- `best_score2 = max(score2 values)` only;
- preserve existing deterministic legal-move ordering;
- preserve first-action order in the best-first-move list;
- exactly one final `rng.choice(best_first_moves)`.

No set conversion, sort, canonical tie priority, or secondary second-move preference is required.

The rollout does not need to materialize one chosen `m2`; only the maximal numeric second reward is necessary for first-action ranking.

## Complexity and boundedness

Let:

- `L1` = number of currently legal first moves;
- `L2(m1)` = number of legal second moves from the two retained visible cards after first move `m1`.

The policy performs:

- `L1` first-action reward evaluations;
- one no-draw successor construction per first action;
- `sum(L2(m1))` second-action reward evaluations.

Therefore rollout scoring work is bounded by:

`O(L1 + sum_m1 L2(m1))`

plus the existing board legality/feature cost per move.

The current legal-move generator is finite and deterministic:

- only two cards are considered at step 2;
- each card has at most one COLLECT candidate;
- each card has four rotation attempts;
- candidate origins are finite board-derived sets;
- duplicate geometry/origin placements are deduplicated;
- origins are traversed deterministically.

There is no recursive third ply, beam width, stochastic rollout, or tuned pruning criterion.

For the current card/board representation, exhaustive depth-two visible-hand enumeration is therefore structurally bounded enough to be the direct implementation target. No performance optimization experiment is needed for this design checkpoint.

## Material edge cases

### First action is COLLECT and retained EXIT becomes ready

Use updated equipment counters at step 2. The retained EXIT receives ordinary `places_exit_ready` or `places_exit_early` based on that updated state.

### First action is EXIT but does not end the game

Set `exit_placed=True`, `exit_seen=True`, then enumerate retained second actions if open tunnels remain and victory has not occurred.

### Current visible hand already contains EXIT

Canonical state already has `exit_seen=True`. V4 ignores this field, so the rollout remains well-defined.

### Unknown replacement is EXIT

Real `exit_seen` changes, but V4 second legality and score do not. Hidden card remains unread.

### Replacement card would have the best real next action

The rollout does not know it and does not approximate it. It evaluates only retained visible cards by design.

### No retained action is legal

Use only `score1`. Do not refresh and do not infer hidden replacement playability.

### Duplicate-looking cards

Use stable `card_id` / exact `CardDefinition` identity plus explicit original/preview index mapping. Geometry equality does not collapse identities.

## Why this is Class A rather than B

The architecture requires no unresolved arbitrary choice.

In particular it does not need:

- a discount factor;
- a second-step coefficient;
- terminal utility beyond existing V4 features;
- a score-gap threshold;
- a beam width;
- a second-move tie priority;
- a new feature;
- a V5 phase rule;
- a hidden-draw estimate.

The only potentially surprising behavior comes from existing non-telescoping V4 fields being accumulated once per action. That behavior is fully specified by the existing reward definitions and the preregistered undiscounted sum. No new number or semantic branch is needed.

## Why this is not Class C

No unavailable information is required to represent the two-action visible rollout.

The hidden replacement draw:

- cannot invalidate a retained-card legal move;
- is not required for V4 score;
- can affect `exit_seen`, but V4 does not use that field;
- may add extra future actions, which the visible-hand rollout intentionally excludes.

No canonical game rule must be changed.

## Classification gates

| Class A condition | Result |
| --- | :---: |
| Pure no-draw successor exact/unambiguous | PASS |
| PLACE / COLLECT / EXIT first actions covered | PASS |
| Retained-card identity unambiguous | PASS |
| Second actions enumerated from visible information only | PASS |
| Unknown replacement not required for legality/scoring | PASS |
| Non-zero V4 features coherent sequentially | PASS |
| No new numeric convention needed | PASS |
| Terminal handling requires no arbitrary utility | PASS |
| Zero rollout RNG + one final current RNG sufficient | PASS |
| No game/model rule change needed | PASS |

Final classification:

`v4_visible_hand_two_action_rollout_design_feasible`

## Non-blocking implementation risks

These are requirements for a later implementation, not unresolved design choices:

1. Do not call normal `GameState.apply()` on a state carrying the real hidden draw while scoring rollout PLACE actions.
2. Unit-prove pure no-draw feature equivalence against current V4 `move_features()`.
3. Keep original-card identity separate from compact preview hand index.
4. Do not accidentally invoke 3-card refresh logic on the intentional 2-card rollout hand.
5. Do not use `exit_seen` to introduce V5 behavior.
6. Preserve legal-move ordering and consume no RNG before final first-action tie selection.
7. Keep positive-only/path-dependent `new_trapped_water` and `bounded_merge_setup_gain` semantics exactly as-is rather than converting them to net two-step features.

## Boundaries observed by Worker #20

Worker #20 did not:

- implement a visible-hand-lookahead policy;
- modify production policy/game/model code;
- run candidate trajectories;
- run a win-rate experiment;
- consume fresh or holdout seeds;
- tune on Worker #13;
- use 2238/2282 outcomes as design inputs;
- add a parameter, weight, feature, threshold, penalty, discount, beam, or depth weighting;
- reuse V5 safety filtering;
- choose a subsequent research slice.

No raw Drive artifact is needed for this design-only checkpoint.
