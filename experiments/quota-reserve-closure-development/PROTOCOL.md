# Worker35 preregistration: quota-reserve closure override

Status: SCIENTIFIC DESIGN AND POPULATION PREREGISTERED. Worker34 acceptance is complete at https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5947173308, current main87ddc894668ec60e7a8419e65308cadb0ced6ed9. Under the owner's autonomous mandate, Forge authorizes native implementation and synthetic preflight of the exact candidate, independent reference and bounded execution harness. Actual cohort execution is NOT authorized until a separate exact source/runtime/resource freeze and execution-go record. No candidate outputs on real observations or new games have been computed. All scientific rules, the400-seed population, three-pass order and net+8 screen below are fixed before implementation; resource limits will be frozen prospectively before any real execution, never changed after observing outcomes.

## Hypothesis and scope

Test whether using a still-needed equipment card for an immediately useful tunnel closure, while preserving sufficient public equipment supply, improves win probability over canonical V4-250. This is one complete one-ply candidate, with no fitted coefficients or weight sweep. It can cross an all-COLLECT unfiltered V4 tier; Worker31 only refined choices within that tier. Worker34's reported component tradeoff motivates a test but does not validate this rule or imply a win-rate improvement.

Only repository `carabinshely/bandido-alcatraz-solve`; canonical solo v2, easy five-exit START, six-card hand, exact three raincoats/two ropes, quota-limited optional COLLECT and unchanged full-hand refresh. Canonical legality, geometry, deck, shuffle, RNG and legal-move order remain unchanged.

## Public-supply invariant

For each material m, let q_m be its required quota (3 raincoats, 2 ropes), c_m its public collected count, T_m its fixed physical deck total (12 raincoats, 8 ropes), and p_m the number of physical identities of that material in the complete public placement history, including covered cards. For a still-needed material, define d_m = q_m - c_m > 0 and A_m = T_m - c_m - p_m.

A_m is exact unconsumed supply across own hand and draw pile under these preconditions: fixed canonical physical deck; no creation/duplication; irreversible collection; monotone collected counters; complete public placement history; and refresh allowed only when the entire hand has no legal action. A hand containing a still-needed material always has legal COLLECT, so it cannot refresh. A material needed now was also needed earlier. Therefore no still-needed copy could have entered face-down set-aside. Ordinary refresh returns cards and is not subtracted. After short-pile refresh, A_m must equal that material's own-hand count.

This is a stock count, not a guarantee of drawing or collecting before terminal failure. It requires no hidden identity, deck order, teammate hand, private set-aside identities or inference about a future draw. Static canonical card identity-to-material and EXIT-geometry data are allowed public catalog inputs.

Validate the full public placement and collection history and own-hand physical identities against the fixed catalog, including covered placements. Reject unknown/duplicate IDs, cross-zone reuse, material/geometry mismatch and collected-count/history mismatch. Reconstruct public board geometry from the complete placement history and match the observation. Do not silently repair malformed input or reconstruct hidden identities. A physically valid live state with A_m < d_m is already supply-infeasible, not necessarily malformed; the policy still follows the rule below.

## Exact complete candidate

The policy domain is canonical live decision points after the runner's existing terminal checks. Terminal observations are not policy inputs; a live state may have no legal move and need engine-owned refresh handling. Let S4(a) be the unchanged canonical V4-250 immediate move score. Every hypothetical placement is detached, one-action and no-draw; repeated internal previews do not create a deeper search horizon.

1. Validate the live public observation and enumerate the complete legal list L in canonical order. If genuinely empty, return None and consume no RNG.
2. Score every member of L with S4. Let T0 be all maximizers over the unfiltered L, in canonical relative order.
3. Form policy-admissible list F by excluding a PLACE of still-needed material m when A_m <= d_m. This does not change engine legality. Let T be all maximizers of S4 over F, in canonical relative order. F cannot be emptied solely by this filter: the same hand card has a legal COLLECT action.
4. If T contains any PLACE, the final choice tier is T.
5. Otherwise T is entirely COLLECT. Form C from every PLACE in F satisfying all of:
   - Its card carries still-needed material m and A_m > d_m
   - The resulting board has strictly fewer open tunnels and still has at least one open tunnel
   - Visible-water count, water-obstruction count and trapped-water count each do not increase
   - If EXIT is unplaced, the resulting board admits at least one legal placement of the fixed canonical EXIT card
6. If C is nonempty, the final tier is all maximizers of S4 over C, preserving canonical relative order. Otherwise it is T.
7. Call the existing RNG's choice exactly once on the final tier, including a singleton. Scoring, guards and previews consume no RNG. Use no persistent policy state, sampling, hidden draws, horizon extension or outcome lookup.

