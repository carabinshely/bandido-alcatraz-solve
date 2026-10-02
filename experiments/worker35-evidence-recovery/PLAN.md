# Worker35 evidence-only recovery draft

This is the local recovery implementation/review record. The parent published
initial recovery commit `25cc3159a7bd75a3681a1c7d36afa05d5007f791`; run
`37069115788` failed before any job was created. That failed attempt is preserved.
It performed no metadata inspection or research execution. This worker did not
publish or launch any workflow. Tests use invented local fixtures.

The first workflow had two configuration defects: runner.temp was used in job
defaults where runner is unavailable, and the run block had 23,567 characters,
above GitHub's 21,000-character limit. The narrow repair moves working-directory
to the Inspect step and compacts only generated Python presentation, proving
exact AST equality including docstrings and constants. Original standalone
inspector source and its scientific/no-mutation limits are unchanged. GitHub's
exact rejection annotation is unavailable; these are confirmed invalid settings
consistent with the pre-job failure, not a claimed fetched error message.

Primary references: [context availability](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability)
and [run block limit](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idstepsrun).

## Confirmed facts

- Original run: 36990202101, attempt 1, job 110784375570, frozen source
  `7ac2f62c9c5c9dcac9ec9b8770382960f985acc2`
- Original workflow assigns output to
  `GITHUB_WORKSPACE.parent/bandido-quota-closure-development/36990202101/1`
- GitHub reports run/job failure, cohort step still in progress, reconciliation,
  packaging and upload pending; current metadata has no scientific completion
  evidence. Parent separately established zero artifacts and unavailable logs.
- The 18-hour cohort and 23-hour workflow caps do not explain an approximately
  11h42m infrastructure termination by themselves. Root cause is still unknown.
- Original initialize/admission are exclusive; original run prohibits resume.
- Original finalize replaces receipt.json. Original package_attempt can replace
  it on packaging failure. Neither may be used for this preservation operation.
- Original independent verifier requires successful original workflow/job and
  finalization metadata. A successful recovery workflow cannot substitute for
  the failed original workflow or upgrade its scientific classification.

## First operation: metadata only

Proposed repository workflow path: `.github/workflows/worker35-evidence-recovery.yml`

Proposed branch: `research/worker35-evidence-recovery-36990202101`, branched from
current main. Trigger is a push to that exact branch, by the authorized owner,
first recovery attempt only. No PR is necessary to run this diagnostic. Parent
verified current normal CI runs only main pushes and PRs, so this branch push
does not incidentally invoke tests or any game machinery.

The generated workflow contains all reviewed Python inline. It has no checkout,
pip/install, Git operation, project-code import, original harness invocation,
model/deck reads, policy call, game initialization or outcome calculation. It
uses existing python3 with `-I -B`. Its shell starts in runner.temp, outside the
original checkout. The job uses existing runner labels and validates the actual
registered runner_id against the original job before accessing its evidence.

New recovery bytes are written exclusively beneath a fresh sibling directory:
`GITHUB_WORKSPACE.parent/bandido-worker35-evidence-recovery/<new-run-id>/1`.
Existing paths, original admission guards, output and receipts are never removed,
reused, renamed, repaired or overwritten. Every recovery file is created with
exclusive creation. Symlinked configured paths and receipt ancestors are rejected.

The job has a 10-minute infrastructure limit, with a dedicated 300-second
inspection deadline that leaves time for explicit failure receipts and upload,
and reads only:

1. Authenticated original run/job and current recovery-job metadata
2. UTC/boot identity and PID namespace observations
3. Two bounded lstat-only inventories of original output (no raw file contents)
4. Original receipt, at most 8 MiB, and original admission, at most 1 MiB; bytes
   are copied verbatim and hashed, including malformed JSON
5. A same-owner-UID process scan: producer-entrypoint match, original checkout/
   output cwd, output descriptors and mappings; it records only PID/reason labels

No environment content or unrelated process commands appear in the report.
Uninspectable relevant state is reported as unknown. Live process matches are
potential-writer evidence. Neither no matches nor stable lstat metadata is
represented as proof of quiescence. The script always reports quiescence false,
classification null, no interpretation, and no packaging. It contains no packaging
mode or hidden flag that could expand this operation.

Recovery receipts are uploaded on success or diagnostic failure, subject to an
explicit <30 MiB metadata guard. A failure before the fresh directory exists or
an infrastructure kill may prevent upload; do not claim recovery without readback.
Copies and any partial recovery files remain on the runner. No automatic retries.

