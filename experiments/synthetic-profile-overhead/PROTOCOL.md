# Worker36 synthetic aggregate profiling overhead diagnostic

Status: prospectively selected Worker36 protocol following independent static review. Implementation and synthetic fault-test preparation may proceed. No measurement allocation is admitted yet: a later exact-head source/runtime/resource freeze and separately recorded one-shot synthetic execution admission are required before any of the 40 allocated evaluator calls. Preflight tests must use stubs/invented fault fixtures and must not execute the five measurement fixtures or real observations.

## Question and interpretation boundary

How much faster do the unchanged Worker35 candidate and independent-reference evaluator bodies run on five fixed invented fixtures when Python profiling is entirely suppressed in a disposable synthetic-only process?

The motivating resource observation was inclusive time inside candidate/reference wrappers, not exclusive profiler time. It did not identify the bottleneck. This diagnostic compares the original metered path P with a science-only, hook-suppressed path U. It tests aggregate profiling overhead, including callback dispatch and bookkeeping, without assuming that profiling dominates.

U is a measured hook-suppressed contrast for the same evaluator bodies. It is not a production implementation, and the contrast neither bounds nor predicts the performance of a future fully metered implementation. This experiment cannot establish which profiling layer is responsible, universal semantic equivalence, exact unprofiled physical costs, cap/error equivalence, a real-game runtime forecast, or policy efficacy. The independent reference runs in every successful cell in both conditions.

No actual game observation, game seed, raw candidate outcome, or held-out population may be inspected or used. The Worker35 interrupted attempt remains closed and has no efficacy interpretation. There is no old-GO reuse, resume, replacement development cohort, replay completion, or automatic research rerun. Fresh confirmation remains unallocated.

## Repository and source restoration

Repository: `carabinshely/bandido-alcatraz-solve` only.