The selection rule uses reserve-filtered T, not T0. Log F != L (reserve filter active), T != T0 (reserve primary tier changed), and whether the closure branch selected from C separately. A true original all-COLLECT crossover requires T0 to be entirely COLLECT and the chosen action to come from C. If filtering removed an original PLACE tier before the closure branch ran, report a reserve-filter-mediated change, not an original all-COLLECT crossover. T0 is an audit reference and does not silently replace T in the rule.

None is reserved for a genuinely empty L. Malformed input, an impossible empty F/final tier, resource overflow or independent-checker disagreement must fail explicitly. Never convert these into a V4 fallback, None/refresh, a terminal game loss or a valid completed screen.

The positive-open-tunnel condition prevents immediate closed-tunnel loss from the override. The water guards preserve the model's local visible hazard measures, not every possible future water repair. The EXIT guard ensures current standalone capacity, not future arrival or continued capacity. Global supply filtering prevents deliberately spending an indispensable equipment copy but cannot guarantee survival until collection. These limitations are part of the hypothesis, not grounds for post-result rule changes.

## Prospective paired spent-development design

Worker34 acceptance is complete and native implementation is authorized by this record. Implement and independently review this exact candidate, validate correctness/resources using invented fixtures only, then record exact source, environment and resource ceilings before the separate execution-go. Do not evaluate the candidate on any real cohort observation during preflight.

- Entire permanently spent population: seeds 1000000 through 1000399 inclusive
- Three complete serial ascending passes: V4-250 control, candidate, candidate replay
- Exactly 400 + 400 + 400 game executions; no subset selection, seed expansion, coefficient sweep or outcome-dependent stopping
- Pin candidate, independent reference/checker, harness, model/deck blobs, setup, runtime and workflow; leave canonical model/RNG/order unchanged
- Retain all attempted runs and partial evidence. A resource or integrity failure cannot be relabeled as a complete negative screen or repaired by silently changing caps, seeds or policy
- No fresh seeds without later candidate freeze and separately approved confirmation preregistration

### Integrity and reproducibility gates

Require complete 400-seed coverage in each pass; exact control matching against accepted baseline evidence at all available levels; exact candidate/replay trace agreement; legal moves; correct quotas, victory and physical conservation; public-input-only decisions; observation/real-state immutability; and compliance with prospectively frozen resource limits. Independent checking must reproduce each candidate decision's physical public-input validation, supply counts, scores, guards, ordered T0/F/T/C/final tiers and chosen-action/RNG behavior without importing candidate decision helpers. Shared frozen canonical geometry is permitted but is not an independently validated game engine.

Before cohort execution, synthetic fixtures must cover quota boundaries, covered-card history, public-ID/material/geometry/count-history validation failures, ordinary/short-pile refresh invariants, the live-input contract, terminal closure prevention, water/EXIT guards, mixed and tied tiers, reserve-filter attribution versus true T0-all-COLLECT crossover, singleton/empty RNG behavior, explicit failure paths and hidden-zone independence. Preserve public observations, canonical legal roots, scores, guard classifications, T0/F/T/C/final tiers, selected moves, actual physical operation counts and RNG fingerprints for every decision, plus final conservation/victory evidence.

### Outcome screen and diagnostics

Conditional on all integrity/reproducibility/resource gates, the fixed development threshold for potential advancement is candidate wins minus control wins >= 8 (at least 53 versus a reproduced 45 control wins). This is a spent-development screen, not fresh confirmation, significance evidence or automatic advancement.

Prespecified descriptive diagnostics: full paired 2x2 and gained/lost outcomes; equipment-ready terminal count relative to control's 396/400; water/EXIT and other terminal failures; reserve-filter activity, reserve primary-tier changes and closure-branch selections; and true T0-all-COLLECT crossovers as separately defined above. Equipment completion is not an advancement gate: the program objective is win probability, and a useful geometry tradeoff may reduce equipment completion among losing games. Exact quota/victory/conservation validity remains mandatory. Mechanism activity is reported, not used to invent a post-result threshold. If there are no actual closure overrides, do not attribute a change to that mechanism; any effect can only support the complete observed policy behavior.

A complete result below net +8 closes this exact candidate without post-result tuning. Passing permits consideration of separately frozen fresh confirmation; it does not establish improvement. Report uncertainty and the whole cohort, including unfavorable outcomes.

## Prospective resource-freeze requirement

The scientific horizon is one action, but this is not a one-physical-enumeration or one-physical-preview-per-root contract. In the current source, score_move_no_draw calls move_features_no_draw, which calls preview_move_without_draw; the preview checks membership by re-enumerating the state's legal moves for each PLACE root. Separate guard/EXIT inspection may perform further previews and enumerations. Instrument and account for all actual physical legal enumerations, previews and standalone EXIT geometry checks, including independent validation. Do not require a cache or new optimization merely to meet an invented operation bound.

