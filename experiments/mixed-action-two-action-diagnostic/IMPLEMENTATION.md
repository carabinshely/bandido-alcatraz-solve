# Worker33 completed mechanism checkpoint

Authority: [frozen Worker33 protocol and exact input freeze](https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5944922245).
[Terminal evidence record](https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5945498880).

## Terminal result

Run [36961069413, attempt 1](https://github.com/carabinshely/bandido-alcatraz-solve/actions/runs/36961069413)
completed successfully at execution head
`99164d0212d50fce37f8a2a9656198ca08ccde32`, tree
`8351ff128c91c34276382e427dadcf10ba844591`, frozen in
[the exact-head execution record](https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5945157800).
All 160 fresh calls completed in candidate-then-reference order; all 80 entire
scientific payload pairs matched. There were no qualifying strict departures.
The result is `mixed_action_two_action_diagnostic_mechanism_not_exercised`.

The UTC whole-compute journal span was 1,269.038007 seconds. Per-call wall-time
sums were 163.7711524280021 seconds for candidate and 1,063.5291602760553 seconds
for reference. These are separate clock observations, not an independent
measurement of the supervisor's monotonic deadline. See
`mechanism-not-exercised-2026-10-02.manifest.json` for execution, integrity, cost,
persistence and interpretation details.

The original Actions ZIP is 19,184,749 bytes, SHA256
`18a58ec0505d81eaf4b0cfb4798b7e38b0d9555d22ad77c5d4681b5fce89492a`.
Its [persisted raw copy](https://drive.google.com/file/d/1WJE6WVR8bW0BSTTBoqx8GWkLWm1d7MAu/view)
was freshly downloaded and byte-compared by the coordinating verifier. The
[complete reproduction proof](https://drive.google.com/file/d/1-a1I6-TA9m9vudV2Mob23txx57TPBhl-/view)
is 3,030,368 bytes, SHA256
`82fe20b455263ea914b235e6e2a9e223826765ef9ab0146f809625cf8f5e0836`;
its fresh byte-for-byte readback is also verified. It contains exact execution
source, frozen inputs, authenticated metadata, verifier and 126 passing tests,
reproduction instructions and the complete verified result. Final checkpoint reviews, CI and repository acceptance are recorded
separately in [PR36](https://github.com/carabinshely/bandido-alcatraz-solve/pull/36)
and Issue2. This execution record does not preclaim their outcome.

The temporary execution workflow has been removed. Its byte-identical inert
archive is `execution-workflow.yml`, SHA256
`3ec8d21ffc6fa8311c559d52231456839c9519eb51ad2b593d166d66a9ad17c0`.
The workflow regression retains its frozen guard assertions and now also checks
that the active workflow is absent. The final cleanup head is distinct from the
execution head. Scientific source, core pins, canonical model/data and all
inherited Worker32 modules/tests remain unchanged.

This result is limited to the fixed stress-enriched, trajectory-conditioned,
spent-observation population. It establishes no population departure frequency,
full-game runtime, isolated horizon-two causality, win-rate improvement, adoption,
confirmation or PROGRAM_SUCCESS. Worker32 remains `resource_incomplete`. No
fresh seeds or new research games were allocated or run. No follow-up execution is authorized;
a new bounded research decision requires separate preregistration.

## Historical implementation handoff

The remaining sections describe the implementation frozen and executed at the
head above. The original coding task used synthetic fixtures and byte/metadata
checks only; selected observations were subsequently evaluated solely on the
authorized runner. Immutable preparation files retain their historical status
text and do not substitute for the terminal evidence.

## Minimal isolated changes

The repository baseline is accepted main
`1b5881802fc995d301ed3eca6a0e75c1d2dcb90c`, tree
`ed213a0356fe278acc14a6b223fde71c7264a1c4`. It is distinct from the canonical
source/data comparator `c50a7ab8e73eaf3c497c5d1c9fef5cbe53261853`, retained as
runtime `BASE`. Runtime `REPOSITORY_BASE` records that accepted repository baseline in
provenance as `repository_base`; it does not assert the immediate Git parent of
a later implementation commit. The original implementation preserved existing
source, data and tests and appended a prospective Worker33 ledger allocation.
This checkpoint updates only that step33 allocation with the terminal result.

`src/bandido_alcatraz/worker33/inputs.py` and `runtime.py` are versioned copies
of the accepted Worker32 drivers. They change only input/protocol identities,
the mixed-action gate, exact runtime restriction, prospective time limits and
result labels. There is no game-policy registration, fallback wrapper, pruning,
new search algorithm, shared-global monkeypatch or extra scoring pass.

Unchanged imports and byte dependencies:

- `src/bandido_alcatraz/worker32/candidate.py`: SHA256
  `d806a40383566d82f8af4259179940feff0339ac786bcf6207e7f7e0503e1b01`
- `src/bandido_alcatraz/worker32/reference.py`: SHA256
  `2a396aed1e303332d72b254f30dd58b57133364eafa29e50c5a51807f892e20b`
- `src/bandido_alcatraz/worker32/evidence.py`: SHA256
  `292baa7966b8b96dc79ebb1b5b17ae86182d61fc11f37dbd86adb2d4cdc78a20`
- `src/bandido_alcatraz/worker32/containment.py`: unchanged process-group and
  residual cleanup. Its internal imports of `worker32.runtime.durable` for
  exclusive serialization remain unchanged. Its process schemas/token names,
  and the scientific schema `worker32-scientific-v1`, are inherited wire formats.
  Worker33 is bound separately by new protocol, branch, head/run and ledger.

Source/installed-package provenance, validators, rejection preservation,
failure taxonomy and strict-departure mathematics are copied without semantic
change. The entire checked-out inventory remains bound to the exact PR head;
every installed Python source must equal its tracked source, with no extra
installed modules. All 26 canonical source/data blobs retain the original gate.

## Fixed population and baseline gate

The four preparation files are copied byte-for-byte from the frozen preparation:

- `selected-corpus.jsonl.gz`: 14,286 bytes, SHA256
  `ab4133bd880fed194f7f22fcc3ad00371013f18d0c51f51ef8ffe36705ad4300`
- `audit-reference.jsonl`: 30,132 bytes, SHA256
  `4ca2c08160b8e641f26d3dfbb2759727c522fe1d0235837cdaab35e3e967502e`
- `selection-manifest.json`: 73,029 bytes, SHA256
  `3ad07d6237b3f7f24c60448fc346a013261d05b8e36fd998ffd440faceee9a78`
- `select_public_snapshots.py`: 25,468 bytes, SHA256
  `30699b72adb5c731523c84bc298c04fca41de90df00d074e628a0fc5e55e82ca`

The bounded uncompressed corpus is exactly 326,455 bytes, SHA256
`2366287bd1e05d6b47ed47344996120f76bc02b297a81b3238099dc329066df5`.
Immutable preparation status text describes its earlier preparation stage;
current authority is the separately frozen protocol linked above.

There are 80 observations from 71 permanently spent source seeds, ordered hash64
then stress16. The old 80 Worker32 identities are excluded. No fresh seeds or
games are allocated. The experimental unit is an observation, not a call.

On the authorized runner, each observation is reconstructed and validated using
the inherited exact public-history gate. The one already-enumerated baseline
legal list must have unchanged B/C, both COLLECT and PLACE, and exact positive
counts equal to manifest `collect_count_metadata` and `place_count_metadata`.
EXIT is PLACE. The same list supplies unchanged V4-250 score, complete ordered
primary tier/digest and canonical root count/digest. A mismatch is
`integrity_invalid`, never replacement or omission. No second baseline pass is
added.

All 80 candidate calls precede all 80 reference calls in the fixed order. Every
call gets a fresh unchanged instance and `Random(0)`. The preview ceiling remains
32,768; complete payload equality, binding, RNG and envelope gates remain intact.
No draw, refresh, game continuation, old completion or selective retry is used.

## Frozen execution workflow and evidence

The executed `.github/workflows/worker33-mixed-action.yml` was adapted from the
Worker32 execution workflow at `d21421e883cbc08d3a9e99ea8d856894c6ac41a8`,
not the accepted checkpoint where that workflow was removed. It accepted only
the first `pull_request: opened` event for a same-repository draft on
`research/worker33-mixed-action-diagnostic`, and checked out the exact head SHA.
It had no push, synchronize or dispatch trigger, and no automatic rerun. This
checkpoint retains only its inert archive outside `.github/workflows`.

Only `bandido-alcatraz-ci`, CPython 3.11.16 and `PYTHONHASHSEED=0` are accepted.
A missing exact interpreter raises `ExecutionBlocked`; wrong hash-seed or
integrity checks retain `integrity_invalid`. Setup failures block research.
The isolated package runs focused synthetic preflight against installed sources.

The unchanged containment function receives explicit `timeout=5400, grace=30`.
Its inherited 1,800-second default is never used by this supervisor. The deadline
contains provenance, reconstruction, baseline gates and all 160 calls. The
compute step is 92 minutes; setup totals 10 minutes (1+1+2+2+4), finalization and
upload total 10 minutes (2+8), within the 120-minute job ceiling. No extension,
executor switch, population reduction or completion reuse is allowed.

Evidence uses exclusive `$HOME/bandido-worker33-evidence/<run>-<attempt>`
directories, separate from Worker32, checkout and runner-temp. Durable started,
completed, failed and rejected records, fail-closed residual cleanup, safe
regular-file inventory and always-upload gating are inherited. Existing evidence
cannot be overwritten. A failure receipt overrides a result; terminal workflow
success and independent evidence persistence/hash/readback verification remain
required for acceptance.

Only complete valid evidence can produce
`mixed_action_two_action_diagnostic_mechanism_exercised` or
`mixed_action_two_action_diagnostic_mechanism_not_exercised`. The unchanged rule
requires opposite entire candidate and V4 action-type tiers plus a strict best
key improvement over every V4-tier root. These labels concern mechanism/cost on
this fixed stress-enriched spent population. They do not establish population
frequency, full-game cost, isolated horizon-two causality, win-rate improvement,
adoption, confirmation or PROGRAM_SUCCESS.

## Validation history and remaining acceptance gates

Before execution, local CPython 3.12.14 passed 667 tests and 149 subtests; the
isolated wheel-installed focused suite passed 141 tests, including 40 new adapter
tests. All 31 installed Python sources matched the export byte-for-byte. New
Python files also parsed with Python 3.11 grammar; that syntax check was not
represented as execution on CPython 3.11.16.

The authorized runner subsequently used CPython 3.11.16 and passed its installed
synthetic preflight. Routine CI run
[36961069310](https://github.com/carabinshely/bandido-alcatraz-solve/actions/runs/36961069310)
passed 667 tests and 149 subtests on synthetic PR merge
`448831ee3eb1b85a9c743ca29e3d1f60b79a47a2`, whose tree matches the execution tree.
Those results concern the executed implementation, not this later cleanup head.

Cleanup validation remains synthetic and metadata-only. No selected observation
is reconstructed, enumerated, scored, searched or continued locally. With an
installed package, override pytest's source path using `-o pythonpath=`. Final
checkpoint review, CI and PR acceptance are recorded separately in PR36/Issue2;
both proof and raw persistence/readback fields are finalized in the manifest.
The retained runtime does not authorize a rerun.
