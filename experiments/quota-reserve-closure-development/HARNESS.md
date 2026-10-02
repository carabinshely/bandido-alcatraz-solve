# Worker35 bounded execution and evidence wire

Implementation only. There is no execution-ready resource configuration in this
change. An exact source/runtime/resource freeze, clean independent exact-head
reviews, green exact-head CI, and a separate root execution-go are prerequisites
for real decisions or any of the 1,200 allocated game executions.

## Reviewed lineage and ownership

The runner is a direct adaptation of `run_equipment_opportunity_development.py`
from Worker31 commit `7a2b681f2d78c9e4cef466eb5250c4bd6c6c52ed` (Git blob
`2615059581d5eb24ac67c9eb787cdc11a98940c3`). It preserves exclusive attempt
initialization, fsynced append-only journals, retained raw results, finalization
reconciliation, complete ordered population checks, and fail-closed source gates.
No canonical source/model/RNG/move order was changed. The existing pure
`worker31_geometry.py` rechecks final physical geometry and victory. Its source
is separately pinned in the freeze; it does not constitute another game engine.

The frozen canonical comparator is the original 26 `src/` and `data/` blobs at
`c50a7ab8e73eaf3c497c5d1c9fef5cbe53261853`, not all subsequently added research
modules. Execution must descend from accepted main
`87ddc894668ec60e7a8419e65308cadb0ced6ed9`, accepted tree
`3e0c450ed82ecd47fdd1e239da47d97567d584a6`.

Candidate and independently authored reference retain their own `OperationLimits`
classes. They share only frozen canonical engine/scoring and the agreed wire
serialization. The wrapper passes each the detached public observation and its
own identical initial RNG state. The reference is validation, never another game.

## Lifecycle and first admission

`initialize`, `run`, and `finalize` remain separate invocations. `admit` and
`package` perform only administration and evidence transport.

The temporary workflow's `opened`/`synchronize` job runs invented fixtures on
CPython 3.11.16. It does not require or create a research admission. Its benchmark
requires explicit candidate/reference source hashes and uses distinct
benchmark-only wall/memory protections. These are not research ceilings.

Research requires `pull_request: edited` with an absent-to-present transition of
exact marker lines in the draft PR body, authorized repository/actor/author,
branch `research/worker35-quota-reserve-closure`, first run attempt, named runner
`bandido-alcatraz-ci`, and this one-line JSON payload:

```
WORKER35_EXECUTION_GO_JSON
{"head":"<exact commit>","tree":"<exact tree>","freeze_sha256":"<raw freeze bytes SHA256>","execution_go_url":"<separate Issue2 go comment>"}
END_WORKER35_EXECUTION_GO_JSON
```

The event JSON is parsed directly; PR text is never interpolated into a shell.
The URL is provenance. The root verifies the actual external go/reviews/CI before
making the edit; the runner does not fetch or reinterpret the comment.

After event/freeze validation, an atomic per-head admission directory under the
repository's existing checkout-sibling experiment area admits only one run ID and
attempt. Existing guards/outputs are never removed, reused, or resumed. Removing
and readding the body marker cannot produce another attempt at the same head.
The first receipt precedes source checks, dependency installation, and tests.
A failed attempt requires explicit prospective handling, never a hidden retry.

## Mandatory freeze

Path: `experiments/quota-reserve-closure-development/execution-freeze.json`.
No default file or permissive cap is provided. Exact top-level keys:

- `schema`: `worker35-execution-freeze-v1`
- `preregistration_url`, `baseline_commit`
- `baseline_source_blobs`: exact canonical 26 path-to-Git-blob map
- `execution_source_sha256`: every tracked `src/`, `data/`, `scripts/`, `tests/`,
  `.github/` input plus `pyproject.toml`, protocol, and audit contract
- `runtime`: exact `implementation`, `version`, `executable_sha256`
- `resources`: all caps below
- `reviews`: `candidate`, `reference`, `harness`, `independent_a`, `independent_b`,
  each exactly `required-clean-exact-head-before-go`
- `synthetic_preflight_sha256`: previously retained invented-resource evidence

The freeze itself is excluded from its source map to avoid self-reference. Root's
external go binds its raw SHA256 plus final head/tree. Review role declarations
are requirements, not proof of approval; actual final-head approval and CI URLs
belong in the external go. The benchmark scientific source pins remain stable
while final configuration-only changes receive fresh CI and review.

Every resource is a required positive integer, with no implicit `None`/unlimited:

- `per_call.control`, `.candidate`, `.reference`: `legal_enumerations`, `previews`,
  `exit_geometry_checks`, `roots`, `wall_seconds`, `cpu_seconds`
- `total_operations`: `legal_enumerations`, `previews`, `exit_geometry_checks`
- `cohort_wall_seconds`, `verification_wall_seconds`, `address_space_bytes`
- `evidence_bytes`, `trace_bytes`, `line_bytes`, `receipt_bytes`
- `shard_bytes`, `archive_bytes`

Physical operations are observed using scoped Python profile hooks, including
preview membership re-enumeration, standalone EXIT enumeration, independent
checking, and engine actions/refresh. Prior Python hooks are forwarded/restored;
unsupported noncallable native hooks fail before replacement. Actual control
roots/scores are observed from unchanged V4's return frame, not recomputed.
Linux main-thread `ITIMER_REAL` and `ITIMER_PROF` enforce wall/CPU ceilings;
`RLIMIT_AS` enforces the exact process address-space ceiling. Whole-run physical
limits include operations outside the decision wrapper. Game deltas sum exactly
to the receipt's whole-run counters. No physical-operation bound is misrepresented
as a semantic search horizon.