## Second operation, only after diagnostic review

If runner boot/process/receipt facts establish that the original producer and
its descendants cannot continue, authorize a separately reviewed preservation
step. Any live writer, inaccessible relevant process state, ambiguous surviving
producer, or unstable content leaves preservation blocked. Do not kill processes,
stop services, change permissions, guess cgroups, or invent a quiescence claim.
A host reboot after the original job's final failure is strong evidence that
original processes are gone; corroborate identity and current scoped processes.

No giant raw copy is necessary. Frozen `scripts/worker35_resources.py` is stdlib
only and `package_evidence(root, fresh_destination, limits)` reads the source tree
and writes only its exclusive destination. Authenticate its bytes against SHA256
`c30ebcf620345aa809accf6c349ac816fb9837a0c3a90f36e984666cb61c812c` before importing it.
Do not call the original harness, package_attempt, finalize, admit, initialize,
or run, and do not falsify GITHUB_RUN_ID, attempt or event metadata.

Before packaging, authenticate the raw original freeze SHA256 against the recorded
execution-go, require expected original source/run/admission identities, reject
symlinks/special files, check disk capacity, and retain a complete pre-read
size/hash inventory of all original bytes. Keep recovery records outside original
output. Invoke only the pinned helper with original output as root and a brand-new
recovery transport destination. Preserve the frozen 16 GiB expanded evidence,
4 GiB archive, 30 MiB shards, <=256 parts and 7,200-second packaging limit; no
post-result cap extension. A recovery-specific smaller ceiling may stop transport
without altering original scientific/resource classifications.

Preserve all source files, malformed/partial journals, recovery receipts and
already-emitted transport pieces. Never silently truncate, repair or delete.
Compare source inventory, inode/mtime/ctime and SHA256 again after packaging;
changed bytes quarantine the recovery and prohibit acceptance. Verify every part,
reassembled archive and archived member against inventory on readback. Upload each
30 MiB part separately, preserving the <32 MiB connector wrapper requirement.
Keep original execution identity distinct from recovery transport provenance.

Persist recovered raw evidence and explicit failure/unknown record to the existing
canonical destination under authorized custody rules; verify fresh byte/hash
readback. Do not patch original receipt to manufacture complete finalization.

## Classification

Current defensible statement: execution/evidence infrastructure failed; original
scientific outcome and execution extent are unknown. The cohort began, so do not
call this pre-execution blocked. The recorded scientific/resource caps are not
known to have tripped. Partial output may establish more facts after recovery.

- Retained integrity errors dominate later infrastructure failures
- A retained resource failure is resource-incomplete, never a valid negative
- A stale running receipt or partial journal is interrupted/incomplete evidence
- Even 1,200 retained rows do not satisfy missing source/finalization/workflow gates
- No win-rate claim, negative screen, advancement decision, rerun or policy change
  follows from this recovery

## Frozen source references

- [Workflow](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/.github/workflows/quota-reserve-closure-development.yml)
- [Harness, including receipt replacement and packaging paths](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/scripts/run_quota_reserve_closure_development.py#L1283-L1553)
- [Non-mutating source transport helper](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/scripts/worker35_resources.py#L314-L353)
- [Independent metadata gates](https://github.com/carabinshely/bandido-alcatraz-solve/blob/7ac2f62c9c5c9dcac9ec9b8770382960f985acc2/scripts/verify_worker35_development.py#L624-L715)
- [Evidence-only recovery authorization](https://github.com/carabinshely/bandido-alcatraz-solve/issues/2#issuecomment-5961700025)

## Local validation

Twenty invented-only/syntax unittest cases pass. They cover exact original run/runner
identity, bounds, symlinks, exclusive writes, source-byte preservation, lstat-only
inventory, live producer/fd/mapping detection, process uncertainty, privacy and no
quiescence overclaim, source/output symlink-swap races, deadline propagation and
preservation when boot/namespace evidence is unavailable. Inline Python AST parses
and YAML parses. Separate regressions enforce the supported context placement,
21,000-character run limit and complete embedded Python AST equivalence. These tests are
not a runner execution or evidence that the original output exists.

After edits, regenerate YAML with `python3 -I -B build_workflow.py`, rerun tests,
and review the exact final workflow bytes before publishing. No claim of two
independent reviews is made by this draft.