- Post-checkpoint main: `9c1eeeb8a26868d41f8d8d89b17fc897a60cb38b`
- Main tree: `e05ed74aba3b290f194e2871d950fa26ead6c55e`
- Merged checkpoint: [PR39](https://github.com/carabinshely/bandido-alcatraz-solve/pull/39)
- Post-merge CI: [run 37108669492](https://github.com/carabinshely/bandido-alcatraz-solve/actions/runs/37108669492); its successful completion must be verified before later admission
- Frozen computational comparator: `7ac2f62c9c5c9dcac9ec9b8770382960f985acc2`

PR39 removed the transient Worker35 implementation from main. Do not assume its benchmark, candidate, reference, or harness exists in the new checkout. Restore the exact comparator source blobs into an isolated temporary package owned by this synthetic attempt. Preserve the original package and scripts layout so imports resolve within that package. Obtain its complete source dependency closure by static inspection before the execution freeze, pin every restored file by repository path, Git blob identity and raw SHA256, and reject missing or changed bytes. Pin and restore canonical raw Git blob bytes, including their exact final-newline convention. A connector-rendered source copy may add an extra newline; it is not authoritative unless its bytes reproduce the pinned blob identity. Do not normalize whitespace or hash a rendered copy as though it were the canonical blob. Canonical engine and serialization dependencies must also come from that exact comparator, not a mixture of main and historical modules. Data may be hash-checked as source provenance; the experiment must not load a real deck or observation dataset.

The new diagnostic driver and its source manifest are separate, explicitly hashed inputs. Verify resolved module file paths and hashes before any policy call and record them. Use isolated imports, disable bytecode writes, and reject ambient profile/trace hooks. Do not patch restored source files, restore the old workflow/admission mechanism, or invoke the old benchmark CLI's `main`, research `initialize`, `run`, `one_game`, or any game entry point. Restoring source for imports conveys no research execution authority. Preserve the restored-source manifest and content hashes with the attempt evidence.

Frozen primary sources:

- [Fixture constructor and full wrapper](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/scripts/benchmark_worker35_synthetic.py), blob `c552da477744f0f0984204bb3078331ab48cfb54`
- [AuditPolicy and durable decision wrapper](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/scripts/run_quota_reserve_closure_development.py), blob `45d2af37cf601395a806752cf3eec60b7d6a5e1a`
- [Meters, protection and evidence helpers](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/scripts/worker35_resources.py), blob `27730c1f539fab88c8d2a7c8670fd982e3f010b1`
- [Candidate](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/src/bandido_alcatraz/quota_reserve_closure.py), blob `da66df30c7e323cfe1e2fc7255c34e8952d2d504`
- [Independent reference](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/src/bandido_alcatraz/quota_reserve_closure_reference.py), blob `cece8e6f7cab6286bebf034e0310f7be90dca632`
- [Original harness contract](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/experiments/quota-reserve-closure-development/HARNESS.md) and [resource reasoning](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/experiments/quota-reserve-closure-development/resource-planning.md)
- [Candidate tests](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/tests/test_quota_reserve_closure.py), [reference tests](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/tests/test_quota_reserve_closure_reference.py), and [harness tests](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/tests/test_quota_closure_development.py), read-only design evidence

## Invented fixtures and exact allocation

Reuse the frozen benchmark's fixture construction without scientific changes. Sizes are exactly `0, 4, 8, 40, 48`. Each has an invented two-cell START, 12 distinct one-cell raincoat caps, eight rope caps, 48 ordinary cards, one invented EXIT, and coat-0 through coat-5 in hand. For size n, only the first n ordinary cards are four-way and are manually placed at `(2+i, 0)`. Preserve all 69 identities, the remaining invented draw-pile order, counters, setup and conservation witness.

Use the frozen fixture-only `Random(11)` initializer. The literal 11 is not a research/game seed allocation. Candidate and reference receive distinct RNG objects with exactly the same initial state. Each reference receives the same detached public observation content as its candidate, copied before candidate evaluation. Neither policy receives the real-state witness or hidden zones.

Schedule, fixed before measurements:

1. Cells 1–10: repetition 1, sizes `0, 4, 8, 40, 48`, P then U at each size
2. Cells 11–20: repetition 2, sizes `48, 40, 8, 4, 0`, U then P at each size

Each cell uses a fresh serial child process, newly constructed state/RNGs, and an exclusive output directory. Candidate precedes reference within every cell. No warm-up, calibration call, sampling canary, concurrent timing, adaptive repetition count, excluded first result, replacement cell, or retry is allowed.

All children use the same pinned interpreter with exactly the flags `-B -s`, `PYTHONHASHSEED=0`, and `PYTHONDONTWRITEBYTECODE=1`. Clear other inherited `PYTHON*` environment variables, including `PYTHONPATH`; the driver installs only the frozen source-package paths. Do not use `-I` or `-E`, which would ignore the fixed hash seed, or add optimization flags. Record the effective flags and these environment settings in every cell's preflight. Keep CPython's default enabled garbage-collection policy, record `gc.isenabled()` and `gc.get_threshold()` before each cell's evaluator calls, and require the same default thresholds throughout. Do not disable GC, change thresholds, force a collection, or tune allocator/GC behavior for either condition.

The entire allocation is exactly **20 planned cells: 10 full P AuditPolicy wrapper calls and 10 direct U candidate/reference pairs**. Complete execution contains **20 candidate evaluate calls plus 20 reference evaluate calls, 40 evaluator calls total, zero games**. A failure stops the schedule; actual starts/returns may then be fewer and must be reported. Source checks and offline evidence verification must not evaluate a policy. Additional policy-bearing tests or preflight decisions are outside this allocation; they cannot be added to this attempt or hidden in setup.

## P and U execution paths

P calls the frozen `measure_wrapper` and full `AuditPolicy.choose`, including the whole-wrapper, decision, and policy meters, independent reference, public/engine checks, choice-event checks, canonical serialization, durable journals, and fsync. Its only interface addition is a thin timing delegate around each original `evaluate` invocation. The delegate returns the identical tuple unchanged and captures the complete reference scientific object for later equality verification. It does no I/O or scientific work inside the timed interval. P uses persistent attempt directories rather than the old CLI's automatically deleted temporary output.

U directly calls those same original candidate and reference evaluator methods. Within that disposable U child only, a narrow temporary shim makes Python profile-hook installation ineffective. Require the real `sys.getprofile()` to be None before suppression and after each evaluator; preserve the original setter and restore it in an explicit outer `finally`, including exceptions. The shim must not invoke registered callbacks, fabricate events, substitute counters, or change the evaluator source. Single-threaded execution and no ambient trace hook are prerequisites. A restoration failure invalidates the attempt.

U uses the same explicit OperationLimits values as P for interface consistency, but their physical-operation enforcement is inactive. Its separate diagnostic schema must state `physical_cost: null`, `physical_operation_caps_enforced: false`, `choice_events_observed: false`, and `production_admissible: false`. Never present its suppressed internal zero counters as measured costs. U does not call a weakened AuditPolicy, fake a successful production journal, or synthesize missing choice events. Full candidate/reference scientific returns and actual RNG states remain available for byte equality.

Both conditions use the identical timing delegate and clock-call order: capture monotonic wall and process CPU immediately before calling the original evaluator method, capture both immediately after its return, and record failures as failures rather than successful timings. This window includes each method's own input validation, scientific computation, RNG use, and hook setup/restoration. It excludes outer fixture construction, public/engine witnessing, journal I/O and inter-evaluator verification. No overhead subtraction is permitted. Compare these matched evaluator windows only: P's full-wrapper elapsed time must never be divided by U's direct-call time.

P retains its original check order and physical ceilings. U retains independently supervised wall/CPU, address-space, output and whole-cell limits, and performs its returned-root check only after successful durable capture of the scientific return. Its explicit lack of physical-operation cap enforcement is a synthetic diagnostic exception, not a production cap change. In either condition, the reference starts only after the candidate's scientific return has been successfully written and fsynced. This is an ordering requirement, not a guarantee that every in-memory return survives a kill, I/O failure, or output-cap failure. If capture fails or durability cannot be confirmed, do not start the reference; preserve the surviving prefix and mark the durable return missing or unconfirmed. Failures introduced by the new delegate or capture machinery do not establish production exception equivalence.

## Exact equality gates

For each cell, compare independently computed candidate and reference chosen move, complete canonical scientific bytes, and actual final RNG states. Retain the full canonical scientific objects from both implementations; matching two ungrounded digest strings is insufficient. Preserve ordered roots and scores, supply, all tiers, guards, flags, chosen index, input hashes, and RNG hashes. Record complete canonical initial/final RNG states as well as hashes.

Across all four cells for each fixture, require the same exact chosen move, complete scientific bytes, and initial/final RNG state bytes. This establishes equality of eight scientific returns per fixture when complete. Before/after public-observation bytes and the real invented-state witness must also agree, with all 69 identities conserved. A difference is an integrity failure, regardless of timing.

For P, independently reconcile all three existing meters: candidate and reference physical costs must match their harness observations; whole-wrapper counts must equal their sum on this fixture path; and each implementation must satisfy `legal_enumerations = 1 + previews + exit_geometry_checks`. Its repeated full candidate/reference call journals and decision traces must be byte-identical after mapping only the per-cell output directory. Wall/CPU/RSS and the separately named timing sidecar are excluded; no other field is dropped to obtain equality. Preserve P's original root limits, RNG-choice evidence, check order, hook/timer restoration, attempt-to-persist-before-post-check order, and independent-reference disagreement-capture path. No claim of production exception equivalence follows from the added timing/capture delegate or its possible failures.

U supplies no measured physical count, observed choice-event sequence, or physical-cap/error equivalence claim. Exact scientific/RNG equality cannot be relabeled as proof of those absent properties. No production optimization or alternative error path is tested here.

## Frozen resource limits

These protections are fixed for this synthetic experiment. They do not revise Worker35's old research freeze.

| Resource | Fixed bound |
| --- | ---: |
| Runner | Existing `bandido-alcatraz-ci`, serial children |
| Interpreter | CPython 3.11.16 |
| Interpreter executable SHA256 | `a15ccdaf07655a8667a3687b13171486c9a265d92273ba3ad820fbb64d2cfecc` |
| Each candidate/reference call protection scope | 360 wall seconds and 360 CPU seconds |
| Returned roots per evaluator | 16,384 |
| P legal enumerations per evaluator | 32,768 |
| P previews per evaluator | 32,768 |
| P standalone EXIT checks per evaluator | 16,384 |
| Complete P wrapper or U pair | 720 wall seconds and 720 CPU seconds |
| P whole-wrapper operations | Twice each corresponding per-evaluator operation bound |
| Sum across all P cells | 1,000,000 for each physical-operation category |
| Each process address space | Exact 512 MiB `RLIMIT_AS` |
| Complete measurement phase including child startup | 1,800 wall seconds and 1,800 summed parent/child CPU seconds |
| Raw attempt including sidecars and receipt | 64 MiB |
| Reserved terminal receipt | 1 MiB |
| One P decision trace | 16 MiB |
| One JSONL line | 8 MiB |
| Complete transport archive | 64 MiB |
| One transport payload part | 30 MiB |
| Local verification and preservation phase | 600 wall seconds |
| Workflow hard backstop | 45 minutes |

Enforce the measurement-phase process-group wall/CPU ceiling outside the policy hooks. Independent supervision must still stop U if its Python code hangs, and must stop the serial process group rather than leaving a child running. Per-call protections surround the evaluator and immediate durable return handling; the performance window remains the narrower identical method-call interval defined above. Use the same memory and output protections in both conditions. Require at least 1 GiB free attempt storage before work; recheck before transport/readback. Unexpected inherited limits, existing output directories, occupied hooks, wrong runner/runtime, or unavailable supervision block admission rather than weakening protection.

A cap is an abort boundary, not proof every possible state will fit. Preserve a durable prefix on overflow; do not truncate a record to fit, discard a cell, increase a cap, resume, or replace a failed attempt. CPU/wall/RSS measurements are descriptive resources, not scientific outcomes. Process high-water RSS is measured per fresh child and is not described as precise live evaluator memory.

## Evidence and canonical custody

Create a new exclusive Worker36 attempt identity and durable receipt before importing restored executable sources or starting a cell. Bind the preregistration URL, exact diagnostic head/tree, restored-source inventory, runtime/executable hash, resource freeze, source-manifest hash, ordered 20-cell schedule, runner, workflow run/attempt and fixed maximum 40 evaluator calls. Record source/runtime preflight as a distinct phase with zero evaluator starts.

Before each cell and each evaluator, fsync a start record containing its identity, fixture observation hash and initial RNG hash. Immediately after each returned evaluator, attempt durable capture of its full scientific/RNG evidence and elapsed clocks; record capture as confirmed only after successful write and fsync. P additionally retains its original production-path call/decision/resource journals. U uses separate diagnostic-only records and the explicit unmeasured-accounting flags. A complete cell receipt records the boundary/equality/restoration gates, actual starts/returns, and confirmed durable captures. The parent receipt records the current cell, ordered completed prefix, errors, status, resource totals and file inventory.

Keep partial files and external supervisor logs even when a child is killed. A hard kill, I/O error, or output failure may prevent capture of a returned object or its confirmation record; the supervisor records the missing/unconfirmed durable return and available exit/signal without inventing science, counts or a completed cell. If the main receipt is unreadable, preserve its original bytes and write a bounded, separately named failure sidecar. Never repair it into success. Once a candidate capture is confirmed durable, preserve those bytes even if its reference or a later persistence check fails; otherwise report the surviving prefix and the capture gap explicitly.

Use the repository's [canonical persistence contract](https://github.com/carabinshely/bandido-alcatraz-solve/blob/9c1eeeb8a26868d41f8d8d89b17fc897a60cb38b/docs/persistence.md): raw artifacts belong in [Bandido Alcatraz Solver / Experiment Artifacts / Raw](https://drive.google.com/drive/folders/1sQhQY3aKuHvQfyOTUIQjJGANCKOwKgEd), folder ID `1sQhQY3aKuHvQfyOTUIQjJGANCKOwKgEd`. Git contains a compact manifest; interpretation belongs in Issue #2. Do not change sharing or use a new storage account.

GitHub artifacts are temporary transport only. Use bounded deterministic packaging and, only as needed, split its byte stream into ordered parts of at most 30 MiB. Verify actual provider ZIP wrappers remain below the 32 MiB download limit. Retain every file's path/size/SHA256 and every transport part's order/size/hash. Independently verify transport reassembly and raw inventory, upload through the established Drive route, then freshly download/read back the stored bytes and verify their hashes. Record Drive file IDs, direct URLs, sizes and SHA256s in the compact manifest. Keep failed and incomplete evidence too. No successful timing classification is accepted until canonical custody is verified; a preservation blocker never grants another compute attempt.

## Analysis and fixed decision rule

Timing interpretation starts only after all 20 cells, exact source/runtime/equality/boundary/restoration checks, complete evidence inventory and canonical byte/hash readback pass. Equality/resource checks may fail closed during execution; no partial timing comparison is used to continue, stop early for success, select a fixture, or change the schedule.

For each cell define evaluator CPU time as candidate method CPU plus reference method CPU. For each of sizes 40 and 48, divide the sum of its two U evaluator CPU times by the sum of its two P evaluator CPU times. Profiling is material only if:

1. Both size-level U/P ratios are at most **0.80**
2. Each of the four individual repetition-matched large-fixture U/P ratios is at most **0.90**

All denominators must be positive finite measurements. Report all 20 cell results, candidate/reference timings separately, both primary ratios, all four individual primary ratios, and every small-fixture CPU/wall result. Wall time has no promotion rule. No confidence interval, significance claim, post-hoc subset, adjusted threshold, timing correction, or omitted cell is allowed. These are fixed practical thresholds for these invented inputs.

- `profile_overhead_material`: every gate passes and both conditions above pass
- `profile_overhead_not_material`: every gate passes but the prespecified joint materiality criterion is not met; this status does not assert that profiling overhead is globally immaterial

A material result meets the prespecified aggregate-overhead criterion on this finite synthetic set. A non-material result means only that the joint criterion was not met and closes this allocation; it does not establish global immateriality. Neither result bounds or predicts a future fully metered implementation, proves a particular optimization will help, or allocates an optimization, additional benchmark, research run, or fresh confirmation cohort.

## Failure and closure

Keep execution outcome separate from custody status and final interpretation:

- `execution_blocked`: source/runtime/import-path/runner/supervision/storage preflight fails before any evaluator starts; record zero calls and the exact failed prerequisite
- `integrity_invalid`: an observed source drift after admission, scientific/RNG/boundary/accounting mismatch, unexpected policy/integrity exception, corrupted required evidence, or failed hook/timer restoration invalidates the attempt
- `resource_incomplete`: wall, CPU, operation, memory or output protection ends an otherwise unclassified attempt
- `execution_incomplete`: an infrastructure or I/O interruption after evaluator execution starts prevents completion without establishing a scientific mismatch
- Custody `pending`, `verified`, or `blocked` is an additional field; absent readback or durable storage prevents either successful timing classification even if computation completed

Integrity failure dominates later resource/infrastructure/preservation failures. Missing output is never imputed and an incomplete pair contributes no decision ratio. Preserve the reason and phase, close the one-shot allocation, and report no material/non-material conclusion unless the complete acceptance gates pass. No automatic retry, alternative diagnostic, cap increase, resumption, or new research execution is authorized by any terminal category.

Independent static review completed before preregistration, including source-level feasibility, allocation, timing boundaries, resource plausibility and failure/custody semantics. Its clarifications are incorporated. Next: bounded implementation and a prospectively fixed synthetic fault-test plan, independent preflight reviews, then exact source/runtime/resource freezing and a separate one-shot measurement admission. Preparation used read-only source inspection only; no evaluator call or game was executed.