Ceilings are safety protections, not predictions all theoretical states fit.
The reviewed static call graph provides prospective operation bounds, while the
pinned-runtime invented benchmark informs wall/memory/output choices. A
resource-incomplete attempt cannot become a complete negative screen. No
outcome-dependent cap increase, omitted seed, scientific fallback, or truncation
is supported.

## Evidence files and scientific deduplication

- `receipt.json`: Worker31-style lifecycle identity, freeze snapshot/hash,
  admission/go, source snapshots, ordered attempted games, completed count,
  status/errors, resource totals, elapsed times, and successful summary
- `completed.jsonl`: exactly `{pass,record}` in control400, candidate400,
  replay400 ascending seed order; normalized record remains Worker31-compatible
- `raw-results/pass-{1,2,3}/{seed}.json`: raw returned result, one public final
  capture, trace counts, `final_public_observation`, and `conservation`
- `decision-traces/pass-{p}/{seed}.jsonl`: alternating `decision_started`
  (ordinal, complete public observation, initial RNG hash) and
  `decision_completed` (ordinal, audit), then `game_returned` and `game_completed`
- `call-results/pass-{p}/{seed}.jsonl`: immediate durable policy/checker returns
- `resource-metrics.jsonl`: decision rows then one game row per completed game
- `recovery-receipt-*.json`: additional failure records when original receipt
  cannot safely be read/reconciled; original bytes remain untouched

A candidate return row contains `{ordinal,scope:"candidate",result:{chosen,
scientific,cost}}`, with the complete AUDIT-CONTRACT scientific object stored
exactly once before the reference runs. The reference computes its full object
independently. On successful exact canonical-byte equality, its return row stores
`{ordinal,scope:"reference",result:{chosen,scientific_sha256,cost}}`. On disagreement,
the full differing reference object is additionally persisted before failure.

Completed candidate trace audits contain `scientific_sha256`,
`reference_scientific_sha256`, `candidate_cost`, `reference_cost`, and `boundary`.
Every reference must resolve to the exact full candidate bytes and ordered call
journal; successful counts or two ungrounded digest strings are insufficient.
Candidate/replay decision traces and call journals must match byte for byte.
Wall/CPU/RSS observations are separate and are not compared byte for byte.

Control audits preserve Worker31's public-observation/chosen/RNG fields and add
actual `roots`, `final` root indices, `cost`, and `boundary`. Control call rows
store the returned chosen/roots/final/cost. The normalized complete control array
must equal SHA256 `a4d2d06e5592caa35c03d00337d0254c07f767d5cb8ee0777cbb51f543803021`
and reproduce 45 wins before candidate execution begins. Independently verified
historical control traces are compared by the offline verifier at all shared
fields.

Boundary keys: `public_before`, `public_after`, `engine_before`, `engine_after`,
`choice_calls`, `choice_tier`, `reference_choice_calls`, `reference_choice_tier`.
The trusted harness inspects the canonical runner's real state only to check
physical conservation/immutability. Policies never receive that state, draw order,
or hidden zones. Real-state hashes preserve ordered private state internally;
final conservation is separate evidence, with sorted IDs under `placed`,
`collected`, `hand`, `draw`, `set_aside`, `inventory_count=69`, and SHA256 of the
sorted complete inventory. These final proof fields are never decision inputs.

Decision resource row keys: `kind`, `pass`, `seed`, `ordinal`, `scope`,
`wall_seconds`, `cpu_seconds`, `peak_rss_kib`, `cost`, `status` (`returned` or
`failed`). Game rows omit ordinal/scope/cost and add `operations`; successful game
status is `complete`. Both elapsed receipt fields include administration overhead
inside their supervised phase. Failed metrics do not override an already known
integrity failure.

## Transport and terminal acceptance

Evidence writes are fsynced and byte-budgeted before writing, with reserved
receipt space. Exceeding a bound retains the last complete prefix and fails
explicitly. Finalization never accepts incomplete coverage or a failed test,
workflow, source, reference, resource, or replay gate.

Packaging uses sorted, fixed-timestamp/perms ZIP entries with DEFLATE level6.
Compressed bytes stream directly into numbered `evidence.part-00001` files;
there is no giant staging archive. Each part is at most frozen `shard_bytes`
(ceiling30MiB), and the frozen compressed archive cap cannot exceed256parts.
A separate upload-only matrix job sends each part as its own artifact, so the
outer GitHub ZIP remains below the32MiB download ceiling. Metadata/receipt are a
small separate artifact. `artifact-manifest.json` records every original file's
byte/hash identity, complete reassembled ZIP hash/size, and every ordered part's
hash/size. The format label is `concatenated-zip-deflate6`.

Part limits and compressed archive overflow are resource failures. Original raw
files and every emitted partial shard remain. No already written part is
silently deleted or truncated. Failed compute/finalization still reaches
packaging/upload through `always()`; a successful result requires all artifact
jobs and external byte/hash readback, not merely a producer summary.

Terminal categories are `execution_blocked` (pre-compute/infrastructure),
`integrity_invalid`, `resource_incomplete`, and complete development classifications
`quota_reserve_closure_development_no_advancement` or
`quota_reserve_closure_development_advanced`. Integrity failures dominate later
resource/infrastructure errors. Only complete evidence permits the net+8 spent
screen. Full paired outcomes, equipment-ready totals, terminal components, reserve
filter/tier changes, closure selections, and correctly attributed original
all-COLLECT crossovers are descriptive outputs; no new mechanism threshold exists.
