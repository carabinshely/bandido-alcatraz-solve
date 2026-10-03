# Worker35 three-file tail preservation

## Scope and publication

This is a separate evidence-preservation workflow. Publish only the reviewed `worker35-tail-recovery.yml` as `.github/workflows/worker35-tail-recovery.yml` on exact branch `research/worker35-tail-recovery-36990202101`. It permits owner-triggered push attempt 1, one job, original registered runner ID 2/name `bandido-alcatraz-ci`, read-only repository/Actions permission, and a pinned upload-artifact action. No checkout, repository dependency imports, raw game execution, policy calls, seeds, receipt changes, archive extraction/repacking, or original-file writes occur.

Implementation and tests occurred outside the repository. No publication or live workflow execution was performed. Tests use invented opaque bytes except one bounded integration read of the already-preserved metadata ZIP; original raw research files and the sealed archive were not opened locally.

## Inputs and exact gates

- Original run 36990202101 attempt 1, failed job 110784375570, head `7ac2f62c9c5c9dcac9ec9b8770382960f985acc2`; authenticated metadata must retain cancelled cohort, failed finalization, successful original packaging and failed original upload
- Prior successful sealed recovery 37104113098 attempt 1 at head `f10138c716246929ac3f3a752f555c3b17ee8327`
- Accepted original manifest SHA256 `eaa4f9360aea9bc51a726cd02fb342217cb02381047cfcbdc1b67a559fd2be72`, exactly 2,162 original file paths
- Accepted sealed archive identity 29,742,478 bytes / SHA256 `47b3f93e8825936c5106820bc536f8e7dfbfb4781ab9680bf495c15593767ba1`
- Original receipt SHA256 `027b6b35d75983ecf1760395418ff00d2df2a7fab63afee617bc73e4d8e3b3af`, exact frozen string run/attempt identities, original head/freeze, `execution_blocked` status and null classification
- Current expected complete file sizes: call-results/pass-2/1000319.jsonl 208,945; decision-traces/pass-2/1000319.jsonl 133,757; resource-metrics.jsonl 14,404,454 bytes

The runtime summary deliberately includes source_before and source_at_finalization (Python3.11.16). Original initialization provenance (Python3.12.3) remains unchanged in the already preserved sealed receipt; this short summary does not remove or reconcile that difference.

All reads use canonical absolute paths and descriptor-relative no-follow traversal. Symlinks, nonregular files, hard links, wrong file owners, missing/extra file paths, manifest drift, receipt drift, and size drift block acceptance. The original raw tree must contain exactly the accepted manifest's file-path population. Directory metadata is bounded to depth eight and 100 directories; it is compared before and after reading.

## Byte-preservation procedure

1. Create a fresh exclusive sibling `bandido-worker35-tail-recovery/<new-run>/1`
2. Pin original manifest/receipt identity and record authenticated Actions metadata and selected pre-run/finalization runtime identity
3. Inventory the exact source tree without following symlinks or opening unrelated file contents
4. Copy only the three named whole files, under fixed flat names, while hashing their bytes and each original-length prefix
5. Hash every other original file and compare it with its accepted sealed-manifest hash; do not parse raw file contents
6. Reread/hash every source file and compare full hash, size and file stamp with the first pass; compare directory inventory and manifest/receipt identity again
7. Rehash the three copied files; produce hash/stamp inventory and a preservation report
8. Seal only the fresh destination directory through its held descriptor (copied files remain private mode0600), bind the upload to the already observed expected file hashes, and carry hash/stamp/location pins in trusted step outputs; verify these before and after one upload of seven explicit filenames

No pathname-based chmod is performed. Capture requires every expected filename and rejects staged-byte changes instead of blessing a new baseline. A successful snapshot therefore has exactly all seven required files. If a source read failed mid-copy, an unmatched named partial copy may be preserved only under a blocked/contradictory report; it has no completed source-inventory identity and must never be accepted as a verified full copy.

The only raw content copied is the three complete named files, about 14.1 MiB total. Four metadata files accompany them: accepted manifest, authenticated Actions metadata, observed source inventory, recovery report. The upload payload is strictly capped at 29 MiB, leaving room for provider ZIP overhead below the download ceiling. No recursive directory upload is used.

The two full source passes share a strict read counter capped at 16 GiB minus 128 MiB. That reservation covers additional bounded metadata, copied-file and upload-verification reads. The expected source is about 737 MB per pass. Snapshot code has a 600-second alarm; verification code has 90-second alarms; the whole job is limited to 15 minutes. All GitHub response bodies/pagination and file/directory populations are bounded.

## Contradictions and failure

A prefix mismatch or another file's unexpected hash does not discard a copy or alter the originals. All three copies and the bounded hash inventory are retained, the report says `preserved_with_contradictions`, and the snapshot step fails. Other interruptions or integrity failures say `preservation_blocked` and retain any copied prefix or completed file. An always-on upload path can preserve these bytes plus the failure report after local safety checks.

Before fresh snapshot creation, API/source identity failures remain in the Actions log; no source content has been copied. If metadata writing/upload checks themselves fail, no unsafe upload is enabled, all existing bytes remain, and logs record the failure. A failed or cancelled check is never treated as acceptance.

## Acceptance boundary

The report describes local bounded observations only. It explicitly says quiescence is not proven, no scientific interpretation/classification occurred, and remote artifact bytes are not yet verified. Same-UID or higher-ancestor races are not solved as a general hostile-host problem.

The parent must independently download the artifact, verify provider ZIP identity, validate its exact bounded seven-member inventory, and pin `recovery-report.json` to `report_sha256` printed in the snapshot log. Then verify the report-bound authenticated metadata and source inventory hashes, the accepted manifest hash, and each copied file against the reported hash/size. Recompute the three prefix hashes and require every other observed file hash to match the accepted manifest before reporting byte preservation as accepted. A green workflow is only successful execution/upload attempts, not remote-byte acceptance or a scientific result.

## Verification and current hashes

`python3 -B -m unittest -v` passes 25 tests. Coverage includes byte-exact three-file copying, two-pass full inventory verification, prefix/non-tail hash contradictions, source population/size drift, symlink/hardlink/FIFO rejection, source mutation, read budget, destination collision, upload write/restore detection, and bounded metadata integration.

Rendered YAML round-trips; Python blocks compile and preserve renderer AST semantics after removing each step’s unreachable other-mode branch; shell blocks pass `bash -n`. Run strings are 20,999 and 8,424 characters, below GitHub's 21,000-character limit. Runner context is step-only. No actionlint binary was available; these checks are not a live GitHub acceptance claim.

- Source SHA256: `888e32b41e948ddc7fe90d357088d0777b625230e2c0745754aa0b81415578e2`
- Workflow SHA256: `bb7e4ce2fa2b457f794c6c57bc5ec242f0ceb9cc581c07b6250734890e29981c`
- Renderer SHA256: `7180864d7ebf29a107466ceb5ceca66016abeb1419b1655adb8a3c7e5135bd5d`
