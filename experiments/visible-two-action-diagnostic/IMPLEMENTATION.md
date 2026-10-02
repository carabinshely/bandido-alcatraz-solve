# Worker32 implementation handoff

Authority: [frozen preregistration](https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5930681529).
The four preparation files remain byte-for-byte unchanged. No selected-state
policy call, baseline scoring, trajectory continuation or game was executed in
the coding environment. The seed-ledger entry is prospective, references the
existing permanently spent cohort, and allocates no seeds or games.

## Implementation boundaries

`bandido_alcatraz.worker32.candidate` and `.reference` independently implement
enumeration, potential, ranking, root aggregation and final tie selection.
Only wire serialization, input validation and immutable budget constants are
shared. Reference previews use canonical `preview_move_without_draw`.
Candidate previews clone public state into an empty-draw GameState, verify
membership in the already enumerated node-local legal list, and call unchanged
`apply(validate=False)`. Neither is registered with canonical policies.

The scientific payload contains ordered root identities, first-transition
hashes, complete ordered second-action lists, every ordered leaf key and
transition hash, canonical witness sequences, every root maximum, the complete
maximal root set, chosen move, RNG state hashes, input hashes, and reconciled
logical counts. Ordered lists also have SHA256 digests. Hash encoding is sorted,
compact, ASCII JSON with one trailing newline, finite numbers only. Moves are
canonical dataclass fields. Transitions hash the full serialized public successor,
including retained hand, board cells, placement and collection histories.

The separate envelope holds pass/call identity, UTC timestamps, run identity,
wall seconds, process CPU seconds, process lifetime peak RSS in KiB (Linux), and
physical legal-list invocation counts. Pass 1 costs include its evidence assembly;
pass 2 costs are reported separately. No timing/metadata field enters the exact
scientific comparison. `omitted_draw_dead_end` denotes a carried open first-action
leaf without a legal retained second action; open depth-two leaves use `horizon`.
Neither is asserted to be actual deck exhaustion or actual no-legal-move defeat.

The input gate hashes all frozen compressed/preparation bytes before use and
bounds gzip output to 877,585 bytes before requiring exactly 877,584. It verifies
all 80 observation identities/hashes and reconstructs each from accepted card
definitions, legal public placement history and public equipment history, then
requires exact serialized equality. Canonical legal count, V4-250 score and
complete tier (including its hash) must match the separate audit references.
Those gates execute on the runner inside the same deadline as the 160 calls.

## Runner and durable evidence

The temporary workflow listens only to `pull_request: opened`, requires the exact
research branch, same repository, draft status and first run attempt, and checks
out the PR head SHA. It has no push, synchronize, workflow-dispatch or automatic
retry entry point. Forge must freeze the implementation before opening that PR.
The runtime repeats these guards and refuses cloud execution. Existing routine
CI is unchanged.

Setup/checkout/dependencies/synthetic preflight have individual bounds totaling
10 minutes. Failure skips research. The job ceiling is 60 minutes. A new process
group receives the entire provenance/baseline/two-pass compute, with one 1,800
second deadline, SIGTERM and 30-second grace, then SIGKILL of surviving group
members. Every exit and handled supervisor interruption also cleans and reaps
the group; the leader remains unreaped until signaling is finished, preventing
PGID reuse. Linux subreaper ownership handles orphaned descendants. Before
finalization, durable pre-execution session registration, boot identity and a
random process token identify residuals after supervisor death; start-time checks and pidfd signals avoid reused PIDs.
A live separate supervisor, uninspectable ownership, or surviving compute
process blocks finalization and upload. The containing step is 32 minutes.
Finalization and upload total at most 10 minutes. No selective retry is implemented; attempt directories are exclusive.

