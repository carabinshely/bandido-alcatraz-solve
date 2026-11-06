# Worker35 deterministic decision audit v1

This wire contract defines serialization only. Candidate and reference must not
import each other's validation, scoring orchestration, decision or guard helpers.
Sharing the frozen canonical engine/scoring and `worker32.evidence` serialization
(`canonical`, `sha`, `card`, `observation`, `move`) is permitted and disclosed.

## Interface

`QuotaReserveClosurePolicy(*, catalog: tuple[CardDefinition, ...], start_card:
CardDefinition, exit_card: CardDefinition)` snapshots a public immutable catalog.
`catalog` contains all 69 draw-deck identities including EXIT, not START. START is
the separate easy setup identity. The runner binds these inputs to frozen model
blobs; synthetic tests use invented inventories/geometries only.

`evaluate(observation, rng, *, limits=None)` returns `(Move | None, science, cost)`.
`choose(observation, rng)` returns only the move. `OperationLimits` is a frozen
dataclass with `legal_enumerations`, `previews`, `exit_geometry_checks`, each a
nonnegative integer or `None`. No production ceiling is set by this contract;
the execution freeze must supply them and independently supervise wall time,
memory and evidence. `IntegrityError` and `ResourceExceeded` fail explicitly.

The canonical live public contract includes exact hand conservation:
remaining=69-turns-set_aside; remaining must be positive and own hand length is
min(6,remaining). Set-aside is either zero or six: before draw stock empties the
hand remains full; the only short refresh discards those six and empties draw
stock permanently. With set-aside six, remaining equals own-hand length, and
still-needed material supply must equal its own-hand count. A closed board or
exhausted hand is a terminal input, not an empty-live-legal-list decision.

## Science exact keys

- `schema`: `worker35-scientific-v1`
- `input_before`, `input_after`: SHA256 of canonical public observation wire
- `roots`: complete canonical-order list of `{move, score}`; move uses established
  move serialization, score is the unchanged integer V4 score with setup_weight250
- `supply`: keys `raincoat`, `rope`, each `{quota, collected, total, placed,
  deficit, available, own_hand}`; all integers, placed includes covered identities
- `tiers`: `{T0, F, T, C, final}`, each ordered zero-based root-index list
- `guards`: one record per root, exact keys `{eligible, reason, after,
  exit_legal_count}`; eligible is boolean; after is null or `[open_tunnels,
  visible_water_cells, water_obstruction, trapped_water_cells]`; exit_legal_count
  is null unless actually evaluated, otherwise its nonnegative integer count
- `flags`: `{reserve_filter_active, reserve_primary_tier_changed,
  closure_branch_selected, true_original_all_collect_crossover,
  reserve_filter_mediated_change}`, all booleans
- `chosen_index`: null or zero-based root index
- `chosen`: null or established move serialization of the selected root
- `rng_before`, `rng_after`: SHA256 of canonical `rng.getstate()`

If T contains any PLACE, every guard is `{eligible:false,
reason:"branch_not_active",after:null,exit_legal_count:null}` and C is empty.
An empty L has the same empty C, all tiers/roots/guards empty, null chosen/index,
false flags and unchanged RNG. Public validation still runs for empty L.

When T is nonempty/all COLLECT, process every root in order. Guard reasons use
this exact first-match order:

1. `not_place` for COLLECT
2. `reserve_filtered` for a root outside F
3. `not_needed_material` for absent material or met quota
4. Preview once with canonical no-draw preview; always record all four metrics
5. `not_reduced` if resulting open >= original open
6. `closed_tunnels` if resulting open <= 0
7. `visible_water_increased`
8. `water_obstruction_increased`
9. `trapped_water_increased`
10. If EXIT unplaced, evaluate standalone canonical EXIT capacity; record count
    and use `no_exit_capacity` if zero
11. `eligible` otherwise, with eligible=true and root included in C

Every pre-preview rejection has null after/EXIT count. Every pre-EXIT rejection
has null EXIT count. If EXIT already placed, EXIT count remains null.

F contains all roots except indispensable still-needed material placements
(available <= deficit). T0 maximizes all scores, T maximizes over F. If C is
nonempty, final maximizes scores over C, otherwise final=T. All ordered lists
preserve canonical root order. Selection calls the supplied RNG's `choice` once
on the Move list for final, including a singleton, and zero times when L empty.

Flags are exactly:

- reserve_filter_active = F differs from all root indices
- reserve_primary_tier_changed = T differs from T0
- closure_branch_selected = C nonempty
- true_original_all_collect_crossover = closure_branch_selected and T0 is
  nonempty/all COLLECT
- reserve_filter_mediated_change = closure_branch_selected and T differs from
  T0 and T0 contains at least one PLACE

## Separate physical costs

Exact keys: `{legal_enumerations, previews, exit_geometry_checks, roots}`.
`legal_enumerations` counts actual canonical `moves.legal_moves` and
`moves.placement_moves` entries, including preview membership validation and
standalone EXIT checks. `previews` counts actual
`strategy.preview_move_without_draw` entries; `exit_geometry_checks` counts
actual `strategy.standalone_exit_legal_move_count` entries. `roots` is len(L).
These are physical operations, not a semantic one-ply bound. A scoped profile
hook observes function entries without patching canonical modules and restores
the prior profile hook even on failure. Checker costs are accounted separately;
they need not equal candidate costs if its independent implementation differs.
The hook itself adds runtime overhead, included in measured wall/CPU costs; it
does not establish a resource ceiling. Existing callable Python profile hooks
are forwarded and restored. An active non-callable native profiler cannot be
safely forwarded/restored through `sys.setprofile`, so evaluation fails
explicitly before replacing it; the native profiler remains untouched.