Cost-only historical evidence: accepted Worker31 run 36848990406, job 110325910903, records its complete three-phase cohort step from 10:32:34 to 11:08:17 UTC on 2026-10-01 (35m43s), focused synthetic tests at 1m54s, and reconciliation at 1m13s. This used another candidate/call graph and is planning context, not a bound for this candidate or its independent checker. Source: https://github.com/carabinshely/bandido-alcatraz-solve/actions/runs/36848990406/job/110325910903 and the already accepted local metadata.

No actual run is approved until resource caps are validated and frozen in the separate execution record. Earlier figures (32,768 roots/previews, 30 seconds per decision, 2 GiB worker memory, 120 minutes for game passes, 60 minutes for verification, 4 GiB expanded evidence and 1 GiB archive) were unvalidated estimates and are not requirements or evidence that this implementation fits. Derive defensible per-call/whole-run physical-operation, wall-time, memory and evidence limits from the reviewed call graph and permitted synthetic/resource checks. Confirm or replace these estimates prospectively on the pinned environment, freeze all caps before execution and before candidate cohort outcomes, and retain fail-explicit behavior. No silent post-result cap increase, fallback or cohort truncation.

## Implementation stage and mandatory execution gates

- Accepted repository base:87ddc894668ec60e7a8419e65308cadb0ced6ed9, tree3e0c450ed82ecd47fdd1e239da47d97567d584a6. Reconcile live main and competing work before publication or execution.
- Canonical source/data comparator remains c50a7ab8e73eaf3c497c5d1c9fef5cbe53261853 and its26 unchanged baseline/model/data blobs. New isolated research files do not alter that comparator.
- Canonical baseline is V4-250 under v2 exact quota-limited collection, solo/easy5/hand6, unchanged MAX_STEPS=1000. The accepted normalized400-control array SHA256 is a4d2d06e5592caa35c03d00337d0254c07f767d5cb8ee0777cbb51f543803021; require exact reproduced control evidence before interpretation.
- Candidate and independently authored reference must not share custom decision helpers. Shared frozen canonical geometry/scoring definitions are allowed and must be disclosed. Use the own dot's native code/GitHub capabilities; no new Codex or Work task is required without a genuine missing capability.
- Selected-state evaluation and all actual games run only on the existing bandido-alcatraz-ci runner, using prospectively pinned CPython3.11.16 and canonical randomization semantics. Native preflight uses invented synthetic fixtures only; no user local-computer access.
- Reuse reviewed persistence, trace, model/source checks and failure handling from prior accepted work where appropriate. Avoid unrelated refactoring or a new infrastructure framework.
- Before any real candidate evaluation, freeze complete candidate/reference/harness/workflow sources, baseline input hashes, runtime, physical-operation/time/memory/output limits, mechanical evidence-sharding rules and all acceptance conditions. Synthetic preflight and independent exact-head reviews must pass. A separate execution-go comment will identify the one admitted complete attempt.
- Preserve every failed attempt, partial trace and receipt. Distinguish inaccessible pre-execution infrastructure, integrity-invalid evidence, resource-incomplete evidence, valid complete negative and valid complete advancing development result. No silent fallback, resume, shortened cohort, cap extension or source repair after results. Harness-only repairs require a separately recorded full rerun under the unchanged scientific question and population.
- All raw evidence must be independently verified and persisted with fresh byte/hash readback in the canonical Bandido Drive folder. Compact manifests and the permanent seed ledger are Git-tracked. Complete exact-head external review attempt plus both independent internal reviews, affected CI and guarded squash/postmerge verification are required before acceptance. An unavailable external service follows the owner's documented waiver policy.

The complete policy, tie/RNG contract, all400 permanently spent seeds, ascending control→candidate→replay order and net+8 screen are frozen here. No equipment-completion threshold or minimum override count can be introduced after results. No fresh confirmation population is allocated by this record. Any substantive scientific change requires a new prospective protocol before outcomes.

## Inspected sources

- Observation, actions and refresh: https://github.com/carabinshely/bandido-alcatraz-solve/blob/7a2b681f2d78c9e4cef466eb5250c4bd6c6c52ed/src/bandido_alcatraz/game.py
- V4 scoring and previews: https://github.com/carabinshely/bandido-alcatraz-solve/blob/7a2b681f2d78c9e4cef466eb5250c4bd6c6c52ed/src/bandido_alcatraz/strategy.py
- Public placement history and geometry: https://github.com/carabinshely/bandido-alcatraz-solve/blob/7a2b681f2d78c9e4cef466eb5250c4bd6c6c52ed/src/bandido_alcatraz/board.py
- Prior Worker31 protocol: https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5928556762

These links identify inspected frozen source history. The new experiment must separately pin its accepted current canonical source; these links are not its future execution freeze.