Evidence lives at `$HOME/bandido-worker32-evidence/<run>-<attempt>`, outside both
checkout and runner-temp. Started/completed/failed call records are flushed and
fsynced. Completed calls are exclusive durable JSON files; returned outputs
rejected by validation or reference comparison are preserved separately as bounded
raw evidence with their failure receipts. Prior calls, journal and process log
survive an interrupted call. An interrupted call may have no complete payload;
its started record is never counted as completed. Result creation occurs only
after all 160 calls and comparisons succeed. Finalization records file hashes
without overwriting evidence and rejects symlinks/nonregular members. Upload is
`if: always()` with a successful regular-file safety gate; unsafe members block
upload while retaining the durable directory. Failed attempts are never valid
negative mechanism evidence. Any failure receipt overrides a result file; acceptance
also requires successful terminal workflow status.

`execution_blocked` means inaccessible input before verification or setup/event
failure. `integrity_invalid` covers model/source/input/reconstruction/baseline/
transition/replay failures. Budget, timeout or memory exhaustion is
`resource_incomplete`. An externally interrupted started compute is incomplete.

## Independent preflight and acceptance

Forge should freeze the exact commit/tree and source inventory, inspect workflow
and installed-package provenance, and independently verify the evidence schema
and protocol before opening the draft PR. Runtime provenance includes the full
tracked Git blob/SHA256/byte inventory, accepted-model immutability checks, and
byte equality of every installed Python source with the exact checked-out head.
Synthetic real-Git fixtures test model edits, installed corruption and injected
modules; they do not weaken production gates.

After execution, independently authenticate run/event/head identity, preserve
and hash the uploaded artifact, require the complete call order and 160 completed
journal records, compare each entire scientific payload, reconcile all root,
child, leaf and preview counts, and verify strict cross-type departure against
all V4-tier roots. Runtime validators and complete raw scientific outputs support
this review; they are not a substitute for Forge's independent acceptance.
Only the two preregistered mechanism classifications are successful outcomes.
Neither establishes improved wins, isolated horizon causality, confirmation or
PROGRAM_SUCCESS. No follow-up game run is authorized here.

Synthetic verification (full checkout, CPython 3.11):

```
python -m pytest -q
python -m pytest -q -o pythonpath= tests/test_worker32.py tests/test_worker32_preflight.py
```

An installed-package check should override the repository pytest `pythonpath`
setting using `-o pythonpath=`. Do not invoke the runner harness with selected
observations in a development environment.

## Bounded preflight repair batch

[Independent review record](https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5943715725).
Search mathematics, the four corpus preparation files, canonical sources/data,
and execution ceilings are unchanged. The runtime/evidence repairs are:

* All supervisor exits clean the compute group, including nonzero leader exits,
  SIGTERM/SIGINT, timeout, KeyboardInterrupt and exceptions. A child bootstrap
  refuses execution after parent death and sets Linux PDEATHSIG. Durable token
  ownership supports a fail-closed residual check after unhandleable death.
* Git/provenance subprocess timeouts and genuine resource errnos are incomplete,
  while arbitrary I/O corruption remains integrity-invalid. Initial runtime/head
  provenance is durable before the detailed Git gate begins.
* Rejected returns have exclusive `rejected-call-NNN.raw` and `.json` receipts,
  distinct from accepted call files. Raw evidence is a JSON prefix bounded to
  64 MiB; its receipt identifies completeness, byte count/hash, validation error
  and any serialization/size failure. A malformed or oversized return cannot
  create an accepted-call file or a completed-call event. The evidence byte
  bound does not alter search enumeration or the successor-preview budget.
* The envelope is bound to the exact frozen-order identity and run/attempt.
  Identity integers exclude booleans/fractions; timestamps must be aware UTC
  with finish at or after start. Timing/cost metadata remains outside scientific
  equality.
* The baseline gate retains its already-enumerated canonical root count/digest.
  Each return must match those and the frozen observation hash before any
  classification. This adds no policy call, search or legal enumeration.

The focused regressions use real synthetic descendant processes, interruption
and orphan cleanup, invented observations and deliberately corrupted returns.
No selected-state computation is part of these tests. Exact-head independent
rereview remains required before any draft PR or diagnostic execution.
