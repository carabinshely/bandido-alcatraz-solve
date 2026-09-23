# V5 visible-repair-reserve design

Status: **preregistered implementation design; not implemented or evaluated**

Date: 2026-09-23

Authority:
- [Issue #2 orchestrator decision after Worker #10](https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5795436465)
- starting canonical \`main\`: [\`2aa980ae55c15fb672c4c1adf84b41cde07ef9fd\`](https://github.com/carabinshely/bandido-alcatraz-solve/commit/2aa980ae55c15fb672c4c1adf84b41cde07ef9fd)
- accepted Worker #10 result: [Issue #2 comment](https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5794419199)
- accepted Worker #10 manifest: [\`preaction-visible-repair-reserve-audit-2026-09-23.manifest.json\`](https://github.com/carabinshely/bandido-alcatraz-solve/blob/2aa980ae55c15fb672c4c1adf84b41cde07ef9fd/experiments/real-deck-policy-v4/preaction-visible-repair-reserve-audit-2026-09-23.manifest.json)

This document specifies exactly one later policy, working name
\`VisibleRepairReserveV5Policy\`. It does not authorize another feature,
threshold, penalty, weight sweep, hidden-draw lookahead, or post-zero recovery
preference.

## Fixed behavior

V5 is exactly \`BoundedMergeV4Policy(setup_weight=250)\` plus one
**lexicographic safety tier**. All V4 features and weights remain unchanged.

The safety tier is active only when all three conditions hold:

1. \`state.exit_placed is False\`;
2. \`state.exit_seen is False\`;
3. canonical standalone EXIT legal-move capacity on the current board is
   positive.

Outside that scope, V5 delegates to exact V4 behavior.

Inside that scope, a currently legal move is either **normal** or
\`unsafe_capacity_kill_without_visible_repair_reserve\`. If at least one
normal move exists, unsafe moves are excluded from that one decision. If all
legal moves are unsafe, all legal moves become eligible again. The eligible
moves are then scored with the unchanged V4-250 scoring function and the
existing RNG tie break.

This is a lexicographic demotion, not an illegal-move rule.

No new numeric weight, score penalty, score-gap threshold, turn threshold,
open-tunnel threshold, or merge threshold is part of V5.

## 1. Code-surface map

### \`src/bandido_alcatraz/game.py\` — generic engine support

Later semantic changes:

- add canonical state \`exit_seen: bool\`;
- initialize it from the visible initial hand, never from \`draw_pile\`;
- preserve the invariant that a currently visible or already placed EXIT
  implies \`exit_seen == True\`;
- set it on a normal draw that reveals EXIT;
- set it on a hand refresh that reveals EXIT;
- never reset it;
- preserve it during EXIT placement and terminal/winning states.

Recommended construction invariant:

- \`GameState.__post_init__\` may promote \`exit_seen\` to true when
  \`exit_placed\` is already true or the supplied visible \`hand\` already
  contains EXIT;
- it must never scan \`draw_pile\`.

This keeps direct test fixtures and any future direct state construction from
representing "EXIT visible but never seen".

This is **generic engine support**, not V5-specific policy memory.

No board, rule, deck, equipment, or refresh semantics change.

### \`src/bandido_alcatraz/strategy.py\` — generic pure analysis support

Later semantic changes:

- \`clone_state()\` must copy \`exit_seen\` exactly;
- add the pure standalone EXIT-capacity helper described below;
- add the pure no-draw placement preview described below;
- add the pure visible-repair-reserve helper described below;
- add the pure unsafe-candidate classifier described below.

The existing \`MoveFeatures\`, \`PolicyWeights\`, \`move_features()\`,
\`score_features()\`, and V4 scoring weights remain unchanged.

This file is **generic strategy-analysis support**. The helper contracts are
defined so that V5 cannot accidentally consume a replacement draw.

### \`src/bandido_alcatraz/policies.py\` — V5-specific policy layer

Later semantic changes:

- add \`VisibleRepairReserveV5Policy\`;
- inherit the V4 scoring configuration and explicitly freeze it to
  \`setup_weight=250\`;
- inject the canonical EXIT \`CardDefinition\` into the policy constructor as
  immutable deck/rule metadata;
- override \`choose()\` only to add the preregistered lexicographic safety tier.

The injected EXIT definition is **not historical mutable policy state**. It is
known card geometry, equivalent to the fixed model definition. The policy must
not locate EXIT by scanning \`state.draw_pile\`.

The existing \`BoundedMergeV4Policy\` is not modified semantically.

### \`src/bandido_alcatraz/simulate.py\` — no core change required

\`play_game()\` already creates canonical runtime state through
\`GameState.new()\`. Therefore \`exit_seen\` lifecycle belongs in
\`GameState\`, not in the simulator.

No change to \`GameResult\` is required for gameplay. A later V5 diagnostic
runner may record \`exit_seen\` and its first transition to true as diagnostic
fields, but that is experiment instrumentation rather than simulation rules.

### \`src/bandido_alcatraz/moves.py\` and \`src/bandido_alcatraz/board.py\` — reuse unchanged

No semantic change is planned.

- \`legal_moves(board, hand)\` remains the sole canonical legal-move
  enumerator.
- \`Board.clone()\` remains the board-copy seam.
- \`Board.place()\` remains the placement authority, including rotation,
  tunnel/earth adjacency, and water-cover overlap validation.

The V5 helpers must reuse these existing authorities rather than reimplement
placement geometry.

### \`src/bandido_alcatraz/physical_deck.py\` — no model change

No deck-data change is required. Later V5 construction receives the already
loaded \`RealDeck.exit_card\`.

A later bounded evaluation runner should instantiate conceptually:

\`VisibleRepairReserveV5Policy(exit_card=deck.exit_card)\`

while its comparator remains:

\`BoundedMergeV4Policy(setup_weight=250)\`.

### Existing tests affected later

#### \`tests/test_game.py\`

Add lifecycle tests for \`exit_seen\`: initial hand, normal draw, EXIT draw,
refresh, monotonicity, EXIT placement, and direct visible-state construction.

#### \`tests/test_strategy.py\`

Add tests for:

- \`clone_state()\` preserving \`exit_seen\`;
- standalone EXIT capacity;
- no-draw placement preview;
- visible repair reserve;
- unsafe classification;
- source-state non-mutation.

Existing V4 feature/score tests remain unchanged.

#### \`tests/test_policies.py\`

Add V5 selection tests, including exact V4 fallback/equivalence and existing
RNG tie semantics. Existing policy-weight tests remain unchanged and must
continue to prove V4 isolation.

No production or test file is changed by Worker #11 itself.

## 2. \`exit_seen\` lifecycle contract

\`exit_seen\` is canonical monotonic game history.

State transition rule:

- \`False -> True\`: allowed only when EXIT becomes visible or is already
  visibly/placed present in a constructed state;
- \`True -> False\`: forbidden.

Exact expected lifecycle:

| Event | Expected \`exit_seen\` |
| --- | --- |
| Initial deal without EXIT | \`False\` |
| Initial deal with EXIT | \`True\` |
| Ordinary non-EXIT draw, previously false | remains \`False\` |
| Ordinary non-EXIT draw, previously true | remains \`True\` |
| Normal draw reveals EXIT | becomes \`True\` |
| Refresh with no EXIT, previously false | remains \`False\` |
| Refresh reveals EXIT | becomes \`True\` |
| Any later refresh after EXIT was previously seen | remains \`True\` |
| Clone/copy | exact source value |
| EXIT placement | \`True\`; \`exit_placed=True\` |
| Winning/terminal state after EXIT was seen/placed | remains \`True\` |

Implementation lifecycle locations later:

1. **construction / initial deal** — after the visible hand is formed,
   initialize from that hand;
2. **normal draw** — when \`_draw_one()\` appends the drawn card, set true if
   that card is EXIT;
3. **refresh** — after each refresh branch forms the newly visible hand, set
   true if any newly visible card is EXIT;
4. **apply EXIT** — preserve/set true defensively when EXIT is placed;
5. **clone** — copy exactly in \`clone_state()\`.

The engine must never inspect hidden \`draw_pile\` contents merely to update
\`exit_seen\`.

There is currently no canonical \`GameState\` serializer. No old persisted
artifact requires backfilling. Any future diagnostic snapshot that claims to
reconstruct V5 phase state must explicitly include \`exit_seen\` (and may
add the first sighting turn/index as diagnostic provenance).

### Three-card visibility invariant during the active phase

The fixed model uses a three-card hand. Under canonical runtime, an active V5
phase cannot legitimately need hidden information to manufacture the "two
retained cards":

- if EXIT is unplaced and \`exit_seen=False\`, EXIT is still hidden in the draw
  pile;
- therefore the normal draw mechanism can still replenish a consumed card;
- a short terminal refresh that reveals the remaining EXIT immediately flips
  \`exit_seen=True\` and disables the safety tier.

The classifier is therefore specified against the canonical three-card
pre-action hand used by Worker #10. It must not invent a replacement card.

## 3. Canonical standalone EXIT-capacity helper

Conceptual API:

\`standalone_exit_legal_move_count(board, exit_card) -> int\`

Inputs:

- a \`Board\`;
- the canonical immutable EXIT \`CardDefinition\`.

Output:

- integer count of canonical legal standalone EXIT placements.

Exact definition:

\`len(legal_moves(board, (exit_card,)))\`

Because EXIT cannot also be equipment, canonical standalone EXIT moves are
placements. An implementation may assert this invariant, but must not change
the counted move set.

Mutation guarantees:

- does not mutate \`board\`;
- does not mutate any \`GameState\`;
- does not inspect or mutate a hand or draw pile;
- consumes no RNG.

V5 uses the integer count because the Worker #10 property is defined by
positive versus zero EXIT legal capacity and later diagnostics need the exact
count. Boolean tests use \`count > 0\`; no separate competing capacity
definition is allowed.

## 4. Candidate post-placement helper

Conceptual data shape:

\`PlacementPreview(resulting_board, retained_visible_cards)\`

where each retained-card entry preserves:

- original pre-action hand index;
- \`CardDefinition\`.

Conceptual API:

\`preview_ordinary_non_exit_placement_without_draw(state, move) -> PlacementPreview\`

Contract:

- \`move\` must be a currently legal \`Action.PLACE\` move from
  \`state.legal_moves()\`;
- the selected card must be non-EXIT;
- the source visible hand is the exact pre-action hand;
- clone only \`state.board\`;
- apply the selected card to that board clone with the move's exact
  \`origin\` and \`quarter_turns\`;
- form retained visible cards by removing exactly
  \`move.hand_index\` from the source hand;
- under the fixed model this yields the two other pre-action cards;
- return the board clone and retained visible-card identities;
- do not construct a future hand;
- do not call \`GameState.apply()\`;
- do not call \`_draw_one()\`;
- do not refresh;
- do not read \`state.draw_pile\`;
- do not mutate \`state\`.

Placement validation remains delegated to \`Board.place()\`. This preserves
canonical water-cover, overlap, rotation, and adjacency semantics.

Interaction by move type:

- **ordinary non-EXIT placement:** valid helper input;
- **water-cover placement:** valid; normal \`Board.place()\` semantics apply;
- **EXIT placement:** classifier declares it normal before this helper and
  must not call this helper;
- **equipment collection:** classifier declares it normal before this helper
  and must not call this helper.

## 5. Visible repair reserve helper

Conceptual API:

\`has_visible_exit_repair_reserve(resulting_board, retained_visible_cards, exit_card) -> bool\`

Inputs are limited to:

- the candidate's resulting board;
- the two cards retained from the exact visible pre-action hand;
- canonical EXIT card geometry.

Algorithmic contract:

1. for each retained visible card, enumerate
   \`legal_moves(resulting_board, (retained_card,))\`;
2. consider only \`Action.PLACE\` moves;
3. if the retained card is EXIT, skip it: EXIT itself is not an "ordinary
   repair card" under the Worker #10 definition;
4. for each legal ordinary placement:
   - clone \`resulting_board\`;
   - apply exactly that one placement using \`Board.place()\`;
   - compute standalone EXIT legal capacity on that repair board;
   - if capacity is positive, return \`True\`;
5. otherwise return \`False\`.

Allowed depth:

candidate placement -> **no draw** -> one retained-card ordinary placement ->
measure EXIT capacity -> **stop**.

Forbidden inside this helper:

- equipment collection as a repair;
- replacement draw;
- refresh;
- hidden draw inspection;
- third action;
- trajectory continuation;
- RNG.

Equipment collection is excluded because it cannot alter board geometry or
restore standalone EXIT placement capacity. A material card may still be used
as an ordinary placement if that placement is legal.

Multiple restoring placements do not create a preference; the helper remains
a boolean existential check.

## 6. Unsafe-candidate classifier

Conceptual API:

\`is_unsafe_capacity_kill_without_visible_repair_reserve(state, move, exit_card) -> bool\`

This helper is pure and matches Worker #10 semantics. Phase gating by
\`exit_seen\` belongs in V5 \`choose()\`, not in the geometric property itself.

Non-executable pseudocode:

\`\`\`text
function is_unsafe_capacity_kill_without_visible_repair_reserve(
    state,
    move,
    exit_card,
):
    if move.action != PLACE:
        return false

    chosen_card = state.hand[move.hand_index]

    if chosen_card.is_exit:
        return false

    current_capacity =
        standalone_exit_legal_move_count(state.board, exit_card)

    if current_capacity <= 0:
        return false

    preview =
        preview_ordinary_non_exit_placement_without_draw(state, move)

    post_capacity =
        standalone_exit_legal_move_count(preview.resulting_board, exit_card)

    if post_capacity > 0:
        return false

    repair_exists =
        has_visible_exit_repair_reserve(
            preview.resulting_board,
            preview.retained_visible_cards,
            exit_card,
        )

    return not repair_exists
\`\`\`

The helper does not inspect \`exit_seen\`, \`exit_placed\`, score, turn,
open-tunnel thresholds, merge count, or future draws.

## 7. V5 \`choose()\` pseudocode

Future class relationship:

\`VisibleRepairReserveV5Policy(BoundedMergeV4Policy)\`

Constructor contract:

- accept immutable canonical \`exit_card\`;
- initialize inherited V4 weights exactly as
  \`BoundedMergeV4Policy(setup_weight=250)\`;
- expose no new score weight and no tunable safety penalty;
- retain no mutable per-game history.

Non-executable implementation-ready pseudocode:

\`\`\`text
function choose(state, rng):
    moves = state.legal_moves()

    if moves is empty:
        return None

    # Phase gate 1 and 2.
    if state.exit_placed or state.exit_seen:
        return exact V4 choose(state, rng)

    current_capacity =
        standalone_exit_legal_move_count(state.board, self.exit_card)

    # Phase gate 3.
    if current_capacity <= 0:
        return exact V4 choose(state, rng)

    normal_moves = []

    for move in moves, preserving existing order:
        unsafe =
            is_unsafe_capacity_kill_without_visible_repair_reserve(
                state,
                move,
                self.exit_card,
            )

        if not unsafe:
            append move to normal_moves

    if normal_moves is non-empty:
        eligible = normal_moves
    else:
        # Lexicographic fallback: never invent no_legal_move.
        eligible = moves

    scored = [
        (
            score_features(move_features(state, move), self.weights),
            move,
        )
        for move in eligible, preserving eligible order
    ]

    best_score = max(score for score, move in scored)

    candidates = [
        move
        for score, move in scored
        if score == best_score
    ]

    return rng.choice(candidates)
\`\`\`

"Exact V4 choose" means the existing inherited V4/WeightedGreedy path with the
same source state and RNG. The safety helpers themselves consume no RNG.

No sort, set conversion, or independent candidate ordering may be inserted.

## 8. Invariants

A conforming implementation must satisfy all of the following.

1. V4-250 \`PolicyWeights\` are unchanged.
2. No new weighted \`MoveFeatures\` field is introduced for V5 safety.
3. Outside the active safety phase, move choice is behavior-equivalent to V4
   for the same state and RNG.
4. When all legal moves are unsafe, V5 restores the complete original legal
   move list and performs ordinary V4 scoring/tie selection.
5. Existing deterministic \`state.legal_moves()\` order remains authoritative.
6. V5 performs no independent candidate reordering.
7. The only RNG call remains the ordinary tie choice among equal best eligible
   moves.
8. No safety decision depends on hidden draw order or a replacement draw.
9. No policy object retains \`exit_seen\` or any per-game historical state.
10. \`exit_seen\` is canonical, monotonic, and copied exactly.
11. The classifier and its helpers do not mutate the source \`GameState\`.
12. The no-draw preview does not call \`GameState.apply()\`.
13. No post-zero recovery preference is added.
14. If current EXIT capacity is already zero, V5 is exact V4.
15. After EXIT has ever been seen, V5 is exact V4.
16. If EXIT is already placed, V5 is exact V4.
17. EXIT placement itself is never classified unsafe.
18. Collection itself is never classified unsafe.
19. Water-cover legality remains canonical \`Board.place()\` behavior.
20. Static injected EXIT geometry is model metadata, not hidden-state
    inspection.

## 9. Edge cases

### EXIT initially in hand

\`exit_seen=True\` immediately. V5 safety tier is inactive from the first
choice; behavior is V4.

### EXIT currently visible

A valid canonical state has \`exit_seen=True\`; V5 is V4.

### EXIT seen earlier but no longer visible

\`exit_seen\` stays true. V5 is V4.

### Current EXIT capacity already zero

V5 safety tier is inactive. No post-zero repair preference is introduced.

### All legal moves unsafe

Fallback makes all legal moves eligible and applies unchanged V4 scoring.
V5 cannot create \`no_legal_move\`.

### Only one legal move and it is unsafe

The normal tier is empty, fallback restores that single move, and it is
selected by V4 semantics.

### Candidate is EXIT placement

Always normal. It is never passed through the non-EXIT placement preview.

### Candidate is equipment collection

Always normal. Collection does not alter board geometry.

### Retained hand contains EXIT

In a canonical active phase this should not occur because a visible EXIT
implies \`exit_seen=True\`. The repair helper nevertheless treats EXIT as not
an ordinary repair card and skips it.

### Retained cards have zero legal ordinary placements

No visible repair reserve exists; a zero-capacity candidate therefore meets
the reserve-negative part of the unsafe definition.

### Multiple retained-card repairs exist

The reserve is simply true. V5 does not rank or prefer the repair moves.

### Water-cover candidate

It is evaluated with the same \`Board.place()\` overlap/water rules as normal
play. It can be normal or unsafe solely according to resulting EXIT capacity
and the exact visible-repair-reserve test.

### Candidate itself wins

During the active phase \`exit_placed=False\`; under canonical victory rules an
ordinary non-EXIT placement cannot itself complete a win. EXIT placement is
normal and follows V4. Outside the active phase all winning semantics are V4.

### Game state already terminal

The simulator's existing terminal checks remain authoritative. V5 does not
change terminal detection. If \`choose()\` is nevertheless called with no legal
moves, it returns \`None\` exactly as the existing policy path.

### Direct/manual state construction

A valid directly constructed state with EXIT currently visible or already
placed must have \`exit_seen=True\`; the proposed construction invariant in
\`GameState\` prevents an inconsistent visible-but-unseen fixture without
scanning hidden cards.

## 10. Later unit-test matrix

Worker #11 does not write these tests. A later implementation must add them.

### \`exit_seen\`

1. initial dealt hand without EXIT -> false;
2. initial dealt hand with EXIT -> true;
3. non-EXIT normal draw while false -> stays false;
4. EXIT normal draw -> true;
5. refresh without EXIT while false -> stays false;
6. refresh revealing EXIT -> true;
7. later refresh after prior sighting -> stays true;
8. EXIT placement -> true and never reset;
9. direct state with visible EXIT satisfies visible-implies-seen invariant;
10. \`clone_state()\` preserves false exactly;
11. \`clone_state()\` preserves true exactly;
12. no lifecycle operation changes true back to false;
13. hidden EXIT remaining in draw pile does not by itself set true.

### Standalone EXIT capacity

1. helper count equals
   \`len(legal_moves(board, (exit_card,)))\` on positive capacity;
2. zero-capacity board returns zero;
3. board remains byte/structure equivalent after the call;
4. no hand/draw state is required.

### Candidate preview

1. exact origin and quarter-turn are applied;
2. two retained cards preserve original hand identity/index;
3. source board/hand/draw pile/counters remain unchanged;
4. water-cover placement uses canonical overlap behavior;
5. collect input is rejected/not routed here;
6. EXIT input is rejected/not routed here;
7. no replacement card appears in retained cards.

### Visible repair reserve

1. repair exists only in retained card 1 -> true;
2. repair exists only in retained card 2 -> true;
3. repair exists in both -> true;
4. no repair -> false;
5. repair would require replacement draw -> false;
6. repair would require refresh -> false;
7. repair would require equipment collection -> false;
8. retained equipment card can count only through a legal ordinary placement;
9. retained EXIT is skipped as a repair card;
10. retained cards with zero ordinary placements -> false;
11. source/resulting board passed in remains unchanged after the helper.

### Unsafe classifier

1. positive capacity -> candidate zero -> no reserve -> unsafe;
2. positive capacity -> candidate zero -> reserve exists -> normal;
3. positive capacity -> candidate remains positive -> normal;
4. capacity already zero -> false/normal property result;
5. collect move -> false;
6. EXIT placement -> false;
7. source \`GameState\` remains unchanged;
8. classifier consumes no RNG and no draw.

### V5 selection

1. unsafe move has higher V4 score than a normal lower-scoring move -> normal
   move is selected;
2. multiple normal moves -> exact V4 scoring among normal moves;
3. tied normal moves -> existing RNG result/order semantics preserved;
4. every move unsafe -> exact V4 fallback across all moves;
5. single unsafe legal move -> fallback selects it;
6. capacity already zero -> V4-equivalent choice;
7. EXIT already seen -> V4-equivalent choice;
8. EXIT already placed -> V4-equivalent choice;
9. kill with visible reserve -> remains normal;
10. direct capacity-preserving placement -> normal;
11. collection -> normal;
12. EXIT placement -> normal;
13. V5 weights equal \`BoundedMergeV4Policy(setup_weight=250).weights\`;
14. repeated same state/RNG preserves deterministic tie behavior;
15. no safety helper changes the source state or draw order.

## 11. Later implementation-evaluation preregistration

This section specifies the next bounded experiment but does not execute it.

### Compared policies

Exactly two:

- comparator: \`BoundedMergeV4Policy(setup_weight=250)\`;
- treatment: the single \`VisibleRepairReserveV5Policy\` design specified in
  this document.

No alternate V5 variant, penalty, threshold, or weight sweep is allowed.

### Model

Use the same fixed model:

- \`data/deck-v1.json\`;
- EXIT geometry from \`data/deck-observations-v0.json\`;
- \`v0-threshold-equipment\`;
- raincoats >= 3;
- ropes >= 2;
- START easy / 5 exits;
- hand size 3.

### First evaluation seed scope

Use only the same 23 already-spent Worker #10 development/diagnostic seeds:

\`2001, 2004, 2005, 2020, 2024, 2034, 2084, 2098, 2104, 2110, 2129, 2130, 2138, 2168, 2171, 2212, 2238, 2282, 2286, 2314, 2334, 2371, 2372\`.

No fresh confirmation seed is allowed in this first implementation evaluation.

Before interpreting V5, the V4 comparator must reproduce the canonical
starting checkpoint on these spent seeds.

### Required 18 persistent Class-A checkpoints

Track all of the Worker #10 persistent transitions:

- \`2001:a25:s24\`
- \`2004:a8:s7\`
- \`2020:a22:s21\`
- \`2024:a20:s19\`
- \`2034:a18:s17\`
- \`2084:a18:s17\`
- \`2098:a17:s16\`
- \`2104:a6:s5\`
- \`2110:a15:s14\`
- \`2129:a21:s20\`
- \`2130:a26:s25\`
- \`2138:a12:s11\`
- \`2168:a35:s34\`
- \`2171:a23:s22\`
- \`2212:a34:s33\`
- \`2314:a22:s21\`
- \`2334:a13:s12\`
- \`2372:a17:s16\`

### Required six reversible false-positive checkpoints

Track all accepted Worker #10 false positives:

- \`2024:a14:s13\`
- \`2130:a19:s18\`
- \`2168:a26:s25\`
- \`2168:a30:s29\`
- \`2282:a6:s5\`
- \`2372:a13:s12\`

Seed \`2282\` receives explicit trajectory attention because its flagged
checkpoint belongs to a canonical winning V4 trajectory.

### Trajectory-level diagnostics to record later

For each V4/V5 seed pair, record at minimum:

- final \`won\`, failure reason, turns, final open tunnels, visible water,
  raincoats, ropes, equipment readiness, EXIT placed;
- first \`exit_seen\` transition and whether/when EXIT is placed;
- first action where V5 diverges from V4, if any;
- V4 move and V5 move at that divergence;
- current EXIT capacity before the decision;
- normal/unsafe legal-move counts under the V5 tier;
- whether the V4-chosen move was classified unsafe;
- whether a visible repair reserve existed;
- whether the all-unsafe fallback was invoked;
- resulting immediate EXIT capacity after the selected move;
- first zero-capacity state/interval, if any;
- whether capacity later recovers;
- whether the exact canonical target transition was reached.

For every required target transition, record one of:

1. exact checkpoint reached and action evaluated;
2. checkpoint not reached because V5 had already diverged, including the
   earlier divergence turn/action.

Do not force a counterfactual historical action after the live V5 trajectory
has diverged.

For seed \`2282\`, explicitly record whether V5 suppresses
\`2282:a6:s5\`, the first resulting divergence, later EXIT-capacity history,
EXIT sighting/placement, and final outcome.

The experiment is descriptive development evaluation only. No confirmatory
p-value, no fresh holdout, and no win-rate benefit claim is authorized.

## Known accepted risk

The six reversible false positives are retained deliberately, not repaired by
another feature:

- \`2024:a14:s13\`
- \`2130:a19:s18\`
- \`2168:a26:s25\`
- \`2168:a30:s29\`
- \`2282:a6:s5\`
- \`2372:a13:s12\`

The sole winning false positive is \`2282:a6:s5\`.

This design therefore authorizes implementation/evaluation only after mother
orchestration acceptance; it does not claim V5 is beneficial.

## Implementation risks to preserve in handoff

- Correct \`exit_seen\` lifecycle is essential; policy-local history is
  forbidden.
- Candidate safety must never call \`GameState.apply()\`, because that consumes
  the replacement draw.
- Immutable EXIT geometry injection must match the fixed deck's canonical EXIT
  definition without inspecting hidden card order.
- Nested legal-move enumeration adds computation, but performance optimization
  must not change move order or semantics.
- The six accepted reversible false positives, especially winning seed 2282,
  remain intentional evaluation risks rather than targets for post-hoc tuning.

## Decision

Worker #11 freezes the above as the implementation-ready V5 design.

It does **not** implement V5, add \`exit_seen\`, add helpers, modify tests, or
run a V5 experiment.

The next step is intentionally left to the mother orchestration session.
