# Worker35 sealed transport recovery draft

## Publication contract

Publish only the reviewed `worker35-sealed-recovery.yml` as `.github/workflows/worker35-sealed-recovery.yml` on `research/worker35-sealed-recovery-36990202101`. The workflow is self-contained; the Python source, renderer and tests are review artifacts, not runtime downloads. No publication, GitHub run, original research execution, or local-computer action was performed by this implementation task.

The workflow permits only the repository owner `carabinshely`, push events on that exact branch, recovery attempt 1, and the original registered runner ID 2 / name `bandido-alcatraz-ci`. The original run must remain 36990202101 attempt 1 at head `7ac2f62c9c5c9dcac9ec9b8770382960f985acc2`, original job 110784375570, failed overall with cohort cancelled, finalization failed, packaging successful, and artifact upload failed. Every upload matrix job rechecks its authenticated runner and source identity before and after upload.

## Preservation boundaries

- Reads existing `1-transport/artifact-manifest.json` and named parts only, plus the original bounded receipt/admission and authenticated Actions metadata
- Derives canonical absolute sibling paths from GITHUB_WORKSPACE, with no literal parent traversal, symlink following, project imports, checkout, dependencies, subprocess execution, archive extraction or recompression
- Pins original receipt SHA256 `027b6b35d75983ecf1760395418ff00d2df2a7fab63afee617bc73e4d8e3b3af` and admission SHA256 `c60ff9cd1813729fdad2c99ef337fd4727fc24bd5855114027cf64fc34cd3c76` from metadata artifact 11266298223
- Requires original manifest schema, exact 30 MiB shard convention, canonical contiguous part names, bounded file metadata, ≤4 GiB archive and ≤137 shards
- Creates a fresh exclusive sibling snapshot at `bandido-worker35-sealed-recovery/<new-run>/1`; never overwrites prior recovery state or source evidence
- Verifies each source part hash/size while copying; then rereads every source part, then every snapshot part, including concatenated SHA256; checks stable source file/directory identity, original receipt/admission and manifest
- Uploads metadata separately and each copied part as its own uncompressed artifact, using pinned actions/upload-artifact commit `ea165f8d65b6e75b540449e92b4886f43607fa02`; each part is hash/stamp checked again before and after upload; metadata uses explicit filenames and separately pinned hash/stat records with pre/post checks
- Preserves existing source and partial snapshot bytes on failure; emits a bounded blocked report for failures occurring after metadata-directory creation, if a safe metadata report remains writable. Before that point, the job log is the blocker record and no source bytes have been copied
- Snapshot and upload jobs are bounded to 15 and 5 minutes respectively; snapshot code has a 600-second alarm; part/metadata checks have 90-second alarms; GitHub metadata response bodies and pagination are bounded

## What success means

Workflow success records a byte-preserving local snapshot and successful upload attempts. Local pre/post hash and identity observations do not establish the bytes actually accepted by the remote artifact service, including any unobserved ancestor-swap window. The report explicitly leaves remote_artifact_bytes_verified false. It does not establish scientific validity, completion of the experiment, quiescence of the original raw tree, or consistency between archived members and manifest per-member hashes.

The recovered raw-tree lstat metadata records writes after original packaging, before orphan Python cleanup. The original packager hashed each member before reopening and compressing it, without a post-read mutation gate. Therefore the existing sealed archive may omit later raw bytes, and its member hashes remain unaudited. This caveat is carried into every successful recovery report. The original receipt remains `execution_blocked`, classification null. No partial outcomes are interpreted.

The original receipt is copied byte-for-byte and includes full original source inventories and runtime provenance. The recovery report also repeats its initialization, pre-run, and finalization runtime identity fields for convenient review, without claiming these were re-executed or newly established.

## Mandatory parent acceptance gate

Regardless of workflow conclusion, download the provider artifact ZIPs and verify their reported digest/size where available, then validate their inner bytes. Pin `recovery-report.json` to the `report_sha256` printed in the successful snapshot job log. Pin `artifact-manifest.json` to that report's manifest hash; pin original receipt/admission to their known hashes. Require exactly one bounded inner part with its expected filename in each part artifact; hash every extracted part against the manifest and hash their ordered concatenation against the archive hash. Do not treat a green workflow, missing postcheck, cancellation, provider-only hash, or partial artifact list as byte acceptance. Keep the raw-tail preservation gap distinct from sealed-transport acceptance.

Failures before snapshot creation preserve no separate metadata artifact: the API/identity blocker remains in Actions logs, and no source or copied bytes were changed. Failures after metadata creation attempt to preserve a bounded blocked report without deleting any partial files. Infrastructure cancellation may preempt a postcheck; this is a failure/inconclusive state and must not be reported as accepted preservation.

## Evidence read for implementation

- Frozen original harness, resources helper and workflow at commit `7ac2f62c9c5c9dcac9ec9b8770382960f985acc2`, fetched through GitHub into `source/` for read-only reference; the three original frozen source files were normalized to exact bytes and SHA256-checked against the preserved original receipt
- Existing metadata-recovery workflow at commit `0186ea90534d4eb8f62d84816ec27eb04cc59e26`
- Previously downloaded metadata artifact 11266298223, SHA256 `ddfb0ba99622d8ea4c30c7c7e73b02059aa43b76207e777ffad18fc590ddb6a7`; only receipt, admission, inspection and lstat metadata were inspected

## Verification

Run `python3 -B -m unittest -v` in this draft directory. All 31 tests passed: invented transport/unit tests, platform-semantic checks, and one integration check of the already preserved bounded metadata artifact (no raw outcome computation). Tests cover byte-exact copying, collision refusal, symlink/hardlink/FIFO rejection, unexpected entries, source and snapshot mutation, manifest bounds, malformed JSON, hash failures, blocked-report preservation, runner identity, attempt/branch/actor gates, job pagination, and the original packaging sequence.

The workflow is YAML round-trip checked. Each embedded Python program compiles; each shell block passes `bash -n`. The renderer asserts AST preservation while compacting source and enforces the GitHub 21,000-character limit. Current run blocks are 20,845 characters for snapshot and 11,319 for each part/metadata verification. All runner-context references are in step-level working-directory fields. The source has no GitHub expression interpolation.

No actionlint binary was available; these are focused platform semantic tests, not a claim of live GitHub acceptance. The parent should obtain two independent reviews before publication. Reviewers can read the unminified Python source and compare a rebuild of the workflow.

## Current hashes

- `recover_sealed.py`: `474d9276cf7dbfa60739203775091bfb03f8ff7c0461fc0e68a95f5f43215fdd`
- `worker35-sealed-recovery.yml`: `a10b275f57627c84aba5bbdde5bc14dc507bec594ea70ce83b06f8b12e04ead6`
- `build_workflow.py`: `03f4cedb0bb9f7920105888fbce706fc0b7eebc51d97e21fbef85f8e24bfd750`
